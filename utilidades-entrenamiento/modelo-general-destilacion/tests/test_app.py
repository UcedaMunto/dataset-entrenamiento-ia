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
        app._nim_model_strikes.clear()
        strikes_patch = patch.object(app, "NIM_MODEL_MAX_STRIKES", 1)
        strikes_patch.start()
        self.addCleanup(strikes_patch.stop)
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
                    (4, "temporada", json.dumps(["invierno"])),
                ],
            )
        self.env_patch = patch.dict(os.environ, {"DATASET_ROOT": str(self.dataset_root)})
        self.env_patch.start()
        self.addCleanup(self.env_patch.stop)

    def tearDown(self):
        self.temp.cleanup()

    def run_ingest(self, provider="nim", items=None, limit=None, settings=None):
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
            patch.object(
                app,
                "provider_settings",
                side_effect=settings,
            ) if settings else patch.object(
                app,
                "provider_settings",
                return_value=("test-key", "https://test.invalid/v1", "test-model"),
            ),
            patch.dict(
                os.environ,
                {"NVIDIA_NIM_FALLBACK_MODELS": "meta/llama-3.2-11b-vision-instruct"},
            ),
        ):
            return app.command_ingest(args, {"fixture": self.source})

    def test_analysis_fingerprint_is_stable_and_provider_specific(self):
        first = app.analysis_fingerprint(self.digest, "camisa", "nim", "test-model")
        self.assertEqual(first, app.analysis_fingerprint(self.digest, "camisa", "nim", "test-model"))
        self.assertNotEqual(first, app.analysis_fingerprint(self.digest, "camisa", "deepseek", "test-model"))
        self.assertNotEqual(first, app.analysis_fingerprint(self.digest, "chaqueta", "nim", "test-model"))

    def test_nim_automatically_switches_to_fallback_model_after_failure(self):
        annotation = {"apta": False, "motivo_descarte": "No es una camisa."}
        unavailable_models = set()
        with patch.dict(
            os.environ,
            {"NVIDIA_NIM_FALLBACK_MODELS": "meta/llama-3.2-11b-vision-instruct"},
        ), patch.object(
            app,
            "annotate_image",
            side_effect=[RuntimeError("NIM HTTP 404"), annotation],
        ) as annotate:
            result = app.annotate_with_provider_fallback(
                self.image_path,
                "camisa",
                "nim",
                "nim-key",
                "https://nim.test/v1",
                "nvidia/nemotron-3.5-super-vl-120b-a12b",
                ["azul"],
                ["casual"],
                app.DEFAULT_PROMPT_INSTRUCTIONS,
                ["invierno"],
                unavailable_nim_models=unavailable_models,
            )

        self.assertEqual(
            result[:3],
            (annotation, "nim", "meta/llama-3.2-11b-vision-instruct"),
        )
        self.assertEqual(
            [call.args[5] for call in annotate.call_args_list],
            [
                "nvidia/nemotron-3.5-super-vl-120b-a12b",
                "meta/llama-3.2-11b-vision-instruct",
            ],
        )
        self.assertEqual(
            unavailable_models,
            {"nvidia/nemotron-3.5-super-vl-120b-a12b"},
        )

    def test_all_failed_nim_models_are_not_retried_for_later_images(self):
        primary_model = "nvidia/nemotron-3.5-super-vl-120b-a12b"
        fallback_model = "meta/llama-3.2-11b-vision-instruct"
        unavailable_models = set()
        with patch.dict(
            os.environ,
            {"NVIDIA_NIM_FALLBACK_MODELS": fallback_model},
        ), patch.object(
            app,
            "annotate_image",
            side_effect=[RuntimeError("HTTP 404 invalid"), RuntimeError("HTTP 404 invalid")],
        ) as annotate:
            with self.assertRaisesRegex(RuntimeError, "HTTP 404 invalid"):
                app.annotate_with_provider_fallback(
                    self.image_path,
                    "camisa",
                    "nim",
                    "nim-key",
                    "https://nim.test/v1",
                    primary_model,
                    ["azul"],
                    ["casual"],
                    app.DEFAULT_PROMPT_INSTRUCTIONS,
                    ["invierno"],
                    unavailable_nim_models=unavailable_models,
                )

            self.assertEqual(unavailable_models, {primary_model, fallback_model})
            with self.assertRaisesRegex(RuntimeError, "No quedan modelos NVIDIA NIM"):
                app.annotate_with_provider_fallback(
                    self.image_path,
                    "camisa",
                    "nim",
                    "nim-key",
                    "https://nim.test/v1",
                    primary_model,
                    ["azul"],
                    ["casual"],
                    app.DEFAULT_PROMPT_INSTRUCTIONS,
                    ["invierno"],
                    unavailable_nim_models=unavailable_models,
                )

        self.assertEqual(annotate.call_count, 2)

    def test_transient_nim_500_is_retried_and_does_not_exclude_model(self):
        annotation = {"apta": False, "motivo_descarte": "No es una camisa."}
        unavailable_models = set()
        primary_model = "nvidia/nemotron-3.5-super-vl-120b-a12b"
        with patch.object(app, "NIM_MODEL_MAX_STRIKES", 4), patch.object(
            app,
            "annotate_image",
            side_effect=[RuntimeError("NIM HTTP 500"), annotation],
        ) as annotate, patch.object(app.CANCEL_REQUESTED, "wait", return_value=False):
            result = app.annotate_with_provider_fallback(
                self.image_path, "camisa", "nim", "nim-key", "https://nim.test/v1",
                primary_model, ["azul"], ["casual"], app.DEFAULT_PROMPT_INSTRUCTIONS,
                ["invierno"], unavailable_nim_models=unavailable_models,
            )
        self.assertEqual(result[2], primary_model)
        self.assertEqual(annotate.call_count, 2)
        self.assertEqual(unavailable_models, set())

    def test_default_nim_model_chain_includes_two_additional_vision_models(self):
        with patch.dict(os.environ, {"NVIDIA_NIM_FALLBACK_MODELS": ""}):
            self.assertEqual(
                app.nim_model_chain("primary-model"),
                [
                    "primary-model",
                    "meta/llama-3.2-11b-vision-instruct",
                    "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning",
                ],
            )

    def test_deepseek_failure_falls_back_to_nim(self):
        annotation = {
            "apta": True,
            "motivo_descarte": "",
            "descripcion": "Camisa azul.",
            "colores": ["azul"],
            "estilos": [],
            "temporadas": [],
        }
        with patch.dict(
            os.environ,
            {"NVIDIA_NIM_FALLBACK_MODELS": "meta/llama-3.2-11b-vision-instruct"},
        ), patch.object(
            app,
            "annotate_image",
            side_effect=[RuntimeError("DeepSeek API unavailable"), annotation],
        ) as annotate:
            result = app.annotate_with_provider_fallback(
                self.image_path,
                "camisa",
                "deepseek",
                "deepseek-key",
                "https://deepseek.test/v1",
                "deepseek-flash",
                ["azul"],
                ["casual"],
                app.DEFAULT_PROMPT_INSTRUCTIONS,
                ["invierno"],
                nim_settings=(
                    "nim-key",
                    "https://nim.test/v1",
                    "nvidia/nemotron-3.5-super-vl-120b-a12b",
                ),
            )

        self.assertEqual(
            result[:3],
            (annotation, "nim", "nvidia/nemotron-3.5-super-vl-120b-a12b"),
        )
        self.assertEqual(
            [call.args[2] for call in annotate.call_args_list], ["deepseek", "nim"]
        )

    def test_cached_accepted_analysis_is_imported_without_reanalysis(self):
        result = {
            "apta": True,
            "motivo_descarte": "",
            "descripcion": "Camisa azul.",
            "colores": ["azul"],
            "estilos": [],
            "temporadas": [],
        }
        prompt = app.build_annotation_prompt(
            app.DEFAULT_PROMPT_INSTRUCTIONS, "camisa", ["azul"], ["casual"], "nim",
            ["invierno"],
        )
        fingerprint = app.analysis_fingerprint(
            self.digest, "camisa", "nim", "test-model", prompt
        )
        with sqlite3.connect(self.database) as connection:
            app.save_analysis(connection, fingerprint, self.item, "nim", "test-model", result)

        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": ""}), patch.object(
            app, "annotate_image", side_effect=AssertionError("cache miss")
        ) as annotate:
            self.assertEqual(self.run_ingest(), 0)
            self.assertEqual(self.run_ingest(), 0)
        annotate.assert_not_called()
        with sqlite3.connect(self.database) as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM analisis_imagen").fetchone()[0], 1)
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM prenda_imagen").fetchone()[0], 1)
            self.assertEqual(connection.execute("SELECT etiqueta_fuente FROM prenda_imagen").fetchone()[0], "Polo")
            self.assertEqual(connection.execute("SELECT estado_revision FROM descripcion_prenda").fetchone()[0], "pendiente")

    def test_new_styles_and_seasons_are_added_but_colors_stay_restricted(self):
        result = {
            "apta": True,
            "motivo_descarte": "",
            "descripcion": "Camisa azul.",
            "colores": ["azul"],
            "estilos": ["bohemio"],
            "temporadas": ["otoño"],
        }
        with patch.object(app, "annotate_image", return_value=result):
            self.assertEqual(self.run_ingest(), 0)

        with sqlite3.connect(self.database) as connection:
            catalogs = {
                code: json.loads(values)
                for code, values in connection.execute(
                    "SELECT codigo, valores_permitidos FROM catalogo_propiedad"
                )
            }
        self.assertIn("bohemio", catalogs["estilo"])
        self.assertIn("otoño", catalogs["temporada"])
        self.assertEqual(catalogs["color"], ["azul"])

    def test_rejected_analysis_also_adds_reported_styles_and_seasons(self):
        result = {
            "apta": False,
            "motivo_descarte": "No corresponde a camisa.",
            "estilos": ["bohemio"],
            "temporadas": ["otoño"],
        }
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": ""}), patch.object(
            app, "annotate_image", return_value=result
        ):
            self.assertEqual(self.run_ingest(), 0)

        with sqlite3.connect(self.database) as connection:
            styles = json.loads(connection.execute(
                "SELECT valores_permitidos FROM catalogo_propiedad WHERE codigo='estilo'"
            ).fetchone()[0])
            seasons = json.loads(connection.execute(
                "SELECT valores_permitidos FROM catalogo_propiedad WHERE codigo='temporada'"
            ).fetchone()[0])
            imported = connection.execute("SELECT COUNT(*) FROM prenda").fetchone()[0]
        self.assertIn("bohemio", styles)
        self.assertIn("otoño", seasons)
        self.assertEqual(imported, 0)

    def test_cached_rejection_is_not_sent_or_imported_again(self):
        result = {"apta": False, "motivo_descarte": "No corresponde a camisa."}
        prompt = app.build_annotation_prompt(
            app.DEFAULT_PROMPT_INSTRUCTIONS, "camisa", ["azul"], ["casual"], "nim",
            ["invierno"],
        )
        fingerprint = app.analysis_fingerprint(
            self.digest, "camisa", "nim", "test-model", prompt
        )
        with sqlite3.connect(self.database) as connection:
            app.save_analysis(connection, fingerprint, self.item, "nim", "test-model", result)

        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": ""}), patch.object(
            app, "annotate_image", side_effect=AssertionError("cache miss")
        ) as annotate:
            self.assertEqual(self.run_ingest(), 0)
            self.assertEqual(self.run_ingest(), 0)
        annotate.assert_not_called()
        with sqlite3.connect(self.database) as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM analisis_imagen").fetchone()[0], 1)
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM prenda").fetchone()[0], 0)

    def test_existing_rejections_do_not_consume_the_new_analysis_limit(self):
        rejection = {"apta": False, "motivo_descarte": "No corresponde a camisa."}
        prompt = app.build_annotation_prompt(
            app.DEFAULT_PROMPT_INSTRUCTIONS, "camisa", ["azul"], ["casual"], "nim",
            ["invierno"],
        )
        fingerprint = app.analysis_fingerprint(
            self.digest, "camisa", "nim", "test-model", prompt
        )
        with sqlite3.connect(self.database) as connection:
            app.save_analysis(
                connection, fingerprint, self.item, "nim", "test-model", rejection
            )

        unprocessed = []
        for index, color in enumerate(((30, 100, 50), (160, 80, 30)), start=1):
            path = self.root / f"new-shirt-{index}.png"
            Image.new("RGB", (16, 16), color).save(path)
            unprocessed.append({
                **self.item,
                "path": path,
                "relative_path": Path(f"train/camisa/new-shirt-{index}.png"),
                "digest": hashlib.sha256(path.read_bytes()).hexdigest(),
            })
        accepted = {
            "apta": True,
            "motivo_descarte": "",
            "descripcion": "Camisa verde.",
            "colores": ["azul"],
            "estilos": ["casual"],
            "temporadas": [],
        }
        with patch.object(app, "annotate_image", return_value=accepted) as annotate:
            self.assertEqual(
                self.run_ingest(items=[self.item, *unprocessed], limit=1), 0
            )

        annotate.assert_called_once()
        self.assertEqual(annotate.call_args.args[0], unprocessed[0]["path"])

    def test_deepseek_failure_persists_nim_fallback_result_and_model(self):
        accepted = {
            "apta": True,
            "motivo_descarte": "",
            "descripcion": "Camisa azul.",
            "colores": ["azul"],
            "estilos": ["casual"],
            "temporadas": [],
        }
        with patch.dict(
            os.environ,
            {
                "DEEPSEEK_API_KEY": "test-deepseek-key",
                "NVIDIA_NIM_API_KEY": "test-nim-key",
                "NVIDIA_NIM_FALLBACK_MODELS": "meta/llama-3.2-11b-vision-instruct",
            },
        ), patch.object(
            app,
            "annotate_image",
            side_effect=[RuntimeError("DeepSeek unavailable"), accepted],
        ) as annotate:
            self.assertEqual(self.run_ingest(
                provider="deepseek",
                settings=[
                    ("test-deepseek-key", "https://deepseek.test/v1", "deepseek-model"),
                    ("test-nim-key", "https://nim.test/v1", "nim-model"),
                ],
            ), 0)

        self.assertEqual(
            [call.args[2] for call in annotate.call_args_list], ["deepseek", "nim"]
        )
        with sqlite3.connect(self.database) as connection:
            self.assertEqual(
                connection.execute(
                    "SELECT proveedor, modelo FROM analisis_imagen"
                ).fetchone(),
                ("nim", "nim-model"),
            )
            self.assertEqual(
                connection.execute(
                    "SELECT proveedor, modelo FROM descripcion_prenda"
                ).fetchone(),
                ("nim", "nim-model"),
            )

    def test_nim_rejection_is_rechecked_by_deepseek_and_imported_if_accepted(self):
        nim_rejection = {
            "apta": False,
            "motivo_descarte": "No corresponde a camisa.",
            "colores": ["azul"],
            "estilos": ["casual"],
            "temporadas": [],
        }
        deepseek_acceptance = {
            "apta": True,
            "motivo_descarte": "",
            "descripcion": "Camisa azul casual.",
            "colores": ["azul"],
            "estilos": ["casual"],
            "temporadas": [],
        }
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "test-deepseek-key"}), patch.object(
            app, "annotate_image", side_effect=[nim_rejection, deepseek_acceptance]
        ) as annotate:
            self.assertEqual(self.run_ingest(settings=[
                ("test-nim-key", "https://nim.test/v1", "nim-model"),
                ("test-deepseek-key", "https://deepseek.test/v1", "deepseek-model"),
            ]), 0)

        self.assertEqual(
            [call.args[2] for call in annotate.call_args_list], ["nim", "deepseek"]
        )
        with sqlite3.connect(self.database) as connection:
            analyses = connection.execute(
                "SELECT proveedor, estado FROM analisis_imagen ORDER BY proveedor"
            ).fetchall()
            self.assertEqual(analyses, [("deepseek", "aceptada"), ("nim", "descartada")])
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM prenda").fetchone()[0], 1)
            self.assertEqual(
                connection.execute("SELECT proveedor, modelo FROM descripcion_prenda").fetchone(),
                ("deepseek", "deepseek-model"),
            )

    def test_nim_and_deepseek_rejections_are_both_saved_without_import(self):
        nim_rejection = {
            "apta": False,
            "motivo_descarte": "No corresponde a camisa.",
            "colores": ["azul"],
            "estilos": ["casual"],
            "temporadas": [],
        }
        deepseek_rejection = {
            "apta": False,
            "motivo_descarte": "No es una camisa.",
            "colores": ["azul"],
            "estilos": ["casual"],
            "temporadas": [],
        }
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "test-deepseek-key"}), patch.object(
            app, "annotate_image", side_effect=[nim_rejection, deepseek_rejection]
        ):
            self.assertEqual(self.run_ingest(settings=[
                ("test-nim-key", "https://nim.test/v1", "nim-model"),
                ("test-deepseek-key", "https://deepseek.test/v1", "deepseek-model"),
            ]), 0)

        with sqlite3.connect(self.database) as connection:
            self.assertEqual(
                connection.execute(
                    "SELECT proveedor, estado FROM analisis_imagen ORDER BY proveedor"
                ).fetchall(),
                [("deepseek", "descartada"), ("nim", "descartada")],
            )
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM prenda").fetchone()[0], 0)

    def test_new_analysis_is_saved_and_reused(self):
        result = {
            "apta": True,
            "motivo_descarte": "",
            "descripcion": "Camisa azul.",
            "colores": ["azul"],
            "estilos": [],
            "temporadas": [],
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
                            "temporadas": ["verano"],
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

    def test_invalid_annotations_exhausting_nim_stop_batch_without_retries(self):
        second_path = self.root / "shirt-two.png"
        Image.new("RGB", (16, 16), (90, 20, 40)).save(second_path)
        second_item = {
            **self.item,
            "path": second_path,
            "relative_path": Path("train/camisa/shirt-two.png"),
            "digest": hashlib.sha256(second_path.read_bytes()).hexdigest(),
        }
        with patch.object(
            app,
            "annotate_image",
            side_effect=[
                ValueError("invalid provider shape"),
                ValueError("fallback response also invalid"),
            ],
        ) as annotate:
            with self.assertRaisesRegex(RuntimeError, "No quedan modelos NVIDIA NIM"):
                self.run_ingest(items=[self.item, second_item])

        self.assertEqual(annotate.call_count, 2)
        with sqlite3.connect(self.database) as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM analisis_imagen").fetchone()[0], 0)
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM prenda").fetchone()[0], 0)

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

    def test_nim_timeout_retries_models_then_stops_after_chain_is_exhausted(self):
        second_path = self.root / "shirt-after-timeout.png"
        Image.new("RGB", (16, 16), (90, 20, 40)).save(second_path)
        second_item = {
            **self.item,
            "path": second_path,
            "relative_path": Path("train/camisa/shirt-after-timeout.png"),
            "digest": hashlib.sha256(second_path.read_bytes()).hexdigest(),
        }
        with (
            patch.object(
                app,
                "annotate_image",
                side_effect=[
                    app.AnnotationTimeoutError("first timeout"),
                    app.AnnotationTimeoutError("second timeout"),
                    app.AnnotationTimeoutError("fallback first timeout"),
                    app.AnnotationTimeoutError("fallback second timeout"),
                ],
            ) as annotate,
            patch.object(app.random, "randint", return_value=73) as randint,
            patch.object(app.CANCEL_REQUESTED, "wait", return_value=False) as wait,
        ):
            with self.assertRaisesRegex(RuntimeError, "No quedan modelos NVIDIA NIM"):
                self.run_ingest(items=[self.item, second_item])

        self.assertEqual(annotate.call_count, 4)
        self.assertEqual(
            [call.args[0] for call in annotate.call_args_list],
            [
                self.item["path"],
                self.item["path"],
                self.item["path"],
                self.item["path"],
            ],
        )
        self.assertEqual(randint.call_count, 2)
        self.assertEqual(randint.call_args_list, [unittest.mock.call(30, 120)] * 2)
        self.assertEqual(wait.call_args_list, [unittest.mock.call(73)] * 2)
        with sqlite3.connect(self.database) as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM analisis_imagen").fetchone()[0], 0)
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM prenda_imagen").fetchone()[0], 0)

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

    def test_scan_unifies_camisa_and_camiseta_as_canonical_camisa(self):
        root = self.root / "raw"
        shirt_dir = root / "train" / "shirt"
        tshirt_dir = root / "train" / "t-shirt"
        shirt_dir.mkdir(parents=True)
        tshirt_dir.mkdir(parents=True)
        Image.new("RGB", (16, 16), (40, 80, 120)).save(shirt_dir / "shirt.png")
        Image.new("RGB", (16, 16), (120, 80, 40)).save(tshirt_dir / "tshirt.png")

        items, _ = app.scan_source(root, {
            "class_map": {"shirt": "camisa", "t-shirt": "camiseta"}
        })

        self.assertEqual({item["category"] for item in items}, {"camisa"})

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
                ValueError,
                r"NIM devolvió una salida no válida en etapa colores "
                r"\(JSON malformado; finish_reason=length",
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

    def test_nemotron_vision_requests_no_reasoning_for_short_json_stages(self):
        response = SimpleNamespace(
            status_code=200,
            raise_for_status=lambda: None,
            json=lambda: {"choices": [{
                "message": {"content": '{"colores":["azul"]}'},
                "finish_reason": "stop",
            }]},
        )
        with patch.object(app, "wait_for_nim_request_slot"), patch.object(
            app.requests, "post", return_value=response
        ) as post:
            result = app.request_nim_stage_json(
                self.image_path,
                "data:image/png;base64,dGVzdA==",
                "test-secret",
                "https://test.invalid/v1",
                app.NIM_VISION_MODEL,
                "Devuelve un JSON conciso.",
                "colores",
            )

        self.assertEqual(result, {"colores": ["azul"]})
        payload = post.call_args.kwargs["json"]
        self.assertEqual(payload["model"], app.NIM_VISION_MODEL)
        self.assertEqual(payload["reasoning_effort"], "none")
        self.assertEqual(payload["response_format"], {"type": "json_object"})

    def test_nim_reports_valid_json_with_wrong_stage_shape_separately(self):
        response = SimpleNamespace(
            status_code=200,
            raise_for_status=lambda: None,
            json=lambda: {"choices": [{
                "message": {"content": '{"colores":"azul"}'},
                "finish_reason": "stop",
            }]},
        )
        with patch.object(app, "wait_for_nim_request_slot"), patch.object(
            app.requests, "post", return_value=response
        ):
            with self.assertRaisesRegex(
                ValueError,
                r"estructura JSON inesperada; finish_reason=stop",
            ):
                app.request_nim_stage_json(
                    self.image_path,
                    "data:image/png;base64,dGVzdA==",
                    "test-secret",
                    "https://test.invalid/v1",
                    "meta/llama-3.2-11b-vision-instruct",
                    "Devuelve un JSON conciso.",
                    "colores",
                )

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
                            "temporadas": ["verano"],
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
        self.assertEqual(post.call_count, 4)
        self.assertEqual(post.call_args.kwargs["json"]["response_format"]["type"], "json_object")
        prompts = [
            call.kwargs["json"]["messages"][0]["content"][0]["text"]
            for call in post.call_args_list
        ]
        self.assertIn("ETAPA 1/4 — COLORES", prompts[0])
        self.assertIn("ETAPA 2/4 — ESTILOS", prompts[1])
        self.assertIn("ETAPA 3/4 — TEMPORADAS", prompts[2])
        self.assertIn("ETAPA 4/4 — VALIDACIÓN Y DESCRIPCIÓN", prompts[3])
        self.assertEqual(result["temporadas"], ["verano"])

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
                            "estilos": ["minimalista", "formal", "casual"],
                            "temporadas": ["primavera", "verano", "invierno"],
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
        self.assertIn("máximo 8 palabras", prompts[3])
        self.assertEqual(len(result["descripcion"].split()), 8)
        self.assertEqual(result["colores"], ["azul", "rojo"])
        self.assertEqual(result["estilos"], ["minimalista", "formal"])
        self.assertEqual(result["temporadas"], ["primavera", "verano"])

    def test_nim_retries_invalid_json_per_stage_and_combines_results(self):
        contents = [
            '{"colores":["azul"',
            '{"colores":["azul","inventado"]}',
            '{"estilos":"casual"}',
            '{"estilos":["casual"]}',
            '{"temporadas":["invierno"]}',
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
        self.assertEqual(result["temporadas"], ["invierno"])
        self.assertEqual(len(payloads), 6)
        self.assertTrue(all(header == "Bearer test-secret" for header in authorization_headers))
        self.assertEqual(
            [payload["max_tokens"] for payload in payloads],
            [256, 512, 256, 512, 256, 256],
        )
        self.assertEqual(
            [
                payload["messages"][0]["content"][0]["text"].splitlines()[0]
                for payload in payloads
            ],
            [
                "ETAPA 1/4 — COLORES",
                "ETAPA 1/4 — COLORES",
                "ETAPA 2/4 — ESTILOS",
                "ETAPA 2/4 — ESTILOS",
                "ETAPA 3/4 — TEMPORADAS",
                "ETAPA 4/4 — VALIDACIÓN Y DESCRIPCIÓN",
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
                            "temporadas": [],
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
                            "temporadas": [],
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
        self.assertEqual(result["estilos"], ["casual", "formal", "deportivo"])
        payload = post.call_args.kwargs["json"]
        self.assertEqual(payload["response_format"], {"type": "json_object"})
        self.assertEqual(payload["thinking"], {"type": "disabled"})
        self.assertEqual(payload["max_tokens"], 1024)
        self.assertIn("Ejemplo de forma", payload["messages"][0]["content"][0]["text"])
        self.assertIn("máximo 12 palabras", payload["messages"][0]["content"][0]["text"])
        self.assertIn("colores (lista de máximo 3)", payload["messages"][0]["content"][0]["text"])

    def test_deepseek_accepts_new_styles_and_seasons_but_rejects_unknown_colors(self):
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
                            "estilos": ["bohemio"],
                            "temporadas": ["otoño"],
                        })
                    },
                    "finish_reason": "stop",
                }]
            },
        )
        with patch.object(app.requests, "post", return_value=response):
            result = app.annotate_image(
                self.image_path,
                "camisa",
                "deepseek",
                "test-secret",
                "https://test.invalid/v1",
                "deepseek-flash",
                ["azul"],
                ["casual"],
                seasons=["invierno"],
            )
        self.assertEqual(result["estilos"], ["bohemio"])
        self.assertEqual(result["temporadas"], ["otoño"])

        invalid_color = copy.deepcopy(response)
        invalid_color.json = lambda: {
            "choices": [{
                "message": {
                    "content": json.dumps({
                        "apta": True,
                        "motivo_descarte": "",
                        "descripcion": "Camisa azul.",
                        "colores": ["cian"],
                        "estilos": ["bohemio"],
                        "temporadas": ["otoño"],
                    })
                },
                "finish_reason": "stop",
            }]
        }
        with patch.object(app.requests, "post", return_value=invalid_color):
            with self.assertRaisesRegex(ValueError, "colores contiene valores fuera del catálogo"):
                app.annotate_image(
                    self.image_path,
                    "camisa",
                    "deepseek",
                    "test-secret",
                    "https://test.invalid/v1",
                    "deepseek-flash",
                    ["azul"],
                    ["casual"],
                    seasons=["invierno"],
                )

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
