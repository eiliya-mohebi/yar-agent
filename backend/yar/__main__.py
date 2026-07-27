"""Entrypoint — installed as the `yar` command (and `python -m yar`).

Subcommands: `yar dashboard` starts the local API on :7777.
CLI chat gateway lands in a later ticket.
"""

from __future__ import annotations

import sys

from yar.config import load_settings


def main(argv: list[str] | None = None) -> None:
    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] == "dashboard":
        from yar.ops.dashboard import main as dashboard_main

        dashboard_main()
        return

    # Gate the process early: no silent mock when the key is missing.
    load_settings().require_api_key()
    print(
        "Yar package is ready. Try: uv run yar dashboard",
        file=sys.stderr,
    )
    sys.exit(2)


if __name__ == "__main__":
    main()
