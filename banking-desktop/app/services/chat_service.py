from uuid import UUID
from sqlalchemy.orm import Session
from app.db.models import ChatSession, ChatMessage, MessageRole
import logging
_log = logging.getLogger(__name__)

def create_session(db: Session, user_id: UUID, title: str = "New Chat") -> ChatSession:
    session = ChatSession(user_id=user_id, title=title)
    db.add(session)
    db.flush()
    db.refresh(session)
    return session

def add_message(db: Session, session_id: UUID, role: MessageRole, content: str) -> ChatMessage:
    msg = ChatMessage(session_id=session_id, role=role, content=content)
    db.add(msg)
    db.flush()
    return msg

def get_messages(db: Session, session_id: UUID) -> list[ChatMessage]:
    return db.query(ChatMessage).filter(ChatMessage.session_id == session_id).order_by(ChatMessage.created_at).all()

def list_sessions(db: Session, user_id: UUID) -> list[ChatSession]:
    return db.query(ChatSession).filter(ChatSession.user_id == user_id).order_by(ChatSession.updated_at.desc()).all()

def get_session_history_for_llm(db: Session, session_id: UUID, max_messages: int = 20) -> list[dict]:
    msgs = db.query(ChatMessage).filter(ChatMessage.session_id == session_id).order_by(ChatMessage.created_at.desc()).limit(max_messages).all()
    result = []
    for m in reversed(msgs):
        role = "user" if m.role == MessageRole.USER else "assistant"
        result.append({"role": role, "content": m.content})
    return result
