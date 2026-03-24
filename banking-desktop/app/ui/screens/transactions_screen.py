# -*- coding: utf-8 -*-
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QPushButton, QLineEdit, QComboBox, QScrollArea, QSizePolicy)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

BG="#0b0f1a"; PANEL="#111827"; ACCENT="#3b82f6"; GREEN="#22c55e"
TEXT="#e2e8f0"; MUTED="#64748b"; RED="#ef4444"; BORDER="#1e293b"

def _lbl(text, color=TEXT, size=13, bold=False):
    l = QLabel(text)
    l.setFont(QFont("Segoe UI", size, QFont.Bold if bold else QFont.Normal))
    l.setStyleSheet(f"color:{color}; background:transparent;")
    return l

def _combo_style():
    return """
        QComboBox { background:#1e293b; border:1px solid #334155; border-radius:8px; color:#e2e8f0; padding:8px 12px; font-size:12px; }
        QComboBox QAbstractItemView { background:#0d1117; color:#e2e8f0; selection-background-color:#3b82f6; border:1px solid #334155; }
        QComboBox QAbstractItemView::item { padding:6px 12px; min-height:28px; }
        QComboBox QAbstractItemView::item:hover { background:#1e293b; }
    """

class TransactionsScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background-color:{BG};")
        self._all_txs = []
        self._acct_list = []
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(16)
        layout.addWidget(_lbl("Transaction History", TEXT, 22, True))

        filter_card = QFrame()
        filter_card.setStyleSheet(f"QFrame {{ background:{PANEL}; border-radius:12px; border:1px solid {BORDER}; }}")
        fl = QHBoxLayout(filter_card)
        fl.setContentsMargins(20, 14, 20, 14)
        fl.setSpacing(10)

        self.type_combo = QComboBox()
        self.type_combo.addItems(["All Types", "Deposit", "Withdrawal"])
        self.type_combo.setStyleSheet(_combo_style())
        self.type_combo.setFixedHeight(38)
        self.type_combo.currentIndexChanged.connect(self._apply_filter)

        self.acct_combo = QComboBox()
        self.acct_combo.setStyleSheet(_combo_style())
        self.acct_combo.setFixedHeight(38)
        self.acct_combo.currentIndexChanged.connect(self._apply_filter)

        self.search_inp = QLineEdit()
        self.search_inp.setPlaceholderText("Search description...")
        self.search_inp.setFixedHeight(38)
        self.search_inp.setStyleSheet(f"QLineEdit {{ background:#1e293b; border:1px solid #334155; border-radius:8px; color:{TEXT}; padding:6px 12px; font-size:12px; }} QLineEdit:focus {{ border-color:{ACCENT}; }}")
        self.search_inp.textChanged.connect(self._apply_filter)

        fl.addWidget(_lbl("Filter:", MUTED, 11))
        fl.addWidget(self.acct_combo, 2)
        fl.addWidget(self.type_combo, 1)
        fl.addWidget(self.search_inp, 2)

        self.count_lbl = _lbl("0 transactions", MUTED, 11)
        fl.addWidget(self.count_lbl)
        layout.addWidget(filter_card)

        self.tx_scroll = QScrollArea()
        self.tx_scroll.setWidgetResizable(True)
        self.tx_scroll.setStyleSheet(f"""
            QScrollArea {{ border:none; background:transparent; }}
            QScrollBar:vertical {{ background:#0f172a; width:6px; border-radius:3px; }}
            QScrollBar::handle:vertical {{ background:#334155; border-radius:3px; min-height:20px; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height:0px; }}
        """)
        self.tx_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.tx_inner = QWidget()
        self.tx_inner.setStyleSheet("background:transparent;")
        self.tx_list = QVBoxLayout(self.tx_inner)
        self.tx_list.setSpacing(6)
        self.tx_list.setContentsMargins(0, 0, 6, 0)
        self.tx_list.addStretch()
        self.tx_scroll.setWidget(self.tx_inner)
        layout.addWidget(self.tx_scroll, 1)

    def refresh(self):
        from app.services.auth_service import get_current_user
        from app.services.account_service import list_accounts
        from app.services.deposit_service import get_transaction_history
        from app.db.session import get_db

        user = get_current_user()
        if not user: return

        with get_db() as db:
            accounts = list_accounts(db, user.id)

        self.acct_combo.blockSignals(True)
        self.acct_combo.clear()
        self.acct_combo.addItem("All Accounts")
        self._acct_list = accounts
        for a in accounts:
            self.acct_combo.addItem(f"{a['account_number']} ({a['account_type'].title()})")
        self.acct_combo.blockSignals(False)

        self._all_txs = []
        with get_db() as db:
            for a in accounts:
                txs = get_transaction_history(db, a["id"], user.id, limit=200)
                for tx in txs:
                    tx["account_number"] = a["account_number"]
                self._all_txs.extend(txs)
        self._all_txs.sort(key=lambda t: t["created_at"], reverse=True)
        self._apply_filter()

    def _apply_filter(self):
        q        = self.search_inp.text().strip().lower()
        tx_type  = self.type_combo.currentText()
        acct_idx = self.acct_combo.currentIndex()

        filtered = []
        for tx in self._all_txs:
            if tx_type == "Deposit"    and tx["transaction_type"].value != "DEPOSIT": continue
            if tx_type == "Withdrawal" and tx["transaction_type"].value == "DEPOSIT": continue
            if acct_idx > 0:
                acct = self._acct_list[acct_idx - 1]
                if tx.get("account_number") != acct["account_number"]: continue
            if q and q not in (tx.get("description") or "").lower(): continue
            filtered.append(tx)

        self.count_lbl.setText(f"{len(filtered)} transactions")
        self._render(filtered)

    def _render(self, txs):
        while self.tx_list.count() > 1:
            item = self.tx_list.takeAt(0)
            if item.widget(): item.widget().deleteLater()

        if not txs:
            self.tx_list.insertWidget(0, _lbl("No transactions found.", MUTED, 12))
            return

        for i, tx in enumerate(txs):
            is_dep = tx["transaction_type"].value == "DEPOSIT"
            sign   = "+" if is_dep else "-"
            color  = GREEN if is_dep else RED
            icon   = "IN" if is_dep else "OUT"

            row = QFrame()
            row.setStyleSheet(f"QFrame {{ background:{PANEL}; border-radius:10px; border:1px solid {BORDER}; }}")
            rl = QHBoxLayout(row)
            rl.setContentsMargins(16, 10, 16, 10)
            rl.setSpacing(14)

            badge = QLabel(icon)
            badge.setFixedSize(40, 36)
            badge.setAlignment(Qt.AlignCenter)
            badge.setStyleSheet(f"background:{color}22; color:{color}; border-radius:6px; font-size:10px; font-weight:bold;")
            rl.addWidget(badge)

            info = QVBoxLayout(); info.setSpacing(2)
            info.addWidget(_lbl(tx.get("description") or tx["transaction_type"].value.title(), TEXT, 12, True))
            acct_no = tx.get("account_number", "")
            info.addWidget(_lbl(f"{acct_no}  -  {tx['created_at'].strftime('%d %b %Y  %H:%M')}", MUTED, 10))
            rl.addLayout(info)
            rl.addStretch()

            rl.addWidget(_lbl(f"{sign}${tx['amount']:,.2f}", color, 13, True))
            self.tx_list.insertWidget(i, row)