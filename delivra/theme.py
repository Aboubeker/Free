"""Système de design de Delivra : palettes, typographies, métriques.

Tout le rendu (PDF, aperçu web, PPTX, DOCX) puise ses couleurs et polices ici,
afin que le document soit visuellement cohérent quel que soit le format exporté.
"""
from __future__ import annotations

import colorsys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ASSETS = Path(__file__).resolve().parent / "assets"
FONT_DIR = ASSETS / "fonts"

# --------------------------------------------------------------------------- #
#  Palettes                                                                   #
# --------------------------------------------------------------------------- #
PALETTES: Dict[str, Dict[str, Any]] = {
    "ocean": {
        "label": "Océan", "primary": "#0B5FFF", "accent": "#00C2A8",
        "dark": "#0A1930", "ink": "#16202E", "muted": "#5B6B7F",
        "surface": "#F4F7FC", "line": "#DCE4EF", "cover": "deep",
    },
    "nuit": {
        "label": "Nuit", "primary": "#6D5BFF", "accent": "#FF6B9A",
        "dark": "#0D0B1F", "ink": "#1B1830", "muted": "#66628A",
        "surface": "#F5F4FB", "line": "#E2DFF2", "cover": "gradient",
    },
    "emeraude": {
        "label": "Émeraude", "primary": "#0E7C5A", "accent": "#F2B84B",
        "dark": "#06251C", "ink": "#132A23", "muted": "#5B7268",
        "surface": "#F2F8F5", "line": "#D8E8E0", "cover": "deep",
    },
    "graphite": {
        "label": "Graphite", "primary": "#243044", "accent": "#E4572E",
        "dark": "#121A26", "ink": "#1D2634", "muted": "#6A7688",
        "surface": "#F5F6F8", "line": "#E0E4EA", "cover": "minimal",
    },
    "sable": {
        "label": "Sable", "primary": "#A8742B", "accent": "#2F6F62",
        "dark": "#2A2119", "ink": "#332B22", "muted": "#7C6F5F",
        "surface": "#FBF7F0", "line": "#EAE0CF", "cover": "deep",
    },
    "bordeaux": {
        "label": "Bordeaux", "primary": "#8C1D3F", "accent": "#D4A04C",
        "dark": "#2B0A16", "ink": "#331620", "muted": "#7A6169",
        "surface": "#FBF5F6", "line": "#EDDDE1", "cover": "gradient",
    },
}

# --------------------------------------------------------------------------- #
#  Typographies                                                               #
# --------------------------------------------------------------------------- #
# `heading` / `body` référencent des familles réellement embarquées.
FONT_STACKS: Dict[str, Dict[str, str]] = {
    "manrope":      {"label": "Manrope · moderne",       "heading": "Manrope",      "body": "Manrope"},
    "sora":         {"label": "Sora · technologique",    "heading": "Sora",         "body": "Manrope"},
    "serif":        {"label": "Source Serif · éditorial", "heading": "SourceSerif", "body": "SourceSerif"},
    "serif-mix":    {"label": "Serif / Sans · mixte",    "heading": "SourceSerif",  "body": "Manrope"},
    "technical":    {"label": "Sora / Mono · technique", "heading": "Sora",         "body": "Manrope"},
}

# Poids réellement présents sur disque pour chaque famille.
WEIGHTS = {
    "Manrope": [400, 500, 600, 700, 800],
    "SourceSerif": [400, 600, 700],
    "Sora": [400, 600, 700, 800],
    "JetBrainsMono": [400, 500, 700],
}


def resolve_weight(family: str, requested: int) -> int:
    """Renvoie le poids disponible le plus proche (ex. SourceSerif 800 → 700)."""
    avail = WEIGHTS.get(family) or [400]
    return min(avail, key=lambda w: (abs(w - requested), -w))


