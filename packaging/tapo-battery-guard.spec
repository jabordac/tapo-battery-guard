# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

from PyInstaller.utils.hooks import collect_all

SPECDIR = Path(SPECPATH).resolve()
ROOT = SPECDIR.parent
ICON_ICO = SPECDIR / "assets" / "icon.ico"

datas: list = []
binaries: list = []
hiddenimports = [
    "customtkinter",
    "darkdetect",
    "packaging",
    "packaging.version",
    "keyring.backends",
    "keyring.backends.Windows",
    "keyring.backends.SecretService",
    "keyring.backends.libsecret",
    "keyring.backends.kwallet",
    "keyring.backends.chainer",
    "keyring.backends.fail",
    "jaraco",
    "jaraco.classes",
    "jaraco.context",
    "jaraco.functools",
    "pkg_resources",
    "pystray",
    "pystray._appindicator",
    "pystray._gtk",
    "pystray._win32",
    "pystray._darwin",
    "pystray._dummy",
    "pystray._xorg",
    "kasa",
    "aiohttp",
    "certifi",
    "cryptography",
    "psutil",
    "PIL",
    "PIL._tkinter_finder",
]

for package in ("customtkinter", "kasa", "pystray", "keyring", "certifi", "cryptography"):
    pkg_datas, pkg_binaries, pkg_hidden = collect_all(package)
    datas += pkg_datas
    binaries += pkg_binaries
    hiddenimports += pkg_hidden

a = Analysis(
    [str(SPECDIR / "launch.py")],
    pathex=[str(ROOT / "src")],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["pytest", "_pytest", "pygments"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="TapoBatteryGuard",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    icon=str(ICON_ICO) if ICON_ICO.exists() else None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="TapoBatteryGuard",
)
