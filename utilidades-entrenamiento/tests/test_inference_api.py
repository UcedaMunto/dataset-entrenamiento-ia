import io
import json
import socket
import threading
import time
import unittest
import urllib.error
import urllib.request
from unittest.mock import patch

import torch
import uvicorn
from PIL import Image

import inference_api as api


CHECKPOINT = {
    "classes": {
        "tipo_prenda": ["camisa", "vestido"],
        "color": ["azul", "rojo"],
        "estilo": ["casual", "elegante"],
    },
    "multilabel_threshold": 0.5,
}
OUTPUTS = {
    "type": torch.tensor([[3.0, 0.0]]),
    "color": torch.tensor([[3.0, -3.0]]),
    "style": torch.tensor([[3.0, -3.0]]),
}


class GarmentPredictionTests(unittest.TestCase):
    def test_openapi_requires_only_garment_image(self):
        schema = api.app.openapi()
        request_body = schema["paths"]["/v1/predict"]["post"]["requestBody"]
        component = request_body["content"]["multipart/form-data"]["schema"]["$ref"].rsplit("/", 1)[-1]
        fields = schema["components"]["schemas"][component]
        self.assertEqual(fields["required"], ["garment_image"])
        self.assertEqual(set(fields["properties"]), {"garment_image"})
        self.assertEqual(fields["properties"]["garment_image"]["format"], "binary")

    def test_describes_one_image_and_applies_checkpoint_threshold(self):
        result = api.describe_image_prediction(OUTPUTS, CHECKPOINT)
        self.assertEqual(result["tipo_prenda"]["valor"], "camisa")
        self.assertIn("azul", result["descripcion_mas_probable"])
        self.assertIn("casual", result["descripcion_mas_probable"])
        self.assertEqual([x["valor"] for x in result["colores"] if x["supera_umbral"]], ["azul"])
        self.assertAlmostEqual(result["tipo_prenda"]["probabilidad"], 0.952574)
        self.assertEqual(result["umbral_multietiqueta"], 0.5)
        strict = api.describe_image_prediction(OUTPUTS, {**CHECKPOINT, "multilabel_threshold": 0.99})
        self.assertIn("sin color sobre el umbral", strict["descripcion_mas_probable"])
        self.assertIn("sin estilo sobre el umbral", strict["descripcion_mas_probable"])


class GarmentHTTPTests(unittest.TestCase):
    """Real multipart requests; mock network weights so tests need no checkpoint."""

    @classmethod
    def setUpClass(cls):
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

    def request_image(self, data, name="garment_image", mime="image/png"):
        boundary = "prendas-test-boundary"
        body = (f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"; filename="test.png"\r\n'
                f'Content-Type: {mime}\r\n\r\n').encode() + data + f"\r\n--{boundary}--\r\n".encode()
        request = urllib.request.Request(self.url + "/v1/predict", data=body,
                                        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
        try:
            with urllib.request.urlopen(request, timeout=5) as response:
                return response.status, json.load(response)
        except urllib.error.HTTPError as error:
            return error.code, json.load(error)

    def test_one_upload_succeeds_and_model_receives_batch_of_one(self):
        image = io.BytesIO()
        Image.new("RGB", (16, 16), "blue").save(image, "PNG")
        with patch.object(api, "model", return_value=OUTPUTS) as model, \
                patch.object(api, "checkpoint", CHECKPOINT), \
                patch.object(api, "transform", return_value=torch.zeros(3, 224, 224)):
            status, result = self.request_image(image.getvalue())
        self.assertEqual(status, 200)
        self.assertEqual(tuple(model.call_args.args[0].shape), (1, 3, 224, 224))
        self.assertEqual(result["tipo_prenda"]["valor"], "camisa")
        self.assertIn("descripcion_mas_probable", result)
        self.assertEqual(result["device"], "cpu")
        self.assertIn("inferencia_imagen", result["latencia_ms"])
        self.assertNotIn("predicciones_por_imagen", result)

    def test_missing_garment_field_returns_422(self):
        status, _ = self.request_image(b"x", name="other_image")
        self.assertEqual(status, 422)

    def test_invalid_image_returns_422(self):
        with patch.object(api, "model", object()), patch.object(api, "checkpoint", CHECKPOINT), \
                patch.object(api, "transform", object()):
            status, _ = self.request_image(b"not an image")
        self.assertEqual(status, 422)

    def test_oversized_request_returns_413(self):
        # Lower the limit for the test; the middleware must account for one image.
        with patch.object(api, "MAX_IMAGE_BYTES", 1):
            status, _ = self.request_image(b"x" * 1_000_002)
        self.assertEqual(status, 413)

    def test_unloaded_model_returns_503(self):
        with patch.object(api, "model", None):
            status, _ = self.request_image(b"x")
        self.assertEqual(status, 503)


if __name__ == "__main__":
    unittest.main()
