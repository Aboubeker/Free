"""Serveur local Delivra — une seule app, deux usages.

* L'interface web (SPA) est servie depuis `delivra/static/`.
* L'API REST permet de générer, éditer, prévisualiser et exporter les livrables.
* Le même module embarque le mode bureau (fenêtre native) : `--desktop`.

L'application ne dépend d'aucun service en ligne : tout est stocké localement.
"""
from __future__ import annotations

import argparse
import io
import json
import mimetypes
import os
import socket
import sys
import threading
import time
import webbrowser
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import unquote

from flask import Flask, Response, jsonify, request, send_file, send_from_directory

from . import __version__
from .ai import engine as ai
from .model import blank_deliverable, normalize, outline, quality_report
from .theme import Style, catalog

STATIC_DIR = Path(__file__).resolve().parent / "static"


def create_app() -> Flask:
    app = Flask(__name__, static_folder=str(STATIC_DIR), static_url_path="/static")
    app.config["MAX_CONTENT_LENGTH"] = 64 * 1024 * 1024
    app.json.ensure_ascii = False

    # ---------------------------------------------------------------- #
    #  Utilitaires                                                      #
    # ---------------------------------------------------------------- #
    def error(message: str, code: int = 400):
        return jsonify({"error": message}), code

    @app.after_request
    def no_cache_api(resp: Response) -> Response:
        if request.path.startswith("/api/"):
            resp.headers["Cache-Control"] = "no-store"
        return resp

    @app.errorhandler(413)
    def too_large(_e):
        return error("Fichier trop volumineux (64 Mo maximum).", 413)

    @app.errorhandler(Exception)
    def on_error(exc: Exception):
        import traceback
        traceback.print_exc()
        return error(f"Erreur interne : {exc}", 500)

    # ---------------------------------------------------------------- #
    #  Interface                                                        #
    # ---------------------------------------------------------------- #
    @app.get("/")
    def index():
        html = (STATIC_DIR / "index.html").read_text(encoding="utf-8")
        return Response(html, mimetype="text/html")

    @app.get("/favicon.ico")
    def favicon():
        icon = STATIC_DIR / "favicon.svg"
        if icon.exists():
            return send_file(icon, mimetype="image/svg+xml")
        return Response(status=204)

    @app.get("/api/fonts/<name>")
    def font_file(name: str):
        from .theme import FONT_DIR
        safe = Path(name).name
        if not safe.endswith(".ttf"):
            safe += ".ttf"
        target = FONT_DIR / safe
        if not target.exists():
            return error("Police introuvable.", 404)
        return send_file(target, mimetype="font/ttf", max_age=86400)

    @app.get("/healthz")
    def healthz():
        return jsonify({"ok": True, "version": __version__})

    # ---------------------------------------------------------------- #
    #  Catalogue & réglages                                             #
    # ---------------------------------------------------------------- #
    @app.get("/api/bootstrap")
    def bootstrap():
        from . import storage
        provider = ai.build_provider(_settings())
        return jsonify({
            "version": __version__,
            "catalog": catalog(),
            "playbooks": [{"key": k, **{kk: vv for kk, vv in v.items() if kk != "architecture_layers"}}
                          for k, v in ai.PLAYBOOKS.items()],
            "block_types": ai.__dict__.get("BLOCK_TYPES", []),
            "ai": {"provider": provider.name, "available": provider.available},
            "paths": {"data": str(storage.data_dir())},
            "defaults": blank_deliverable(),
        })

    def _settings_path() -> Path:
        from .storage import data_dir
        return data_dir() / "settings.json"

    def _settings() -> Dict[str, Any]:
        p = _settings_path()
        if p.exists():
            try:
                return json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                return {}
        return {}

    @app.get("/api/settings")
    def get_settings():
        s = dict(_settings())
        if s.get("api_key"):
            s["api_key_set"] = True
            s["api_key"] = "••••" + str(s["api_key"])[-4:]
        return jsonify(s)

    @app.post("/api/settings")
    def post_settings():
        body = request.get_json(silent=True) or {}
        current = _settings()
        if body.get("api_key") and not str(body["api_key"]).startswith("••••"):
            current["api_key"] = str(body["api_key"])[:300]
        for key in ("provider", "model", "base_url", "default_palette", "default_typography"):
            if key in body:
                current[key] = str(body.get(key) or "")[:300]
        _settings_path().write_text(json.dumps(current, indent=2), encoding="utf-8")
        provider = ai.build_provider(current)
        return jsonify({"ok": True, "ai": {"provider": provider.name, "available": provider.available}})

    @app.post("/api/settings/test")
    def test_settings():
        provider = ai.build_provider(_settings())
        if not provider.available:
            return jsonify({"ok": False, "message": "Aucun fournisseur LLM configuré — le moteur local reste actif."})
        out = provider.complete("Tu réponds en un mot.", "Réponds uniquement : OK", max_tokens=10)
        return jsonify({"ok": bool(out), "message": out or "Connexion impossible.",
                        "provider": provider.name})

    @app.get("/api/ai/status")
    def ai_status():
        provider = ai.build_provider(_settings())
        return jsonify({"provider": provider.name, "available": provider.available})

    # ---------------------------------------------------------------- #
    #  Génération & analyse                                             #
    # ---------------------------------------------------------------- #
    @app.post("/api/generate")
    def generate():
        body = request.get_json(silent=True) or {}
        brief = body.get("brief") or body
        if not isinstance(brief, dict):
            return error("Brief invalide.")
        doc = ai.generate(brief, _settings())
        if body.get("save", True):
            from . import storage
            doc = storage.save_project(doc)
        return jsonify({"document": doc, "quality": quality_report(doc), "outline": outline(doc)})

    @app.post("/api/plan")
    def plan():
        body = request.get_json(silent=True) or {}
        p = ai.plan_outline(body)
        return jsonify(p)

    @app.post("/api/suggest-titles")
    def suggest_titles():
        body = request.get_json(silent=True) or {}
        return jsonify({"titles": ai.suggest_titles(body, _settings())})

    @app.post("/api/rewrite")
    def rewrite():
        """Réécrit un texte (paragraphe, intro, résumé) via le LLM si disponible."""
        body = request.get_json(silent=True) or {}
        text = str(body.get("text") or "")[:8000]
        tone = str(body.get("tone") or "professionnel")[:40]
        provider = ai.build_provider(_settings())
        if not text.strip():
            return error("Texte vide.")
        if not provider.available:
            return jsonify({"text": _local_rewrite(text, tone), "engine": "local"})
        prompt = (f"Réécris le texte suivant dans un registre {tone}, en français "
                  f"professionnel, sans changer le sens ni ajouter de listes. "
                  f"Réponds au format {{\"text\": \"...\"}}.\n\n{text}")
        raw = provider.complete("Tu es un rédacteur technique senior.", prompt, max_tokens=1200)
        if not raw:
            return jsonify({"text": _local_rewrite(text, tone), "engine": "local"})
        try:
            import re as _re
            data = json.loads(_re.search(r"\{.*\}", raw, flags=_re.S).group(0))
            return jsonify({"text": data.get("text") or text, "engine": provider.name})
        except Exception:
            return jsonify({"text": raw.strip(), "engine": provider.name})

    @app.post("/api/quality")
    def quality():
        body = request.get_json(silent=True) or {}
        doc = normalize(body.get("document") or body)
        return jsonify(quality_report(doc))

    # ---------------------------------------------------------------- #
    #  Projets                                                          #
    # ---------------------------------------------------------------- #
    @app.get("/api/projects")
    def projects_list():
        from . import storage
        return jsonify(storage.list_projects())

    @app.post("/api/projects")
    def projects_create():
        from . import storage
        body = request.get_json(silent=True) or {}
        base = blank_deliverable()
        if body.get("document"):
            doc = normalize(body["document"])
        else:
            doc = normalize({**base, "meta": {**base["meta"], **(body.get("meta") or {})},
                             "sections": body.get("sections") or []})
        doc = storage.save_project(doc)
        return jsonify({"document": doc, "quality": quality_report(doc)})

    @app.get("/api/projects/<pid>")
    def projects_get(pid: str):
        from . import storage
        doc = storage.load_project(pid)
        if not doc:
            return error("Projet introuvable.", 404)
        return jsonify({"document": doc, "quality": quality_report(doc), "outline": outline(doc)})

    @app.put("/api/projects/<pid>")
    def projects_save(pid: str):
        from . import storage
        body = request.get_json(silent=True) or {}
        doc = body.get("document") or body
        doc["id"] = pid
        saved = storage.save_project(doc)
        return jsonify({"document": saved, "quality": quality_report(saved), "saved_at": saved["updated_at"]})

    @app.delete("/api/projects/<pid>")
    def projects_delete(pid: str):
        from . import storage
        return jsonify({"deleted": storage.delete_project(pid)})

    @app.post("/api/projects/<pid>/duplicate")
    def projects_duplicate(pid: str):
        from . import storage
        doc = storage.duplicate_project(pid)
        if not doc:
            return error("Projet introuvable.", 404)
        return jsonify({"document": doc})

    # ---------------------------------------------------------------- #
    #  Assets (logos, captures, PDF)                                    #
    # ---------------------------------------------------------------- #
    @app.post("/api/upload")
    def upload():
        from . import storage
        if "file" not in request.files:
            return error("Aucun fichier reçu.")
        f = request.files["file"]
        kind = request.form.get("kind") or "image"
        data = f.read()
        try:
            meta = storage.save_asset(f.filename or "fichier.png", data, kind=kind)
        except ValueError as exc:
            return error(str(exc))
        if kind == "image":
            try:
                from PIL import Image
                src = storage.resolve_asset(meta["asset"])
                with Image.open(src) as im:
                    meta["width"], meta["height"] = im.width, im.height
                    meta["dims"] = f"{im.width}×{im.height}"
            except Exception:
                pass
        meta["url"] = f"/api/assets/{meta['id']}"
        return jsonify(meta)

    @app.get("/api/assets")
    def assets_list():
        from . import storage
        items = storage.list_assets()
        for it in items:
            it["url"] = f"/api/assets/{Path(it['name']).stem}"
        return jsonify(items)

    @app.get("/api/assets/<path:name>")
    def asset_get(name: str):
        from . import storage
        name = Path(unquote(name)).name
        p = storage.assets_dir() / name
        if not p.exists():
            stem = Path(name).stem
            for ext in (".png", ".jpg", ".jpeg", ".svg", ".webp", ".gif"):
                cand = storage.assets_dir() / f"{stem}{ext}"
                if cand.exists():
                    p = cand
                    break
        if not p.exists():
            return error("Fichier introuvable.", 404)
        mime = mimetypes.guess_type(str(p))[0] or "application/octet-stream"
        return send_file(p, mimetype=mime, max_age=3600)

    @app.delete("/api/assets/<path:name>")
    def asset_delete(name: str):
        from . import storage
        return jsonify({"deleted": storage.delete_asset(name)})

    # ---------------------------------------------------------------- #
    #  Aperçu & exports                                                 #
    # ---------------------------------------------------------------- #
    def _doc_from_request() -> Optional[Dict[str, Any]]:
        body = request.get_json(silent=True) or {}
        if body.get("document"):
            return normalize(body["document"])
        if body.get("id"):
            from . import storage
            return storage.load_project(body["id"])
        return None

    @app.post("/api/preview")
    def preview():
        """Rendu image A4 (ou Letter) pour l'aperçu fidèle dans le navigateur."""
        doc = _doc_from_request()
        if not doc:
            return error("Document introuvable.")
        body = request.get_json(silent=True) or {}
        pages = body.get("pages") or [1]
        section_map = []
        scale = min(3.0, max(0.6, float(body.get("scale") or 1.35)))
        try:
            pages = [max(1, int(p)) for p in pages][:8]
        except (TypeError, ValueError):
            pages = [1]
        from .render import render_pdf_with_toc
        import base64
        try:
            pdf_bytes, toc = render_pdf_with_toc(doc)
            section_map = [{"number": n, "title": t, "page": pg} for n, t, pg in toc]
        except Exception as exc:  # rendu partiel : on informe sans casser l'UI
            return error(f"Échec du rendu : {exc}", 500)
        out = []
        try:
            import pypdfium2 as pdfium
            pdf = pdfium.PdfDocument(pdf_bytes)
            count = len(pdf)
            for n in pages:
                if n > count:
                    continue
                pil = pdf[n - 1].render(scale=scale).to_pil()
                buf = io.BytesIO()
                pil.save(buf, format="JPEG", quality=86, optimize=True)
                out.append({"page": n, "total": count,
                            "image": "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()})
            if not out and count:
                pil = pdf[0].render(scale=scale).to_pil()
                buf = io.BytesIO()
                pil.save(buf, format="JPEG", quality=86)
                out.append({"page": 1, "total": count,
                            "image": "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()})
            return jsonify({"pages": out, "total": count, "sections": section_map})
        except Exception as exc:
            return error(f"Aperçu indisponible : {exc}", 500)

    @app.post("/api/export/<fmt>")
    def export(fmt: str):
        from . import storage
        doc = _doc_from_request()
        if not doc:
            return error("Document introuvable.")
        fmt = fmt.lower()
        body = request.get_json(silent=True) or {}
        safe_name = _filename(doc)
        try:
            if fmt == "pdf":
                from .render import render_pdf
                payload = render_pdf(doc)
                mime, ext = "application/pdf", "pdf"
            elif fmt == "docx":
                from .export.docx_export import build_docx
                payload = build_docx(doc)
                mime, ext = "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "docx"
            elif fmt == "pptx":
                from .export.pptx_export import build_pptx
                payload = build_pptx(doc)
                mime, ext = "application/vnd.openxmlformats-officedocument.presentationml.presentation", "pptx"
            elif fmt in ("json", "delivra"):
                payload = json.dumps(doc, ensure_ascii=False, indent=2).encode("utf-8")
                mime, ext = "application/json", "json"
            elif fmt == "md":
                from .export.markdown_export import build_markdown
                payload = build_markdown(doc).encode("utf-8")
                mime, ext = "text/markdown", "md"
            else:
                return error(f"Format non pris en charge : {fmt}")
        except Exception as exc:
            import traceback
            traceback.print_exc()
            return error(f"Export impossible : {exc}", 500)
        target = storage.exports_dir() / f"{safe_name}.{ext}" if body.get("keep", True) else None
        if target:
            target.write_bytes(payload)
        return send_file(io.BytesIO(payload), mimetype=mime, as_attachment=True,
                         download_name=f"{safe_name}.{ext}")

    @app.get("/api/exports")
    def exports_list():
        from . import storage
        items = []
        for f in sorted(storage.exports_dir().iterdir(),
                        key=lambda x: x.stat().st_mtime, reverse=True)[:40]:
            if f.is_file():
                items.append({"name": f.name, "size": f.stat().st_size,
                              "modified": time.strftime("%d/%m/%Y %H:%M",
                                                        time.localtime(f.stat().st_mtime))})
        return jsonify(items)

    @app.get("/api/exports/<path:name>")
    def exports_get(name: str):
        from . import storage
        f = storage.exports_dir() / Path(unquote(name)).name
        if not f.exists():
            return error("Fichier introuvable.", 404)
        return send_file(f, as_attachment=True, download_name=f.name)

    @app.post("/api/export/preview-bundle")
    def export_bundle():
        """ZIP contenant les trois formats (PDF, Word, PowerPoint)."""
        import zipfile
        from . import storage
        doc = _doc_from_request()
        if not doc:
            return error("Document introuvable.")
        from .render import render_pdf
        from .export.docx_export import build_docx
        from .export.pptx_export import build_pptx
        name = _filename(doc)
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr(f"{name}.pdf", render_pdf(doc))
            z.writestr(f"{name}.docx", build_docx(doc))
            z.writestr(f"{name}.pptx", build_pptx(doc))
            z.writestr(f"{name}.json", json.dumps(doc, ensure_ascii=False, indent=2))
        payload = buf.getvalue()
        (storage.exports_dir() / f"{name}.zip").write_bytes(payload)
        return send_file(io.BytesIO(payload), mimetype="application/zip",
                         as_attachment=True, download_name=f"{name}.zip")

    # ---------------------------------------------------------------- #
    #  Text to image                                                    #
    # ---------------------------------------------------------------- #
    @app.post("/api/visual")
    def visual():
        """Génère un visuel : couverture abstraite, motif ou schéma d'architecture."""
        from . import storage
        body = request.get_json(silent=True) or {}
        kind = body.get("kind") or "cover"
        style = Style(body.get("style") or {})
        seed = int(body.get("seed") or 7)
        from .diagrams import cover_art_png, pattern_png, architecture_png
        try:
            if kind == "cover":
                png = cover_art_png(style, seed=seed)
                name = "couverture"
            elif kind == "pattern":
                png = pattern_png(style, seed=seed)
                name = "motif"
            elif kind == "architecture":
                layers = body.get("layers") or []
                if not layers:
                    pb = ai.PLAYBOOKS.get(body.get("playbook") or "cloud", ai.PLAYBOOKS["cloud"])
                    layers = [{"title": t, "nodes": n, "tone": tone} for t, n, tone in pb["architecture_layers"]]
                png = architecture_png(layers, style, caption=body.get("caption"), width_px=2400)
                name = "architecture"
            else:
                return error("Type de visuel inconnu.")
        except Exception as exc:
            return error(f"Génération impossible : {exc}", 500)
        meta = storage.save_asset(f"{name}-{int(time.time())}.png", png)
        meta["url"] = f"/api/assets/{meta['id']}"
        return jsonify(meta)

    @app.post("/api/ai/architecture")
    def ai_architecture():
        """Propose une architecture en couches à partir d'une description libre."""
        from . import storage
        body = request.get_json(silent=True) or {}
        text = " ".join(str(body.get(k) or "") for k in ("description", "project", "context", "stack"))
        pb_key = ai.detect_playbook(text)
        pb = ai.PLAYBOOKS[pb_key]
        stack = body.get("stack")
        if isinstance(stack, str):
            stack = [s.strip() for s in stack.replace(";", ",").split(",") if s.strip()]
        layers = [{"title": t, "nodes": n, "tone": tone} for t, n, tone in pb["architecture_layers"]]
        if stack:
            layers[2]["nodes"] = list(stack)[:4]
        style = Style(body.get("style") or {})
        from .diagrams import architecture_png
        png = architecture_png(layers, style, caption=body.get("caption") or "Architecture proposée",
                               width_px=2400)
        meta = storage.save_asset(f"architecture-{int(time.time())}.png", png)
        meta["url"] = f"/api/assets/{meta['id']}"
        return jsonify({"layers": layers, "asset": meta, "playbook": pb_key,
                        "playbook_label": pb["label"]})

    return app


def _filename(doc: Dict[str, Any]) -> str:
    import re
    meta = doc.get("meta") or {}
    raw = f"{meta.get('title') or 'livrable'}_{meta.get('client') or ''}_{meta.get('date') or ''}"
    slug = re.sub(r"[^\w\s-]", "", raw, flags=re.UNICODE)
    slug = re.sub(r"[-\s]+", "-", slug).strip("-_")[:90]
    return slug or "livrable"


def _local_rewrite(text: str, tone: str) -> str:
    """Réécriture hors ligne : normalise, structure et reformule légèrement."""
    import re
    t = re.sub(r"\s+", " ", text).strip()
    if not t:
        return ""
    sentences = re.split(r"(?<=[.!?])\s+", t)
    out = []
    replacements = [
        (r"\bfait\b", "réalise"), (r"\bchose\b", "élément"), (r"\bbeaucoup de\b", "de nombreux"),
        (r"\btrès\b", "particulièrement"), (r"\bproblème\b", "difficulté"),
        (r"\bon va\b", "nous allons"), (r"\bil faut\b", "il convient de"),
    ]
    for s in sentences:
        for pat, rep in replacements:
            s = re.sub(pat, rep, s, flags=re.I)
        s = s[0].upper() + s[1:] if s else s
        if not s.endswith((".", "!", "?")):
            s += "."
        out.append(s)
    return " ".join(out)


def find_port(preferred: int = 8760, host: str = "127.0.0.1", attempts: int = 40) -> int:
    for i in range(attempts):
        port = preferred + i
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.bind((host, port))
                return port
            except OSError:
                continue
    return preferred


def serve(host: str = "127.0.0.1", port: Optional[int] = None, debug: bool = False,
          open_browser: bool = True) -> None:
    app = create_app()
    port = port or find_port(host=host if host != "0.0.0.0" else "127.0.0.1")
    url = f"http://{'127.0.0.1' if host == '0.0.0.0' else host}:{port}/"
    print("\n  Delivra — agent de livrables")
    print(f"  Interface : {url}")
    print("  Arrêt     : Ctrl+C\n", flush=True)
    if open_browser and not debug:
        threading.Timer(1.1, lambda: webbrowser.open(url)).start()
    app.run(host=host, port=port, debug=debug, threaded=True, use_reloader=False)


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(description="Delivra — agent IA de livrables")
    parser.add_argument("--host", default=os.environ.get("DELIVRA_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("DELIVRA_PORT", "8760")))
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--desktop", action="store_true", help="Ouvre une fenêtre native (pywebview)")
    args = parser.parse_args(argv)

    if args.desktop:
        return run_desktop(args)

    serve(host=args.host, port=args.port, debug=args.debug,
          open_browser=not args.no_browser)
    return 0


def run_desktop(args: argparse.Namespace) -> int:
    """Fenêtre native : WebView2 sous Windows, WebKit ailleurs."""
    try:
        import webview  # type: ignore
    except ImportError:
        print("pywebview n'est pas installé — ouverture dans le navigateur par défaut.")
        return main([a for a in sys.argv[1:] if a != "--desktop"])
    port = find_port(port=args.port)
    app = create_app()
    threading.Thread(
        target=lambda: app.run(host="127.0.0.1", port=port, threaded=True, use_reloader=False),
        daemon=True).start()
    time.sleep(0.9)
    webview.create_window("Delivra — agent de livrables", f"http://127.0.0.1:{port}/",
                          width=1440, height=920, min_size=(1100, 720))
    webview.start()
    return 0


if __name__ == "__main__":
    sys.exit(main())