def hex_to_rgb(value: str) -> Tuple[int, int, int]:
    v = value.lstrip("#")
    if len(v) == 3:
        v = "".join(c * 2 for c in v)
    return tuple(int(v[i:i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def rgb_to_hex(rgb: Tuple[int, int, int]) -> str:
    return "#%02X%02X%02X" % rgb


def mix(a: str, b: str, t: float) -> str:
    """Mélange linéaire entre deux couleurs hex (t=0 → a, t=1 → b)."""
    ra, ga, ba = hex_to_rgb(a)
    rb, gb, bb = hex_to_rgb(b)
    return rgb_to_hex((round(ra + (rb - ra) * t), round(ga + (gb - ga) * t), round(ba + (bb - ba) * t)))


def lighten(color: str, t: float) -> str:
    return mix(color, "#FFFFFF", t)


def darken(color: str, t: float) -> str:
    return mix(color, "#000000", t)


def readable_on(background: str) -> str:
    """Retourne blanc ou encre selon la luminance du fond (contraste AA)."""
    r, g, b = (c / 255 for c in hex_to_rgb(background))
    lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
    return "#0B1220" if lum > 0.62 else "#FFFFFF"


def tonal_ramp(base: str, steps: int = 5) -> List[str]:
    """Dégradé harmonieux (clair → base → sombre) utile pour les couvertures."""
    out = []
    for i in range(steps):
        t = i / max(1, steps - 1)
        if t < 0.5:
            out.append(mix(lighten(base, 0.55), base, t * 2))
        else:
            out.append(mix(base, darken(base, 0.55), (t - 0.5) * 2))
    return out


# --------------------------------------------------------------------------- #
#  Résolution du style                                                        #
# --------------------------------------------------------------------------- #
DEFAULT_STYLE: Dict[str, Any] = {
    "palette": "ocean",
    "typography": "manrope",
    "primary": None,       # override manuel éventuel
    "accent": None,
    "density": "normal",   # compact | normal | aéré
    "paper": "A4",         # A4 | Letter
    "cover_style": None,
}


class Style:
    """Style résolu, prêt à consommer par les moteurs de rendu."""

    def __init__(self, data: Optional[Dict[str, Any]] = None):
        d = {**DEFAULT_STYLE, **(data or {})}
        palette = PALETTES.get(d.get("palette") or "ocean", PALETTES["ocean"])
        self.palette_key = d.get("palette") if d.get("palette") in PALETTES else "ocean"
        self.palette = palette
        self.primary = d.get("primary") or palette["primary"]
        self.accent = d.get("accent") or palette["accent"]
        self.dark = palette["dark"]
        self.ink = palette["ink"]
        self.muted = palette["muted"]
        self.surface = palette["surface"]
        self.line = palette["line"]
        self.cover_style = d.get("cover_style") or palette.get("cover", "deep")
        stack = FONT_STACKS.get(d.get("typography") or "manrope", FONT_STACKS["manrope"])
        self.typography_key = d.get("typography") if d.get("typography") in FONT_STACKS else "manrope"
        self.font_label = stack["label"]
        self.heading_family = stack["heading"]
        self.body_family = stack["body"]
        self.mono_family = "JetBrainsMono"
        self.density = d.get("density") if d.get("density") in ("compact", "normal", "aere") else "normal"
        self.paper = d.get("paper") or "A4"

    # -- helpers ---------------------------------------------------------- #
    @property
    def spacing(self) -> float:
        return {"compact": 0.82, "normal": 1.0, "aere": 1.22}.get(self.density, 1.0)

    @property
    def page_size_mm(self) -> Tuple[float, float]:
        return (215.9, 279.4) if self.paper == "Letter" else (210.0, 297.0)

    @property
    def page_w_pt(self) -> float:
        return round(self.page_size_mm[0] * 72 / 25.4, 2)

    @property
    def page_h_pt(self) -> float:
        return round(self.page_size_mm[1] * 72 / 25.4, 2)

    def heading_font(self, weight: int = 700) -> str:
        return "DL-%s-%d" % (self.heading_family, resolve_weight(self.heading_family, weight))

    def body_font(self, weight: int = 400) -> str:
        return "DL-%s-%d" % (self.body_family, resolve_weight(self.body_family, weight))

    def mono_font(self, weight: int = 400) -> str:
        return "DL-JetBrainsMono-%d" % resolve_weight("JetBrainsMono", weight)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "palette": self.palette_key, "typography": self.typography_key,
            "primary": self.primary, "accent": self.accent, "dark": self.dark,
            "ink": self.ink, "muted": self.muted, "surface": self.surface,
            "line": self.line, "cover_style": self.cover_style, "density": self.density,
            "paper": self.paper, "font_label": self.font_label,
            "heading_family": self.heading_family, "body_family": self.body_family,
        }


def catalog() -> Dict[str, Any]:
    return {
        "palettes": [{"key": k, **v} for k, v in PALETTES.items()],
        "typographies": [{"key": k, **v} for k, v in FONT_STACKS.items()],
        "densities": [
            {"key": "compact", "label": "Compact"},
            {"key": "normal", "label": "Équilibré"},
            {"key": "aere", "label": "Aéré"},
        ],
        "papers": [{"key": "A4", "label": "A4 · 210 × 297 mm"},
                   {"key": "Letter", "label": "US Letter · 8.5 × 11 in"}],
    }
