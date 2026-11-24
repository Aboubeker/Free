"""Génère des livrables d'exemple (PDF + DOCX + PPTX) dans data/examples/.

    python tools/generate_examples.py
"""
from __future__ import annotations
import os, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DELIVRA_HOME", str(ROOT / "data"))

from delivra.ai.engine import generate          # noqa: E402
from delivra.model import quality_report, normalize  # noqa: E402
from delivra.render import render_pdf          # noqa: E402
from delivra.storage import save_project, exports_dir, data_dir  # noqa: E402

EXAMPLES = [
    {
        "title": "Dossier de livraison — Plateforme Data Client 360",
        "client": "Atlas Telecom", "project": "Plateforme Data Client 360",
        "industry": "Télécommunications", "weeks": 20,
        "context": "Atlas Telecom opère 4 marques et 11 canaux de contact. Les données "
                   "client sont dispersées entre le CRM, la facturation et les plateformes "
                   "digitales, ce qui empêche toute vision unifiée du parcours client.",
        "goals": "Disposer d'une clé client unique fiable\nIndustrialiser les 17 flux d'ingestion\n"
                 "Mettre à disposition 12 tableaux de bord métier",
        "stack": "Azure Databricks, ADLS Gen2, Data Factory, Power BI, Unity Catalog",
        "author": "Yacine Bensalem", "author_role": "Architecte Data",
        "recipient": "Direction des Systèmes d'Information",
        "palette": "ocean", "typography": "manrope",
        "reference": "LIV-2026-0114", "version": "2.0",
    },
    {
        "title": "Dossier de déploiement — Portail Client Omnicanal",
        "client": "Banque Atlas", "project": "Portail Client Omnicanal",
        "industry": "Services financiers", "weeks": 24,
        "context": "Les clients particuliers utilisent quatre canaux distincts (agence, web, "
                   "application mobile, téléphone) sans continuité de parcours ni historique "
                   "partagé entre les conseillers.",
        "goals": "Offrir un parcours unifié et repris d'un canal à l'autre\n"
                 "Réduire de moitié le temps de traitement des demandes\n"
                 "Renforcer l'authentification et la traçabilité des opérations",
        "stack": "React / Next.js, API REST, PostgreSQL, Redis, Azure",
        "author": "Salima Cherif", "author_role": "Directrice de projet",
        "recipient": "Direction du Numérique",
        "palette": "bordeaux", "typography": "serif-mix",
        "reference": "LIV-2026-0207", "version": "1.0",
    },
    {
        "title": "Dossier de livraison — Système de Gestion Intégré (ERP)",
        "client": "Groupe Sahel Industrie", "project": "Déploiement SAP S/4HANA",
        "industry": "Industrie & distribution", "weeks": 40,
        "context": "La croissance externe du groupe a laissé cohabiter cinq systèmes de "
                   "gestion hétérogènes, rendant les consolidations comptables longues et "
                   "peu fiables.",
        "goals": "Standardiser 46 processus métier\nRéduire la clôture comptable de 9 à 4 jours\n"
                 "Sécuriser la reprise de 7 ans d'historique",
        "stack": "SAP S/4HANA, Fiori, SAP BTP, Solution Manager, Power BI",
        "author": "Karim Haddad", "author_role": "Directeur de programme",
        "recipient": "Comité de direction",
        "palette": "graphite", "typography": "sora",
        "reference": "LIV-2026-0311", "version": "3.1",
    },
]


def main() -> int:
    out = data_dir() / "examples"
    out.mkdir(parents=True, exist_ok=True)
    for brief in EXAMPLES:
        doc = generate(brief)
        doc = normalize(doc)
        save_project(doc)
        q = quality_report(doc)
        slug = doc["meta"]["reference"].replace("/", "-")
        (out / f"{slug}.pdf").write_bytes(render_pdf(doc))
        try:
            from delivra.export.docx_export import build_docx
            from delivra.export.pptx_export import build_pptx
            from delivra.export.markdown_export import build_markdown
            (out / f"{slug}.docx").write_bytes(build_docx(doc))
            (out / f"{slug}.pptx").write_bytes(build_pptx(doc))
            (out / f"{slug}.md").write_text(build_markdown(doc), encoding="utf-8")
        except Exception as exc:  # pragma: no cover — best effort
            print("  ! export secondaire :", exc)
        print(f"✓ {slug} — {q['score']}/100 · {len(doc['sections'])} sections · {q['words']} mots")
    print(f"\nExemples générés dans {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
