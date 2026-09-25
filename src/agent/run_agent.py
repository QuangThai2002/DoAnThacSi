from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


SRC_DIR = Path(__file__).resolve().parents[1]
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from agent.agent_runner import AgentRunner  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the traceable thesis Agent baseline.")
    parser.add_argument("question", nargs="+", help="Vietnamese question for the Agent")
    parser.add_argument("--json", action="store_true", help="Print the full trace as JSON")
    args = parser.parse_args()

    result = AgentRunner().run(" ".join(args.question))
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    print(result["answer"])
    print("\nTrace:")
    print(json.dumps(result["plan"], ensure_ascii=False, indent=2))
    print(f"Tools executed: {', '.join(step['tool'] for step in result['trace'])}")


if __name__ == "__main__":
    main()
