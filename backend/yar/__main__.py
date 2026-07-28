"""Entrypoint — installed as the `yar` command (and `python -m yar`):

  yar                       chat in the terminal (default)
  yar dashboard             the browser cockpit → localhost:7777
  yar brief                 morning briefing (calendar + memory)
  yar skill install <url>   install a community skill
"""

from __future__ import annotations

import sys


def main(argv: list[str] | None = None) -> None:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        from yar.gateway.cli import main as cli_main

        cli_main()
    elif args[0] == "dashboard":
        from yar.ops.dashboard import main as dashboard_main

        dashboard_main()
    elif args[0] == "brief":
        from yar.ops.brief import main as brief_main

        brief_main()
    elif args[0] == "skill" and len(args) >= 3 and args[1] == "install":
        from yar.memory.procedural.installer import install

        install(args[2])
    else:
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
