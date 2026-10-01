"""Cliente local para enchufes Tapo y regletas Kasa (HS300, etc.)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from kasa import Credentials, Device, DeviceConfig, Discover
from kasa.device_factory import GET_SYSINFO_QUERY, get_device_class_from_sys_info
from kasa.deviceconfig import DeviceConnectionParameters, DeviceEncryptionType, DeviceFamily
from kasa.exceptions import AuthenticationError
from kasa.protocols import IotProtocol
from kasa.transports import KlapTransportV2


@dataclass(frozen=True)
class DiscoveredPlug:
    host: str
    alias: str
    model: str
    child: str = ""


@dataclass(frozen=True)
class OutletChoice:
    """Un conector de una regleta. `spec` es 1, 2, 3... como en la carcasa."""

    spec: str
    alias: str

    @property
    def label(self) -> str:
        return f"{self.spec} · {self.alias}" if self.alias else self.spec


def list_outlet_choices(device: Any) -> list[OutletChoice]:
    children = list(getattr(device, "children", None) or [])
    choices: list[OutletChoice] = []
    for index, child in enumerate(children, start=1):
        alias = str(getattr(child, "alias", "") or f"Conector {index}")
        choices.append(OutletChoice(spec=str(index), alias=alias))
    return choices


def resolve_target(device: Any, child: str) -> Any:
    """Devuelve el enchufe a controlar. En una regleta hay que elegir la toma."""
    children = list(getattr(device, "children", None) or [])
    if not children:
        return device

    spec = (child or "").strip()
    if not spec:
        names = ", ".join(
            f"{index} ({getattr(plug, 'alias', '') or f'Conector {index}'})"
            for index, plug in enumerate(children, start=1)
        )
        model = str(getattr(device, "model", "") or "regleta")
        raise RuntimeError(
            f"La {model} tiene {len(children)} conectores en la misma IP. "
            f"Elige el del cargador: {names}."
        )

    if spec.isdigit():
        number = int(spec)
        if 1 <= number <= len(children):
            return children[number - 1]
        raise RuntimeError(
            f"El conector {number} no existe. Hay {len(children)} tomas (1–{len(children)})."
        )

    spec_lower = spec.lower()
    for index, plug in enumerate(children, start=1):
        alias = str(getattr(plug, "alias", "") or "")
        if alias.lower() == spec_lower:
            return plug
        if spec_lower in {f"plug {index}", f"conector {index}", str(index)}:
            return plug

    getter = getattr(device, "get_child_device", None)
    if callable(getter):
        found = getter(spec)
        if found is not None:
            return found

    by_name = getattr(device, "get_plug_by_name", None)
    if callable(by_name):
        try:
            return by_name(spec)
        except Exception:
            pass

    names = ", ".join(
        f"{index} ({getattr(plug, 'alias', '') or f'Conector {index}'})"
        for index, plug in enumerate(children, start=1)
    )
    raise RuntimeError(f"No hay un conector llamado {spec!r}. Disponibles: {names}.")


class TapoClient:
    def __init__(self) -> None:
        self._device: Device | None = None
        self._target: Device | None = None
        self._child: str = ""

    @property
    def connected(self) -> bool:
        return self._device is not None and self._target is not None

    @property
    def parent_connected(self) -> bool:
        return self._device is not None

    @property
    def model(self) -> str:
        if self._device is None:
            return ""
        return str(getattr(self._device, "model", "") or "")

    @property
    def alias(self) -> str:
        target = self._target
        if target is None:
            return ""
        return str(getattr(target, "alias", "") or "")

    @property
    def child(self) -> str:
        return self._child

    def list_children(self) -> list[OutletChoice]:
        if self._device is None:
            return []
        return list_outlet_choices(self._device)

    async def connect(
        self,
        host: str,
        username: str,
        password: str,
        child: str = "",
    ) -> None:
        host = host.strip()
        username = username.strip()
        credentials = Credentials(username, password) if username or password else None
        try:
            device = await self._open_device(host, credentials)
            await device.update()
        except AuthenticationError as exc:
            raise RuntimeError(
                "La regleta rechazó el correo o la contraseña. "
                "Tiene que ser la cuenta TP-Link con la que está emparejada en la app Kasa. "
                "Si recuperaste una contraseña antigua de Windows, usa la actual."
            ) from exc
        self._device = device
        self._target = None
        self._child = ""
        if list_outlet_choices(device):
            if child.strip():
                self.select_child(child)
            return
        self._target = device
        self._child = ""

    def select_child(self, child: str) -> None:
        device = self._require_parent()
        target = resolve_target(device, child)
        if target is device:
            self._target = device
            self._child = ""
            return
        choices = list_outlet_choices(device)
        spec = child.strip()
        for choice in choices:
            if spec == choice.spec or spec.lower() == choice.alias.lower():
                spec = choice.spec
                break
        else:
            if spec.isdigit() and 1 <= int(spec) <= len(choices):
                spec = str(int(spec))
        self._target = target
        self._child = spec

    async def _connect_iot_klap_v2(self, config: DeviceConfig) -> Device:
        """HS300 y otros IOT con firmware nuevo: KLAP login_version 2 (SHA-256)."""
        protocol = IotProtocol(transport=KlapTransportV2(config=config))
        try:
            info = await protocol.query(GET_SYSINFO_QUERY)
            device_class = get_device_class_from_sys_info(info)
            device = device_class(config.host, config=config, protocol=protocol)
            device.update_from_discover_info(info)
            return device
        except Exception:
            await protocol.close()
            raise

    def _is_iot_klap_v2(self, config: DeviceConfig) -> bool:
        connection = config.connection_type
        return (
            connection.device_family is DeviceFamily.IotSmartPlugSwitch
            and connection.encryption_type is DeviceEncryptionType.Klap
            and (connection.login_version or 0) >= 2
        )

    async def _open_device(self, host: str, credentials: Credentials | None) -> Device:
        discovered: Device | None = None
        try:
            discovered = await Discover.discover_single(
                host,
                credentials=credentials,
                timeout=8,
                discovery_timeout=8,
            )
        except AuthenticationError:
            raise
        except Exception:
            discovered = None

        if discovered is not None:
            config = discovered.config
            if credentials is not None:
                config.credentials = credentials
            if self._is_iot_klap_v2(config):
                try:
                    await discovered.disconnect()
                except Exception:
                    pass
                return await self._connect_iot_klap_v2(config)
            return discovered

        try:
            device = await Device.connect(
                config=DeviceConfig(host=host, credentials=credentials, timeout=8)
            )
            if device is not None:
                return device
        except Exception:
            pass

        try:
            return await Device.connect(
                config=DeviceConfig(
                    host=host,
                    credentials=credentials,
                    timeout=8,
                    connection_type=DeviceConnectionParameters(
                        DeviceFamily.IotSmartPlugSwitch,
                        DeviceEncryptionType.Xor,
                    ),
                )
            )
        except Exception:
            pass

        try:
            return await Device.connect(
                config=DeviceConfig(
                    host=host,
                    credentials=credentials,
                    timeout=8,
                    connection_type=DeviceConnectionParameters(
                        DeviceFamily.SmartTapoPlug,
                        DeviceEncryptionType.Klap,
                        login_version=2,
                    ),
                )
            )
        except Exception:
            pass

        raise RuntimeError(
            f"No se pudo conectar con {host}. "
            "Comprueba la IP, que el dispositivo esté en la misma Wi‑Fi y el correo TP-Link."
        )

    async def disconnect(self) -> None:
        device = self._device
        self._device = None
        self._target = None
        self._child = ""
        if device is None:
            return
        closer = getattr(device, "disconnect", None)
        if closer is None:
            return
        result = closer()
        if hasattr(result, "__await__"):
            await result

    async def update(self) -> None:
        device = self._require_parent()
        await device.update()

    async def is_on(self) -> bool:
        device = self._require_parent()
        await device.update()
        return bool(self._require_target().is_on)

    async def turn_on(self) -> None:
        target = self._require_target()
        await target.turn_on()
        await self._require_parent().update()

    async def turn_off(self) -> None:
        target = self._require_target()
        await target.turn_off()
        await self._require_parent().update()

    async def toggle(self) -> bool:
        if await self.is_on():
            await self.turn_off()
            return False
        await self.turn_on()
        return True

    def _require_parent(self) -> Device:
        if self._device is None:
            raise RuntimeError("No hay un enchufe conectado.")
        return self._device

    def _require_target(self) -> Device:
        if self._target is None:
            choices = list_outlet_choices(self._require_parent())
            names = ", ".join(choice.label for choice in choices) or "ninguno"
            raise RuntimeError(
                "Esta regleta comparte una sola IP. Elige el conector del cargador: "
                f"{names}."
            )
        return self._target


async def discover_plugs(username: str, password: str, timeout: int = 8) -> list[DiscoveredPlug]:
    credentials = Credentials(username.strip(), password) if username.strip() or password else None
    devices = await Discover.discover(
        credentials=credentials,
        timeout=timeout,
        discovery_timeout=timeout,
    )
    plugs: list[DiscoveredPlug] = []
    for device in devices.values():
        try:
            await device.update()
        except Exception:
            continue
        host = device.host
        model = str(getattr(device, "model", "") or "TP-Link")
        outlets = list_outlet_choices(device)
        if outlets:
            for outlet in outlets:
                plugs.append(
                    DiscoveredPlug(
                        host=host,
                        alias=outlet.alias,
                        model=model,
                        child=outlet.spec,
                    )
                )
            continue
        plugs.append(
            DiscoveredPlug(
                host=host,
                alias=str(getattr(device, "alias", "") or host),
                model=model,
            )
        )
    plugs.sort(key=lambda item: (item.host, item.child, item.alias.lower()))
    return plugs
