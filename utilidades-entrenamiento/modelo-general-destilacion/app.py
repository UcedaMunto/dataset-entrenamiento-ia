#!/usr/bin/env python3
import argparse
import base64
import csv
import hashlib
import json
import os
import random
import re
import signal
import shutil
import sqlite3
import sys
import threading
import time
import unicodedata
from pathlib import Path

import requests
from PIL import Image


ROOT = Path(__file__).resolve().parent
SOURCE_CONFIG = ROOT / "sources.json"
IMAGE_EXTENSIONS = {".avif", ".bmp", ".gif", ".jpeg", ".jpg", ".png", ".webp"}
REMOTE_IMAGE_EXTENSIONS = {".gif", ".jpeg", ".jpg", ".png", ".webp"}
MAX_IMAGE_BYTES = 200_000
NIM_MIN_REQUEST_INTERVAL_SECONDS = 3
NIM_TIMEOUT_RETRY_MIN_SECONDS = 30
NIM_TIMEOUT_RETRY_MAX_SECONDS = 120
_nim_request_lock = threading.Lock()
_last_nim_request_at: float | None = None
NIM_MODEL_MAX_STRIKES = 4
_nim_model_strikes: dict[str, int] = {}
_NIM_PERMANENT_ERROR = re.compile(r"HTTP (401|403|404)\b")
_NIM_TRANSIENT_ERROR = re.compile(r"HTTP (429|5\d\d)\b")
CANCEL_REQUESTED = threading.Event()
ANALYSIS_PROMPT_VERSION = "4"
NIM_ANALYSIS_PROMPT_VERSION = "5"
NIM_VISION_MODEL = "nvidia/nemotron-3.5-super-vl-120b-a12b"
DEFAULT_NIM_FALLBACK_MODELS = (
    "meta/llama-3.2-11b-vision-instruct",
    "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning",
)
DEFAULT_PROMPT_INSTRUCTIONS = (
    "Determina si la imagen muestra claramente una sola prenda de la clase indicada. "
    "Si no corresponde a la clase, está corrupta, es ilegible, contiene principalmente "
    "otra cosa o no permite describirla con confianza, marca apta=false y explica "
    "brevemente el motivo. No cambies la clase canónica. Si es apta, describe solo "
    "rasgos visuales verificables en español. Elige cero o más colores y estilos de "
    "los vocabularios proporcionados. No inventes material, talla, marca, contexto de "
    "uso, identidad, género ni atributos no visibles. Ante cualquier duda importante, "
    "descarta la imagen."
)
IMAGE_MIME_TYPES = {
    "GIF": "image/gif",
    "JPEG": "image/jpeg",
    "PNG": "image/png",
    "WEBP": "image/webp",
}
PROVIDER_DEFAULTS = {
    "openai": ("OPENAI_API_KEY", "OPENAI_BASE_URL", "OPENAI_MODEL",
               "https://api.openai.com/v1", "gpt-4o-mini"),
    "nim": ("NVIDIA_NIM_API_KEY", "NVIDIA_NIM_BASE_URL", "NVIDIA_NIM_MODEL",
            "https://integrate.api.nvidia.com/v1", NIM_VISION_MODEL),
    "deepseek": ("DEEPSEEK_API_KEY", "DEEPSEEK_BASE_URL", "DEEPSEEK_MODEL",
                 "https://api.deepseek.com", "deepseek-flash"),
}
CATEGORY_PATHS = {
    "abrigo": "superior/abrigos",
    "blusa": "superior/blusas",
    "camisa": "superior/camisas",
    "chaqueta": "superior/chaquetas",
    "falda": "inferior/faldas",
    "pantalon": "inferior/pantalones",
    "short": "inferior/shorts",
    "sueter": "superior/sueteres",
    "vestido": "inferior_superior/vestido",
}


class AnnotationTimeoutError(RuntimeError):
    pass


class ProcessingCancelled(RuntimeError):
    pass


def request_processing_cancel(signum, frame) -> None:
    CANCEL_REQUESTED.set()


def install_cancellation_handler() -> None:
    signal.signal(signal.SIGTERM, request_processing_cancel)


