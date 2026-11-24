"""Export Markdown — utile pour ReStructuredText, Notion, Obsidian ou Git."""
from __future__ import annotations

from typing import Any, Dict


def build_markdown(doc: Dict[str, Any]) -> str:
    meta = doc.get("meta") or {}
    out = [f"# {meta.get('title') or 'Document de livraison'}"]
    if meta.get("subtitle"):
        out.append(f"*{meta['subtitle']}*")
    out.append("")
    info = [("Client", meta.get("client")), ("Projet", meta.get("project")),
            ("Version", meta.get("version")), ("Date", meta.get("date")),
            ("Référence", meta.get("reference")), ("Auteur", meta.get("author")),
            ("Destinataire", meta.get("recipient")),
            ("Confidentialité", meta.get("confidentiality"))]
    out += [f"- **{k}** : {v}" for k, v in info if v]
    out.append("")

    if meta.get("executive_summary"):
        out += ["## Résumé exécutif", "", meta["executive_summary"], ""]

    visible = [s for s in doc.get("sections") or [] if not s.get("hidden")]
    if visible:
        out += ["## Sommaire", ""]
        for i, s in enumerate(visible, 1):
            out.append(f"{i}. {s.get('title')}")
        out.append("")

    for i, sec in enumerate(visible, 1):
        out += [f"## {i}. {sec.get('title')}", ""]
        if sec.get("intro"):
            out += [sec["intro"], ""]
        sub = 0
        for b in sec.get("blocks") or []:
            t = b.get("type")
            if t == "heading":
                sub += 1
                prefix = f"{i}.{sub} " if b.get("number") else ""
                out += [f"### {prefix}{b.get('text')}", ""]
            elif t == "paragraph":
                out += [b.get("text") or "", ""]
            elif t == "bullets":
                out += [f"- {x}" for x in b.get("items") or []] + [""]
            elif t == "numbered":
                out += [f"{k + 1}. {x}" for k, x in enumerate(b.get("items") or [])] + [""]
            elif t == "checklist":
                out += [f"- [{'x' if it.get('done') else ' '}] {it.get('text')}"
                        for it in b.get("items") or []] + [""]
            elif t == "callout":
                out += [f"> **{b.get('title') or 'Note'}** — {b.get('text')}", ""]
            elif t == "quote":
                out += [f"> {b.get('text')}"]
                if b.get("author"):
                    out += [f"> — {b['author']}"]
                out.append("")
            elif t == "table":
                cols = b.get("columns") or []
                rows = b.get("rows") or []
                if b.get("caption"):
                    out += [f"*{b['caption']}*", ""]
                if cols:
                    out.append("| " + " | ".join(cols) + " |")
                    out.append("|" + "|".join(["---"] * len(cols)) + "|")
                for r in rows:
                    out.append("| " + " | ".join(str(c) for c in r) + " |")
                out.append("")
            elif t == "kpi":
                for it in b.get("items") or []:
                    out.append(f"- **{it.get('value')}** — {it.get('label')}"
                               + (f" ({it['hint']})" if it.get("hint") else ""))
                out.append("")
            elif t == "timeline":
                for it in b.get("items") or []:
                    out.append(f"- **{it.get('when')}** — {it.get('title')} : {it.get('text')}")
                out.append("")
            elif t == "image":
                out += [f"![{b.get('caption') or 'capture'}]({b.get('asset')})", ""]
            elif t == "architecture":
                caption = b.get("caption") or "Schéma d'architecture"
                out += [f"*{caption}*", ""]
                for layer in b.get("layers") or []:
                    out.append(f"- **{layer.get('title')}** : " + ", ".join(layer.get("nodes") or []))
                out.append("")
            elif t == "code":
                out += [f"```{b.get('language') or ''}", b.get("text") or "", "```", ""]
            elif t == "two_col":
                for side in (b.get("left") or {}, b.get("right") or {}):
                    out += [f"**{side.get('title')}**", ""]
                    out += [f"- {x}" for x in side.get("items") or []] + [""]
            elif t == "signature":
                for p in b.get("parties") or []:
                    out += [f"_{p.get('role')} : {p.get('name') or '________________'}_  "]
                out.append("")
            elif t == "divider":
                out += ["---", ""]
    return "\n".join(out).strip() + "\n"
