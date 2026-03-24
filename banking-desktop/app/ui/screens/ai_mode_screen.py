from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QScrollArea)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

BG="#0b0f1a"; PANEL="#111827"; ACCENT="#3b82f6"; TEXT="#e2e8f0"; MUTED="#64748b"

class AIModeScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background-color:{BG};")
        self._flow_id = None
        self._build()

    def _build(self):
        layout = QVBoxLayout(self); layout.setContentsMargins(32,28,32,28); layout.setSpacing(20)
        title = QLabel("AI Mode"); title.setFont(QFont("Segoe UI",22,QFont.Bold))
        title.setStyleSheet(f"color:{TEXT}; background:transparent;"); layout.addWidget(title)
        sub = QLabel("Choose a guided workflow:"); sub.setStyleSheet(f"color:{MUTED}; background:transparent;"); layout.addWidget(sub)

        flow_row = QHBoxLayout(); flow_row.setSpacing(12)
        for ft, label, icon in [("open_account","Open Account","🏦"),("deposit","Make Deposit","💰"),("check_balance","Check Balance","📊")]:
            btn = QPushButton(f"{icon}\n{label}"); btn.setFixedSize(160,90)
            btn.setStyleSheet(f"QPushButton {{ background:{PANEL}; color:{TEXT}; border:1px solid #1e293b; border-radius:12px; font-size:13px; font-weight:600; }} QPushButton:hover {{ border-color:{ACCENT}; color:{ACCENT}; }}")
            btn.clicked.connect(lambda _, f=ft: self._start_flow(f))
            flow_row.addWidget(btn)
        flow_row.addStretch(); layout.addLayout(flow_row)

        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border:none; background:transparent; }")
        self.msg_w = QWidget(); self.msg_w.setStyleSheet("background:transparent;")
        self.msg_layout = QVBoxLayout(self.msg_w); self.msg_layout.setSpacing(8); self.msg_layout.setContentsMargins(0,0,0,0)
        self.msg_layout.addStretch(); scroll.setWidget(self.msg_w); layout.addWidget(scroll, 1)

        inp_row = QHBoxLayout()
        self.inp = QLineEdit(); self.inp.setPlaceholderText("Type your response...")
        self.inp.setStyleSheet("QLineEdit { background:#1e293b; border:1px solid #334155; border-radius:8px; color:#e2e8f0; padding:10px 14px; font-size:14px; } QLineEdit:focus { border-color:#3b82f6; }")
        self.inp.setFixedHeight(46); self.inp.returnPressed.connect(self._send)
        send = QPushButton("Send"); send.setFixedSize(80,46)
        send.setStyleSheet(f"QPushButton {{ background:{ACCENT}; color:white; border:none; border-radius:8px; font-size:14px; font-weight:600; }} QPushButton:hover {{ background:#2563eb; }}")
        send.clicked.connect(self._send)
        inp_row.addWidget(self.inp,1); inp_row.addWidget(send); layout.addLayout(inp_row)

    def refresh(self): pass

    def _add_msg(self, text: str, is_user: bool):
        b = QLabel(text); b.setWordWrap(True)
        if is_user:
            b.setStyleSheet(f"background:{ACCENT}22; color:{TEXT}; padding:10px 14px; border-radius:10px; font-size:13px;")
            b.setAlignment(Qt.AlignRight)
        else:
            b.setStyleSheet(f"background:{PANEL}; color:{TEXT}; padding:10px 14px; border-radius:10px; border:1px solid #1e293b; font-size:13px;")
        self.msg_layout.insertWidget(self.msg_layout.count()-1, b)

    def _start_flow(self, flow_type: str):
        from app.services.auth_service import get_current_user
        from app.services.ai_flow_service import start_flow
        from app.db.session import get_db
        user = get_current_user()
        if not user: return
        with get_db() as db:
            ok, msg, flow_id = start_flow(db, user.id, flow_type)
        if ok:
            self._flow_id = flow_id  # flow_id is already a plain UUID
            self._add_msg(msg, False)
        else:
            self._add_msg(f"Error: {msg}", False)

    def _send(self):
        text = self.inp.text().strip()
        if not text or not self._flow_id: return
        self.inp.clear(); self._add_msg(text, True)
        from app.services.auth_service import get_current_user
        from app.services.ai_flow_service import process_flow_input
        from app.db.session import get_db
        user = get_current_user()
        if not user: return
        with get_db() as db:
            ok, response, done = process_flow_input(db, self._flow_id, user.id, text)
        self._add_msg(response, False)
        if done: self._flow_id = None
