"""Modo sin ventana: útil en Linux con systemd o al iniciar sesión."""

from __future__ import annotations

import asyncio
import logging
import signal

from tapo_battery_guard.config import load_config, load_password
from tapo_battery_guard.controller import ChargeController
from tapo_battery_guard.tapo_client import TapoClient

log = logging.getLogger("tapo-battery-guard")


async def run_daemon() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    config = load_config()
    error = config.validate()
    if error:
        raise SystemExit(error)

    password = load_password(config.username)
    if not password:
        raise SystemExit("No hay contraseña en el llavero. Abre primero la interfaz y pulsa Guardar.")

    client = TapoClient()
    controller = ChargeController(client)
    stop = asyncio.Event()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop.set)
        except NotImplementedError:
            signal.signal(sig, lambda *_args: stop.set())

    log.info("Conectando con %s", config.host)
    await client.connect(config.host, config.username, password, config.child)
    if config.child:
        log.info(
            "Conectado a %s (%s), conector %s",
            client.alias or config.host,
            client.model or "TP-Link",
            config.child,
        )
    else:
        log.info("Conectado a %s (%s)", client.alias or config.host, client.model or "TP-Link")

    while not stop.is_set():
        try:
            snapshot = await controller.tick(config)
            log.info(snapshot.message)
        except Exception as exc:
            log.warning("Error de control: %s. Reintentando conexión.", exc)
            try:
                await client.connect(config.host, config.username, password, config.child)
            except Exception as reconnect_error:
                log.warning("No se pudo reconectar: %s", reconnect_error)
        try:
            await asyncio.wait_for(stop.wait(), timeout=config.poll_interval_seconds)
        except TimeoutError:
            pass

    await client.disconnect()
