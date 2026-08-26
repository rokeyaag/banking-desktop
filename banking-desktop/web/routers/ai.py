from datetime import datetime
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.db.models import User, ChatSession, ChatMessage, MessageRole, DocumentChunk
from app.llm.ollama_client import is_ollama_available, chat as ollama_chat
from web.security import get_db, get_current_user_from_token

router = APIRouter(prefix="/api/ai", tags=["ai"])

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[UUID] = None

SYSTEM_PROMPT = """You are NexaAI, an intelligent and polite banking assistant for NexaBank.
Help users with account information, deposits, transfers, loans, interest rates, security tips, and bank policies.
Be concise, clear, and professional."""

def get_fallback_response(query: str, db: Session) -> str:
    query_lower = query.lower()
    
    # Check DocumentChunk in DB
    keywords = [w for w in query_lower.split() if len(w) > 3]
    chunks = []
    if keywords:
        filters = [DocumentChunk.content.ilike(f"%{k}%") for k in keywords[:3]]
        chunks = db.query(DocumentChunk).filter(or_(*filters)).limit(2).all()
    
    if chunks:
        policy_info = "\n\n".join([c.content for c in chunks])
        return f"Here is what I found in our NexaBank policies regarding your query:\n\n{policy_info}"
    
    if any(w in query_lower for w in ["transfer", "send money", "pathano"]):
        return "To transfer funds:\n1. Click 'Transfer Funds' in the left menu.\n2. Choose source account & recipient account number.\n3. Enter amount & your 4-digit Security PIN.\n4. Click 'Send Money'."
    elif any(w in query_lower for w in ["deposit", "add money"]):
        return "To deposit funds into your account:\n1. Navigate to 'Deposit' tab.\n2. Select your account and enter the amount.\n3. Enter your Security PIN to confirm."
    elif any(w in query_lower for w in ["loan", "emi", "interest"]):
        return "NexaBank offers competitive personal and business loans starting at 8.5% annual interest. You can use our built-in Loan EMI Calculator in the Loans section to check monthly repayments and apply instantly."
    elif any(w in query_lower for w in ["pin", "security", "lock"]):
        return "Your 4-6 digit Security PIN protects your funds during all transfers and withdrawals. Never share your PIN with anyone. If you enter the wrong PIN 3 times, your account will be temporarily locked for 15 minutes."
    elif any(w in query_lower for w in ["hello", "hi", "hey", "salam"]):
        return "Hello! Welcome to NexaBank Assistant. How can I help you manage your finances, transfers, or loans today?"
    else:
        return "I'm NexaBank AI Assistant. You can ask me about account types, fund transfers, loan interest rates, security PIN, or banking policies. How can I assist you?"

@router.post("/chat")
def api_chat(req: ChatRequest, current_user: User = Depends(get_current_user_from_token), db: Session = Depends(get_db)):
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")
    
    # Get or create chat session
    session = None
    if req.session_id:
        session = db.query(ChatSession).filter(ChatSession.id == req.session_id, ChatSession.user_id == current_user.id).first()
    if not session:
        session = ChatSession(user_id=current_user.id, title=req.message[:40] + ("..." if len(req.message) > 40 else ""))
        db.add(session)
        db.flush()
    
    # Save User message
    user_msg = ChatMessage(session_id=session.id, role=MessageRole.USER, content=req.message)
    db.add(user_msg)
    
    # Generate Assistant response
    assistant_reply = ""
    try:
        if is_ollama_available():
            history = db.query(ChatMessage).filter(ChatMessage.session_id == session.id).order_by(ChatMessage.created_at.asc()).limit(6).all()
            messages = [{"role": m.role.value.lower(), "content": m.content} for m in history]
            messages.append({"role": "user", "content": req.message})
            assistant_reply = ollama_chat(messages=messages, system=SYSTEM_PROMPT)
        else:
            assistant_reply = get_fallback_response(req.message, db)
    except Exception:
        assistant_reply = get_fallback_response(req.message, db)
    
    asst_msg = ChatMessage(session_id=session.id, role=MessageRole.ASSISTANT, content=assistant_reply)
    db.add(asst_msg)
    db.commit()
    
    return {
        "reply": assistant_reply,
        "session_id": str(session.id),
        "timestamp": datetime.utcnow().strftime("%I:%M %p")
    }

@router.get("/history")
def api_chat_history(session_id: Optional[UUID] = None, current_user: User = Depends(get_current_user_from_token), db: Session = Depends(get_db)):
    if not session_id:
        session = db.query(ChatSession).filter(ChatSession.user_id == current_user.id).order_by(ChatSession.created_at.desc()).first()
        if not session:
            return {"session_id": None, "messages": []}
        session_id = session.id
    
    msgs = db.query(ChatMessage).filter(ChatMessage.session_id == session_id).order_by(ChatMessage.created_at.asc()).all()
    return {
        "session_id": str(session_id),
        "messages": [
            {
                "role": str(m.role.value if hasattr(m.role, 'value') else m.role).lower(),
                "content": m.content,
                "created_at": m.created_at.strftime("%I:%M %p") if m.created_at else ""
            }
            for m in msgs
        ]
    }
