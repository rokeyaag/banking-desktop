from uuid import UUID
from sqlalchemy import cast, String
from sqlalchemy.orm import Session
from app.db.models import DocumentChunk, Account, Transaction
import logging
_log = logging.getLogger(__name__)

def keyword_search_chunks(db: Session, user_id: UUID, query: str, limit: int = 10) -> list[DocumentChunk]:
    return db.query(DocumentChunk).filter(DocumentChunk.user_id == user_id, DocumentChunk.content.ilike(f"%{query}%")).limit(limit).all()

def search_accounts(db: Session, user_id: UUID, query: str) -> list[Account]:
    return db.query(Account).filter(Account.user_id == user_id, Account.is_active == True, Account.account_number.ilike(f"%{query}%")).limit(10).all()

def search_transactions(db: Session, user_id: UUID, query: str) -> list[Transaction]:
    from app.db.models import Account
    acct_ids = [a.id for a in db.query(Account).filter(Account.user_id == user_id).all()]
    if not acct_ids: return []
    return db.query(Transaction).filter(Transaction.account_id.in_(acct_ids), Transaction.description.ilike(f"%{query}%")).order_by(Transaction.created_at.desc()).limit(20).all()
