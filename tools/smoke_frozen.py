"""Vérifie que le binaire empaqueté démarre et répond sur /healthz.

Utilisé par la CI après PyInstaller, et exécutable à la main :

    python tools/smoke_frozen.py [chemin/du/binaire]
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

PORT = int(os.environ.get("DELIVRA_SMOKE_PORT", "8791"))


def main() -> int:
    if len(sys.argv) > 1:
        exe = Path(sys.argv[1])
    else:
        exe = Path("dist/Delivra") / ("Delivra.exe" if os.name == "nt" else "Delivra")
    if not exe.exists():
        print(f"Binaire introuvable : {exe}", file=sys.stderr)
        return 2

    env = dict(os.environ,
               DELIVRA_BROWSER_ONLY="1",
               DELIVRA_NO_BROWSER="1",
               DELIVRA_PORT=str(PORT),
               DELIVRA_HOME="smoke-data",
               PYTHONUNBUFFERED="1")
    proc = subprocess.Popen([str(exe)], env=env,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

    url = f"http://127.0.0.1:{PORT}/healthz"
    ok = False
    for _ in range(90):
        if proc.poll() is not None:
            print(f"Le processus s'est arrêté prématurément (code {proc.returncode}).",
                  file=sys.stderr)
            break
        time.sleep(1)
        try:
            with urllib.request.urlopen(url, timeout=2) as resp:
                if resp.status == 200:
                    ok = True
                    break
        except Exception:
            continue

    if ok:
        # vérification fonctionnelle : catalogue et génération accessibles
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/api/bootstrap", timeout=5) as r:
                body = r.read()
            ok = r.status == 200 and b"palettes" in body
        except Exception as exc:
            print(f"/api/bootstrap indisponible : {exc}", file=sys.stderr)
            ok = False

    proc.terminate()
    try:
        out = proc.communicate(timeout=20)[0].decode(errors="ignore")
    except Exception:
        proc.kill()
        out = ""
    if out.strip():
        print(out[-4000:])
    print("Démarrage vérifié" if ok else "ÉCHEC du smoke test", file=sys.stderr)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
