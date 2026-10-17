#!/usr/bin/env python3
import json
import os
import re
import sqlite3
import signal
import subprocess
import sys
import tempfile
import threading
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

import app


ROOT = Path(__file__).resolve().parent
HTML_FILE = ROOT / "dashboard.html"
ENV_FILE = ROOT / ".env"
DATASET_ROOT = Path(os.environ.get("DATASET_ROOT", "/app/dataset")).resolve()
DATABASE = DATASET_ROOT / "metadata.sqlite"
PORT = int(os.environ.get("DASHBOARD_PORT", "8787"))
HOST = os.environ.get("DASHBOARD_HOST", "127.0.0.1")
TARGET_COUNT = 5000
MAX_BATCH_SIZE = 5000
PROVIDERS = {
    "openai": "OPENAI_API_KEY",
    "nim": "NVIDIA_NIM_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
}
JOB_LOCK = threading.Lock()
JOB_PROCESSES: dict[str, subprocess.Popen] = {}
JOB_STATES: dict[str, dict] = {}


def _empty_job(provider: str) -> dict:
    return {
        "status": "idle",
        "source": None,
        "provider": provider,
        "limit": None,
        "started_at": None,
        "finished_at": None,
        "exit_code": None,
        "cancellation_requested": False,
        "message": "Todavía no se ha iniciado un procesamiento.",
        "logs": [],
    }


def get_job_status(provider: str | None = None) -> dict:
    with JOB_LOCK:
        if provider:
            state = JOB_STATES.get(provider, _empty_job(provider))
            return {**state, "logs": list(state["logs"])}
        jobs = []
        for name in ("nim", "deepseek", "none"):
            state = JOB_STATES.get(name, _empty_job(name))
            jobs.append({**state, "logs": list(state["logs"])})
        return {"jobs": jobs}


def validate_ingest_request(payload: dict) -> tuple[str, str, int, dict[str, str]]:
    source_id = payload.get("source")
    provider = payload.get("provider")
    limit = payload.get("limit")
    if not isinstance(source_id, str):
        raise ValueError("Selecciona una fuente de datos válida.")
    sources = app.load_sources()
    source = sources.get(source_id)
    if not source or not source.get("allow_import") or source.get("benchmark_only"):
        raise ValueError("La fuente seleccionada no está habilitada para importar.")
    if provider not in {"none", "nim", "deepseek"}:
        raise ValueError("Selecciona Sin IA, NVIDIA NIM o DeepSeek.")
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= MAX_BATCH_SIZE:
        raise ValueError(f"El lote debe ser un entero entre 1 y {MAX_BATCH_SIZE}.")
    if payload.get("confirm_write") is not True:
        raise ValueError("Confirma que autorizas escribir en el dataset y la base SQLite.")
    if provider != "none" and payload.get("confirm_remote") is not True:
        raise ValueError("Confirma explícitamente el envío de imágenes al proveedor remoto.")

    _, env_values = read_env_file()
    if provider != "none" and not env_values.get(PROVIDERS[provider], "").strip():
        raise ValueError(f"No hay una API key configurada para {provider}.")
    return source_id, provider, limit, env_values


def _append_job_log(provider: str, line: str, secrets: list[str]) -> None:
    for secret in secrets:
        if secret:
            line = line.replace(secret, "[REDACTED]")
    line = line.rstrip()[:2000]
    if not line:
        return
    with JOB_LOCK:
        state = JOB_STATES[provider]
        state["logs"].append(line)
        state["logs"] = state["logs"][-80:]


