import threading
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QLineEdit, QScrollArea)
from PySide6.QtCore import Qt, Slot, Signal, QThread
from PySide6.QtGui import QFont

BG="#0b0f1a"; PANEL="#111827"; ACCENT="#3b82f6"; TEXT="#e2e8f0"; MUTED="#64748b"
RED="#ef4444"; GREEN="#22c55e"


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
            import tempfile, os, wave
            from faster_whisper import WhisperModel
            self._running = True
            sample_rate = 16000
            chunk_secs = 0.1
            chunk_frames = int(sample_rate * chunk_secs)
            all_frames = []
            elapsed = 0
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
            tmp = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
            tmp_path = tmp.name
            tmp.close()
            with wave.open(tmp_path, 'wb') as wf:
                wf.setnchannels(1); wf.setsampwidth(2)
                wf.setframerate(sample_rate)
                wf.writeframes(audio.tobytes())
            model = WhisperModel('tiny', device='cpu', compute_type='int8')
            segments, _ = model.transcribe(tmp_path, language='en')
            text = ' '.join(s.text for s in segments).strip()
            try: os.unlink(tmp_path)
            except: pass
            if text: self.text_ready.emit(text)
            else: self.error.emit('Could not hear anything.')
        except ImportError:
            self.error.emit('Run: pip install faster-whisper sounddevice')
        except Exception as e:
            self.error.emit(f'Voice error: {str(e)}')


def _detect_db_intent(query: str):
    import re
    q = query.lower()

    acc_match = re.search(r'\b(\d{8,20})\b', query)

    # Transaction/Statement — account number সহ
    if acc_match and any(w in q for w in [
        "transaction", "transactions", "statement", "statment",
        "statemen", "history", "payment", "debit", "credit", "last", "activity"
    ]):
        return {"type": "transactions", "account_number": acc_match.group(1)}

    # শুধু account number → details
    if acc_match:
        return {"type": "balance", "account_number": acc_match.group(1)}

    # Interest rate
    if any(w in q for w in ["interest rate", "interest rates", "what is interest", "rate"]):
        return {"type": "interest_rate"}

    # শুধু numbers
    if any(w in q for w in ["show account number", "account number list", "account numbers",
                             "number list", "total account number", "all account number"]):
        return {"type": "list_numbers"}

    # শুধু names
    if any(w in q for w in ["show account name", "account name list", "account names",
                             "name list", "holder name", "all names", "account holder name"]):
        return {"type": "list_names"}

    # শুধু balances
    if any(w in q for w in ["show balance", "balance list", "all balance",
                             "show all balance", "account balance list"]):
        return {"type": "list_balances"}

    # Full statement — no account number
    if any(w in q for w in ["full statement", "full statment", "statement", "statment"]):
        return {"type": "transactions", "account_number": None}

    # সব account
    if any(w in q for w in [
        "my account", "my accounts", "show account", "list account",
        "account list", "all account", "show my", "total account",
        "account total", "all accounts", "my balance",
        "account details", "account info", "account holder", "holder list"
    ]):
        return {"type": "balance", "account_number": None}

    # Transaction — no account number
    if any(w in q for w in ["transaction", "history", "last", "recent", "payment"]):
        return {"type": "transactions", "account_number": None}

    # Loan
    if any(w in q for w in ["my loan", "loan status", "my emi"]):
        return {"type": "loan"}

    # Deposit execution
    import re as _re2
    dep = _re2.match(r"deposit\s+(\d{8,20})\s+([\d.]+)\s*(.*)", q.strip())
    if dep:
        return {"type": "do_deposit", "account_number": dep.group(1), "amount": float(dep.group(2)), "description": dep.group(3).strip() or "Deposit"}

    # Transfer execution
    tr = _re2.match(r"transfer\s+(\d{8,20})\s+(\d{8,20})\s+([\d.]+)\s*(.*)", q.strip())
    if tr:
        return {"type": "do_transfer", "from_acc": tr.group(1), "to_acc": tr.group(2), "amount": float(tr.group(3)), "description": tr.group(4).strip() or "Transfer"}

    # Show deposit guide - only if asking how
    if any(w in q for w in ["add money", "add fund"]):
        return {"type": "action_deposit"}

    # Show transfer guide - only if asking how
    if any(w in q for w in ["send money", "send to"]):
        return {"type": "action_transfer"}

    # Loan apply
    if any(w in q for w in ["apply loan", "loan apply", "take loan", "need loan", "borrow"]):
        return {"type": "action_loan"}

    # Open account
    if any(w in q for w in ["open account", "create account", "new account", "account open"]):
        return {"type": "action_open_account"}

    return None


