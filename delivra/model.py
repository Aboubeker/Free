"""Schéma du livrable : normalisation, valeurs par défaut, validation.

Un livrable (`Deliverable`) est un dict sérialisable JSON :
    meta        identité du projet (client, solution, dates, référence…)
    style       palette, typographie, densité, format papier
    brand       logos (data-URI ou chemins relatifs)
    sections    liste ordonnée de sections, chacune composée de blocs
    assets      captures d'écran, schémas, images générées
    options     inclusions (sommaire, annexes, filigrane, pagination…)

Les blocs disponibles :
    heading, paragraph, bullets, numbered, callout, table, kpi, timeline,
    image, architecture, quote, code, checklist, divider, signature, two_col
"""
from __future__ import annotations

import copy
import re
import uuid
from datetime import date, datetime
from typing import Any, Dict, List, Optional

BLOCK_TYPES = [
    "heading", "paragraph", "bullets", "numbered", "callout", "table", "kpi",
    "timeline", "image", "architecture", "quote", "code", "checklist",
    "divider", "signature", "two_col",
]

DEFAULT_OPTIONS = {
    "toc": True,
    "page_numbers": True,
    "header": True,
    "cover": True,
    "annexes": True,
    "watermark": "",
    "footer_text": "Document confidentiel",
    "signature": True,
    "summary_box": True,
    "theme_mood": "professionnel",
}

DEFAULT_META = {
    "title": "Document de livraison",
    "subtitle": "",
    "client": "",
    "client_logo": "",
    "project": "",
    "reference": "",
    "version": "1.0",
    "date": "",
    "author": "",
    "author_role": "",
    "author_email": "",
    "recipient": "",
    "confidentiality": "Confidentiel",
    "industry": "",
    "executive_summary": "",
    "tags": [],
}

SECTION_TEMPLATES = {
    "contexte": {"title": "Contexte & enjeux", "icon": "target"},
    "objectifs": {"title": "Objectifs du projet", "icon": "flag"},
    "perimetre": {"title": "Périmètre & exclusions", "icon": "layers"},
    "architecture": {"title": "Architecture de la solution", "icon": "flow"},
    "deploiement": {"title": "Déploiement & infrastructure", "icon": "server"},
    "integrations": {"title": "Intégrations & interfaces", "icon": "plug"},
    "securite": {"title": "Sécurité & conformité", "icon": "shield"},
    "donnees": {"title": "Données & migration", "icon": "database"},
    "tests": {"title": "Stratégie de tests & recette", "icon": "check"},
    "exploitation": {"title": "Exploitation & supervision", "icon": "activity"},
    "planning": {"title": "Planning & jalons", "icon": "calendar"},
    "budget": {"title": "Budget & ressources", "icon": "wallet"},
    "risques": {"title": "Risques & plan de mitigation", "icon": "alert"},
    "resultats": {"title": "Résultats & bénéfices", "icon": "trending"},
    "annexes": {"title": "Annexes", "icon": "paperclip"},
}


def new_id(prefix: str = "id") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}"


def today_fr() -> str:
    months = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet",
              "août", "septembre", "octobre", "novembre", "décembre"]
    d = date.today()
    return f"{d.day} {months[d.month - 1]} {d.year}"


def _clean(value: Any, limit: int = 20000) -> str:
    if value is None:
        return ""
    text = str(value)
    text = re.sub(r"<script.*?</script>", "", text, flags=re.S | re.I)
    return text[:limit]


