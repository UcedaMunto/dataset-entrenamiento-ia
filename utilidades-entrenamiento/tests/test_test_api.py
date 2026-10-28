import io
import json
import socket
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest.mock import patch

import torch
import uvicorn
from PIL import Image

import test_api as api


CHECKPOINT = {
    "classes": {
        "tipo_prenda": ["camisa", "vestido"],
        "color": ["azul", "rojo"],
        "estilo": ["casual", "elegante"],
    },
    "multilabel_threshold": 0.5,
    "image_size": 224,
    "epoch": 1,
}


class FakeModel:
    def __init__(self, outputs):
        self.outputs = list(outputs)

    def __call__(self, tensor):
        return self.outputs.pop(0)


def make_manifest(root: Path) -> dict:
    images = [
        {"archivo": "a.jpg", "codigo": "a", "tipo_prenda": "camisa",
         "colores": ["azul"], "estilos": ["casual"]},
        {"archivo": "b.jpg", "codigo": "b", "tipo_prenda": "vestido",
         "colores": ["rojo"], "estilos": ["elegante"]},
        {"archivo": "c.jpg", "codigo": "c", "tipo_prenda": "camisa",
         "colores": ["azul", "rojo"], "estilos": ["casual", "elegante"]},
    ]
    for entry in images:
        image = Image.new("RGB", (16, 16), "blue")
        image.save(root / entry["archivo"])
    manifest = {
        "classes": CHECKPOINT["classes"],
        "umbral_multietiqueta": 0.5,
        "image_size": 224,
        "imagenes": images,
    }
    (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return manifest


def fake_outputs():
    # img a: camisa, azul, casual (todo correcto)
    # img b: vestido, rojo, elegante (todo correcto)
    # img c: camisa, azul, casual (color y estilo parciales)
    return [
        {
            "type": torch.tensor([[3.0, -3.0]]),
            "color": torch.tensor([[3.0, -3.0]]),
            "style": torch.tensor([[3.0, -3.0]]),
        },
        {
            "type": torch.tensor([[-3.0, 3.0]]),
            "color": torch.tensor([[-3.0, 3.0]]),
            "style": torch.tensor([[-3.0, 3.0]]),
        },
        {
            "type": torch.tensor([[3.0, -3.0]]),
            "color": torch.tensor([[3.0, -3.0]]),
            "style": torch.tensor([[3.0, -3.0]]),
        },
    ]


class HelpersTests(unittest.TestCase):
    def test_binarize_marks_only_present_labels(self):
        result = api.binarize(["azul"], ["azul", "rojo"])
        self.assertEqual(result.dtype, torch.bool)
        self.assertEqual(result.tolist(), [True, False])

    def test_design_summary_contains_dsr_phases(self):
        summary = api.design_summary()
        self.assertEqual(summary["metodologia"], "Design Science Research (DSR)")
        self.assertEqual(len(summary["fases"]), 6)
        self.assertAlmostEqual(summary["resultado_esperado"]["promedio_macro_pct"], 77.52)


class RunEvaluationTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.manifest = make_manifest(self.root)

    def tearDown(self):
        self.tempdir.cleanup()

    def test_run_evaluation_computes_report_metrics(self):
        with patch.object(api, "TEST_IMAGES_ROOT", self.root), \
                patch.object(api, "MANIFEST_PATH", self.root / "manifest.json"), \
                patch.object(api, "RESULTS_DIR", self.root / "resultados"), \
                patch.object(api, "CHECKPOINT_PATH", Path("/tmp/best.pt")), \
                patch.object(api, "checkpoint", CHECKPOINT), \
                patch.object(api, "manifest", self.manifest), \
                patch.object(api, "checkpoint_sha256", return_value="abc123"), \
                patch.object(api, "model", FakeModel(fake_outputs())), \
                patch.object(api, "transform", lambda image: torch.zeros(3, 224, 224)):
            report = api.run_evaluation("cpu", max_images=None)

        self.assertEqual(report["imagenes_evaluadas"], 3)
        self.assertEqual(report["tipo_prenda"]["accuracy_pct"], 100.0)
        self.assertEqual(report["color"]["coincidencia_exacta"]["porcentaje"], 66.67)
        self.assertEqual(report["color"]["coincidencia_parcial_jaccard_pct"], 83.33)
        self.assertEqual(report["estilo"]["coincidencia_parcial_jaccard_pct"], 83.33)
        self.assertEqual(report["promedio_macro_propiedades"]["porcentaje"], 88.89)


class HTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tempdir = tempfile.TemporaryDirectory()
        cls.root = Path(cls.tempdir.name)
        cls.manifest = make_manifest(cls.root)
        cls.socket = socket.socket()
        cls.socket.bind(("127.0.0.1", 0))
        cls.url = f"http://127.0.0.1:{cls.socket.getsockname()[1]}"
        cls.server = uvicorn.Server(uvicorn.Config(api.app, lifespan="off", log_level="error"))
        cls.thread = threading.Thread(target=cls.server.run, kwargs={"sockets": [cls.socket]}, daemon=True)
        cls.thread.start()
        deadline = time.monotonic() + 5
        while not cls.server.started and cls.thread.is_alive() and time.monotonic() < deadline:
            time.sleep(0.01)
        if not cls.server.started:
            raise RuntimeError("No se pudo iniciar el servidor HTTP temporal.")

    @classmethod
    def tearDownClass(cls):
        cls.server.should_exit = True
        cls.thread.join(timeout=5)
        cls.socket.close()
        cls.tempdir.cleanup()

    def setUp(self):
        self.results_dir = self.root / "resultados" / self._testMethodName
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.patches = (
            patch.object(api, "TEST_IMAGES_ROOT", self.root),
            patch.object(api, "MANIFEST_PATH", self.root / "manifest.json"),
            patch.object(api, "RESULTS_DIR", self.results_dir),
            patch.object(api, "CHECKPOINT_PATH", Path("/tmp/best.pt")),
            patch.object(api, "DESIGN_DOC_PATH", self.root / "design.md"),
            patch.object(api, "checkpoint", CHECKPOINT),
            patch.object(api, "checkpoint_sha256", return_value="abc123"),
            patch.object(api, "model", FakeModel(fake_outputs())),
            patch.object(api, "transform", lambda image: torch.zeros(3, 224, 224)),
            patch.object(api, "manifest", self.manifest),
        )
        for patcher in self.patches:
            patcher.start()

    def tearDown(self):
        for patcher in reversed(self.patches):
            patcher.stop()

    def get_json(self, path):
        with urllib.request.urlopen(self.url + path, timeout=5) as response:
            return response.status, json.load(response)

    def test_health_reports_manifest_total(self):
        status, body = self.get_json("/health")
        self.assertEqual(status, 200)
        self.assertEqual(body["status"], "ok")
        self.assertEqual(body["test_manifest"]["total_imagenes"], 3)

    def test_design_endpoint(self):
        status, body = self.get_json("/test/design")
        self.assertEqual(status, 200)
        self.assertEqual(body["metodologia"], "Design Science Research (DSR)")

    def test_manifest_summary(self):
        status, body = self.get_json("/test/manifest")
        self.assertEqual(status, 200)
        self.assertEqual(body["total_imagenes"], 3)
        self.assertEqual(body["imagenes_por_tipo"], {"camisa": 2, "vestido": 1})

    def test_run_and_list_results(self):
        with urllib.request.urlopen(self.url + "/test/run", data=b"", timeout=10) as response:
            status = response.status
            report = json.load(response)
        self.assertEqual(status, 200)
        self.assertEqual(report["promedio_macro_propiedades"]["porcentaje"], 88.89)
        self.assertIn("run_id", report)

        status, listing = self.get_json("/test/results")
        self.assertEqual(status, 200)
        self.assertEqual(len(listing["resultados"]), 1)
        run_id = listing["resultados"][0]["run_id"]

        status, saved = self.get_json(f"/test/results/{run_id}")
        self.assertEqual(status, 200)
        self.assertEqual(saved["imagenes_evaluadas"], 3)

    def test_informe_endpoint_combines_annex_data(self):
        with urllib.request.urlopen(self.url + "/test/run", data=b"", timeout=10) as response:
            json.load(response)
        status, body = self.get_json("/test/informe")
        self.assertEqual(status, 200)
        self.assertEqual(body["tipo"], "evidencia_informe_anexo_g")
        self.assertEqual(body["requisito_R11"]["umbral_pct"], 70.0)
        self.assertEqual(body["metodologia"], "Design Science Research Methodology (DSRM)")
        self.assertEqual(len(body["correspondencia_dsrm"]), 6)
        self.assertIn("definiciones_operacionales", body)
        self.assertIn("condiciones_de_control", body)
        self.assertIn("conjunto_de_prueba", body)
        self.assertGreaterEqual(len(body["matriz_comparativa"]), 1)
        self.assertEqual(body["ultimo_resultado"]["promedio_macro_propiedades"]["porcentaje"], 88.89)

    def test_unloaded_model_returns_503(self):
        with patch.object(api, "model", None):
            try:
                urllib.request.urlopen(self.url + "/test/run", data=b"", timeout=5)
            except urllib.error.HTTPError as error:
                self.assertEqual(error.code, 503)
            else:
                self.fail("Se esperaba un 503 con el modelo no cargado.")


if __name__ == "__main__":
    unittest.main()
