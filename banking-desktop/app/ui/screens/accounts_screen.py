# -*- coding: utf-8 -*-
import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QComboBox, QScrollArea, QDialog, QLineEdit, QFileDialog, QTextEdit)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QPixmap

BG="#0b0f1a"; PANEL="#111827"; ACCENT="#3b82f6"; GREEN="#22c55e"; TEXT="#e2e8f0"; MUTED="#64748b"


def _get_acct_type_str(val):
    """Safely get account type as string regardless of enum or str"""
    if hasattr(val, "value"):
        return val.value.title()
    return str(val).title()


class AccountsScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background-color:{BG};")
        self._photo_path = ""
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(20)

        hdr = QHBoxLayout()
        title = QLabel("Accounts")
        title.setFont(QFont("Segoe UI", 22, QFont.Bold))
        title.setStyleSheet(f"color:{TEXT}; background:transparent;")
        hdr.addWidget(title)
        hdr.addStretch()
        btn = QPushButton("+ Open New Account")
        btn.setFixedHeight(38)
        btn.setStyleSheet(f"QPushButton {{ background:{ACCENT}; color:white; border:none; border-radius:8px; padding:0 20px; font-size:13px; font-weight:600; }} QPushButton:hover {{ background:#2563eb; }}")
        btn.clicked.connect(self._open_dialog)
        hdr.addWidget(btn)
        layout.addLayout(hdr)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border:none; background:transparent; }")
        self.container = QWidget()
        self.container.setStyleSheet("background:transparent;")
        self.vbox = QVBoxLayout(self.container)
        self.vbox.setSpacing(12)
        self.vbox.setContentsMargins(0, 0, 0, 0)
        scroll.setWidget(self.container)
        layout.addWidget(scroll, 1)

    def refresh(self):
        while self.vbox.count():
            item = self.vbox.takeAt(0)
            if item.widget(): item.widget().deleteLater()

        from app.services.auth_service import get_current_user
        from app.services.account_service import list_accounts
        from app.db.session import get_db

        user = get_current_user()
        if not user: return

        with get_db() as db:
            accounts = list_accounts(db, user.id)

        if not accounts:
            lbl = QLabel("No accounts yet. Open your first account!")
            lbl.setStyleSheet(f"color:{MUTED}; padding:30px; background:transparent;")
            lbl.setAlignment(Qt.AlignCenter)
            self.vbox.addWidget(lbl)
        else:
            for a in accounts:
                acct_type_str = _get_acct_type_str(a.get("account_type", ""))

                card = QFrame()
                card.setStyleSheet(f"QFrame {{ background:{PANEL}; border:1px solid #1e293b; border-radius:12px; }}")
                cl = QVBoxLayout(card)
                cl.setContentsMargins(24, 20, 24, 20)
                cl.setSpacing(6)

                # Top row: type + balance
                top = QHBoxLayout()
                tl = QLabel(f"  {acct_type_str}")
                tl.setFont(QFont("Segoe UI", 14, QFont.Bold))
                tl.setStyleSheet(f"color:{ACCENT}; background:transparent; border:none;")
                top.addWidget(tl)
                top.addStretch()
                bl = QLabel(f"${a['balance']:,.2f}")
                bl.setFont(QFont("Segoe UI", 18, QFont.Bold))
                bl.setStyleSheet(f"color:{GREEN}; background:transparent; border:none;")
                top.addWidget(bl)
                cl.addLayout(top)

                # Holder name row
                holder_name = a.get("holder_name") or a.get("name") or ""
                if holder_name:
                    hl = QLabel(f"  {holder_name}")
                    hl.setFont(QFont("Segoe UI", 12, QFont.Bold))
                    hl.setStyleSheet(f"color:{TEXT}; background:transparent; border:none;")
                    cl.addWidget(hl)

                # Account number + currency
                nl = QLabel(f"Account: {a['account_number']}  ·  {a.get('currency', 'BDT')}")
                nl.setStyleSheet(f"color:{MUTED}; font-size:12px; background:transparent; border:none;")
                cl.addWidget(nl)

                # Opened date
                if a.get("created_at"):
                    dl = QLabel(f"Opened: {a['created_at'].strftime('%B %d, %Y')}")
                    dl.setStyleSheet(f"color:{MUTED}; font-size:11px; background:transparent; border:none;")
                    cl.addWidget(dl)

                self.vbox.addWidget(card)
        self.vbox.addStretch()

    def _inp_style(self):
        return "QLineEdit { background:#1e293b; border:1px solid #334155; border-radius:8px; color:#e2e8f0; padding:8px 12px; font-size:13px; } QLineEdit:focus { border-color:#3b82f6; }"

    def _lbl(self, text):
        l = QLabel(text)
        l.setStyleSheet(f"color:{MUTED}; font-size:12px; background:transparent;")
        return l

    def _open_dialog(self):
        from app.db.models import AccountType
        from app.services.auth_service import get_current_user
        from app.services.account_service import open_account
        from app.db.session import get_db

        self._photo_path = ""

        dialog = QDialog(self)
        dialog.setWindowTitle("Open New Account")
        dialog.setFixedSize(500, 620)
        dialog.setStyleSheet(f"""
            QDialog {{ background:{PANEL}; }}
            QLabel {{ color:{TEXT}; background:transparent; }}
            QLineEdit {{ background:#1e293b; border:1px solid #334155; border-radius:8px; color:#e2e8f0; padding:8px 12px; font-size:13px; }}
            QLineEdit:focus {{ border-color:#3b82f6; }}
            QTextEdit {{ background:#1e293b; border:1px solid #334155; border-radius:8px; color:#e2e8f0; padding:8px 12px; font-size:13px; }}
            QComboBox {{ background:#1e293b; border:1px solid #334155; border-radius:8px; color:#e2e8f0; padding:8px 12px; font-size:13px; }}
            QComboBox QAbstractItemView {{ background:#0d1117; color:#e2e8f0; selection-background-color:#3b82f6; selection-color:white; border:1px solid #334155; outline:none; }}
            QComboBox QAbstractItemView::item {{ padding:8px 12px; min-height:30px; color:#e2e8f0; }}
            QComboBox QAbstractItemView::item:hover {{ background:#1e293b; }}
        """)

        root = QVBoxLayout(dialog)
        root.setContentsMargins(28, 24, 28, 20)
        root.setSpacing(12)

        hdr = QLabel("Open New Account")
        hdr.setFont(QFont("Segoe UI", 15, QFont.Bold))
        hdr.setStyleSheet(f"color:{TEXT}; background:transparent;")
        root.addWidget(hdr)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border:none; background:transparent; }")
        form_w = QWidget()
        form_w.setStyleSheet("background:transparent;")
        form = QVBoxLayout(form_w)
        form.setSpacing(10)
        form.setContentsMargins(0, 4, 8, 4)

        form.addWidget(self._lbl("Account Type"))
        type_combo = QComboBox()
        type_combo.addItems(["Checking", "Savings", "Business"])
        type_combo.setFixedHeight(42)
        form.addWidget(type_combo)

        form.addWidget(self._lbl("Account Holder Name  *"))
        name_inp = QLineEdit()
        name_inp.setPlaceholderText("Full legal name")
        name_inp.setFixedHeight(42)
        form.addWidget(name_inp)

        form.addWidget(self._lbl("Date of Birth"))
        dob_inp = QLineEdit()
        dob_inp.setPlaceholderText("DD/MM/YYYY")
        dob_inp.setFixedHeight(42)
        form.addWidget(dob_inp)

        form.addWidget(self._lbl("NID / Passport Number"))
        nid_inp = QLineEdit()
        nid_inp.setPlaceholderText("National ID or Passport")
        nid_inp.setFixedHeight(42)
        form.addWidget(nid_inp)

        form.addWidget(self._lbl("Phone Number"))
        phone_inp = QLineEdit()
        phone_inp.setPlaceholderText("+880...")
        phone_inp.setFixedHeight(42)
        form.addWidget(phone_inp)

        form.addWidget(self._lbl("Address"))
        addr_inp = QTextEdit()
        addr_inp.setPlaceholderText("Full address...")
        addr_inp.setFixedHeight(70)
        form.addWidget(addr_inp)

        form.addWidget(self._lbl("Occupation"))
        occ_inp = QLineEdit()
        occ_inp.setPlaceholderText("e.g. Engineer, Student, Business")
        occ_inp.setFixedHeight(42)
        form.addWidget(occ_inp)

        dep_row = QHBoxLayout()
        dep_row.setSpacing(10)
        dep_col = QVBoxLayout(); dep_col.setSpacing(4)
        dep_col.addWidget(self._lbl("Initial Deposit ($)"))
        deposit_inp = QLineEdit()
        deposit_inp.setPlaceholderText("0.00")
        deposit_inp.setFixedHeight(42)
        dep_col.addWidget(deposit_inp)
        cur_col = QVBoxLayout(); cur_col.setSpacing(4)
        cur_col.addWidget(self._lbl("Currency"))
        cur_combo = QComboBox()
        cur_combo.addItems(["USD", "BDT", "EUR", "GBP", "CAD", "AUD"])
        cur_combo.setFixedHeight(42)
        cur_col.addWidget(cur_combo)
        dep_row.addLayout(dep_col, 2)
        dep_row.addLayout(cur_col, 1)
        form.addLayout(dep_row)

        form.addWidget(self._lbl("Photo (optional)"))
        photo_row = QHBoxLayout(); photo_row.setSpacing(12)
        self._photo_preview = QLabel("No photo")
        self._photo_preview.setFixedSize(56, 56)
        self._photo_preview.setAlignment(Qt.AlignCenter)
        self._photo_preview.setStyleSheet("background:#1e293b; border:1px dashed #334155; border-radius:8px; color:#64748b; font-size:10px;")
        photo_btn = QPushButton("Choose Photo")
        photo_btn.setFixedHeight(42)
        photo_btn.setStyleSheet(f"QPushButton {{ background:transparent; color:{ACCENT}; border:1px solid {ACCENT}; border-radius:8px; padding:0 16px; font-size:13px; }} QPushButton:hover {{ background:{ACCENT}22; }}")

        def pick_photo():
            path, _ = QFileDialog.getOpenFileName(dialog, "Select Photo", "", "Images (*.png *.jpg *.jpeg)")
            if path:
                self._photo_path = path
                pix = QPixmap(path).scaled(56, 56, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self._photo_preview.setPixmap(pix)
                self._photo_preview.setStyleSheet("border-radius:8px; border:1px solid #334155; background:transparent;")

        photo_btn.clicked.connect(pick_photo)
        photo_row.addWidget(self._photo_preview)
        photo_row.addWidget(photo_btn)
        photo_row.addStretch()
        form.addLayout(photo_row)

        err_lbl = QLabel("")
        err_lbl.setStyleSheet("color:#ef4444; background:transparent; font-size:12px;")
        err_lbl.setVisible(False)
        form.addWidget(err_lbl)

        scroll.setWidget(form_w)
        root.addWidget(scroll, 1)

        btn_row = QHBoxLayout(); btn_row.setSpacing(10)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedHeight(44)
        cancel_btn.setStyleSheet("QPushButton { background:#1e293b; color:#e2e8f0; border:1px solid #334155; border-radius:8px; font-size:14px; } QPushButton:hover { background:#334155; }")
        cancel_btn.clicked.connect(dialog.reject)
        ok_btn = QPushButton("Open Account")
        ok_btn.setFixedHeight(44)
        ok_btn.setStyleSheet(f"QPushButton {{ background:{ACCENT}; color:white; border:none; border-radius:8px; font-size:14px; font-weight:600; }} QPushButton:hover {{ background:#2563eb; }}")

        def submit():
            holder = name_inp.text().strip()
            if not holder:
                err_lbl.setText("Account holder name is required.")
                err_lbl.setVisible(True); return
            try:
                initial = float(deposit_inp.text().strip()) if deposit_inp.text().strip() else 0.0
                if initial < 0: raise ValueError
            except ValueError:
                err_lbl.setText("Invalid deposit amount.")
                err_lbl.setVisible(True); return

            mapping = {
                "Checking": AccountType.CHECKING,
                "Savings":  AccountType.SAVINGS,
                "Business": AccountType.BUSINESS
            }
            user = get_current_user()
            with get_db() as db:
                ok, msg, account = open_account(
                    db, user.id, mapping[type_combo.currentText()],
                    initial_deposit=initial,
                    holder_name=name_inp.text().strip(),
                    dob=dob_inp.text().strip(),
                    nid=nid_inp.text().strip(),
                    phone=phone_inp.text().strip(),
                    address=addr_inp.toPlainText().strip(),
                    occupation=occ_inp.text().strip(),
                    currency=cur_combo.currentText(),
                    photo_path=self._photo_path,
                )

            if ok:
                dialog.accept()
                self._show_success(
                    f"Account opened successfully!\n\n"
                    f"Account Number:\n{account['account_number']}\n\n"
                    f"Holder: {holder}  -  {type_combo.currentText()}  -  {cur_combo.currentText()}"
                )
                self.refresh()
            else:
                err_lbl.setText(msg)
                err_lbl.setVisible(True)

        ok_btn.clicked.connect(submit)
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(ok_btn)
        root.addLayout(btn_row)
        dialog.exec()

    def _show_success(self, message: str):
        d = QDialog(self)
        d.setWindowTitle("Success")
        d.setFixedSize(400, 230)
        d.setStyleSheet("QDialog { background:#111827; }")
        layout = QVBoxLayout(d)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(16)
        il = QLabel("OK")
        il.setStyleSheet(f"font-size:28px; background:transparent; color:{GREEN};")
        il.setAlignment(Qt.AlignCenter)
        layout.addWidget(il)
        ml = QLabel(message)
        ml.setWordWrap(True)
        ml.setStyleSheet("color:#e2e8f0; font-size:13px; background:transparent;")
        ml.setAlignment(Qt.AlignCenter)
        layout.addWidget(ml)
        btn = QPushButton("OK")
        btn.setFixedHeight(40)
        btn.setStyleSheet("QPushButton { background:#3b82f6; color:white; border:none; border-radius:8px; font-size:14px; font-weight:600; } QPushButton:hover { background:#2563eb; }")
        btn.clicked.connect(d.accept)
        layout.addWidget(btn)
        d.exec()

    def _show_error_msg(self, message: str):
        d = QDialog(self)
        d.setWindowTitle("Error")
        d.setFixedSize(360, 180)
        d.setStyleSheet("QDialog { background:#111827; }")
        layout = QVBoxLayout(d)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(16)
        il = QLabel("Error")
        il.setStyleSheet("font-size:22px; background:transparent; color:#ef4444;")
        il.setAlignment(Qt.AlignCenter)
        layout.addWidget(il)
        ml = QLabel(message)
        ml.setWordWrap(True)
        ml.setStyleSheet("color:#ef4444; font-size:13px; background:transparent;")
        ml.setAlignment(Qt.AlignCenter)
        layout.addWidget(ml)
        btn = QPushButton("OK")
        btn.setFixedHeight(38)
        btn.setStyleSheet("QPushButton { background:#334155; color:white; border:none; border-radius:8px; font-size:13px; } QPushButton:hover { background:#475569; }")
        btn.clicked.connect(d.accept)
        layout.addWidget(btn)
        d.exec()