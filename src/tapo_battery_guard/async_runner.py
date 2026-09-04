"""Bucle asyncio en un hilo aparte, para no bloquear la interfaz."""

from __future__ import annotations

import asyncio
import threading
from collections.abc import Callable, Coroutine
from typing import Any


class AsyncRunner:
    def __init__(self) -> None:
        self.loop = asyncio.new_event_loop()
        self._thread = threading.Thread(
            target=self._run,
            name="tapo-async",
            daemon=True,
        )
        self._started = False

    def start(self) -> None:
        if self._started:
            return
        self._thread.start()
        self._started = True

    def stop(self) -> None:
        if not self._started:
            return
        self.loop.call_soon_threadsafe(self.loop.stop)
        self._thread.join(timeout=3)

    def submit(self, coro: Coroutine[Any, Any, Any]) -> asyncio.Future[Any]:
        if not self._started:
            raise RuntimeError("El bucle asíncrono no está en marcha.")
        return asyncio.run_coroutine_threadsafe(coro, self.loop)

    def call_soon(self, callback: Callable[..., None], *args: Any) -> None:
        self.loop.call_soon_threadsafe(callback, *args)

    def _run(self) -> None:
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()
        pending = asyncio.all_tasks(self.loop)
        for task in pending:
            task.cancel()
        self.loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        self.loop.close()
