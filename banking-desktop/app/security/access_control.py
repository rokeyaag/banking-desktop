from uuid import UUID
from sqlalchemy.orm import Session
from app.db.models import DocumentChunk

def get_user_accessible_chunk_ids(db: Session, user_id: UUID) -> list:
    rows = db.query(DocumentChunk.id).filter(DocumentChunk.user_id == user_id).all()
    return [r.id for r in rows]
