import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("NexaBank")
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    app.setStyleSheet("""
        * { font-family: 'Segoe UI', sans-serif; }
        QScrollBar:vertical { background:#0f172a; width:8px; border-radius:4px; }
        QScrollBar::handle:vertical { background:#334155; border-radius:4px; min-height:20px; }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height:0px; }
    """)

    import logging
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    log = logging.getLogger(__name__)

    try:
        from app.db.session import init_db
        init_db()
        log.info("Database initialized.")
    except Exception as e:
        log.error(f"Database init failed: {e}")

    from app.ui.app_window import AppWindow
    window = AppWindow()
    window.show()
    log.info("NexaBank started.")
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
