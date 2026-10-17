import base64
import copy
import hashlib
import json
import os
import sqlite3
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from PIL import Image

import app


TEST_SCHEMA = """
CREATE TABLE prenda (
    id_prenda INTEGER PRIMARY KEY,
    codigo TEXT NOT NULL UNIQUE,
    ruta_categoria TEXT NOT NULL,
    split TEXT,
    estado_revision TEXT NOT NULL,
    apta_para_entrenamiento INTEGER NOT NULL
);
CREATE TABLE prenda_imagen (
    id_imagen INTEGER PRIMARY KEY,
    id_prenda INTEGER NOT NULL,
    ruta_relativa TEXT NOT NULL UNIQUE,
    vista TEXT,
    es_fotografia_real INTEGER NOT NULL,
    fuente TEXT NOT NULL,
    etiqueta_fuente TEXT,
    permiso_uso TEXT NOT NULL,
    sha256 TEXT
);
CREATE TABLE catalogo_propiedad (
    id_propiedad INTEGER PRIMARY KEY,
    codigo TEXT NOT NULL,
    valores_permitidos TEXT NOT NULL,
    activo INTEGER NOT NULL
);
CREATE TABLE valor_propiedad_prenda (
    id_valor INTEGER PRIMARY KEY,
    id_prenda INTEGER NOT NULL,
    id_propiedad INTEGER NOT NULL,
    valor TEXT NOT NULL
);
CREATE TABLE descripcion_prenda (
    id_descripcion INTEGER PRIMARY KEY,
    id_prenda INTEGER NOT NULL,
    texto TEXT NOT NULL,
    atributos_sugeridos TEXT NOT NULL,
    proveedor TEXT NOT NULL,
    modelo TEXT NOT NULL,
    estado_revision TEXT NOT NULL
);
CREATE TABLE analisis_imagen (
    huella_analisis TEXT PRIMARY KEY,
    sha256 TEXT NOT NULL,
    categoria TEXT NOT NULL,
    proveedor TEXT NOT NULL,
    modelo TEXT NOT NULL,
    version_prompt TEXT NOT NULL,
    estado TEXT NOT NULL,
    resultado_json TEXT NOT NULL,
    fecha_analisis TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE pipeline_config (
    clave TEXT PRIMARY KEY,
    valor TEXT NOT NULL,
    actualizado_en TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


class CurationPipelineTests(unittest.TestCase):
    def setUp(self):
        app.CANCEL_REQUESTED.clear()
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.dataset_root = self.root / "dataset"
        self.dataset_root.mkdir()
        self.database = self.dataset_root / "metadata.sqlite"
        self.image_path = self.root / "shirt.png"
        Image.new("RGB", (16, 16), (20, 60, 140)).save(self.image_path)
        self.digest = hashlib.sha256(self.image_path.read_bytes()).hexdigest()
        self.item = {
            "path": self.image_path,
            "relative_path": Path("train/camisa/shirt.png"),
            "label": "Polo",
            "category": "camisa",
            "digest": self.digest,
            "split": "train",
        }
        self.source = {
            "path": "fixture",
            "license": "test",
            "allow_import": True,
            "photograph": True,
            "class_map": {"Polo": "camisa"},
        }
        with sqlite3.connect(self.database) as connection:
            connection.executescript(TEST_SCHEMA)
            connection.executemany(
                "INSERT INTO catalogo_propiedad VALUES (?, ?, ?, 1)",
                [
                    (1, "color", json.dumps(["azul"])),
                    (2, "estilo", json.dumps(["casual"])),
                    (3, "tipo_prenda", json.dumps(["camisa"])),
                ],
            )
        self.env_patch = patch.dict(os.environ, {"DATASET_ROOT": str(self.dataset_root)})
        self.env_patch.start()
        self.addCleanup(self.env_patch.stop)

    def tearDown(self):
        self.temp.cleanup()

    def run_ingest(self, provider="nim", items=None, limit=None):
        items = items or [self.item]
        args = SimpleNamespace(
            limit=limit or len(items),
            provider=provider,
            execute=True,
            allow_remote=True,
        )
        with (
            patch.object(app, "ROOT", self.root),
            patch.object(app, "ensure_database"),
            patch.object(app, "scan_source", return_value=(items, {
                "images": len(items),
                "mapped": len(items),
                "unmapped": 0,
                "oversize": 0,
            })),
            patch.object(app, "provider_settings", return_value=("test-key", "https://test.invalid/v1", "test-model")),
        ):
            return app.command_ingest(args, {"fixture": self.source})

    def test_analysis_fingerprint_is_stable_and_provider_specific(self):
        first = app.analysis_fingerprint(self.digest, "camisa", "nim", "test-model")
        self.assertEqual(first, app.analysis_fingerprint(self.digest, "camisa", "nim", "test-model"))
        self.assertNotEqual(first, app.analysis_fingerprint(self.digest, "camisa", "deepseek", "test-model"))
        self.assertNotEqual(first, app.analysis_fingerprint(self.digest, "chaqueta", "nim", "test-model"))

    def test_cached_accepted_analysis_is_imported_without_reanalysis(self):
        result = {
            "apta": True,
            "motivo_descarte": "",
            "descripcion": "Camisa azul.",
            "colores": ["azul"],
            "estilos": [],
        }
        prompt = app.build_annotation_prompt(
            app.DEFAULT_PROMPT_INSTRUCTIONS, "camisa", ["azul"], ["casual"], "nim"
        )
        fingerprint = app.analysis_fingerprint(
            self.digest, "camisa", "nim", "test-model", prompt
        )
        with sqlite3.connect(self.database) as connection:
            app.save_analysis(connection, fingerprint, self.item, "nim", "test-model", result)

        with patch.object(app, "annotate_image", side_effect=AssertionError("cache miss")) as annotate:
            self.assertEqual(self.run_ingest(), 0)
            self.assertEqual(self.run_ingest(), 0)
        annotate.assert_not_called()
        with sqlite3.connect(self.database) as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM analisis_imagen").fetchone()[0], 1)
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM prenda_imagen").fetchone()[0], 1)
            self.assertEqual(connection.execute("SELECT etiqueta_fuente FROM prenda_imagen").fetchone()[0], "Polo")
            self.assertEqual(connection.execute("SELECT estado_revision FROM descripcion_prenda").fetchone()[0], "pendiente")

    def test_cached_rejection_is_not_sent_or_imported_again(self):
        result = {"apta": False, "motivo_descarte": "No corresponde a camisa."}
        prompt = app.build_annotation_prompt(
            app.DEFAULT_PROMPT_INSTRUCTIONS, "camisa", ["azul"], ["casual"], "nim"
        )
        fingerprint = app.analysis_fingerprint(
            self.digest, "camisa", "nim", "test-model", prompt
        )
        with sqlite3.connect(self.database) as connection:
            app.save_analysis(connection, fingerprint, self.item, "nim", "test-model", result)

        with patch.object(app, "annotate_image", side_effect=AssertionError("cache miss")) as annotate:
            self.assertEqual(self.run_ingest(), 0)
            self.assertEqual(self.run_ingest(), 0)
        annotate.assert_not_called()
        with sqlite3.connect(self.database) as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM analisis_imagen").fetchone()[0], 1)
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM prenda").fetchone()[0], 0)

    def test_new_analysis_is_saved_and_reused(self):
        result = {
            "apta": True,
            "motivo_descarte": "",
            "descripcion": "Camisa azul.",
            "colores": ["azul"],
            "estilos": [],
        }
        with patch.object(app, "annotate_image", return_value=result) as annotate:
            self.assertEqual(self.run_ingest(), 0)
            self.assertEqual(self.run_ingest(), 0)
        annotate.assert_called_once()
        with sqlite3.connect(self.database) as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM analisis_imagen").fetchone()[0], 1)
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM prenda_imagen").fetchone()[0], 1)

    def test_parallel_imports_of_same_hash_create_only_one_dataset_item(self):
        barrier = threading.Barrier(2)

        def import_concurrently():
            created_files = []
            with sqlite3.connect(self.database, timeout=10) as connection:
                connection.execute("PRAGMA foreign_keys = ON")
                barrier.wait()
                imported = app.import_one(
                    connection,
                    self.item,
                    "fixture",
                    self.source,
                    self.dataset_root,
                    None,
                    "none",
                    "none",
                    created_files,
                )
                if imported:
                    connection.commit()
                return imported

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: import_concurrently(), range(2)))

        self.assertEqual(sorted(results), [False, True])
        with sqlite3.connect(self.database) as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM prenda").fetchone()[0], 1)
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM prenda_imagen").fetchone()[0], 1)

    def test_null_discard_reason_is_normalized_for_accepted_image(self):
        response = SimpleNamespace(
            status_code=200,
            raise_for_status=lambda: None,
            json=lambda: {
                "choices": [{
                    "message": {
                        "content": json.dumps({
                            "apta": True,
                            "motivo_descarte": None,
                            "descripcion": "Camisa azul.",
                            "colores": ["azul"],
                            "estilos": ["casual"],
                        })
                    },
                    "finish_reason": "stop",
                }]
            },
        )
        with patch.object(app, "wait_for_nim_request_slot"), patch.object(
            app.requests, "post", return_value=response
        ):
            result = app.annotate_image(
                self.image_path,
                "camisa",
                "nim",
                "test-secret",
                "https://test.invalid/v1",
                "meta/llama-3.2-11b-vision-instruct",
                ["azul"],
                ["casual"],
            )
        self.assertTrue(result["apta"])
        self.assertEqual(result["motivo_descarte"], "")

    def test_invalid_annotation_skips_image_and_continues_batch(self):
        second_path = self.root / "shirt-two.png"
        Image.new("RGB", (16, 16), (90, 20, 40)).save(second_path)
        second_item = {
            **self.item,
            "path": second_path,
            "relative_path": Path("train/camisa/shirt-two.png"),
            "digest": hashlib.sha256(second_path.read_bytes()).hexdigest(),
        }
        valid_annotation = {
            "apta": True,
            "motivo_descarte": "",
            "descripcion": "Camisa roja.",
            "colores": ["azul"],
            "estilos": ["casual"],
        }
        with patch.object(
            app,
            "annotate_image",
            side_effect=[ValueError("invalid provider shape"), valid_annotation],
        ) as annotate:
            self.assertEqual(self.run_ingest(items=[self.item, second_item]), 0)

        self.assertEqual(annotate.call_count, 2)
        with sqlite3.connect(self.database) as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM analisis_imagen").fetchone()[0], 1)
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM prenda").fetchone()[0], 1)
            self.assertEqual(
                connection.execute("SELECT sha256 FROM prenda_imagen").fetchone()[0],
                second_item["digest"],
            )

    def test_stop_after_current_analysis_prevents_sending_the_next_image(self):
        second_path = self.root / "shirt-after-stop.png"
        Image.new("RGB", (16, 16), (10, 100, 80)).save(second_path)
        second_item = {
            **self.item,
            "path": second_path,
            "relative_path": Path("train/camisa/shirt-after-stop.png"),
            "digest": hashlib.sha256(second_path.read_bytes()).hexdigest(),
        }
        result = {
            "apta": True,
            "motivo_descarte": "",
            "descripcion": "Camisa azul.",
            "colores": ["azul"],
            "estilos": ["casual"],
        }

        def finish_current_image(*args, **kwargs):
            app.CANCEL_REQUESTED.set()
            return result

        with patch.object(app, "annotate_image", side_effect=finish_current_image) as annotate:
            self.assertEqual(self.run_ingest(items=[self.item, second_item]), 0)

        annotate.assert_called_once()
        with sqlite3.connect(self.database) as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM prenda").fetchone()[0], 1)
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM analisis_imagen").fetchone()[0], 1)

    def test_stop_during_timeout_does_not_retry_or_advance_to_another_image(self):
        second_path = self.root / "shirt-after-cancelled-timeout.png"
        Image.new("RGB", (16, 16), (50, 120, 30)).save(second_path)
        second_item = {
            **self.item,
            "path": second_path,
            "relative_path": Path("train/camisa/shirt-after-cancelled-timeout.png"),
            "digest": hashlib.sha256(second_path.read_bytes()).hexdigest(),
        }

        def timeout_and_stop(*args, **kwargs):
            app.CANCEL_REQUESTED.set()
            raise app.AnnotationTimeoutError("read timed out")

        with patch.object(app, "annotate_image", side_effect=timeout_and_stop) as annotate, patch.object(
            app, "random"
        ) as random:
            self.assertEqual(self.run_ingest(items=[self.item, second_item]), 0)

        annotate.assert_called_once()
        random.randint.assert_not_called()
        with sqlite3.connect(self.database) as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM analisis_imagen").fetchone()[0], 0)
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM prenda").fetchone()[0], 0)

    def test_nim_timeout_retries_same_image_then_continues_to_next_image(self):
        second_path = self.root / "shirt-after-timeout.png"
        Image.new("RGB", (16, 16), (90, 20, 40)).save(second_path)
        second_item = {
            **self.item,
            "path": second_path,
            "relative_path": Path("train/camisa/shirt-after-timeout.png"),
            "digest": hashlib.sha256(second_path.read_bytes()).hexdigest(),
        }
        valid_annotation = {
            "apta": True,
            "motivo_descarte": "",
            "descripcion": "Camisa roja.",
            "colores": ["azul"],
            "estilos": ["casual"],
        }
        with (
            patch.object(
                app,
                "annotate_image",
                side_effect=[
                    app.AnnotationTimeoutError("first timeout"),
                    app.AnnotationTimeoutError("second timeout"),
                    valid_annotation,
                ],
            ) as annotate,
            patch.object(app.random, "randint", return_value=73) as randint,
            patch.object(app.CANCEL_REQUESTED, "wait", return_value=False) as wait,
        ):
            self.assertEqual(self.run_ingest(items=[self.item, second_item]), 0)

        self.assertEqual(annotate.call_count, 3)
        self.assertEqual(
            [call.args[0] for call in annotate.call_args_list],
            [self.item["path"], self.item["path"], second_item["path"]],
        )
        randint.assert_called_once_with(30, 120)
        wait.assert_called_once_with(73)
        with sqlite3.connect(self.database) as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM analisis_imagen").fetchone()[0], 1)
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM prenda_imagen").fetchone()[0], 1)
            self.assertEqual(
                connection.execute("SELECT sha256 FROM prenda_imagen").fetchone()[0],
                second_item["digest"],
            )

    def test_imported_images_are_filtered_before_applying_batch_limit(self):
        items = [self.item]
        for index, color in enumerate(((90, 20, 40), (30, 100, 50)), start=2):
            path = self.root / f"shirt-{index}.png"
            Image.new("RGB", (16, 16), color).save(path)
            items.append({
                **self.item,
                "path": path,
                "relative_path": Path(f"train/camisa/shirt-{index}.png"),
                "digest": hashlib.sha256(path.read_bytes()).hexdigest(),
            })
        with sqlite3.connect(self.database) as connection:
            connection.execute(
                """
                INSERT INTO prenda_imagen
                    (id_prenda, ruta_relativa, es_fotografia_real, fuente,
                     etiqueta_fuente, permiso_uso, sha256)
                VALUES (99, 'already/imported.png', 1, 'fixture', 'Polo', 'test', ?)
                """,
                (self.digest,),
            )

        valid_annotation = {
            "apta": True,
            "motivo_descarte": "",
            "descripcion": "Camisa.",
            "colores": ["azul"],
            "estilos": ["casual"],
        }
        with patch.object(
            app, "annotate_image", side_effect=[valid_annotation, valid_annotation]
        ) as annotate:
            self.assertEqual(self.run_ingest(items=items, limit=2), 0)

        self.assertEqual(annotate.call_count, 2)
        self.assertEqual(
            {call.args[0] for call in annotate.call_args_list},
            {items[1]["path"], items[2]["path"]},
        )
        with sqlite3.connect(self.database) as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM prenda").fetchone()[0], 2)
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM analisis_imagen").fetchone()[0], 2)

    def test_scan_excludes_unmapped_and_over_limit_images(self):
        root = self.root / "raw"
        mapped = root / "train" / "camisa"
        excluded = root / "train" / "lenceria"
        mapped.mkdir(parents=True)
        excluded.mkdir(parents=True)
        (mapped / "small.jpg").write_bytes(b"small")
        (mapped / "large.jpg").write_bytes(b"x" * (app.MAX_IMAGE_BYTES + 1))
        (excluded / "lingerie.jpg").write_bytes(b"excluded")

        items, counts = app.scan_source(root, {"class_map": {"camisa": "camisa"}})
        self.assertEqual(counts, {
            "images": 3,
            "mapped": 1,
            "unmapped": 1,
            "oversize": 1,
        })
        self.assertEqual([item["label"] for item in items], ["camisa"])

    def test_image_payload_preserves_bytes_and_detects_actual_format(self):
        data_url = app.image_data_url(self.image_path)
        header, encoded = data_url.split(",", 1)
        self.assertTrue(header.startswith("data:image/png;base64"))
        self.assertEqual(base64.b64decode(encoded), self.image_path.read_bytes())
        large = self.root / "large.png"
        large.write_bytes(self.image_path.read_bytes() + b"x" * app.MAX_IMAGE_BYTES)
        with self.assertRaises(RuntimeError):
            app.image_data_url(large)

    def test_nim_http_error_includes_model_detail_without_leaking_key(self):
        response = SimpleNamespace(
            status_code=404,
            text='{"detail":"model not found; key=test-secret"}',
        )
        response.raise_for_status = lambda: (_ for _ in ()).throw(
            app.requests.HTTPError("404 Client Error")
        )
        with patch.object(app, "wait_for_nim_request_slot"), patch.object(
            app.requests, "post", return_value=response
        ):
            with self.assertRaises(RuntimeError) as raised:
                app.annotate_image(
                    self.image_path,
                    "camisa",
                    "nim",
                    "test-secret",
                    "https://test.invalid/v1",
                    "meta/llama-3.2-11b-vision-instruct",
                    ["azul"],
                    ["casual"],
                )
        message = str(raised.exception)
        self.assertIn("HTTP 404", message)
        self.assertIn("meta/llama-3.2-11b-vision-instruct", message)
        self.assertIn("[REDACTED]", message)
        self.assertNotIn("test-secret", message)

    def test_nim_requests_json_mode_and_reports_truncated_output(self):
        response = SimpleNamespace(
            status_code=200,
            raise_for_status=lambda: None,
            json=lambda: {
                "choices": [{
                    "message": {"content": '{"apta":true,"descripcion":"Camisa azul'},
                    "finish_reason": "length",
                }]
            },
        )
        payloads = []

        def post_response(*args, **kwargs):
            payloads.append(copy.deepcopy(kwargs["json"]))
            return response

        with patch.object(app, "wait_for_nim_request_slot"), patch.object(
            app.requests, "post", side_effect=post_response
        ) as post:
            with self.assertRaisesRegex(
                ValueError, r"NIM devolvió JSON inválido en etapa colores"
            ):
                app.annotate_image(
                    self.image_path,
                    "camisa",
                    "nim",
                    "test-secret",
                    "https://test.invalid/v1",
                    "meta/llama-3.2-11b-vision-instruct",
                    ["azul"],
                    ["casual"],
                )

        self.assertEqual(post.call_count, 2)
        payload = payloads[0]
        self.assertEqual(payload["response_format"], {"type": "json_object"})
        self.assertEqual(payload["max_tokens"], 256)
        self.assertEqual(payloads[1]["max_tokens"], 512)

    def test_nim_json_response_is_parsed(self):
        response = SimpleNamespace(
            status_code=200,
            raise_for_status=lambda: None,
            json=lambda: {
                "choices": [{
                    "message": {
                        "content": json.dumps({
                            "apta": True,
                            "motivo_descarte": "",
                            "descripcion": "Camisa azul.",
                            "colores": ["azul"],
                            "estilos": ["casual"],
                        })
                    },
                    "finish_reason": "stop",
                }]
            },
        )
        with patch.object(app, "wait_for_nim_request_slot"), patch.object(
            app.requests, "post", return_value=response
        ) as post:
            result = app.annotate_image(
                self.image_path,
                "camisa",
                "nim",
                "test-secret",
                "https://test.invalid/v1",
                "meta/llama-3.2-11b-vision-instruct",
                ["azul"],
                ["casual"],
            )
        self.assertTrue(result["apta"])
        self.assertEqual(result["descripcion"], "Camisa azul.")
        self.assertEqual(post.call_count, 3)
        self.assertEqual(post.call_args.kwargs["json"]["response_format"]["type"], "json_object")
        prompts = [
            call.kwargs["json"]["messages"][0]["content"][0]["text"]
            for call in post.call_args_list
        ]
        self.assertIn("ETAPA 1/3 — COLORES", prompts[0])
        self.assertIn("ETAPA 2/3 — ESTILOS", prompts[1])
        self.assertIn("ETAPA 3/3 — VALIDACIÓN Y DESCRIPCIÓN", prompts[2])

    def test_nim_prompt_and_result_limit_description_and_attributes(self):
        response = SimpleNamespace(
            status_code=200,
            raise_for_status=lambda: None,
            json=lambda: {
                "choices": [{
                    "message": {
                        "content": json.dumps({
                            "apta": True,
                            "motivo_descarte": "",
                            "descripcion": "Camisa de algodón azul lisa para uso diario casual.",
                            "colores": ["verde", "azul", "rojo"],
                            "estilos": ["formal", "casual", "deportivo"],
                        })
                    },
                    "finish_reason": "stop",
                }]
            },
        )
        with patch.object(app, "wait_for_nim_request_slot"), patch.object(
            app.requests, "post", return_value=response
        ) as post:
            result = app.annotate_image(
                self.image_path,
                "camisa",
                "nim",
                "test-secret",
                "https://test.invalid/v1",
                "meta/llama-3.2-11b-vision-instruct",
                ["azul", "rojo", "verde"],
                ["casual", "deportivo", "formal"],
            )

        prompts = [
            call.kwargs["json"]["messages"][0]["content"][0]["text"]
            for call in post.call_args_list
        ]
        self.assertIn('"azul"', prompts[0])
        self.assertIn('"rojo"', prompts[0])
        self.assertIn('"casual"', prompts[1])
        self.assertIn('"formal"', prompts[1])
        self.assertIn("máximo 8 palabras", prompts[2])
        self.assertEqual(len(result["descripcion"].split()), 8)
        self.assertEqual(result["colores"], ["azul", "rojo"])
        self.assertEqual(result["estilos"], ["casual", "deportivo"])

    def test_nim_retries_invalid_json_per_stage_and_combines_results(self):
        contents = [
            '{"colores":["azul"]} contenido extra',
            '{"colores":["azul","inventado"]}',
            '{"estilos":"casual"}',
            '{"estilos":["casual"]}',
            '{"apta":true,"motivo_descarte":"","descripcion":"Camisa azul casual"}',
        ]
        payloads = []
        authorization_headers = []

        def post_response(*args, **kwargs):
            payloads.append(copy.deepcopy(kwargs["json"]))
            authorization_headers.append(kwargs["headers"]["Authorization"])
            content = contents.pop(0)
            return SimpleNamespace(
                status_code=200,
                raise_for_status=lambda: None,
                json=lambda: {"choices": [{
                    "message": {"content": content},
                    "finish_reason": "stop",
                }]},
            )

        with patch.object(app, "wait_for_nim_request_slot"), patch.object(
            app.requests, "post", side_effect=post_response
        ):
            result = app.annotate_image(
                self.image_path,
                "camisa",
                "nim",
                "test-secret",
                "https://test.invalid/v1",
                "meta/llama-3.2-11b-vision-instruct",
                ["azul", "rojo"],
                ["casual", "formal"],
            )

        self.assertTrue(result["apta"])
        self.assertEqual(result["colores"], ["azul"])
        self.assertEqual(result["estilos"], ["casual"])
        self.assertEqual(len(payloads), 5)
        self.assertTrue(all(header == "Bearer test-secret" for header in authorization_headers))
        self.assertEqual(
            [payload["max_tokens"] for payload in payloads], [256, 512, 256, 512, 256]
        )
        self.assertEqual(
            [
                payload["messages"][0]["content"][0]["text"].splitlines()[0]
                for payload in payloads
            ],
            [
                "ETAPA 1/3 — COLORES",
                "ETAPA 1/3 — COLORES",
                "ETAPA 2/3 — ESTILOS",
                "ETAPA 2/3 — ESTILOS",
                "ETAPA 3/3 — VALIDACIÓN Y DESCRIPCIÓN",
            ],
        )

    def test_nim_discard_reason_is_limited_to_eight_words(self):
        response = SimpleNamespace(
            status_code=200,
            raise_for_status=lambda: None,
            json=lambda: {
                "choices": [{
                    "message": {
                        "content": json.dumps({
                            "apta": False,
                            "colores": ["azul"],
                            "estilos": ["casual"],
                            "motivo_descarte": (
                                "Esta imagen no parece corresponder a camisa debido "
                                "a la forma y el contexto."
                            ),
                        })
                    },
                    "finish_reason": "stop",
                }]
            },
        )
        with patch.object(app, "wait_for_nim_request_slot"), patch.object(
            app.requests, "post", return_value=response
        ):
            result = app.annotate_image(
                self.image_path,
                "camisa",
                "nim",
                "test-secret",
                "https://test.invalid/v1",
                "meta/llama-3.2-11b-vision-instruct",
                ["azul"],
                ["casual"],
            )

        self.assertEqual(len(result["motivo_descarte"].split()), 8)

    def test_deepseek_disables_thinking_and_requests_json_mode(self):
        response = SimpleNamespace(
            status_code=200,
            raise_for_status=lambda: None,
            json=lambda: {
                "choices": [{
                    "message": {
                        "content": json.dumps({
                            "apta": True,
                            "motivo_descarte": "",
                            "descripcion": "Camisa azul.",
                            "colores": ["azul", "negro", "blanco"],
                            "estilos": ["casual", "formal", "deportivo"],
                        })
                    },
                    "finish_reason": "stop",
                }]
            },
        )
        with patch.object(app.requests, "post", return_value=response) as post:
            result = app.annotate_image(
                self.image_path,
                "camisa",
                "deepseek",
                "test-secret",
                "https://test.invalid/v1",
                "deepseek-flash",
                ["azul", "negro", "blanco"],
                ["casual", "formal", "deportivo"],
            )
        self.assertTrue(result["apta"])
        self.assertEqual(result["colores"], ["azul", "blanco", "negro"])
        self.assertEqual(result["estilos"], ["casual", "deportivo", "formal"])
        payload = post.call_args.kwargs["json"]
        self.assertEqual(payload["response_format"], {"type": "json_object"})
        self.assertEqual(payload["thinking"], {"type": "disabled"})
        self.assertEqual(payload["max_tokens"], 1024)
        self.assertIn("Ejemplo de forma", payload["messages"][0]["content"][0]["text"])
        self.assertIn("máximo 12 palabras", payload["messages"][0]["content"][0]["text"])
        self.assertIn("colores (lista de máximo 3)", payload["messages"][0]["content"][0]["text"])

    def test_deepseek_empty_json_output_is_retried_once(self):
        valid_content = json.dumps({
            "apta": True,
            "motivo_descarte": "",
            "descripcion": "Camisa azul.",
            "colores": ["azul"],
            "estilos": ["casual"],
        })
        responses = [
            SimpleNamespace(
                status_code=200,
                raise_for_status=lambda: None,
                json=lambda: {"choices": [{
                    "message": {"content": ""},
                    "finish_reason": "length",
                }]},
            ),
            SimpleNamespace(
                status_code=200,
                raise_for_status=lambda: None,
                json=lambda: {"choices": [{
                    "message": {"content": valid_content},
                    "finish_reason": "stop",
                }]},
            ),
        ]
        payloads = []

        def post_response(*args, **kwargs):
            payloads.append(copy.deepcopy(kwargs["json"]))
            return responses.pop(0)

        with patch.object(app.requests, "post", side_effect=post_response) as post:
            result = app.annotate_image(
                self.image_path,
                "camisa",
                "deepseek",
                "test-secret",
                "https://test.invalid/v1",
                "deepseek-flash",
                ["azul"],
                ["casual"],
            )
        self.assertTrue(result["apta"])
        self.assertEqual(post.call_count, 2)
        self.assertEqual(
            [payload["max_tokens"] for payload in payloads],
            [1024, 2048],
        )

    def test_nim_request_spacing_is_at_least_three_seconds(self):
        with (
            patch.object(app, "_last_nim_request_at", None),
            patch.object(app.time, "monotonic", side_effect=[100.0, 101.0, 104.0]),
            patch.object(app.time, "sleep") as sleep,
        ):
            app.wait_for_nim_request_slot()
            app.wait_for_nim_request_slot()
        sleep.assert_called_once_with(2.0)


if __name__ == "__main__":
    unittest.main()
