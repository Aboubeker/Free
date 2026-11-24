"""Script de construction de l'exécutable autonome.

Usage :
    python -m delivra.build              # construit avec PyInstaller
    python -m delivra.build --zip        # construit puis crée l'archive

Sous Windows, le résultat est `dist/Delivra/Delivra.exe`.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
BUILD = ROOT / "build"


def ensure_deps() -> None:
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        print("PyInstaller absent — installation…")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller>=6.3"])


def make_icon() -> None:
    script = ROOT / "packaging" / "make_icon.py"
    if script.exists():
        subprocess.check_call([sys.executable, str(script)])


def build() -> Path:
    ensure_deps()
    make_icon()
    cmd = [sys.executable, "-m", "PyInstaller", str(ROOT / "delivra.spec"),
           "--noconfirm", "--clean", "--distpath", str(DIST), "--workpath", str(BUILD)]
    print("›", " ".join(cmd))
    subprocess.check_call(cmd, cwd=ROOT)
    target = DIST / "Delivra"
    exe = target / ("Delivra.exe" if sys.platform.startswith("win") else "Delivra")
    if not exe.exists():
        raise SystemExit(f"Échec : binaire introuvable ({exe})")
    size = sum(f.stat().st_size for f in target.rglob("*") if f.is_file())
    print(f"\n✓ Exécutable prêt : {exe}")
    print(f"  Poids total : {size / 1024 / 1024:.1f} Mo")
    return exe


def make_zip() -> Path:
    name = f"Delivra-{sys.platform}-" + ("x64" if sys.maxsize > 2**32 else "x86")
    archive = DIST / f"{name}.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as z:
        for f in (DIST / "Delivra").rglob("*"):
            if f.is_file():
                z.write(f, f.relative_to(DIST))
    print(f"✓ Archive : {archive}")
    return archive


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Construit l'exécutable Delivra")
    parser.add_argument("--zip", action="store_true", help="crée une archive zip après compilation")
    parser.add_argument("--skip-build", action="store_true")
    args = parser.parse_args(argv)
    if not args.skip_build:
        build()
    if args.zip:
        make_zip()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
