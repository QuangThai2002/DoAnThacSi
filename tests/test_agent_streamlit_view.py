from __future__ import annotations

import sys
import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest


SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


class AgentStreamlitViewTests(unittest.TestCase):
    def test_clear_removes_messages_and_previous_suggestion(self) -> None:
        """The Agent clear action must not resubmit a selected suggestion."""
        app = AppTest.from_file(SRC_DIR / "agent_demo.py", default_timeout=30).run()

        app.pills(key="agent_suggestion").select("Cảnh báo tồn kho").run()
        self.assertEqual(len(app.chat_message), 2)

        app.button(key="clear_agent_chat").click().run()

        self.assertEqual(len(app.chat_message), 0)
        self.assertEqual(app.session_state["agent_messages"], [])
        self.assertIsNone(app.pills(key="agent_suggestion").value)
        self.assertEqual(len(app.error), 0)


if __name__ == "__main__":
    unittest.main()
