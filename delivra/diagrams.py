"""Génération d'images « text to image » : schémas d'architecture, bandeaux de
couverture, motifs et visuels de section, rendus avec Pillow en haute définition.
"""
from __future__ import annotations

import io
import math
import random
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from .theme import FONT_DIR, Style, darken, hex_to_rgb, lighten, mix, readable_on

_FONT_CACHE: Dict[Tuple[str, int], ImageFont.FreeTypeFont] = {}


def font(family: str, weight: int = 400, size: int = 24) -> ImageFont.FreeTypeFont:
    from .theme import resolve_weight
    w = resolve_weight(family, weight)
    key = (family, w)
    if key not in _FONT_CACHE:
        path = FONT_DIR / f"{family}-{w}.ttf"
        try:
            _FONT_CACHE[key] = ImageFont.truetype(str(path), size)
        except Exception:
            _FONT_CACHE[key] = ImageFont.load_default()
    f = _FONT_CACHE[key]
    try:
        return f.font_variant(size=size)
    except Exception:
        return ImageFont.truetype(str(FONT_DIR / f"{family}-{w}.ttf"), size)


def _rgb(v: str) -> Tuple[int, int, int]:
    return hex_to_rgb(v)


def _rounded(draw: ImageDraw.ImageDraw, box, radius: int, fill=None, outline=None, width: int = 2) -> None:
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def _text_center(draw, cx: float, cy: float, text: str, f, fill) -> None:
    bbox = draw.textbbox((0, 0), text, font=f)
    draw.text((cx - (bbox[2] - bbox[0]) / 2, cy - (bbox[3] - bbox[1]) / 2 - bbox[1] / 2), text, font=f, fill=fill)


def _truncate(draw, text: str, f, max_w: int) -> str:
    if draw.textlength(text, font=f) <= max_w:
        return text
    while text and draw.textlength(text + "…", font=f) > max_w:
        text = text[:-1]
    return text + "…"


