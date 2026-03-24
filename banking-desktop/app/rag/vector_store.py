from uuid import UUID
from sqlalchemy.orm import Session
from app.db.models import DocumentChunk

def store_chunks(db: Session, document_id: UUID, user_id: UUID, embedded_chunks: list[tuple[str, list]]):
    for i, (content, embedding) in enumerate(embedded_chunks):
        chunk = DocumentChunk(document_id=document_id, user_id=user_id, chunk_index=i, content=content, embedding=embedding if embedding else None)
        db.add(chunk)
    db.flush()
