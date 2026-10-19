import unittest

import torch

from evaluate_properties import macro_property_average, summarize_multilabel, summarize_types


class PropertyMetricTests(unittest.TestCase):
    def test_macro_average_gives_equal_weight_to_three_properties(self):
        result = macro_property_average(94.94, 68.42, 69.21)

        self.assertEqual(result["porcentaje"], 77.52)
        self.assertEqual(len(result["componentes_pct"]), 3)

    def test_multilabel_exact_match_and_micro_metrics(self):
        expected = torch.tensor([[True, False], [False, True], [True, True]])
        predicted = torch.tensor([[True, False], [False, True], [False, True]])

        result = summarize_multilabel(predicted, expected, ["azul", "rojo"])

        self.assertEqual(result["coincidencia_exacta"], {
            "correctas": 2, "total": 3, "porcentaje": 66.67,
        })
        self.assertEqual(result["coincidencia_parcial_jaccard_pct"], 83.33)
        self.assertEqual(result["micro_precision_pct"], 100.0)
        self.assertEqual(result["micro_recall_pct"], 75.0)

    def test_type_accuracy_reports_correct_count_and_percent(self):
        confusion = torch.tensor([[2, 1], [0, 1]])

        result = summarize_types(confusion, ["camisa", "vestido"])

        self.assertEqual(result["correctas"], 3)
        self.assertEqual(result["total"], 4)
        self.assertEqual(result["accuracy_pct"], 75.0)


if __name__ == "__main__":
    unittest.main()