from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import shopee_rag_complete_v4_0_1 as backend


class _FakeResponse:
    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(
            {"message": {"content": "Phí cố định áp dụng theo ngành hàng."}}
        ).encode("utf-8")


class OllamaRuntimeConfigTests(unittest.TestCase):
    def test_chat_request_uses_bounded_direct_answer_configuration(self) -> None:
        contexts = [
            {
                "text": "Phí cố định áp dụng theo ngành hàng.",
                "metadata": {"title": "Nguồn kiểm thử", "page": "1"},
            }
        ]

        with patch.object(
            backend.request,
            "urlopen",
            return_value=_FakeResponse(),
        ) as urlopen:
            answer, _elapsed = backend.call_ollama(
                "Phí cố định là gì?",
                contexts,
            )

        request_object = urlopen.call_args.args[0]
        payload = json.loads(request_object.data.decode("utf-8"))

        self.assertTrue(answer)
        self.assertEqual(payload["think"], backend.OLLAMA_THINK)
        self.assertEqual(
            payload["options"]["num_predict"],
            backend.OLLAMA_MAX_TOKENS,
        )
        self.assertEqual(
            urlopen.call_args.kwargs["timeout"],
            backend.OLLAMA_REQUEST_TIMEOUT_SECONDS,
        )

    def test_default_runtime_limits_are_bounded_for_interactive_use(self) -> None:
        self.assertGreater(backend.OLLAMA_REQUEST_TIMEOUT_SECONDS, 0)
        self.assertLessEqual(backend.OLLAMA_REQUEST_TIMEOUT_SECONDS, 120)
        self.assertGreater(backend.OLLAMA_MAX_TOKENS, 0)


if __name__ == "__main__":
    unittest.main()
