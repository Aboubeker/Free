"""Export Word (.docx) éditable — reprend la structure et les styles du livrable."""
from __future__ import annotations

import io
from typing import Any, Dict, List, Optional

from docx import Document as DocxDocument
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

from ..theme import FONT_DIR, Style, darken, hex_to_rgb, lighten

FONT_FILES = {
    "Manrope": "Manrope", "SourceSerif": "SourceSerif", "Sora": "Sora",
    "JetBrainsMono": "JetBrainsMono",
}


def _rgb(value: str) -> RGBColor:
    r, g, b = hex_to_rgb(value)
    return RGBColor(r, g, b)


def _shade(cell, hex_color: str) -> None:
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_color.lstrip("#"))
    tcPr.append(shd)


def _borders(table, color: str) -> None:
    tbl = table._tbl
    tblPr = tbl.tblPr
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        el = OxmlElement(f"w:{edge}")
        el.set(qn("w:val"), "single")
        el.set(qn("w:sz"), "4")
        el.set(qn("w:color"), color.lstrip("#"))
        borders.append(el)
    tblPr.append(borders)


def _no_borders(table) -> None:
    tbl = table._tbl
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        el = OxmlElement(f"w:{edge}")
        el.set(qn("w:val"), "nil")
        borders.append(el)
    tbl.tblPr.append(borders)


def _add_page_number(paragraph, style: Style) -> None:
    run = paragraph.add_run()
    for instr in ("begin", "instrText", "end"):
        if instr == "instrText":
            el = OxmlElement("w:instrText")
            el.set(qn("xml:space"), "preserve")
            el.text = " PAGE "
        else:
            el = OxmlElement("w:fldChar")
            el.set(qn("w:fldCharType"), instr)
        run._r.append(el)
    run.font.size = Pt(8)
    run.font.color.rgb = _rgb(style.muted)


def _resolve_source(asset: str) -> Optional[Any]:
    from ..storage import resolve_asset
    p = resolve_asset(asset)
    if p is None:
        return None
    try:
        p = str(p)
        return p if p.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".bmp")) else None
    except Exception:
        return None