def normalize(value: str) -> str:
    value = unicodedata.normalize("NFKD", value.casefold())
    value = "".join(char for char in value if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", "-", value).strip("-")


def canonical_category(value: str) -> str:
    return "camisa" if normalize(value) in {"camisa", "camiseta"} else value


def nim_model_chain(primary_model: str) -> list[str]:
    configured = os.environ.get("NVIDIA_NIM_FALLBACK_MODELS", "")
    fallback_models = (
        [model.strip() for model in configured.split(",") if model.strip()]
        if configured.strip()
        else list(DEFAULT_NIM_FALLBACK_MODELS)
    )
    return list(dict.fromkeys([primary_model, *fallback_models]))


def load_sources() -> dict:
    try:
        sources = json.loads(SOURCE_CONFIG.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeError(f"No se pudo leer el inventario {SOURCE_CONFIG}: {error}") from error
    if not isinstance(sources, dict):
        raise ValueError("sources.json debe contener un objeto.")
    return sources


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audita e importa imágenes etiquetadas al dataset local."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    audit = subparsers.add_parser("audit", help="Cuenta imágenes y etiquetas; no modifica archivos.")
    audit.add_argument("--source", default="all")

    ingest = subparsers.add_parser("ingest", help="Copia imágenes y registra metadatos.")
    ingest.add_argument("--source", default="all")
    ingest.add_argument("--execute", action="store_true", help="Confirma escrituras en dataset/ y SQLite.")
    ingest.add_argument(
        "--provider",
        choices=("none", "openai", "nim", "deepseek"),
        default=os.environ.get("ANNOTATION_PROVIDER", "none"),
    )
    ingest.add_argument("--allow-remote", action="store_true", help="Autoriza enviar imágenes al proveedor elegido.")
    ingest.add_argument("--limit", type=int, help="Límite obligatorio de imágenes si se usa un proveedor remoto.")

    return parser.parse_args()


def select_sources(sources: dict, requested: str) -> dict:
    if requested == "all":
        return sources
    if requested not in sources:
        raise ValueError(f"Fuente desconocida {requested!r}. Disponibles: {', '.join(sources)}")
    return {requested: sources[requested]}


def find_class(relative_path: Path, class_map: dict) -> tuple[str | None, str | None]:
    normalized_map = {
        normalize(label): (label, category) for label, category in class_map.items()
    }
    for part in reversed(relative_path.parts[:-1]):
        key = normalize(part)
        if key in normalized_map:
            return part, normalized_map[key][1]
    return None, None


def find_split(relative_path: Path, digest: str) -> str:
    for part in relative_path.parts[:-1]:
        split = normalize(part)
        if split == "train":
            return "train"
        if split in {"val", "valid", "validation"}:
            return "val"
        if split in {"test", "testing"}:
            return "test"
    number = int(digest[:8], 16) % 100
    return "train" if number < 80 else "val" if number < 90 else "test"


def scan_source(source_root: Path, source: dict) -> tuple[list[dict], dict]:
    if not source_root.is_dir():
        return [], {"missing_directory": str(source_root)}

    if source.get("labels_csv"):
        return scan_labeled_csv(source_root, source)

    counts = {"images": 0, "mapped": 0, "unmapped": 0, "oversize": 0}
    items = []
    for path in sorted(source_root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in IMAGE_EXTENSIONS:
            continue
        counts["images"] += 1
        if path.stat().st_size > MAX_IMAGE_BYTES:
            counts["oversize"] += 1
            continue
        relative_path = path.relative_to(source_root)
        source_label, category = find_class(relative_path, source.get("class_map", {}))
        if category is None:
            counts["unmapped"] += 1
            continue
        category = canonical_category(category)
        counts["mapped"] += 1
        digest = file_digest(path)
        items.append({
            "path": path,
            "relative_path": relative_path,
            "label": source_label,
            "category": category,
            "digest": digest,
            "split": find_split(relative_path, digest),
        })
    return items, counts


def scan_labeled_csv(source_root: Path, source: dict) -> tuple[list[dict], dict]:
    manifest = source_root / source["labels_csv"]
    if not manifest.is_file():
        return [], {"missing_directory": str(manifest)}

    counts = {"images": 0, "mapped": 0, "unmapped": 0, "oversize": 0}
    items = []
    class_map = {normalize(label): category for label, category in source["class_map"].items()}
    try:
        with manifest.open(newline="", encoding="utf-8-sig") as stream:
            rows = csv.DictReader(stream)
            required = {"image", "label"}
            if not rows.fieldnames or not required.issubset(rows.fieldnames):
                raise ValueError(f"{manifest} debe tener columnas {sorted(required)}.")
            for row in rows:
                counts["images"] += 1
                source_label = row["label"].strip()
                label = normalize(source_label)
                category = class_map.get(label)
                if category is None:
                    counts["unmapped"] += 1
                    continue
                category = canonical_category(category)
                image_id = Path(row["image"]).name
                image_path = (source_root / source["image_dir"] / f"{image_id}.jpg").resolve()
                if not image_path.is_relative_to(source_root.resolve()):
                    raise ValueError(f"Ruta insegura en {manifest}: {row['image']}")
                if not image_path.is_file():
                    raise FileNotFoundError(f"Imagen anotada en CSV que no existe: {image_path}")
                if image_path.stat().st_size > MAX_IMAGE_BYTES:
                    counts["oversize"] += 1
                    continue
                digest = file_digest(image_path)
                counts["mapped"] += 1
                items.append({
                    "path": image_path,
                    "relative_path": image_path.relative_to(source_root.resolve()),
                    "label": source_label,
                    "category": category,
                    "digest": digest,
                    "split": find_split(Path(), digest),
                })
    except (OSError, csv.Error) as error:
        raise RuntimeError(f"No se pudo leer el manifiesto {manifest}: {error}") from error
    return items, counts


def file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as error:
        raise RuntimeError(f"No se pudo leer {path}: {error}") from error
    return digest.hexdigest()


def command_audit(sources: dict, selected: dict) -> int:
    total_images = 0
    for source_id, source in selected.items():
        source_root = ROOT / "datos-crudos" / source["path"]
        _, counts = scan_source(source_root, source)
        if "missing_directory" in counts:
            print(f"{source_id}: directorio ausente ({counts['missing_directory']})")
            continue
        total_images += counts["images"]
        status = "habilitada" if source.get("allow_import") else "bloqueada hasta verificar licencia"
        if source.get("benchmark_only"):
            status = "benchmark solamente; fuera del dataset de entrenamiento"
        print(
            f"{source_id}: imágenes={counts['images']}, mapeadas={counts['mapped']}, "
            f"sin clase={counts['unmapped']}, >200 KB omitidas={counts['oversize']}; {status}"
        )
    if total_images == 0:
        print("No hay imágenes locales reconocidas; audit no descarga repositorios ni datasets.")
    return 0


def get_catalog(connection: sqlite3.Connection, code: str) -> list[str]:
    row = connection.execute(
        "SELECT valores_permitidos FROM catalogo_propiedad WHERE codigo = ? AND activo = 1",
        (code,),
    ).fetchone()
    if row is None or row[0] is None:
        raise ValueError(f"Falta vocabulario activo para {code} en el catálogo SQLite.")
    values = json.loads(row[0])
    if not isinstance(values, list) or not all(isinstance(item, str) for item in values):
        raise ValueError(f"Vocabulario inválido en catalogo_propiedad.{code}.")
    return values


def ensure_database(database: Path) -> None:
    schema = Path("/app/schema.sql")
    if not schema.is_file():
        raise FileNotFoundError(f"No está montado el esquema del proyecto: {schema}")
    database.parent.mkdir(parents=True, exist_ok=True)
    try:
        sql = schema.read_text(encoding="utf-8")
        with sqlite3.connect(database, timeout=30) as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.executescript(sql)
            columns = {
                row[1] for row in connection.execute("PRAGMA table_info(prenda_imagen)")
            }
            if "etiqueta_fuente" not in columns:
                connection.execute("ALTER TABLE prenda_imagen ADD COLUMN etiqueta_fuente TEXT")
            if connection.execute("PRAGMA foreign_keys").fetchone()[0] != 1:
                raise RuntimeError("SQLite no activó las claves foráneas.")
    except (OSError, sqlite3.Error) as error:
        raise RuntimeError(f"No se pudo inicializar {database}: {error}") from error


def provider_settings(provider: str) -> tuple[str, str, str]:
    if provider == "none":
        return "", "", ""
    key_name, url_name, model_name, default_url, default_model = PROVIDER_DEFAULTS[provider]
    api_key = os.environ.get(key_name, "").strip()
    if not api_key:
        raise ValueError(f"Configura {key_name} en el archivo .env.")
    base_url = os.environ.get(url_name, default_url).strip().rstrip("/")
    model = os.environ.get(model_name, default_model).strip()
    if not base_url or not model:
        raise ValueError(f"Configura {url_name} y {model_name} para el proveedor {provider}.")
    return api_key, base_url, model


def image_data_url(path: Path) -> str:
    try:
        if path.stat().st_size > MAX_IMAGE_BYTES:
            raise ValueError(f"La imagen supera el límite de {MAX_IMAGE_BYTES} bytes: {path}")
        with Image.open(path) as source:
            image_format = source.format
            source.verify()
        mime_type = IMAGE_MIME_TYPES.get(image_format)
        if mime_type is None:
            raise ValueError(f"Formato no admitido para envío remoto: {image_format}")
        encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    except (OSError, ValueError) as error:
        raise RuntimeError(f"No se pudo preparar imagen para anotación {path}: {error}") from error
    return f"data:{mime_type};base64,{encoded}"


def analysis_fingerprint(
    digest: str, category: str, provider: str, model: str, prompt: str = ""
) -> str:
    prompt_version = (
        NIM_ANALYSIS_PROMPT_VERSION if provider == "nim" else ANALYSIS_PROMPT_VERSION
    )
    identity = json.dumps(
        [digest, category, provider, model, prompt_version, prompt],
        separators=(",", ":"),
    )
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()


def get_cached_analysis(
    connection: sqlite3.Connection, fingerprint: str
) -> dict | None:
    row = connection.execute(
        "SELECT resultado_json FROM analisis_imagen WHERE huella_analisis = ?",
        (fingerprint,),
    ).fetchone()
    if row is None:
        return None
    try:
        result = json.loads(row[0])
    except json.JSONDecodeError as error:
        raise ValueError(f"Resultado cacheado inválido para {fingerprint}.") from error
    if not isinstance(result, dict) or not isinstance(result.get("apta"), bool):
        raise ValueError(f"Resultado cacheado inválido para {fingerprint}.")
    return result


def get_setting(connection: sqlite3.Connection, key: str, default: str) -> str:
    row = connection.execute(
        "SELECT valor FROM pipeline_config WHERE clave = ?", (key,)
    ).fetchone()
    return default if row is None else row[0]


def build_prompt(
    instructions: str,
    known_type: str,
    colors: list[str],
    styles: list[str],
    max_description_words: int = 12,
    max_attribute_values: int = 3,
    max_reason_words: int | None = None,
    seasons: list[str] | None = None,
) -> str:
    seasons = seasons or []
    reason_instruction = (
        f"Si apta es false, el motivo_descarte debe tener máximo {max_reason_words} palabras. "
        if max_reason_words is not None
        else ""
    )
    return (
        "Contexto estructurado en TOON:\n"
        f"tarea: {json.dumps('validar_y_describir_prenda', ensure_ascii=False)}\n"
        f"clase_fuente: {json.dumps(known_type, ensure_ascii=False)}\n"
        f"clase_canonica: {json.dumps(known_type, ensure_ascii=False)}\n"
        f"colores[{len(colors)}]: {', '.join(json.dumps(value, ensure_ascii=False) for value in colors)}\n"
        f"estilos[{len(styles)}]: {', '.join(json.dumps(value, ensure_ascii=False) for value in styles)}\n\n"
        f"temporadas[{len(seasons)}]: "
        f"{', '.join(json.dumps(value, ensure_ascii=False) for value in seasons)}\n\n"
        "Instrucciones:\n"
        f"{instructions.strip()}\n\n"
        "Devuelve únicamente un objeto JSON completo, sin Markdown ni texto adicional. "
        "Ejemplo de forma (sustituye los valores por observaciones reales y valores de los "
        "vocabularios): "
        '{"apta":true,"motivo_descarte":"","descripcion":"Camisa azul lisa.",'
        '"colores":["azul"],"estilos":["casual"],"temporadas":["invierno"]}. '
        "Usa estas claves: apta (booleano), motivo_descarte (texto), descripcion "
        f"(una frase de máximo {max_description_words} palabras), colores "
        f"(lista de máximo {max_attribute_values}) y estilos "
        f"(lista de máximo {max_attribute_values}; puede incluir nuevos valores observables), "
        "temporadas (lista de máximo 2; puede incluir nuevos valores con evidencia visual). "
        f"{reason_instruction}Mantén "
        "motivo_descarte como cadena vacía cuando la imagen sea apta; nunca uses null. "
        "Mantén la respuesta muy concisa. Los colores solo pueden usar valores del catálogo. "
        "Estilos y temporadas pueden ser opciones nuevas, concretas y observables; se agregarán "
        "al catálogo. Si apta es false, incluye un motivo breve."
    )


def build_annotation_prompt(
    instructions: str,
    known_type: str,
    colors: list[str],
    styles: list[str],
    provider: str,
    seasons: list[str] | None = None,
) -> str:
    if provider == "nim":
        return "\n\n--- SIGUIENTE ETAPA ---\n\n".join(
            build_nim_stage_prompts(instructions, known_type, colors, styles, seasons or [])
        )
    return build_prompt(
        instructions, known_type, colors, styles, seasons=seasons
    )


def build_nim_stage_prompts(
    instructions: str,
    known_type: str,
    colors: list[str],
    styles: list[str],
    seasons: list[str] | None = None,
) -> list[str]:
    seasons = seasons or []
    color_values = ", ".join(json.dumps(value, ensure_ascii=False) for value in colors)
    style_values = ", ".join(json.dumps(value, ensure_ascii=False) for value in styles)
    season_values = ", ".join(json.dumps(value, ensure_ascii=False) for value in seasons)
    context = (
        f"Clase de prenda: {known_type}. "
        "Analiza solo la prenda visible en la imagen."
    )
    return [
        (
            "ETAPA 1/4 — COLORES\n"
            f"{context}\n"
            f"Colores permitidos: [{color_values}].\n"
            "Devuelve solo un objeto JSON con la clave colores y una lista de cero, uno "
            'o dos valores exactos del catálogo, por ejemplo {"colores":["azul"]}. '
            "No incluyas estilo, descripción, explicación ni otras claves."
        ),
        (
            "ETAPA 2/4 — ESTILOS\n"
            f"{context}\n"
            f"Estilos permitidos: [{style_values}].\n"
            "Devuelve solo un objeto JSON con la clave estilos y una lista de cero, uno "
            'o dos estilos, por ejemplo {"estilos":["casual"]}. '
            "Puedes proponer estilos nuevos, concretos y observables. "
            "No incluyas colores, temporadas, descripción ni otras claves."
        ),
        (
            "ETAPA 3/4 — TEMPORADAS\n"
            f"{context}\n"
            f"Opciones conocidas: [{season_values}].\n"
            "Devuelve solo un objeto JSON con la clave temporadas y una lista de cero, "
            'uno o dos opciones, por ejemplo {"temporadas":["invierno"]}. '
            "Puedes proponer opciones nuevas solo cuando exista evidencia visual; "
            "si no se infiere una temporada, devuelve una lista vacía. "
            "No incluyas colores, estilos, descripción ni otras claves."
        ),
        (
            "ETAPA 4/4 — VALIDACIÓN Y DESCRIPCIÓN\n"
            f"{context}\n"
            "Instrucciones editables:\n"
            f"{instructions.strip()}\n\n"
            "Devuelve únicamente un objeto JSON completo y conciso con las claves apta "
            "(booleano), motivo_descarte (texto de máximo 8 palabras) y descripcion "
            "(texto de máximo 8 palabras; cadena vacía si apta es false). "
            'Ejemplo: {"apta":true,"motivo_descarte":"","descripcion":"Camisa azul lisa"}. '
            "No incluyas colores, estilos ni temporadas; se combinarán desde las etapas anteriores. "
            "Si apta es true, deja motivo_descarte vacío."
        ),
    ]


def save_analysis(
    connection: sqlite3.Connection,
    fingerprint: str,
    item: dict,
    provider: str,
    model: str,
    annotation: dict,
    source_id: str | None = None,
) -> None:
    result = dict(annotation)
    if source_id is not None:
        result["_source_id"] = source_id
        result["_source_relative_path"] = item["relative_path"].as_posix()
    connection.execute(
        """
        INSERT INTO analisis_imagen
            (huella_analisis, sha256, categoria, proveedor, modelo,
             version_prompt, estado, resultado_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            fingerprint,
            item["digest"],
            item["category"],
            provider,
            model,
            NIM_ANALYSIS_PROMPT_VERSION if provider == "nim" else ANALYSIS_PROMPT_VERSION,
            "aceptada" if annotation["apta"] else "descartada",
            json.dumps(result, ensure_ascii=False),
        ),
    )


def parse_model_json(content: str) -> dict:
    text = content.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.IGNORECASE)
    try:
        result = json.loads(text)
    except json.JSONDecodeError as error:
        result = None
        start = text.find("{")
        if start != -1:
            try:
                result, _ = json.JSONDecoder().raw_decode(text[start:])
            except json.JSONDecodeError:
                result = None
        if result is None:
            raise ValueError(
                f"El proveedor no devolvió JSON válido: {error}. "
                f"Salida: {text[:120]!r}"
            ) from error
    if not isinstance(result, dict):
        raise ValueError("La respuesta del proveedor debe ser un objeto JSON.")
    return result


def wait_for_nim_request_slot() -> None:
    global _last_nim_request_at
    with _nim_request_lock:
        now = time.monotonic()
        if _last_nim_request_at is not None:
            remaining = NIM_MIN_REQUEST_INTERVAL_SECONDS - (now - _last_nim_request_at)
            if remaining > 0:
                time.sleep(remaining)
                now = time.monotonic()
        _last_nim_request_at = now


def validate_nim_stage_result(result: dict, stage: str) -> None:
    if stage in {"colores", "estilos", "temporadas"}:
        values = result.get(stage)
        if not isinstance(values, list) or any(not isinstance(value, str) for value in values):
            raise ValueError(f"La etapa {stage} debe devolver una lista de texto.")
        return
    if stage != "validación":
        raise ValueError(f"Etapa NIM desconocida: {stage}.")
    suitable = result.get("apta")
    if not isinstance(suitable, bool):
        raise ValueError("La etapa validación debe devolver apta como booleano.")
    reason = result.get("motivo_descarte", "")
    if reason is None and suitable:
        reason = ""
    if not isinstance(reason, str):
        raise ValueError("La etapa validación debe devolver motivo_descarte como texto.")
    if suitable:
        description = result.get("descripcion")
        if not isinstance(description, str) or not description.strip():
            raise ValueError("La etapa validación debe devolver una descripción no vacía.")


def request_nim_stage_json(
    path: Path,
    image_url: str,
    api_key: str,
    base_url: str,
    model: str,
    prompt: str,
    stage: str,
) -> dict:
    payload = {
        "model": model,
        "temperature": 0,
        "max_tokens": 256,
        "response_format": {"type": "json_object"},
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": image_url}},
            ],
        }],
    }
    if model == NIM_VISION_MODEL:
        payload["reasoning_effort"] = "none"
    for attempt in range(2):
        wait_for_nim_request_slot()
        if CANCEL_REQUESTED.is_set():
            raise ProcessingCancelled("Detención solicitada antes de enviar la imagen.")
        try:
            response = requests.post(
                f"{base_url}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json=payload,
                timeout=(15, 120),
            )
            response.raise_for_status()
            body = response.json()
            choice = body["choices"][0]
            content = choice["message"]["content"]
        except requests.HTTPError as error:
            status = response.status_code
            detail = response.text[:500].replace(api_key, "[REDACTED]")
            raise RuntimeError(
                f"El proveedor nim respondió HTTP {status} para el modelo {model}. "
                f"Detalle: {detail or 'sin detalle'}"
            ) from error
        except requests.Timeout as error:
            raise AnnotationTimeoutError(
                f"Timeout al solicitar anotación al proveedor nim: {error}"
            ) from error
        except requests.RequestException as error:
            raise RuntimeError(
                f"Falló la solicitud de anotación al proveedor nim: {error}"
            ) from error
        except (ValueError, KeyError, IndexError, TypeError) as error:
            raise RuntimeError(f"Respuesta inesperada del proveedor nim: {error}") from error

        if not isinstance(content, str):
            raise ValueError(
                f"NIM no devolvió texto JSON para la etapa {stage} ({path.name})."
            )
        try:
            result = parse_model_json(content)
        except ValueError as parse_error:
            failure = parse_error
            problem = "JSON malformado"
        else:
            try:
                validate_nim_stage_result(result, stage)
                return result
            except ValueError as validation_error:
                failure = validation_error
                problem = "estructura JSON inesperada"
        if attempt == 0:
            if CANCEL_REQUESTED.is_set():
                raise ProcessingCancelled(
                    "Detención solicitada; no se reintentará la respuesta JSON inválida."
                ) from failure
            payload["max_tokens"] = 512
            payload["messages"][0]["content"][0]["text"] += (
                "\nReintento: devuelve únicamente un objeto JSON con la estructura "
                "exacta solicitada, sin razonamiento ni texto adicional."
            )
            print(
                f"Salida NIM inválida en etapa {stage} ({problem}; "
                f"finish_reason={choice.get('finish_reason') or 'desconocido'}; "
                f"caracteres={len(content)}); se reintentará una vez."
            )
            continue
        raise ValueError(
            f"NIM devolvió una salida no válida en etapa {stage} ({problem}; "
            f"finish_reason={choice.get('finish_reason') or 'desconocido'}; "
            f"caracteres={len(content)}): {failure}"
        ) from failure
    raise RuntimeError(f"Se agotaron los intentos de NIM para la etapa {stage}.")


def _nim_catalog_values(result: dict, field: str, catalog: list[str]) -> list[str]:
    values = result.get(field)
    if not isinstance(values, list) or any(not isinstance(value, str) for value in values):
        raise ValueError(f"NIM no devolvió una lista de texto para {field}.")
    distinct_values = set(values)
    valid_values = sorted(value for value in distinct_values if value in catalog)
    unknown_count = len(distinct_values) - len(valid_values)
    if unknown_count:
        print(
            f"NIM propuso {unknown_count} valor(es) fuera del catálogo en {field}; "
            "se ignoraron."
        )
    if len(valid_values) > 2:
        print(f"NIM propuso más de dos valores en {field}; se conservaron solo dos.")
    accepted = valid_values[:2]
    return accepted


def _dynamic_catalog_values(result: dict, field: str, limit: int = 2) -> list[str]:
    values = result.get(field, [])
    if not isinstance(values, list) or any(not isinstance(value, str) for value in values):
        raise ValueError(f"El proveedor no devolvió una lista de texto para {field}.")
    cleaned = []
    seen = set()
    for value in values:
        normalized = " ".join(value.split())
        if not normalized or len(normalized) > 40:
            raise ValueError(f"Valor inválido propuesto para {field}.")
        folded = normalized.casefold()
        if folded not in seen:
            cleaned.append(normalized)
            seen.add(folded)
    return cleaned[:limit]


def merge_catalog_values(
    connection: sqlite3.Connection, code: str, values: list[str]
) -> None:
    if not values:
        return
    connection.execute("BEGIN IMMEDIATE")
    row = connection.execute(
        "SELECT valores_permitidos FROM catalogo_propiedad WHERE codigo=? AND activo=1",
        (code,),
    ).fetchone()
    if row is None or row[0] is None:
        connection.rollback()
        raise ValueError(f"Falta propiedad activa con catálogo: {code}.")
    try:
        catalog = json.loads(row[0])
    except json.JSONDecodeError as error:
        connection.rollback()
        raise ValueError(f"Catálogo JSON inválido para {code}.") from error
    if not isinstance(catalog, list) or any(not isinstance(value, str) for value in catalog):
        connection.rollback()
        raise ValueError(f"Catálogo inválido para {code}.")
    existing = {value.casefold() for value in catalog}
    for value in values:
        if value.casefold() not in existing:
            catalog.append(value)
            existing.add(value.casefold())
    connection.execute(
        "UPDATE catalogo_propiedad SET valores_permitidos=? WHERE codigo=?",
        (json.dumps(catalog, ensure_ascii=False), code),
    )
    connection.commit()


def merge_annotation_catalogs(
    connection: sqlite3.Connection, annotation: dict | None
) -> None:
    if not annotation:
        return
    for code, field in (("estilo", "estilos"), ("temporada", "temporadas")):
        values = annotation.get(field, [])
        if not isinstance(values, list) or any(not isinstance(value, str) for value in values):
            raise ValueError(f"Lista de sugerencias inválida para {field}.")
        merge_catalog_values(connection, code, values)


def annotate_nim_image(
    path: Path,
    known_type: str,
    api_key: str,
    base_url: str,
    model: str,
    colors: list[str],
    styles: list[str],
    seasons: list[str],
    instructions: str,
) -> dict:
    image_url = image_data_url(path)
    color_prompt, style_prompt, season_prompt, decision_prompt = build_nim_stage_prompts(
        instructions, known_type, colors, styles, seasons
    )
    color_result = request_nim_stage_json(
        path, image_url, api_key, base_url, model, color_prompt, "colores"
    )
    style_result = request_nim_stage_json(
        path, image_url, api_key, base_url, model, style_prompt, "estilos"
    )
    season_result = request_nim_stage_json(
        path, image_url, api_key, base_url, model, season_prompt, "temporadas"
    )
    decision = request_nim_stage_json(
        path, image_url, api_key, base_url, model, decision_prompt, "validación"
    )

    suitable = decision.get("apta")
    reason = decision.get("motivo_descarte", "")
    if reason is None and suitable:
        reason = ""
    colors_found = _nim_catalog_values(color_result, "colores", colors)
    styles_found = _dynamic_catalog_values(style_result, "estilos")
    seasons_found = _dynamic_catalog_values(season_result, "temporadas")
    if not suitable:
        return {
            "apta": False,
            "motivo_descarte": " ".join(reason.strip().split()[:8])
            or "La IA descartó la imagen.",
            "colores": colors_found,
            "estilos": styles_found,
            "temporadas": seasons_found,
        }
    description = decision.get("descripcion")
    if not isinstance(description, str) or not description.strip():
        raise ValueError("NIM no devolvió una descripción para la prenda apta.")
    return {
        "apta": True,
        "motivo_descarte": "",
        "descripcion": " ".join(description.split()[:8]),
        "colores": colors_found,
        "estilos": styles_found,
        "temporadas": seasons_found,
    }


def annotate_image(
    path: Path,
    known_type: str,
    provider: str,
    api_key: str,
    base_url: str,
    model: str,
    colors: list[str],
    styles: list[str],
    instructions: str = DEFAULT_PROMPT_INSTRUCTIONS,
    seasons: list[str] | None = None,
) -> dict:
    if provider == "nim":
        return annotate_nim_image(
            path, known_type, api_key, base_url, model, colors, styles,
            seasons or [], instructions
        )
    prompt = build_annotation_prompt(
        instructions, known_type, colors, styles, provider, seasons
    )
    payload = {
        "model": model,
        "temperature": 0,
        "max_tokens": 1024,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": image_data_url(path)}},
            ],
        }],
    }
    if provider in {"nim", "deepseek"}:
        payload["response_format"] = {"type": "json_object"}
    if provider == "deepseek":
        payload["thinking"] = {"type": "disabled"}
    result = None
    for attempt in range(2):
        if provider == "nim":
            wait_for_nim_request_slot()
        if CANCEL_REQUESTED.is_set():
            raise ProcessingCancelled("Detención solicitada antes de enviar la imagen.")
        try:
            response = requests.post(
                f"{base_url}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json=payload,
                timeout=(15, 120),
            )
            response.raise_for_status()
            body = response.json()
            choice = body["choices"][0]
            content = choice["message"]["content"]
            finish_reason = choice.get("finish_reason")
        except requests.HTTPError as error:
            status = response.status_code
            detail = response.text[:500].replace(api_key, "[REDACTED]")
            raise RuntimeError(
                f"El proveedor {provider} respondió HTTP {status} para el modelo {model}. "
                f"Detalle: {detail or 'sin detalle'}"
            ) from error
        except requests.Timeout as error:
            raise AnnotationTimeoutError(
                f"Timeout al solicitar anotación al proveedor {provider}: {error}"
            ) from error
        except requests.RequestException as error:
            raise RuntimeError(
                f"Falló la solicitud de anotación al proveedor {provider}: {error}"
            ) from error
        except (ValueError, KeyError, IndexError, TypeError) as error:
            raise RuntimeError(f"Respuesta inesperada del proveedor {provider}: {error}") from error

        if not isinstance(content, str):
            raise ValueError("El proveedor debe responder texto JSON en choices[0].message.content.")
        try:
            result = parse_model_json(content)
            break
        except ValueError as error:
            incomplete = finish_reason == "length" or not content.strip()
            if attempt == 0 and incomplete:
                if CANCEL_REQUESTED.is_set():
                    raise ProcessingCancelled(
                        "Detención solicitada; no se reintentará la respuesta incompleta."
                    ) from error
                payload["max_tokens"] = 2048
                payload["messages"][0]["content"][0]["text"] += (
                    "\nResponde inmediatamente con el objeto JSON completo del ejemplo; "
                    "omite cualquier razonamiento, explicación o detalle adicional."
                )
                print(
                    f"Respuesta incompleta de {provider} (finish_reason="
                    f"{finish_reason or 'desconocido'}, caracteres={len(content)}); "
                    "se reintentará una vez con JSON conciso."
                )
                continue
            if finish_reason == "length":
                raise ValueError(
                    f"Respuesta truncada por límite de tokens (finish_reason=length, "
                    f"caracteres={len(content)}, max_tokens={payload['max_tokens']}); "
                    "se agotó un reintento y no se guardó el análisis."
                ) from error
            if not content.strip():
                raise ValueError(
                    f"El proveedor {provider} devolvió contenido vacío; se agotó un "
                    "reintento y no se guardó el análisis."
                ) from error
            raise ValueError(
                f"El proveedor devolvió JSON inválido "
                f"(finish_reason={finish_reason or 'desconocido'}, "
                f"caracteres={len(content)}): {error}"
            ) from error
    suitable = result.get("apta")
    if not isinstance(suitable, bool):
        raise ValueError("El proveedor debe indicar apta como booleano.")
    reason = result.get("motivo_descarte", "")
    if reason is None and suitable:
        reason = ""
    if not isinstance(reason, str):
        raise ValueError("El campo motivo_descarte debe ser texto.")
    if not suitable:
        return {
            "apta": False,
            "motivo_descarte": (
                " ".join(reason.strip().split()[:8])
                if provider == "nim"
                else reason.strip()[:500]
            ) or "La IA descartó la imagen.",
            "estilos": _dynamic_catalog_values(
                result, "estilos", 2 if provider == "nim" else 3
            ),
            "temporadas": _dynamic_catalog_values(result, "temporadas"),
        }
    description = result.get("descripcion")
    if not isinstance(description, str) or not description.strip():
        raise ValueError("El proveedor no devolvió una descripcion no vacía.")
    for field, vocabulary in (("colores", colors),):
        values = result.get(field, [])
        if not isinstance(values, list) or any(value not in vocabulary for value in values):
            raise ValueError(f"El campo {field} contiene valores fuera del catálogo.")
        result[field] = sorted(set(values))
        if provider == "nim":
            result[field] = result[field][:2]
    styles_found = _dynamic_catalog_values(
        result, "estilos", 2 if provider == "nim" else 3
    )
    seasons_found = _dynamic_catalog_values(result, "temporadas")
    return {
        "apta": True,
        "motivo_descarte": "",
        "descripcion": " ".join(description.split()[:8])
        if provider == "nim"
        else description.strip()[:1200],
        "colores": result["colores"],
        "estilos": styles_found,
        "temporadas": seasons_found,
    }


def annotate_with_provider_fallback(
    path: Path,
    known_type: str,
    provider: str,
    api_key: str,
    base_url: str,
    model: str,
    colors: list[str],
    styles: list[str],
    instructions: str,
    seasons: list[str],
    nim_settings: tuple[str, str, str] | None = None,
    unavailable_nim_models: set[str] | None = None,
) -> tuple[dict | None, str, str, int]:
    unavailable_nim_models = unavailable_nim_models if unavailable_nim_models is not None else set()
    candidates = [(provider, api_key, base_url, model)]
    if provider == "nim":
        candidates = [
            ("nim", api_key, base_url, candidate_model)
            for candidate_model in nim_model_chain(model)
            if candidate_model not in unavailable_nim_models
        ]
    elif provider == "deepseek" and nim_settings is not None:
        nim_key, nim_url, nim_model = nim_settings
        candidates.extend(
            ("nim", nim_key, nim_url, candidate_model)
            for candidate_model in nim_model_chain(nim_model)
            if candidate_model not in unavailable_nim_models
        )
    if not candidates:
        raise RuntimeError(
            "No quedan modelos NVIDIA NIM disponibles en esta ejecución; "
            "se detiene el lote para evitar repetir llamadas a modelos fallidos."
        )

    exhausted_timeouts = 0
    failed_nim_models: set[str] = set()
    last_error: RuntimeError | ValueError | None = None
    for candidate_index, (candidate_provider, candidate_key, candidate_url, candidate_model) in enumerate(candidates):
        attempts = 2 if candidate_provider == "nim" else 1
        for attempt in range(attempts):
            if CANCEL_REQUESTED.is_set():
                raise ProcessingCancelled("Detención solicitada antes de completar la anotación.")
            try:
                annotation = annotate_image(
                    path,
                    known_type,
                    candidate_provider,
                    candidate_key,
                    candidate_url,
                    candidate_model,
                    colors,
                    styles,
                    instructions,
                    seasons=seasons,
                )
                unavailable_nim_models.update(failed_nim_models)
                if candidate_provider == "nim":
                    _nim_model_strikes.pop(candidate_model, None)
                if candidate_index:
                    print(
                        f"Fallback completado: {candidate_provider}/{candidate_model} "
                        f"para {path.name}."
                    )
                return annotation, candidate_provider, candidate_model, exhausted_timeouts
            except ProcessingCancelled:
                raise
            except AnnotationTimeoutError as error:
                last_error = error
                if CANCEL_REQUESTED.is_set():
                    raise ProcessingCancelled(
                        "Detención solicitada; no se reintentará la petición NIM."
                    ) from error
                if attempt == 0 and candidate_provider == "nim":
                    delay = random.randint(
                        NIM_TIMEOUT_RETRY_MIN_SECONDS,
                        NIM_TIMEOUT_RETRY_MAX_SECONDS,
                    )
                    print(
                        f"Timeout de NIM para {path.name} con {candidate_model}; "
                        f"se reintentará una vez en {delay} segundos."
                    )
                    if CANCEL_REQUESTED.wait(delay):
                        raise ProcessingCancelled(
                            "Detención solicitada durante la espera de reintento NIM."
                        ) from error
                    continue
                if candidate_provider == "nim":
                    exhausted_timeouts += 1
                break
            except (RuntimeError, ValueError) as error:
                last_error = error
                if (
                    attempt == 0
                    and candidate_provider == "nim"
                    and _NIM_TRANSIENT_ERROR.search(str(error))
                ):
                    print(f"Error transitorio de NIM con {candidate_model}; se reintenta en 3 segundos.")
                    if CANCEL_REQUESTED.wait(3):
                        raise ProcessingCancelled(
                            "Detención solicitada durante la espera de reintento NIM."
                        ) from error
                    continue
                break

        if candidate_provider == "nim":
            strikes = _nim_model_strikes.get(candidate_model, 0) + 1
            _nim_model_strikes[candidate_model] = strikes
            if strikes >= NIM_MODEL_MAX_STRIKES or _NIM_PERMANENT_ERROR.search(str(last_error)):
                failed_nim_models.add(candidate_model)
        if candidate_index + 1 < len(candidates):
            next_provider, _, _, next_model = candidates[candidate_index + 1]
            print(
                f"Falló {candidate_provider}/{candidate_model} para {path.name}: "
                f"{last_error}. Se intentará {next_provider}/{next_model}."
            )

    unavailable_nim_models.update(failed_nim_models)
    if last_error is None:
        raise RuntimeError("No se pudo iniciar la anotación con ningún proveedor.")
    if provider == "deepseek" and nim_settings is None:
        print("No se pudo usar el fallback NVIDIA NIM: falta NVIDIA_NIM_API_KEY.")
    if isinstance(last_error, AnnotationTimeoutError) and exhausted_timeouts:
        print(
            f"Timeout agotado para todos los modelos NIM disponibles; "
            f"se omite {path.name} sin guardar análisis."
        )
        return None, provider, model, exhausted_timeouts
    raise last_error


def safe_extension(path: Path) -> str:
    extension = path.suffix.lower()
    return extension if extension in IMAGE_EXTENSIONS else ".jpg"


def import_one(
    connection: sqlite3.Connection,
    item: dict,
    source_id: str,
    source: dict,
    dataset_root: Path,
    annotation: dict | None,
    provider: str,
    model: str,
    created_files: list[Path],
) -> bool:
    connection.execute("BEGIN IMMEDIATE")
    exists = connection.execute(
        "SELECT 1 FROM prenda_imagen WHERE sha256 = ? LIMIT 1", (item["digest"],)
    ).fetchone()
    if exists:
        connection.rollback()
        return False

    code = f"{source_id}-{item['digest'][:16]}"
    category = canonical_category(item["category"])
    category_path = CATEGORY_PATHS[category]
    folder = dataset_root / category_path / code
    folder.mkdir(parents=True, exist_ok=True)
    image_path = folder / f"imagen{safe_extension(item['path'])}"
    if image_path.exists():
        raise FileExistsError(f"El destino ya existe y no está registrado: {image_path}")
    shutil.copy2(item["path"], image_path)
    created_files.append(image_path)
    relative_path = image_path.relative_to(dataset_root).as_posix()

    connection.execute(
        """
        INSERT INTO prenda
            (codigo, ruta_categoria, split, estado_revision, apta_para_entrenamiento)
        VALUES (?, ?, ?, 'pendiente', 0)
        """,
        (code, category_path, item["split"]),
    )
    garment_id = connection.execute(
        "SELECT id_prenda FROM prenda WHERE codigo = ?", (code,)
    ).fetchone()[0]
    connection.execute(
        """
        INSERT INTO prenda_imagen
            (id_prenda, ruta_relativa, es_fotografia_real, fuente, etiqueta_fuente, permiso_uso, sha256)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            garment_id,
            relative_path,
            int(source.get("photograph", True)),
            source_id,
            item["label"],
            source["license"],
            item["digest"],
        ),
    )
    type_property = connection.execute(
        "SELECT id_propiedad FROM catalogo_propiedad WHERE codigo = 'tipo_prenda'"
    ).fetchone()
    if type_property is None:
        raise ValueError("El catálogo SQLite no contiene tipo_prenda.")
    connection.execute(
        "INSERT INTO valor_propiedad_prenda (id_prenda, id_propiedad, valor) VALUES (?, ?, ?)",
        (garment_id, type_property[0], category),
    )

    if annotation:
        attributes = {
            "colores": annotation.get("colores", []),
            "estilos": annotation.get("estilos", []),
            "temporadas": annotation.get("temporadas", []),
        }
        connection.execute(
            """
            INSERT INTO descripcion_prenda
                (id_prenda, texto, atributos_sugeridos, proveedor, modelo, estado_revision)
            VALUES (?, ?, ?, ?, ?, 'pendiente')
            """,
            (
                garment_id,
                annotation["descripcion"],
                json.dumps(attributes, ensure_ascii=False),
                provider,
                model,
            ),
        )
    return True


def filter_duplicate_plans(
    plans: list[tuple[str, dict, dict]],
    database: Path,
    provider: str,
    model: str,
    limit: int | None,
) -> tuple[list[tuple[str, dict, dict]], int, int, int]:
    imported_hashes = set()
    cached_analyses = {}
    colors = []
    styles = []
    seasons = []
    instructions = DEFAULT_PROMPT_INSTRUCTIONS
    if database.is_file():
        with sqlite3.connect(database, timeout=30) as connection:
            imported_hashes = {
                row[0]
                for row in connection.execute(
                    "SELECT DISTINCT sha256 FROM prenda_imagen WHERE sha256 IS NOT NULL"
                )
            }
            if provider != "none":
                cached_analyses = {
                    row[0]: row[1]
                    for row in connection.execute(
                        "SELECT huella_analisis, resultado_json FROM analisis_imagen"
                    )
                }
                colors = get_catalog(connection, "color")
                styles = get_catalog(connection, "estilo")
                seasons = get_catalog(connection, "temporada")
                instructions = get_setting(
                    connection, "prompt_instructions", DEFAULT_PROMPT_INSTRUCTIONS
                )

    seen_hashes = set(imported_hashes)
    new_plans = []
    recoverable_plans = []
    duplicates = 0
    already_analyzed = 0
    for plan in plans:
        digest = plan[2]["digest"]
        if digest in seen_hashes:
            duplicates += 1
            continue
        seen_hashes.add(digest)
        if provider != "none":
            _, _, item = plan
            prompt = build_annotation_prompt(
                instructions, item["category"], colors, styles, provider, seasons
            )
            fingerprint = analysis_fingerprint(
                digest, item["category"], provider, model, prompt
            )
            cached_json = cached_analyses.get(fingerprint)
            if cached_json is not None:
                try:
                    cached = json.loads(cached_json)
                except json.JSONDecodeError as error:
                    raise ValueError(
                        f"Resultado cacheado inválido para {fingerprint}."
                    ) from error
                if not isinstance(cached, dict) or not isinstance(cached.get("apta"), bool):
                    raise ValueError(f"Resultado cacheado inválido para {fingerprint}.")
                if cached["apta"]:
                    recoverable_plans.append(plan)
                else:
                    already_analyzed += 1
                continue
        new_plans.append(plan)

    selected_new = new_plans if limit is None else new_plans[:limit]
    return (
        recoverable_plans + selected_new,
        duplicates,
        already_analyzed,
        len(recoverable_plans),
    )


def command_ingest(args: argparse.Namespace, selected: dict) -> int:
    if args.limit is not None and args.limit < 1:
        raise ValueError("--limit debe ser un entero positivo.")
    if args.provider != "none":
        if not args.execute:
            raise ValueError("Las llamadas API requieren --execute explícito.")
        if not args.allow_remote:
            raise ValueError("Añade --allow-remote para confirmar el envío de imágenes al proveedor.")
        if args.limit is None:
            raise ValueError("Las llamadas API requieren --limit para acotar costo y volumen.")
    api_key, base_url, model = provider_settings(args.provider)
    deepseek_fallback = None
    nim_fallback = None
    deepseek_fallback_suppressed = (
        os.environ.get("NIM_DEEPSEEK_FALLBACK", "1").strip().lower()
        in {"0", "false", "no"}
    )
    if (
        args.provider == "nim"
        and not deepseek_fallback_suppressed
        and os.environ.get("DEEPSEEK_API_KEY", "").strip()
    ):
        deepseek_fallback = provider_settings("deepseek")
    if (
        args.provider == "deepseek"
        and os.environ.get("NVIDIA_NIM_API_KEY", "").strip()
    ):
        nim_fallback = provider_settings("nim")
    dataset_root = Path(os.environ.get("DATASET_ROOT", "/app/dataset")).resolve()
    database = dataset_root / "metadata.sqlite"
    plans = []
    skipped_remote_format = 0
    for source_id, source in selected.items():
        source_root = ROOT / "datos-crudos" / source["path"]
        items, counts = scan_source(source_root, source)
        if "missing_directory" in counts:
            print(f"{source_id}: se omite; falta {counts['missing_directory']}")
            continue
        if source.get("benchmark_only"):
            print(f"{source_id}: omitida; benchmark_only no se mezcla con fotos de prendas.")
            continue
        if not source.get("allow_import", False):
            print(f"{source_id}: bloqueada hasta verificar identidad/licencia de la fuente.")
            continue
        if not items:
            print(
                f"{source_id}: imágenes={counts['images']}, mapeadas=0; "
                "no se encontraron clases con mapeo aprobado."
            )
            continue
        if args.provider != "none":
            supported_items = []
            for item in items:
                if item["path"].suffix.lower() not in REMOTE_IMAGE_EXTENSIONS:
                    skipped_remote_format += 1
                    continue
                supported_items.append(item)
            items = supported_items
        plans.extend((source_id, source, item) for item in items)

    if args.execute and plans:
        ensure_database(database)
    plans, pre_skipped_duplicates, pre_skipped_analyzed, recovered_cached = (
        filter_duplicate_plans(plans, database, args.provider, model, args.limit)
    )
    print(
        f"Imágenes nuevas para analizar: {len(plans) - recovered_cached}; "
        f"análisis aceptados pendientes de importar={recovered_cached}; "
        f"proveedor={args.provider}; "
        f"formatos no admitidos omitidos={skipped_remote_format}; "
        f"ya analizadas omitidas={pre_skipped_analyzed}; "
        f"duplicadas omitidas antes de IA={pre_skipped_duplicates}."
    )
    if not args.execute:
        print("Ensayo solamente. Añade --execute para copiar imágenes y escribir SQLite.")
        return 0
    if not plans:
        if pre_skipped_analyzed and not pre_skipped_duplicates:
            print(
                "Todas las imágenes elegibles ya tienen un análisis vigente para este "
                "proveedor y configuración."
            )
        elif pre_skipped_duplicates:
            print(
                "Todas las imágenes elegibles ya estaban importadas o analizadas; "
                "se omitieron antes de llamar a la IA."
            )
        else:
            print("No hay imágenes elegibles. Revisa auditoría, carpetas fuente y dudas.md.")
        return 0

    imported = 0
    skipped = pre_skipped_duplicates
    rejected = 0
    cache_hits = 0
    invalid_annotations = 0
    timed_out_images = 0
    stopped = False
    unavailable_nim_models: set[str] = set()
    with sqlite3.connect(database, timeout=30) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        colors = get_catalog(connection, "color")
        styles = get_catalog(connection, "estilo")
        seasons = get_catalog(connection, "temporada")
        prompt_instructions = get_setting(
            connection, "prompt_instructions", DEFAULT_PROMPT_INSTRUCTIONS
        )
        for source_id, source, item in plans:
            if CANCEL_REQUESTED.is_set():
                stopped = True
                print("Detención solicitada; no se enviarán más imágenes.")
                break
            exists = connection.execute(
                "SELECT 1 FROM prenda_imagen WHERE sha256 = ? LIMIT 1",
                (item["digest"],),
            ).fetchone()
            if exists:
                skipped += 1
                continue

            annotation = None
            fingerprint = None
            result_provider = args.provider
            result_model = model
            if args.provider != "none":
                fingerprint = analysis_fingerprint(
                    item["digest"],
                    item["category"],
                    args.provider,
                    model,
                    build_annotation_prompt(
                        prompt_instructions,
                        item["category"],
                        colors,
                        styles,
                        args.provider,
                        seasons,
                    ),
                )
                annotation = get_cached_analysis(connection, fingerprint)
                if annotation is not None:
                    cache_hits += 1
                else:
                    try:
                        (
                            annotation,
                            result_provider,
                            result_model,
                            exhausted_timeouts,
                        ) = annotate_with_provider_fallback(
                            item["path"],
                            item["category"],
                            args.provider,
                            api_key,
                            base_url,
                            model,
                            colors,
                            styles,
                            prompt_instructions,
                            seasons,
                            nim_settings=nim_fallback,
                            unavailable_nim_models=unavailable_nim_models,
                        )
                        timed_out_images += exhausted_timeouts
                        if annotation is None:
                            continue
                    except ProcessingCancelled:
                        stopped = True
                        print("Detención solicitada; no se enviarán más imágenes.")
                        break
                    except ValueError as error:
                        invalid_annotations += 1
                        print(
                            f"Respuesta inválida de IA; imagen omitida sin guardar "
                            f"análisis ({source_id}/{item['label']}): "
                            f"{item['relative_path']} — {error}"
                        )
                        continue
                    if result_provider == "nim" and args.provider == "nim":
                        model = result_model
                    result_prompt = build_annotation_prompt(
                        prompt_instructions,
                        item["category"],
                        colors,
                        styles,
                        result_provider,
                        seasons,
                    )
                    fingerprint = analysis_fingerprint(
                        item["digest"],
                        item["category"],
                        result_provider,
                        result_model,
                        result_prompt,
                    )
                    save_analysis(
                        connection,
                        fingerprint,
                        item,
                        result_provider,
                        result_model,
                        annotation,
                        source_id,
                    )
                    connection.commit()
                merge_annotation_catalogs(connection, annotation)
                styles = get_catalog(connection, "estilo")
                seasons = get_catalog(connection, "temporada")
                if args.provider == "nim" and not annotation["apta"]:
                    if deepseek_fallback is None:
                        if deepseek_fallback_suppressed:
                            print(
                                "La segunda evaluación se deja al lote DeepSeek que ya "
                                "está ejecutándose en paralelo."
                            )
                        else:
                            print(
                                "Descarte de NIM sin segunda evaluación: DeepSeek no está "
                                "configurado (falta DEEPSEEK_API_KEY)."
                            )
                    else:
                        deepseek_key, deepseek_url, deepseek_model = deepseek_fallback
                        deepseek_prompt = build_annotation_prompt(
                            prompt_instructions,
                            item["category"],
                            colors,
                            styles,
                            "deepseek",
                            seasons,
                        )
                        deepseek_fingerprint = analysis_fingerprint(
                            item["digest"],
                            item["category"],
                            "deepseek",
                            deepseek_model,
                            deepseek_prompt,
                        )
                        deepseek_annotation = get_cached_analysis(
                            connection, deepseek_fingerprint
                        )
                        if deepseek_annotation is not None:
                            cache_hits += 1
                        else:
                            try:
                                deepseek_annotation = annotate_image(
                                    item["path"],
                                    item["category"],
                                    "deepseek",
                                    deepseek_key,
                                    deepseek_url,
                                    deepseek_model,
                                    colors,
                                    styles,
                                    prompt_instructions,
                                    seasons=seasons,
                                )
                            except ProcessingCancelled:
                                stopped = True
                                print(
                                    "Detención solicitada durante la segunda evaluación "
                                    "de DeepSeek."
                                )
                                break
                            except (AnnotationTimeoutError, ValueError) as error:
                                invalid_annotations += isinstance(error, ValueError)
                                print(
                                    "DeepSeek no pudo completar la segunda evaluación; "
                                    f"se conserva el descarte de NIM para "
                                    f"{item['relative_path']}: {error}"
                                )
                                deepseek_annotation = None
                            if deepseek_annotation is not None:
                                save_analysis(
                                    connection,
                                    deepseek_fingerprint,
                                    item,
                                    "deepseek",
                                    deepseek_model,
                                    deepseek_annotation,
                                    source_id,
                                )
                                connection.commit()
                        if deepseek_annotation is not None:
                            merge_annotation_catalogs(connection, deepseek_annotation)
                            styles = get_catalog(connection, "estilo")
                            seasons = get_catalog(connection, "temporada")
                            annotation = deepseek_annotation
                            fingerprint = deepseek_fingerprint
                            result_provider = "deepseek"
                            result_model = deepseek_model
                            print(
                                f"Segunda evaluación de DeepSeek completada para "
                                f"{item['relative_path']}: "
                                f"{'aceptada' if annotation['apta'] else 'descartada'}."
                            )
                if not annotation["apta"]:
                    rejected += 1
                    print(
                        f"Descartada por {result_provider} ({source_id}/{item['label']}): "
                        f"{item['relative_path']} — {annotation['motivo_descarte']}"
                    )
                    continue

            created_files = []
            try:
                if import_one(
                    connection,
                    item,
                    source_id,
                    source,
                    dataset_root,
                    annotation,
                    result_provider,
                    result_model,
                    created_files,
                ):
                    connection.commit()
                    imported += 1
                else:
                    connection.rollback()
                    skipped += 1
            except (FileNotFoundError, FileExistsError, OSError, RuntimeError, ValueError, sqlite3.Error):
                connection.rollback()
                for path in created_files:
                    path.unlink(missing_ok=True)
                    try:
                        path.parent.rmdir()
                    except OSError:
                        pass
                raise
            if CANCEL_REQUESTED.is_set():
                stopped = True
                print("Detención solicitada; lote detenido tras completar la imagen actual.")
                break

    print(
        f"Importadas: {imported}; duplicadas omitidas: {skipped}; "
        f"ya analizadas omitidas: {pre_skipped_analyzed}; "
        f"descartadas por IA: {rejected}; análisis reutilizados: {cache_hits}; "
        f"respuestas inválidas omitidas: {invalid_annotations}; "
        f"timeouts agotados omitidos: {timed_out_images}; "
        f"detenido={str(stopped or CANCEL_REQUESTED.is_set()).lower()}; "
        "estado_revision=pendiente."
    )
    return 0


def main() -> int:
    CANCEL_REQUESTED.clear()
    install_cancellation_handler()
    args = parse_args()
    sources = load_sources()
    selected = select_sources(sources, args.source)
    if args.command == "audit":
        return command_audit(sources, selected)
    return command_ingest(args, selected)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (FileNotFoundError, FileExistsError, OSError, RuntimeError, ValueError, sqlite3.Error) as error:
        print(f"Error de curación de datos: {error}", file=sys.stderr)
        raise SystemExit(1) from error
