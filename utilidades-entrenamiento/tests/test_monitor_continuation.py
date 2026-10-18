import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import monitor
from monitor import continuation_command


class MonitorContinuationTests(unittest.TestCase):
    def test_builds_command_for_selected_checkpoint_and_strategy(self):
        run_id = "20261018-020637"
        with tempfile.TemporaryDirectory() as temporary_directory:
            checkpoint = Path(temporary_directory) / "runs" / run_id / "best.pt"
            checkpoint.parent.mkdir(parents=True)
            checkpoint.write_bytes(b"checkpoint")

            command = continuation_command(run_id, "fine_tune", Path(temporary_directory))

        self.assertEqual(command[-4:], ["--continue-from", run_id, "--strategy", "fine_tune"])

    def test_rejects_run_ids_that_could_escape_model_directory(self):
        with self.assertRaisesRegex(ValueError, "ID de ejecución"):
            continuation_command("../../outside", "fine_tune", Path("/tmp"))

    def test_rejects_missing_checkpoint(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            with self.assertRaisesRegex(FileNotFoundError, "no tiene un mejor checkpoint"):
                continuation_command("20261018-020637", "fine_tune", Path(temporary_directory))

    def test_rejects_unknown_strategy(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            with self.assertRaisesRegex(ValueError, "estrategia"):
                continuation_command("20261018-020637", "unknown", Path(temporary_directory))

    def test_start_training_launches_the_selected_continuation(self):
        run_id = "20261018-020637"
        with tempfile.TemporaryDirectory() as temporary_directory:
            model_dir = Path(temporary_directory)
            checkpoint = model_dir / "runs" / run_id / "best.pt"
            checkpoint.parent.mkdir(parents=True)
            checkpoint.write_bytes(b"checkpoint")
            process = Mock()
            process.poll.return_value = None

            with (
                patch.object(monitor, "MODEL_DIR", model_dir),
                patch.object(monitor, "LOG_PATH", model_dir / "training.log"),
                patch.object(monitor.subprocess, "Popen", return_value=process) as popen,
            ):
                monitor._process = None
                status, body = monitor.start_training(run_id, "heads_only")
                command = popen.call_args.args[0]
                monitor._process = None

        self.assertEqual(status, 200)
        self.assertEqual(body, {"ok": True})
        self.assertEqual(command[-4:], ["--continue-from", run_id, "--strategy", "heads_only"])


if __name__ == "__main__":
    unittest.main()