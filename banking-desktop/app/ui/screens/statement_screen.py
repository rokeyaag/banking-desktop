# -*- coding: utf-8 -*-
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QPushButton, QComboBox, QFileDialog, QMessageBox)
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
        QComboBox { background:#1e293b; border:1px solid #334155; border-radius:8px; color:#e2e8f0; padding:10px 14px; font-size:13px; }
        QComboBox QAbstractItemView { background:#0d1117; color:#e2e8f0; selection-background-color:#3b82f6; border:1px solid #334155; }
        QComboBox QAbstractItemView::item { padding:8px 14px; min-height:30px; }
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

class StatementScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background-color:{BG};")
        self._accounts = []
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(20)
        layout.addWidget(_lbl("Account Statement", TEXT, 22, True))

        card = QFrame()
        card.setStyleSheet(f"QFrame {{ background:{PANEL}; border-radius:16px; border:1px solid {BORDER}; }}")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(32, 28, 32, 28)
        cl.setSpacing(14)

        cl.addWidget(_lbl("Select Account:"))
        self.acct_combo = QComboBox()
        self.acct_combo.setStyleSheet(_combo_style())
        self.acct_combo.setFixedHeight(46)
        cl.addWidget(self.acct_combo)

        cl.addWidget(_lbl("Statement Period:"))
        self.period_combo = QComboBox()
        self.period_combo.addItems(["Last 1 Month", "Last 3 Months", "Last 6 Months", "Last 1 Year", "All Time"])
        self.period_combo.setCurrentIndex(1)
        self.period_combo.setStyleSheet(_combo_style())
        self.period_combo.setFixedHeight(46)
        cl.addWidget(self.period_combo)

        cl.addSpacing(8)
        cl.addWidget(_lbl("Download Options:", MUTED, 11, True))

        for icon_text, title_text, desc_text, badge_color in [
            ("[ PDF ]", "Full Statement",  "All transactions with running balance", ACCENT),
            ("[ RPT ]", "Summary Report",  "Total income, expenses and net balance", GREEN),
        ]:
            opt = QFrame()
            opt.setStyleSheet(f"QFrame {{ background:#0b0f1a; border-radius:10px; border:1px solid {BORDER}; }} QFrame:hover {{ border-color:{ACCENT}; }}")
            opt.setCursor(Qt.PointingHandCursor)
            ol = QHBoxLayout(opt)
            ol.setContentsMargins(16, 12, 16, 12)
            ol.setSpacing(14)
            ol.addWidget(_lbl(icon_text, badge_color, 11, True))
            info = QVBoxLayout(); info.setSpacing(2)
            info.addWidget(_lbl(title_text, TEXT, 12, True))
            info.addWidget(_lbl(desc_text, MUTED, 10))
            ol.addLayout(info)
            ol.addStretch()
            badge = QLabel("PDF")
            badge.setStyleSheet(f"background:{badge_color}22; color:{badge_color}; font-size:10px; font-weight:700; padding:3px 8px; border-radius:4px;")
            ol.addWidget(badge)
            cl.addWidget(opt)

        cl.addSpacing(4)
        dl_btn = QPushButton("Download Statement PDF")
        dl_btn.setFixedHeight(48)
        dl_btn.setStyleSheet(f"QPushButton {{ background:{ACCENT}; color:white; border:none; border-radius:8px; font-size:15px; font-weight:600; }} QPushButton:hover {{ background:#2563eb; }}")
        dl_btn.clicked.connect(self._download)
        cl.addWidget(dl_btn)

        self.err_lbl = QLabel("")
        self.err_lbl.setStyleSheet(f"color:{RED}; background:transparent; font-size:13px;")
        self.err_lbl.setVisible(False)
        cl.addWidget(self.err_lbl)

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
            })
        self.acct_combo.clear()
        for a in self._accounts:
            self.acct_combo.addItem(
                f"{a['account_number']} ({a['account_type'].title()}) -- ${a['balance']:,.2f}"
            )

    def _download(self):
        self.err_lbl.setVisible(False)
        if not self._accounts:
            self.err_lbl.setText("No accounts found.")
            self.err_lbl.setVisible(True); return

        idx = self.acct_combo.currentIndex()
        if idx < 0: return
        acct = self._accounts[idx]

        from datetime import datetime, timedelta
        period = self.period_combo.currentText()
        now = datetime.now()
        if   period == "Last 1 Month":  start = now - timedelta(days=30)
        elif period == "Last 3 Months": start = now - timedelta(days=90)
        elif period == "Last 6 Months": start = now - timedelta(days=180)
        elif period == "Last 1 Year":   start = now - timedelta(days=365)
        else:                            start = datetime(2000, 1, 1)

        path, _ = QFileDialog.getSaveFileName(
            self, "Save Statement",
            f"statement_{acct['account_number']}.pdf",
            "PDF Files (*.pdf)"
        )
        if not path: return

        try:
            self._generate_pdf(path, acct, start, now, period)
            _msgbox(self, "Success", f"Statement saved:\n{path}")
        except Exception as e:
            self.err_lbl.setText(f"Error: {str(e)}")
            self.err_lbl.setVisible(True)

    def _generate_pdf(self, path, acct, start, end, period):
        from app.services.auth_service import get_current_user
        from app.services.deposit_service import get_transaction_history
        from app.db.session import get_db
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import mm

        user = get_current_user()
        with get_db() as db:
            all_txs = get_transaction_history(db, acct["id"], user.id, limit=1000)

        txs = [t for t in all_txs if t["created_at"] >= start]
        txs.sort(key=lambda t: t["created_at"])

        total_dep = sum(t["amount"] for t in txs if t["transaction_type"].value == "DEPOSIT")
        total_wd  = sum(t["amount"] for t in txs if t["transaction_type"].value != "DEPOSIT")
        net       = total_dep - total_wd

        doc  = SimpleDocTemplate(path, pagesize=A4,
                                 rightMargin=20*mm, leftMargin=20*mm,
                                 topMargin=20*mm, bottomMargin=20*mm)
        stys = getSampleStyleSheet()
        elms = []

        title_style = ParagraphStyle("title", parent=stys["Title"], fontSize=18,
                                     textColor=colors.HexColor("#1e40af"))
        elms.append(Paragraph("NexaBank - Account Statement", title_style))
        elms.append(Spacer(1, 6*mm))

        info = [
            ["Account Number:", acct["account_number"]],
            ["Account Type:",   acct["account_type"].title()],
            ["Current Balance:", f"${acct['balance']:,.2f}"],
            ["Period:",          period],
            ["Generated:",       end.strftime("%d %b %Y %H:%M")],
            ["Account Holder:",  user.full_name],
        ]
        info_tbl = Table(info, colWidths=[50*mm, 100*mm])
        info_tbl.setStyle(TableStyle([
            ("FONTSIZE",      (0,0),(-1,-1), 10),
            ("TEXTCOLOR",     (0,0),(0,-1),  colors.HexColor("#64748b")),
            ("FONTNAME",      (0,0),(0,-1),  "Helvetica-Bold"),
            ("BOTTOMPADDING", (0,0),(-1,-1), 4),
        ]))
        elms.append(info_tbl)
        elms.append(Spacer(1, 6*mm))

        summary_data = [
            ["Total Deposits",     "Total Withdrawals", "Net Balance"],
            [f"${total_dep:,.2f}", f"${total_wd:,.2f}", f"${net:,.2f}"],
        ]
        s_tbl = Table(summary_data, colWidths=[55*mm, 55*mm, 55*mm])
        s_tbl.setStyle(TableStyle([
            ("BACKGROUND",     (0,0),(-1,0),  colors.HexColor("#1e40af")),
            ("TEXTCOLOR",      (0,0),(-1,0),  colors.white),
            ("FONTNAME",       (0,0),(-1,0),  "Helvetica-Bold"),
            ("FONTSIZE",       (0,0),(-1,-1), 11),
            ("ALIGN",          (0,0),(-1,-1), "CENTER"),
            ("ROWBACKGROUNDS", (0,1),(-1,-1), [colors.HexColor("#f0f9ff")]),
            ("GRID",           (0,0),(-1,-1), 0.5, colors.HexColor("#cbd5e1")),
            ("BOTTOMPADDING",  (0,0),(-1,-1), 8),
            ("TOPPADDING",     (0,0),(-1,-1), 8),
        ]))
        elms.append(s_tbl)
        elms.append(Spacer(1, 6*mm))

        elms.append(Paragraph("Transaction Details",
            ParagraphStyle("hdr", parent=stys["Heading2"], fontSize=13,
                           textColor=colors.HexColor("#1e293b"))))
        elms.append(Spacer(1, 3*mm))

        tx_data = [["Date", "Description", "Type", "Amount"]]
        for tx in txs:
            is_dep = tx["transaction_type"].value == "DEPOSIT"
            sign   = "+" if is_dep else "-"
            tx_data.append([
                tx["created_at"].strftime("%d %b %Y"),
                (tx.get("description") or tx["transaction_type"].value.title())[:40],
                "Deposit" if is_dep else "Withdrawal",
                f"{sign}${tx['amount']:,.2f}",
            ])

        tx_tbl = Table(tx_data, colWidths=[32*mm, 80*mm, 30*mm, 28*mm])
        tx_style = [
            ("BACKGROUND",    (0,0),(-1,0),  colors.HexColor("#1e40af")),
            ("TEXTCOLOR",     (0,0),(-1,0),  colors.white),
            ("FONTNAME",      (0,0),(-1,0),  "Helvetica-Bold"),
            ("FONTSIZE",      (0,0),(-1,-1), 9),
            ("ALIGN",         (3,0),(3,-1),  "RIGHT"),
            ("GRID",          (0,0),(-1,-1), 0.3, colors.HexColor("#e2e8f0")),
            ("BOTTOMPADDING", (0,0),(-1,-1), 5),
            ("TOPPADDING",    (0,0),(-1,-1), 5),
        ]
        for i, tx in enumerate(txs, 1):
            bg  = colors.HexColor("#f0fdf4") if tx["transaction_type"].value == "DEPOSIT" else colors.HexColor("#fff1f2")
            col = colors.HexColor("#16a34a") if tx["transaction_type"].value == "DEPOSIT" else colors.HexColor("#dc2626")
            tx_style.append(("BACKGROUND", (0,i),(-1,i), bg))
            tx_style.append(("TEXTCOLOR",  (3,i),(3,i),  col))
        tx_tbl.setStyle(TableStyle(tx_style))
        elms.append(tx_tbl)
        doc.build(elms)