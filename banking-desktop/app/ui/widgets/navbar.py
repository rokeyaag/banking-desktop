from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QSpacerItem, QSizePolicy
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QFont

BG = "#0d1117"; ACCENT = "#3b82f6"; TEXT = "#e2e8f0"; MUTED = "#64748b"

class NavBar(QWidget):
    navigate = Signal(str)
    logout_requested = Signal()

    def __init__(self):
        super().__init__()
        self.setStyleSheet(f"background-color: {BG}; border-right: 1px solid #1e293b;")
        self._active = ""
        self._btns = {}
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 20, 12, 20)
        layout.setSpacing(4)

        # Logo
        logo = QLabel("🏦 NexaBank")
        logo.setFont(QFont("Segoe UI", 16, QFont.Bold))
        logo.setStyleSheet(f"color: {ACCENT}; padding: 8px 4px 20px 4px; background: transparent;")
        layout.addWidget(logo)

        # User info
        self.user_label = QLabel("Welcome")
        self.user_label.setStyleSheet(f"color: {MUTED}; font-size: 11px; padding: 0 4px 12px 4px; background: transparent;")
        self.user_label.setWordWrap(True)
        layout.addWidget(self.user_label)

        # MAIN
        layout.addWidget(self._section_lbl("MAIN"))
        for key, label in [
            ("dashboard", "📊  Dashboard"),
            ("accounts",  "🏦  Accounts"),
            ("deposit",   "💰  Deposit"),
        ]:
            layout.addWidget(self._make_btn(key, label))

        layout.addSpacing(8)

        # BANKING
        layout.addWidget(self._section_lbl("BANKING"))
        for key, label in [
            ("transfer",     "💸  Transfer"),
            ("transactions", "📋  Transactions"),
            ("statement",    "📄  Statement"),
            ("loan",         "🧮  Loan Calculator"),
        ]:
            layout.addWidget(self._make_btn(key, label))

        layout.addSpacing(8)

        # AI TOOLS
        layout.addWidget(self._section_lbl("AI TOOLS"))
        for key, label in [
            ("ai_mode", "🤖  AI Mode"),
            ("chatbot",  "💬  Chatbot"),
        ]:
            layout.addWidget(self._make_btn(key, label))

        layout.addSpacerItem(QSpacerItem(0, 0, QSizePolicy.Minimum, QSizePolicy.Expanding))

        # Logout
        logout = QPushButton("⇠  Logout")
        logout.setFixedHeight(40)
        logout.setCursor(Qt.PointingHandCursor)
        logout.clicked.connect(self.logout_requested.emit)
        logout.setStyleSheet("""
            QPushButton { background: transparent; color: #ef4444; border: 1px solid #ef4444;
                border-radius: 8px; font-size: 13px; text-align: left; padding-left: 16px; }
            QPushButton:hover { background: #ef444422; }
        """)
        layout.addWidget(logout)

    def _section_lbl(self, text):
        lbl = QLabel(text)
        lbl.setFont(QFont("Segoe UI", 9, QFont.Bold))
        lbl.setStyleSheet("color: #7c93b0; font-size: 9px; font-weight: 700; letter-spacing: 2px; padding: 4px 6px 2px 6px; background: transparent;")
        return lbl

    def _make_btn(self, key, label):
        btn = QPushButton(label)
        btn.setFixedHeight(40)
        btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(lambda _, k=key: self.navigate.emit(k))
        btn.setStyleSheet(self._btn_style(False))
        self._btns[key] = btn
        return btn

    def _btn_style(self, active: bool) -> str:
        if active:
            return f"QPushButton {{ background-color: {ACCENT}22; color: {ACCENT}; border: none; border-left: 3px solid {ACCENT}; border-radius: 8px; font-size: 13px; font-weight: 600; text-align: left; padding-left: 13px; }} QPushButton:hover {{ background-color: {ACCENT}33; }}"
        return f"QPushButton {{ background-color: transparent; color: {TEXT}; border: none; border-radius: 8px; font-size: 13px; text-align: left; padding-left: 16px; }} QPushButton:hover {{ background-color: #1e293b; }}"

    def set_user(self, user):
        self.user_label.setText(f"{user.full_name}\n{user.email}")

    def set_active(self, key: str):
        if self._active and self._active in self._btns:
            self._btns[self._active].setStyleSheet(self._btn_style(False))
        self._active = key
        if key in self._btns:
            self._btns[key].setStyleSheet(self._btn_style(True))