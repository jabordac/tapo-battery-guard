"""Lectura de batería multiplataforma (Windows y Linux)."""

from __future__ import annotations

from dataclasses import dataclass

import psutil


@dataclass(frozen=True)
class BatteryStatus:
    percent: int
    charging: bool
    present: bool
    message: str = ""


def read_battery() -> BatteryStatus:
    """Devuelve el estado actual de la batería del equipo."""
    info = psutil.sensors_battery()
    if info is None:
        return BatteryStatus(
            percent=0,
            charging=False,
            present=False,
            message="No se detectó una batería. ¿Es un portátil?",
        )

    percent = max(0, min(100, round(info.percent)))
    charging = bool(info.power_plugged)
    return BatteryStatus(percent=percent, charging=charging, present=True)
