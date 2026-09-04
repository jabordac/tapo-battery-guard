"""Configuración persistente. La contraseña va al llavero del sistema."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import keyring
from platformdirs import user_config_dir

APP_NAME = "tapo-battery-guard"
KEYRING_SERVICE = "tapo-battery-guard"


@dataclass
class AppConfig:
    host: str = ""
    username: str = ""
    min_percent: int = 20
    max_percent: int = 80
    poll_interval_seconds: int = 15
    auto_connect: bool = False
    automation_enabled: bool = True
    theme: str = "dark"

    def validate(self) -> str | None:
        if not self.host.strip():
            return "Indica la IP o el nombre del enchufe."
        if not self.username.strip():
            return "Indica el correo de la cuenta Tapo."
        if not 0 <= self.min_percent <= 100:
            return "El mínimo debe estar entre 0 y 100."
        if not 0 <= self.max_percent <= 100:
            return "El máximo debe estar entre 0 y 100."
        if self.min_percent >= self.max_percent:
            return "El mínimo debe ser menor que el máximo."
        if self.poll_interval_seconds < 5:
            return "El intervalo de sondeo debe ser de al menos 5 segundos."
        if self.theme not in {"dark", "light"}:
            return "El tema debe ser dark o light."
        return None


def config_path() -> Path:
    directory = Path(user_config_dir(APP_NAME, appauthor=False))
    directory.mkdir(parents=True, exist_ok=True)
    return directory / "config.json"


def load_config() -> AppConfig:
    path = config_path()
    if not path.exists():
        return AppConfig()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return AppConfig()

    defaults = AppConfig()
    return AppConfig(
        host=str(data.get("host", defaults.host)),
        username=str(data.get("username", defaults.username)),
        min_percent=int(data.get("min_percent", defaults.min_percent)),
        max_percent=int(data.get("max_percent", defaults.max_percent)),
        poll_interval_seconds=int(
            data.get("poll_interval_seconds", defaults.poll_interval_seconds)
        ),
        auto_connect=bool(data.get("auto_connect", defaults.auto_connect)),
        automation_enabled=bool(
            data.get("automation_enabled", defaults.automation_enabled)
        ),
        theme=str(data.get("theme", defaults.theme)),
    )


def save_config(config: AppConfig) -> None:
    payload = asdict(config)
    config_path().write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def load_password(username: str) -> str:
    if not username.strip():
        return ""
    try:
        return keyring.get_password(KEYRING_SERVICE, username.strip()) or ""
    except keyring.errors.KeyringError:
        return ""


def save_password(username: str, password: str) -> str | None:
    """Guarda la contraseña. Devuelve un aviso si el llavero no está disponible."""
    if not username.strip() or not password:
        return None
    try:
        keyring.set_password(KEYRING_SERVICE, username.strip(), password)
        return None
    except keyring.errors.KeyringError as exc:
        return f"No se pudo guardar la contraseña en el llavero: {exc}"


def delete_password(username: str) -> None:
    if not username.strip():
        return
    try:
        keyring.delete_password(KEYRING_SERVICE, username.strip())
    except keyring.errors.KeyringError:
        pass