# --------------------------------------------------------------------------- #
#  Schéma d'architecture                                                      #
# --------------------------------------------------------------------------- #
def architecture_png(layers: Sequence[Dict[str, Any]], style: Style,
                     caption: Optional[str] = None, width_px: int = 2400,
                     scale: int = 2) -> bytes:
    """Schéma en couches avec nœuds, flèches de flux et légende.

    Rendu en 2× puis réduction (anti-aliasing) pour un tracé net à l'impression.
    """
    W = width_px
    pad = 56
    header_h = 96
    row_h = 116
    gap = 40
    cap_h = 60 if caption else 0
    n = max(1, len(layers))
    H = pad + header_h + n * row_h + (n - 1) * gap + pad + cap_h

    img = Image.new("RGB", (W, H), _rgb(mix(style.surface, "#FFFFFF", 0.5)))
    d = ImageDraw.Draw(img)

    # trame discrète
    grid = _rgb(mix(style.surface, "#FFFFFF", 0.22))
    for x in range(0, W, 44):
        d.line([(x, 0), (x, H)], fill=grid, width=1)
    for y in range(0, H, 44):
        d.line([(0, y), (W, y)], fill=grid, width=1)

    f_kicker = font(style.body_family, 700, 16)
    f_title = font(style.heading_family, 700, 27)
    f_layer = font(style.body_family, 700, 18)
    f_node = font(style.body_family, 600, 16)
    f_cap = font(style.body_family, 400, 17)

    d.text((pad, pad - 4), "ARCHITECTURE CIBLE", font=f_kicker, fill=_rgb(style.muted))
    d.text((pad, pad + 22), "Vue logique des composants et flux de données",
           font=f_title, fill=_rgb(style.ink))
    d.rectangle([pad, pad + header_h - 24, pad + 110, pad + header_h - 19], fill=_rgb(style.accent))

    tones = {
        "primary": (style.primary, "#FFFFFF"),
        "accent": (style.accent, readable_on(style.accent)),
        "dark": (style.dark, "#FFFFFF"),
        "neutral": (mix(style.surface, style.line, 0.45), style.ink),
    }

    inner_x0 = pad
    inner_x1 = W - pad
    tops: List[int] = []
    y = pad + header_h
    for layer in layers:
        tops.append(y)
        bg, fg = tones.get(layer.get("tone") or "neutral", tones["neutral"])
        _rounded(d, [inner_x0, y, inner_x1, y + row_h], 16, fill=_rgb(bg),
                 outline=_rgb(darken(bg, 0.10)), width=2)
        d.text((inner_x0 + 24, y + 18), (layer.get("title") or "").upper()[:44],
               font=f_layer, fill=_rgb(fg))
        nodes = layer.get("nodes") or []
        if nodes:
            nx0 = inner_x0 + 24
            avail = (inner_x1 - 24) - nx0
            g = 14
            nw = max(100.0, (avail - g * (len(nodes) - 1)) / len(nodes))
            box_top = y + 52
            box_bottom = y + row_h - 16
            node_bg = mix(bg, "#FFFFFF", 0.66)
            for ni, node in enumerate(nodes):
                nx = nx0 + ni * (nw + g)
                _rounded(d, [nx, box_top, nx + nw, box_bottom], 9, fill=_rgb(node_bg),
                         outline=_rgb(mix(bg, "#FFFFFF", 0.30)), width=2)
                label = _truncate(d, node, f_node, int(nw) - 24)
                _text_center(d, nx + nw / 2, (box_top + box_bottom) / 2, label,
                             f_node, _rgb(readable_on(node_bg)))
        y += row_h + gap

    # flèches de flux : strictement dans les interstices
    for i in range(n - 1):
        y_from = tops[i] + row_h
        y_to = tops[i + 1]
        cx = W / 2
        d.line([(cx, y_from + 3), (cx, y_to - 15)], fill=_rgb(style.muted), width=4)
        d.polygon([(cx - 11, y_to - 17), (cx + 11, y_to - 17), (cx, y_to - 2)],
                  fill=_rgb(style.muted))

    if caption:
        d.text((pad, H - cap_h + 14), _truncate(d, caption, f_cap, W - pad * 2),
               font=f_cap, fill=_rgb(style.muted))

    out = io.BytesIO()
    img.resize((W // scale, H // scale), Image.LANCZOS).save(out, format="PNG", optimize=True)
    return out.getvalue()


# --------------------------------------------------------------------------- #
#  Visuels « text to image » : couverture & motifs                            #
# --------------------------------------------------------------------------- #
def cover_art_png(style: Style, title: str = "", seed: int = 7,
                  width_px: int = 2480, height_px: int = 1800) -> bytes:
    """Bandeau de couverture abstrait : dégradés, maillage et halo.

    Utilisable comme image de fond de couverture (brand.cover_image) ou comme
    illustration autonome depuis l'assistant.
    """
    rnd = random.Random(seed)
    W, H = width_px, height_px
    base = Image.new("RGB", (W, H), _rgb(style.dark))
    px = base.load()
    c1 = _rgb(mix(style.dark, style.primary, 0.55))
    c2 = _rgb(style.dark)
    for y in range(H):
        t = y / H
        row = tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))
        for x in range(W):
            px[x, y] = row

    overlay = Image.new("RGB", (W, H), (0, 0, 0))
    od = ImageDraw.Draw(overlay)
    # maillage de courbes
    for i in range(14):
        pts = []
        amp = rnd.randint(30, 120)
        phase = rnd.random() * math.tau
        yy = int(H * (i / 14)) + rnd.randint(-20, 20)
        for x in range(0, W + 20, 20):
            pts.append((x, yy + int(amp * math.sin(x / 320 + phase))))
        od.line(pts, fill=_rgb(mix(style.primary, "#FFFFFF", 0.35)), width=rnd.choice([1, 1, 2]))
    overlay = overlay.filter(ImageFilter.GaussianBlur(0.6))
    base = Image.blend(base, Image.blend(base, overlay, 0.5), 0.22)

    # halos
    glow = Image.new("RGB", (W, H), (0, 0, 0))
    gd = ImageDraw.Draw(glow)
    for _ in range(3):
        cx, cy = rnd.randint(W // 3, W), rnd.randint(0, H // 2)
        r = rnd.randint(220, 520)
        gd.ellipse([cx - r, cy - r, cx + r, cy + r],
                   fill=_rgb(mix(style.accent, style.primary, rnd.random() * 0.6)))
    glow = glow.filter(ImageFilter.GaussianBlur(180))
    base = Image.blend(base, glow, 0.42)

    # grain léger
    grain = Image.effect_noise((W, H), 12).convert("RGB")
    base = Image.blend(base, grain, 0.03)

    if title:
        d = ImageDraw.Draw(base)
        f = font(style.heading_family, 800, 92)
        d.text((110, H - 260), title[:40], font=f, fill=(255, 255, 255))
    out = io.BytesIO()
    base.save(out, format="PNG", optimize=True)
    return out.getvalue()


def pattern_png(style: Style, width_px: int = 1600, height_px: int = 900,
                seed: int = 3) -> bytes:
    """Motif géométrique sobre pour habiller une section ou un intercalaire."""
    rnd = random.Random(seed)
    W, H = width_px, height_px
    img = Image.new("RGB", (W, H), _rgb(mix(style.primary, "#FFFFFF", 0.93)))
    d = ImageDraw.Draw(img)
    for _ in range(60):
        x, y = rnd.randint(0, W), rnd.randint(0, H)
        s = rnd.randint(20, 160)
        col = mix(style.primary, style.accent, rnd.random())
        if rnd.random() > 0.5:
            d.ellipse([x - s, y - s, x + s, y + s], outline=_rgb(lighten(col, 0.55)), width=rnd.choice([2, 3]))
        else:
            d.rounded_rectangle([x - s, y - s / 2, x + s, y + s / 2], radius=18,
                                outline=_rgb(lighten(col, 0.55)), width=2)
    img = img.filter(ImageFilter.GaussianBlur(0.8))
    out = io.BytesIO()
    img.save(out, format="PNG", optimize=True)
    return out.getvalue()


def blank_capture_placeholder(style: Style, label: str = "Capture d'écran",
                              width_px: int = 1600, height_px: int = 1000) -> bytes:
    """Image de remplacement élégante si aucune capture n'est encore fournie."""
    img = Image.new("RGB", (width_px, height_px), _rgb(mix(style.surface, "#FFFFFF", 0.3)))
    d = ImageDraw.Draw(img)
    _rounded(d, [30, 30, width_px - 30, height_px - 30], 24,
             outline=_rgb(mix(style.line, style.muted, 0.25)), width=4)
    f = font(style.body_family, 600, 34)
    _text_center(d, width_px / 2, height_px / 2, label, f, _rgb(style.muted))
    out = io.BytesIO()
    img.save(out, format="PNG")
    return out.getvalue()
