"""Sesiones Chromium efímeras; sin perfil persistente ni lectura de OTP."""
import os
import subprocess
import sys
import threading
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
REGISTRATION_URL = 'https://cnshopper.com/?invite_id=2370842&promoter_id=2370842'


def launch_browser(mode='desktop', client=None, on_error=None, attempt_id=None):
    """Inicia una sesión temporal aislada en otro proceso. No guarda datos en disco del proyecto."""
    if mode not in ('mobile', 'desktop'):
        raise ValueError('Vista no válida')
    client = client or {}
    command = [sys.executable, str(APP_DIR / 'browser_worker.py'), mode,
               REGISTRATION_URL, client.get('name', ''), client.get('email', ''),
               client.get('phone', '')]
    if attempt_id is not None:
        command.append(str(attempt_id))
    flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
    try:
        proc = subprocess.Popen(command, cwd=str(APP_DIR), creationflags=flags,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                text=True)
    except OSError as exc:
        if on_error:
            on_error(str(exc))
        return False

    def watch():
        output, error = proc.communicate()
        if proc.returncode and on_error:
            on_error((error or 'No se pudo iniciar Chromium.').strip()[-1800:])
    threading.Thread(target=watch, daemon=True).start()
    return True