def build_docx(doc: Dict[str, Any]) -> bytes:
    style = Style(doc.get("style"))
    meta = doc.get("meta") or {}
    options = doc.get("options") or {}
    d = DocxDocument()

    # -- mise en page ---------------------------------------------------- #
    sec = d.sections[0]
    if style.paper == "Letter":
        sec.page_width, sec.page_height = Cm(21.59), Cm(27.94)
    else:
        sec.page_width, sec.page_height = Cm(21), Cm(29.7)
    sec.left_margin = sec.right_margin = Cm(2.2)
    sec.top_margin, sec.bottom_margin = Cm(2.2), Cm(2.0)
    sec.header_distance, sec.footer_distance = Cm(1.1), Cm(1.0)

    # styles de base
    for name in ("Normal", "List Bullet", "List Number"):
        st = d.styles[name]
        st.font.name = style.body_family
        st.font.size = Pt(10)
        st.font.color.rgb = _rgb(style.ink)
        rpr = st.element.get_or_add_rPr()
        fonts = OxmlElement("w:rFonts")
        fonts.set(qn("w:ascii"), style.body_family)
        fonts.set(qn("w:hAnsi"), style.body_family)
        fonts.set(qn("w:cs"), style.body_family)
        rpr.append(fonts)
    for i, size in ((1, 20), (2, 14), (3, 11.5)):
        h = d.styles[f"Heading {i}"]
        h.font.name = style.heading_family
        h.font.size = Pt(size)
        h.font.bold = True
        h.font.color.rgb = _rgb(style.ink)
        rpr = h.element.get_or_add_rPr()
        fonts = OxmlElement("w:rFonts")
        fonts.set(qn("w:ascii"), style.heading_family)
        fonts.set(qn("w:hAnsi"), style.heading_family)
        rpr.append(fonts)

    # en-tête / pied
    if options.get("header", True):
        hdr = sec.header.paragraphs[0]
        hdr.text = (meta.get("client") or "").upper()
        hdr.alignment = WD_ALIGN_PARAGRAPH.LEFT
        for r in hdr.runs:
            r.font.size = Pt(7.5)
            r.font.name = style.body_family
            r.font.color.rgb = _rgb(style.muted)
        if meta.get("reference"):
            hdr.add_run("\t\t" + meta["reference"]).font.size = Pt(7.5)
    if options.get("page_numbers", True):
        ftr = sec.footer.paragraphs[0]
        ftr.text = (options.get("footer_text") or "") + " \u00b7 " + (meta.get("client") or "")
        ftr.alignment = WD_ALIGN_PARAGRAPH.LEFT
        for r in ftr.runs:
            r.font.size = Pt(7.5)
            r.font.color.rgb = _rgb(style.muted)
        ftr.add_run("\t\t")
        _add_page_number(ftr, style)

    # -- couverture ------------------------------------------------------ #
    if options.get("cover", True):
        for _ in range(2):
            d.add_paragraph()
        brand = doc.get("brand") or {}
        logo = _resolve_source(brand.get("logo") or "")
        if logo:
            p = d.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            try:
                p.add_run().add_picture(logo, width=Cm(3.6))
            except Exception:
                pass
        tag = d.add_paragraph()
        tr = tag.add_run((meta.get("confidentiality") or "CONFIDENTIEL").upper())
        tr.font.size = Pt(8)
        tr.font.bold = True
        tr.font.color.rgb = _rgb(style.primary)
        tr.font.name = style.body_family

        for _ in range(3):
            d.add_paragraph()
        title = d.add_paragraph()
        tr = title.add_run(meta.get("title") or "Document de livraison")
        tr.font.size = Pt(30)
        tr.font.bold = True
        tr.font.name = style.heading_family
        tr.font.color.rgb = _rgb(style.ink)
        if meta.get("subtitle") or meta.get("project"):
            sub = d.add_paragraph()
            sr = sub.add_run(meta.get("subtitle") or meta.get("project"))
            sr.font.size = Pt(13)
            sr.font.name = style.body_family
            sr.font.color.rgb = _rgb(style.muted)

        for _ in range(6):
            d.add_paragraph()
        info = d.add_table(rows=2, cols=3)
        _no_borders(info)
        info.alignment = WD_TABLE_ALIGNMENT.LEFT
        values = [("CLIENT", meta.get("client")), ("DATE", meta.get("date")),
                  ("RÉFÉRENCE", (meta.get("reference") or ""))]
        for i, (label, value) in enumerate(values):
            top = info.cell(0, i).paragraphs[0]
            lr = top.add_run(label)
            lr.font.size = Pt(7)
            lr.font.bold = True
            lr.font.color.rgb = _rgb(style.muted)
            lr.font.name = style.body_family
            bottom = info.cell(1, i).paragraphs[0]
            vr = bottom.add_run(value or "—")
            vr.font.size = Pt(10)
            vr.font.bold = True
            vr.font.color.rgb = _rgb(style.ink)
            vr.font.name = style.body_family
        d.add_page_break()

    # -- résumé exécutif -------------------------------------------------- #
    summary = meta.get("executive_summary")
    if summary:
        h = d.add_paragraph(style="Heading 1")
        h.add_run("Résumé exécutif")
        p = d.add_paragraph(summary)
        p.paragraph_format.space_after = Pt(14)
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        d.add_page_break()

    # -- table des matières Word (champ TOC natif) ------------------------ #
    if options.get("toc", True):
        h = d.add_paragraph(style="Heading 1")
        h.add_run("Table des matières")
        p = d.add_paragraph()
        run = p.add_run()
        fld = OxmlElement("w:fldSimple")
        fld.set(qn("w:instr"), 'TOC \\o "1-2" \\h \\z \\u')
        inner = OxmlElement("w:r")
        t = OxmlElement("w:t")
        t.text = "Sommaire automatique — clic droit puis « Mettre à jour les champs »."
        inner.append(t)
        fld.append(inner)
        run._r.addnext(fld)
        d.add_page_break()

    # -- sections --------------------------------------------------------- #
    visible = [s for s in doc.get("sections") or [] if not s.get("hidden")]
    for idx, section in enumerate(visible, start=1):
        h = d.add_paragraph(style="Heading 1")
        prefix = h.add_run(f"{idx:02d}  ")
        prefix.font.color.rgb = _rgb(style.primary)
        h.add_run(section.get("title") or f"Section {idx}")
        if section.get("intro"):
            p = d.add_paragraph(section["intro"])
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            p.paragraph_format.space_after = Pt(10)
        sub = 0
        for block in section.get("blocks") or []:
            t = block.get("type")
            if t == "heading":
                sub += 1
                lvl = 2 if block.get("level", 2) == 2 else 3
                hh = d.add_paragraph(style=f"Heading {lvl}")
                hh.add_run((f"{idx}.{sub}  " if block.get("number") else "") + (block.get("text") or ""))
            elif t == "paragraph":
                p = d.add_paragraph(block.get("text") or "")
                p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                p.paragraph_format.space_after = Pt(8)
            elif t in ("bullets", "numbered"):
                stl = "List Bullet" if t == "bullets" else "List Number"
                for item in block.get("items") or []:
                    d.add_paragraph(item, style=stl)
            elif t == "callout":
                table = d.add_table(rows=1, cols=1)
                _no_borders(table)
                cell = table.cell(0, 0)
                _shade(cell, lighten(style.primary, 0.9))
                p = cell.paragraphs[0]
                r = p.add_run((block.get("title") or "À noter").upper() + "\n")
                r.font.bold = True
                r.font.size = Pt(8.5)
                r.font.color.rgb = _rgb(darken(style.primary, 0.15))
                r2 = p.add_run(block.get("text") or "")
                r2.font.size = Pt(9.5)
                d.add_paragraph()
            elif t == "kpi":
                items = block.get("items") or []
                if items:
                    table = d.add_table(rows=2, cols=len(items))
                    _no_borders(table)
                    for i, it in enumerate(items):
                        c1 = table.cell(0, i)
                        _shade(c1, style.surface)
                        r = c1.paragraphs[0].add_run(it.get("value") or "")
                        r.font.size = Pt(17)
                        r.font.bold = True
                        r.font.color.rgb = _rgb(style.primary)
                        c2 = table.cell(1, i)
                        _shade(c2, style.surface)
                        r2 = c2.paragraphs[0].add_run(it.get("label") or "")
                        r2.font.size = Pt(8)
                        r2.font.color.rgb = _rgb(style.muted)
                    d.add_paragraph()
            elif t == "table":
                cols = block.get("columns") or []
                rows = block.get("rows") or []
                if block.get("caption"):
                    cap = d.add_paragraph()
                    cr = cap.add_run(block["caption"])
                    cr.font.size = Pt(8)
                    cr.font.italic = True
                    cr.font.color.rgb = _rgb(style.muted)
                ncols = max(len(cols), max((len(r) for r in rows), default=0), 1)
                table = d.add_table(rows=1 + len(rows), cols=ncols)
                _borders(table, style.line)
                for ci in range(ncols):
                    cell = table.cell(0, ci)
                    _shade(cell, style.dark)
                    p = cell.paragraphs[0]
                    r = p.add_run(cols[ci] if ci < len(cols) else "")
                    r.font.bold = True
                    r.font.size = Pt(8.5)
                    r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
                for ri, row in enumerate(rows, start=1):
                    for ci in range(ncols):
                        cell = table.cell(ri, ci)
                        if ri % 2 == 0:
                            _shade(cell, style.surface)
                        p = cell.paragraphs[0]
                        r = p.add_run(str(row[ci]) if ci < len(row) else "")
                        r.font.size = Pt(8.5)
                        if ci == 0:
                            r.font.bold = True
                d.add_paragraph()
            elif t == "timeline":
                for it in block.get("items") or []:
                    p = d.add_paragraph()
                    when = p.add_run((it.get("when") or "").upper() + " — ")
                    when.font.bold = True
                    when.font.size = Pt(8)
                    when.font.color.rgb = _rgb(style.primary)
                    p.add_run(it.get("title") or "").font.bold = True
                    if it.get("text"):
                        p2 = d.add_paragraph(it["text"])
                        p2.paragraph_format.left_indent = Cm(0.6)
                        for r in p2.runs:
                            r.font.size = Pt(9)
                            r.font.color.rgb = _rgb(style.muted)
            elif t == "image":
                src = _resolve_source(block.get("asset") or "")
                if src:
                    try:
                        d.add_picture(src, width=Cm(16 if block.get("layout") != "half" else 10))
                        if block.get("caption"):
                            cap = d.add_paragraph()
                            cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
                            cr = cap.add_run(block["caption"])
                            cr.font.size = Pt(8)
                            cr.font.italic = True
                            cr.font.color.rgb = _rgb(style.muted)
                    except Exception:
                        pass
            elif t == "architecture":
                # schéma vectoriel → image PNG haute définition
                from ..diagrams import architecture_png
                layers = block.get("layers") or []
                if layers:
                    png = architecture_png(layers, style, caption=None, width_px=2000)
                    try:
                        d.add_picture(io.BytesIO(png), width=Cm(16))
                        if block.get("caption"):
                            cap = d.add_paragraph(block["caption"])
                            cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
                            for r in cap.runs:
                                r.font.size = Pt(8)
                                r.font.italic = True
                                r.font.color.rgb = _rgb(style.muted)
                    except Exception:
                        pass
            elif t == "quote":
                p = d.add_paragraph()
                r = p.add_run("“ " + (block.get("text") or ""))
                r.font.size = Pt(12)
                r.font.italic = True
                r.font.color.rgb = _rgb(style.primary)
                if block.get("author"):
                    a = d.add_paragraph()
                    ar = a.add_run("— " + block["author"])
                    ar.font.size = Pt(8.5)
                    ar.font.color.rgb = _rgb(style.muted)
            elif t == "code":
                table = d.add_table(rows=1, cols=1)
                _no_borders(table)
                cell = table.cell(0, 0)
                _shade(cell, style.dark)
                for i, line in enumerate((block.get("text") or "").splitlines()):
                    p = cell.paragraphs[0] if i == 0 else cell.add_paragraph()
                    r = p.add_run(line)
                    r.font.name = "Consolas"
                    r.font.size = Pt(8)
                    r.font.color.rgb = RGBColor(0xE6, 0xED, 0xF7)
                d.add_paragraph()
            elif t == "checklist":
                for it in block.get("items") or []:
                    p = d.add_paragraph()
                    box = "☑ " if it.get("done") else "☐ "
                    r = p.add_run(box + (it.get("text") or ""))
                    r.font.size = Pt(9.5)
                    r.font.name = "Segoe UI Symbol"
            elif t == "signature":
                parties = block.get("parties") or []
                table = d.add_table(rows=1, cols=max(1, len(parties)))
                _borders(table, style.line)
                for i, party in enumerate(parties):
                    cell = table.cell(0, i)
                    p = cell.paragraphs[0]
                    r = p.add_run((party.get("role") or "").upper())
                    r.font.size = Pt(7.5)
                    r.font.bold = True
                    r.font.color.rgb = _rgb(style.primary)
                    name_run = cell.add_paragraph().add_run(party.get("name") or "________________")
                    name_run.font.bold = True
                    place_run = cell.add_paragraph().add_run(party.get("place") or "")
                    place_run.font.size = Pt(8)
                    cell.add_paragraph("\n\n")
                    sig_run = cell.add_paragraph().add_run("Signature & cachet")
                    sig_run.font.size = Pt(7.5)
                    sig_run.font.color.rgb = _rgb(style.muted)
                d.add_paragraph()
            elif t == "two_col":
                table = d.add_table(rows=1, cols=2)
                _no_borders(table)
                for i, side in enumerate((block.get("left") or {}, block.get("right") or {})):
                    cell = table.cell(0, i)
                    _shade(cell, lighten(style.primary if i == 0 else style.accent, 0.92))
                    p = cell.paragraphs[0]
                    r = p.add_run((side.get("title") or "").upper())
                    r.font.bold = True
                    r.font.size = Pt(8.5)
                    r.font.color.rgb = _rgb(style.primary if i == 0 else darken(style.accent, 0.3))
                    for item in side.get("items") or []:
                        r_item = cell.add_paragraph().add_run("• " + item)
                        r_item.font.size = Pt(9)
                d.add_paragraph()
            elif t == "divider":
                d.add_paragraph("─" * 40)
        if idx < len(visible):
            d.add_page_break()

    # -- annexe de contrôle ---------------------------------------------- #
    if options.get("annexes", True):
        d.add_page_break()
        h = d.add_paragraph(style="Heading 1")
        h.add_run("Annexe — fiche de contrôle du livrable")
        from ..model import quality_report
        q = quality_report(doc)
        p = d.add_paragraph()
        r = p.add_run(f"Score de complétude : {q['score']}/100 ({q['grade']})  ·  "
                      f"{q['sections']} sections  ·  {q['words']} mots")
        r.font.size = Pt(9)
        r.font.color.rgb = _rgb(style.muted)
        table = d.add_table(rows=0, cols=2)
        _borders(table, style.line)
        for chk in q["checks"]:
            row = table.add_row()
            c0 = row.cells[0]
            p0 = c0.paragraphs[0]
            r0 = p0.add_run(("✓ " if chk["ok"] else "✗ ") + chk["label"])
            r0.font.size = Pt(9)
            r0.font.color.rgb = _rgb("#12805C" if chk["ok"] else "#B42318")
            c1 = row.cells[1]
            r1 = c1.paragraphs[0].add_run(chk["hint"] if not chk["ok"] else "Conforme")
            r1.font.size = Pt(8)
            r1.font.color.rgb = _rgb(style.muted)

    buf = io.BytesIO()
    d.save(buf)
    return buf.getvalue()
