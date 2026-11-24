"""Persistance locale : projets, assets importés, exports générés.

Tout vit sous le dossier de données utilisateur (aucun serveur, aucun cloud) :
    Windows : %APPDATA%\\Delivra
    macOS   : ~/Library/Application Support/Delivra
    Linux   : ~/.local/share/Delivra
Un dossier `data/` à la racine de l'application (mode portable) est prioritaire
s'il existe.
"""
from __future__ import annotations

import base64
import binascii
import json
import os
import re
import shutil
import sys
import tempfile
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

APP_DIR_NAME = "Delivra"
MAX_UPLOAD = 12 * 1024 * 1024  # 12 Mo par fichier
ALLOWED_IMAGES = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".svg"}
ALLOWED_DOCS = {".pdf"}
_LOCK = threading.RLock()


def app_root() -> Path:
    """Racine de l'application (gère PyInstaller)."""
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parents[1]


def bundle_dir() -> Path:
    """Dossier des ressources embarquées (lecture seule)."""
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent)) / "delivra" \
            if (Path(getattr(sys, "_MEIPASS", "")) / "delivra").exists() \
            else Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parent


def data_dir() -> Path:
    env = os.environ.get("DELIVRA_HOME")
    if env:
        p = Path(env)
    else:
        portable = Path(sys.executable if getattr(sys, "frozen", False) else __file__).resolve().parent
        candidates = [portable.parent / "data", app_root() / "data"]
        found = next((c for c in candidates if c.is_dir() and os.access(c, os.W_OK)), None)
        if found:
            p = found
        elif sys.platform.startswith("win"):
            p = Path(os.environ.get("APPDATA", tempfile.gettempdir())) / APP_DIR_NAME
        elif sys.platform == "darwin":
            p = Path.home() / "Library" / "Application Support" / APP_DIR_NAME
        else:
            p = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / APP_DIR_NAME
    for sub in ("projects", "assets", "exports", "tmp"):
        (p / sub).mkdir(parents=True, exist_ok=True)
    return p


def projects_dir() -> Path:
    return data_dir() / "projects"


def assets_dir() -> Path:
    return data_dir() / "assets"


def exports_dir() -> Path:
    return data_dir() / "exports"


# --------------------------------------------------------------------------- #
#  Projets                                                                    #
# --------------------------------------------------------------------------- #
def _safe_id(value: str) -> str:
    sid = re.sub(r"[^a-zA-Z0-9_-]", "", str(value or ""))[:60]
    if not sid:
        raise ValueError("identifiant invalide")
    return sid


def project_path(pid: str) -> Path:
    return projects_dir() / f"{_safe_id(pid)}.json"


def list_projects() -> List[Dict[str, Any]]:
    out = []
    for f in sorted(projects_dir().glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            meta = data.get("meta") or {}
            out.append({
                "id": data.get("id") or f.stem,
                "title": meta.get("title") or "Sans titre",
                "client": meta.get("client") or "",
                "project": meta.get("project") or "",
                "date": meta.get("date") or "",
                "version": meta.get("version") or "",
                "sections": len(data.get("sections") or []),
                "updated_at": data.get("updated_at") or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(f.stat().st_mtime)),
                "palette": (data.get("style") or {}).get("palette") or "ocean",
            })
        except Exception:
            continue
    return out


def load_project(pid: str) -> Optional[Dict[str, Any]]:
    p = project_path(pid)
    if not p.exists():
        return None
    with _LOCK:
        return json.loads(p.read_text(encoding="utf-8"))


def save_project(doc: Dict[str, Any]) -> Dict[str, Any]:
    from .model import normalize
    doc = normalize(doc)
    path = project_path(doc["id"])
    tmp = path.with_suffix(".json.tmp")
    with _LOCK:
        tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
        tmp.replace(path)
    return doc


def delete_project(pid: str) -> bool:
    p = project_path(pid)
    if p.exists():
        with _LOCK:
            p.unlink()
        return True
    return False


def duplicate_project(pid: str) -> Optional[Dict[str, Any]]:
    doc = load_project(pid)
    if not doc:
        return None
    doc["id"] = f"dlv-{uuid.uuid4().hex[:10]}"
    doc["meta"]["title"] = (doc["meta"].get("title") or "Livrable") + " (copie)"
    return save_project(doc)


# --------------------------------------------------------------------------- #
#  Assets                                                                     #
# --------------------------------------------------------------------------- #
def _ext(filename: str) -> str:
    return Path(filename or "").suffix.lower()


