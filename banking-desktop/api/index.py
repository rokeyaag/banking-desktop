import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

os.environ["VERCEL"] = "1"

from web.app import app as _app

app = _app
handler = _app
application = _app
