"""Release gate — the diamond before "Release" on the whiteboard.

Changed the prompt? Swapped the model? Tuned retrieval top-k? Run the gate:

    python -m yar.ops.release_gate     (or: make gate)

Deterministic evals must pass 100% — they are unit tests; one failure blocks.
Judge evals run when a key is present and report scores. Exit code 0 = ship.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()  # the key check below must see .env, same as the app does

REPO = Path(__file__).resolve().parents[2]


def run(suite: str) -> tuple[int, dict]:
    """Run a pytest suite; return (exit_code, {passed, failed}). Counts come
    from the -q summary line — zero extra deps; 0/0 on a miss is honest."""
    print(f"\n=== {suite} ===")
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", str(REPO / "evals" / suite)],
        cwd=REPO,
        capture_output=True,
        text=True,
    )
    print(proc.stdout, end="")
    print(proc.stderr, end="", file=sys.stderr)
    counts = {
        k: (int(m.group(1)) if (m := re.search(rf"(\d+) {k}", proc.stdout)) else 0)
        for k in ("passed", "failed")
    }
    return proc.returncode, counts


def report(deterministic: str, judge: str, suites: dict | None = None) -> None:
    """Persist the latest verdict AND append it to the run history."""
    from yar.config import load_settings

    settings = load_settings()
    settings.ensure_home()
    record = {
        "deterministic": deterministic,
        "judge": judge,
        "suites": suites or {},
        "ran_at": datetime.now(UTC).isoformat(timespec="seconds"),
    }
    (settings.home / "eval_report.json").write_text(
        json.dumps(record), encoding="utf-8"
    )
    with (settings.home / "eval_runs.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


def main() -> None:
    suites: dict = {}
    code, suites["deterministic"] = run("deterministic")
    if code:
        report("fail", "not run", suites)
        print("\nGATE CLOSED — deterministic evals failed. Fix before releasing.")
        sys.exit(1)

    from yar.config import load_settings

    settings = load_settings()
    if settings.api_key.strip():
        code, suites["judge"] = run("judge")
        if code:
            report("pass", "fail", suites)
            print("\nGATE CLOSED — judge scores below threshold.")
            sys.exit(1)
        report("pass", "pass", suites)
    else:
        report("pass", "skipped", suites)
        print("\n(judge suite skipped: no OPENAI_API_KEY / YAR_API_KEY)")

    print("\nGATE OPEN — safe to release.")


if __name__ == "__main__":
    main()
