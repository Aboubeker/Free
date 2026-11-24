"""Télécharge les polices libres (Google Fonts, licence OFL) et génère des
instances statiques utilisables par ReportLab / Pillow.

Usage :  python tools/fetch_fonts.py
"""
from __future__ import annotations
import json, os, sys, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FONT_DIR = ROOT / "delivra" / "assets" / "fonts"
FONT_DIR.mkdir(parents=True, exist_ok=True)

FAMILIES = {
    "Manrope":     {"path": "ofl/manrope/Manrope%5Bwght%5D.ttf",                    "axes": {"wght": [400, 500, 600, 700, 800]}, "kind": "sans"},
    "SourceSerif": {"path": "ofl/sourceserif4/SourceSerif4%5Bopsz,wght%5D.ttf",     "axes": {"wght": [400, 600, 700]}, "pinned": {"opsz": 22}, "kind": "serif"},
    "Sora":        {"path": "ofl/sora/Sora%5Bwght%5D.ttf",                          "axes": {"wght": [400, 600, 700, 800]}, "kind": "display"},
    "JetBrainsMono": {"path": "ofl/jetbrainsmono/JetBrainsMono%5Bwght%5D.ttf",      "axes": {"wght": [400, 500, 700]}, "kind": "mono"},
}
API = "https://api.github.com/repos/google/fonts/contents/{}"


def download(url: str, raw: bool = False) -> bytes:
    headers = {"User-Agent": "delivra-font-fetch"}
    if raw:
        headers["Accept"] = "application/vnd.github.raw"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=90) as r:
        return r.read()


def main() -> int:
    for name, spec in FAMILIES.items():
        raw = download(API.format(spec["path"]), raw=True)
        var_path = FONT_DIR / f"{name}-Var.ttf"
        var_path.write_bytes(raw)
        print(f"↓ {name}: {len(raw)//1024} Ko")
        try:
            from fontTools.ttLib import TTFont
            from fontTools.varLib.instancer import instantiateVariableFont
        except ImportError:
            print("  ! fonttools manquant, instances statiques ignorées")
            continue
        for weight in spec["axes"]["wght"]:
            font = TTFont(var_path)
            loc = {"wght": weight, **spec.get("pinned", {})}
            inst = instantiateVariableFont(font, loc, updateFontNames=False, optimize=True)
            out = FONT_DIR / f"{name}-{weight}.ttf"
            inst.save(out)
            print(f"  → {out.name} ({out.stat().st_size//1024} Ko)")
        var_path.unlink(missing_ok=True)
        lic = download(API.format("ofl/%s/OFL.txt" % {
            "Manrope": "manrope", "SourceSerif": "sourceserif4", "Sora": "sora",
            "JetBrainsMono": "jetbrainsmono"}[name]), raw=True)
        (FONT_DIR / f"OFL-{name}.txt").write_bytes(lic)
    print("Terminé →", FONT_DIR)
    return 0


if __name__ == "__main__":
    sys.exit(main())
