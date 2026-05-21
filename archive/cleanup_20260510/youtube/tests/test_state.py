import tempfile
import unittest
from pathlib import Path

from money_machine.state import StreamState


class StateTests(unittest.TestCase):
    def test_checkpoint_progress(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            state = StreamState(base / "progress.json", base / "manifest.jsonl")
            state.mark_completed("u1", total_units=3)
            state.mark_failed("u2", total_units=3)
            progress = state.load_progress()
            self.assertEqual(progress["completed"], ["u1"])
            self.assertEqual(progress["failed"], ["u2"])


if __name__ == "__main__":
    unittest.main()
