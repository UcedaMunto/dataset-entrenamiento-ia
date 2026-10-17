import base64
import hashlib
import json
import os
import sqlite3
import tempfile
import unittest
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

    def run_ingest(self, provider="nim"):
        args = SimpleNamespace(
            limit=1,
            provider=provider,
            execute=True,
            allow_remote=True,
        )
        with (
            patch.object(app, "ROOT", self.root),
            patch.object(app, "ensure_database"),
            patch.object(app, "scan_source", return_value=([self.item], {
                "images": 1, "mapped": 1, "unmapped": 0, "oversize": 0,
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
        prompt = app.build_prompt(
            app.DEFAULT_PROMPT_INSTRUCTIONS, "camisa", ["azul"], ["casual"]
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
        prompt = app.build_prompt(
            app.DEFAULT_PROMPT_INSTRUCTIONS, "camisa", ["azul"], ["casual"]
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


if __name__ == "__main__":
    unittest.main()
