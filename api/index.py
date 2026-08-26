import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(ROOT_DIR / "banking-desktop"))

try:
    from web.app import app
except ImportError:
    from banking_desktop.web.app import app
