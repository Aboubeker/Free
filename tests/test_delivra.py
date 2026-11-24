"""Tests de non-régression de Delivra.

    python -m unittest discover -s tests -v

Aucun réseau requis : la génération, le rendu et les exports sont testés hors ligne.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ["DELIVRA_HOME"] = tempfile.mkdtemp(prefix="delivra-tests-")

from delivra.ai.engine import detect_playbook, generate, plan_outline  # noqa: E402
from delivra.export.docx_export import build_docx  # noqa: E402
from delivra.export.markdown_export import build_markdown  # noqa: E402
from delivra.export.pptx_export import build_pptx  # noqa: E402
from delivra.model import blank_deliverable, normalize, outline, quality_report  # noqa: E402
from delivra.render import render_pdf, render_pdf_with_toc  # noqa: E402
from delivra.theme import PALETTES, Style, catalog, resolve_weight  # noqa: E402

BRIEF = {
    "title": "Dossier de livraison — Portail Client",
    "client": "Banque Atlas",
    "project": "Portail Client Omnicanal",
    "industry": "Services financiers",
    "context": "Parcours client fragmenté sur quatre canaux.",
    "weeks": 20,
    "stack": "React, API REST, PostgreSQL, Azure",
    "author": "Salima Cherif",
}


class TestModel(unittest.TestCase):
    def test_blank_deliverable_is_valid(self):
        doc = blank_deliverable()
        self.assertIn("meta", doc)
        self.assertIn("options", doc)
        self.assertEqual(doc["sections"], [])

    def test_normalize_cleans_dangerous_input(self):
        doc = normalize({
            "meta": {"title": "<script>alert(1)</script>Titre", "client": "X" * 900},
            "sections": [{"title": "S", "blocks": [
                {"type": "unknown", "text": "abc"},
                {"type": "table", "rows": [{"cells": ["a", "b"]}]},
                {"type": "bullets", "items": "un\ndeux\ntrois"},
            ]}],
        })
        self.assertNotIn("<script>", doc["meta"]["title"])
        self.assertLessEqual(len(doc["meta"]["client"]), 300)
        self.assertEqual(doc["sections"][0]["blocks"][0]["type"], "paragraph")
        self.assertEqual(len(doc["sections"][0]["blocks"][2]["items"]), 3)

    def test_quality_report_signals_gaps(self):
        q = quality_report(normalize({"meta": {"title": "Vide"}}))
        self.assertLess(q["score"], 60)
        self.assertEqual(q["grade"], "Insuffisant")
        self.assertTrue(any(not c["ok"] for c in q["checks"]))

    def test_outline_numbers_sections(self):
        doc = normalize({"sections": [{"title": "A"}, {"title": "B", "hidden": True}, {"title": "C"}]})
        items = outline(doc)
        self.assertEqual([i["title"] for i in items], ["A", "C"])
        self.assertEqual(items[1]["number"], 2)


class TestEngine(unittest.TestCase):
    def test_playbook_detection(self):
        self.assertEqual(detect_playbook("migration azure kubernetes"), "cloud")
        self.assertEqual(detect_playbook("databricks data analytics power bi"), "data")
        self.assertEqual(detect_playbook("erp sap s4hana sihr"), "erp")
        self.assertEqual(detect_playbook("pentest rgpd soc conformité"), "securite")

    def test_plan_respects_requested_sections(self):
        p = plan_outline({**BRIEF, "sections": ["contexte", "architecture"]})
        self.assertEqual([s["key"] for s in p["outline"]], ["contexte", "architecture"])
        self.assertIn(p["palette"], PALETTES)

    def test_generate_produces_complete_deliverable(self):
        doc = generate(BRIEF)
        self.assertGreaterEqual(len(doc["sections"]), 8)
        self.assertIn("Banque Atlas", doc["meta"]["executive_summary"])
        self.assertRegex(doc["meta"]["reference"], r"^LIV-\d{4}-\d{4}$")
        q = quality_report(doc)
        self.assertGreaterEqual(q["score"], 70)
        self.assertGreater(q["words"], 500)
        # le schéma d'architecture doit être présent
        types = {b["type"] for s in doc["sections"] for b in s["blocks"]}
        self.assertIn("architecture", types)
        self.assertIn("table", types)

    def test_content_is_contextual_and_deterministic(self):
        from delivra.ai.engine import contextual_kpis
        from delivra.ai.engine import PLAYBOOKS
        bank = {"title": "T", "client": "Banque Atlas", "playbook": "data", "industry": "Services financiers"}
        kpis_bank = contextual_kpis(bank, PLAYBOOKS["data"])
        self.assertTrue(any("conformité" in label.lower() for label, _ in kpis_bank))
        # deux appels avec le même brief → mêmes valeurs
        self.assertEqual(kpis_bank, contextual_kpis(dict(bank), PLAYBOOKS["data"]))
        # un autre secteur produit d'autres indicateurs
        health = {"title": "T", "client": "CHU", "playbook": "data", "industry": "Santé"}
        self.assertNotEqual(kpis_bank, contextual_kpis(health, PLAYBOOKS["data"]))

    def test_client_specific_risk_is_mentioned(self):
        doc = generate({**BRIEF, "client": "Groupe Horizon"})
        blob = json.dumps(doc, ensure_ascii=False)
        self.assertIn("Groupe Horizon", blob)

    def test_generate_all_playbooks(self):
        cases = {
            "cloud": "migration azure kubernetes terraform",
            "data": "entrepôt de données databricks power bi",
            "web": "application mobile react next.js",
            "integration": "api gateway kafka sap interfaces",
            "securite": "soc cyber iso 27001 pentest",
            "erp": "erp sap s4hana paie",
        }
        for expected, context in cases.items():
            with self.subTest(expected=expected):
                doc = generate({**BRIEF, "context": context, "playbook": expected})
                self.assertEqual(doc["meta"]["playbook"], expected)
                self.assertGreaterEqual(len(doc["sections"]), 8)


class TestRendering(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = generate(BRIEF)

    def test_pdf_is_valid_and_multipage(self):
        pdf = render_pdf(self.doc)
        self.assertTrue(pdf.startswith(b"%PDF"))
        self.assertGreater(len(pdf), 20000)
        import pypdfium2 as pdfium
        pages = pdfium.PdfDocument(pdf)
        self.assertGreaterEqual(len(pages), 8)

    def test_pdf_toc_pagination_is_consistent(self):
        pdf, toc = render_pdf_with_toc(self.doc)
        import pypdfium2 as pdfium
        total = len(pdfium.PdfDocument(pdf))
        self.assertEqual(len(toc), len([s for s in self.doc["sections"] if not s.get("hidden")]))
        for number, title, page in toc:
            self.assertGreaterEqual(page, 1)
            self.assertLessEqual(page, total)
        # la pagination doit être croissante
        pages = [p for _, _, p in toc]
        self.assertEqual(pages, sorted(pages))

    def test_docx_export(self):
        data = build_docx(self.doc)
        self.assertTrue(data.startswith(b"PK"))
        import docx
        import io
        d = docx.Document(io.BytesIO(data))
        text = "\n".join(p.text for p in d.paragraphs)
        self.assertIn("Banque Atlas", text)
        self.assertGreater(len(d.tables), 3)

    def test_pptx_export(self):
        data = build_pptx(self.doc)
        self.assertTrue(data.startswith(b"PK"))
        import io
        import pptx
        p = pptx.Presentation(io.BytesIO(data))
        self.assertGreaterEqual(len(p.slides), 6)

    def test_markdown_export(self):
        md = build_markdown(self.doc)
        self.assertIn("# Dossier de livraison", md)
        self.assertIn("## 1.", md)

    def test_every_palette_and_typography_renders(self):
        info = catalog()
        for palette in [p["key"] for p in info["palettes"]]:
            with self.subTest(palette=palette):
                doc = normalize({**self.doc, "style": {"palette": palette}})
                pdf = render_pdf(doc, two_pass=False)
                self.assertGreater(len(pdf), 10000)
        for typo in [t["key"] for t in info["typographies"]]:
            with self.subTest(typography=typo):
                doc = normalize({**self.doc, "style": {"typography": typo}})
                self.assertGreater(len(render_pdf(doc, two_pass=False)), 10000)

    def test_cover_variants(self):
        for variant in ("deep", "gradient", "minimal"):
            with self.subTest(variant=variant):
                doc = normalize({**self.doc, "style": {"cover_style": variant}})
                self.assertGreater(len(render_pdf(doc, two_pass=False)), 10000)

    def test_letter_paper(self):
        doc = normalize({**self.doc, "style": {"paper": "Letter"}})
        self.assertGreater(len(render_pdf(doc, two_pass=False)), 10000)

    def test_empty_document_does_not_crash(self):
        doc = normalize({"meta": {"title": "Vide"}, "sections": []})
        pdf = render_pdf(doc)
        self.assertTrue(pdf.startswith(b"%PDF"))


class TestTheme(unittest.TestCase):
    def test_weight_fallback(self):
        self.assertEqual(resolve_weight("SourceSerif", 800), 700)
        self.assertEqual(resolve_weight("Manrope", 500), 500)
        self.assertEqual(resolve_weight("Inconnue", 700), 400)

    def test_page_sizes(self):
        self.assertAlmostEqual(Style({"paper": "A4"}).page_w_pt, 595.28, places=1)
        self.assertAlmostEqual(Style({"paper": "Letter"}).page_h_pt, 792.0, places=0)

    def test_unknown_values_fall_back(self):
        s = Style({"palette": "inexistante", "typography": "inconnue", "density": "x"})
        self.assertEqual(s.palette_key, "ocean")
        self.assertEqual(s.typography_key, "manrope")
        self.assertEqual(s.density, "normal")


class TestStorage(unittest.TestCase):
    def test_project_roundtrip(self):
        from delivra import storage
        doc = generate(BRIEF)
        saved = storage.save_project(doc)
        loaded = storage.load_project(saved["id"])
        self.assertEqual(loaded["meta"]["title"], doc["meta"]["title"])
        self.assertIn(saved["id"], [p["id"] for p in storage.list_projects()])
        self.assertTrue(storage.delete_project(saved["id"]))
        self.assertIsNone(storage.load_project(saved["id"]))

    def test_asset_validation(self):
        from delivra import storage
        with self.assertRaises(ValueError):
            storage.save_asset("virus.exe", b"MZ", kind="image")
        with self.assertRaises(ValueError):
            storage.save_asset("vide.png", b"", kind="image")

    def test_data_uri_asset(self):
        from delivra import storage
        png = (b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
               b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
               b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82")
        import base64
        uri = "data:image/png;base64," + base64.b64encode(png).decode()
        path = storage.resolve_asset(uri)
        self.assertIsNotNone(path)
        self.assertTrue(Path(path).exists())


class TestServer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from delivra.server import create_app
        cls.app = create_app()
        cls.client = cls.app.test_client()

    def test_index_and_health(self):
        self.assertEqual(self.client.get("/").status_code, 200)
        self.assertTrue(self.client.get("/healthz").get_json()["ok"])

    def test_bootstrap_catalog(self):
        data = self.client.get("/api/bootstrap").get_json()
        self.assertIn("palettes", data["catalog"])
        self.assertIn("playbooks", data)
        self.assertGreaterEqual(len(data["playbooks"]), 6)

    def test_generate_endpoint(self):
        r = self.client.post("/api/generate", json={"brief": BRIEF, "save": False})
        self.assertEqual(r.status_code, 200)
        body = r.get_json()
        self.assertGreaterEqual(body["quality"]["score"], 70)
        self.assertTrue(body["document"]["sections"])

    def test_preview_endpoint(self):
        doc = generate(BRIEF)
        r = self.client.post("/api/preview", json={"document": doc, "pages": [1, 2], "scale": 0.8})
        self.assertEqual(r.status_code, 200)
        body = r.get_json()
        self.assertEqual(len(body["pages"]), 2)
        self.assertTrue(body["pages"][0]["image"].startswith("data:image/jpeg;base64,"))
        self.assertTrue(body["sections"])

    def test_export_endpoints(self):
        doc = generate(BRIEF)
        for fmt, magic in (("pdf", b"%PDF"), ("docx", b"PK"), ("pptx", b"PK"), ("md", b"# ")):
            with self.subTest(fmt=fmt):
                r = self.client.post(f"/api/export/{fmt}", json={"document": doc})
                self.assertEqual(r.status_code, 200)
                self.assertTrue(r.data.startswith(magic))

    def test_unknown_format_rejected(self):
        doc = generate(BRIEF)
        r = self.client.post("/api/export/exe", json={"document": doc})
        self.assertEqual(r.status_code, 400)

    def test_text_to_image(self):
        r = self.client.post("/api/visual", json={"kind": "cover", "style": {"palette": "nuit"}})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.get_json()["asset"].startswith("assets/"))

    def test_project_crud(self):
        doc = generate(BRIEF)
        created = self.client.post("/api/projects", json={"document": doc}).get_json()
        pid = created["document"]["id"]
        self.assertEqual(self.client.get(f"/api/projects/{pid}").status_code, 200)
        doc["meta"]["title"] = "Titre modifié"
        saved = self.client.put(f"/api/projects/{pid}", json={"document": doc}).get_json()
        self.assertEqual(saved["document"]["meta"]["title"], "Titre modifié")
        self.assertTrue(self.client.delete(f"/api/projects/{pid}").get_json()["deleted"])

    def test_rewrite_falls_back_locally(self):
        r = self.client.post("/api/rewrite", json={"text": "il faut faire beaucoup de chose", "tone": "professionnel"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_json()["engine"], "local")


if __name__ == "__main__":
    unittest.main(verbosity=2)
