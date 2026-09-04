"""Reglas de carga y bucle de automatización."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from tapo_battery_guard.battery import BatteryStatus, read_battery
from tapo_battery_guard.config import AppConfig
from tapo_battery_guard.tapo_client import TapoClient


class PlugAction(str, Enum):
    ON = "on"
    OFF = "off"
    HOLD = "hold"


@dataclass(frozen=True)
class ControllerSnapshot:
    battery: BatteryStatus
    plug_on: bool | None
    action: PlugAction
    message: str


def decide_action(percent: int, plug_on: bool, min_percent: int, max_percent: int) -> PlugAction:
    """Enciende por debajo del mínimo y apaga al llegar al máximo."""
    if percent <= min_percent and not plug_on:
        return PlugAction.ON
    if percent >= max_percent and plug_on:
        return PlugAction.OFF
    return PlugAction.HOLD


class ChargeController:
    def __init__(self, client: TapoClient) -> None:
        self.client = client

    async def tick(self, config: AppConfig) -> ControllerSnapshot:
        battery = read_battery()
        if not battery.present:
            return ControllerSnapshot(
                battery=battery,
                plug_on=None,
                action=PlugAction.HOLD,
                message=battery.message,
            )

        if not self.client.connected:
            return ControllerSnapshot(
                battery=battery,
                plug_on=None,
                action=PlugAction.HOLD,
                message="Enchufe desconectado.",
            )

        plug_on = await self.client.is_on()
        if not config.automation_enabled:
            state = "encendido" if plug_on else "apagado"
            return ControllerSnapshot(
                battery=battery,
                plug_on=plug_on,
                action=PlugAction.HOLD,
                message=f"Automatización en pausa. Enchufe {state}.",
            )

        action = decide_action(
            battery.percent,
            plug_on,
            config.min_percent,
            config.max_percent,
        )
        if action is PlugAction.ON:
            await self.client.turn_on()
            return ControllerSnapshot(
                battery=battery,
                plug_on=True,
                action=action,
                message=f"Batería al {battery.percent}%. Encendiendo el enchufe.",
            )
        if action is PlugAction.OFF:
            await self.client.turn_off()
            return ControllerSnapshot(
                battery=battery,
                plug_on=False,
                action=action,
                message=f"Batería al {battery.percent}%. Apagando el enchufe.",
            )

        state = "encendido" if plug_on else "apagado"
        return ControllerSnapshot(
            battery=battery,
            plug_on=plug_on,
            action=action,
            message=f"Batería al {battery.percent}%. Enchufe {state}.",
        )
