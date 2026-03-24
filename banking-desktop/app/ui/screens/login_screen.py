from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QSizePolicy, QGraphicsDropShadowEffect,
    QSplitter
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor

BG       = "#070d1a"
CARD     = "#111c33"
ACCENT   = "#3b82f6"
ACCENT2  = "#6366f1"
MUTED    = "#4a5568"
TEXT     = "#e2e8f0"
SUBTEXT  = "#8896a9"
ERROR    = "#ef4444"
BORDER   = "#1e2d4a"
INPUT_BG = "#0a1628"


def _input_style():
    return f"""
        QLineEdit {{
            background-color: {INPUT_BG};
            border: 1.5px solid {BORDER};
            border-radius: 10px;
            color: {TEXT};
            padding: 12px 16px;
            font-size: 13px;
            font-family: 'Segoe UI';
        }}
        QLineEdit:focus {{
            border-color: {ACCENT};
            background-color: #0d1e38;
        }}
        QLineEdit::placeholder {{ color: {MUTED}; }}
    """


class GlowButton(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setFixedHeight(48)
        self.setCursor(Qt.PointingHandCursor)
        self._update_style(False)

    def _update_style(self, hovered):
        bg = "stop:0 #4f8ef7, stop:1 #7c7ff5" if hovered else f"stop:0 {ACCENT}, stop:1 {ACCENT2}"
        self.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0, {bg});
                color: white; border: none; border-radius: 10px;
                font-size: 14px; font-weight: 700;
                font-family: 'Segoe UI'; letter-spacing: 0.5px;
            }}
        """)

    def enterEvent(self, e): self._update_style(True); super().enterEvent(e)
    def leaveEvent(self, e): self._update_style(False); super().leaveEvent(e)


class LoginScreen(QWidget):
    login_success = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background-color: {BG};")
        self._mode = "login"
        self._build_ui()

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # QSplitter gives true 50/50
        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(0)
        splitter.setStyleSheet("QSplitter::handle { background: #1e2d4a; width: 1px; }")

        # ── LEFT PANEL ───────────────────────────────────────────
        left = QWidget()
        left.setStyleSheet("""
            background: qlineargradient(
                x1:0, y1:0, x2:1, y2:1,
                stop:0 #060d1f, stop:0.5 #0a1628, stop:1 #0d1e38
            );
        """)
        ll = QVBoxLayout(left)
        ll.setAlignment(Qt.AlignCenter)
        ll.setContentsMargins(48, 48, 48, 48)
        ll.setSpacing(0)

        # Icon with glow
        icon_wrap = QWidget()
        icon_wrap.setFixedSize(86, 86)
        icon_wrap.setStyleSheet(f"""
            background: qradialgradient(cx:0.5,cy:0.5,radius:0.5,
                stop:0 #1a3a6e, stop:1 #0a1628);
            border-radius: 43px;
            border: 2px solid {ACCENT};
        """)
        iw_layout = QVBoxLayout(icon_wrap)
        iw_layout.setAlignment(Qt.AlignCenter)
        icon_lbl = QLabel("🏦")
        icon_lbl.setFont(QFont("Segoe UI", 32))
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setStyleSheet("background:transparent; border:none;")
        iw_layout.addWidget(icon_lbl)
        glow = QGraphicsDropShadowEffect()
        glow.setBlurRadius(35)
        glow.setColor(QColor(59, 130, 246, 180))
        glow.setOffset(0, 0)
        icon_wrap.setGraphicsEffect(glow)
        ll.addWidget(icon_wrap, 0, Qt.AlignCenter)
        ll.addSpacing(16)

        bank_name = QLabel("NexaBank")
        bank_name.setFont(QFont("Segoe UI", 32, QFont.Bold))
        bank_name.setStyleSheet(f"color:{TEXT}; background:transparent; letter-spacing:3px;")
        bank_name.setAlignment(Qt.AlignCenter)
        ll.addWidget(bank_name)

        tagline = QLabel("Next Generation Banking")
        tagline.setFont(QFont("Segoe UI", 11))
        tagline.setStyleSheet(f"color:{SUBTEXT}; background:transparent; letter-spacing:1px;")
        tagline.setAlignment(Qt.AlignCenter)
        ll.addWidget(tagline)
        ll.addSpacing(44)

        for icon, text in [
            ("◈", "AI-Guided Banking Flows"),
            ("⬡", "Smart Chatbot Assistant"),
            ("◉", "Secure PIN Transactions"),
            ("☁", "Document Upload & RAG"),
        ]:
            row = QHBoxLayout(); row.setSpacing(14)
            i = QLabel(icon)
            i.setFont(QFont("Segoe UI", 12))
            i.setFixedWidth(22)
            i.setStyleSheet(f"color:{ACCENT}; background:transparent;")
            t = QLabel(text)
            t.setFont(QFont("Segoe UI", 11))
            t.setStyleSheet(f"color:{SUBTEXT}; background:transparent;")
            row.addWidget(i); row.addWidget(t); row.addStretch()
            ll.addLayout(row)
            ll.addSpacing(10)

        ll.addStretch()
        btm = QLabel("Secure  ·  Intelligent  ·  Modern")
        btm.setFont(QFont("Segoe UI", 9))
        btm.setStyleSheet(f"color:{MUTED}; background:transparent; letter-spacing:2px;")
        btm.setAlignment(Qt.AlignCenter)
        ll.addWidget(btm)

        # ── RIGHT PANEL ──────────────────────────────────────────
        right = QWidget()
        right.setStyleSheet(f"background-color:{BG};")
        rl = QVBoxLayout(right)
        rl.setAlignment(Qt.AlignCenter)
        rl.setContentsMargins(40, 40, 40, 40)

        self.form_card = QFrame()
        self.form_card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.form_card.setStyleSheet(f"""
            QFrame {{
                background-color: {CARD};
                border-radius: 18px;
                border: 1px solid {BORDER};
            }}
        """)
        card_shadow = QGraphicsDropShadowEffect()
        card_shadow.setBlurRadius(40)
        card_shadow.setColor(QColor(0, 0, 0, 130))
        card_shadow.setOffset(0, 8)
        self.form_card.setGraphicsEffect(card_shadow)

        self.form_layout = QVBoxLayout(self.form_card)
        self.form_layout.setContentsMargins(36, 38, 36, 38)
        self.form_layout.setSpacing(0)
        self._build_form()

        rl.addWidget(self.form_card)

        # Add both to splitter — equal sizes
        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setSizes([500, 500])  # true 50/50
        splitter.setCollapsible(0, False)
        splitter.setCollapsible(1, False)

        root.addWidget(splitter)

    def _build_form(self):
        while self.form_layout.count():
            item = self.form_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()

        title_text = "Welcome Back"            if self._mode == "login" else "Create Account"
        sub_text   = "Sign in to your account" if self._mode == "login" else "Start your journey with NexaBank"

        title = QLabel(title_text)
        title.setFont(QFont("Segoe UI", 22, QFont.Bold))
        title.setStyleSheet(f"color:{TEXT}; background:transparent; border:none;")
        self.form_layout.addWidget(title)

        sub = QLabel(sub_text)
        sub.setFont(QFont("Segoe UI", 11))
        sub.setStyleSheet(f"color:{SUBTEXT}; background:transparent; border:none;")
        self.form_layout.addWidget(sub)
        self.form_layout.addSpacing(28)

        if self._mode == "register":
            self.name_input = self._inp("Full Name", False)
            self.form_layout.addWidget(self._wrap("Full Name", self.name_input))
            self.form_layout.addSpacing(14)
            self.phone_input = self._inp("Phone (optional)", False)
            self.form_layout.addWidget(self._wrap("Phone", self.phone_input))
            self.form_layout.addSpacing(14)

        self.email_input = self._inp("Enter your email", False)
        self.form_layout.addWidget(self._wrap("Email Address", self.email_input))
        self.form_layout.addSpacing(14)

        self.pw_input = self._inp("Enter your password", True)
        self.pw_input.returnPressed.connect(self._submit)
        self.form_layout.addWidget(self._wrap("Password", self.pw_input))
        self.form_layout.addSpacing(6)

        self.error_label = QLabel("")
        self.error_label.setStyleSheet(f"color:{ERROR}; font-size:12px; background:transparent; border:none;")
        self.error_label.setWordWrap(True)
        self.error_label.setVisible(False)
        self.form_layout.addWidget(self.error_label)
        self.form_layout.addSpacing(18)

        btn_text = "Sign In" if self._mode == "login" else "Create Account"
        self.submit_btn = GlowButton(btn_text)
        self.submit_btn.clicked.connect(self._submit)
        self.form_layout.addWidget(self.submit_btn)
        self.form_layout.addSpacing(16)

        sep = QFrame(); sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet(f"background:{BORDER}; border:none; max-height:1px;")
        self.form_layout.addWidget(sep)
        self.form_layout.addSpacing(14)

        toggle_text = "Don't have an account?  Register →" if self._mode == "login" else "Already have an account?  Sign In →"
        toggle = QPushButton(toggle_text)
        toggle.setStyleSheet(f"""
            QPushButton {{ background:transparent; color:{ACCENT}; border:none;
                font-size:12px; font-family:'Segoe UI'; padding:4px 0; }}
            QPushButton:hover {{ color:#93c5fd; }}
        """)
        toggle.setCursor(Qt.PointingHandCursor)
        toggle.clicked.connect(self._toggle_mode)
        self.form_layout.addWidget(toggle, 0, Qt.AlignCenter)

    def _inp(self, placeholder, is_password):
        inp = QLineEdit()
        inp.setPlaceholderText(placeholder)
        inp.setFixedHeight(46)
        inp.setStyleSheet(_input_style())
        if is_password: inp.setEchoMode(QLineEdit.Password)
        return inp

    def _wrap(self, label_text, widget):
        w = QWidget(); w.setStyleSheet("background:transparent;")
        wl = QVBoxLayout(w); wl.setContentsMargins(0,0,0,0); wl.setSpacing(6)
        lbl = QLabel(label_text)
        lbl.setFont(QFont("Segoe UI", 10, QFont.Bold))
        lbl.setStyleSheet(f"color:{SUBTEXT}; background:transparent; letter-spacing:0.5px;")
        wl.addWidget(lbl); wl.addWidget(widget)
        return w

    def _toggle_mode(self):
        self._mode = "register" if self._mode == "login" else "login"
        self._build_form()

    def _show_error(self, msg):
        self.error_label.setText(f"⚠  {msg}")
        self.error_label.setVisible(True)

    def _submit(self):
        self.error_label.setVisible(False)
        email    = self.email_input.text().strip()
        password = self.pw_input.text()

        from app.db.session import get_db
        from app.services.auth_service import login_user, register_user

        if self._mode == "login":
            with get_db() as db:
                ok, msg, user = login_user(db, email, password)
            if ok: self.login_success.emit(user)
            else:  self._show_error(msg)
        else:
            full_name = self.name_input.text().strip()
            phone     = self.phone_input.text().strip()
            with get_db() as db:
                ok, msg, user = register_user(db, email, password, full_name, phone)
            if ok:
                with get_db() as db:
                    ok2, msg2, user2 = login_user(db, email, password)
                if ok2: self.login_success.emit(user2)
                else:
                    self._show_error("Registered! Please sign in.")
                    self._mode = "login"; self._build_form()
            else:
                self._show_error(msg)