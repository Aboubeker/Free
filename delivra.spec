# -*- mode: python ; coding: utf-8 -*-
"""Configuration PyInstaller de Delivra.

    pyinstaller delivra.spec --noconfirm

Produit :
    dist/Delivra/Delivra.exe      (Windows, mode dossier, démarrage rapide)
    dist/Delivra                  (Linux/macOS : binaire + dossier)
"""
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

ROOT = Path(SPECPATH).resolve()
APP = ROOT / "delivra"

datas = [
    (str(APP / "static"), "delivra/static"),
    (str(APP / "assets" / "fonts"), "delivra/assets/fonts"),
]
# ressources éventuelles (icônes, modèles)
for extra in ("assets", "templates"):
    p = APP / extra
    if p.exists() and extra != "assets":
        datas.append((str(p), f"delivra/{extra}"))

hiddenimports = (
    collect_submodules("delivra")
    + [
        "reportlab.pdfbase._fontdata",
        "reportlab.graphics.barcode",
        "reportlab.graphics.charts",
        "pypdfium2",
        "pypdfium2_raw",
        "docx",
        "pptx",
        "PIL._tkinter_finder",
        "flask",
        "werkzeug",
        "jinja2",
        "waitress",
        "runpy",
    ]
)

icon_path = ROOT / "packaging" / ("delivra.ico" if sys.platform.startswith("win") else "delivra.png")
icon = str(icon_path) if icon_path.exists() else None

a = Analysis(
    [str(APP / "desktop.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "numpy", "pandas", "scipy", "pytest", "pip", "playwright"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Delivra",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,          # application fenêtrée : pas de console noire
    disable_windowed_traceback=False,
    icon=icon,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="Delivra",
)
