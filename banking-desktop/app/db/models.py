import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, ForeignKey, Text, Enum as SAEnum
from sqlalchemy.orm import relationship
from sqlalchemy.types import TypeDecorator, CHAR
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
import enum
from app.db.session import Base

class GUID(TypeDecorator):
    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        else:
            return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return str(value)
        else:
            if not isinstance(value, uuid.UUID):
                return str(uuid.UUID(str(value)))
            else:
                return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        else:
            if not isinstance(value, uuid.UUID):
                return uuid.UUID(str(value))
            else:
                return value

def UUID(as_uuid=True):
    return GUID()

PGVECTOR_AVAILABLE = False
try:
    from pgvector.sqlalchemy import Vector
    _VCOL = lambda: Column(Vector(768), nullable=True)
    PGVECTOR_AVAILABLE = True
except ImportError:
    _VCOL = lambda: Column(Text, nullable=True)

class AccountType(str, enum.Enum):
    CHECKING="CHECKING"; SAVINGS="SAVINGS"; BUSINESS="BUSINESS"

class TransactionType(str, enum.Enum):
    DEPOSIT="DEPOSIT"; WITHDRAWAL="WITHDRAWAL"; TRANSFER="TRANSFER"

class MessageRole(str, enum.Enum):
    USER="USER"; ASSISTANT="ASSISTANT"; SYSTEM="SYSTEM"

class FlowStatus(str, enum.Enum):
    ACTIVE="ACTIVE"; COMPLETED="COMPLETED"; CANCELLED="CANCELLED"

class LoanStatus(str, enum.Enum):
    PENDING="PENDING"; ACTIVE="ACTIVE"; CLOSED="CLOSED"; DEFAULTED="DEFAULTED"

class TransferStatus(str, enum.Enum):
    COMPLETED="COMPLETED"; FAILED="FAILED"; PENDING="PENDING"

class User(Base):
    __tablename__ = "users"
    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email         = Column(String(255), unique=True, nullable=False, index=True)
    full_name     = Column(String(255), nullable=False)
    password_hash = Column(String(255), nullable=False)
    phone         = Column(String(30), nullable=True)
    is_active     = Column(Boolean, default=True)
    is_admin      = Column(Boolean, default=False)
    created_at    = Column(DateTime, default=datetime.utcnow)
    updated_at    = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    accounts      = relationship("Account", back_populates="user", cascade="all, delete-orphan")
    chat_sessions = relationship("ChatSession", back_populates="user", cascade="all, delete-orphan")
    ai_flows      = relationship("AIFlow", back_populates="user", cascade="all, delete-orphan")
    uploaded_docs = relationship("UploadedDocument", back_populates="user", cascade="all, delete-orphan")
    pin           = relationship("UserPIN", back_populates="user", uselist=False, cascade="all, delete-orphan")
    loans         = relationship("Loan", back_populates="user", cascade="all, delete-orphan")
    def __repr__(self): return f"<User {self.email}>"

class UserPIN(Base):
    __tablename__ = "user_pins"
    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id         = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    pin_hash        = Column(String(255), nullable=False)
    failed_attempts = Column(Integer, default=0)
    locked_until    = Column(DateTime, nullable=True)
    created_at      = Column(DateTime, default=datetime.utcnow)
    updated_at      = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user = relationship("User", back_populates="pin")

class Account(Base):
    __tablename__ = "accounts"
    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id        = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    account_number = Column(String(20), unique=True, nullable=False, index=True)
    account_type   = Column(SAEnum(AccountType), nullable=False)
    balance        = Column(Float, default=0.0, nullable=False)
    currency       = Column(String(3), default="USD")
    is_active      = Column(Boolean, default=True)
    created_at     = Column(DateTime, default=datetime.utcnow)
    updated_at     = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    holder_name    = Column(String(255), nullable=True)
    photo_path     = Column(String(512), nullable=True)
    dob            = Column(String(20),  nullable=True)
    nid            = Column(String(100), nullable=True)
    phone          = Column(String(30),  nullable=True)
    address        = Column(Text,        nullable=True)
    occupation     = Column(String(100), nullable=True)
    interest_rate  = Column(Float, default=0.0, nullable=True)
    interest_rate  = Column(Float, default=0.0, nullable=True)
    user         = relationship("User", back_populates="accounts")
    transactions = relationship("Transaction", back_populates="account", cascade="all, delete-orphan")
    sent_transfers = relationship("Transfer", foreign_keys="Transfer.sender_account_id", back_populates="sender_account")
    recv_transfers = relationship("Transfer", foreign_keys="Transfer.receiver_account_id", back_populates="receiver_account")

