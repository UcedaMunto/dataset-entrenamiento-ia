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
CANCEL_REQUESTED = threading.Event()
ANALYSIS_PROMPT_VERSION = "3"
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
            "https://integrate.api.nvidia.com/v1", "meta/llama-3.2-11b-vision-instruct"),
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
    identity = json.dumps(
        [digest, category, provider, model, ANALYSIS_PROMPT_VERSION, prompt],
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
) -> str:
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
        "Instrucciones:\n"
        f"{instructions.strip()}\n\n"
        "Devuelve únicamente un objeto JSON completo, sin Markdown ni texto adicional. "
        "Ejemplo de forma (sustituye los valores por observaciones reales y valores de los "
        "vocabularios): "
        '{"apta":true,"motivo_descarte":"","descripcion":"Camisa azul lisa.",'
        '"colores":["azul"],"estilos":["casual"]}. '
        "Usa estas claves: apta (booleano), motivo_descarte (texto), descripcion "
        f"(una frase de máximo {max_description_words} palabras), colores "
        f"(lista de máximo {max_attribute_values}) y estilos "
        f"(lista de máximo {max_attribute_values}). "
        f"{reason_instruction}Mantén "
        "motivo_descarte como cadena vacía cuando la imagen sea apta; nunca uses null. "
        "Mantén la respuesta muy concisa. Colores y estilos solo pueden usar los valores de los "
        "vocabularios TOON. Si apta es false, incluye un motivo breve."
    )


def build_annotation_prompt(
    instructions: str,
    known_type: str,
    colors: list[str],
    styles: list[str],
    provider: str,
) -> str:
    if provider == "nim":
        return build_prompt(
            instructions,
            known_type,
            colors,
            styles,
            max_description_words=8,
            max_attribute_values=2,
            max_reason_words=8,
        )
    return build_prompt(instructions, known_type, colors, styles)


def save_analysis(
    connection: sqlite3.Connection,
    fingerprint: str,
    item: dict,
    provider: str,
    model: str,
    annotation: dict,
) -> None:
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
            ANALYSIS_PROMPT_VERSION,
            "aceptada" if annotation["apta"] else "descartada",
            json.dumps(annotation, ensure_ascii=False),
        ),
    )


def parse_model_json(content: str) -> dict:
    text = content.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.IGNORECASE)
    try:
        result = json.loads(text)
    except json.JSONDecodeError as error:
        raise ValueError(f"El proveedor no devolvió JSON válido: {error}") from error
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
) -> dict:
    prompt = build_annotation_prompt(
        instructions, known_type, colors, styles, provider
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
        }
    description = result.get("descripcion")
    if not isinstance(description, str) or not description.strip():
        raise ValueError("El proveedor no devolvió una descripcion no vacía.")
    for field, vocabulary in (("colores", colors), ("estilos", styles)):
        values = result.get(field, [])
        if not isinstance(values, list) or any(value not in vocabulary for value in values):
            raise ValueError(f"El campo {field} contiene valores fuera del catálogo.")
        result[field] = sorted(set(values))
        if provider == "nim":
            result[field] = result[field][:2]
    return {
        "apta": True,
        "motivo_descarte": "",
        "descripcion": " ".join(description.split()[:8])
        if provider == "nim"
        else description.strip()[:1200],
        "colores": result["colores"],
        "estilos": result["estilos"],
    }


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
    category_path = CATEGORY_PATHS[item["category"]]
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
        (garment_id, type_property[0], item["category"]),
    )

    if annotation:
        attributes = {"colores": annotation["colores"], "estilos": annotation["estilos"]}
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
    plans: list[tuple[str, dict, dict]], database: Path
) -> tuple[list[tuple[str, dict, dict]], int]:
    imported_hashes = set()
    if database.is_file():
        with sqlite3.connect(database, timeout=30) as connection:
            imported_hashes = {
                row[0]
                for row in connection.execute(
                    "SELECT DISTINCT sha256 FROM prenda_imagen WHERE sha256 IS NOT NULL"
                )
            }

    seen_hashes = set(imported_hashes)
    unique_plans = []
    duplicates = 0
    for plan in plans:
        digest = plan[2]["digest"]
        if digest in seen_hashes:
            duplicates += 1
            continue
        seen_hashes.add(digest)
        unique_plans.append(plan)
    return unique_plans, duplicates


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
    plans, pre_skipped_duplicates = filter_duplicate_plans(plans, database)
    if args.limit is not None:
        plans = plans[:args.limit]
    print(
        f"Imágenes preparadas para procesar: {len(plans)}; proveedor={args.provider}; "
        f"formatos no admitidos omitidos={skipped_remote_format}; "
        f"duplicadas omitidas antes de IA={pre_skipped_duplicates}."
    )
    if not args.execute:
        print("Ensayo solamente. Añade --execute para copiar imágenes y escribir SQLite.")
        return 0
    if not plans:
        if pre_skipped_duplicates:
            print(
                "Todas las imágenes elegibles ya estaban importadas; "
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
    with sqlite3.connect(database, timeout=30) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        colors = get_catalog(connection, "color")
        styles = get_catalog(connection, "estilo")
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
                    ),
                )
                annotation = get_cached_analysis(connection, fingerprint)
                if annotation is not None:
                    cache_hits += 1
                else:
                    for attempt in range(2):
                        if CANCEL_REQUESTED.is_set():
                            stopped = True
                            break
                        try:
                            annotation = annotate_image(
                                item["path"],
                                item["category"],
                                args.provider,
                                api_key,
                                base_url,
                                model,
                                colors,
                                styles,
                                prompt_instructions,
                            )
                            break
                        except AnnotationTimeoutError as error:
                            if args.provider != "nim":
                                raise
                            if attempt == 0:
                                if CANCEL_REQUESTED.is_set():
                                    stopped = True
                                    break
                                delay = random.randint(
                                    NIM_TIMEOUT_RETRY_MIN_SECONDS,
                                    NIM_TIMEOUT_RETRY_MAX_SECONDS,
                                )
                                print(
                                    f"Timeout de NIM para {item['relative_path']}; "
                                    f"se reintentará la misma imagen en {delay} segundos."
                                )
                                if CANCEL_REQUESTED.wait(delay):
                                    stopped = True
                                    print(
                                        "Detención solicitada durante la espera; "
                                        "no se reintentará ni se enviarán más imágenes."
                                    )
                                    break
                            else:
                                timed_out_images += 1
                                print(
                                    f"Segundo timeout de NIM; imagen omitida y se continúa "
                                    f"con la siguiente ({source_id}/{item['label']}): "
                                    f"{item['relative_path']} — {error}"
                                )
                        except ProcessingCancelled:
                            stopped = True
                            break
                        except ValueError as error:
                            invalid_annotations += 1
                            print(
                                f"Respuesta inválida de IA; imagen omitida sin guardar "
                                f"análisis ({source_id}/{item['label']}): "
                                f"{item['relative_path']} — {error}"
                            )
                            break
                    if stopped:
                        print("Detención solicitada; no se enviarán más imágenes.")
                        break
                    if annotation is None:
                        continue
                    save_analysis(
                        connection, fingerprint, item, args.provider, model, annotation
                    )
                    connection.commit()
                if not annotation["apta"]:
                    rejected += 1
                    print(
                        f"Descartada por IA ({source_id}/{item['label']}): "
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
                    args.provider,
                    model,
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