def _decode_data_uri(value: str) -> Optional[bytes]:
    if not isinstance(value, str) or not value.startswith("data:"):
        return None
    try:
        header, payload = value.split(",", 1)
        if ";base64" in header:
            return base64.b64decode(payload, validate=False)
        from urllib.parse import unquote_to_bytes
        return unquote_to_bytes(payload)
    except (ValueError, binascii.Error):
        return None


def save_asset(filename: str, data: bytes, *, kind: str = "image") -> Dict[str, Any]:
    ext = _ext(filename)
    allowed = ALLOWED_IMAGES | ({"." + kind} if kind in ("svg",) else set())
    if kind == "image":
        allowed = ALLOWED_IMAGES
    elif kind == "document":
        allowed = ALLOWED_DOCS
    if ext not in allowed:
        raise ValueError(f"Format non autorisé : {ext or 'inconnu'}")
    if len(data) == 0:
        raise ValueError("Fichier vide")
    if len(data) > MAX_UPLOAD:
        raise ValueError("Fichier trop volumineux (max 12 Mo)")
    aid = f"ast-{uuid.uuid4().hex[:12]}"
    dest = assets_dir() / f"{aid}{ext}"
    with _LOCK:
        dest.write_bytes(data)
    return {
        "id": aid,
        "name": Path(filename or dest.name).name[:200],
        "kind": kind,
        "asset": f"assets/{aid}{ext}",
        "size": len(data),
        "ext": ext,
    }


def resolve_asset(reference: str) -> Optional[Path]:
    """Résout `assets/xxx.png` ou un data-URI vers un chemin réel sur disque."""
    if not reference:
        return None
    if isinstance(reference, str) and reference.startswith("data:"):
        raw = _decode_data_uri(reference)
        if raw is None:
            return None
        aid = f"inline-{uuid.uuid4().hex[:10]}"
        ext = ".png"
        if reference.startswith("data:image/jpeg"):
            ext = ".jpg"
        elif reference.startswith("data:image/svg"):
            ext = ".svg"
        dest = assets_dir() / f"{aid}{ext}"
        with _LOCK:
            dest.write_bytes(raw)
        return _rasterize_svg(dest)
    p = Path(reference)
    if p.is_absolute() and p.exists():
        return _rasterize_svg(p)
    candidate = data_dir() / reference
    if candidate.exists():
        return _rasterize_svg(candidate)
    alt = assets_dir() / Path(reference).name
    if alt.exists():
        return _rasterize_svg(alt)
    return None


def _rasterize_svg(path: Path) -> Path:
    """Convertit un SVG en PNG pour ReportLab / PPTX (raster libre)."""
    if path.suffix.lower() != ".svg":
        return path
    png = path.with_suffix(".png")
    if png.exists() and png.stat().st_mtime >= path.stat().st_mtime:
        return png
    try:
        from svglib.svglib import svg2rlg
        from reportlab.graphics import renderPM
        drawing = svg2rlg(str(path))
        if drawing:
            renderPM.drawToFile(drawing, str(png), fmt="PNG", bg=0xFFFFFF)
            return png
    except Exception:
        pass
    try:
        from PIL import Image
        img = Image.new("RGBA", (600, 200), (255, 255, 255, 255))
        img.save(png)
        return png
    except Exception:
        return path


def list_assets() -> List[Dict[str, Any]]:
    out = []
    for f in sorted(assets_dir().iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
        if f.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg", ".bmp", ".pdf"):
            st = f.stat()
            try:
                from PIL import Image
                with Image.open(f) as im:
                    dims = f"{im.width}×{im.height}"
            except Exception:
                dims = ""
            out.append({
                "id": f.stem, "name": f.name, "asset": f"assets/{f.name}",
                "size": st.st_size, "dims": dims, "ext": f.suffix.lower(),
                "modified": time.strftime("%d/%m/%Y %H:%M", time.localtime(st.st_mtime)),
            })
    return out


def delete_asset(asset_ref: str) -> bool:
    name = Path(asset_ref).name
    f = assets_dir() / name
    if f.exists() and f.resolve().parent == assets_dir().resolve():
        with _LOCK:
            f.unlink()
        return True
    return False


def asset_bytes(asset_ref: str) -> Optional[bytes]:
    p = resolve_asset(asset_ref)
    if p and Path(p).exists():
        return Path(p).read_bytes()
    return None