class Transaction(Base):
    __tablename__ = "transactions"
    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id       = Column(UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False)
    transaction_type = Column(SAEnum(TransactionType), nullable=False)
    amount           = Column(Float, nullable=False)
    balance_after    = Column(Float, nullable=False)
    description      = Column(String(500), nullable=True)
    reference_id     = Column(String(100), nullable=True)
    created_at       = Column(DateTime, default=datetime.utcnow)
    account = relationship("Account", back_populates="transactions")

class ChatSession(Base):
    __tablename__ = "chat_sessions"
    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id    = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title      = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user     = relationship("User", back_populates="chat_sessions")
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")

class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False)
    role       = Column(SAEnum(MessageRole), nullable=False)
    content    = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    session = relationship("ChatSession", back_populates="messages")

class AIFlow(Base):
    __tablename__ = "ai_flows"
    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id      = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    flow_type    = Column(String(50), nullable=False)
    current_step = Column(String(100), nullable=True)
    status       = Column(SAEnum(FlowStatus), default=FlowStatus.ACTIVE)
    state_json   = Column(Text, nullable=True)
    created_at   = Column(DateTime, default=datetime.utcnow)
    updated_at   = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user = relationship("User", back_populates="ai_flows")

class UploadedDocument(Base):
    __tablename__ = "uploaded_documents"
    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id       = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    filename      = Column(String(255), nullable=False)
    file_path     = Column(String(512), nullable=False)
    file_size     = Column(Integer, nullable=True)
    status        = Column(String(50), default="pending")
    error_message = Column(Text, nullable=True)
    created_at    = Column(DateTime, default=datetime.utcnow)
    user   = relationship("User", back_populates="uploaded_docs")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")

class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("uploaded_documents.id", ondelete="CASCADE"), nullable=False)
    user_id     = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    chunk_index = Column(Integer, nullable=False)
    content     = Column(Text, nullable=False)
    embedding   = _VCOL()
    created_at  = Column(DateTime, default=datetime.utcnow)
    document = relationship("UploadedDocument", back_populates="chunks")

class Loan(Base):
    __tablename__ = "loans"
    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id             = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    principal           = Column(Float, nullable=False)
    outstanding_balance = Column(Float, nullable=False)
    annual_rate         = Column(Float, nullable=False)
    tenure_months       = Column(Integer, nullable=False)
    emi_amount          = Column(Float, nullable=False)
    purpose             = Column(String(255), nullable=True)
    status              = Column(SAEnum(LoanStatus), default=LoanStatus.PENDING)
    applied_at          = Column(DateTime, default=datetime.utcnow)
    start_date          = Column(DateTime, nullable=True)
    next_due_date       = Column(DateTime, nullable=True)
    closed_at           = Column(DateTime, nullable=True)
    user       = relationship("User", back_populates="loans")
    repayments = relationship("LoanRepayment", back_populates="loan", cascade="all, delete-orphan")

class LoanRepayment(Base):
    __tablename__ = "loan_repayments"
    id      = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    loan_id = Column(UUID(as_uuid=True), ForeignKey("loans.id", ondelete="CASCADE"), nullable=False)
    amount  = Column(Float, nullable=False)
    paid_at = Column(DateTime, default=datetime.utcnow)
    loan    = relationship("Loan", back_populates="repayments")

class Transfer(Base):
    __tablename__ = "transfers"
    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sender_account_id   = Column(UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False)
    receiver_account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False)
    amount              = Column(Float, nullable=False)
    note                = Column(String(255), nullable=True)
    status              = Column(SAEnum(TransferStatus), default=TransferStatus.COMPLETED)
    created_at          = Column(DateTime, default=datetime.utcnow)
    sender_account   = relationship("Account", foreign_keys=[sender_account_id], back_populates="sent_transfers")
    receiver_account = relationship("Account", foreign_keys=[receiver_account_id], back_populates="recv_transfers")

