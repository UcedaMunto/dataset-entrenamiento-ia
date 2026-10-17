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
            "DEEPSEEK_API_KEY=deepseek-test-secret\n"
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
            patch.object(dashboard, "REJECTION_IMAGE_CACHE", {}),
            patch.object(dashboard, "REJECTION_IMAGE_LOOKUP_MISSES", set()),
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
            connection.executemany(
                """
                INSERT INTO analisis_imagen
                    (huella_analisis, sha256, categoria, proveedor, modelo,
                     version_prompt, estado, resultado_json)
                VALUES (?, ?, 'camisa', ?, ?, '5', ?, '{}')
                """,
                [
                    ("nim-accepted", "hash-1", "nim", "vision-test", "aceptada"),
                    ("nim-rejected", "hash-2", "nim", "vision-test", "descartada"),
                    ("deepseek-accepted", "hash-3", "deepseek", "flash-test", "aceptada"),
                ],
            )
            connection.commit()

        data = dashboard.get_overview()
        self.assertEqual(data["total"], 1)
        self.assertEqual(data["counts_by_type"]["camisa"], 1)
        self.assertEqual(data["recent_images"][0]["proveedor"], "nim")
        self.assertEqual(data["recent_images"][0]["sugerencias_ia"]["colores"], ["azul"])
        self.assertIn("temporada", data["properties"])
        stats = {(row["provider"], row["model"]): row for row in data["model_stats"]}
        self.assertEqual(stats[("nim", "vision-test")]["valid"], 2)
        self.assertEqual(stats[("nim", "vision-test")]["accepted"], 1)
        self.assertEqual(stats[("nim", "vision-test")]["rejected"], 1)
        self.assertEqual(stats[("deepseek", "flash-test")]["valid"], 1)
        self.assertTrue(data["providers"]["nim"])
        self.assertNotIn("do-not-return-this-secret", json.dumps(data))

    def test_recent_rejections_include_source_images_for_legacy_and_new_records(self):
        source_root = self.root / "datos-crudos" / "fixture"
        source_root.mkdir(parents=True)
        image_path = source_root / "rejected.png"
        dashboard.app.Image.new("RGB", (12, 12), (20, 60, 140)).save(image_path)
        digest = dashboard.app.file_digest(image_path)
        with sqlite3.connect(self.database) as connection:
            connection.executemany(
                """
                INSERT INTO analisis_imagen
                    (huella_analisis, sha256, categoria, proveedor, modelo,
                     version_prompt, estado, resultado_json)
                VALUES (?, ?, 'camisa', ?, 'vision-test', '4', 'descartada', ?)
                """,
                [
                    (
                        "nim-rejection",
                        digest,
                        "nim",
                        json.dumps({
                            "apta": False,
                            "motivo_descarte": "No corresponde a la clase.",
                            "_source_id": "fixture",
                            "_source_relative_path": "rejected.png",
                        }),
                    ),
                    (
                        "deepseek-rejection",
                        digest,
                        "deepseek",
                        json.dumps({
                            "apta": False,
                            "motivo_descarte": "Imagen fuera de clase.",
                        }),
                    ),
                ],
            )
        with patch.object(dashboard, "ROOT", self.root), patch.object(
            dashboard.app,
            "load_sources",
            return_value={"fixture": {"path": "fixture", "allow_import": True}},
        ):
            nim_results = dashboard.get_recent_rejections("nim")
            deepseek_results = dashboard.get_recent_rejections("deepseek")
            handler = object.__new__(dashboard.DashboardHandler)
            handler.wfile = BytesIO()
            handler.send_response = unittest.mock.Mock()
            handler.send_header = unittest.mock.Mock()
            handler.end_headers = unittest.mock.Mock()
            handler._send_json = unittest.mock.Mock()
            handler._send_rejected_image(digest)

        self.assertEqual(len(nim_results), 1)
        self.assertEqual(nim_results[0]["motivo_descarte"], "No corresponde a la clase.")
        self.assertEqual(nim_results[0]["imagen_url"], f"/api/rejected-image/{digest}")
        self.assertEqual(deepseek_results[0]["imagen_url"], f"/api/rejected-image/{digest}")
        handler.send_response.assert_called_once_with(200)
        self.assertEqual(handler.wfile.getvalue(), image_path.read_bytes())

    def test_prompt_and_property_updates_are_persisted(self):
        handler = object.__new__(dashboard.DashboardHandler)
        handler._save_prompt({"instructions": "Describe solo ropa visible."})
        handler._save_properties({
            "color": ["azul", "rojo"],
            "estilo": ["casual", "bohemio"],
            "temporada": ["invierno", "otoño"],
        })
        with sqlite3.connect(self.database) as connection:
            prompt = connection.execute(
                "SELECT valor FROM pipeline_config WHERE clave='prompt_instructions'"
            ).fetchone()[0]
            colors = json.loads(connection.execute(
                "SELECT valores_permitidos FROM catalogo_propiedad WHERE codigo='color'"
            ).fetchone()[0])
            styles = json.loads(connection.execute(
                "SELECT valores_permitidos FROM catalogo_propiedad WHERE codigo='estilo'"
            ).fetchone()[0])
            seasons = json.loads(connection.execute(
                "SELECT valores_permitidos FROM catalogo_propiedad WHERE codigo='temporada'"
            ).fetchone()[0])
        self.assertEqual(prompt, "Describe solo ropa visible.")
        self.assertEqual(colors, ["azul", "rojo"])
        self.assertEqual(styles, ["casual", "bohemio"])
        self.assertEqual(seasons, ["invierno", "otoño"])

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

    def test_ingest_accepts_5000_and_rejects_more(self):
        payload = {
            "source": "clothing-full",
            "provider": "none",
            "limit": 5000,
            "confirm_write": True,
        }
        self.assertEqual(dashboard.validate_ingest_request(payload)[2], 5000)
        with self.assertRaisesRegex(ValueError, "1 y 5000"):
            dashboard.validate_ingest_request({**payload, "limit": 5001})

    def test_start_ingest_launches_bounded_command_without_secret_arguments(self):
        states = {}
        processes = {}
        worker = unittest.mock.Mock()
        request = {
            "source": "clothing-full",
            "provider": "nim",
            "limit": 3,
            "confirm_write": True,
            "confirm_remote": True,
        }
        with patch.object(dashboard, "JOB_STATES", states), patch.object(
            dashboard, "JOB_PROCESSES", processes
        ), patch.object(
            dashboard.threading, "Thread", return_value=worker
        ) as thread_factory:
            result = dashboard.start_ingest(request)

        provider, command, environment, secrets = thread_factory.call_args.kwargs["args"]
        self.assertEqual(provider, "nim")
        self.assertIn("--allow-remote", command)
        self.assertIn("--limit", command)
        self.assertIn("3", command)
        self.assertNotIn("do-not-return-this-secret", command)
        self.assertEqual(environment["NVIDIA_NIM_API_KEY"], "do-not-return-this-secret")
        self.assertIn("do-not-return-this-secret", secrets)
        self.assertEqual(result["jobs"][0]["status"], "running")
        worker.start.assert_called_once()

    def test_start_ingest_launches_nim_and_deepseek_in_parallel(self):
        states = {}
        workers = [unittest.mock.Mock(), unittest.mock.Mock()]
        request = {
            "source": "clothing-full",
            "providers": ["nim", "deepseek"],
            "limit": 5000,
            "confirm_write": True,
            "confirm_remote": True,
        }
        with patch.object(dashboard, "JOB_STATES", states), patch.object(
            dashboard, "JOB_PROCESSES", {}
        ), patch.object(
            dashboard.threading, "Thread", side_effect=workers
        ) as thread_factory:
            result = dashboard.start_ingest(request)

        self.assertEqual([job["provider"] for job in result["jobs"]], ["nim", "deepseek"])
        self.assertTrue(all(job["status"] == "running" for job in result["jobs"]))
        self.assertEqual(thread_factory.call_count, 2)
        self.assertEqual(
            [worker.start.call_count for worker in workers],
            [1, 1],
        )
        launched = [call.kwargs["args"] for call in thread_factory.call_args_list]
        self.assertEqual([args[0] for args in launched], ["nim", "deepseek"])
        self.assertTrue(all("--limit" in args[1] and "5000" in args[1] for args in launched))
        self.assertEqual(launched[0][2]["NIM_DEEPSEEK_FALLBACK"], "0")

    def test_stop_ingest_sends_cooperative_signal_to_running_process(self):
        state = {"nim": {
            "status": "running",
            "cancellation_requested": False,
            "message": "",
            "logs": [],
        }}
        process = unittest.mock.Mock()
        process.pid = 42
        with patch.object(dashboard, "JOB_STATES", state), patch.object(
            dashboard, "JOB_PROCESSES", {"nim": process}
        ):
            result = dashboard.stop_ingest("nim")

        process.send_signal.assert_called_once_with(dashboard.signal.SIGTERM)
        self.assertTrue(result["cancellation_requested"])
        self.assertIn("Detención solicitada", result["message"])

    def test_stop_ingest_is_remembered_if_child_is_not_started_yet(self):
        state = {"nim": {
            "status": "running",
            "cancellation_requested": False,
            "message": "",
            "logs": [],
        }}
        with patch.object(dashboard, "JOB_STATES", state), patch.object(
            dashboard, "JOB_PROCESSES", {}
        ):
            result = dashboard.stop_ingest("nim")
        self.assertTrue(result["cancellation_requested"])

    def test_stop_endpoint_calls_cooperative_stop(self):
        handler = object.__new__(dashboard.DashboardHandler)
        handler.headers = Message()
        handler.headers["Host"] = "127.0.0.1:8787"
        handler.headers["Origin"] = "http://127.0.0.1:8787"
        handler.headers["Content-Type"] = "application/json"
        body = json.dumps({"provider": "nim"}).encode()
        handler.headers["Content-Length"] = str(len(body))
        handler.rfile = BytesIO(body)
        handler.path = "/api/stop"
        handler._send_json = unittest.mock.Mock()
        with patch.object(dashboard, "stop_ingest", return_value={"status": "running"}) as stop:
            dashboard.DashboardHandler.do_POST(handler)
        stop.assert_called_once_with("nim")
        handler._send_json.assert_called_once_with(202, {"status": "running"})

    def test_job_logs_redact_provider_keys(self):
        states = {"nim": {"logs": []}}
        with patch.object(dashboard, "JOB_STATES", states):
            dashboard._append_job_log(
                "nim",
                "provider error: do-not-return-this-secret",
                ["do-not-return-this-secret"]
            )
        self.assertEqual(states["nim"]["logs"], ["provider error: [REDACTED]"])


if __name__ == "__main__":
    unittest.main()
