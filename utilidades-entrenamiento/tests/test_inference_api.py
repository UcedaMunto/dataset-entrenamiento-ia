import unittest

import torch

from inference_api import app, combine_image_predictions


class PairPredictionTests(unittest.TestCase):
    def test_openapi_requires_garment_and_person_images(self):
        schema = app.openapi()
        request_body = schema["paths"]["/v1/predict"]["post"]["requestBody"]
        multipart_schema = request_body["content"]["multipart/form-data"]["schema"]
        component_name = multipart_schema["$ref"].rsplit("/", 1)[-1]
        fields = schema["components"]["schemas"][component_name]

        self.assertEqual(set(fields["required"]), {"garment_image", "person_image"})
        self.assertEqual(fields["properties"]["garment_image"]["format"], "binary")
        self.assertEqual(fields["properties"]["person_image"]["format"], "binary")

    def test_combines_two_views_and_preserves_each_view_prediction(self):
        outputs = {
            "type": torch.tensor([[3.0, 0.0], [0.0, 3.0]]),
            "color": torch.tensor([[3.0, 0.0], [3.0, -3.0]]),
            "style": torch.tensor([[0.0, 3.0], [0.0, 3.0]]),
        }
        checkpoint = {
            "classes": {
                "tipo_prenda": ["camisa", "vestido"],
                "color": ["azul", "rojo"],
                "estilo": ["casual", "elegante"],
            },
            "multilabel_threshold": 0.5,
        }

        result = combine_image_predictions(outputs, checkpoint)

        self.assertEqual(result["metodo_combinacion"], "media_aritmetica_de_probabilidades")
        self.assertEqual(result["predicciones_por_imagen"]["prenda"]["tipo_prenda"]["valor"], "camisa")
        self.assertEqual(result["predicciones_por_imagen"]["persona"]["tipo_prenda"]["valor"], "vestido")
        self.assertIn("descripcion_mas_probable", result)
        self.assertIn("azul", [item["valor"] for item in result["prediccion_combinada"]["colores"]])


if __name__ == "__main__":
    unittest.main()