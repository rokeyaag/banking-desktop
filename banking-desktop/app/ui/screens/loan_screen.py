# -*- coding: utf-8 -*-
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QPushButton, QLineEdit, QComboBox, QGridLayout)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

BG="#0b0f1a"; PANEL="#111827"; ACCENT="#3b82f6"; GREEN="#22c55e"
TEXT="#e2e8f0"; MUTED="#64748b"; RED="#ef4444"; BORDER="#1e293b"

def _lbl(text, color=TEXT, size=13, bold=False):
    l = QLabel(text)
    l.setFont(QFont("Segoe UI", size, QFont.Bold if bold else QFont.Normal))
    l.setStyleSheet(f"color:{color}; background:transparent;")
    return l

def _inp():
    return f"QLineEdit {{ background:#1e293b; border:1px solid #334155; border-radius:8px; color:{TEXT}; padding:10px 14px; font-size:14px; }} QLineEdit:focus {{ border-color:{ACCENT}; }}"

class LoanScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background-color:{BG};")
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(20)
        layout.addWidget(_lbl("Loan Calculator", TEXT, 22, True))

        card = QFrame()
        card.setStyleSheet(f"QFrame {{ background:{PANEL}; border-radius:16px; border:1px solid {BORDER}; }}")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(32, 28, 32, 28)
        cl.setSpacing(14)

        cl.addWidget(_lbl("Loan Amount ($):"))
        self.amount_inp = QLineEdit()
        self.amount_inp.setPlaceholderText("e.g. 50000")
        self.amount_inp.setText("50000")
        self.amount_inp.setStyleSheet(_inp())
        self.amount_inp.setFixedHeight(46)
        cl.addWidget(self.amount_inp)

        cl.addWidget(_lbl("Annual Interest Rate (%):"))
        self.rate_inp = QLineEdit()
        self.rate_inp.setPlaceholderText("e.g. 8.5")
        self.rate_inp.setText("8.5")
        self.rate_inp.setStyleSheet(_inp())
        self.rate_inp.setFixedHeight(46)
        cl.addWidget(self.rate_inp)

        cl.addWidget(_lbl("Loan Term:"))
        self.term_combo = QComboBox()
        self.term_combo.addItems(["6 months", "12 months", "24 months", "36 months", "48 months", "60 months"])
        self.term_combo.setCurrentIndex(2)
        self.term_combo.setStyleSheet("""
            QComboBox { background:#1e293b; border:1px solid #334155; border-radius:8px; color:#e2e8f0; padding:10px 14px; font-size:13px; }
            QComboBox QAbstractItemView { background:#0d1117; color:#e2e8f0; selection-background-color:#3b82f6; border:1px solid #334155; }
            QComboBox QAbstractItemView::item { padding:8px 14px; min-height:30px; }
            QComboBox QAbstractItemView::item:hover { background:#1e293b; }
        """)
        self.term_combo.setFixedHeight(46)
        cl.addWidget(self.term_combo)

        calc_btn = QPushButton("Calculate EMI")
        calc_btn.setFixedHeight(48)
        calc_btn.setStyleSheet(f"QPushButton {{ background:{ACCENT}; color:white; border:none; border-radius:8px; font-size:15px; font-weight:600; }} QPushButton:hover {{ background:#2563eb; }}")
        calc_btn.clicked.connect(self._calculate)
        cl.addWidget(calc_btn)

        self.result_frame = QFrame()
        self.result_frame.setStyleSheet(f"QFrame {{ background:#0b0f1a; border-radius:12px; border:1px solid {BORDER}; }}")
        self.result_frame.setVisible(False)
        rl = QGridLayout(self.result_frame)
        rl.setContentsMargins(20, 16, 20, 16)
        rl.setSpacing(16)

        self.emi_val      = _lbl("$0", ACCENT, 22, True)
        self.total_val    = _lbl("$0", TEXT,   18, True)
        self.interest_val = _lbl("$0", RED,    18, True)
        self.rate_val     = _lbl("0%", GREEN,  18, True)

        for col, (val_lbl, label_text) in enumerate([
            (self.emi_val,      "Monthly EMI"),
            (self.total_val,    "Total Payment"),
            (self.interest_val, "Total Interest"),
            (self.rate_val,     "Interest Rate"),
        ]):
            val_lbl.setAlignment(Qt.AlignCenter)
            lbl = _lbl(label_text, MUTED, 10)
            lbl.setAlignment(Qt.AlignCenter)
            rl.addWidget(val_lbl, 0, col)
            rl.addWidget(lbl,     1, col)

        cl.addWidget(self.result_frame)

        self.err_lbl = QLabel("")
        self.err_lbl.setStyleSheet(f"color:{RED}; background:transparent; font-size:13px;")
        self.err_lbl.setVisible(False)
        cl.addWidget(self.err_lbl)

        layout.addWidget(card)
        layout.addStretch()

    def _calculate(self):
        self.err_lbl.setVisible(False)
        try:
            p        = float(self.amount_inp.text().strip())
            r_annual = float(self.rate_inp.text().strip())
            n        = int(self.term_combo.currentText().split()[0])

            if p <= 0 or r_annual < 0 or n <= 0:
                raise ValueError("Invalid input")

            r = r_annual / 100 / 12
            if r == 0:
                emi = p / n
            else:
                emi = p * r * (1 + r)**n / ((1 + r)**n - 1)

            total    = emi * n
            interest = total - p

            self.emi_val.setText(f"${emi:,.2f}")
            self.total_val.setText(f"${total:,.2f}")
            self.interest_val.setText(f"${interest:,.2f}")
            self.rate_val.setText(f"{r_annual}%")
            self.result_frame.setVisible(True)

        except Exception:
            self.err_lbl.setText("Please enter valid numbers.")
            self.err_lbl.setVisible(True)
            self.result_frame.setVisible(False)