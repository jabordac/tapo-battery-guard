"""Cliente local para enchufes Tapo (P110M, P125M, P100, etc.)."""

from __future__ import annotations

from dataclasses import dataclass

from kasa import Credentials, Device, DeviceConfig, Discover
from kasa.deviceconfig import DeviceConnectionParameters, DeviceEncryptionType, DeviceFamily


@dataclass(frozen=True)
class DiscoveredPlug:
    host: str
    alias: str
    model: str


class TapoClient:
    def __init__(self) -> None:
        self._device: Device | None = None

    @property
    def connected(self) -> bool:
        return self._device is not None

    @property
    def model(self) -> str:
        if self._device is None:
            return ""
        return str(getattr(self._device, "model", "") or "")

    @property
    def alias(self) -> str:
        if self._device is None:
            return ""
        return str(getattr(self._device, "alias", "") or "")

    async def connect(self, host: str, username: str, password: str) -> None:
        host = host.strip()
        credentials = Credentials(username.strip(), password)
        device = await self._open_device(host, credentials)
        await device.update()
        self._device = device

    async def _open_device(self, host: str, credentials: Credentials) -> Device:
        try:
            device = await Discover.discover_single(
                host,
                credentials=credentials,
                timeout=8,
                discovery_timeout=8,
            )
            if device is not None:
                return device
        except Exception:
            pass

        config = DeviceConfig(
            host=host,
            credentials=credentials,
            timeout=8,
            connection_type=DeviceConnectionParameters(
                DeviceFamily.SmartTapoPlug,
                DeviceEncryptionType.Klap,
                login_version=2,
            ),
        )
        return await Device.connect(config=config)

    async def disconnect(self) -> None:
        device = self._device
        self._device = None
        if device is None:
            return
        closer = getattr(device, "disconnect", None)
        if closer is None:
            return
        result = closer()
        if hasattr(result, "__await__"):
            await result

    async def update(self) -> None:
        device = self._require_device()
        await device.update()

    async def is_on(self) -> bool:
        device = self._require_device()
        await device.update()
        return bool(device.is_on)

    async def turn_on(self) -> None:
        device = self._require_device()
        await device.turn_on()
        await device.update()

    async def turn_off(self) -> None:
        device = self._require_device()
        await device.turn_off()
        await device.update()

    async def toggle(self) -> bool:
        if await self.is_on():
            await self.turn_off()
            return False
        await self.turn_on()
        return True

    def _require_device(self) -> Device:
        if self._device is None:
            raise RuntimeError("No hay un enchufe Tapo conectado.")
        return self._device


async def discover_plugs(username: str, password: str, timeout: int = 8) -> list[DiscoveredPlug]:
    devices = await Discover.discover(
        credentials=Credentials(username.strip(), password),
        timeout=timeout,
        discovery_timeout=timeout,
    )
    plugs: list[DiscoveredPlug] = []
    for device in devices.values():
        try:
            await device.update()
        except Exception:
            continue
        plugs.append(
            DiscoveredPlug(
                host=device.host,
                alias=str(getattr(device, "alias", "") or device.host),
                model=str(getattr(device, "model", "") or "Tapo"),
            )
        )
    plugs.sort(key=lambda item: (item.alias.lower(), item.host))
    return plugs