def _handle_db_intent(intent: dict, user_id) -> str:
    try:
        from app.db.session import get_db
        from app.db.models import Account, Transaction, TransactionType

        with get_db() as db:

            # Interest Rate
            if intent["type"] == "interest_rate":
                accounts = db.query(Account).filter(
                    Account.user_id == user_id,
                    Account.is_active == True
                ).all()
                lines = ["NexaBank Interest Rates", ""]
                shown = set()
                for a in accounts:
                    atype = a.account_type.value if a.account_type else "N/A"
                    if atype not in shown:
                        rate = getattr(a, "interest_rate", None)
                        if rate:
                            lines.append("  " + atype + " : " + str(rate) + "% per year")
                        shown.add(atype)
                if len(lines) == 2:
                    lines.append("  CHECKING : 5% per year")
                    lines.append("  SAVINGS  : 7% per year")
                    lines.append("  BUSINESS : 9% per year")
                return "\n".join(lines)

            # List numbers only
            elif intent["type"] == "list_numbers":
                accounts = db.query(Account).filter(
                    Account.user_id == user_id,
                    Account.is_active == True
                ).all()
                if not accounts:
                    return "No active accounts found."
                lines = ["Account Numbers (Total: " + str(len(accounts)) + ")", ""]
                for i, a in enumerate(accounts, 1):
                    lines.append("  " + str(i) + ". " + a.account_number)
                return "\n".join(lines)

            # List names only
            elif intent["type"] == "list_names":
                accounts = db.query(Account).filter(
                    Account.user_id == user_id,
                    Account.is_active == True
                ).all()
                if not accounts:
                    return "No active accounts found."
                lines = ["Account Holder Names (Total: " + str(len(accounts)) + ")", ""]
                for i, a in enumerate(accounts, 1):
                    name = a.holder_name or "N/A"
                    lines.append("  " + str(i) + ". " + name)
                return "\n".join(lines)

            # List balances only
            elif intent["type"] == "list_balances":
                accounts = db.query(Account).filter(
                    Account.user_id == user_id,
                    Account.is_active == True
                ).all()
                if not accounts:
                    return "No active accounts found."
                total = sum(float(a.balance) for a in accounts)
                lines = ["Account Balances (Total: " + str(len(accounts)) + ")", ""]
                for a in accounts:
                    name = a.holder_name or "N/A"
                    curr = a.currency or "BDT"
                    bal = "{:,.2f}".format(float(a.balance))
                    lines.append("  " + a.account_number + "  ->  " + curr + " " + bal + "  (" + name + ")")
                lines.append("")
                lines.append("  Total Balance : BDT " + "{:,.2f}".format(total))
                return "\n".join(lines)

            # Name search
            elif intent["type"] == "search_by_name":
                name = intent.get("name", "").strip()
                accounts = db.query(Account).filter(
                    Account.user_id == user_id,
                    Account.holder_name.ilike("%" + name + "%")
                ).all()
                if accounts:
                    lines = ["Search Results for '" + name + "'", ""]
                    for a in accounts:
                        status = "Active" if a.is_active else "Inactive"
                        atype = a.account_type.value if a.account_type else "N/A"
                        curr = a.currency or "BDT"
                        bal = "{:,.2f}".format(float(a.balance))
                        lines.append("  Account No : " + a.account_number)
                        lines.append("  Name       : " + (a.holder_name or "N/A"))
                        lines.append("  Type       : " + atype)
                        lines.append("  Balance    : " + curr + " " + bal)
                        lines.append("")
                    return "\n".join(lines)
                else:
                    return ("No account found for '" + name + "' under your profile.\n\n"
                            "For security reasons, you can only view your own accounts.")

            # Balance / Account details
            elif intent["type"] == "balance":
                acc_no = intent.get("account_number")
                if acc_no:
                    account = db.query(Account).filter(
                        Account.account_number == acc_no,
                        Account.user_id == user_id
                    ).first()
                    if account:
                        status = "Active" if account.is_active else "Inactive"
                        atype = account.account_type.value if account.account_type else "N/A"
                        curr = account.currency or "BDT"
                        bal = "{:,.2f}".format(float(account.balance))
                        return ("Account Details\n\n"
                                "  Account No   : " + account.account_number + "\n"
                                "  Account Name : " + (account.holder_name or "N/A") + "\n"
                                "  Type         : " + atype + "\n"
                                "  Balance      : " + curr + " " + bal + "\n"
                                "  Status       : " + status)
                    else:
                        return "Account not found or you do not have access to this account."
                else:
                    accounts = db.query(Account).filter(
                        Account.user_id == user_id,
                        Account.is_active == True
                    ).all()
                    if not accounts:
                        return "No active accounts found."
                    lines = ["Your Accounts (Total: " + str(len(accounts)) + ")", ""]
                    for a in accounts:
                        atype = a.account_type.value if a.account_type else "N/A"
                        curr = a.currency or "BDT"
                        bal = "{:,.2f}".format(float(a.balance))
                        lines.append("  Account No : " + a.account_number)
                        lines.append("  Name       : " + (a.holder_name or "N/A"))
                        lines.append("  Type       : " + atype)
                        lines.append("  Balance    : " + curr + " " + bal)
                        lines.append("")
                    return "\n".join(lines)

            # Transactions
            elif intent["type"] == "transactions":
                acc_no = intent.get("account_number")
                if acc_no:
                    account = db.query(Account).filter(
                        Account.account_number == acc_no,
                        Account.user_id == user_id
                    ).first()
                    if not account:
                        return "Account not found or you do not have access to this account."
                    txns = (db.query(Transaction)
                            .filter(Transaction.account_id == account.id)
                            .order_by(Transaction.created_at.desc())
                            .limit(10).all())
                else:
                    accounts = db.query(Account).filter(Account.user_id == user_id).all()
                    acc_ids = [a.id for a in accounts]
                    txns = (db.query(Transaction)
                            .filter(Transaction.account_id.in_(acc_ids))
                            .order_by(Transaction.created_at.desc())
                            .limit(10).all())
                if not txns:
                    return "No recent transactions found."
                lines = ["Last 10 Transactions", ""]
                for t in txns:
                    arrow = "+" if t.transaction_type == TransactionType.DEPOSIT else "-"
                    date = t.created_at.strftime("%d %b %Y %H:%M")
                    amt = "{:,.2f}".format(float(t.amount))
                    desc = t.description or ""
                    lines.append("  " + arrow + " " + amt + "  |  " + t.transaction_type.value + "  |  " + date + "  |  " + desc)
                return "\n".join(lines)

            # Loan
            elif intent["type"] == "loan":
                try:
                    from app.db.models import Loan
                    loans = (db.query(Loan)
                             .filter(Loan.user_id == user_id)
                             .order_by(Loan.applied_at.desc()).all())
                    if not loans:
                        return "You have no loans at the moment."
                    lines = ["Your Loans", ""]
                    for l in loans:
                        status = l.status.value if l.status else "N/A"
                        lines.append("  Principal   : " + "{:,.2f}".format(float(l.principal)))
                        lines.append("  Outstanding : " + "{:,.2f}".format(float(l.outstanding_balance)))
                        lines.append("  EMI/month   : " + "{:,.2f}".format(float(l.emi_amount)))
                        lines.append("  Status      : " + status)
                        lines.append("")
                    return "\n".join(lines)
                except Exception:
                    return "Loan information is not available right now."

            # Do deposit
            elif intent["type"] == "do_deposit":
                acc_no = intent["account_number"]
                amount = intent["amount"]
                desc = intent["description"]
                account = db.query(Account).filter(Account.account_number == acc_no, Account.user_id == user_id).first()
                if not account:
                    return "Account not found or not yours."
                account.balance = float(account.balance) + amount
                from datetime import datetime
                from app.db.models import Transaction, TransactionType
                import uuid
                db.add(Transaction(id=uuid.uuid4(), account_id=account.id, transaction_type=TransactionType.DEPOSIT, amount=amount, description=desc, created_at=datetime.now()))
                db.commit()
                curr = account.currency or "BDT"
                msg = "Deposit Successful!\n\n"
                msg += "  Account : " + acc_no + "\n"
                msg += "  Name    : " + (account.holder_name or "N/A") + "\n"
                msg += "  Amount  : " + curr + " " + "{:,.2f}".format(amount) + "\n"
                msg += "  Balance : " + curr + " " + "{:,.2f}".format(float(account.balance)) + "\n"
                msg += "  Note    : " + desc
                return msg

            # Do transfer
            elif intent["type"] == "do_transfer":
                from_acc_no = intent["from_acc"]
                to_acc_no = intent["to_acc"]
                amount = intent["amount"]
                from_acc = db.query(Account).filter(Account.account_number == from_acc_no, Account.user_id == user_id).first()
                to_acc = db.query(Account).filter(Account.account_number == to_acc_no).first()
                if not from_acc:
                    return "From account not found or not yours."
                if not to_acc:
                    return "Destination account " + to_acc_no + " not found."
                if float(from_acc.balance) < amount:
                    return "Insufficient balance. Your balance: " + (from_acc.currency or "BDT") + " " + "{:,.2f}".format(float(from_acc.balance))
                from_acc.balance = float(from_acc.balance) - amount
                to_acc.balance = float(to_acc.balance) + amount
                from datetime import datetime
                from app.db.models import Transaction, TransactionType
                import uuid
                db.add(Transaction(id=uuid.uuid4(), account_id=from_acc.id, transaction_type=TransactionType.WITHDRAWAL, amount=amount, description="Transfer to " + to_acc_no, created_at=datetime.now()))
                db.add(Transaction(id=uuid.uuid4(), account_id=to_acc.id, transaction_type=TransactionType.DEPOSIT, amount=amount, description="Transfer from " + from_acc_no, created_at=datetime.now()))
                db.commit()
                curr = from_acc.currency or "BDT"
                msg = "Transfer Successful!\n\n"
                msg += "  From    : " + from_acc_no + " (" + (from_acc.holder_name or "N/A") + ")\n"
                msg += "  To      : " + to_acc_no + " (" + (to_acc.holder_name or "N/A") + ")\n"
                msg += "  Amount  : " + curr + " " + "{:,.2f}".format(amount) + "\n"
                msg += "  Balance : " + curr + " " + "{:,.2f}".format(float(from_acc.balance))
                return msg

            # Deposit guide
            elif intent["type"] == "action_deposit":
                accounts = db.query(Account).filter(Account.user_id == user_id, Account.is_active == True).all()
                lines = ["To deposit money, type:", "", "  deposit <account_number> <amount> <note>", "", "Example:", "  deposit 580455564829 5000 salary", "", "Your Accounts:"]
                for a in accounts:
                    lines.append("  " + a.account_number + "  " + (a.holder_name or "") + "  (BDT " + "{:,.2f}".format(float(a.balance)) + ")")
                return "\n".join(lines)

            # Transfer guide
            elif intent["type"] == "action_transfer":
                accounts = db.query(Account).filter(Account.user_id == user_id, Account.is_active == True).all()
                lines = ["To transfer money, type:", "", "  transfer <from_account> <to_account> <amount>", "", "Example:", "  transfer 580455564829 856701141261 1000", "", "Your Accounts:"]
                for a in accounts:
                    lines.append("  " + a.account_number + "  " + (a.holder_name or "") + "  (BDT " + "{:,.2f}".format(float(a.balance)) + ")")
                return "\n".join(lines)

            # Loan apply
            elif intent["type"] == "action_loan":
                return "To apply for a loan:\n\n  Reply: apply loan <amount>\n  Example: apply loan 50000\n\nOr go to Loan Calculator in the left sidebar."

            # Open account
            elif intent["type"] == "action_open_account":
                return "To open a new account:\n\n  Documents needed:\n  - National ID / Passport\n  - Recent photo\n  - Address proof\n  - Minimum deposit BDT 500\n\n  Account Types:\n  - SAVINGS  : 7% per year\n  - CHECKING : 5% per year\n  - BUSINESS : 9% per year"

    except Exception as e:
        return "Could not fetch data: " + str(e)

    return None


