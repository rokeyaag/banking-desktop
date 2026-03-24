# -*- coding: utf-8 -*-
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QPushButton, QLineEdit, QComboBox, QMessageBox)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

BG="#0b0f1a"; PANEL="#111827"; ACCENT="#3b82f6"; GREEN="#22c55e"
TEXT="#e2e8f0"; MUTED="#64748b"; RED="#ef4444"; BORDER="#1e293b"

def _inp():
    return f"QLineEdit {{ background:#1e293b; border:1px solid #334155; border-radius:8px; color:{TEXT}; padding:10px 14px; font-size:14px; }} QLineEdit:focus {{ border-color:{ACCENT}; }}"

def _combo_style():
    return """
        QComboBox { background:#1e293b; border:1px solid #334155; border-radius:8px; color:#e2e8f0; padding:10px 14px; font-size:13px; }
        QComboBox QAbstractItemView { background:#0d1117; color:#e2e8f0; selection-background-color:#3b82f6; border:1px solid #334155; }
        QComboBox QAbstractItemView::item { padding:10px 14px; min-height:34px; }
        QComboBox QAbstractItemView::item:hover { background:#1e293b; }
    """

def _msgbox(parent, title, text):
    msg = QMessageBox(parent)
    msg.setWindowTitle(title)
    msg.setText(text)
    msg.setStyleSheet("""
        QMessageBox { background-color: #111827; }
        QLabel { color: #e2e8f0; font-size: 14px; background: transparent; }
        QPushButton { background: #3b82f6; color: white; border: none; border-radius: 6px; padding: 6px 24px; font-size: 13px; }
        QPushButton:hover { background: #2563eb; }
    """)
    msg.exec()

def _lbl(text, color=TEXT, size=13, bold=False):
    l = QLabel(text)
    l.setFont(QFont("Segoe UI", size, QFont.Bold if bold else QFont.Normal))
    l.setStyleSheet(f"color:{color}; background:transparent;")
    return l

def _acct_label(a):
    """Build dropdown display text with holder name if available"""
    acct_type = a["account_type"]
    if hasattr(acct_type, "value"):
        acct_type = acct_type.value
    name = a.get("holder_name") or a.get("name") or ""
    base = f"{a['account_number']} ({acct_type.title()}) -- ${a['balance']:,.2f}"
    if name:
        base += f"  |  {name}"
    return base

class TransferScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background-color:{BG};")
        self._accounts = []
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(20)
        layout.addWidget(_lbl("Transfer Money", TEXT, 22, True))

        card = QFrame()
        card.setStyleSheet(f"QFrame {{ background:{PANEL}; border-radius:16px; border:1px solid {BORDER}; }}")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(32, 28, 32, 28)
        cl.setSpacing(14)

        cl.addWidget(_lbl("From Account:"))
        self.from_combo = QComboBox()
        self.from_combo.setStyleSheet(_combo_style())
        self.from_combo.setFixedHeight(46)
        cl.addWidget(self.from_combo)

        arrow = _lbl("-- Transfer To -->", ACCENT, 13, True)
        arrow.setAlignment(Qt.AlignCenter)
        cl.addWidget(arrow)

        cl.addWidget(_lbl("To Account:"))
        self.to_combo = QComboBox()
        self.to_combo.setStyleSheet(_combo_style())
        self.to_combo.setFixedHeight(46)
        cl.addWidget(self.to_combo)

        cl.addWidget(_lbl("Amount:"))
        self.amount_inp = QLineEdit()
        self.amount_inp.setPlaceholderText("0.00")
        self.amount_inp.setStyleSheet(_inp())
        self.amount_inp.setFixedHeight(46)
        cl.addWidget(self.amount_inp)

        cl.addWidget(_lbl("Description (optional):"))
        self.desc_inp = QLineEdit()
        self.desc_inp.setPlaceholderText("e.g. Rent payment")
        self.desc_inp.setStyleSheet(_inp())
        self.desc_inp.setFixedHeight(46)
        cl.addWidget(self.desc_inp)

        cl.addWidget(_lbl("PIN:"))
        self.pin_inp = QLineEdit()
        self.pin_inp.setEchoMode(QLineEdit.Password)
        self.pin_inp.setPlaceholderText("Enter PIN")
        self.pin_inp.setStyleSheet(_inp())
        self.pin_inp.setFixedHeight(46)
        cl.addWidget(self.pin_inp)

        self.err_lbl = QLabel("")
        self.err_lbl.setStyleSheet(f"color:{RED}; background:transparent; font-size:13px;")
        self.err_lbl.setVisible(False)
        cl.addWidget(self.err_lbl)

        submit = QPushButton("Transfer Now")
        submit.setFixedHeight(48)
        submit.setStyleSheet(f"QPushButton {{ background:{ACCENT}; color:white; border:none; border-radius:8px; font-size:15px; font-weight:600; }} QPushButton:hover {{ background:#2563eb; }}")
        submit.clicked.connect(self._submit)
        cl.addWidget(submit)

        layout.addWidget(card)
        layout.addStretch()

    def refresh(self):
        from app.services.auth_service import get_current_user
        from app.services.account_service import list_accounts
        from app.db.session import get_db
        user = get_current_user()
        if not user: return
        with get_db() as db:
            raw = list_accounts(db, user.id)
        self._accounts = []
        for a in raw:
            acct_type = a["account_type"]
            if hasattr(acct_type, "value"):
                acct_type = acct_type.value
            self._accounts.append({
                "id":             a["id"],
                "account_number": a["account_number"],
                "account_type":   acct_type,
                "balance":        a["balance"],
                "holder_name":    a.get("holder_name") or a.get("name") or "",
            })
        self.from_combo.clear()
        self.to_combo.clear()
        for a in self._accounts:
            text = _acct_label(a)
            self.from_combo.addItem(text)
            self.to_combo.addItem(text)
        if len(self._accounts) > 1:
            self.to_combo.setCurrentIndex(1)

    def _submit(self):
        self.err_lbl.setVisible(False)
        from app.services.auth_service import get_current_user
        from app.services.deposit_service import withdraw, deposit
        from app.db.session import get_db

        user = get_current_user()
        if not user or len(self._accounts) < 2:
            self.err_lbl.setText("Need at least 2 accounts to transfer.")
            self.err_lbl.setVisible(True); return

        fi = self.from_combo.currentIndex()
        ti = self.to_combo.currentIndex()
        if fi == ti:
            self.err_lbl.setText("From and To account must be different.")
            self.err_lbl.setVisible(True); return

        amount = self.amount_inp.text().strip()
        pin    = self.pin_inp.text().strip()
        desc   = self.desc_inp.text().strip() or "Transfer"

        if not amount:
            self.err_lbl.setText("Enter an amount."); self.err_lbl.setVisible(True); return
        if not pin:
            self.err_lbl.setText("Enter your PIN."); self.err_lbl.setVisible(True); return

        try:
            from_acct = self._accounts[fi]
            to_acct   = self._accounts[ti]
            with get_db() as db:
                ok, msg, _ = withdraw(db, user.id, from_acct["id"], amount, pin,
                                      f"Transfer to {to_acct['account_number']}")
            if not ok:
                self.err_lbl.setText(msg); self.err_lbl.setVisible(True); return
            with get_db() as db:
                ok2, msg2, _ = deposit(db, user.id, to_acct["id"], amount, pin,
                                       f"Transfer from {from_acct['account_number']}")
            if ok2:
                _msgbox(self, "Success", f"Transferred ${amount} successfully!")
                self.amount_inp.clear(); self.pin_inp.clear(); self.desc_inp.clear()
                self.refresh()
            else:
                self.err_lbl.setText(msg2); self.err_lbl.setVisible(True)
        except Exception as e:
            self.err_lbl.setText(str(e)); self.err_lbl.setVisible(True)