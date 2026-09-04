"""Interfaz gráfica para Windows y Linux."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any

import customtkinter as ctk

from tapo_battery_guard.async_runner import AsyncRunner
from tapo_battery_guard.battery import read_battery
from tapo_battery_guard.config import (
    AppConfig,
    load_config,
    load_password,
    save_config,
    save_password,
)
from tapo_battery_guard.controller import ChargeController
from tapo_battery_guard.tapo_client import TapoClient, discover_plugs
from tapo_battery_guard.tray import SystemTray


class BatteryGuardApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Tapo Battery Guard")
        self.geometry("520x640")
        self.minsize(480, 600)

        self.config_data = load_config()
        self.client = TapoClient()
        self.controller = ChargeController(self.client)
        self.runner = AsyncRunner()
        self.runner.start()

        self._poll_task: asyncio.Future[Any] | None = None
        self._busy = False
        self._quitting = False
        self._tray_hint_shown = False
        self._plug_on: bool | None = None
        self.tray = SystemTray(
            on_show=lambda: self.after(0, self._show_window),
            on_toggle_automation=lambda: self.after(0, self._toggle_automation),
            on_connect=lambda: self.after(0, self._connect_from_tray),
            on_toggle_plug=lambda: self.after(0, self._toggle),
            on_quit=lambda: self.after(0, self._quit),
            is_automation_on=lambda: self.config_data.automation_enabled,
            is_connected=lambda: self.client.connected,
        )

        ctk.set_appearance_mode(self.config_data.theme)
        ctk.set_default_color_theme("blue")

        self._build()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.bind("<Unmap>", self._on_unmap)
        self.after(200, self._refresh_battery)
        self.after(300, self._start_tray)
        if self.config_data.auto_connect:
            self.after(600, self._connect)

    def _build(self) -> None:
        self.grid_columnconfigure(0, weight=1)

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=(18, 8))
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header,
            text="Tapo Battery Guard",
            font=ctk.CTkFont(size=22, weight="bold"),
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            header,
            text="Enciende o apaga el enchufe según el % real de la batería.",
            font=ctk.CTkFont(size=13),
            text_color=("gray30", "gray70"),
        ).grid(row=1, column=0, sticky="w", pady=(2, 0))

        status = ctk.CTkFrame(self)
        status.grid(row=1, column=0, sticky="ew", padx=20, pady=8)
        status.grid_columnconfigure((0, 1, 2), weight=1)

        self.battery_label = ctk.CTkLabel(status, text="Batería —", font=ctk.CTkFont(size=18, weight="bold"))
        self.battery_label.grid(row=0, column=0, padx=10, pady=(14, 4))
        self.charge_label = ctk.CTkLabel(status, text="Estado —")
        self.charge_label.grid(row=1, column=0, padx=10, pady=(0, 14))

        self.link_label = ctk.CTkLabel(status, text="Tapo desconectado", font=ctk.CTkFont(size=18, weight="bold"))
        self.link_label.grid(row=0, column=1, padx=10, pady=(14, 4))
        self.plug_label = ctk.CTkLabel(status, text="Enchufe —")
        self.plug_label.grid(row=1, column=1, padx=10, pady=(0, 14))

        self.model_label = ctk.CTkLabel(status, text="Modelo —", font=ctk.CTkFont(size=18, weight="bold"))
        self.model_label.grid(row=0, column=2, padx=10, pady=(14, 4))
        self.alias_label = ctk.CTkLabel(status, text="Nombre —")
        self.alias_label.grid(row=1, column=2, padx=10, pady=(0, 14))

        form = ctk.CTkFrame(self)
        form.grid(row=2, column=0, sticky="nsew", padx=20, pady=8)
        self.grid_rowconfigure(2, weight=1)
        form.grid_columnconfigure((0, 1), weight=1)

        self.min_var = ctk.StringVar(value=str(self.config_data.min_percent))
        self.max_var = ctk.StringVar(value=str(self.config_data.max_percent))
        self.host_var = ctk.StringVar(value=self.config_data.host)
        self.user_var = ctk.StringVar(value=self.config_data.username)
        self.password_var = ctk.StringVar(value=load_password(self.config_data.username))
        self.auto_var = ctk.BooleanVar(value=self.config_data.auto_connect)
        self.auto_run_var = ctk.BooleanVar(value=self.config_data.automation_enabled)
        self.theme_var = ctk.BooleanVar(value=self.config_data.theme == "dark")

        self._labeled_entry(form, "Mínimo (%)", self.min_var, 0, 0)
        self._labeled_entry(form, "Máximo (%)", self.max_var, 0, 1)
        self._labeled_entry(form, "IP o host del enchufe", self.host_var, 1, 0, span=2)
        self._labeled_entry(form, "Correo Tapo", self.user_var, 2, 0, span=2)
        self._labeled_entry(form, "Contraseña Tapo", self.password_var, 3, 0, span=2, secret=True)

        flags = ctk.CTkFrame(form, fg_color="transparent")
        flags.grid(row=4, column=0, columnspan=2, sticky="ew", padx=12, pady=(8, 4))
        ctk.CTkCheckBox(
            flags,
            text="Automatización activa",
            variable=self.auto_run_var,
            command=self._sync_automation,
            onvalue=True,
            offvalue=False,
        ).pack(side="left", padx=(0, 16))
        ctk.CTkCheckBox(
            flags,
            text="Auto-conectar al iniciar",
            variable=self.auto_var,
            onvalue=True,
            offvalue=False,
        ).pack(side="left", padx=(0, 16))
        ctk.CTkCheckBox(
            flags,
            text="Tema oscuro",
            variable=self.theme_var,
            command=self._apply_theme,
            onvalue=True,
            offvalue=False,
        ).pack(side="left")

        buttons = ctk.CTkFrame(form, fg_color="transparent")
        buttons.grid(row=5, column=0, columnspan=2, sticky="ew", padx=12, pady=(8, 16))
        for i in range(4):
            buttons.grid_columnconfigure(i, weight=1)

        self.save_btn = ctk.CTkButton(buttons, text="Guardar", command=self._save)
        self.save_btn.grid(row=0, column=0, padx=4, pady=4, sticky="ew")
        self.connect_btn = ctk.CTkButton(buttons, text="Conectar", command=self._connect)
        self.connect_btn.grid(row=0, column=1, padx=4, pady=4, sticky="ew")
        self.toggle_btn = ctk.CTkButton(buttons, text="Alternar enchufe", command=self._toggle, state="disabled")
        self.toggle_btn.grid(row=0, column=2, padx=4, pady=4, sticky="ew")
        self.discover_btn = ctk.CTkButton(buttons, text="Descubrir", command=self._discover)
        self.discover_btn.grid(row=0, column=3, padx=4, pady=4, sticky="ew")

        self.status_box = ctk.CTkTextbox(self, height=90)
        self.status_box.grid(row=3, column=0, sticky="ew", padx=20, pady=(4, 18))
        self.status_box.configure(state="disabled")
        self._set_status("Listo. Guarda los datos del enchufe y pulsa Conectar.")

    def _start_tray(self) -> None:
        if self.tray.start():
            self._set_status(
                "Listo. Al cerrar la ventana la app sigue en la bandeja del sistema. "
                "Usa Salir en el icono para cerrarla del todo."
            )
            return
        if self.tray.error:
            self._set_status(
                "La bandeja del sistema no está disponible. "
                f"{self.tray.error} La ventana se cerrará por completo al pulsar X."
            )

    def _labeled_entry(
        self,
        parent: ctk.CTkFrame,
        label: str,
        variable: ctk.StringVar,
        row: int,
        column: int,
        span: int = 1,
        secret: bool = False,
    ) -> None:
        box = ctk.CTkFrame(parent, fg_color="transparent")
        box.grid(row=row, column=column, columnspan=span, sticky="ew", padx=12, pady=8)
        box.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(box, text=label).grid(row=0, column=0, sticky="w")
        entry = ctk.CTkEntry(box, textvariable=variable, show="•" if secret else "")
        entry.grid(row=1, column=0, sticky="ew", pady=(4, 0))

    def _apply_theme(self) -> None:
        ctk.set_appearance_mode("dark" if self.theme_var.get() else "light")

    def _sync_automation(self) -> None:
        self.config_data.automation_enabled = bool(self.auto_run_var.get())

    def _toggle_automation(self) -> None:
        self.auto_run_var.set(not bool(self.auto_run_var.get()))
        self._sync_automation()
        state = "activa" if self.config_data.automation_enabled else "en pausa"
        self._set_status(f"Automatización {state}.")

    def _connect_from_tray(self) -> None:
        self._show_window()
        self._connect()

    def _read_form(self) -> AppConfig | None:
        try:
            min_percent = int(self.min_var.get().strip())
            max_percent = int(self.max_var.get().strip())
        except ValueError:
            self._set_status("Los umbrales mínimo y máximo deben ser números enteros.")
            return None

        config = AppConfig(
            host=self.host_var.get().strip(),
            username=self.user_var.get().strip(),
            min_percent=min_percent,
            max_percent=max_percent,
            poll_interval_seconds=self.config_data.poll_interval_seconds,
            auto_connect=bool(self.auto_var.get()),
            automation_enabled=bool(self.auto_run_var.get()),
            theme="dark" if self.theme_var.get() else "light",
        )
        error = config.validate()
        if error:
            self._set_status(error)
            return None
        return config

    def _save(self) -> None:
        config = self._read_form()
        if config is None:
            return
        save_config(config)
        self.config_data = config
        warning = save_password(config.username, self.password_var.get())
        if warning:
            self._set_status(f"Ajustes guardados. {warning}")
        else:
            self._set_status("Ajustes guardados.")

    def _connect(self) -> None:
        config = self._read_form()
        if config is None:
            return
        password = self.password_var.get()
        if not password:
            self._set_status("Indica la contraseña de la cuenta Tapo.")
            return
        self.config_data = config
        self._run_async(self._connect_async(config, password), "Conectando con el enchufe Tapo...")

    async def _connect_async(self, config: AppConfig, password: str) -> None:
        await self.client.connect(config.host, config.username, password)
        plug_on = await self.client.is_on()
        self._ui(lambda: self._on_connected(plug_on))
        self._start_polling()

    def _set_plug_state(self, plug_on: bool | None) -> None:
        self._plug_on = plug_on
        if plug_on is None:
            self.plug_label.configure(text="Enchufe —")
        else:
            self.plug_label.configure(text="Enchufe encendido" if plug_on else "Enchufe apagado")

    def _on_connected(self, plug_on: bool) -> None:
        self.connect_btn.configure(state="disabled")
        self.toggle_btn.configure(state="normal")
        self.link_label.configure(text="Tapo conectado")
        self._set_plug_state(plug_on)
        self.model_label.configure(text=self.client.model or "Tapo")
        self.alias_label.configure(text=self.client.alias or self.config_data.host)
        self._set_status("Conectado. La automatización usará el porcentaje de batería del portátil.")

    def _toggle(self) -> None:
        self._run_async(self._toggle_async(), "Cambiando el estado del enchufe...")

    async def _toggle_async(self) -> None:
        is_on = await self.client.toggle()
        self._ui(lambda: self._set_plug_state(is_on))
        self._ui(lambda: self._set_status("Enchufe encendido." if is_on else "Enchufe apagado."))

    def _discover(self) -> None:
        username = self.user_var.get().strip()
        password = self.password_var.get()
        if not username or not password:
            self._set_status("Para descubrir enchufes hacen falta el correo y la contraseña Tapo.")
            return
        self._run_async(self._discover_async(username, password), "Buscando enchufes Tapo en la red local...")

    async def _discover_async(self, username: str, password: str) -> None:
        plugs = await discover_plugs(username, password)
        if not plugs:
            self._ui(lambda: self._set_status("No se encontró ningún enchufe Tapo en la red."))
            return

        first = plugs[0]
        self._ui(lambda: self.host_var.set(first.host))
        listing = ", ".join(f"{item.alias} ({item.model} · {item.host})" for item in plugs)
        self._ui(lambda: self._set_status(f"Encontrados: {listing}. Se rellenó el primero en el campo IP."))

    def _start_polling(self) -> None:
        if self._poll_task is not None and not self._poll_task.done():
            return
        self._poll_task = self.runner.submit(self._poll_loop())

    async def _poll_loop(self) -> None:
        while self.client.connected:
            config = self.config_data
            try:
                snapshot = await self.controller.tick(config)
            except Exception as exc:
                self._ui(lambda message=str(exc): self._set_status(f"Error de control: {message}"))
                await asyncio.sleep(config.poll_interval_seconds)
                continue

            def update() -> None:
                self._set_plug_state(snapshot.plug_on)
                self._set_status(snapshot.message)

            self._ui(update)
            await asyncio.sleep(config.poll_interval_seconds)

    def _refresh_battery(self) -> None:
        status = read_battery()
        if status.present:
            self.battery_label.configure(text=f"Batería {status.percent}%")
            self.charge_label.configure(text="Cargando" if status.charging else "En batería")
            title = f"Tapo Battery Guard · {status.percent}%"
            if self.client.connected:
                title += " · conectado"
            self.tray.set_status(title, charging=status.charging, plugged=self._plug_on)
        else:
            self.battery_label.configure(text="Batería —")
            self.charge_label.configure(text=status.message)
        self.after(1000, self._refresh_battery)

    def _run_async(self, coro: Any, waiting_message: str) -> None:
        if self._busy:
            return
        self._busy = True
        self._set_status(waiting_message)

        future = self.runner.submit(coro)

        def done(task: asyncio.Future[Any]) -> None:
            def finish() -> None:
                self._busy = False
                try:
                    task.result()
                except Exception as exc:
                    self._set_status(f"Error: {exc}")

            self._ui(finish)

        future.add_done_callback(done)

    def _ui(self, callback: Callable[[], None]) -> None:
        self.after(0, callback)

    def _set_status(self, message: str) -> None:
        self.status_box.configure(state="normal")
        self.status_box.delete("1.0", "end")
        self.status_box.insert("1.0", message)
        self.status_box.configure(state="disabled")

    def _on_unmap(self, event: Any) -> None:
        if event.widget is not self or self._quitting or not self.tray.available:
            return
        try:
            iconic = str(self.state()) == "iconic"
        except Exception:
            return
        if iconic:
            self.withdraw()

    def _on_close(self) -> None:
        if self._quitting or not self.tray.available:
            self._quit()
            return
        self.withdraw()
        if not self._tray_hint_shown:
            self._tray_hint_shown = True
            self.tray.notify(
                "Tapo Battery Guard",
                "Sigue en ejecución. Clic en el icono para abrir la configuración.",
            )

    def _show_window(self) -> None:
        self.deiconify()
        self.lift()
        self.focus_force()

    def _quit(self) -> None:
        if self._quitting:
            return
        self._quitting = True
        self.tray.stop()
        async def shutdown() -> None:
            await self.client.disconnect()

        try:
            future = self.runner.submit(shutdown())
            future.result(timeout=3)
        except Exception:
            pass
        self.runner.stop()
        self.destroy()


def run_gui() -> None:
    app = BatteryGuardApp()
    app.mainloop()
