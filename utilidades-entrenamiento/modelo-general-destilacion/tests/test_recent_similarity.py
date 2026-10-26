import hashlib
import io
import json
import os
import sqlite3
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from PIL import Image, ImageDraw

import app
import test_app


class RecentSimilarityTests(unittest.TestCase):
    setUp = test_app.CurationPipelineTests.setUp
    tearDown = test_app.CurationPipelineTests.tearDown
    run_ingest = test_app.CurationPipelineTests.run_ingest

    def make_item(self, name, color, size=(16, 16)):
        path = self.root / name
        Image.new("RGB", size, color).save(path)
        return {**self.item, "path": path, "relative_path": Path("train/camisa") / name,
                "digest": hashlib.sha256(path.read_bytes()).hexdigest()}

    @staticmethod
    def annotation():
        return {"apta": True, "motivo_descarte": "", "descripcion": "Camisa.",
                "colores": ["azul"], "estilos": ["casual"]}

    def test_skips_similar_without_consuming_limit_and_continues(self):
        similar = self.make_item("near-copy.png", (21, 61, 141), (32, 32))
        different = self.make_item("different.png", (150, 20, 40))
        output = io.StringIO()
        with patch.object(app, "annotate_image", return_value=self.annotation()) as annotate, redirect_stdout(output):
            self.run_ingest(items=[self.item, similar, different], limit=2)
        self.assertEqual([call.args[0] for call in annotate.call_args_list],
                         [self.item["path"], different["path"]])
        self.assertIn("similares omitidas antes de IA: 1", output.getvalue())
        with sqlite3.connect(self.database) as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM prenda").fetchone()[0], 2)
            self.assertIsNone(connection.execute("SELECT 1 FROM analisis_imagen WHERE sha256=?", (similar["digest"],)).fetchone())
        self.assertTrue(similar["path"].is_file())

    def test_history_survives_batches_and_is_separate_by_provider(self):
        similar = self.make_item("next-batch-copy.png", (22, 62, 142))
        with patch.object(app, "annotate_image", return_value=self.annotation()) as annotate:
            self.run_ingest(provider="deepseek")
            self.run_ingest(provider="deepseek", items=[similar])
            self.assertEqual(annotate.call_count, 1)
            self.run_ingest(provider="nim", items=[similar])
        self.assertEqual(annotate.call_count, 2)

    def test_failed_remote_result_stays_in_recent_history(self):
        similar = self.make_item("after-timeout.png", (21, 60, 140))
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "", "NVIDIA_NIM_API_KEY": ""}), \
                patch.object(app, "annotate_with_provider_fallback", return_value=(None, "nim", "test-model", 1)) as annotate:
            self.run_ingest(items=[self.item, similar], limit=2)
        annotate.assert_called_once()
        with sqlite3.connect(self.database) as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM analisis_imagen").fetchone()[0], 0)

    def test_window_keeps_ten_sends_not_ten_candidates(self):
        with sqlite3.connect(self.database) as connection:
            first = app.recent_image_signature(self.image_path, self.digest, "first")
            self.assertIsNone(app.reserve_recent_image(connection, "nim", first))
            for _ in range(15):
                self.assertEqual(app.reserve_recent_image(connection, "nim", first), "first")
            for i in range(10):
                item = self.make_item(f"window-{i}.png", ((i % 4) * 60, (i // 4) * 80, 240))
                signature = app.recent_image_signature(item["path"], item["digest"], str(i))
                self.assertIsNone(app.reserve_recent_image(connection, "nim", signature))
            history = json.loads(app.get_setting(connection, app.RECENT_IMAGE_HISTORY_PREFIX + "nim", "[]"))
            self.assertEqual(len(history), 10)
            self.assertNotIn(self.digest, [item["digest"] for item in history])
            self.assertIsNone(app.reserve_recent_image(connection, "nim", first))

    def test_different_colors_with_same_grayscale_shape_are_preserved(self):
        blue = app.recent_image_signature(self.image_path, self.digest, "blue")
        item = self.make_item("red.png", (140, 60, 20))
        red = app.recent_image_signature(item["path"], item["digest"], "red")
        self.assertEqual(blue["dhash"], red["dhash"])
        self.assertFalse(app.recent_images_are_similar(blue, red))

    def test_different_shape_or_aspect_is_preserved(self):
        first = app.recent_image_signature(self.image_path, self.digest, "first")
        item = self.make_item("wide.png", (20, 60, 140), (32, 16))
        aspect = app.recent_image_signature(item["path"], item["digest"], "wide")
        self.assertFalse(app.recent_images_are_similar(first, aspect))
        shape = {**first, "digest": "different", "dhash": "ffffffffffffffff"}
        self.assertFalse(app.recent_images_are_similar(first, shape))

    def test_recompressed_resized_photo_is_skipped_but_local_color_change_is_not(self):
        original = Image.new("RGB", (128, 128), "white")
        ImageDraw.Draw(original).rectangle((32, 16, 96, 112), fill=(20, 60, 140))
        original_path = self.root / "original.png"
        original.save(original_path)
        compressed_path = self.root / "compressed.jpg"
        original.resize((256, 256), Image.Resampling.LANCZOS).save(compressed_path, quality=90)
        changed_path = self.root / "changed.png"
        changed = original.copy()
        ImageDraw.Draw(changed).rectangle((40, 32, 88, 96), fill=(140, 60, 20))
        changed.save(changed_path)
        signatures = [app.recent_image_signature(p, hashlib.sha256(p.read_bytes()).hexdigest(), p.name)
                      for p in (original_path, compressed_path, changed_path)]
        self.assertTrue(app.recent_images_are_similar(signatures[0], signatures[1]))
        self.assertFalse(app.recent_images_are_similar(signatures[0], signatures[2]))

    def test_cached_analysis_is_reused_without_reserving_another_send(self):
        fingerprint = app.analysis_fingerprint(
            self.digest, "camisa", "nim", "test-model",
            app.build_annotation_prompt(app.DEFAULT_PROMPT_INSTRUCTIONS, "camisa", ["azul"], ["casual"], "nim", ["invierno"]),
        )
        with sqlite3.connect(self.database) as connection:
            app.save_analysis(connection, fingerprint, self.item, "nim", "test-model", self.annotation())
        with patch.object(app, "reserve_recent_image") as reserve, patch.object(app, "annotate_image") as annotate:
            self.run_ingest()
        reserve.assert_not_called()
        annotate.assert_not_called()

    def test_concurrent_reservations_do_not_send_the_same_visual_candidate_twice(self):
        similar = self.make_item("concurrent-copy.png", (21, 61, 141))
        signatures = [app.recent_image_signature(item["path"], item["digest"], str(index))
                      for index, item in enumerate((self.item, similar))]
        def reserve(signature):
            with sqlite3.connect(self.database, timeout=5) as connection:
                return app.reserve_recent_image(connection, "nim", signature)
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(reserve, signatures))
        self.assertEqual(results.count(None), 1)
        with sqlite3.connect(self.database) as connection:
            self.assertEqual(len(json.loads(app.get_setting(connection, app.RECENT_IMAGE_HISTORY_PREFIX + "nim", "[]"))), 1)

    def test_local_import_does_not_apply_remote_filter(self):
        similar = self.make_item("local-copy.png", (21, 61, 141))
        with patch.object(app, "reserve_recent_image") as reserve, patch.object(app, "annotate_image") as annotate:
            self.run_ingest(provider="none", items=[self.item, similar])
        reserve.assert_not_called()
        annotate.assert_not_called()
        with sqlite3.connect(self.database) as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM prenda").fetchone()[0], 2)

    def test_unreadable_candidate_does_not_consume_limit(self):
        bad = {**self.item, "path": self.root / "bad.png", "digest": "bad", "relative_path": Path("bad.png")}
        bad["path"].write_bytes(b"invalid image")
        with patch.object(app, "annotate_image", return_value=self.annotation()) as annotate:
            self.run_ingest(items=[bad, self.item], limit=1)
        annotate.assert_called_once()
        self.assertEqual(annotate.call_args.args[0], self.image_path)
