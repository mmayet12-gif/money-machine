import json
import tempfile
import unittest
from pathlib import Path

from money_machine.config import load_config
from money_machine.pipeline import MoneyMachinePipeline


class FakeClient:
    def __init__(self):
        self.calls = 0

    def health_check(self):
        return True

    def generate(self, prompt: str):
        self.calls += 1
        return "Generated content"


class PipelineIntegrationTests(unittest.TestCase):
    def test_selective_stream_run_and_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            cfg_path = base / "cfg.json"
            cfg_data = {
                "model_policy": "local-ollama",
                "output_root": str(base / "runs"),
                "batch_size": 2,
                "topics_source": {"type": "inline", "inline_topics": []},
                "streams": [
                    {"id": "S1", "name": "YouTube Long-form", "enabled": True, "output_formats": ["txt"]},
                    {"id": "S2", "name": "YouTube Shorts", "enabled": True, "output_formats": ["txt"]},
                ],
            }
            cfg_path.write_text(json.dumps(cfg_data), encoding="utf-8")
            cfg = load_config(str(cfg_path))

            pipe = MoneyMachinePipeline(cfg)
            pipe.client = FakeClient()
            status = pipe.run(run_id="testrun", stream_filter=["S1"])
            self.assertEqual(status.run_id, "testrun")
            self.assertIn("S1", status.streams)
            self.assertNotIn("S2", status.streams)

            status2 = pipe.status("testrun")
            self.assertIn(status2.status, {"completed", "partial"})


if __name__ == "__main__":
    unittest.main()
