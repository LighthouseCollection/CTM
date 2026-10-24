"""Local-only paths for QA-01. Secrets live outside the repository, under %TEMP%/ctmqa/secrets."""

import json
import os
import tempfile
from pathlib import Path

SECRETS_DIR = Path(os.environ.get("QA01_SECRETS_DIR", Path(tempfile.gettempdir()) / "ctmqa" / "secrets"))
SECRETS_DIR.mkdir(parents=True, exist_ok=True)
RUN_DIR = Path(os.environ.get("QA01_RUN_DIR", Path(tempfile.gettempdir()) / "ctmqa" / "run"))
RUN_DIR.mkdir(parents=True, exist_ok=True)
HARNESS = Path(__file__).resolve().parent
QA_DIR = HARNESS.parent
RUN = os.environ.get("QA01_RUN", "run2")  # run1 = db6dfa3/e4d2fb3, run2 = bb3e48b/65fa389
EVIDENCE = QA_DIR / "evidence" / RUN
EVIDENCE.mkdir(parents=True, exist_ok=True)
BASE_URL = "http://127.0.0.1:18870"


def save_env(values):
    path = SECRETS_DIR / "env.json"
    current = json.loads(path.read_text()) if path.exists() else {}
    current.update(values)
    path.write_text(json.dumps(current))


def load_env():
    return json.loads((SECRETS_DIR / "env.json").read_text())


def fixtures():
    """Synthetic record ids and test-issued session cookies (cookies never leave SECRETS_DIR)."""
    return json.loads((SECRETS_DIR / "fixtures.json").read_text())
