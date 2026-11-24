"""Primitives de dessin bas niveau pour le rendu PDF Delivra.

ReportLab est impératif : cette couche encapsule les gestes graphiques
(typographie, filets, badges, arrondis, ombres, dégradés) réutilisés par
`render_pdf`. Rien ici ne connaît le contenu métier d'un livrable.
"""
from __future__ import annotations

import io
import os
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from reportlab.lib.colors import Color, HexColor
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from .theme import FONT_DIR, WEIGHTS, Style, darken, hex_to_rgb, lighten, mix

_REGISTERED = False


def register_fonts() -> None:
    """Enregistre une fois les familles embarquées auprès de ReportLab."""
    global _REGISTERED
    if _REGISTERED:
        return
    for family, weights in WEIGHTS.items():
        for w in weights:
            name = "DL-%s-%d" % (family, w)
            path = FONT_DIR / f"{family}-{w}.ttf"
            if path.exists() and name not in pdfmetrics.getRegisteredFontNames():
                pdfmetrics.registerFont(TTFont(name, str(path)))
    _REGISTERED = True


def color(value: str, alpha: float = 1.0) -> Color:
    r, g, b = hex_to_rgb(value)
    return Color(r / 255, g / 255, b / 255, alpha=alpha)


# --------------------------------------------------------------------------- #
#  Police embarquée                                                           #
# --------------------------------------------------------------------------- #
class Painter:
    """Enveloppe un canvas ReportLab avec les primitives du design system."""

    def __init__(self, c: canvas.Canvas, style: Style):
        self.c = c
        self.s = style
        self.page_w, self.page_h = style.page_w_pt, style.page_h_pt
        register_fonts()

    # -- couleurs / polices ---------------------------------------------- #
    def fill(self, value: str, alpha: float = 1.0) -> None:
        self.c.setFillColor(color(value, alpha))

    def stroke(self, value: str, width: float = 0.8, alpha: float = 1.0) -> None:
        self.c.setStrokeColor(color(value, alpha))
        self.c.setLineWidth(width)

    def font(self, family: str, weight: int, size: float) -> None:
        from .theme import resolve_weight
        self.c.setFont("DL-%s-%d" % (family, resolve_weight(family, weight)), size)

    def heading(self, size: float, weight: int = 700) -> None:
        self.font(self.s.heading_family, weight, size)

    def body(self, size: float, weight: int = 400) -> None:
        self.font(self.s.body_family, weight, size)

    def mono(self, size: float, weight: int = 400) -> None:
        self.font("JetBrainsMono", weight, size)

    # -- mesures ---------------------------------------------------------- #
    def text_width(self, text: str) -> float:
        return self.c.stringWidth(text, self.c._fontname, self.c._fontsize)

    def wrap(self, text: str, max_width: float, size: float) -> List[str]:
        """Retourne des lignes sans débordement.

        Les mots plus larges que la colonne (URL, identifiants, suites de
        caractères) sont découpés caractère par caractère pour ne jamais
        dépasser la marge imprimable.
        """
        self.c.setFont(self.c._fontname, size)

        def hard_split(word: str) -> List[str]:
            pieces, current = [], ""
            for ch in word:
                if current and self.text_width(current + ch) > max_width:
                    pieces.append(current)
                    current = ch
                else:
                    current += ch
            if current:
                pieces.append(current)
            return pieces or [""]

        lines: List[str] = []
        for paragraph in (text or "").split("\n"):
            current = ""
            for word in paragraph.split(" "):
                candidate = f"{current} {word}".strip()
                if self.text_width(candidate) <= max_width:
                    current = candidate
                    continue
                if current:
                    lines.append(current)
                    current = ""
                if self.text_width(word) <= max_width:
                    current = word
                else:
                    chunks = hard_split(word)
                    lines.extend(chunks[:-1])
                    current = chunks[-1]
            if current:
                lines.append(current)
            elif paragraph == "":
                lines.append("")
        return lines or [""]

    def para(self, text: str, x: float, y: float, width: float, size: float,
             leading: float, value: Optional[str] = None, weight: int = 400,
             align: str = "left", family: Optional[str] = None) -> float:
        """Écrit un paragraphe et retourne le y du curseur après écriture."""
        self.font(family or self.s.body_family, weight, size)
        self.fill(value or self.s.ink)
        lines = self.wrap(text, width, size)
        cursor = y
        for line in lines:
            if align == "center":
                tw = self.text_width(line)
                self.c.drawString(x + (width - tw) / 2, cursor - size, line)
            elif align == "right":
                tw = self.text_width(line)
                self.c.drawString(x + width - tw, cursor - size, line)
            elif align == "justify" and len(lines) > 1 and line is not lines[-1]:
                self._draw_justified(line, x, cursor - size, width, size)
            else:
                self.c.drawString(x, cursor - size, line)
            cursor -= leading
        return cursor

    def _draw_justified(self, line: str, x: float, y: float, width: float, size: float) -> None:
        words = line.split(" ")
        if len(words) < 2:
            self.c.drawString(x, y, line)
            return
        natural = self.text_width(line)
        gap = (width - natural) / (len(words) - 1)
        cx = x
        for w in words:
            self.c.drawString(cx, y, w)
            cx += self.text_width(w) + self.c._spaceWidth * size + gap \
                if hasattr(self.c, "_spaceWidth") else self.text_width(w) + gap + 2.2

    # -- formes ----------------------------------------------------------- #
    def rect(self, x: float, y: float, w: float, h: float, radius: float = 0.0,
             fill_value: Optional[str] = None, stroke_value: Optional[str] = None,
             line_width: float = 0.8, alpha: float = 1.0) -> None:
        if fill_value:
            self.fill(fill_value, alpha)
        if stroke_value:
            self.stroke(stroke_value, line_width)
        if radius > 0:
            self.c.roundRect(x, y, w, h, radius, stroke=1 if stroke_value else 0,
                             fill=1 if fill_value else 0)
        else:
            self.c.rect(x, y, w, h, stroke=1 if stroke_value else 0,
                        fill=1 if fill_value else 0)

    def hline(self, x1: float, x2: float, y: float, value: str, width: float = 0.7,
              alpha: float = 1.0) -> None:
        self.stroke(value, width, alpha)
        self.c.line(x1, y, x2, y)

    def gradient(self, x: float, y: float, w: float, h: float,
                 c1: str, c2: str, steps: int = 90, vertical: bool = True) -> None:
        """Dégradé par bandes : rendu net et compatible XPS/PDF."""
        self.c.saveState()
        self.c.clipPath(_rect_path(self.c, x, y, w, h), stroke=0, fill=0)
        for i in range(steps):
            t = i / max(1, steps - 1)
            col = color(mix(c1, c2, t), 1.0)
            self.c.setFillColor(col)
            if vertical:
                self.c.rect(x, y + h * i / steps, w, h / steps + 0.6, stroke=0, fill=1)
            else:
                self.c.rect(x + w * i / steps, y, w / steps + 0.6, h, stroke=0, fill=1)
        self.c.restoreState()

    def badge(self, text: str, x: float, y: float, *, bg: Optional[str] = None,
              fg: Optional[str] = None, size: float = 8.2, pad_x: float = 8,
              height: float = 17, radius: float = 8.5, weight: int = 700) -> float:
        self.body(size, weight)
        w = self.text_width(text.upper()) + pad_x * 2
        self.rect(x, y, w, height, radius=radius, fill_value=bg or lighten(self.s.primary, 0.88))
        self.fill(fg or darken(self.s.primary, 0.12))
        self.c.drawString(x + pad_x, y + (height - size) / 2 + 1.1, text.upper())
        return w

    def pill(self, text: str, x: float, y: float, *, bg: str, fg: str,
             size: float = 8.4, height: float = 18) -> float:
        self.body(size, 600)
        w = self.text_width(text) + 20
        self.rect(x, y, w, height, radius=height / 2, fill_value=bg)
        self.fill(fg)
        self.c.drawString(x + 10, y + (height - size) / 2 + 1.2, text)
        return w

    # -- images ----------------------------------------------------------- #
    def image(self, source: Any, x: float, y: float, w: float, h: float,
              mode: str = "contain") -> bool:
        """Place une image (chemin, bytes, PIL) recadrée ou ajustée."""
        try:
            img = _open_image(source)
        except Exception:
            return False
        if img is None:
            return False
        iw, ih = img.size
        if not iw or not ih:
            return False
        sx, sy = w / iw, h / ih
        scale = max(sx, sy) if mode == "cover" else min(sx, sy)
        dw, dh = iw * scale, ih * scale
        self.c.saveState()
        self.c.clipPath(_rect_path(self.c, x, y, w, h), stroke=0, fill=0)
        self.c.drawImage(ImageReader(img), x + (w - dw) / 2, y + (h - dh) / 2,
                         dw, dh, mask="auto")
        self.c.restoreState()
        return True

    def image_natural(self, source: Any, x: float, y: float, max_w: float,
                      max_h: float) -> Tuple[float, float, float, float]:
        """Retourne (x, y, w, h) d'une image insérée sans déformation."""
        img = _open_image(source)
        if img is None:
            return x, y, 0, 0
        iw, ih = img.size
        scale = min(max_w / iw, max_h / ih, 1.0 if iw <= max_w else 10)
        scale = min(max_w / iw, max_h / ih)
        return x, y + (max_h - ih * scale) / 2, iw * scale, ih * scale


def _open_image(source: Any):
    from PIL import Image
    if source is None:
        return None
    if hasattr(source, "size") and hasattr(source, "convert"):
        return source.convert("RGB")
    if isinstance(source, (bytes, bytearray)):
        return Image.open(io.BytesIO(source)).convert("RGB")
    if isinstance(source, (str, os.PathLike)):
        p = Path(source)
        if p.exists():
            return Image.open(p).convert("RGB")
    return None


def _rect_path(c: canvas.Canvas, x: float, y: float, w: float, h: float):
    p = c.beginPath()
    p.rect(x, y, w, h)
    return p
