"""Export PowerPoint (.pptx) : déclinaison slide du livrable.

Une diapositive de couverture, une par section, et des diapositives dédiées
pour les KPI, tableaux et schémas d'architecture — utile pour la réunion de
restitution.
"""
from __future__ import annotations

import io
from typing import Any, Dict, List, Optional

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Emu, Inches, Pt

from ..theme import Style, darken, hex_to_rgb, lighten, readable_on


def _rgb(value: str) -> RGBColor:
    r, g, b = hex_to_rgb(value)
    return RGBColor(r, g, b)


class Deck:
    def __init__(self, doc: Dict[str, Any]):
        self.doc = doc
        self.meta = doc.get("meta") or {}
        self.style = Style(doc.get("style"))
        self.prs = Presentation()
        wide = self.style.paper != "Letter"
        self.prs.slide_width = Inches(13.333)
        self.prs.slide_height = Inches(7.5)
        self.W = self.prs.slide_width
        self.H = self.prs.slide_height
        self.blank = self.prs.slide_layouts[6]

    # -- helpers ---------------------------------------------------------- #
    def slide(self, bg: Optional[str] = None):
        s = self.prs.slides.add_slide(self.blank)
        if bg:
            fill = s.background.fill
            fill.solid()
            fill.fore_color.rgb = _rgb(bg)
        return s

    def rect(self, s, x, y, w, h, color, radius=True, alpha=None):
        shape_type = MSO_SHAPE.ROUNDED_RECTANGLE if radius else MSO_SHAPE.RECTANGLE
        shp = s.shapes.add_shape(shape_type, x, y, w, h)
        shp.fill.solid()
        shp.fill.fore_color.rgb = _rgb(color)
        shp.line.fill.background()
        shp.shadow.inherit = False
        if radius:
            try:
                shp.adjustments[0] = 0.08
            except Exception:
                pass
        return shp

    def text(self, s, x, y, w, h, text, size=18, color=None, bold=False,
             family=None, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP,
             spacing=1.05, italic=False):
        tb = s.shapes.add_textbox(x, y, w, h)
        tf = tb.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_right = 0
        tf.margin_top = tf.margin_bottom = 0
        tf.vertical_anchor = anchor
        p = tf.paragraphs[0]
        p.alignment = align
        p.line_spacing = spacing
        run = p.add_run()
        run.text = text
        f = run.font
        f.size = Pt(size)
        f.bold = bold
        f.italic = italic
        f.name = family or self.style.body_family
        f.color.rgb = _rgb(color or self.style.ink)
        return tb

    def bullets(self, s, x, y, w, h, items, size=15, color=None):
        tb = s.shapes.add_textbox(x, y, w, h)
        tf = tb.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_right = 0
        for i, item in enumerate(items[:8]):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            p.space_after = Pt(8)
            p.line_spacing = 1.12
            run = p.add_run()
            run.text = "•  " + item
            run.font.size = Pt(size)
            run.font.name = self.style.body_family
            run.font.color.rgb = _rgb(color or self.style.ink)

    def header(self, s, kicker: str, title: str, number: Optional[int] = None):
        st = self.style
        self.text(s, Inches(0.75), Inches(0.5), Inches(9), Inches(0.3),
                  kicker.upper(), size=11, color=st.primary, bold=True)
        self.text(s, Inches(0.75), Inches(0.78), Inches(11), Inches(0.9),
                  title, size=30, color=st.ink, bold=True, family=st.heading_family)
        self.rect(s, Inches(0.75), Inches(1.62), Inches(0.75), Inches(0.055), st.accent, radius=False)
        if number is not None:
            self.text(s, Inches(11.4), Inches(0.42), Inches(1.2), Inches(0.9),
                      f"{number:02d}", size=46, color=lighten(st.primary, 0.78), bold=True,
                      family=st.heading_family, align=PP_ALIGN.RIGHT)
        # pied de page
        self.text(s, Inches(0.75), Inches(6.98), Inches(6), Inches(0.3),
                  ((self.meta.get("client") or "") + " · " + (self.meta.get("reference") or "")).strip(" ·")[:70],
                  size=9, color=st.muted)

    # -- diapositives ------------------------------------------------------ #
    def cover(self):
        st = self.style
        s = self.slide(bg=st.dark)
        # bande latérale accent
        self.rect(s, 0, 0, Inches(0.22), self.H, st.accent, radius=False)
        band = s.shapes.add_shape(MSO_SHAPE.OVAL, Inches(9.2), Inches(-1.4), Inches(6.4), Inches(6.4))
        band.fill.solid()
        band.fill.fore_color.rgb = _rgb(lighten(st.dark, 0.09))
        band.line.fill.background()

        y = Inches(0.7)
        brand = self.doc.get("brand") or {}
        logo = _picture_source(brand.get("logo") or self.meta.get("client_logo"))
        if logo:
            try:
                s.shapes.add_picture(logo, Inches(0.75), y, height=Inches(0.62))
                y += Inches(0.95)
            except Exception:
                y += Inches(0.2)
        self.text(s, Inches(0.75), y, Inches(6), Inches(0.3),
                  (self.meta.get("confidentiality") or "CONFIDENTIEL").upper(),
                  size=10, color="#FFFFFF", bold=True)
        self.text(s, Inches(0.75), Inches(2.35), Inches(10.6), Inches(2.2),
                  self.meta.get("title") or "Document de livraison",
                  size=42, color="#FFFFFF", bold=True, family=st.heading_family, spacing=1.0)
        sub = self.meta.get("subtitle") or self.meta.get("project") or ""
        if sub:
            self.text(s, Inches(0.75), Inches(4.55), Inches(9.6), Inches(0.8),
                      sub, size=17, color=lighten(st.dark, 0.62))
        self.rect(s, Inches(0.75), Inches(5.55), Inches(0.9), Inches(0.06), st.accent, radius=False)
        meta_line = " · ".join(x for x in [self.meta.get("client"), self.meta.get("date"),
                                           ("v" + self.meta["version"]) if self.meta.get("version") else None] if x)
        self.text(s, Inches(0.75), Inches(5.85), Inches(10), Inches(0.4),
                  meta_line, size=12, color=lighten(st.dark, 0.55))

    def agenda(self):
        st = self.style
        sections = [s for s in self.doc.get("sections") or [] if not s.get("hidden")]
        if not sections:
            return
        s = self.slide(bg="#FFFFFF")
        self.header(s, "Sommaire", "Ordre du jour", None)
        per_col = (len(sections) + 1) // 2
        for i, sec in enumerate(sections[:10]):
            col = i // per_col
            row = i % per_col
            x = Inches(0.75 + col * 6.1)
            y = Inches(2.15 + row * 0.78)
            self.text(s, x, y, Inches(0.62), Inches(0.4), f"{i + 1:02d}", size=17,
                      color=st.primary, bold=True)
            self.text(s, x + Inches(0.7), y, Inches(4.7), Inches(0.6),
                      sec.get("title") or "", size=15, color=st.ink)

    def section_slide(self, sec: Dict[str, Any], idx: int):
        st = self.style
        s = self.slide(bg="#FFFFFF")
        self.header(s, sec.get("kicker") or "Section", sec.get("title") or "", idx)
        y = Inches(2.0)
        if sec.get("intro"):
            self.text(s, Inches(0.75), y, Inches(11.6), Inches(0.8), sec["intro"],
                      size=14, color=st.muted)
            y += Inches(0.95)
        bullets: List[str] = []
        for b in sec.get("blocks") or []:
            if b.get("type") in ("bullets", "numbered", "checklist"):
                items = b.get("items") or []
                bullets += [i.get("text") if isinstance(i, dict) else i for i in items]
            elif b.get("type") == "paragraph" and len(bullets) < 3:
                bullets.append((b.get("text") or "")[:150])
        self.bullets(s, Inches(0.75), y, Inches(6.2), Inches(4.4), bullets, size=14)

        # aperçu visuel à droite : KPI, architecture ou tableau
        visual = next((b for b in sec.get("blocks") or [] if b.get("type") in ("kpi", "architecture", "table")), None)
        if visual:
            self.visual_panel(visual, Inches(7.35), Inches(2.0), Inches(5.25), Inches(4.6))

    def visual_panel(self, block: Dict[str, Any], x, y, w, h):
        st = self.style
        t = block.get("type")
        if t == "kpi":
            items = (block.get("items") or [])[:3]
            for i, it in enumerate(items):
                yy = y + Emu(int(h * 0.06)) + Emu(int(i * (h - Inches(0.3)) / max(1, len(items))))
                box_h = Emu(int((h - Inches(0.5)) / max(1, len(items))) - Inches(0.15))
                self.rect(self.prs.slides[-1], x, yy, w, box_h, st.surface)
                sl = self.prs.slides[-1]
                self.text(sl, x + Inches(0.25), yy + Inches(0.12), w - Inches(0.5), Inches(0.5),
                          it.get("value") or "", size=26, color=st.primary, bold=True,
                          family=st.heading_family)
                self.text(sl, x + Inches(0.25), yy + box_h - Inches(0.5), w - Inches(0.5), Inches(0.4),
                          it.get("label") or "", size=11, color=st.ink)
        elif t == "architecture":
            from ..diagrams import architecture_png
            try:
                png = architecture_png(block.get("layers") or [], st, caption=None, width_px=1600)
                self.prs.slides[-1].shapes.add_picture(io.BytesIO(png), x, y, width=w)
            except Exception:
                pass
        elif t == "table":
            cols = block.get("columns") or []
            rows = (block.get("rows") or [])[:6]
            ncols = max(1, len(cols))
            nrows = len(rows) + (1 if cols else 0)
            if nrows == 0:
                return
            shape = self.prs.slides[-1].shapes.add_table(
                nrows, ncols, x, y, w, Emu(int(h * 0.9)))
            table = shape.table
            ri = 0
            if cols:
                for ci, col in enumerate(cols[:ncols]):
                    cell = table.cell(0, ci)
                    cell.text = str(col)
                    cell.fill.solid()
                    cell.fill.fore_color.rgb = _rgb(st.dark)
                    para = cell.text_frame.paragraphs[0]
                    if para.runs:
                        para.runs[0].font.size = Pt(11)
                        para.runs[0].font.color.rgb = _rgb("#FFFFFF")
                        para.runs[0].font.bold = True
                        para.runs[0].font.name = st.body_family
                ri = 1
            for r in rows:
                for ci in range(ncols):
                    if ci >= len(r):
                        continue
                    cell = table.cell(ri, ci)
                    cell.text = str(r[ci])
                    para = cell.text_frame.paragraphs[0]
                    if para.runs:
                        para.runs[0].font.size = Pt(10)
                        para.runs[0].font.name = st.body_family
                ri += 1

    def kpi_slide(self, block: Dict[str, Any], idx: int):
        st = self.style
        items = (block.get("items") or [])[:4]
        if not items:
            return
        s = self.slide(bg=st.surface)
        self.text(s, Inches(0.75), Inches(0.7), Inches(8), Inches(0.4),
                  "CHIFFRES CLÉS", size=12, color=st.primary, bold=True)
        self.text(s, Inches(0.75), Inches(1.0), Inches(11), Inches(0.9),
                  "Résultats mesurés", size=32, color=st.ink, bold=True, family=st.heading_family)
        n = len(items)
        gap = Inches(0.28)
        cw = Emu(int((Inches(11.83) - gap * (n - 1)) / n))
        for i, it in enumerate(items):
            x = Inches(0.75) + Emu(int(i * (cw + gap)))
            self.rect(s, x, Inches(2.6), cw, Inches(2.5), "#FFFFFF")
            self.rect(s, x, Inches(2.6), cw, Inches(0.07), st.primary if i % 2 == 0 else st.accent, radius=False)
            self.text(s, x + Inches(0.3), Inches(2.95), cw - Inches(0.6), Inches(0.9),
                      it.get("value") or "—", size=40, color=st.primary, bold=True, family=st.heading_family)
            self.text(s, x + Inches(0.3), Inches(3.95), cw - Inches(0.6), Inches(0.7),
                      it.get("label") or "", size=13, color=st.ink)
            if it.get("hint"):
                self.text(s, x + Inches(0.3), Inches(4.6), cw - Inches(0.6), Inches(0.4),
                          it["hint"], size=10, color=st.muted)

    def table_slide(self, block: Dict[str, Any], idx: int):
        st = self.style
        s = self.slide(bg="#FFFFFF")
        self.header(s, "Tableau de synthèse", block.get("caption") or f"Tableau {idx}", None)
        self.visual_panel(block, Inches(0.75), Inches(2.0), Inches(11.8), Inches(4.4))

    def arch_slide(self, block: Dict[str, Any], idx: int):
        st = self.style
        s = self.slide(bg=st.surface)
        self.text(s, Inches(0.75), Inches(0.65), Inches(8), Inches(0.4),
                  "ARCHITECTURE", size=12, color=st.primary, bold=True)
        self.text(s, Inches(0.75), Inches(0.95), Inches(11), Inches(0.9),
                  "Vue d'ensemble de la solution", size=30, color=st.ink, bold=True,
                  family=st.heading_family)
        from ..diagrams import architecture_png
        try:
            png = architecture_png(block.get("layers") or [], st,
                                   caption=block.get("caption"), width_px=2200)
            s.shapes.add_picture(io.BytesIO(png), Inches(0.75), Inches(2.05), width=Inches(11.8))
        except Exception:
            pass

    def closing(self):
        st = self.style
        s = self.slide(bg=st.dark)
        self.rect(s, 0, 0, Inches(0.22), self.H, st.accent, radius=False)
        self.text(s, Inches(0.9), Inches(2.9), Inches(11), Inches(1.0), "Merci de votre attention",
                  size=40, color="#FFFFFF", bold=True, family=st.heading_family)
        contact = " · ".join(x for x in [self.meta.get("author"), self.meta.get("author_email")] if x)
        if contact:
            self.text(s, Inches(0.9), Inches(4.15), Inches(11), Inches(0.5), contact,
                      size=15, color=lighten(st.dark, 0.6))
        self.text(s, Inches(0.9), Inches(6.5), Inches(11), Inches(0.4),
                  (self.meta.get("client") or "") + " · " + (self.meta.get("date") or ""),
                  size=11, color=lighten(st.dark, 0.45))

    def build(self) -> bytes:
        self.cover()
        self.agenda()
        for idx, sec in enumerate([s for s in self.doc.get("sections") or [] if not s.get("hidden")], start=1):
            self.section_slide(sec, idx)
            for b in sec.get("blocks") or []:
                if b.get("type") == "kpi":
                    self.kpi_slide(b, idx)
                elif b.get("type") == "architecture":
                    self.arch_slide(b, idx)
                elif b.get("type") == "table" and len(b.get("rows") or []) >= 4:
                    self.table_slide(b, idx)
        self.closing()
        out = io.BytesIO()
        self.prs.save(out)
        return out.getvalue()


def _picture_source(ref: str):
    from ..storage import resolve_asset
    p = resolve_asset(ref)
    if p and str(p).lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".bmp")):
        return str(p)
    return None


def build_pptx(doc: Dict[str, Any]) -> bytes:
    return Deck(doc).build()
