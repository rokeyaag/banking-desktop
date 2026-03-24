from PySide6.QtWidgets import QWidget, QHBoxLayout, QLineEdit, QPushButton
from PySide6.QtCore import Signal, QTimer

class SearchBar(QWidget):
    search_changed = Signal(str)

    def __init__(self, placeholder="Search...", parent=None):
        super().__init__(parent)
        self._timer = QTimer(); self._timer.setSingleShot(True); self._timer.timeout.connect(self._emit)
        layout = QHBoxLayout(self); layout.setContentsMargins(0,0,0,0)
        self.input = QLineEdit()
        self.input.setPlaceholderText(placeholder)
        self.input.setStyleSheet("QLineEdit { background: #1e293b; border: 1px solid #334155; border-radius: 8px; color: #e2e8f0; padding: 8px 14px; font-size: 13px; } QLineEdit:focus { border-color: #3b82f6; }")
        self.input.textChanged.connect(lambda: self._timer.start(300))
        layout.addWidget(self.input)

    def _emit(self): self.search_changed.emit(self.input.text().strip())
