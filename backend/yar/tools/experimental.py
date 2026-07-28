"""Opt-in experimental tools — off unless YAR_EXPERIMENTAL=1.

`delegate_task` is live: hands a coding job to pi
(https://github.com/earendil-works/pi) via headless print mode. Yar orchestrates
(memory, context, evals); pi codes. The other three boxes are honest
"coming soon" stubs — terminal/browser/cron need a real sandbox first.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from yar.config import Settings
from yar.tools.registry import Tool

PI_INSTALL_HINT = "npm install -g --ignore-scripts @earendil-works/pi-coding-agent"

# Still-skeleton boxes: name → what it will do.
PLANNED = [
    {
        "name": "run_command",
        "box": "Terminal tool",
        "description": (
            "Run a shell command in a sandbox and read the output — Hermes's "
            "'Terminal' tool. Needs a real sandbox + safety surface first."
        ),
    },
    {
        "name": "browse_web",
        "box": "Browser tool",
        "description": (
            "Open a page and read/click it — Hermes's 'Browser' tool. "
            "(search_web already covers read-only web lookups.)"
        ),
    },
    {
        "name": "schedule_task",
        "box": "Cron Job",
        "description": (
            "Let the agent schedule its own recurring runs. Today `make brief` "
            "+ a system cron line already does scheduled runs; this would move "
            "it in-app."
        ),
    },
]


def make_delegate_tool(settings: Settings) -> Tool:
    """Delegate a coding task to pi. Honest return strings for every outcome."""

    def delegate_task(task: str = "", cwd: str = "", timeout_seconds: int = 0) -> str:
        if not task.strip():
            return (
                "delegate_task needs a 'task' — a plain-English description of "
                "the coding job, e.g. 'fix the failing test in this repo'."
            )
        pi_bin = shutil.which("pi")
        if not pi_bin:
            return (
                f"pi isn't installed, so I can't delegate. "
                f"Install it with: {PI_INSTALL_HINT}"
            )

        from yar.tools import workspace

        if cwd:
            workdir = Path(cwd).expanduser()
            if not workdir.is_dir():
                return f"delegate_task: the working directory '{cwd}' doesn't exist."
            in_workspace = False
        else:
            workdir = workspace.new_run_folder(
                settings.model, task, root=settings.workspace
            )
            in_workspace = True

        # YAR_DELEGATE_TIMEOUT is a call-site knob (ARCHITECTURE §9).
        timeout = int(timeout_seconds) or int(os.getenv("YAR_DELEGATE_TIMEOUT", "300"))
        # OpenAI only — Yar has one provider. Pass the loop's model so the
        # sub-agent codes with the same brain.
        cmd = [pi_bin, "--provider", "openai"]
        if settings.model:
            cmd += ["--model", settings.model]
        if settings.api_key:
            cmd += ["--api-key", settings.api_key]
        cmd += ["-p", task, "-a", "--no-session"]
        try:
            result = subprocess.run(
                cmd,
                cwd=workdir,
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return (
                f"pi was still working after {timeout}s so I stopped it — try a "
                f"smaller task, or raise YAR_DELEGATE_TIMEOUT."
            )
        except OSError as exc:
            return f"Couldn't launch pi: {exc}"

        transcript = (
            (workdir / "pi-transcript.log")
            if in_workspace
            else (
                settings.home
                / "outbox"
                / f"delegate-{datetime.now():%Y%m%d-%H%M%S}.log"
            )
        )
        transcript.parent.mkdir(parents=True, exist_ok=True)
        # Omit api-key from the paper trail.
        safe_cmd = [
            c for i, c in enumerate(cmd) if not (i > 0 and cmd[i - 1] == "--api-key")
        ]
        transcript.write_text(
            f"$ {' '.join(safe_cmd[:-2])} -p {task!r}   (cwd: {workdir})\n\n"
            f"--- stdout ---\n{result.stdout}\n--- stderr ---\n{result.stderr}",
            encoding="utf-8",
        )

        if result.returncode != 0:
            err = (result.stderr or result.stdout).strip()[-200:] or "no output"
            return f"pi hit an error: {err} (full log: {transcript})"
        summary = result.stdout.strip()[-500:] or "(pi finished but printed nothing)"

        if not in_workspace:
            return (
                f"pi finished the delegated task in {workdir}.\n{summary}\n"
                f"(full log: {transcript})"
            )

        files = workspace.created_files(workdir)
        run = workspace.autorun(
            workdir,
            enabled=settings.delegate_autorun,
            timeout=settings.autorun_timeout,
        )
        workspace.write_manifest(
            workdir, "openai", settings.model or "(default)", task, files, run
        )
        made = ", ".join(p.name for p in files[:6]) or "no files"
        lines = [f"pi finished. Files saved to {workdir} ({made}).", summary]
        if run is not None:
            entry, code, out, secs = run
            verdict = (
                "still running (interactive)"
                if code is None
                else ("ran clean" if code == 0 else f"exited {code}")
            )
            lines.append(f"\nAuto-ran {entry}: {verdict} in {secs}s.\n{out[-400:]}")
        return "\n".join(lines)

    return Tool(
        name="delegate_task",
        description=(
            "Delegate a CODING task (fixing tests, multi-file edits, writing "
            "programs) to pi, a specialist coding agent running locally on this "
            "machine. Give it a self-contained task and, when the work targets an "
            "existing project, that project's absolute path as cwd. Use this for "
            "real programming work instead of describing code in chat."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "task": {
                    "type": "string",
                    "description": (
                        "Plain-English description of the coding job, self-contained"
                    ),
                },
                "cwd": {
                    "type": "string",
                    "description": (
                        "Absolute path of the repo/directory to work in; "
                        "omit for a scratch sandbox"
                    ),
                },
                "timeout_seconds": {
                    "type": "integer",
                    "description": "Max seconds to let pi work (default 300)",
                },
            },
            "required": ["task"],
        },
        fn=delegate_task,
    )


def _stub(name: str, description: str, box: str) -> Tool:
    def fn(**kwargs) -> str:
        return (
            f"'{name}' maps to the '{box}' box on the architecture chart and "
            f"isn't wired in yet — it's on the roadmap (coming soon). "
            f"Tell the user honestly."
        )

    return Tool(
        name=name,
        description=f"[coming soon] {description}",
        input_schema={"type": "object", "properties": {}},
        fn=fn,
    )


def make_tools(settings: Settings) -> list[Tool]:
    """Experimental tools — only registered when YAR_EXPERIMENTAL=1."""
    return [make_delegate_tool(settings)] + [
        _stub(p["name"], p["description"], p["box"]) for p in PLANNED
    ]
