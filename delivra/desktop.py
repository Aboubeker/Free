"""Point d'entrée de l'application de bureau empaquetée (.exe / .app / binaire).

Comportement :
    • démarre le serveur local sur le premier port libre (127.0.0.1),
    • ouvre une fenêtre native si pywebview + WebView2 sont disponibles,
    • sinon ouvre l'interface dans le navigateur par défaut.
Aucun accès réseau sortant n'est nécessaire.
"""
from __future__ import annotations

import multiprocessing
import os
import socket
import sys
import threading
import time
import webbrowser
from pathlib import Path

if __package__ in (None, ""):
    # exécution directe (« python delivra/desktop.py ») ou script PyInstaller :
    # on rétablit l'import par chemin absolu du paquet
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

WINDOW_TITLE = "Delivra — agent de livrables"


def _free_port(preferred: int = 8760) -> int:
    for port in range(preferred, preferred + 60):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _start_server(port: int) -> threading.Thread:
    from delivra.server import create_app
    app = create_app()

    def run() -> None:
        try:
            from waitress import serve  # type: ignore
            serve(app, host="127.0.0.1", port=port, threads=8)
        except ImportError:
            app.run(host="127.0.0.1", port=port, threaded=True, use_reloader=False, debug=False)

    t = threading.Thread(target=run, daemon=True, name="delivra-server")
    t.start()
    return t


def _wait_ready(port: int, timeout: float = 25.0) -> bool:
    import urllib.request
    deadline = time.time() + timeout
    url = f"http://127.0.0.1:{port}/healthz"
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1.5) as r:
                if r.status == 200:
                    return True
        except Exception:
            time.sleep(0.25)
    return False


def main() -> int:
    multiprocessing.freeze_support()
    port = _free_port(int(os.environ.get("DELIVRA_PORT", "8760")))
    url = f"http://127.0.0.1:{port}/"
    _start_server(port)
    ready = _wait_ready(port)
    if not ready:
        print("Le serveur local n'a pas démarré.", file=sys.stderr)

    no_browser = os.environ.get("DELIVRA_NO_BROWSER") == "1"

    if os.environ.get("DELIVRA_BROWSER_ONLY") == "1":
        if not no_browser:
            _open_browser(url)
        return _keep_alive()

    try:
        import webview  # type: ignore
    except Exception:
        print(f"Delivra est disponible sur {url}")
        if not no_browser:
            _open_browser(url)
        return _keep_alive()

    try:
        window = webview.create_window(
            WINDOW_TITLE, url, width=1440, height=920, min_size=(1024, 680),
            background_color="#0d1017", text_select=True,
        )
        webview.start(debug=bool(os.environ.get("DELIVRA_DEBUG")))
        return 0
    except Exception as exc:  # WebView2 absent, session graphique indisponible…
        print(f"Fenêtre native indisponible ({exc}) — ouverture du navigateur.")
        if not no_browser:
            _open_browser(url)
        return _keep_alive()


def _open_browser(url: str) -> None:
    """Ouvre le navigateur sans jamais faire échouer le démarrage (CI sans écran)."""
    try:
        webbrowser.open(url)
    except Exception as exc:  # aucun navigateur disponible
        print(f"Navigateur indisponible ({exc}) — ouvrez {url}", file=sys.stderr)


def _keep_alive() -> int:
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    sys.exit(main())
