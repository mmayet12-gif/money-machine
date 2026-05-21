from __future__ import annotations

import json
import socket
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Dict

from .config import OllamaConfig


class OllamaError(RuntimeError):
    pass


@dataclass
class OllamaClient:
    config: OllamaConfig

    def _post(self, payload: Dict[str, object]) -> Dict[str, object]:
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url=f"{self.config.base_url}/api/generate",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        timeout = max(self.config.timeouts.connect_seconds, self.config.timeouts.read_seconds)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                text = response.read().decode("utf-8")
                return json.loads(text)
        except urllib.error.URLError as exc:
            reason = getattr(exc, "reason", exc)
            raise OllamaError(f"Ollama request failed: {reason}") from exc
        except socket.timeout as exc:
            raise OllamaError("Ollama request timed out.") from exc
        except json.JSONDecodeError as exc:
            raise OllamaError("Ollama returned invalid JSON.") from exc

    def health_check(self) -> bool:
        try:
            data = self._post(
                {"model": self.config.model, "prompt": "Say READY", "stream": False}
            )
        except OllamaError:
            return False
        return "response" in data

    def generate(self, prompt: str) -> str:
        attempts = self.config.max_retries + 1
        last_error = ""
        for _ in range(attempts):
            try:
                data = self._post(
                    {
                        "model": self.config.model,
                        "prompt": prompt,
                        "stream": False,
                    }
                )
                response = data.get("response", "")
                if not isinstance(response, str) or not response.strip():
                    raise OllamaError("Ollama returned an empty response.")
                return response
            except OllamaError as exc:
                last_error = str(exc)
        raise OllamaError(last_error or "Unknown Ollama error.")
