"""Rendu PDF professionnel d'un livrable.

Le document comporte : couverture (4 variantes graphiques), page d'identité,
sommaire paginé, sections numérotées avec blocs riches, et page de signature.
Un système de « pages différées » (`_Deferred`) permet d'imprimer le sommaire
avec la vraie pagination : on compose le document une première fois, on
enregistre les numéros de page, puis on réémet le PDF final.
"""
from __future__ import annotations

import io
import math
from typing import Any, Dict, List, Optional, Tuple

from reportlab.pdfgen import canvas

from .pdfkit import Painter, _open_image, register_fonts
from .theme import Style, darken, lighten, mix, readable_on

MARGIN = {"left": 56.0, "right": 50.0, "top": 58.0, "bottom": 52.0}
CONTENT_W = None  # calculé par Document via style


class Document:
    def __init__(self, doc: Dict[str, Any], *, watermark: bool = True):
        self.doc = doc
        self.meta = doc.get("meta") or {}
        self.style = Style(doc.get("style"))
        self.options = doc.get("options") or {}
        self.buf = io.BytesIO()
        self.c = canvas.Canvas(self.buf, pagesize=(self.style.page_w_pt, self.style.page_h_pt))
        self.c.setTitle(self.meta.get("title") or "Livrable")
        self.c.setAuthor(self.meta.get("author") or "")
        self.c.setSubject(self.meta.get("subtitle") or self.meta.get("project") or "")
        self.c.setCreator("Delivra — agent de livrables")
        self.p = Painter(self.c, self.style)
        self.W, self.H = self.style.page_w_pt, self.style.page_h_pt
        self.left, self.right = MARGIN["left"], MARGIN["right"]
        self.top, self.bottom = MARGIN["top"], MARGIN["bottom"]
        self.content_w = self.W - self.left - self.right
        self.page_no = 0
        self.section_no = 0
        self.toc_pages: List[Tuple[str, int]] = []
        self._in_cover = False
        self._in_toc = False

    # ------------------------------------------------------------------ #
    #  Gestion des pages                                                  #
    # ------------------------------------------------------------------ #
    def new_page(self, footer: bool = True) -> None:
        """Clôt la page courante et en ouvre une nouvelle (source unique de vérité)."""
        if self.page_no:
            self._decorate(footer)
            self.c.showPage()
        self.page_no += 1
        self._in_cover = False
        self._sub_no = 0

    def _decorate(self, footer: bool = True) -> None:
        p, s = self.p, self.style
        if self._in_cover:
            return
        yo = 30
        if self.options.get("header", True) and self.page_no > 1:
            p.hline(self.left, self.W - self.right, self.H - 38, s.line, 0.6)
            p.body(7.6, 600)
            p.fill(s.muted)
            label = (self.meta.get("client") or self.meta.get("project") or "").upper()
            p.c.drawString(self.left, self.H - 32, label[:70])
            right = (self.meta.get("reference") or self.meta.get("version") and
                     f"v{self.meta.get('version')}" or "")
            if right:
                p.c.drawRightString(self.W - self.right, self.H - 32, right[:40])
        wm = (self.options.get("watermark") or "").strip()
        if wm:
            self.c.saveState()
            self.c.translate(self.W / 2, self.H / 2)
            self.c.rotate(38)
            p.heading(58, 800)
            p.fill(s.primary, 0.065)
            p.c.drawCentredString(0, 0, wm.upper()[:26])
            self.c.restoreState()
        if footer:
            p.hline(self.left, self.W - self.right, 44, s.line, 0.6)
            p.body(7.6, 500)
            p.fill(s.muted)
            txt = (self.options.get("footer_text") or "").strip()
            if txt:
                p.c.drawString(self.left, yo, f"{txt} · {self.meta.get('client') or ''}".strip(" ·")[:80])
            if self.options.get("page_numbers", True):
                p.mono(8, 500)
                p.fill(s.muted)
                p.c.drawRightString(self.W - self.right, yo, f"{self.page_no:02d}")

    def finish(self) -> bytes:
        if self.page_no == 0:
            self.new_page()
        self._decorate(True)
        self.c.showPage()
        self.c.save()
        return self.buf.getvalue()

    # ------------------------------------------------------------------ #
    #  Couverture                                                         #
    # ------------------------------------------------------------------ #
    def cover(self) -> None:
        p, s, m = self.p, self.style, self.meta
        self.new_page(footer=False)
        self._in_cover = True
        W, H = self.W, self.H
        variant = s.cover_style
        brand = self.doc.get("brand") or {}
        logo = brand.get("logo") or m.get("client_logo")
        cover_img = brand.get("cover_image")

        if variant == "minimal":
            p.fill("#FFFFFF")
            p.c.rect(0, 0, W, H, stroke=0, fill=1)
            p.rect(0, 0, 10, H, fill_value=s.primary)
            p.rect(10, H - 6, W - 10, 6, fill_value=s.accent)
            ink = s.ink
        elif variant == "gradient":
            p.gradient(0, 0, W, H, s.dark, mix(s.primary, s.dark, 0.45), steps=110)
            p.c.setFillColor(__import__("reportlab.lib.colors", fromlist=["Color"]).Color(1, 1, 1))
            ink = "#FFFFFF"
        else:  # deep
            p.fill(s.dark)
            p.c.rect(0, 0, W, H, stroke=0, fill=1)
            ink = "#FFFFFF"

        # halo décoratif / capture de couverture
        if cover_img:
            try:
                self.c.saveState()
                p.image(cover_img, 0, 0, W, H, mode="cover")
                p.fill(s.dark, 0.72)
                self.c.rect(0, 0, W, H, stroke=0, fill=1)
                self.c.restoreState()
            except Exception:
                pass

        if variant in ("deep", "gradient"):
            self.c.saveState()
            p.fill(s.accent, 0.09)
            self.c.circle(W - 40, H + 70, 165, stroke=0, fill=1)
            p.fill("#FFFFFF", 0.035)
            self.c.circle(W + 30, H - 120, 120, stroke=0, fill=1)
            p.fill(s.primary, 0.10)
            self.c.circle(self.left - 70, -75, 120, stroke=0, fill=1)
            self.c.restoreState()

        x = self.left
        y = H - 92

        # En-tête : logo + badge de confidentialité
        if logo:
            img = _open_image(logo)
            if img:
                iw, ih = img.size
                scale = min(min(170.0, self.content_w * 0.42) / iw, 48.0 / ih)
                self.c.drawImage(__import__("reportlab.lib.utils", fromlist=["ImageReader"]).ImageReader(img),
                                 x, y - 8, iw * scale, ih * scale, mask="auto", preserveAspectRatio=True)
                y -= 70
            else:
                y -= 6
        else:
            p.heading(15, 800)
            p.fill(ink)
            p.c.drawString(x, y, (m.get("author") or "DELIVRA").upper()[:28])
            y -= 26

        if m.get("author") and logo:
            p.body(8.6, 600)
            p.fill(mix(ink, s.dark, 0.5))
            p.c.drawString(x, y + 6, str(m["author"])[:60])
            y -= 20

        label = m.get("confidentiality", "CONFIDENTIEL").upper()
        p.body(8, 700)
        badge_w = p.text_width(label) + 22
        badge_bg = s.accent if variant != "minimal" else s.primary
        p.rect(x, y - 2, badge_w, 20, radius=10, fill_value=badge_bg)
        p.fill(readable_on(badge_bg))
        p.c.drawString(x + 11, y + 4.3, label)

        # Tags projet
        ty = H - 232
        tx = x
        for tag in (m.get("tags") or [])[:4]:
            p.body(7.4, 600)
            w = p.text_width(tag) + 18
            if tx + w > W - self.right:
                break
            p.rect(tx, ty, w, 19, radius=9.5, fill_value=mix(ink, s.dark, 0.3), alpha=0.18)
            p.fill(mix(ink, s.accent, 0.25) if variant != "minimal" else s.muted)
            p.c.drawString(tx + 9, ty + 6, tag)
            tx += w + 7

        # Titre principal
        title = m.get("title") or "Document de livraison"
        p.heading(37, 800)
        p.fill(ink)
        lines = p.wrap(title, W - self.left - self.right - 30, 37)
        if len(lines) > 3:
            lines = p.wrap(title, W - self.left - self.right - 30, 30)
            size = 30
        else:
            size = 37
        p.heading(size, 800)
        cy = H * 0.545 + (len(lines) - 1) * (size * 1.12) / 2
        for line in lines:
            if variant == "minimal":
                p.fill(s.primary)
            p.c.drawString(x, cy, line)
            cy -= size * 1.12

        # Sous-titre / solution
        sub = m.get("subtitle") or m.get("project")
        if sub:
            p.body(13.5, 500)
            p.fill(mix(ink, s.dark, 0.35) if variant != "minimal" else s.muted)
            sub_lines = p.wrap(sub, self.content_w - 60, 13.5)
            sy = cy - 10
            for line in sub_lines[:2]:
                p.c.drawString(x, sy, line)
                sy -= 19
            rules_y = sy - 6
        else:
            rules_y = cy - 4

        # Filet accent + mention solution déployée
        y2 = H * 0.235
        p.rect(x, y2 + 22, 46, 4, fill_value=(s.accent if variant != "minimal" else s.primary))
        p.body(8.2, 700)
        p.fill(mix(ink, s.dark, 0.25) if variant != "minimal" else s.muted)
        p.c.drawString(x, y2, "SOLUTION DÉPLOYÉE".upper())
        p.heading(15, 700)
        p.fill(ink)
        p.c.drawString(x, y2 - 24, (m.get("project") or m.get("industry") or "—")[:64])

        # Pied de couverture : client, date, référence
        fy = 74
        p.hline(x, W - self.right, fy + 34, mix(ink, s.dark, 0.6) if variant != "minimal" else s.line, 0.6, 0.5)
        col = self.content_w / 3
        for i, (label, value) in enumerate([
            ("CLIENT", m.get("client") or "—"),
            ("DATE", m.get("date") or ""),
            ("RÉFÉRENCE", (m.get("reference") or "") + (f" · v{m.get('version')}" if m.get("version") else "")),
        ]):
            cx = x + i * col
            p.body(7, 700)
            p.fill(mix(ink, s.dark, 0.42) if variant != "minimal" else s.muted)
            p.c.drawString(cx, fy + 6, label)
            p.body(9.6, 600)
            p.fill(ink if variant != "minimal" else s.ink)
            p.c.drawString(cx, fy - 9, (value or "—")[:34])

        if m.get("client_logo"):
            img = _open_image(m.get("client_logo"))
            if img:
                iw, ih = img.size
                scale = min(110 / iw, 34 / ih)
                self.c.drawImage(__import__("reportlab.lib.utils", fromlist=["ImageReader"]).ImageReader(img),
                                 W - self.right - iw * scale, H - 116, iw * scale, ih * scale, mask="auto")

        self._in_cover = True

    # ------------------------------------------------------------------ #
    #  Page d'identité (résumé exécutif + méta)                           #
    # ------------------------------------------------------------------ #
    def identity_page(self) -> None:
        p, s, m = self.p, self.style, self.meta
        self.new_page()
        y = self.H - self.top - 26
        p.body(8, 700)
        p.fill(s.primary)
        p.c.drawString(self.left, y, "SYNTHÈSE")
        y -= 36
        p.heading(24, 800)
        p.fill(s.ink)
        p.c.drawString(self.left, y, "Résumé exécutif")
        y -= 22
        p.rect(self.left, y, 44, 3.5, fill_value=s.accent)
        y -= 26

        summary = m.get("executive_summary") or self._fallback_summary()
        if self.options.get("summary_box", True):
            box_lines = p.wrap(summary, self.content_w - 48, 10.4)
            box_h = len(box_lines) * 16.6 + 40
            p.rect(self.left, y - box_h + 18, self.content_w, box_h, radius=10,
                   fill_value=lighten(s.primary, 0.945))
            p.rect(self.left, y - box_h + 18, 4, box_h, fill_value=s.primary)
            p.para(summary, self.left + 24, y, self.content_w - 46, 10.4, 16.6,
                   value=s.ink, weight=400, align="justify")
            y -= box_h + 26
        else:
            y = p.para(summary, self.left, y, self.content_w, 10.4, 16.6, align="justify") - 18

        # Bandeau de métadonnées
        p.body(7.6, 700)
        p.fill(s.muted)
        p.c.drawString(self.left, y, "INFORMATIONS CLÉS")
        p.hline(self.left, self.W - self.right, y - 8, s.line, 0.6)
        y -= 30
        pairs = [
            ("Client", m.get("client")), ("Projet", m.get("project")),
            ("Secteur", m.get("industry")), ("Version", m.get("version")),
            ("Date", m.get("date")), ("Référence", m.get("reference")),
            ("Auteur", m.get("author")), ("Destinataire", m.get("recipient")),
        ]
        pairs = [(k, v) for k, v in pairs if v]
        col_w = self.content_w / 2
        for i, (k, v) in enumerate(pairs):
            cx = self.left + (i % 2) * col_w
            cy = y - (i // 2) * 44
            p.body(7.2, 700)
            p.fill(s.muted)
            p.c.drawString(cx, cy, k.upper())
            p.body(10.4, 600)
            p.fill(s.ink)
            p.c.drawString(cx, cy - 15, str(v)[:48])
        y -= math.ceil(len(pairs) / 2) * 44 + 6

        # Points clés (extraits du document)
        highlights = self._highlights()
        if highlights:
            p.body(7.6, 700)
            p.fill(s.muted)
            p.c.drawString(self.left, y, "À RETENIR")
            p.hline(self.left, self.W - self.right, y - 8, s.line, 0.6)
            y -= 26
            for h in highlights[:4]:
                p.rect(self.left + 2, y - 3, 6, 6, radius=3, fill_value=s.accent)
                p.para(h, self.left + 18, y + 2, self.content_w - 18, 9.8, 15.2, value=s.ink)
                y -= 15.2 * max(1, len(p.wrap(h, self.content_w - 18, 9.8))) + 4

    def _fallback_summary(self) -> str:
        m = self.meta
        client = m.get("client") or "le client"
        project = m.get("project") or m.get("title") or "la solution"
        parts = [f"Ce document présente la livraison de {project} réalisée pour {client}."]
        secs = [s.get("title") for s in self.doc.get("sections") or [] if not s.get("hidden")]
        if secs:
            parts.append("Il couvre notamment : " + ", ".join(secs[:5]) + ".")
        parts.append("Il constitue le référentiel contractuel de la solution déployée et de son "
                     "exploitation, et peut être utilisé comme support de recette.")
        return " ".join(parts)

    def _highlights(self) -> List[str]:
        out = []
        for sec in self.doc.get("sections") or []:
            for b in sec.get("blocks") or []:
                if b.get("type") == "callout" and b.get("text"):
                    out.append(b["text"].split(".")[0] + ".")
                elif b.get("type") == "kpi":
                    for it in b.get("items") or []:
                        if it.get("value") and it.get("label"):
                            out.append(f"{it['label']} : {it['value']}")
                if len(out) >= 6:
                    return out
        return out

    # ------------------------------------------------------------------ #
    #  Sommaire                                                           #
    # ------------------------------------------------------------------ #
    def toc(self) -> None:
        if not self.options.get("toc", True):
            return
        p, s = self.p, self.style
        self.new_page()
        y = self.H - self.top - 26
        p.body(8, 700)
        p.fill(s.primary)
        p.c.drawString(self.left, y, "SOMMAIRE")
        y -= 44
        p.heading(30, 800)
        p.fill(s.ink)
        p.c.drawString(self.left, y, "Table des matières")
        y -= 20
        p.hline(self.left, self.W - self.right, y, s.line, 0.7)
        y -= 28
        entries = self._toc_entries()
        for num, title, page, sub in entries:
            if y < self.bottom + 40:
                self.new_page()
                y = self.H - self.top - 20
            p.mono(8.4, 500)
            p.fill(s.primary if not sub else s.muted)
            p.c.drawString(self.left, y, f"{num:02d}" if isinstance(num, int) else num)
            p.heading(11.6 if not sub else 9.8, 700 if not sub else 500)
            p.fill(s.ink if not sub else s.muted)
            label = title
            maxw = self.content_w - 84
            while p.text_width(label) > maxw and len(label) > 4:
                label = label[:-2]
            if label != title:
                label = label.rstrip(" .:") + "…"
            p.c.drawString(self.left + 34, y, label)
            p.mono(8.4, 500)
            p.fill(s.primary if not sub else s.muted)
            p.c.drawRightString(self.W - self.right, y, str(page) if page else "")
            dots_from = self.left + 34 + p.text_width(label) + 8
            dots_to = self.W - self.right - 18
            if dots_to > dots_from and not sub:
                self.c.saveState()
                self.c.setStrokeColorRGB(*[x / 255 for x in __import__("delivra.theme", fromlist=["hex_to_rgb"]).hex_to_rgb(s.line)])
                self.c.setLineWidth(0.5)
                self.c.setDash(1, 3)
                self.c.line(dots_from, y + 2.6, dots_to, y + 2.6)
                self.c.restoreState()
            y -= 27 if not sub else 21

    def _toc_entries(self) -> List[Tuple[Any, str, int, bool]]:
        return [(n, t, pg, False) for n, t, pg in self.toc_pages]

    # ------------------------------------------------------------------ #
    #  Sections                                                           #
    # ------------------------------------------------------------------ #
    def render_sections(self) -> None:
        for idx, sec in enumerate([s for s in self.doc.get("sections") or [] if not s.get("hidden")], start=1):
            self.section_no = idx
            self.toc_pages.append((idx, sec.get("title") or f"Section {idx}", self.page_no + 1))
            if sec.get("page_break", True) or idx == 1:
                self.new_page()
            self.section_header(sec, idx)
            y = self.cursor_y
            for block in sec.get("blocks") or []:
                y = self.render_block(block, y)
            if not (sec.get("blocks") or []):
                self.p.para("Cette section est à compléter.", self.left, y,
                            self.content_w, 10, 16, value=self.style.muted)
        if self.options.get("signature", True) and self._needs_signature():
            self.signature_page()

    def _needs_signature(self) -> bool:
        for sec in self.doc.get("sections") or []:
            for b in sec.get("blocks") or []:
                if b.get("type") == "signature":
                    return False
        return True

    @property
    def cursor_y(self) -> float:
        return self._y

    def section_header(self, sec: Dict[str, Any], idx: int) -> None:
        p, s = self.p, self.style
        y = self.H - self.top - 26
        # Numéro géant en filigrane
        p.heading(78, 800)
        p.fill(s.primary, 0.055)
        p.c.drawRightString(self.W - self.right, y - 26, f"{idx:02d}")
        p.body(7.8, 700)
        p.fill(s.primary)
        p.c.drawString(self.left, y, (sec.get("kicker") or "SECTION").upper()[:60])
        y -= 30
        p.heading(22, 800)
        p.fill(s.ink)
        lines = p.wrap(sec.get("title") or "", self.content_w, 22)
        for line in lines:
            p.c.drawString(self.left, y, line)
            y -= 26
        p.rect(self.left, y - 2, 40, 3.2, fill_value=s.accent)
        y -= 22
        if sec.get("intro"):
            y = p.para(sec["intro"], self.left, y, self.content_w, 10.2, 16.2,
                       value=darken(s.ink, 0.1), align="justify") - 8
        self._y = y

    # ------------------------------------------------------------------ #
    #  Blocs                                                              #
    # ------------------------------------------------------------------ #
    def ensure(self, y: float, needed: float) -> float:
        """Saute de page si l'espace restant est insuffisant."""
        if y - needed < self.bottom + 8:
            self.new_page()
            return self.H - self.top - 14
        return y

    def render_block(self, b: Dict[str, Any], y: float) -> float:
        p, s = self.p, self.style
        t = b.get("type")
        if t == "heading":
            size = 15.5 if b.get("level", 2) == 2 else 12.4
            prefix = ""
            if b.get("number"):
                self._sub_no = getattr(self, "_sub_no", 0) + 1
                prefix = f"{self.section_no}.{self._sub_no}  "
            p.heading(size, 800)
            lines = p.wrap(prefix + (b.get("text") or ""), self.content_w, size)
            y = self.ensure(y, len(lines) * (size * 1.32) + 16)
            p.fill(s.ink)
            for line in lines:
                p.c.drawString(self.left, y - size, line)
                y -= size * 1.32
            return y - 8

        if t == "paragraph":
            size = 10.6 if b.get("lead") else 10.0
            leading = 16.6 if b.get("lead") else 15.8
            text = b.get("text") or ""
            lines = p.wrap(text, self.content_w, size)
            # découpe en pages si nécessaire
            per_page = max(1, int((y - self.bottom - 10) // leading))
            for chunk_start in range(0, len(lines), per_page):
                chunk = lines[chunk_start:chunk_start + per_page]
                p.body(size, 400)
                p.fill(darken(s.ink, 0.06))
                cy = y
                for line in chunk:
                    p.c.drawString(self.left, cy - size, line)
                    cy -= leading
                y = cy - 4
                if chunk_start + per_page < len(lines):
                    self.new_page()
                    y = self.H - self.top - 14
            return y - 6

        if t in ("bullets", "numbered"):
            items = b.get("items") or []
            if not items:
                return y
            size, leading = 9.9, 15.2 * s.spacing
            cols = 2 if b.get("columns") == 2 and len(items) > 3 else 1
            col_w = (self.content_w - 24) / 2 if cols == 2 else self.content_w
            y = self.ensure(y, min(len(items), 3) * leading + 10)
            start_y = y
            col_idx = 0
            cx = self.left
            for i, item in enumerate(items):
                if cols == 2 and col_idx == 1 and y <= start_y - (leading * (len(items) + 1) / 2.0):
                    pass
                wrapped = p.wrap(item, col_w - 18, size)
                need = len(wrapped) * leading + 3
                if cols == 1:
                    y = self.ensure(y, need)
                p.body(size, 500 if cols == 1 else 400)
                if t == "numbered":
                    p.fill(s.primary)
                    p.mono(8.6, 700)
                    p.c.drawString(cx, y - 10, f"{i + 1:02d}")
                else:
                    p.rect(cx + 1.5, y - 8.6, 5, 5, radius=1.4, fill_value=s.accent)
                p.body(size, 400)
                p.fill(darken(s.ink, 0.05))
                ly = y
                for line in wrapped:
                    p.c.drawString(cx + 20, ly - size, line)
                    ly -= leading
                y = ly - 3
                if cols == 2 and y < self.bottom + 60 and i < len(items) - 1:
                    # colonne suivante
                    cx += col_w + 24
                    y = start_y
            return y - 8

        if t == "callout":
            tone = b.get("tone") or "info"
            accent = {"info": s.primary, "success": "#12805C", "warning": "#B26B00",
                      "danger": "#B42318"}.get(tone, s.primary)
            title = b.get("title") or {"info": "À noter", "success": "Point validé",
                                       "warning": "Attention", "danger": "Point bloquant"}[tone]
            size, leading = 9.9, 15.4
            body_lines = p.wrap(b.get("text") or "", self.content_w - 46, size)
            h = len(body_lines) * leading + 44
            y = self.ensure(y, h + 8)
            p.rect(self.left, y - h, self.content_w, h, radius=8, fill_value=lighten(accent, 0.94))
            p.rect(self.left, y - h, 3.4, h, fill_value=accent)
            p.rect(self.left + 18, y - 21, 14, 14, radius=4, fill_value=accent)
            p.fill("#FFFFFF")
            p.heading(10, 800)
            p.c.drawCentredString(self.left + 25, y - 17.5, "i" if tone == "info" else "!")
            p.body(9.6, 700)
            p.fill(accent)
            p.c.drawString(self.left + 40, y - 17, title.upper()[:70])
            p.body(size, 400)
            p.fill(darken(s.ink, 0.05))
            ly = y - 34
            for line in body_lines:
                p.c.drawString(self.left + 22, ly, line)
                ly -= leading
            return y - h - 10

        if t == "table":
            return self.render_table(b, y)

        if t == "kpi":
            items = b.get("items") or []
            if not items:
                return y
            gap = 10
            n = min(4, len(items))
            cw = (self.content_w - gap * (n - 1)) / n
            inner = cw - 28
            h = 84
            y = self.ensure(y, h + 8)
            for i, it in enumerate(items[:n]):
                x = self.left + i * (cw + gap)
                p.rect(x, y - h, cw, h, radius=9, fill_value=s.surface)
                p.rect(x, y - h, cw, 3, fill_value=s.accent if i % 2 else s.primary)
                # valeur : taille adaptée à la largeur disponible
                value = (it.get("value") or "—")[:14]
                size = 21.0
                p.heading(size, 800)
                while p.text_width(value) > inner and size > 11:
                    size -= 1.5
                    p.heading(size, 800)
                p.fill(s.primary)
                p.c.drawString(x + 14, y - 34 - size * 0.32, value)
                # libellé sur deux lignes maximum
                p.body(8.4, 600)
                p.fill(s.ink)
                label_lines = p.wrap(it.get("label") or "", inner, 8.4)[:2]
                ly = y - 58
                for line in label_lines:
                    p.c.drawString(x + 14, ly, line)
                    ly -= 10.4
                hint = (it.get("hint") or "")[:34]
                if hint:
                    p.body(7.2, 400)
                    p.fill(s.muted)
                    p.c.drawString(x + 14, y - h + 9, hint)
            return y - h - 14

        if t == "timeline":
            items = b.get("items") or []
            if not items:
                return y
            y = self.ensure(y, min(len(items), 3) * 40 + 10)
            x_line = self.left + 8
            top = y
            for i, it in enumerate(items):
                text_lines = p.wrap(it.get("text") or "", self.content_w - 128, 9.2)
                row_h = max(34, len(text_lines) * 13 + 16)
                y = self.ensure(y, row_h + 6)
                status = it.get("status")
                dot = {"done": "#12805C", "in_progress": s.primary, "late": "#B42318"}.get(status, s.muted)
                p.c.setStrokeColor(__import__("reportlab.lib.colors", fromlist=["Color"]).Color(0.86, 0.88, 0.91))
                p.c.setLineWidth(1.2)
                if i < len(items) - 1:
                    p.c.line(x_line + 4, y - 4, x_line + 4, y - row_h - 6)
                p.rect(x_line, y - 8, 9, 9, radius=4.5, fill_value=dot)
                p.mono(7.8, 600)
                p.fill(s.primary)
                p.c.drawString(x_line + 20, y - 4, (it.get("when") or "")[:18].upper())
                p.heading(10.2, 700)
                p.fill(s.ink)
                p.c.drawString(x_line + 20, y - 18, (it.get("title") or "")[:70])
                p.body(9.2, 400)
                p.fill(s.muted)
                ly = y - 31
                for line in text_lines[:3]:
                    p.c.drawString(x_line + 20, ly, line)
                    ly -= 13
                y -= row_h
            return y - 8

        if t == "image":
            return self.render_image(b, y)

        if t == "architecture":
            return self.render_architecture(b, y)

        if t == "quote":
            size, leading = 12.4, 19.6
            lines = p.wrap(b.get("text") or "", self.content_w - 60, size)
            h = len(lines) * leading + (34 if b.get("author") else 24)
            y = self.ensure(y, h + 10)
            p.heading(46, 800)
            p.fill(s.accent, 0.5)
            p.c.drawString(self.left, y - 34, "“")
            p.body(size, 400)
            p.fill(s.ink)
            ly = y - 22
            for line in lines:
                p.c.drawString(self.left + 34, ly, line)
                ly -= leading
            if b.get("author"):
                p.body(9, 700)
                p.fill(s.muted)
                p.c.drawString(self.left + 34, ly - 4, "— " + b["author"][:80])
                ly -= 16
            return ly - 10

        if t == "code":
            lines = (b.get("text") or "").splitlines() or [""]
            size, leading = 8.4, 12.6
            max_lines = 28
            lines = lines[:max_lines]
            h = len(lines) * leading + 30
            y = self.ensure(y, h + 8)
            p.rect(self.left, y - h, self.content_w, h, radius=8,
                   fill_value=darken(s.dark, 0.25) if s.palette_key != "graphite" else "#151B24")
            p.mono(7.6, 700)
            p.fill(mix(s.accent, "#FFFFFF", 0.25))
            p.c.drawString(self.left + 14, y - 15, (b.get("language") or "sh").upper())
            p.mono(size, 400)
            p.fill("#E6EDF7")
            ly = y - 32
            for line in lines:
                p.c.drawString(self.left + 14, ly, line[:110])
                ly -= leading
            return y - h - 10

        if t == "checklist":
            items = b.get("items") or []
            size, leading = 9.9, 15.4
            for it in items:
                y = self.ensure(y, leading + 2)
                box = 10
                p.rect(self.left + 1, y - box, box, box, radius=2.4,
                       fill_value=s.primary if it.get("done") else "#FFFFFF",
                       stroke_value=s.primary if it.get("done") else s.line, line_width=0.9)
                if it.get("done"):
                    p.c.setStrokeColorRGB(1, 1, 1)
                    p.c.setLineWidth(1.4)
                    p.c.setLineCap(1)
                    p.c.line(self.left + 3.4, y - 5.2, self.left + 5.4, y - 7.4)
                    p.c.line(self.left + 5.4, y - 7.4, self.left + 8.8, y - 2.6)
                wrapped = p.wrap(it.get("text") or "", self.content_w - 24, size)
                p.body(size, 400)
                p.fill(darken(s.ink, 0.05))
                ly = y
                for line in wrapped:
                    p.c.drawString(self.left + 20, ly - size, line)
                    ly -= leading
                y = ly - 3
            return y - 6

        if t == "divider":
            y = self.ensure(y, 24)
            if b.get("style") == "accent":
                p.rect(self.left, y - 6, 34, 3, fill_value=s.accent)
            else:
                p.hline(self.left, self.W - self.right, y - 6, s.line, 0.6)
            return y - 22

        if t == "signature":
            return self.render_signature_block(b, y)

        if t == "two_col":
            return self.render_two_col(b, y)

        return y

    # -- blocs complexes --------------------------------------------------- #
    def render_table(self, b: Dict[str, Any], y: float) -> float:
        p, s = self.p, self.style
        cols = b.get("columns") or []
        rows = b.get("rows") or []
        if not cols and rows:
            cols = [f"Colonne {i + 1}" for i in range(len(rows[0]))]
        if not cols or not rows:
            return y
        ncols = len(cols)
        size = 8.8 if ncols <= 4 else 8.0
        weights = []
        for ci in range(ncols):
            maxlen = len(str(cols[ci]))
            for r in rows:
                if ci < len(r):
                    maxlen = max(maxlen, min(len(str(r[ci])), 90))
            weights.append(max(6, min(30, maxlen)))
        total = sum(weights)
        col_ws = [self.content_w * w / total for w in weights]
        leading = 12.4

        def row_height(cells: List[str]) -> float:
            hmax = 1
            for ci, cell in enumerate(cells[:ncols]):
                p.body(size, 400)
                hmax = max(hmax, len(p.wrap(str(cell), col_ws[ci] - 12, size)))
            return hmax * leading + 12

        # en-tête
        header_h = 26
        y = self.ensure(y, header_h + 40)
        if b.get("caption"):
            p.body(8, 600)
            p.fill(s.muted)
            p.c.drawString(self.left, y - 8, b["caption"][:110])
            y -= 16
        p.rect(self.left, y - header_h, self.content_w, header_h, fill_value=darken(s.dark, 0.05))
        x = self.left
        p.body(size, 700)
        p.fill("#FFFFFF")
        for ci, col in enumerate(cols):
            p.c.drawString(x + 6, y - 17, str(col)[:38])
            x += col_ws[ci]
        y -= header_h
        for ri, row in enumerate(rows):
            rh = row_height(row)
            if y - rh < self.bottom + 10:
                self.new_page()
                y = self.H - self.top - 14
            if ri % 2 == 0:
                p.rect(self.left, y - rh, self.content_w, rh, fill_value=s.surface)
            x = self.left
            for ci in range(ncols):
                cell = row[ci] if ci < len(row) else ""
                lines = p.wrap(str(cell), col_ws[ci] - 12, size)
                p.body(size, 500 if ci == 0 else 400)
                p.fill(s.ink if ci == 0 else darken(s.ink, 0.12))
                ly = y - 10
                for line in lines:
                    p.c.drawString(x + 6, ly, line)
                    ly -= leading
                x += col_ws[ci]
            y -= rh
            p.hline(self.left, self.W - self.right, y, s.line, 0.5)
        return y - 14

    def render_image(self, b: Dict[str, Any], y: float) -> float:
        p, s = self.p, self.style
        from .storage import resolve_asset
        src = resolve_asset(b.get("asset") or "")
        img = _open_image(src)
        if img is None:
            return y
        iw, ih = img.size
        max_w = self.content_w if b.get("layout") != "half" else self.content_w * 0.62
        max_h = 300
        scale = min(max_w / iw, max_h / ih)
        dw, dh = iw * scale, ih * scale
        pad = 10 if b.get("layout") == "framed" else 0
        h = dh + pad * 2 + (16 if b.get("caption") else 0)
        y = self.ensure(y, h + 10)
        ix = self.left + (self.content_w - dw) / 2
        if b.get("layout") == "framed":
            p.rect(ix - pad, y - dh - pad * 2, dw + pad * 2, dh + pad * 2, radius=6,
                   fill_value="#FFFFFF", stroke_value=s.line, line_width=0.7)
        self.c.drawImage(__import__("reportlab.lib.utils", fromlist=["ImageReader"]).ImageReader(img),
                         ix, y - pad - dh, dw, dh, mask="auto")
        y -= dh + pad * 2
        if b.get("caption"):
            p.body(8.2, 500)
            p.fill(s.muted)
            lines = p.wrap(b["caption"], self.content_w - 40, 8.2)
            for line in lines[:2]:
                tw = p.text_width(line)
                p.c.drawString(self.left + (self.content_w - tw) / 2, y - 9, line)
                y -= 11
        return y - 12

    def render_architecture(self, b: Dict[str, Any], y: float) -> float:
        """Schéma d'architecture généré vectoriellement (text to image)."""
        p, s = self.p, self.style
        layers = b.get("layers") or []
        if not layers:
            return y
        pad = 12
        arrow_gap = 9 if b.get("flow", True) else 4
        layer_h = 0
        for l in layers:
            layer_h += 38 if len(l.get("nodes") or []) else 28
        layer_h += arrow_gap * (len(layers) - 1)          # interstices + flèches
        total_h = layer_h + pad * 2
        y = self.ensure(y, total_h + 24)
        top = y
        p.rect(self.left, top - total_h, self.content_w, total_h, radius=10,
               fill_value=mix(s.surface, "#FFFFFF", 0.4), stroke_value=s.line, line_width=0.7)
        cy = top - pad
        tones = {
            "primary": (s.primary, "#FFFFFF"),
            "accent": (s.accent, readable_on(s.accent)),
            "neutral": (mix(s.surface, s.line, 0.55), s.ink),
            "dark": (s.dark, "#FFFFFF"),
        }
        for li, layer in enumerate(layers):
            nodes = layer.get("nodes") or []
            hb = 38 if nodes else 28
            bg, fg = tones.get(layer.get("tone") or "neutral", tones["neutral"])
            p.rect(self.left + pad, cy - hb, self.content_w - pad * 2, hb, radius=7,
                   fill_value=bg, stroke_value=darken(bg, 0.08) if layer.get("tone") in (None, "neutral") else None,
                   line_width=0.5)
            p.body(7.2, 700)
            p.fill(fg)
            p.c.drawString(self.left + pad + 12, cy - 11, (layer.get("title") or "").upper()[:48])
            if nodes:
                n = len(nodes)
                avail = self.content_w - pad * 2 - 24
                gap = 6
                nw = (avail - gap * (n - 1)) / n
                nx = self.left + pad + 12
                # contraste : sur une couche sombre, les nœuds restent sombres
                # avec un texte clair (évite le gris sur gris)
                if layer.get("tone") == "dark":
                    node_bg = mix(bg, "#FFFFFF", 0.18)
                    node_fg = fg
                else:
                    node_bg = mix(bg, "#FFFFFF", 0.70)
                    node_fg = readable_on(node_bg)
                for node in nodes:
                    p.rect(nx, cy - hb + 6, nw, 15, radius=3.5, fill_value=node_bg,
                           stroke_value=mix(bg, "#FFFFFF", 0.45), line_width=0.4)
                    label = node
                    p.body(6.8, 600)
                    p.fill(node_fg)
                    while p.text_width(label) > nw - 8 and len(label) > 3:
                        label = label[:-2]
                    if label != node:
                        label = label[:-1] + "…"
                    p.c.drawString(nx + 4, cy - hb + 10, label)
                    nx += nw + gap
            cy -= hb
            if li < len(layers) - 1:
                p.c.setStrokeColor(__import__("reportlab.lib.colors", fromlist=["Color"]).Color(0.62, 0.68, 0.76))
                p.c.setLineWidth(0.8)
                mx = self.left + self.content_w / 2
                p.c.line(mx, cy - 2, mx, cy - arrow_gap + 2)
                path = p.c.beginPath()
                path.moveTo(mx - 2.6, cy - arrow_gap + 4.6)
                path.lineTo(mx, cy - arrow_gap + 0.6)
                path.lineTo(mx + 2.6, cy - arrow_gap + 4.6)
                p.fill(s.muted)
                p.c.drawPath(path, stroke=0, fill=1)
                cy -= arrow_gap
        y = top - total_h - 10
        if b.get("caption"):
            p.body(8.2, 500)
            p.fill(s.muted)
            p.c.drawString(self.left, y - 2, b["caption"][:120])
            y -= 14
        return y - 8

    def render_two_col(self, b: Dict[str, Any], y: float) -> float:
        p, s = self.p, self.style
        gap = 18
        cw = (self.content_w - gap) / 2
        left, right = b.get("left") or {}, b.get("right") or {}
        rows = max(len(left.get("items") or []), len(right.get("items") or []), 1)
        h = rows * 15.4 + 54
        y = self.ensure(y, h + 10)
        for i, side in enumerate((left, right)):
            x = self.left + i * (cw + gap)
            accent = s.primary if i == 0 else s.accent
            p.rect(x, y - h, cw, h, radius=8, fill_value=mix(accent, "#FFFFFF", 0.94))
            p.body(9.4, 700)
            p.fill(accent)
            p.c.drawString(x + 14, y - 20, (side.get("title") or "").upper()[:40])
            ly = y - 38
            for item in side.get("items") or []:
                p.rect(x + 14, ly - 4, 4.4, 4.4, radius=2.2, fill_value=accent)
                p.body(9, 400)
                p.fill(s.ink)
                p.c.drawString(x + 25, ly - 7, item[:56])
                ly -= 15.4
        return y - h - 12

    def render_signature_block(self, b: Dict[str, Any], y: float) -> float:
        p, s = self.p, self.style
        parties = b.get("parties") or []
        n = max(1, len(parties))
        gap = 16
        cw = (self.content_w - gap * (n - 1)) / n
        y = self.ensure(y, 108)
        for i, party in enumerate(parties):
            x = self.left + i * (cw + gap)
            p.rect(x, y - 100, cw, 100, radius=8, fill_value="#FFFFFF",
                   stroke_value=s.line, line_width=0.7)
            p.body(8, 700)
            p.fill(s.primary)
            p.c.drawString(x + 12, y - 18, (party.get("role") or "")[:38].upper())
            p.heading(10.4, 700)
            p.fill(s.ink)
            p.c.drawString(x + 12, y - 34, (party.get("name") or "________________")[:40])
            p.body(7.6, 400)
            p.fill(s.muted)
            p.c.drawString(x + 12, y - 48, (party.get("place") or "")[:40])
            p.hline(x + 12, x + cw - 12, y - 72, s.line, 0.6)
            p.body(7, 400)
            p.fill(s.muted)
            p.c.drawString(x + 12, y - 84, "Signature & cachet")
            p.c.drawRightString(x + cw - 12, y - 84, (party.get("date") or "")[:20])
        return y - 112

    def signature_page(self) -> None:
        p, s, m = self.p, self.style, self.meta
        self.new_page()
        y = self.H - self.top - 26
        p.body(8, 700)
        p.fill(s.primary)
        p.c.drawString(self.left, y, "VALIDATION")
        y -= 36
        p.heading(22, 800)
        p.fill(s.ink)
        p.c.drawString(self.left, y, "Bon pour accord")
        y -= 22
        p.rect(self.left, y, 40, 3.2, fill_value=s.accent)
        y -= 30
        p.para("La signature du présent document vaut validation des éléments décrits "
               "et des conditions de livraison associées. Toute réserve doit être notifiée "
               "par écrit dans un délai de dix (10) jours ouvrés.",
               self.left, y, self.content_w, 9.8, 15.4, align="justify")
        y -= 60
        parties = [
            {"role": "Pour le client", "name": m.get("client") or "", "place": "", "date": ""},
            {"role": "Pour le prestataire", "name": m.get("author") or "", "place": "", "date": ""},
        ]
        self.render_signature_block({"parties": parties}, y)
        y -= 118
        p.body(7.6, 500)
        p.fill(s.muted)
        p.c.drawString(self.left, self.bottom + 30,
                       f"{m.get('reference') or ''} · {m.get('title') or ''}"[:100])


# --------------------------------------------------------------------------- #
#  API publique                                                               #
# --------------------------------------------------------------------------- #
def render_pdf_with_toc(doc: Dict[str, Any]) -> Tuple[bytes, List[Tuple[Any, str, int]]]:
    """Comme `render_pdf`, mais retourne aussi la carte sections → pages."""
    register_fonts()
    first = Document(doc)
    if first.options.get("cover", True):
        first.cover()
    first.identity_page()
    first.toc()
    first.render_sections()
    first.finish()
    return _compose(doc, first.toc_pages), list(first.toc_pages)


def render_pdf(doc: Dict[str, Any], *, two_pass: bool = True) -> bytes:
    """Compose le PDF complet.

    Passe 1 : le sommaire est rendu sans numéros, on note la page de départ de
    chaque section. Passe 2 : le sommaire porte les bons numéros. Le sommaire
    est placé avant les sections et sa hauteur est indépendante du contenu des
    numéros, donc la pagination mesurée en passe 1 reste valide.
    """
    register_fonts()
    if not two_pass:
        return _compose(doc, [])

    first = Document(doc)
    if first.options.get("cover", True):
        first.cover()
    first.identity_page()
    first.toc()
    first.render_sections()
    first.finish()
    return _compose(doc, first.toc_pages)


def _compose(doc: Dict[str, Any], toc: List[Tuple[Any, str, int]]) -> bytes:
    d = Document(doc)
    if d.options.get("cover", True):
        d.cover()
    d.identity_page()
    if d.options.get("toc", True):
        d.toc_pages = list(toc)
        d.toc()
    d.render_sections()
    return d.finish()
