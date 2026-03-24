import threading
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QLineEdit, QScrollArea, QSizePolicy)
from PySide6.QtCore import Qt, Slot, Signal, QThread
from PySide6.QtGui import QFont

BG="#0b0f1a"; PANEL="#111827"; ACCENT="#3b82f6"; TEXT="#e2e8f0"; MUTED="#64748b"
RED="#ef4444"; GREEN="#22c55e"; YELLOW="#f59e0b"


# ── Voice Recording Thread ────────────────────────────────────
class VoiceThread(QThread):
    text_ready = Signal(str)
    error      = Signal(str)
    listening  = Signal()
    tick       = Signal(int)

    def __init__(self):
        super().__init__()
        self._running = False

    def stop(self):
        self._running = False

    def run(self):
        try:
            import sounddevice as sd
            import numpy as np
            import tempfile, os, wave, time
            from faster_whisper import WhisperModel

            self._running = True
            sample_rate  = 16000
            chunk_secs   = 0.1
            chunk_frames = int(sample_rate * chunk_secs)
            all_frames   = []
            elapsed      = 0

            self.listening.emit()

            with sd.InputStream(samplerate=sample_rate, channels=1,
                                 dtype='int16', blocksize=chunk_frames) as stream:
                while self._running:
                    chunk, _ = stream.read(chunk_frames)
                    all_frames.append(chunk.copy())
                    elapsed += chunk_secs
                    if int(elapsed) != int(elapsed - chunk_secs):
                        self.tick.emit(int(elapsed))

            if not all_frames:
                self.error.emit('No audio recorded.')
                return

            audio = np.concatenate(all_frames, axis=0)

            tmp      = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
            tmp_path = tmp.name
            tmp.close()
            with wave.open(tmp_path, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(sample_rate)
                wf.writeframes(audio.tobytes())

            model    = WhisperModel('tiny', device='cpu', compute_type='int8')
            segments, _ = model.transcribe(tmp_path, language='en')
            text     = ' '.join(s.text for s in segments).strip()
            try:
                os.unlink(tmp_path)
            except Exception:
                pass

            if text:
                self.text_ready.emit(text)
            else:
                self.error.emit('Could not hear anything. Please try again.')

        except ImportError:
            self.error.emit('⚠ Run: pip install faster-whisper sounddevice')
        except Exception as e:
            self.error.emit(f'Voice error: {str(e)}')


# ── DB Intent Detection ───────────────────────────────────────
def _detect_db_intent(query: str) -> dict | None:
    """
    Check if user is asking for live DB data.
    Returns intent dict or None if no DB query needed.
    """
    q = query.lower()

    # Balance query
    if any(w in q for w in ["balance", "how much", "account balance", "taka ache", "কত টাকা"]):
        import re
        # extract account number (10+ digit number)
        match = re.search(r'\b(\d{10,20})\b', query)
        if match:
            return {"type": "balance", "account_number": match.group(1)}
        return {"type": "balance", "account_number": None}

    # Transaction history
    if any(w in q for w in ["transaction", "history", "last", "recent", "লেনদেন"]):
        import re
        match = re.search(r'\b(\d{10,20})\b', query)
        return {"type": "transactions", "account_number": match.group(1) if match else None}

    # Loan status
    if any(w in q for w in ["loan", "emi", "borrow", "ঋণ"]):
        return {"type": "loan"}

    return None


def _handle_db_intent(intent: dict, user_id) -> str:
    """
    Fetch live data from DB based on intent.
    Returns a formatted string answer.
    """
    try:
        from app.db.session import get_db
        from app.db.models import Account, Transaction, Loan

        with get_db() as db:

            # ── Balance ──
            if intent["type"] == "balance":
                acc_no = intent.get("account_number")
                if acc_no:
                    account = db.query(Account).filter(
                        Account.account_number == acc_no,
                        Account.user_id == user_id
                    ).first()
                    if account:
                        return (
                            f"✅ Account Balance\n\n"
                            f"Account No : {account.account_number}\n"
                            f"Holder     : {account.holder_name}\n"
                            f"Type       : {account.account_type}\n"
                            f"Balance    : ৳ {float(account.balance):,.2f}\n"
                            f"Status     : {account.status}"
                        )
                    else:
                        return "❌ Account not found or you don't have access to this account."
                else:
                    # Show all accounts of this user
                    accounts = db.query(Account).filter(
                        Account.user_id == user_id,
                        Account.status == "active"
                    ).all()
                    if not accounts:
                        return "❌ No active accounts found."
                    lines = ["✅ Your Account Balances\n"]
                    for a in accounts:
                        lines.append(f"• {a.account_number}  →  ৳ {float(a.balance):,.2f}  ({a.account_type})")
                    return "\n".join(lines)

            # ── Transactions ──
            elif intent["type"] == "transactions":
                acc_no = intent.get("account_number")
                if acc_no:
                    account = db.query(Account).filter(
                        Account.account_number == acc_no,
                        Account.user_id == user_id
                    ).first()
                    if not account:
                        return "❌ Account not found or you don't have access to this account."
                    txns = (
                        db.query(Transaction)
                        .filter(Transaction.account_id == account.id)
                        .order_by(Transaction.created_at.desc())
                        .limit(5)
                        .all()
                    )
                else:
                    # All accounts
                    accounts = db.query(Account).filter(Account.user_id == user_id).all()
                    acc_ids  = [a.id for a in accounts]
                    txns = (
                        db.query(Transaction)
                        .filter(Transaction.account_id.in_(acc_ids))
                        .order_by(Transaction.created_at.desc())
                        .limit(5)
                        .all()
                    )

                if not txns:
                    return "No recent transactions found."

                lines = ["📋 Last 5 Transactions\n"]
                for t in txns:
                    sign  = "+" if t.type == "credit" else "-"
                    color = "↑" if t.type == "credit" else "↓"
                    date  = t.created_at.strftime("%d %b %Y")
                    lines.append(f"{color} {sign}৳{float(t.amount):,.2f}  |  {t.type.upper()}  |  {date}  |  {t.description or ''}")
                return "\n".join(lines)

            # ── Loan ──
            elif intent["type"] == "loan":
                loans = db.query(Loan).filter(
                    Loan.user_id == user_id
                ).order_by(Loan.applied_at.desc()).all()

                if not loans:
                    return "You have no loans at the moment."

                lines = ["🏦 Your Loans\n"]
                for l in loans:
                    lines.append(
                        f"• Loan ID   : {l.id}\n"
                        f"  Principal : ৳ {float(l.principal):,.2f}\n"
                        f"  Outstanding: ৳ {float(l.outstanding_balance):,.2f}\n"
                        f"  EMI       : ৳ {float(l.emi_amount):,.2f}/month\n"
                        f"  Status    : {l.status}\n"
                    )
                return "\n".join(lines)

    except Exception as e:
        return f"⚠️ Could not fetch data: {str(e)}"

    return None


# ── RAG Search Thread ─────────────────────────────────────────
class RAGThread(QThread):
    result_ready = Signal(str)

    def __init__(self, query: str, history: list, user_id=None):
        super().__init__()
        self.query   = query
        self.history = history
        self.user_id = user_id

    def run(self):
        try:
            # ── Step 1: Check if this is a live DB question ──
            if self.user_id:
                intent = _detect_db_intent(self.query)
                if intent:
                    answer = _handle_db_intent(intent, self.user_id)
                    if answer:
                        self.result_ready.emit(answer)
                        return

            # ── Step 2: Normal RAG + LLM flow ──
            from app.db.session import get_db
            from app.llm.ollama_client import get_embedding, chat, is_ollama_available
            from app.db.models import DocumentChunk
            from app.llm.prompts import build_chatbot_system

            if not is_ollama_available():
                self.result_ready.emit("⚠️ Ollama is not running. Please start Ollama.")
                return

            rag_context = ""
            try:
                query_emb = get_embedding(self.query)
                with get_db() as db:
                    chunks = db.query(DocumentChunk).all()

                if chunks:
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
                    top = [c for _, c in scored[:3]]
                    if top:
                        rag_context = "\n\n".join(c.content for c in top)
            except Exception:
                pass

            system = build_chatbot_system()
            if rag_context:
                system += (
                    f"\n\nYou also have access to NexaBank's official policy documents. "
                    f"Use the following context to answer policy/service questions accurately:\n\n"
                    f"--- NexaBank Policy Context ---\n{rag_context}\n---\n\n"
                    f"If the question is about NexaBank policies, fees, limits, or services, "
                    f"prioritize this context in your answer."
                )

            response = chat(self.history, system=system, temperature=0.5)
            self.result_ready.emit(response)

        except Exception as e:
            self.result_ready.emit(f"⚠️ AI error: {str(e)}")


class ChatbotScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background-color:{BG};")
        self._session_id   = None
        self._thinking     = None
        self._voice_thread = None
        self._rag_thread   = None
        self._is_recording = False
        self._current_user = None
        self._build()

    def _build(self):
        root = QHBoxLayout(self); root.setContentsMargins(0,0,0,0); root.setSpacing(0)

        # ── Sidebar ──
        sidebar = QFrame(); sidebar.setFixedWidth(220)
        sidebar.setStyleSheet("QFrame { background:#0d1117; border-right:1px solid #1e293b; }")
        sl = QVBoxLayout(sidebar); sl.setContentsMargins(12,16,12,16); sl.setSpacing(8)

        sl.addWidget(QLabel("Conversations"))
        new_btn = QPushButton("+ New Chat")
        new_btn.setStyleSheet(f"QPushButton {{ background:{ACCENT}; color:white; border:none; border-radius:8px; padding:8px; font-size:13px; }} QPushButton:hover {{ background:#2563eb; }}")
        new_btn.clicked.connect(self._new_chat)
        sl.addWidget(new_btn)

        from app.ui.widgets.upload_dropzone import UploadDropzone
        dropzone = UploadDropzone(); dropzone.file_dropped.connect(self._on_file)
        sl.addWidget(dropzone)
        sl.addStretch()

        self._voice_status = QLabel("")
        self._voice_status.setWordWrap(True)
        self._voice_status.setStyleSheet(f"color:{MUTED}; font-size:10px; background:transparent;")
        sl.addWidget(self._voice_status)
        root.addWidget(sidebar)

        # ── Main chat area ──
        main = QWidget(); main.setStyleSheet(f"background:{BG};")
        ml = QVBoxLayout(main); ml.setContentsMargins(24,20,24,20); ml.setSpacing(12)

        hdr_row = QHBoxLayout()
        header = QLabel("🤖 NexaBank AI Assistant")
        header.setFont(QFont("Segoe UI", 16, QFont.Bold))
        header.setStyleSheet(f"color:{TEXT}; background:transparent;")
        hdr_row.addWidget(header)
        hdr_row.addStretch()
        rag_badge = QLabel("📚 Policy RAG Active")
        rag_badge.setStyleSheet(f"color:{GREEN}; font-size:10px; background:#22c55e22; border:1px solid #22c55e44; border-radius:6px; padding:3px 8px;")
        hdr_row.addWidget(rag_badge)
        ml.addLayout(hdr_row)

        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border:none; background:transparent; }")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.msg_w = QWidget(); self.msg_w.setStyleSheet("background:transparent;")
        self.msg_layout = QVBoxLayout(self.msg_w)
        self.msg_layout.setSpacing(8); self.msg_layout.setContentsMargins(0,0,0,0)
        self.msg_layout.addStretch()
        scroll.setWidget(self.msg_w)
        self._scroll = scroll
        ml.addWidget(scroll, 1)

        qp_row = QHBoxLayout(); qp_row.setSpacing(8)
        prompts = [
            ("💰 Deposit",       "How do I make a deposit?"),
            ("🏦 Open Account",  "How do I open a new account?"),
            ("🔒 PIN Policy",    "What is the PIN policy?"),
            ("💸 Withdrawal",    "What is the withdrawal limit?"),
            ("📊 Interest Rate", "What are the interest rates?"),
        ]
        for label, text in prompts:
            qb = QPushButton(label)
            qb.setStyleSheet(f"QPushButton {{ background:{PANEL}; color:{MUTED}; border:1px solid #1e293b; border-radius:8px; padding:5px 10px; font-size:11px; }} QPushButton:hover {{ border-color:{ACCENT}; color:{TEXT}; }}")
            qb.clicked.connect(lambda _, t=text: self._send_message(t))
            qp_row.addWidget(qb)
        qp_row.addStretch()
        ml.addLayout(qp_row)

        inp_row = QHBoxLayout(); inp_row.setSpacing(8)

        self.inp = QLineEdit()
        self.inp.setPlaceholderText("Ask me anything about NexaBank...")
        self.inp.setStyleSheet("""
            QLineEdit { background:#1e293b; border:1px solid #334155; border-radius:8px;
                        color:#e2e8f0; padding:10px 14px; font-size:14px; }
            QLineEdit:focus { border-color:#3b82f6; }
        """)
        self.inp.setFixedHeight(46)
        self.inp.returnPressed.connect(self._on_send)

        self._voice_btn = QPushButton("🎤")
        self._voice_btn.setFixedSize(46, 46)
        self._voice_btn.setToolTip("Hold to record voice")
        self._voice_btn.setStyleSheet(f"""
            QPushButton {{ background:#1e293b; color:white; border:1px solid #334155;
                           border-radius:8px; font-size:18px; }}
            QPushButton:hover {{ border-color:{ACCENT}; background:#1e3a5f; }}
        """)
        self._voice_btn.clicked.connect(self._on_voice)

        send_btn = QPushButton("Send")
        send_btn.setFixedSize(80, 46)
        send_btn.setStyleSheet(f"""
            QPushButton {{ background:{ACCENT}; color:white; border:none; border-radius:8px;
                           font-size:14px; font-weight:600; }}
            QPushButton:hover {{ background:#2563eb; }}
        """)
        send_btn.clicked.connect(self._on_send)

        inp_row.addWidget(self.inp, 1)
        inp_row.addWidget(self._voice_btn)
        inp_row.addWidget(send_btn)
        ml.addLayout(inp_row)

        root.addWidget(main, 1)

    # ── Voice ─────────────────────────────────────────────────
    def _on_voice(self):
        if not self._is_recording:
            self._is_recording = True
            self._voice_btn.setText('⏹')
            self._voice_btn.setToolTip('Click to stop recording')
            self._voice_btn.setStyleSheet(f"""
                QPushButton {{ background:{RED}; color:white; border:none;
                               border-radius:8px; font-size:18px; }}
                QPushButton:hover {{ background:#dc2626; }}
            """)
            self._voice_status.setText('🔴 Recording... click ⏹ to stop')

            self._voice_thread = VoiceThread()
            self._voice_thread.listening.connect(self._on_listening)
            self._voice_thread.text_ready.connect(self._on_voice_text)
            self._voice_thread.error.connect(self._on_voice_error)
            self._voice_thread.tick.connect(self._on_voice_tick)
            self._voice_thread.start()
        else:
            self._voice_status.setText('⏳ Transcribing...')
            self._voice_btn.setEnabled(False)
            if self._voice_thread:
                self._voice_thread.stop()

    @Slot()
    def _on_listening(self):
        self._voice_status.setText('🔴 Listening... click ⏹ to stop')

    @Slot(int)
    def _on_voice_tick(self, secs: int):
        self._voice_status.setText(f'🔴 Recording {secs}s... click ⏹ to stop')

    @Slot(str)
    def _on_voice_text(self, text: str):
        self._reset_voice_btn()
        self.inp.setText(text)
        self._voice_status.setText(f'✅ {text[:50]}{"..." if len(text)>50 else ""}')
        self._send_message(text)

    @Slot(str)
    def _on_voice_error(self, err: str):
        self._reset_voice_btn()
        self._voice_status.setText(err)
        self._add_bubble(f'⚠ Voice: {err}', False)

    def _reset_voice_btn(self):
        self._is_recording = False
        self._voice_btn.setEnabled(True)
        self._voice_btn.setText('🎤')
        self._voice_btn.setToolTip('Click to start recording')
        self._voice_btn.setStyleSheet(f"""
            QPushButton {{ background:#1e293b; color:white; border:1px solid #334155;
                           border-radius:8px; font-size:18px; }}
            QPushButton:hover {{ border-color:{ACCENT}; background:#1e3a5f; }}
        """)

    # ── Chat ──────────────────────────────────────────────────
    def refresh(self):
        from app.services.auth_service import get_current_user
        self._current_user = get_current_user()
        if not self._session_id:
            self._new_chat()

    def _new_chat(self):
        from app.services.auth_service import get_current_user
        from app.services.chat_service import create_session
        from app.db.session import get_db
        self._current_user = get_current_user()
        if not self._current_user: return
        with get_db() as db:
            session = create_session(db, self._current_user.id)
            self._session_id = session.id
        while self.msg_layout.count() > 1:
            item = self.msg_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        self._add_bubble(
            "👋 Hello! I'm your NexaBank AI Assistant.\n\n"
            "I can help you with:\n"
            "• 💰 Deposits & Withdrawals\n"
            "• 🏦 Account information & balance\n"
            "• 📋 Banking policies & fees\n"
            "• 🔒 Security & PIN help\n"
            "• 📊 Interest rates & limits\n\n"
            "💡 Try asking: 'What is my balance?' or 'Show my transactions'", False)

    def _add_bubble(self, text: str, is_user: bool):
        bubble = QLabel(text); bubble.setWordWrap(True)
        bubble.setTextInteractionFlags(Qt.TextSelectableByMouse)
        max_w = 560
        if is_user:
            bubble.setStyleSheet(f"background:{ACCENT}; color:white; padding:10px 14px; border-radius:12px; font-size:13px;")
            bubble.setMaximumWidth(max_w)
            row = QHBoxLayout(); row.addStretch(); row.addWidget(bubble)
        else:
            bubble.setStyleSheet(f"background:{PANEL}; color:{TEXT}; padding:10px 14px; border-radius:12px; border:1px solid #1e293b; font-size:13px;")
            bubble.setMaximumWidth(max_w)
            row = QHBoxLayout(); row.addWidget(bubble); row.addStretch()
        w = QWidget(); w.setStyleSheet("background:transparent;"); w.setLayout(row)
        self.msg_layout.insertWidget(self.msg_layout.count()-1, w)
        from PySide6.QtCore import QTimer
        QTimer.singleShot(50, lambda: self._scroll.verticalScrollBar().setValue(
            self._scroll.verticalScrollBar().maximum()))

    def _on_send(self):
        text = self.inp.text().strip()
        if not text: return
        self.inp.clear()
        self._send_message(text)

    def _send_message(self, text: str):
        if not self._session_id:
            self._new_chat()
        self._add_bubble(text, True)

        from app.services.auth_service import get_current_user
        from app.services.chat_service import add_message, get_session_history_for_llm
        from app.db.models import MessageRole
        from app.db.session import get_db
        user = self._current_user or get_current_user()
        if not user: return

        with get_db() as db:
            add_message(db, self._session_id, MessageRole.USER, text)
            history = get_session_history_for_llm(db, self._session_id)

        self._thinking = self._add_thinking()

        if self._rag_thread and self._rag_thread.isRunning():
            self._rag_thread.terminate()

        # Pass user_id so RAGThread can do DB lookups
        self._rag_thread = RAGThread(text, history, user_id=user.id)
        self._rag_thread.result_ready.connect(self._on_response)
        self._rag_thread.start()

    def _add_thinking(self):
        lbl = QLabel("⏳ Thinking...")
        lbl.setStyleSheet(f"background:{PANEL}; color:{MUTED}; padding:10px 14px; border-radius:12px; font-size:13px;")
        self.msg_layout.insertWidget(self.msg_layout.count()-1, lbl)
        return lbl

    @Slot(str)
    def _on_response(self, response: str):
        if self._thinking:
            self._thinking.deleteLater()
            self._thinking = None
        self._add_bubble(response, False)

        from app.services.auth_service import get_current_user
        from app.services.chat_service import add_message
        from app.db.models import MessageRole
        from app.db.session import get_db
        user = self._current_user or get_current_user()
        if user and self._session_id:
            with get_db() as db:
                add_message(db, self._session_id, MessageRole.ASSISTANT, response)

    def _on_file(self, path: str):
        from app.services.auth_service import get_current_user
        from app.services.upload_service import save_upload
        from app.db.session import get_db
        import os
        user = self._current_user or get_current_user()
        if not user: return
        filename = os.path.basename(path)
        with get_db() as db:
            ok, msg, doc = save_upload(db, user.id, filename, path)
        if ok:
            self._add_bubble(f"📄 '{filename}' uploaded! Ingesting...", False)
            threading.Thread(target=self._ingest, args=(doc.id, user.id), daemon=True).start()
        else:
            self._add_bubble(f"❌ Upload failed: {msg}", False)

    def _ingest(self, doc_id, user_id):
        from app.services.upload_service import ingest_document
        from app.db.session import get_db
        with get_db() as db:
            ingest_document(db, doc_id, user_id)
        from PySide6.QtCore import QMetaObject, Q_ARG
        QMetaObject.invokeMethod(self, "_on_ingest_done", Qt.QueuedConnection, Q_ARG(str, "✅ Document ingested and ready for AI search!"))

    @Slot(str)
    def _on_ingest_done(self, msg: str):
        self._add_bubble(msg, False)