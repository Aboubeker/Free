"""Vérifie que toutes les ressources nécessaires sont bien listées dans le spec.

    python tools/check_frozen_data.py

À exécuter après modification du dossier `delivra/` (assets, static…).
"""
from __future__ import annotations
import ast, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "delivra.spec"


def main() -> int:
    spec = SPEC.read_text()
    required = {
        "delivra/static": ROOT / "delivra" / "static",
        "delivra/assets/fonts": ROOT / "delivra" / "assets" / "fonts",
    }
    problems = []
    for dest, path in required.items():
        if not path.exists():
            problems.append(f"Dossier source manquant : {path}")
        if dest not in spec:
            problems.append(f"Destination absente du spec : {dest}")

    # chaque fichier statique doit être couvert par le dossier
    static = list((ROOT / "delivra" / "static").rglob("*"))
    fonts = list((ROOT / "delivra" / "assets" / "fonts").glob("*.ttf"))
    print(f"Fichiers statiques : {len([f for f in static if f.is_file()])}")
    print(f"Polices embarquées : {len(fonts)}")

    # contrôle des modules importés dynamiquement
    ast.parse(spec, filename="delivra.spec")
    for mod in ("pypdfium2", "docx", "pptx", "runpy"):
        if mod not in spec:
            problems.append(f"hiddenimports : {mod} manquant")

    if problems:
        print("\n".join("✗ " + p for p in problems))
        return 1
    print("✓ Le spec couvre les ressources nécessaires")
    return 0


if __name__ == "__main__":
    sys.exit(main())
