import unittest

from train import apply_continuation_strategy, validate_initial_checkpoint


class ContinuationStrategyTests(unittest.TestCase):
    def test_fine_tune_uses_lower_rates_and_fresh_schedule(self):
        config = {"epochs": 30, "learning_rate": 0.001, "pretrained": True}

        continued = apply_continuation_strategy(config, "fine_tune")

        self.assertEqual(continued["epochs"], 10)
        self.assertEqual(continued["learning_rate"], 0.0001)
        self.assertEqual(continued["finetune_lr"], 0.00001)
        self.assertEqual(continued["warmup_epochs"], 0)
        self.assertTrue(continued["finetune"])
        self.assertFalse(continued["pretrained"])
        self.assertEqual(config["epochs"], 30)

    def test_heads_only_freezes_backbone(self):
        continued = apply_continuation_strategy({}, "heads_only")

        self.assertFalse(continued["finetune"])
        self.assertEqual(continued["warmup_epochs"], 0)

    def test_rejects_unknown_strategy(self):
        with self.assertRaisesRegex(ValueError, "Estrategia de continuación"):
            apply_continuation_strategy({}, "resume_exact")

    def test_checkpoint_must_match_architecture_classes_and_resolution(self):
        checkpoint = {
            "architecture": "mobilenet_v3_small",
            "classes": {"tipo_prenda": ["camisa"]},
            "image_size": 224,
            "state_dict": {"weights": object()},
        }

        validate_initial_checkpoint(checkpoint, checkpoint["classes"], 224)
        with self.assertRaisesRegex(ValueError, "catálogo de clases"):
            validate_initial_checkpoint(checkpoint, {"tipo_prenda": ["falda"]}, 224)
        with self.assertRaisesRegex(ValueError, "resolución"):
            validate_initial_checkpoint(checkpoint, checkpoint["classes"], 160)


if __name__ == "__main__":
    unittest.main()