def normalize_block(block: Dict[str, Any]) -> Dict[str, Any]:
    b = copy.deepcopy(block or {})
    btype = b.get("type")
    if btype not in BLOCK_TYPES:
        btype = "paragraph"
    out: Dict[str, Any] = {"id": b.get("id") or new_id("blk"), "type": btype}

    if btype in ("heading",):
        out["text"] = _clean(b.get("text"), 400)
        out["level"] = 2 if int(b.get("level") or 2) >= 2 else 3
        out["number"] = bool(b.get("number", True))
    elif btype == "paragraph":
        out["text"] = _clean(b.get("text"))
        out["lead"] = bool(b.get("lead"))
    elif btype in ("bullets", "numbered"):
        items = b.get("items") or []
        if isinstance(items, str):
            items = [i.strip(" -•\t") for i in items.splitlines() if i.strip()]
        out["items"] = [_clean(i, 1000) for i in items][:40]
        out["columns"] = 2 if b.get("columns") == 2 else 1
    elif btype == "callout":
        out["title"] = _clean(b.get("title"), 200)
        out["text"] = _clean(b.get("text"))
        out["tone"] = b.get("tone") if b.get("tone") in ("info", "success", "warning", "danger") else "info"
    elif btype == "table":
        rows = b.get("rows") or []
        clean_rows = []
        for r in rows[:60]:
            if isinstance(r, dict):
                clean_rows.append([_clean(c, 400) for c in (r.get("cells") or [])])
            elif isinstance(r, (list, tuple)):
                clean_rows.append([_clean(c, 400) for c in r])
        out["columns"] = [_clean(c, 120) for c in (b.get("columns") or [])][:10]
        out["rows"] = clean_rows
        out["caption"] = _clean(b.get("caption"), 200)
    elif btype == "kpi":
        out["items"] = [
            {"label": _clean(i.get("label"), 80), "value": _clean(i.get("value"), 24),
             "hint": _clean(i.get("hint"), 120)}
            for i in (b.get("items") or [])[:4] if isinstance(i, dict)
        ]
    elif btype == "timeline":
        out["items"] = [
            {"when": _clean(i.get("when"), 60), "title": _clean(i.get("title"), 160),
             "text": _clean(i.get("text"), 600), "status": i.get("status") or "planned"}
            for i in (b.get("items") or [])[:12] if isinstance(i, dict)
        ]
    elif btype == "image":
        out["asset"] = _clean(b.get("asset"), 400)
        out["caption"] = _clean(b.get("caption"), 300)
        out["layout"] = b.get("layout") if b.get("layout") in ("full", "half", "framed") else "framed"
    elif btype == "architecture":
        out["layers"] = [
            {
                "title": _clean(l.get("title"), 120),
                "nodes": [_clean(n, 80) for n in (l.get("nodes") or [])][:8],
                "tone": l.get("tone") or "neutral",
            }
            for l in (b.get("layers") or [])[:7] if isinstance(l, dict)
        ]
        out["caption"] = _clean(b.get("caption"), 300)
        out["flow"] = bool(b.get("flow", True))
    elif btype == "quote":
        out["text"] = _clean(b.get("text"), 1200)
        out["author"] = _clean(b.get("author"), 120)
    elif btype == "code":
        out["text"] = _clean(b.get("text"), 6000)
        out["language"] = _clean(b.get("language"), 30) or "bash"
    elif btype == "checklist":
        items = b.get("items") or []
        out["items"] = [
            {"text": _clean(i.get("text") if isinstance(i, dict) else i, 300),
             "done": bool(i.get("done")) if isinstance(i, dict) else False}
            for i in items
        ][:30]
    elif btype == "divider":
        out["style"] = b.get("style") or "accent"
    elif btype == "signature":
        out["parties"] = [
            {"role": _clean(p.get("role"), 120), "name": _clean(p.get("name"), 120),
             "place": _clean(p.get("place"), 120), "date": _clean(p.get("date"), 60)}
            for p in (b.get("parties") or [])[:3] if isinstance(p, dict)
        ] or [{"role": "Pour le client", "name": "", "place": "", "date": ""},
              {"role": "Pour le prestataire", "name": "", "place": "", "date": ""}]
    elif btype == "two_col":
        out["left"] = {"title": _clean((b.get("left") or {}).get("title"), 160),
                       "items": [_clean(i, 300) for i in ((b.get("left") or {}).get("items") or [])][:12]}
        out["right"] = {"title": _clean((b.get("right") or {}).get("title"), 160),
                        "items": [_clean(i, 300) for i in ((b.get("right") or {}).get("items") or [])][:12]}
    return out


def normalize_section(section: Dict[str, Any], index: int = 1) -> Dict[str, Any]:
    s = copy.deepcopy(section or {})
    blocks = [normalize_block(b) for b in (s.get("blocks") or []) if isinstance(b, dict)]
    return {
        "id": s.get("id") or new_id("sec"),
        "title": _clean(s.get("title"), 200) or f"Section {index}",
        "kicker": _clean(s.get("kicker"), 80),
        "intro": _clean(s.get("intro"), 2000),
        "icon": _clean(s.get("icon"), 40) or "dot",
        "page_break": bool(s.get("page_break", True)),
        "hidden": bool(s.get("hidden", False)),
        "blocks": blocks,
    }


def blank_deliverable() -> Dict[str, Any]:
    return {
        "id": new_id("dlv"),
        "meta": {**copy.deepcopy(DEFAULT_META), "date": today_fr()},
        "style": {},
        "brand": {"logo": "", "client_logo": "", "cover_image": ""},
        "sections": [],
        "assets": [],
        "options": copy.deepcopy(DEFAULT_OPTIONS),
        "created_at": datetime.utcnow().isoformat() + "Z",
        "updated_at": datetime.utcnow().isoformat() + "Z",
    }


