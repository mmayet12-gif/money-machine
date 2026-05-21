import json
import tempfile
import unittest
from pathlib import Path

from money_machine.config import load_config
from money_machine.topic_loader import load_topics


class TopicLoaderTests(unittest.TestCase):
    def test_load_topics_from_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            topics = [
                {"title": "A", "kw": "a", "hook": "h", "vol": "High", "mon": ["Ads"], "struct": ["x"]},
                {"title": "B", "kw": "b", "hook": "h", "vol": "Low", "mon": ["Affiliate"], "struct": ["x"]},
            ]
            topics_path = base / "topics.json"
            topics_path.write_text(json.dumps(topics), encoding="utf-8")
            cfg_path = base / "cfg.json"
            cfg_path.write_text(
                json.dumps(
                    {
                        "model_policy": "local-ollama",
                        "topics_source": {"type": "json", "path": str(topics_path)},
                        "batch_size": 2,
                    }
                ),
                encoding="utf-8",
            )
            cfg = load_config(str(cfg_path))
            loaded = load_topics(cfg)
            self.assertEqual(len(loaded), 2)
            self.assertEqual(loaded[0].title, "A")


if __name__ == "__main__":
    unittest.main()