class RAGThread(QThread):
    result_ready = Signal(str)

    def __init__(self, query: str, history: list, user_id=None):
        super().__init__()
        self.query = query
        self.history = history
        self.user_id = user_id

    def run(self):
        try:
            if self.user_id:
                intent = _detect_db_intent(self.query)
                if intent:
                    answer = _handle_db_intent(intent, self.user_id)
                    if answer:
                        self.result_ready.emit(answer)
                        return

            from app.db.session import get_db
            from app.llm.ollama_client import get_embedding, chat, is_ollama_available
            from app.db.models import DocumentChunk
            from app.llm.prompts import build_chatbot_system

            if not is_ollama_available():
                self.result_ready.emit("Ollama is not running. Please start Ollama.")
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
                system += "\n\nNexaBank policy context:\n" + rag_context

            response = chat(self.history, system=system, temperature=0.5)
            self.result_ready.emit(response)

        except Exception as e:
            self.result_ready.emit("AI error: " + str(e))


class ChatbotScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background-color:" + BG + ";")
        self._session_id = None
        self._thinking = None
        self._voice_thread = None
        self._rag_thread = None
        self._is_recording = False
        self._current_user = None
        self._build()

    def _build(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        sidebar = QFrame()
        sidebar.setFixedWidth(220)
        sidebar.setStyleSheet("QFrame { background:#0d1117; border-right:1px solid #1e293b; }")
        sl = QVBoxLayout(sidebar)
        sl.setContentsMargins(12, 16, 12, 16)
        sl.setSpacing(8)
        sl.addWidget(QLabel("Conversations"))
        new_btn = QPushButton("+ New Chat")
        new_btn.setStyleSheet(
            "QPushButton { background:" + ACCENT + "; color:white; border:none; border-radius:8px; padding:8px; font-size:13px; }"
            "QPushButton:hover { background:#2563eb; }"
        )
        new_btn.clicked.connect(self._new_chat)
        sl.addWidget(new_btn)
        from app.ui.widgets.upload_dropzone import UploadDropzone
        dropzone = UploadDropzone()
        dropzone.file_dropped.connect(self._on_file)
        sl.addWidget(dropzone)
        sl.addStretch()
        self._voice_status = QLabel("")
        self._voice_status.setWordWrap(True)
        self._voice_status.setStyleSheet("color:" + MUTED + "; font-size:10px; background:transparent;")
        sl.addWidget(self._voice_status)
        root.addWidget(sidebar)

        main = QWidget()
        main.setStyleSheet("background:" + BG + ";")
        ml = QVBoxLayout(main)
        ml.setContentsMargins(24, 20, 24, 20)
        ml.setSpacing(12)

        hdr_row = QHBoxLayout()
        header = QLabel("NexaBank AI Assistant")
        header.setFont(QFont("Segoe UI", 16, QFont.Bold))
        header.setStyleSheet("color:" + TEXT + "; background:transparent;")
        hdr_row.addWidget(header)
        hdr_row.addStretch()
        rag_badge = QLabel("Policy RAG Active")
        rag_badge.setStyleSheet(
            "color:" + GREEN + "; font-size:10px; background:#22c55e22; "
            "border:1px solid #22c55e44; border-radius:6px; padding:3px 8px;"
        )
        hdr_row.addWidget(rag_badge)
        ml.addLayout(hdr_row)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border:none; background:transparent; }")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.msg_w = QWidget()
        self.msg_w.setStyleSheet("background:transparent;")
        self.msg_layout = QVBoxLayout(self.msg_w)
        self.msg_layout.setSpacing(8)
        self.msg_layout.setContentsMargins(0, 0, 0, 0)
        self.msg_layout.addStretch()
        scroll.setWidget(self.msg_w)
        self._scroll = scroll
        ml.addWidget(scroll, 1)

        qp_row = QHBoxLayout()
        qp_row.setSpacing(8)
        prompts = [
            ("Deposit",       "How do I make a deposit?"),
            ("Open Account",  "How do I open a new account?"),
            ("PIN Policy",    "What is the PIN policy?"),
            ("Withdrawal",    "What is the withdrawal limit?"),
            ("Interest Rate", "What are the interest rates?"),
        ]
        for label, text in prompts:
            qb = QPushButton(label)
            qb.setStyleSheet(
                "QPushButton { background:" + PANEL + "; color:" + MUTED + "; border:1px solid #1e293b; border-radius:8px; padding:5px 10px; font-size:11px; }"
                "QPushButton:hover { border-color:" + ACCENT + "; color:" + TEXT + "; }"
            )
            qb.clicked.connect(lambda _, t=text: self._send_message(t))
            qp_row.addWidget(qb)
        qp_row.addStretch()
        ml.addLayout(qp_row)

        inp_row = QHBoxLayout()
        inp_row.setSpacing(8)
        self.inp = QLineEdit()
        self.inp.setPlaceholderText("Ask me anything about NexaBank...")
        self.inp.setStyleSheet(
            "QLineEdit { background:#1e293b; border:1px solid #334155; border-radius:8px; "
            "color:#e2e8f0; padding:10px 14px; font-size:14px; }"
            "QLineEdit:focus { border-color:#3b82f6; }"
        )
        self.inp.setFixedHeight(46)
        self.inp.returnPressed.connect(self._on_send)

        self._voice_btn = QPushButton("🎤")
        self._voice_btn.setFixedSize(46, 46)
        self._voice_btn.setStyleSheet(
            "QPushButton { background:#1e293b; color:white; border:1px solid #334155; border-radius:8px; font-size:18px; }"
            "QPushButton:hover { border-color:" + ACCENT + "; background:#1e3a5f; }"
        )
        self._voice_btn.clicked.connect(self._on_voice)

        send_btn = QPushButton("Send")
        send_btn.setFixedSize(80, 46)
        send_btn.setStyleSheet(
            "QPushButton { background:" + ACCENT + "; color:white; border:none; border-radius:8px; font-size:14px; font-weight:600; }"
            "QPushButton:hover { background:#2563eb; }"
        )
        send_btn.clicked.connect(self._on_send)

        inp_row.addWidget(self.inp, 1)
        inp_row.addWidget(self._voice_btn)
        inp_row.addWidget(send_btn)
        ml.addLayout(inp_row)
        root.addWidget(main, 1)

    def _on_voice(self):
        if not self._is_recording:
            self._is_recording = True
            self._voice_btn.setText('⏹')
            self._voice_btn.setStyleSheet(
                "QPushButton { background:" + RED + "; color:white; border:none; border-radius:8px; font-size:18px; }"
            )
            self._voice_status.setText('Recording... click to stop')
            self._voice_thread = VoiceThread()
            self._voice_thread.listening.connect(self._on_listening)
            self._voice_thread.text_ready.connect(self._on_voice_text)
            self._voice_thread.error.connect(self._on_voice_error)
            self._voice_thread.tick.connect(self._on_voice_tick)
            self._voice_thread.start()
        else:
            self._voice_status.setText('Transcribing...')
            self._voice_btn.setEnabled(False)
            if self._voice_thread:
                self._voice_thread.stop()

    @Slot()
    def _on_listening(self):
        self._voice_status.setText('Listening... click to stop')

    @Slot(int)
    def _on_voice_tick(self, secs: int):
        self._voice_status.setText('Recording ' + str(secs) + 's...')

    @Slot(str)
    def _on_voice_text(self, text: str):
        self._reset_voice_btn()
        self.inp.setText(text)
        self._send_message(text)

    @Slot(str)
    def _on_voice_error(self, err: str):
        self._reset_voice_btn()
        self._add_bubble('Voice error: ' + err, False)

    def _reset_voice_btn(self):
        self._is_recording = False
        self._voice_btn.setEnabled(True)
        self._voice_btn.setText('🎤')
        self._voice_btn.setStyleSheet(
            "QPushButton { background:#1e293b; color:white; border:1px solid #334155; border-radius:8px; font-size:18px; }"
            "QPushButton:hover { border-color:" + ACCENT + "; background:#1e3a5f; }"
        )

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
        if not self._current_user:
            return
        with get_db() as db:
            session = create_session(db, self._current_user.id)
            self._session_id = session.id
        while self.msg_layout.count() > 1:
            item = self.msg_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._add_bubble(
            "Hello! I'm your NexaBank AI Assistant.\n\n"
            "I can help you with:\n"
            "  My balance / account info\n"
            "  My transaction history\n"
            "  My loan status\n"
            "  Interest rates\n"
            "  Banking policies\n\n"
            "Try: 'my accounts' or 'show my balance'", False)

    def _add_bubble(self, text: str, is_user: bool):
        bubble = QLabel(text)
        bubble.setWordWrap(True)
        bubble.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
        bubble.setCursor(Qt.IBeamCursor)
        max_w = 580
        if is_user:
            bubble.setStyleSheet(
                "background:" + ACCENT + "; color:white; padding:10px 14px; "
                "border-radius:12px; font-size:13px;"
            )
            bubble.setMaximumWidth(max_w)
            row = QHBoxLayout()
            row.addStretch()
            row.addWidget(bubble)
        else:
            bubble.setStyleSheet(
                "background:" + PANEL + "; color:" + TEXT + "; padding:10px 14px; "
                "border-radius:12px; border:1px solid #1e293b; font-size:13px;"
            )
            bubble.setMaximumWidth(max_w)
            row = QHBoxLayout()
            row.addWidget(bubble)
            row.addStretch()
        w = QWidget()
        w.setStyleSheet("background:transparent;")
        w.setLayout(row)
        self.msg_layout.insertWidget(self.msg_layout.count() - 1, w)
        from PySide6.QtCore import QTimer
        QTimer.singleShot(50, lambda: self._scroll.verticalScrollBar().setValue(
            self._scroll.verticalScrollBar().maximum()))

    def _on_send(self):
        text = self.inp.text().strip()
        if not text:
            return
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
        if not user:
            return

        with get_db() as db:
            add_message(db, self._session_id, MessageRole.USER, text)
            history = get_session_history_for_llm(db, self._session_id)

        self._thinking = self._add_thinking()
        if self._rag_thread and self._rag_thread.isRunning():
            self._rag_thread.terminate()
        self._rag_thread = RAGThread(text, history, user_id=user.id)
        self._rag_thread.result_ready.connect(self._on_response)
        self._rag_thread.start()

    def _add_thinking(self):
        lbl = QLabel("Thinking...")
        lbl.setStyleSheet(
            "background:" + PANEL + "; color:" + MUTED + "; "
            "padding:10px 14px; border-radius:12px; font-size:13px;"
        )
        self.msg_layout.insertWidget(self.msg_layout.count() - 1, lbl)
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
        if not user:
            return
        filename = os.path.basename(path)
        with get_db() as db:
            ok, msg, doc = save_upload(db, user.id, filename, path)
        if ok:
            self._add_bubble("'" + filename + "' uploaded! Ingesting...", False)
            threading.Thread(target=self._ingest, args=(doc.id, user.id), daemon=True).start()
        else:
            self._add_bubble("Upload failed: " + msg, False)

    def _ingest(self, doc_id, user_id):
        from app.services.upload_service import ingest_document
        from app.db.session import get_db
        with get_db() as db:
            ingest_document(db, doc_id, user_id)
        from PySide6.QtCore import QMetaObject, Q_ARG
        QMetaObject.invokeMethod(self, "_on_ingest_done", Qt.QueuedConnection,
                                 Q_ARG(str, "Document ingested and ready for AI search!"))

    @Slot(str)
    def _on_ingest_done(self, msg: str):
        self._add_bubble(msg, False)