def normalize(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Nettoie et complète un livrable reçu (API, import, IA)."""
    doc = copy.deepcopy(doc or {})
    out = blank_deliverable()
    meta = {**DEFAULT_META, **(doc.get("meta") or {})}
    meta["tags"] = [str(t)[:40] for t in (meta.get("tags") or [])][:8]
    for key in DEFAULT_META:
        if key == "tags":
            continue
        meta[key] = _clean(meta.get(key), 4000 if key == "executive_summary" else 300)
    if not meta["date"]:
        meta["date"] = today_fr()
    out["meta"] = meta
    out["style"] = doc.get("style") or {}
    brand = doc.get("brand") or {}
    out["brand"] = {
        "logo": _clean(brand.get("logo"), 2_000_000),
        "client_logo": _clean(brand.get("client_logo"), 2_000_000),
        "cover_image": _clean(brand.get("cover_image"), 2_000_000),
    }
    out["options"] = {**DEFAULT_OPTIONS, **(doc.get("options") or {})}
    out["options"]["watermark"] = _clean(out["options"].get("watermark"), 40)
    out["sections"] = [
        normalize_section(s, i + 1) for i, s in enumerate(doc.get("sections") or [])
        if isinstance(s, dict)
    ]
    out["assets"] = [
        {"id": a.get("id") or new_id("ast"), "name": _clean(a.get("name"), 200),
         "kind": a.get("kind") or "image"}
        for a in (doc.get("assets") or []) if isinstance(a, dict)
    ]
    out["id"] = doc.get("id") or out["id"]
    out["created_at"] = doc.get("created_at") or out["created_at"]
    out["updated_at"] = datetime.utcnow().isoformat() + "Z"
    return out


def quality_report(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Score de complétude 0-100 avec recommandations actionnables."""
    meta = doc.get("meta") or {}
    sections = [s for s in doc.get("sections") or [] if not s.get("hidden")]
    checks: List[Dict[str, Any]] = []

    def check(key: str, label: str, ok: bool, weight: int, hint: str) -> None:
        checks.append({"key": key, "label": label, "ok": bool(ok), "weight": weight, "hint": hint})

    n_blocks = sum(len(s.get("blocks") or []) for s in sections)
    words = 0
    for s in sections:
        words += len((s.get("intro") or "").split())
        for b in s.get("blocks") or []:
            words += len((b.get("text") or "").split())
            words += sum(len(str(i).split()) for i in (b.get("items") or []) if isinstance(i, str))
            words += sum(len(str(c).split()) for r in (b.get("rows") or []) for c in r)

    check("client", "Nom du client renseigné", bool(meta.get("client")), 12,
          "Renseignez le client pour personnaliser la couverture.")
    check("solution", "Solution / projet identifié", bool(meta.get("project") or meta.get("title")), 10,
          "Indiquez la solution déployée dans les informations projet.")
    check("summary", "Résumé exécutif présent", len(meta.get("executive_summary") or "") > 80, 12,
          "Un résumé exécutif de 3 à 6 lignes est attendu en ouverture.")
    check("sections", "Au moins 5 sections", len(sections) >= 5, 12,
          "Les livrables de référence comportent 5 sections minimum.")
    check("density", "Contenu substantiel (≥ 350 mots)", words >= 350, 12,
          "Ajoutez du texte, des tableaux ou des listes pour étoffer le document.")
    has_arch = any(b.get("type") in ("architecture", "image") for s in sections for b in s.get("blocks") or [])
    check("arch", "Architecture ou visuel technique", has_arch, 12,
          "Insérez un schéma d'architecture ou une capture annotée.")
    check("deploy", "Section déploiement / infrastructure",
          any("déploy" in (s.get("title") or "").lower() or "infra" in (s.get("title") or "").lower()
              for s in sections), 8, "Une section déploiement décrit l'environnement cible.")
    has_table = any(b.get("type") in ("table", "kpi", "timeline") for s in sections for b in s.get("blocks") or [])
    check("data", "Tableaux, KPI ou planning", has_table, 8,
          "Un tableau de synthèse ou un planning renforce la crédibilité.")
    check("logo", "Logo de l'entreprise", bool((doc.get("brand") or {}).get("logo")
                                              or (meta.get("client_logo"))), 6,
          "Importez un logo pour une couverture soignée.")
    check("captures", "Captures d'écran intégrées",
          any(b.get("type") == "image" for s in sections for b in s.get("blocks") or []), 8,
          "Les documents livrables illustrent l'application par des captures.")

    total = sum(c["weight"] for c in checks) or 1
    score = round(100 * sum(c["weight"] for c in checks if c["ok"]) / total)
    grade = "Excellent" if score >= 88 else "Solide" if score >= 70 else \
            "À compléter" if score >= 50 else "Insuffisant"
    return {
        "score": score, "grade": grade, "words": words, "sections": len(sections),
        "blocks": n_blocks, "checks": checks,
    }


def outline(doc: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Sommaire calculé (numérotation cohérente avec le document imprimé)."""
    items = []
    for i, s in enumerate([x for x in doc.get("sections") or [] if not x.get("hidden")], start=1):
        items.append({"number": i, "title": s.get("title"), "kicker": s.get("kicker"),
                      "blocks": len(s.get("blocks") or [])})
    return items
