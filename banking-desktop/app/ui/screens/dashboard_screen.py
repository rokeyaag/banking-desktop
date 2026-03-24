from datetime import datetime
from collections import defaultdict
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QScrollArea, QSizePolicy, QLineEdit, QPushButton, QGridLayout)
from PySide6.QtCore import Qt, Signal, QThread
from PySide6.QtGui import QFont

BG="#0b0f1a"; PANEL="#111827"; ACCENT="#3b82f6"; GREEN="#22c55e"
TEXT="#e2e8f0"; MUTED="#64748b"; RED="#ef4444"; YELLOW="#f59e0b"

CHART_H     = 148
CELL_H      = CHART_H + 24
ANALYTICS_H = CELL_H * 2 + 5 + 20 + 8 + 8 + 3


def _card(parent=None):
    f = QFrame(parent)
    f.setStyleSheet(f"QFrame {{ background:{PANEL}; border-radius:12px; border:1px solid #1e293b; }}")
    return f

def _lbl(text, color=None, size=13, bold=False, parent=None):
    l = QLabel(text, parent)
    w = QFont.Bold if bold else QFont.Normal
    l.setFont(QFont("Segoe UI", size, w))
    l.setStyleSheet(f"color:{color or TEXT}; background:transparent; border:none;")
    return l


# ── Search Thread ─────────────────────────────────────────────
class SearchThread(QThread):
    result_ready = Signal(list)
    error        = Signal(str)

    def __init__(self, query: str, user_id):
        super().__init__()
        self.query   = query
        self.user_id = user_id

    def run(self):
        try:
            from app.db.session import get_db
            from app.llm.ollama_client import get_embedding, chat
            from app.db.models import DocumentChunk

            query_emb = get_embedding(self.query)
            with get_db() as db:
                chunks = db.query(DocumentChunk).all()

            if not chunks:
                self.result_ready.emit([]); return

            import numpy as np
            def cosine(a, b):
                a, b = np.array(a), np.array(b)
                n = np.linalg.norm(a) * np.linalg.norm(b)
                return float(np.dot(a, b) / n) if n > 0 else 0.0

            scored = []
            for c in chunks:
                if c.embedding and isinstance(c.embedding, list):
                    scored.append((cosine(query_emb, c.embedding), c))
                elif self.query.lower() in c.content.lower():
                    scored.append((0.5, c))
            scored.sort(key=lambda x: x[0], reverse=True)
            matched = [c for _, c in scored[:5]]
            if not matched:
                self.result_ready.emit([]); return

            context = "\n\n".join(c.content for c in matched)
            answer = chat(
                messages=[{"role": "user", "content": self.query}],
                system=(f"You are a helpful NexaBank assistant. "
                        f"Answer based on this context:\n\n{context}\n\n"
                        f"Be concise (2-3 sentences max)."),
                temperature=0.3,
            )
            self.result_ready.emit([{"title": "AI Answer", "text": answer}])
        except Exception as e:
            self.error.emit(str(e))


