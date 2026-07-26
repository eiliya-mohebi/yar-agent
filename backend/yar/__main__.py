"""Entrypoint — installed as the `yar` command (and `python -m yar`).

Subcommands (dashboard, brief, skill install) land in later tickets.
This ticket only guarantees: package importable, config loaded, clear key failure.
"""

from __future__ import annotations

import sys

from yar.config import load_settings


def main() -> None:
    # Gate the process early: no silent mock when the key is missing.
    load_settings().require_api_key()
    print(
        "Yar package skeleton is ready (config + text). "
        "CLI gateway is not wired yet.",
        file=sys.stderr,
    )
    sys.exit(2)


if __name__ == "__main__":
    main()
