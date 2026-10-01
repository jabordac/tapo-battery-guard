# Tapo Battery Guard

Aplicación de escritorio para **Windows y Linux** que enciende o apaga un enchufe Tapo o **una toma de una regleta Kasa** según el **porcentaje real de batería** del portátil.

Está inspirada en [Tapo100Automation_Laptop](https://github.com/deadlykam/Tapo100Automation_Laptop), pero usa `python-kasa` (protocolo KLAP actual) y no `PyP100`.

Sirve con el **P110M**, el **P125M**, la **HS300** y otros enchufes Tapo/Kasa de la misma red.

## Cómo funciona

- Si la batería baja al **mínimo** (por defecto 20 %), enciende el enchufe.
- Si llega al **máximo** (por defecto 80 %), lo apaga.
- Entre esos dos valores no cambia de estado, para no estar encendiendo y apagando sin parar.

Esto no lee el Charge Guard del enchufe: el portátil decide con su propia batería. El programa tiene que estar en marcha.

## Requisitos

- Python 3.11 o posterior
- Portátil con batería
- Enchufe Tapo o regleta Kasa en la misma red Wi‑Fi 2.4 GHz
- Cuenta TP-Link (el mismo correo y contraseña de la app Tapo o Kasa)

En Linux, Tkinter:

```bash
sudo apt install python3-tk python3-venv   # Ubuntu/Debian
sudo dnf install python3-tkinter           # Fedora
```

## Instalación

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e .
```

## Uso

Ventana (Windows y Linux):

```bash
tapo-battery-guard
```

o:

```bash
python -m tapo_battery_guard
```

1. Correo y contraseña de TP-Link (Tapo o Kasa).
2. IP del enchufe, o pulsa **Descubrir**.
3. Si es una **HS300** (u otra regleta), elige el **conector** del cargador. Toda la regleta comparte una IP; cada toma se controla aparte.
4. Umbrales mínimo y máximo.
5. **Guardar** y **Conectar**.

La contraseña se guarda en el llavero del sistema (Credential Manager en Windows, Secret Service/KWallet en Linux), no en el archivo de configuración.

### Bandeja del sistema

Al cerrar o minimizar la ventana, la app **sigue en ejecución** junto al reloj.

- **Clic izquierdo** (o la opción por defecto): abre la configuración.
- **Clic derecho:** Mostrar configuración, pausar/activar automatización, conectar, alternar enchufe y **Salir**.
- **Salir** en ese menú cierra la app de verdad.

En Linux, si no aparece el icono:

```bash
sudo apt install gir1.2-ayatanaappindicator3-0.1   # Ubuntu/Debian
```

### Sin ventana

Primero abre la interfaz una vez, guarda y conéctate para dejar la contraseña en el llavero. Después:

```bash
tapo-battery-guard --daemon
```

## Instaladores

No hace falta Python en el PC de destino. En este repo:

```bash
pip install -e ".[pack]"
python packaging/build.py              # carpeta dist/TapoBatteryGuard
python packaging/build.py --appimage   # Linux: dist/*.AppImage
python packaging/build.py --installer  # Windows: dist/*-Setup.exe (requiere Inno Setup)
```

| Sistema | Archivo | Uso |
|---|---|---|
| Windows | `TapoBatteryGuard-*-Setup.exe` | Instalador (menú Inicio, desinstalador, inicio con Windows opcional) |
| Linux | `TapoBatteryGuard-*-x86_64.AppImage` | Marcar como ejecutable y abrir |

En Windows, Inno Setup 6: https://jrsoftware.org/isinfo.php

En GitHub, el flujo `Release` genera ambos al publicar una etiqueta `v0.3.0` o al lanzarlo a mano.

## Notas

- Si el portátil se suspende o se apaga, este programa deja de controlar el enchufe. En un P110M puedes dejar Charge Guard como respaldo.
- La IP puede cambiar con el DHCP. Usa **Descubrir** o reserva la IP en el router.
- En la app Tapo o Kasa, el dispositivo debe estar emparejado con tu cuenta.
- En una HS300, los USB no se encienden o apagan por separado: solo las 6 tomas de corriente.

## Licencia

MIT