class DashboardScreen(QWidget):
    navigate = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background-color:{BG};")
        self._search_thread = None
        self._build()

    def _build(self):
        outer_scroll = QScrollArea()
        outer_scroll.setWidgetResizable(True)
        outer_scroll.setStyleSheet("QScrollArea { border:none; background:transparent; }")
        outer_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        content = QWidget(); content.setStyleSheet("background:transparent;")
        self._layout = QVBoxLayout(content)
        self._layout.setContentsMargins(20, 14, 20, 14)
        self._layout.setSpacing(10)

        # Title + date
        title_row = QHBoxLayout()
        self.greeting = _lbl("Dashboard", TEXT, 20, True)
        title_row.addWidget(self.greeting)
        title_row.addStretch()
        self.date_lbl = _lbl("", MUTED, 11)
        title_row.addWidget(self.date_lbl)
        self._layout.addLayout(title_row)

        # ── Stat cards row ──
        self.stats_row = QHBoxLayout(); self.stats_row.setSpacing(8)
        self._layout.addLayout(self.stats_row)

        # ── Row 2: Analytics 50% + Account List 50% ──
        top_row = QHBoxLayout()
        top_row.setSpacing(10)
        top_row.setAlignment(Qt.AlignTop)

        # LEFT 50%: Analytics card
        self.charts_outer = _card()
        self.charts_outer.setFixedHeight(ANALYTICS_H)
        self.charts_outer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        charts_fl = QVBoxLayout(self.charts_outer)
        charts_fl.setContentsMargins(8, 8, 8, 8)
        charts_fl.setSpacing(3)
        charts_fl.addWidget(_lbl("📊 Analytics", MUTED, 10, True))
        self.charts_grid_layout = QGridLayout()
        self.charts_grid_layout.setSpacing(5)
        self.charts_grid_layout.setContentsMargins(0, 0, 0, 0)
        charts_fl.addLayout(self.charts_grid_layout)
        top_row.addWidget(self.charts_outer, 1)  # stretch=1 → 50%

        # RIGHT 50%: Account List card
        acct_frame = _card()
        acct_frame.setFixedHeight(ANALYTICS_H)
        acct_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        acct_fl = QVBoxLayout(acct_frame)
        acct_fl.setContentsMargins(14, 10, 14, 10); acct_fl.setSpacing(8)

        acct_hdr = QHBoxLayout()
        acct_hdr.addWidget(_lbl("🏦  Account List", TEXT, 12, True))
        acct_hdr.addStretch()
        self.acct_search = QLineEdit()
        self.acct_search.setPlaceholderText("🔍 Search...")
        self.acct_search.setFixedWidth(130); self.acct_search.setFixedHeight(24)
        self.acct_search.setStyleSheet("""
            QLineEdit { background:#0f172a; border:1px solid #334155; border-radius:6px;
                        color:#e2e8f0; padding:3px 8px; font-size:10px; }
            QLineEdit:focus { border-color:#3b82f6; }
        """)
        self.acct_search.textChanged.connect(self._filter_accounts)
        acct_hdr.addWidget(self.acct_search)
        acct_fl.addLayout(acct_hdr)

        acct_scroll_h = ANALYTICS_H - 52
        self.acct_scroll_area = QScrollArea()
        self.acct_scroll_area.setWidgetResizable(True)
        self.acct_scroll_area.setFixedHeight(acct_scroll_h)
        self.acct_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.acct_scroll_area.setStyleSheet("""
            QScrollArea { border:none; background:transparent; }
            QScrollBar:vertical { background:#0f172a; width:4px; border-radius:2px; }
            QScrollBar::handle:vertical { background:#334155; border-radius:2px; min-height:20px; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height:0px; }
        """)
        self.acct_scroll_widget = QWidget()
        self.acct_scroll_widget.setStyleSheet("background:transparent;")
        self.acct_list_layout = QVBoxLayout(self.acct_scroll_widget)
        self.acct_list_layout.setSpacing(6)
        self.acct_list_layout.setContentsMargins(0, 0, 4, 0)
        self.acct_list_layout.addStretch()
        self.acct_scroll_area.setWidget(self.acct_scroll_widget)
        acct_fl.addWidget(self.acct_scroll_area)
        top_row.addWidget(acct_frame, 1)  # stretch=1 → 50%

        self._layout.addLayout(top_row)

        # ── Row 3: Quick Actions 100% ──
        qa_frame = _card()
        qa_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        qa_fl = QVBoxLayout(qa_frame)
        qa_fl.setContentsMargins(16, 12, 16, 12); qa_fl.setSpacing(10)
        qa_fl.addWidget(_lbl("⚡  Quick Actions", TEXT, 12, True))
        qa_grid = QHBoxLayout(); qa_grid.setSpacing(10); qa_grid.setContentsMargins(0, 0, 0, 0)
        actions = [
            ("💰", "Deposit",     "Add funds",  "deposit"),
            ("📤", "Withdraw",    "Withdraw",   "deposit"),
            ("🏦", "New Account", "Open",       "accounts"),
            ("🤖", "AI Mode",     "Guided",     "ai_mode"),
            ("💬", "Chatbot",     "Ask AI",     "chatbot"),
        ]
        for icon, label, tip, nav_target in actions:
            btn = QFrame()
            btn.setStyleSheet(f"QFrame {{ background:#1e293b; border-radius:10px; border:1px solid #334155; }} QFrame:hover {{ border-color:{ACCENT}; }}")
            btn.setCursor(Qt.PointingHandCursor)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            bl = QVBoxLayout(btn); bl.setContentsMargins(10, 14, 10, 14); bl.setSpacing(4)
            bl.setAlignment(Qt.AlignCenter)
            bl.addWidget(_lbl(icon, TEXT, 20), 0, Qt.AlignCenter)
            bl.addWidget(_lbl(label, TEXT, 11, True), 0, Qt.AlignCenter)
            bl.addWidget(_lbl(tip, MUTED, 9), 0, Qt.AlignCenter)
            def make_handler(target):
                def handler(event): self.navigate.emit(target)
                return handler
            btn.mousePressEvent = make_handler(nav_target)
            qa_grid.addWidget(btn, 1)
        qa_fl.addLayout(qa_grid)
        self._layout.addWidget(qa_frame)

        # ── Row 4: Recent Transactions ──
        tx_frame = _card()
        tx_fl = QVBoxLayout(tx_frame); tx_fl.setContentsMargins(14, 10, 14, 10); tx_fl.setSpacing(8)
        tx_hdr = QHBoxLayout()
        tx_hdr.addWidget(_lbl("📋  Recent Transactions", TEXT, 12, True))
        tx_hdr.addStretch()
        self.tx_count_lbl = _lbl("", MUTED, 10)
        tx_hdr.addWidget(self.tx_count_lbl)
        tx_fl.addLayout(tx_hdr)

        self.tx_scroll = QScrollArea()
        self.tx_scroll.setWidgetResizable(True)
        self.tx_scroll.setFixedHeight(230)
        self.tx_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.tx_scroll.setStyleSheet("""
            QScrollArea { border:none; background:transparent; }
            QScrollBar:vertical { background:#0f172a; width:4px; border-radius:2px; }
            QScrollBar::handle:vertical { background:#334155; border-radius:2px; min-height:20px; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height:0px; }
        """)
        tx_inner = QWidget(); tx_inner.setStyleSheet("background:transparent;")
        self.tx_layout = QVBoxLayout(tx_inner)
        self.tx_layout.setSpacing(5); self.tx_layout.setContentsMargins(0, 0, 4, 0)
        self.tx_layout.addStretch()
        self.tx_scroll.setWidget(tx_inner)
        tx_fl.addWidget(self.tx_scroll)
        self._layout.addWidget(tx_frame)

        # ── Row 5: Summary ──
        summary_frame = _card()
        sf = QHBoxLayout(summary_frame); sf.setContentsMargins(0, 0, 0, 0); sf.setSpacing(0)
        self.income_lbl  = _lbl("↑  Total Deposits\n$0.00",    GREEN,  12, True)
        self.expense_lbl = _lbl("↓  Total Withdrawals\n$0.00", RED,    12, True)
        self.net_lbl     = _lbl("◎  Net Balance\n$0.00",       ACCENT, 12, True)
        for i, lbl in enumerate([self.income_lbl, self.expense_lbl, self.net_lbl]):
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setContentsMargins(0, 14, 0, 14)
            sf.addWidget(lbl, 1)
            if i < 2:
                sep = QFrame(); sep.setFrameShape(QFrame.VLine)
                sep.setFixedWidth(1); sep.setStyleSheet("background:#1e293b; border:none;")
                sf.addWidget(sep)
        self._layout.addWidget(summary_frame)

        outer_scroll.setWidget(content)
        root = QVBoxLayout(self); root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(outer_scroll)

    # ── Stat cards + Search card ───────────────────────────────
    def _build_stat_row(self, stats_data):
        self._clear_layout(self.stats_row)

        for label, value, color, icon in stats_data:
            c = _card(); cl = QVBoxLayout(c); cl.setContentsMargins(14, 10, 14, 10); cl.setSpacing(3)
            top = QHBoxLayout()
            top.addWidget(_lbl(icon, color, 15)); top.addStretch()
            cl.addLayout(top)
            cl.addWidget(_lbl(value, color, 15, True))
            cl.addWidget(_lbl(label, MUTED, 9))
            self.stats_row.addWidget(c, 1)

        # Search card
        sc = _card()
        sl = QVBoxLayout(sc); sl.setContentsMargins(14, 10, 14, 10); sl.setSpacing(4)
        self._search_icon_lbl = _lbl("🔍", TEXT, 15)
        sl.addWidget(self._search_icon_lbl)

        self._ai_result_scroll = QScrollArea()
        self._ai_result_scroll.setWidgetResizable(True)
        self._ai_result_scroll.setFixedHeight(55)
        self._ai_result_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._ai_result_scroll.setStyleSheet("""
            QScrollArea { border:none; background:transparent; }
            QScrollBar:vertical { background:#0f172a; width:3px; border-radius:2px; }
            QScrollBar::handle:vertical { background:#334155; border-radius:2px; min-height:10px; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height:0px; }
        """)
        self._ai_result_lbl = QLabel("")
        self._ai_result_lbl.setWordWrap(True)
        self._ai_result_lbl.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self._ai_result_lbl.setStyleSheet(f"color:{TEXT}; font-size:9px; background:transparent; border:none;")
        self._ai_result_scroll.setWidget(self._ai_result_lbl)
        self._ai_result_scroll.setVisible(False)
        sl.addWidget(self._ai_result_scroll)
        sl.addWidget(_lbl("Policy & Service Search", MUTED, 9))
        sl.addStretch()

        inp_row = QHBoxLayout(); inp_row.setSpacing(5)
        self._ai_search_inp = QLineEdit()
        self._ai_search_inp.setPlaceholderText("Ask a question...")
        self._ai_search_inp.setFixedHeight(24)
        self._ai_search_inp.setStyleSheet("""
            QLineEdit { background:#0f172a; border:1px solid #334155; border-radius:6px;
                        color:#e2e8f0; padding:3px 7px; font-size:10px; }
            QLineEdit:focus { border-color:#3b82f6; }
        """)
        self._ai_search_inp.returnPressed.connect(self._do_ai_search)
        ai_btn = QPushButton("AI Search")
        ai_btn.setFixedHeight(24)
        ai_btn.setStyleSheet(f"""
            QPushButton {{ background:{ACCENT}; color:white; border:none; border-radius:6px;
                           padding:0 8px; font-size:9px; font-weight:600; }}
            QPushButton:hover {{ background:#2563eb; }}
        """)
        ai_btn.clicked.connect(self._do_ai_search)
        inp_row.addWidget(self._ai_search_inp, 1)
        inp_row.addWidget(ai_btn)
        sl.addLayout(inp_row)
        self.stats_row.addWidget(sc, 1)

    # ── AI Search ──────────────────────────────────────────────
    def _do_ai_search(self):
        query = self._ai_search_inp.text().strip()
        if not query: return
        self._search_icon_lbl.setVisible(False)
        self._ai_result_lbl.setText("🔄 Searching...")
        self._ai_result_lbl.setStyleSheet(f"color:{MUTED}; font-size:9px; background:transparent; border:none;")
        self._ai_result_lbl.adjustSize()
        self._ai_result_scroll.setVisible(True)
        from app.services.auth_service import get_current_user
        user = get_current_user()
        if self._search_thread and self._search_thread.isRunning():
            self._search_thread.terminate()
        self._search_thread = SearchThread(query, user.id if user else None)
        self._search_thread.result_ready.connect(self._on_search_result)
        self._search_thread.error.connect(self._on_search_error)
        self._search_thread.start()

    def _on_search_result(self, results):
        self._search_icon_lbl.setVisible(False)
        if not results:
            self._ai_result_lbl.setText("❌ No results found.")
            self._ai_result_lbl.setStyleSheet(f"color:{MUTED}; font-size:9px; background:transparent; border:none;")
        else:
            self._ai_result_lbl.setText(f"✅ {results[0]['text']}")
            self._ai_result_lbl.setStyleSheet(f"color:{TEXT}; font-size:9px; background:transparent; border:none;")
        self._ai_result_lbl.adjustSize()
        self._ai_result_scroll.setVisible(True)

    def _on_search_error(self, err):
        self._search_icon_lbl.setVisible(False)
        self._ai_result_lbl.setText(f"⚠ {err[:200]}")
        self._ai_result_lbl.setStyleSheet(f"color:{YELLOW}; font-size:9px; background:transparent; border:none;")
        self._ai_result_lbl.adjustSize()
        self._ai_result_scroll.setVisible(True)

    # ── Compact 2x2 Charts ────────────────────────────────────
    def _build_charts(self, accounts, all_txs):
        while self.charts_grid_layout.count():
            item = self.charts_grid_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
        except ImportError:
            return

        plt.rcParams.update({
            "figure.facecolor": "#0f172a", "axes.facecolor": "#0f172a",
            "axes.edgecolor": "#1e293b",   "axes.labelcolor": "#94a3b8",
            "xtick.color": "#94a3b8",      "ytick.color": "#94a3b8",
            "text.color": "#e2e8f0",       "grid.color": "#1e293b",
            "grid.linewidth": 0.5,
        })

        from datetime import datetime as dt

        monthly_dep = defaultdict(float)
        monthly_wd  = defaultdict(float)
        for tx in all_txs:
            key = tx["created_at"].strftime("%b")
            if tx["transaction_type"].value == "DEPOSIT":
                monthly_dep[key] += tx["amount"]
            else:
                monthly_wd[key]  += tx["amount"]

        all_months = sorted(set(list(monthly_dep.keys()) + list(monthly_wd.keys())))[-5:]
        if not all_months: all_months = [dt.now().strftime("%b")]
        dep_vals = [monthly_dep.get(m, 0) for m in all_months]
        wd_vals  = [monthly_wd.get(m, 0)  for m in all_months]

        cum_dep, cum_wd, d, w = [], [], 0, 0
        for dv, wv in zip(dep_vals, wd_vals):
            d += dv; w += wv
            cum_dep.append(d); cum_wd.append(w)

        fmt = plt.FuncFormatter(lambda v, _: f"${v/1000:.0f}k" if v >= 1000 else f"${v:.0f}")
        leg_kw = dict(fontsize=6.5, facecolor="#0f172a", edgecolor="#334155",
                      labelcolor="#e2e8f0", markerscale=0.8, borderpad=0.4,
                      handlelength=1.2, handletextpad=0.4)

        def make_canvas(fig):
            fig.patch.set_alpha(0)
            c = FigureCanvas(fig)
            c.setStyleSheet("background:transparent;")
            c.setFixedHeight(CHART_H)
            c.setMaximumHeight(CHART_H)
            c.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            plt.close(fig)
            return c

        def wrap(canvas, title):
            f = QFrame()
            f.setStyleSheet("QFrame{background:#0f172a;border-radius:8px;border:1px solid #1e293b;}")
            f.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            f.setFixedHeight(CELL_H)
            fl = QVBoxLayout(f); fl.setContentsMargins(5, 4, 5, 4); fl.setSpacing(2)
            lbl = _lbl(title, MUTED, 9, True)
            lbl.setFixedHeight(16)
            fl.addWidget(lbl)
            fl.addWidget(canvas)
            return f

        # Chart 1: Bar
        fig1, ax1 = plt.subplots(figsize=(4.0, 1.8))
        fig1.subplots_adjust(left=0.18, right=0.97, top=0.97, bottom=0.18)
        x = list(range(len(all_months))); wb = 0.35
        ax1.bar([i-wb/2 for i in x], dep_vals, wb, label="In",  color="#22c55e", alpha=0.85, linewidth=0)
        ax1.bar([i+wb/2 for i in x], wd_vals,  wb, label="Out", color="#ef4444", alpha=0.85, linewidth=0)
        ax1.set_xticks(x); ax1.set_xticklabels(all_months, fontsize=7)
        ax1.tick_params(axis="y", labelsize=7)
        ax1.yaxis.set_major_formatter(fmt)
        ax1.legend(**leg_kw); ax1.grid(axis="y", alpha=0.3)

        # Chart 2: Pie
        fig2, ax2 = plt.subplots(figsize=(4.0, 1.8))
        fig2.subplots_adjust(left=0.0, right=0.55, top=0.97, bottom=0.03)
        if accounts:
            type_bal = defaultdict(float)
            for a in accounts:
                type_bal[a.get("account_type").value.title()] += max(a["balance"], 0.01)
            labels = list(type_bal.keys())
            sizes  = list(type_bal.values())
            colors = ["#3b82f6","#22c55e","#f59e0b","#a855f7","#ef4444"][:len(labels)]
            wedges, _ = ax2.pie(sizes, colors=colors, startangle=90,
                                wedgeprops={"edgecolor":"#0f172a","linewidth":1.5})
            ax2.legend(wedges, [f"{l} ${v:,.0f}" for l, v in zip(labels, sizes)],
                       loc="center left", bbox_to_anchor=(1.05, 0.5),
                       fontsize=6.5, facecolor="#0f172a", edgecolor="#334155",
                       labelcolor="#e2e8f0", framealpha=1,
                       borderpad=0.5, handlelength=1.0, handletextpad=0.4)
        else:
            ax2.text(0.5, 0.5, "No data", ha="center", va="center", color="#64748b", fontsize=8)
            ax2.axis("off")

        # Chart 3: Line
        fig3, ax3 = plt.subplots(figsize=(4.0, 1.8))
        fig3.subplots_adjust(left=0.18, right=0.97, top=0.97, bottom=0.18)
        ax3.plot(all_months, cum_dep, color="#22c55e", lw=1.8, marker="o", ms=3, label="Dep")
        ax3.plot(all_months, cum_wd,  color="#ef4444", lw=1.8, marker="o", ms=3, label="Wd")
        ax3.fill_between(all_months, cum_dep, alpha=0.1, color="#22c55e")
        ax3.fill_between(all_months, cum_wd,  alpha=0.1, color="#ef4444")
        ax3.tick_params(axis="both", labelsize=7)
        ax3.yaxis.set_major_formatter(fmt)
        ax3.legend(**leg_kw); ax3.grid(alpha=0.3)

        # Chart 4: Horizontal Bar
        fig4, ax4 = plt.subplots(figsize=(4.0, 1.8))
        fig4.subplots_adjust(left=0.28, right=0.97, top=0.97, bottom=0.16)
        cat = defaultdict(float)
        for tx in all_txs:
            if tx["transaction_type"].value != "DEPOSIT":
                key = (tx.get("description") or "Other")[:10]
                cat[key] += tx["amount"]
        if cat:
            sc = sorted(cat.items(), key=lambda x: x[1], reverse=True)[:4]
            cl = [c[0] for c in sc]; cv = [c[1] for c in sc]
            bc = ["#f59e0b","#3b82f6","#22c55e","#a855f7"][:len(cl)]
            ax4.barh(cl, cv, color=bc, alpha=0.85, linewidth=0, height=0.5)
            ax4.tick_params(axis="y", labelsize=6.5)
            ax4.tick_params(axis="x", labelsize=6.5)
            ax4.xaxis.set_major_formatter(fmt)
            ax4.invert_yaxis(); ax4.grid(axis="x", alpha=0.3)
        else:
            ax4.text(0.5, 0.5, "No data", ha="center", va="center", color="#64748b", fontsize=8)
            ax4.axis("off")

        self.charts_grid_layout.addWidget(wrap(make_canvas(fig1), "📊 Income vs Expense"), 0, 0)
        self.charts_grid_layout.addWidget(wrap(make_canvas(fig2), "🥧 Balance Share"),      0, 1)
        self.charts_grid_layout.addWidget(wrap(make_canvas(fig3), "📈 History"),            1, 0)
        self.charts_grid_layout.addWidget(wrap(make_canvas(fig4), "💸 Spending"),           1, 1)

    # ── refresh ────────────────────────────────────────────────
    def refresh(self):
        from app.services.auth_service import get_current_user
        from app.services.account_service import list_accounts
        from app.services.deposit_service import get_transaction_history
        from app.db.session import get_db

        user = get_current_user()
        if not user: return

        self.date_lbl.setText(datetime.now().strftime("%A, %d %B %Y"))

        with get_db() as db:
            accounts = list_accounts(db, user.id)

        total = sum(a["balance"] for a in accounts)
        total_dep = total_wd = 0.0
        all_txs = []
        with get_db() as db:
            for a in accounts:
                txs = get_transaction_history(db, a["id"], user.id, limit=10)
                all_txs.extend(txs)
        for tx in all_txs:
            if tx["transaction_type"].value == "DEPOSIT":
                total_dep += tx["amount"]
            else:
                total_wd += tx["amount"]
        net = total_dep - total_wd

        self._build_stat_row([
            ("Total Balance",  f"${total:,.2f}",    GREEN,  "💰"),
            ("Accounts",       str(len(accounts)),   ACCENT, "🏦"),
            ("Total Deposits", f"${total_dep:,.2f}", GREEN,  "↑"),
            ("Withdrawals",    f"${total_wd:,.2f}",  RED,    "↓"),
        ])

        self._build_charts(accounts, all_txs)
        self._all_accounts = accounts
        self._render_account_rows(accounts)

        # Transactions
        while self.tx_layout.count() > 1:
            item = self.tx_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        all_txs.sort(key=lambda t: t["created_at"], reverse=True)
        self.tx_count_lbl.setText(f"{len(all_txs)} transactions")
        if not all_txs:
            self.tx_layout.insertWidget(0, _lbl("No transactions yet.", MUTED, 11))
        else:
            for i, tx in enumerate(all_txs):
                sign  = "+" if tx["transaction_type"].value == "DEPOSIT" else "-"
                color = GREEN if sign == "+" else RED
                row = QFrame()
                row.setStyleSheet("QFrame { background:#0f172a; border-radius:8px; border:1px solid #1e293b; }")
                rl = QHBoxLayout(row); rl.setContentsMargins(12, 7, 12, 7); rl.setSpacing(10)
                rl.addWidget(_lbl("↑" if sign == "+" else "↓", color, 13, True))
                dc = QVBoxLayout(); dc.setSpacing(1)
                dc.addWidget(_lbl(tx["description"] or tx["transaction_type"].value.title(), TEXT, 11))
                dc.addWidget(_lbl(tx["created_at"].strftime("%d %b %Y  %H:%M"), MUTED, 9))
                rl.addLayout(dc); rl.addStretch()
                rl.addWidget(_lbl(f"{sign}${tx['amount']:,.2f}", color, 12, True))
                self.tx_layout.insertWidget(i, row)

        # Summary
        self.income_lbl.setText(f"↑  Total Deposits\n${total_dep:,.2f}")
        self.expense_lbl.setText(f"↓  Total Withdrawals\n${total_wd:,.2f}")
        net_color = GREEN if net >= 0 else RED
        self.net_lbl.setStyleSheet(f"color:{net_color}; background:transparent; border:none;")
        self.net_lbl.setText(f"◎  Net Balance\n${net:,.2f}")

    def _render_account_rows(self, accounts):
        while self.acct_list_layout.count() > 1:
            item = self.acct_list_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()

        if not accounts:
            self.acct_list_layout.insertWidget(0, _lbl("No accounts found.", MUTED, 11))
            return

        import os
        from app.services.auth_service import get_current_user
        user = get_current_user()

        for i, a in enumerate(accounts):
            row = QFrame()
            row.setStyleSheet("QFrame { background:#1e293b; border-radius:8px; border:none; }")
            rl = QHBoxLayout(row); rl.setContentsMargins(10, 7, 10, 7); rl.setSpacing(10)

            photo_path = a.get("photo_path", "")
            if photo_path and os.path.exists(photo_path):
                from PySide6.QtGui import QPixmap
                avatar = QLabel()
                pix = QPixmap(photo_path).scaled(32, 32, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
                avatar.setPixmap(pix); avatar.setFixedSize(32, 32)
                avatar.setStyleSheet("border-radius:16px; border:2px solid #3b82f6; background:transparent;")
            else:
                holder  = a.get("holder_name") or (user.full_name if user else "?")
                initial = holder[0].upper() if holder else "?"
                avatar  = QLabel(initial); avatar.setFixedSize(32, 32)
                avatar.setAlignment(Qt.AlignCenter)
                avatar.setStyleSheet(f"background:{ACCENT}33; color:{ACCENT}; border-radius:16px; font-size:12px; font-weight:bold; border:2px solid {ACCENT}55;")
            rl.addWidget(avatar)

            holder_name = a.get("holder_name") or (user.full_name if user else "Unknown")
            info = QVBoxLayout(); info.setSpacing(1)
            info.addWidget(_lbl(holder_name, TEXT, 11, True))
            info.addWidget(_lbl(f"{a['account_number']}  ·  {a['account_type'].value.title()}", MUTED, 9))
            rl.addLayout(info); rl.addStretch()

            bc = QVBoxLayout(); bc.setSpacing(1); bc.setAlignment(Qt.AlignRight)
            bc.addWidget(_lbl(f"${a['balance']:,.2f}", GREEN, 11, True))
            bc.addWidget(_lbl(a.get("currency", "USD"), MUTED, 9))
            rl.addLayout(bc)
            self.acct_list_layout.insertWidget(i, row)

    def _filter_accounts(self, query: str):
        if not hasattr(self, "_all_accounts"): return
        q = query.strip().lower()
        filtered = [a for a in self._all_accounts if
                    q in a["account_number"].lower() or
                    q in a["account_type"].value.lower() or
                    q in (a.get("holder_name") or "").lower() or
                    q in f"{a['balance']:.2f}"] if q else self._all_accounts
        self._render_account_rows(filtered)

    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
            elif item.layout(): self._clear_layout(item.layout())