import json
import tempfile
import unittest
from pathlib import Path

from money_machine.config import ConfigError, load_config


class ConfigTests(unittest.TestCase):
    def test_load_minimal_config_merges_defaults(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cfg.json"
            path.write_text(json.dumps({"model_policy": "local-ollama"}), encoding="utf-8")
            cfg = load_config(str(path))
            self.assertEqual(cfg.model_policy, "local-ollama")
            self.assertTrue(any(s.enabled for s in cfg.streams))

    def test_rejects_invalid_model_policy(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cfg.json"
            path.write_text(json.dumps({"model_policy": "cloud"}), encoding="utf-8")
            with self.assertRaises(ConfigError):
                load_config(str(path))


if __name__ == "__main__":
    unittest.main()