def _run_ingest(
    provider: str,
    command: list[str],
    environment: dict[str, str],
    secrets: list[str],
) -> None:
    process = None
    try:
        process = subprocess.Popen(
            command,
            cwd=ROOT,
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
        with JOB_LOCK:
            JOB_PROCESSES[provider] = process
            cancel_now = JOB_STATES[provider]["cancellation_requested"]
            if cancel_now:
                try:
                    process.send_signal(signal.SIGTERM)
                except ProcessLookupError:
                    pass
        with process:
            if process.stdout is None:
                raise RuntimeError("No se pudo abrir la salida del proceso de curación.")
            for line in process.stdout:
                _append_job_log(provider, line, secrets)
            exit_code = process.wait()
        finished = datetime.now().astimezone().isoformat(timespec="seconds")
        with JOB_LOCK:
            state = JOB_STATES[provider]
            cancelled = state["cancellation_requested"]
            state["status"] = (
                "cancelled" if cancelled else "completed" if exit_code == 0 else "failed"
            )
            state["finished_at"] = finished
            state["exit_code"] = exit_code
            if cancelled:
                state["message"] = "Procesamiento detenido de forma segura."
            elif exit_code == 0:
                state["message"] = "Procesamiento finalizado correctamente."
            else:
                state["message"] = (
                    f"El procesamiento terminó con error (código {exit_code}). Revisa el registro."
                )
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        with JOB_LOCK:
            state = JOB_STATES[provider]
            state["status"] = "failed"
            state["finished_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
            state["message"] = f"No se pudo ejecutar el procesamiento: {error}"
    finally:
        with JOB_LOCK:
            if JOB_PROCESSES.get(provider) is process:
                JOB_PROCESSES.pop(provider, None)


def stop_ingest(provider: str) -> dict:
    with JOB_LOCK:
        state = JOB_STATES.get(provider)
        if state is None or state["status"] != "running":
            raise ValueError(f"No hay un procesamiento activo de {provider} para detener.")
        if state["cancellation_requested"]:
            return {**state, "logs": list(state["logs"])}

        state["cancellation_requested"] = True
        state["message"] = (
            "Detención solicitada; se espera a que termine la petición de IA actual."
        )
        process = JOB_PROCESSES.get(provider)
        if process is not None:
            try:
                process.send_signal(signal.SIGTERM)
            except ProcessLookupError:
                pass
            except OSError as error:
                state["cancellation_requested"] = False
                state["message"] = f"No se pudo solicitar la detención: {error}"
                raise RuntimeError(state["message"]) from error
        return {**state, "logs": list(state["logs"])}


def start_ingest(payload: dict) -> dict:
    selected_providers = payload.get("providers")
    if selected_providers is None:
        selected_providers = [payload.get("provider")]
    if (
        not isinstance(selected_providers, list)
        or not selected_providers
        or len(selected_providers) > 2
        or any(not isinstance(provider, str) for provider in selected_providers)
        or len(set(selected_providers)) != len(selected_providers)
    ):
        raise ValueError("Selecciona uno o dos proveedores distintos.")
    if any(provider not in {"none", "nim", "deepseek"} for provider in selected_providers):
        raise ValueError("Proveedor inválido; elige Sin IA, NVIDIA NIM o DeepSeek.")
    if "none" in selected_providers and len(selected_providers) != 1:
        raise ValueError("El modo local no se puede combinar con proveedores remotos.")

    validated = []
    for provider in selected_providers:
        provider_payload = {**payload, "provider": provider}
        validated.append(validate_ingest_request(provider_payload))
    source_id, _, limit, env_values = validated[0]

    with JOB_LOCK:
        started = datetime.now().astimezone().isoformat(timespec="seconds")
        active = [
            provider for provider in selected_providers
            if JOB_STATES.get(provider, {}).get("status") == "running"
        ]
        if active:
            raise ValueError(
                f"Ya hay un procesamiento activo para: {', '.join(active)}."
            )
        for provider in selected_providers:
            JOB_STATES[provider] = {
                **_empty_job(provider),
                "status": "running",
                "source": source_id,
                "limit": limit,
                "started_at": started,
                "message": "Procesamiento iniciado; esperando actividad.",
            }

    environment = os.environ.copy()
    environment.update(env_values)
    environment["DATASET_ROOT"] = str(DATASET_ROOT)
    environment["PYTHONUNBUFFERED"] = "1"
    secrets = [env_values.get(name, "") for name in PROVIDERS.values()]
    for provider in selected_providers:
        command = [
            sys.executable,
            str(ROOT / "app.py"),
            "ingest",
            "--source", source_id,
            "--provider", provider,
            "--limit", str(limit),
            "--execute",
        ]
        if provider != "none":
            command.append("--allow-remote")
        worker = threading.Thread(
            target=_run_ingest,
            args=(provider, command, environment, secrets),
            name=f"dashboard-ingest-{provider}",
            daemon=True,
        )
        try:
            worker.start()
        except RuntimeError as error:
            with JOB_LOCK:
                state = JOB_STATES[provider]
                state["status"] = "failed"
                state["finished_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
                state["message"] = f"No se pudo iniciar el proceso de curación: {error}"
    return {"jobs": [get_job_status(provider) for provider in selected_providers]}


def connect_database() -> sqlite3.Connection:
    if not DATABASE.is_file():
        raise FileNotFoundError(f"No existe la base SQLite: {DATABASE}")
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


def read_env_file() -> tuple[list[str], dict[str, str]]:
    if not ENV_FILE.is_file():
        raise FileNotFoundError(f"No existe el archivo de configuración {ENV_FILE}.")
    lines = ENV_FILE.read_text(encoding="utf-8").splitlines()
    values = {}
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return lines, values


def write_env_file(updates: dict[str, str]) -> None:
    lines, _ = read_env_file()
    remaining = dict(updates)
    output = []
    for line in lines:
        if not line.strip() or line.lstrip().startswith("#") or "=" not in line:
            output.append(line)
            continue
        key = line.split("=", 1)[0].strip()
        if key in remaining:
            output.append(f"{key}={remaining.pop(key)}")
        else:
            output.append(line)
    output.extend(f"{key}={value}" for key, value in remaining.items())

    fd, temp_path = tempfile.mkstemp(prefix=".dashboard-env.", text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write("\n".join(output) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temp_path, 0o600)
        contents = Path(temp_path).read_text(encoding="utf-8")
        with ENV_FILE.open("w", encoding="utf-8") as stream:
            stream.write(contents)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(ENV_FILE, 0o600)
    except OSError:
        Path(temp_path).unlink(missing_ok=True)
        raise
    Path(temp_path).unlink(missing_ok=True)


def parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def estimate_completion(connection: sqlite3.Connection, current_count: int) -> dict:
    remaining = max(TARGET_COUNT - current_count, 0)
    if remaining == 0:
        return {"remaining": 0, "seconds": 0, "rate_per_hour": None, "message": "Meta de 5.000 prendas alcanzada."}

    rows = connection.execute(
        """
        SELECT fecha_analisis, estado
        FROM analisis_imagen
        ORDER BY fecha_analisis DESC
        LIMIT 100
        """
    ).fetchall()
    dated = [(parse_timestamp(row["fecha_analisis"]), row["estado"]) for row in rows]
    dated = [(moment, state) for moment, state in dated if moment is not None]
    if len(dated) < 2:
        return {
            "remaining": remaining,
            "seconds": None,
            "rate_per_hour": None,
            "message": "Aún no hay suficientes análisis con tiempo medible para estimar.",
        }

    oldest = min(moment for moment, _ in dated)
    newest = max(moment for moment, _ in dated)
    elapsed = (newest - oldest).total_seconds()
    accepted = sum(state == "aceptada" for _, state in dated)
    if elapsed <= 0 or accepted == 0:
        return {
            "remaining": remaining,
            "seconds": None,
            "rate_per_hour": None,
            "message": "Aún no hay una tasa de importación medible.",
        }

    accepted_per_second = accepted / elapsed
    seconds = int(remaining / accepted_per_second)
    return {
        "remaining": remaining,
        "seconds": seconds,
        "rate_per_hour": round(accepted_per_second * 3600, 2),
        "message": "Estimación basada en hasta los últimos 100 análisis de IA.",
    }


def get_overview() -> dict:
    with connect_database() as connection:
        counts = {category: 0 for category in app.CATEGORY_PATHS}
        rows = connection.execute(
            """
            SELECT v.valor AS categoria, COUNT(DISTINCT p.id_prenda) AS cantidad
            FROM prenda p
            JOIN valor_propiedad_prenda v ON v.id_prenda = p.id_prenda
            JOIN catalogo_propiedad c ON c.id_propiedad = v.id_propiedad
            WHERE c.codigo = 'tipo_prenda'
            GROUP BY v.valor
            """
        ).fetchall()
        for row in rows:
            if row["categoria"] in counts:
                counts[row["categoria"]] = row["cantidad"]
        total = connection.execute("SELECT COUNT(*) FROM prenda").fetchone()[0]

        recent_rows = connection.execute(
            """
            SELECT p.id_prenda, p.codigo, p.ruta_categoria, p.split, p.estado_revision,
                   p.fecha_creacion, i.ruta_relativa, i.fuente, i.etiqueta_fuente,
                   d.texto, d.proveedor, d.modelo, d.atributos_sugeridos
            FROM prenda p
            JOIN prenda_imagen i ON i.id_prenda = p.id_prenda
            LEFT JOIN descripcion_prenda d ON d.id_descripcion = (
                SELECT MAX(d2.id_descripcion)
                FROM descripcion_prenda d2
                WHERE d2.id_prenda = p.id_prenda
            )
            ORDER BY p.id_prenda DESC, i.id_imagen DESC
            LIMIT 5
            """
        ).fetchall()
        recent = []
        ids = [row["id_prenda"] for row in recent_rows]
        properties: dict[int, list[dict]] = {id_prenda: [] for id_prenda in ids}
        if ids:
            placeholders = ",".join("?" for _ in ids)
            property_rows = connection.execute(
                f"""
                SELECT v.id_prenda, c.codigo, v.valor
                FROM valor_propiedad_prenda v
                JOIN catalogo_propiedad c ON c.id_propiedad = v.id_propiedad
                WHERE v.id_prenda IN ({placeholders})
                ORDER BY c.codigo, v.valor
                """,
                ids,
            ).fetchall()
            for row in property_rows:
                properties[row["id_prenda"]].append({
                    "propiedad": row["codigo"],
                    "valor": row["valor"],
                })

        for row in recent_rows:
            try:
                suggested = json.loads(row["atributos_sugeridos"] or "{}")
            except json.JSONDecodeError:
                suggested = {}
            recent.append({
                "id": row["id_prenda"],
                "codigo": row["codigo"],
                "ruta_categoria": row["ruta_categoria"],
                "split": row["split"],
                "estado_revision": row["estado_revision"],
                "fecha": row["fecha_creacion"],
                "ruta_relativa": row["ruta_relativa"],
                "imagen_url": f"/api/image/{row['id_prenda']}",
                "fuente": row["fuente"],
                "etiqueta_fuente": row["etiqueta_fuente"],
                "descripcion": row["texto"],
                "proveedor": row["proveedor"],
                "modelo": row["modelo"],
                "propiedades": properties[row["id_prenda"]],
                "sugerencias_ia": suggested,
            })

        colors = app.get_catalog(connection, "color")
        styles = app.get_catalog(connection, "estilo")
        instructions = app.get_setting(
            connection, "prompt_instructions", app.DEFAULT_PROMPT_INSTRUCTIONS
        )
        providers = {}
        try:
            _, env = read_env_file()
            providers = {
                name: bool(env.get(key, "").strip())
                for name, key in PROVIDERS.items()
            }
            selected_provider = env.get("ANNOTATION_PROVIDER", "none")
        except FileNotFoundError:
            providers = {name: False for name in PROVIDERS}
            selected_provider = "none"

        prompt_preview = app.build_annotation_prompt(
            instructions, "camisa", colors, styles, selected_provider
        )
        estimate = estimate_completion(connection, total)
        analysis_count = connection.execute(
            "SELECT COUNT(*) FROM analisis_imagen"
        ).fetchone()[0]

    return {
        "total": total,
        "target": TARGET_COUNT,
        "counts_by_type": counts,
        "recent_images": recent,
        "estimate": estimate,
        "analysis_count": analysis_count,
        "prompt_instructions": instructions,
        "prompt_preview": prompt_preview,
        "properties": {"color": colors, "estilo": styles},
        "providers": providers,
        "selected_provider": selected_provider,
        "sources": [
            {"id": source_id, "label": source_id}
            for source_id, source in app.load_sources().items()
            if source.get("allow_import") and not source.get("benchmark_only")
        ],
    }


class DashboardHandler(BaseHTTPRequestHandler):
    server_version = "DatasetDashboard/1.0"

    def log_message(self, format, *args):
        print(f"dashboard {self.client_address[0]} {format % args}")

    def _send_json(self, status: int, payload: dict) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(data)

    def _host_allowed(self) -> bool:
        host = self.headers.get("Host", "")
        parsed = urlsplit(f"//{host}")
        return parsed.hostname in {"127.0.0.1", "localhost"}

    def _origin_allowed(self) -> bool:
        origin = self.headers.get("Origin", "")
        if not origin:
            return False
        parsed = urlsplit(origin)
        return parsed.scheme == "http" and parsed.netloc == self.headers.get("Host", "")

    def _read_json(self) -> dict:
        if self.headers.get_content_type() != "application/json":
            raise ValueError("El Content-Type debe ser application/json.")
        length = int(self.headers.get("Content-Length", "0"))
        if length < 1 or length > 1_000_000:
            raise ValueError("El cuerpo de la solicitud debe medir entre 1 byte y 1 MB.")
        payload = json.loads(self.rfile.read(length))
        if not isinstance(payload, dict):
            raise ValueError("El cuerpo JSON debe ser un objeto.")
        return payload

    def do_GET(self):
        if not self._host_allowed():
            self._send_json(403, {"error": "Host no permitido."})
            return
        path = urlsplit(self.path).path
        try:
            if path == "/":
                body = HTML_FILE.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Security-Policy", "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'")
                self.end_headers()
                self.wfile.write(body)
                return
            if path == "/api/overview":
                self._send_json(200, get_overview())
                return
            if path == "/api/jobs":
                self._send_json(200, get_job_status())
                return
            if path == "/api/job":
                self._send_json(200, get_job_status("nim"))
                return
            match = re.fullmatch(r"/api/image/([0-9]+)", path)
            if match:
                self._send_image(int(match.group(1)))
                return
            self._send_json(404, {"error": "Ruta no encontrada."})
        except (OSError, sqlite3.Error, ValueError, RuntimeError) as error:
            self._send_json(500, {"error": str(error)})

    def _send_image(self, garment_id: int) -> None:
        with connect_database() as connection:
            row = connection.execute(
                """
                SELECT ruta_relativa FROM prenda_imagen
                WHERE id_prenda = ?
                ORDER BY id_imagen LIMIT 1
                """,
                (garment_id,),
            ).fetchone()
        if row is None:
            self._send_json(404, {"error": "Imagen no encontrada."})
            return
        image_path = (DATASET_ROOT / row["ruta_relativa"]).resolve()
        if not image_path.is_relative_to(DATASET_ROOT) or not image_path.is_file():
            self._send_json(404, {"error": "Archivo de imagen no encontrado."})
            return
        with open(image_path, "rb") as image:
            body = image.read()
        with app.Image.open(image_path) as source:
            mime_type = app.IMAGE_MIME_TYPES.get(source.format)
        if mime_type is None:
            self._send_json(415, {"error": "Formato de imagen no compatible."})
            return
        self.send_response(200)
        self.send_header("Content-Type", mime_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "private, max-age=60")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if not self._host_allowed() or not self._origin_allowed():
            self._send_json(403, {"error": "Origen local no permitido."})
            return
        path = urlsplit(self.path).path
        try:
            payload = self._read_json()
            if path == "/api/prompt":
                self._save_prompt(payload)
                self._send_json(200, {"saved": True})
            elif path == "/api/properties":
                self._save_properties(payload)
                self._send_json(200, {"saved": True})
            elif path == "/api/credentials":
                self._save_credentials(payload)
                self._send_json(200, {"saved": True})
            elif path == "/api/ingest":
                self._send_json(202, start_ingest(payload))
            elif path == "/api/stop":
                provider = payload.get("provider")
                if not isinstance(provider, str):
                    raise ValueError("Indica el proveedor que quieres detener.")
                self._send_json(202, stop_ingest(provider))
            else:
                self._send_json(404, {"error": "Ruta no encontrada."})
        except (OSError, sqlite3.Error, ValueError, KeyError) as error:
            self._send_json(400, {"error": str(error)})
        except RuntimeError as error:
            self._send_json(500, {"error": str(error)})

    def _save_prompt(self, payload: dict) -> None:
        instructions = payload.get("instructions")
        if not isinstance(instructions, str) or not instructions.strip():
            raise ValueError("El prompt no puede estar vacío.")
        if len(instructions) > 20_000:
            raise ValueError("El prompt no puede superar 20.000 caracteres.")
        with connect_database() as connection:
            connection.execute(
                """
                INSERT INTO pipeline_config (clave, valor)
                VALUES ('prompt_instructions', ?)
                ON CONFLICT(clave) DO UPDATE SET
                    valor = excluded.valor, actualizado_en = CURRENT_TIMESTAMP
                """,
                (instructions.strip(),),
            )
            connection.commit()

    def _save_properties(self, payload: dict) -> None:
        updates = {}
        for code in ("color", "estilo"):
            values = payload.get(code)
            if not isinstance(values, list) or not values or len(values) > 50:
                raise ValueError(f"{code} debe incluir entre 1 y 50 valores.")
            cleaned = []
            for value in values:
                if not isinstance(value, str) or not value.strip() or len(value.strip()) > 40:
                    raise ValueError(f"Cada valor de {code} debe contener entre 1 y 40 caracteres.")
                normalized = value.strip()
                if any(char in normalized for char in "\r\n\t"):
                    raise ValueError(f"Valor inválido para {code}.")
                if normalized not in cleaned:
                    cleaned.append(normalized)
            updates[code] = cleaned
        with connect_database() as connection:
            for code, values in updates.items():
                cursor = connection.execute(
                    """
                    UPDATE catalogo_propiedad SET valores_permitidos = ?
                    WHERE codigo = ? AND activo = 1
                    """,
                    (json.dumps(values, ensure_ascii=False), code),
                )
                if cursor.rowcount != 1:
                    raise ValueError(f"No existe la propiedad activa {code}.")
            connection.commit()

    def _save_credentials(self, payload: dict) -> None:
        provider = payload.get("provider")
        if provider not in {*PROVIDERS, "none"}:
            raise ValueError("Proveedor seleccionado inválido.")
        updates = {"ANNOTATION_PROVIDER": provider}
        for field in PROVIDERS.values():
            value = payload.get(field, "")
            if not isinstance(value, str):
                raise ValueError(f"Valor inválido para {field}.")
            if not value:
                continue
            if len(value) > 512 or not re.fullmatch(r"[A-Za-z0-9._-]+", value):
                raise ValueError(f"Formato de clave inválido para {field}.")
            updates[field] = value
        write_env_file(updates)


def main() -> None:
    app.ensure_database(DATABASE)
    server = ThreadingHTTPServer((HOST, PORT), DashboardHandler)
    print(f"Panel disponible en http://127.0.0.1:{PORT}")
    server.serve_forever()


if __name__ == "__main__":
    main()
