import json
import os
import sqlite3
import tempfile
import unittest
from email.message import Message
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

import dashboard


class DashboardTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.database = self.root / "metadata.sqlite"
        self.env = self.root / ".env"
        self.env.write_text(
            "ANNOTATION_PROVIDER=nim\n"
            "NVIDIA_NIM_API_KEY=do-not-return-this-secret\n"
            "DEEPSEEK_API_KEY=\n"
            "OPENAI_API_KEY=\n",
            encoding="utf-8",
        )
        schema_path = Path("/app/schema.sql")
        with sqlite3.connect(self.database) as connection:
            connection.executescript(schema_path.read_text(encoding="utf-8"))
        self.patches = [
            patch.object(dashboard, "DATABASE", self.database),
            patch.object(dashboard, "DATASET_ROOT", self.root),
            patch.object(dashboard, "ENV_FILE", self.env),
        ]
        for item in self.patches:
            item.start()
            self.addCleanup(item.stop)

    def tearDown(self):
        self.temp.cleanup()

    def test_overview_counts_types_and_does_not_return_keys(self):
        with sqlite3.connect(self.database) as connection:
            connection.execute(
                """
                INSERT INTO prenda
                    (codigo, ruta_categoria, split, estado_revision, apta_para_entrenamiento)
                VALUES ('CAMISA-1', 'superior/camisas', 'train', 'pendiente', 0)
                """
            )
            connection.execute(
                """
                INSERT INTO prenda_imagen
                    (id_prenda, ruta_relativa, fuente, etiqueta_fuente, permiso_uso, sha256)
                VALUES (1, 'superior/camisas/CAMISA-1/imagen.png', 'aig', 'Shirts', 'test', 'abc')
                """
            )
            connection.execute(
                "INSERT INTO valor_propiedad_prenda (id_prenda,id_propiedad,valor) "
                "SELECT 1,id_propiedad,'camisa' FROM catalogo_propiedad WHERE codigo='tipo_prenda'"
            )
            connection.execute(
                """
                INSERT INTO descripcion_prenda
                    (id_prenda, texto, atributos_sugeridos, proveedor, modelo)
                VALUES (1, 'Camisa azul.', '{"colores":["azul"],"estilos":[]}', 'nim', 'vision-test')
                """
            )
            connection.commit()

        data = dashboard.get_overview()
        self.assertEqual(data["total"], 1)
        self.assertEqual(data["counts_by_type"]["camisa"], 1)
        self.assertEqual(data["recent_images"][0]["proveedor"], "nim")
        self.assertEqual(data["recent_images"][0]["sugerencias_ia"]["colores"], ["azul"])
        self.assertTrue(data["providers"]["nim"])
        self.assertNotIn("do-not-return-this-secret", json.dumps(data))

    def test_prompt_and_property_updates_are_persisted(self):
        handler = object.__new__(dashboard.DashboardHandler)
        handler._save_prompt({"instructions": "Describe solo ropa visible."})
        handler._save_properties({"color": ["azul", "rojo"], "estilo": ["casual"]})
        with sqlite3.connect(self.database) as connection:
            prompt = connection.execute(
                "SELECT valor FROM pipeline_config WHERE clave='prompt_instructions'"
            ).fetchone()[0]
            colors = json.loads(connection.execute(
                "SELECT valores_permitidos FROM catalogo_propiedad WHERE codigo='color'"
            ).fetchone()[0])
        self.assertEqual(prompt, "Describe solo ropa visible.")
        self.assertEqual(colors, ["azul", "rojo"])

    def test_credentials_are_replaced_without_readback_or_dropping_existing_keys(self):
        handler = object.__new__(dashboard.DashboardHandler)
        handler._save_credentials({
            "provider": "deepseek",
            "DEEPSEEK_API_KEY": "new-secret-key-123",
            "NVIDIA_NIM_API_KEY": "",
            "OPENAI_API_KEY": "",
        })
        content = self.env.read_text(encoding="utf-8")
        self.assertIn("ANNOTATION_PROVIDER=deepseek", content)
        self.assertIn("DEEPSEEK_API_KEY=new-secret-key-123", content)
        self.assertIn("NVIDIA_NIM_API_KEY=do-not-return-this-secret", content)
        self.assertEqual(self.env.stat().st_mode & 0o777, 0o600)

    def test_estimate_requires_time_spread(self):
        with sqlite3.connect(self.database) as connection:
            connection.row_factory = sqlite3.Row
            connection.execute(
                """
                INSERT INTO analisis_imagen
                    (huella_analisis, sha256, categoria, proveedor, modelo,
                     version_prompt, estado, resultado_json, fecha_analisis)
                VALUES ('one','a','camisa','nim','m','1','aceptada','{}','2026-10-16 22:00:00')
                """
            )
            connection.execute(
                """
                INSERT INTO analisis_imagen
                    (huella_analisis, sha256, categoria, proveedor, modelo,
                     version_prompt, estado, resultado_json, fecha_analisis)
                VALUES ('two','b','camisa','nim','m','1','aceptada','{}','2026-10-16 22:00:00')
                """
            )
            estimate = dashboard.estimate_completion(connection, 1)
        self.assertIsNone(estimate["seconds"])

    def test_ingest_requires_write_and_remote_consents(self):
        with self.assertRaisesRegex(ValueError, "Confirma que autorizas escribir"):
            dashboard.validate_ingest_request({
                "source": "clothing-full",
                "provider": "none",
                "limit": 1,
            })
        with self.assertRaisesRegex(ValueError, "envío de imágenes"):
            dashboard.validate_ingest_request({
                "source": "clothing-full",
                "provider": "nim",
                "limit": 1,
                "confirm_write": True,
            })

        source_id, provider, limit, _ = dashboard.validate_ingest_request({
            "source": "clothing-full",
            "provider": "none",
            "limit": 1,
            "confirm_write": True,
        })
        self.assertEqual((source_id, provider, limit), ("clothing-full", "none", 1))

    def test_start_ingest_launches_bounded_command_without_secret_arguments(self):
        state = {
            "status": "idle",
            "source": None,
            "provider": None,
            "limit": None,
            "started_at": None,
            "finished_at": None,
            "exit_code": None,
            "cancellation_requested": False,
            "message": "",
            "logs": [],
        }
        worker = unittest.mock.Mock()
        request = {
            "source": "clothing-full",
            "provider": "nim",
            "limit": 3,
            "confirm_write": True,
            "confirm_remote": True,
        }
        with patch.object(dashboard, "JOB_STATE", state), patch.object(
            dashboard.threading, "Thread", return_value=worker
        ) as thread_factory:
            result = dashboard.start_ingest(request)

        command, environment, secrets = thread_factory.call_args.kwargs["args"]
        self.assertIn("--allow-remote", command)
        self.assertIn("--limit", command)
        self.assertIn("3", command)
        self.assertNotIn("do-not-return-this-secret", command)
        self.assertEqual(environment["NVIDIA_NIM_API_KEY"], "do-not-return-this-secret")
        self.assertIn("do-not-return-this-secret", secrets)
        self.assertEqual(result["status"], "running")
        worker.start.assert_called_once()

    def test_stop_ingest_sends_cooperative_signal_to_running_process(self):
        state = {
            "status": "running",
            "cancellation_requested": False,
            "message": "",
            "logs": [],
        }
        process = unittest.mock.Mock()
        process.pid = 42
        with patch.object(dashboard, "JOB_STATE", state), patch.object(
            dashboard, "JOB_PROCESS", process
        ):
            result = dashboard.stop_ingest()

        process.send_signal.assert_called_once_with(dashboard.signal.SIGTERM)
        self.assertTrue(result["cancellation_requested"])
        self.assertIn("Detención solicitada", result["message"])

    def test_stop_ingest_is_remembered_if_child_is_not_started_yet(self):
        state = {
            "status": "running",
            "cancellation_requested": False,
            "message": "",
            "logs": [],
        }
        with patch.object(dashboard, "JOB_STATE", state), patch.object(
            dashboard, "JOB_PROCESS", None
        ):
            result = dashboard.stop_ingest()
        self.assertTrue(result["cancellation_requested"])

    def test_stop_endpoint_calls_cooperative_stop(self):
        handler = object.__new__(dashboard.DashboardHandler)
        handler.headers = Message()
        handler.headers["Host"] = "127.0.0.1:8787"
        handler.headers["Origin"] = "http://127.0.0.1:8787"
        handler.headers["Content-Type"] = "application/json"
        handler.headers["Content-Length"] = "2"
        handler.rfile = BytesIO(b"{}")
        handler.path = "/api/stop"
        handler._send_json = unittest.mock.Mock()
        with patch.object(dashboard, "stop_ingest", return_value={"status": "running"}):
            dashboard.DashboardHandler.do_POST(handler)
        handler._send_json.assert_called_once_with(202, {"status": "running"})

    def test_job_logs_redact_provider_keys(self):
        state = {"logs": []}
        with patch.object(dashboard, "JOB_STATE", state):
            dashboard._append_job_log(
                "provider error: do-not-return-this-secret", ["do-not-return-this-secret"]
            )
        self.assertEqual(state["logs"], ["provider error: [REDACTED]"])


if __name__ == "__main__":
    unittest.main()
