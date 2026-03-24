from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QLineEdit, QComboBox, QMessageBox, QDialog, QDialogButtonBox)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

BG="#0b0f1a"; PANEL="#111827"; ACCENT="#3b82f6"; TEXT="#e2e8f0"; MUTED="#64748b"; RED="#ef4444"

def _inp():
    return "QLineEdit { background:#1e293b; border:1px solid #334155; border-radius:8px; color:#e2e8f0; padding:10px 14px; font-size:14px; } QLineEdit:focus { border-color:#3b82f6; }"

def _msgbox(parent, title, text):
    msg_box = QMessageBox(parent)
    msg_box.setWindowTitle(title)
    msg_box.setText(text)
    msg_box.setStyleSheet("QMessageBox { background:#111827; } QLabel { color:#e2e8f0; font-size:14px; } QPushButton { background:#3b82f6; color:white; border:none; border-radius:6px; padding:6px 20px; }")
    msg_box.exec()

class DepositScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background-color:{BG};")
        self._accounts = []
        self._build()

    def _build(self):
        layout = QVBoxLayout(self); layout.setContentsMargins(32,28,32,28); layout.setSpacing(20)
        title = QLabel("Deposit / Withdraw"); title.setFont(QFont("Segoe UI",22,QFont.Bold))
        title.setStyleSheet(f"color:{TEXT}; background:transparent;"); layout.addWidget(title)

        card = QFrame()
        card.setStyleSheet(f"QFrame {{ background:{PANEL}; border-radius:16px; border:1px solid #1e293b; }}")
        cl = QVBoxLayout(card); cl.setContentsMargins(32,28,32,28); cl.setSpacing(16)

        def lbl(t): l=QLabel(t); l.setStyleSheet(f"color:{TEXT}; background:transparent;"); return l

        cl.addWidget(lbl("Account:"))
        self.acct_combo = QComboBox()
        self.acct_combo.setStyleSheet("""
            QComboBox { background:#1e293b; border:1px solid #334155; border-radius:8px; color:#e2e8f0; padding:10px 14px; font-size:14px; }
            QComboBox QAbstractItemView { background:#0d1117; color:#e2e8f0; selection-background-color:#3b82f6; selection-color:white; border:1px solid #334155; outline:none; padding:4px; }
            QComboBox QAbstractItemView::item { padding:8px 14px; min-height:32px; color:#e2e8f0; }
            QComboBox QAbstractItemView::item:hover { background:#1e293b; }
        """)
        self.acct_combo.setFixedHeight(46); cl.addWidget(self.acct_combo)

        cl.addWidget(lbl("Type:"))
        self.type_combo = QComboBox(); self.type_combo.addItems(["Deposit","Withdraw"])
        self.type_combo.setStyleSheet("""
            QComboBox { background:#1e293b; border:1px solid #334155; border-radius:8px; color:#e2e8f0; padding:10px 14px; font-size:14px; }
            QComboBox QAbstractItemView { background:#0d1117; color:#e2e8f0; selection-background-color:#3b82f6; selection-color:white; border:1px solid #334155; outline:none; padding:4px; }
            QComboBox QAbstractItemView::item { padding:8px 14px; min-height:32px; color:#e2e8f0; }
            QComboBox QAbstractItemView::item:hover { background:#1e293b; }
        """)
        self.type_combo.setFixedHeight(46); cl.addWidget(self.type_combo)

        cl.addWidget(lbl("Amount:"))
        self.amount_inp = QLineEdit(); self.amount_inp.setPlaceholderText("0.00")
        self.amount_inp.setStyleSheet(_inp()); self.amount_inp.setFixedHeight(46)
        cl.addWidget(self.amount_inp)

        cl.addWidget(lbl("Description (optional):"))
        self.desc_inp = QLineEdit(); self.desc_inp.setPlaceholderText("Note...")
        self.desc_inp.setStyleSheet(_inp()); self.desc_inp.setFixedHeight(46)
        cl.addWidget(self.desc_inp)

        cl.addWidget(lbl("PIN:"))
        pin_row = QHBoxLayout()
        self.pin_inp = QLineEdit(); self.pin_inp.setEchoMode(QLineEdit.Password)
        self.pin_inp.setPlaceholderText("Enter PIN"); self.pin_inp.setStyleSheet(_inp()); self.pin_inp.setFixedHeight(46)
        set_pin_btn = QPushButton("Set/Change PIN")
        set_pin_btn.setStyleSheet(f"QPushButton {{ background:transparent; color:{ACCENT}; border:1px solid {ACCENT}; border-radius:8px; padding:10px 16px; font-size:12px; }} QPushButton:hover {{ background:{ACCENT}22; }}")
        set_pin_btn.clicked.connect(self._set_pin_dialog)
        pin_row.addWidget(self.pin_inp, 1); pin_row.addWidget(set_pin_btn); cl.addLayout(pin_row)

        self.err_lbl = QLabel("")
        self.err_lbl.setStyleSheet(f"color:{RED}; background:transparent; font-size:13px;")
        self.err_lbl.setVisible(False)
        cl.addWidget(self.err_lbl)

        submit = QPushButton("Submit"); submit.setFixedHeight(48)
        submit.setStyleSheet(f"QPushButton {{ background:{ACCENT}; color:white; border:none; border-radius:8px; font-size:15px; font-weight:600; }} QPushButton:hover {{ background:#2563eb; }}")
        submit.clicked.connect(self._submit); cl.addWidget(submit)

        layout.addWidget(card); layout.addStretch()

    def refresh(self):
        from app.services.auth_service import get_current_user
        from app.services.account_service import list_accounts
        from app.db.session import get_db
        user = get_current_user()
        if not user: return
        with get_db() as db:
            self._accounts = list_accounts(db, user.id)
        self.acct_combo.clear()
        for a in self._accounts:
            holder = a.get("holder_name") or user.full_name
            self.acct_combo.addItem(
                f"{a['account_number']} | {holder} | {a['account_type'].value.title()} | ${a['balance']:,.2f}"
            )

    def _submit(self):
        self.err_lbl.setVisible(False)
        from app.services.auth_service import get_current_user
        from app.services.deposit_service import deposit, withdraw
        from app.db.session import get_db
        user = get_current_user()
        if not user or not self._accounts:
            self.err_lbl.setText("No accounts available."); self.err_lbl.setVisible(True); return
        idx = self.acct_combo.currentIndex()
        if idx < 0 or idx >= len(self._accounts):
            self.err_lbl.setText("Select an account."); self.err_lbl.setVisible(True); return
        acct = self._accounts[idx]
        amount = self.amount_inp.text().strip()
        pin = self.pin_inp.text().strip()
        desc = self.desc_inp.text().strip()
        if not amount:
            self.err_lbl.setText("Enter an amount."); self.err_lbl.setVisible(True); return
        if not pin:
            self.err_lbl.setText("Enter your PIN."); self.err_lbl.setVisible(True); return
        try:
            with get_db() as db:
                if self.type_combo.currentText() == "Deposit":
                    ok, msg, _ = deposit(db, user.id, acct["id"], amount, pin, desc or "Deposit")
                else:
                    ok, msg, _ = withdraw(db, user.id, acct["id"], amount, pin, desc or "Withdrawal")
            if ok:
                _msgbox(self, "Success", f"✅ {msg}")
                self.pin_inp.clear(); self.amount_inp.clear(); self.refresh()
            else:
                self.err_lbl.setText(msg); self.err_lbl.setVisible(True)
        except Exception as e:
            self.err_lbl.setText(str(e)); self.err_lbl.setVisible(True)

    def _set_pin_dialog(self):
        from app.services.auth_service import get_current_user
        from app.services.pin_service import set_pin
        from app.db.session import get_db
        dialog = QDialog(self); dialog.setWindowTitle("Set PIN"); dialog.setFixedSize(320,160)
        dialog.setStyleSheet(f"QDialog {{ background:{PANEL}; }} QLabel {{ color:{TEXT}; background:transparent; }}")
        dl = QVBoxLayout(dialog); dl.setSpacing(12); dl.setContentsMargins(24,24,24,24)
        dl.addWidget(QLabel("New PIN (4–6 digits):"))
        pin_in = QLineEdit(); pin_in.setEchoMode(QLineEdit.Password)
        pin_in.setPlaceholderText("e.g. 1234"); pin_in.setStyleSheet(_inp()); pin_in.setFixedHeight(42)
        dl.addWidget(pin_in)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.setStyleSheet(f"QPushButton {{ background:{ACCENT}; color:white; border:none; border-radius:6px; padding:6px 20px; }}")
        btns.accepted.connect(dialog.accept); btns.rejected.connect(dialog.reject); dl.addWidget(btns)
        if dialog.exec():
            user = get_current_user()
            with get_db() as db:
                ok, msg = set_pin(db, user.id, pin_in.text().strip())
            if ok:
                _msgbox(self, "PIN Set", "✅ PIN set successfully.")
            else:
                QMessageBox.warning(self, "Error", msg)