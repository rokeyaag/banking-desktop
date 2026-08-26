import os
import sys
from pathlib import Path

CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "banking-desktop"))

os.environ["VERCEL"] = "1"

try:
    from web.app import app as _app
except ImportError:
    from banking_desktop.web.app import app as _app

app = _app
handler = _app
application = _app
