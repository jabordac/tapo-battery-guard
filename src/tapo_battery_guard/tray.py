"""Icono de bandeja del sistema para Windows y Linux."""

from __future__ import annotations

import sys
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

from PIL import Image, ImageDraw

if TYPE_CHECKING:
    import pystray


def _enable_system_gi() -> None:
    """Permite usar PyGObject del sistema desde un venv aislado (Linux)."""
    extras = (
        "/usr/lib/python3/dist-packages",
        f"/usr/lib/python{sys.version_info.major}.{sys.version_info.minor}/dist-packages",
    )
    for extra in extras:
        path = Path(extra)
        if path.is_dir() and extra not in sys.path:
            sys.path.append(extra)


def make_icon(
    charging: bool = False,
    plugged: bool | None = None,
    size: int = 64,
) -> Image.Image:
    """Icono de batería generado en memoria, sin archivos extra."""
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    scale = size / 64

    def box(*values: int) -> tuple[int, int, int, int]:
        x0, y0, x1, y1 = (round(value * scale) for value in values)
        return x0, y0, x1, y1

    outline = max(1, round(3 * scale))
    draw.rounded_rectangle(box(10, 18, 48, 46), radius=max(1, round(6 * scale)), outline=(240, 244, 250, 255), width=outline)
    draw.rounded_rectangle(box(48, 26, 56, 38), radius=max(1, round(2 * scale)), fill=(240, 244, 250, 255))

    if plugged is False:
        fill = (220, 80, 70, 255)
        inset = box(16, 24, 28, 40)
    elif charging or plugged:
        fill = (80, 190, 120, 255)
        inset = box(16, 24, 42, 40)
    else:
        fill = (80, 150, 230, 255)
        inset = box(16, 24, 36, 40)
    draw.rounded_rectangle(inset, radius=max(1, round(3 * scale)), fill=fill)
    return image


class SystemTray:
    def __init__(
        self,
        *,
        on_show: Callable[[], None],
        on_toggle_automation: Callable[[], None],
        on_connect: Callable[[], None],
        on_toggle_plug: Callable[[], None],
        on_quit: Callable[[], None],
        is_automation_on: Callable[[], bool],
        is_connected: Callable[[], bool],
    ) -> None:
        self._on_show = on_show
        self._on_toggle_automation = on_toggle_automation
        self._on_connect = on_connect
        self._on_toggle_plug = on_toggle_plug
        self._on_quit = on_quit
        self._is_automation_on = is_automation_on
        self._is_connected = is_connected
        self.icon: pystray.Icon | None = None
        self.available = False
        self.error = ""

    def start(self) -> bool:
        _enable_system_gi()
        try:
            import pystray
        except ImportError as exc:
            self.error = str(exc)
            return False

        menu = pystray.Menu(
            pystray.MenuItem("Mostrar configuración", self._show, default=True),
            pystray.MenuItem(
                "Automatización activa",
                self._toggle_automation,
                checked=lambda _item: self._is_automation_on(),
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                "Conectar",
                self._connect,
                enabled=lambda _item: not self._is_connected(),
            ),
            pystray.MenuItem(
                "Alternar enchufe",
                self._toggle_plug,
                enabled=lambda _item: self._is_connected(),
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Salir", self._quit),
        )
        self.icon = pystray.Icon(
            "tapo-battery-guard",
            make_icon(),
            "Tapo Battery Guard",
            menu,
        )
        try:
            self.icon.run_detached()
        except Exception as exc:
            self.error = str(exc)
            self.icon = None
            return False
        self.available = True
        return True

    def stop(self) -> None:
        icon = self.icon
        self.icon = None
        self.available = False
        if icon is None:
            return
        try:
            icon.stop()
        except Exception:
            pass

    def notify(self, title: str, message: str) -> None:
        if self.icon is None:
            return
        notify = getattr(self.icon, "notify", None)
        if notify is None:
            return
        try:
            notify(message, title)
        except Exception:
            pass

    def set_status(self, title: str, charging: bool, plugged: bool | None) -> None:
        if self.icon is None:
            return
        try:
            self.icon.title = title
            self.icon.icon = make_icon(charging=charging, plugged=plugged)
        except Exception:
            pass

    def _show(self, _icon: Any = None, _item: Any = None) -> None:
        self._on_show()

    def _toggle_automation(self, _icon: Any = None, _item: Any = None) -> None:
        self._on_toggle_automation()

    def _connect(self, _icon: Any = None, _item: Any = None) -> None:
        self._on_connect()

    def _toggle_plug(self, _icon: Any = None, _item: Any = None) -> None:
        self._on_toggle_plug()

    def _quit(self, icon: Any = None, _item: Any = None) -> None:
        if icon is not None:
            try:
                icon.stop()
            except Exception:
                pass
        self.icon = None
        self.available = False
        self._on_quit()
