"""Punto de entrada: interfaz gráfica o daemon."""

from __future__ import annotations

import argparse
import asyncio
import sys


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Controla un enchufe Tapo según la batería del portátil."
    )
    parser.add_argument(
        "--daemon",
        action="store_true",
        help="Ejecuta en segundo plano, sin ventana (Windows y Linux).",
    )
    args = parser.parse_args()

    if args.daemon:
        from tapo_battery_guard.daemon import run_daemon

        asyncio.run(run_daemon())
        return

    try:
        from tapo_battery_guard.app import run_gui
    except ModuleNotFoundError as exc:
        missing = str(exc).lower()
        if "tkinter" in missing or "tk" in missing:
            print(
                "Falta Tkinter para la ventana.\n"
                "Ubuntu/Debian: sudo apt install python3-tk\n"
                "Fedora: sudo dnf install python3-tkinter\n"
                "Windows: reinstala Python marcando tcl/tk.",
                file=sys.stderr,
            )
            raise SystemExit(1) from exc
        raise

    run_gui()


if __name__ == "__main__":
    main()
