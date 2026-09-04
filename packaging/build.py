"""Genera iconos y empaqueta Tapo Battery Guard con PyInstaller."""

from __future__ import annotations

import argparse
import os
import shutil
import stat
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PACKAGING = ROOT / "packaging"
ASSETS = PACKAGING / "assets"
DIST = ROOT / "dist"
BUILD = ROOT / "build"
APPDIR = ROOT / "AppDir"
SPEC = PACKAGING / "tapo-battery-guard.spec"
APPIMAGE_TOOL_URL = (
    "https://github.com/AppImage/appimagetool/releases/download/continuous/"
    "appimagetool-x86_64.AppImage"
)


def project_version() -> str:
    for line in (ROOT / "pyproject.toml").read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("version"):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return "0.0.0"


def generate_icons() -> None:
    sys.path.insert(0, str(ROOT / "src"))
    from tapo_battery_guard.tray import make_icon

    ASSETS.mkdir(parents=True, exist_ok=True)
    master = make_icon(charging=True, plugged=True, size=256)
    master.save(ASSETS / "icon.png", format="PNG")
    sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    images = [make_icon(charging=True, plugged=True, size=side) for side, _ in sizes]
    images[-1].save(ASSETS / "icon.ico", format="ICO", sizes=sizes)
    print(f"Iconos en {ASSETS}")


def run_pyinstaller() -> Path:
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        str(SPEC),
    ]
    subprocess.run(cmd, cwd=ROOT, check=True)
    output = DIST / "TapoBatteryGuard"
    if not output.exists():
        raise SystemExit(f"No se encontró la carpeta empaquetada: {output}")
    print(f"PyInstaller: {output}")
    return output


def build_appimage(app_dir_src: Path) -> Path:
    if sys.platform == "win32":
        raise SystemExit("El AppImage se genera en Linux.")

    if APPDIR.exists():
        shutil.rmtree(APPDIR)

    bin_dir = APPDIR / "usr" / "bin"
    icon_dir = APPDIR / "usr" / "share" / "icons" / "hicolor" / "256x256" / "apps"
    bin_dir.mkdir(parents=True)
    icon_dir.mkdir(parents=True)
    shutil.copytree(app_dir_src, bin_dir, dirs_exist_ok=True)
    shutil.copy2(ASSETS / "icon.png", APPDIR / "tapo-battery-guard.png")
    shutil.copy2(ASSETS / "icon.png", icon_dir / "tapo-battery-guard.png")
    shutil.copy2(
        PACKAGING / "linux" / "tapo-battery-guard.desktop",
        APPDIR / "tapo-battery-guard.desktop",
    )

    apprun = APPDIR / "AppRun"
    apprun.write_text(
        "#!/bin/sh\n"
        'HERE="$(dirname "$(readlink -f "$0")")"\n'
        'export PATH="$HERE/usr/bin:$PATH"\n'
        'exec "$HERE/usr/bin/TapoBatteryGuard" "$@"\n',
        encoding="utf-8",
    )
    apprun.chmod(apprun.stat().st_mode | stat.S_IEXEC)

    tool = BUILD / "appimagetool-x86_64.AppImage"
    BUILD.mkdir(parents=True, exist_ok=True)
    if not tool.exists():
        print("Descargando appimagetool...")
        urllib.request.urlretrieve(APPIMAGE_TOOL_URL, tool)
        tool.chmod(tool.stat().st_mode | stat.S_IEXEC)

    version = project_version()
    output = DIST / f"TapoBatteryGuard-{version}-x86_64.AppImage"
    env = os.environ.copy()
    env["APPIMAGE_EXTRACT_AND_RUN"] = "1"
    env["ARCH"] = "x86_64"
    env["VERSION"] = version
    subprocess.run(
        [str(tool), str(APPDIR), str(output)],
        cwd=ROOT,
        check=True,
        env=env,
    )
    print(f"AppImage: {output}")
    return output


def find_iscc() -> str | None:
    if shutil.which("iscc"):
        return "iscc"
    if shutil.which("ISCC"):
        return "ISCC"
    candidates = [
        Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"))
        / "Inno Setup 6"
        / "ISCC.exe",
        Path(os.environ.get("ProgramFiles", r"C:\Program Files"))
        / "Inno Setup 6"
        / "ISCC.exe",
    ]
    for path in candidates:
        if path.exists():
            return str(path)
    return None


def build_windows_installer() -> Path:
    if sys.platform != "win32":
        raise SystemExit("El instalador de Inno Setup se genera en Windows.")
    iscc = find_iscc()
    if not iscc:
        raise SystemExit(
            "No se encontró Inno Setup. Instálalo y vuelve a ejecutar "
            "python packaging/build.py --installer"
        )
    version = project_version()
    output = DIST / f"TapoBatteryGuard-{version}-Setup.exe"
    cmd = [
        iscc,
        f"/DAppVersion={version}",
        str(PACKAGING / "windows" / "installer.iss"),
    ]
    subprocess.run(cmd, cwd=ROOT, check=True)
    print(f"Instalador: {output}")
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Empaqueta Tapo Battery Guard.")
    parser.add_argument(
        "--appimage",
        action="store_true",
        help="Tras PyInstaller, genera un AppImage (Linux).",
    )
    parser.add_argument(
        "--installer",
        action="store_true",
        help="Tras PyInstaller, genera el instalador Inno Setup (Windows).",
    )
    args = parser.parse_args()

    generate_icons()
    app_dir = run_pyinstaller()
    if args.appimage:
        build_appimage(app_dir)
    if args.installer:
        build_windows_installer()


if __name__ == "__main__":
    main()
