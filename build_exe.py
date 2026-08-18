from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
APP_NAME = "Spotisaver"
ENTRYPOINT = PROJECT_ROOT / "playlist_gui.py"
DIST_DIR = PROJECT_ROOT / "dist"
BUILD_DIR = PROJECT_ROOT / "build"
SPEC_FILE = PROJECT_ROOT / f"{APP_NAME}.spec"


def run(command: list[str]) -> None:
    print(">", " ".join(command))
    subprocess.run(command, cwd=PROJECT_ROOT, check=True)


def clean_previous_build() -> None:
    for path in (BUILD_DIR, DIST_DIR, SPEC_FILE):
        if path.is_dir():
            shutil.rmtree(path)
        elif path.exists():
            path.unlink()


def ensure_pyinstaller() -> None:
    try:
        import PyInstaller  # noqa: F401
    except ModuleNotFoundError:
        run([sys.executable, "-m", "pip", "install", "--upgrade", "pyinstaller"])


def build() -> None:
    clean_previous_build()
    ensure_pyinstaller()

    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--windowed",
        "--name",
        APP_NAME,
        "--exclude-module",
        "pytest",
        "--exclude-module",
        "unittest",
        str(ENTRYPOINT),
    ]
    run(command)

    exe_path = DIST_DIR / f"{APP_NAME}.exe"
    print()
    print(f"EXE listo: {exe_path}")
    print("Nota: ffmpeg debe estar instalado en Windows para convertir MP3 y unir algunos MP4.")


if __name__ == "__main__":
    build()
