import os
import shutil
from uuid import UUID
from sqlalchemy.orm import Session
from app.db.models import UploadedDocument
from app.config import config
import logging
_log = logging.getLogger(__name__)

def save_upload(db: Session, user_id: UUID, filename: str, src_path: str) -> tuple[bool, str, UploadedDocument | None]:
    try:
        dest_dir = os.path.join(config.UPLOAD_DIR, str(user_id))
        os.makedirs(dest_dir, exist_ok=True)
        dest = os.path.join(dest_dir, filename)
        shutil.copy2(src_path, dest)
        size = os.path.getsize(dest)
        doc = UploadedDocument(user_id=user_id, filename=filename, file_path=dest, file_size=size, status="pending")
        db.add(doc)
        db.flush()
        db.refresh(doc)
        return True, "File saved.", doc
    except Exception as e:
        return False, str(e), None

def list_uploads(db: Session, user_id: UUID) -> list[UploadedDocument]:
    return db.query(UploadedDocument).filter(UploadedDocument.user_id == user_id).order_by(UploadedDocument.created_at.desc()).all()

def ingest_document(db: Session, doc_id: UUID, user_id: UUID):
    doc = db.query(UploadedDocument).filter(UploadedDocument.id == doc_id, UploadedDocument.user_id == user_id).first()
    if not doc: return
    doc.status = "processing"
    db.commit()
    try:
        text = open(doc.file_path, encoding="utf-8").read()
        from app.rag.chunker import chunk_text
        from app.rag.embedder import embed_chunks
        from app.rag.vector_store import store_chunks
        chunks = chunk_text(text)
        embedded = embed_chunks(chunks)
        store_chunks(db, doc_id, user_id, embedded)
        doc.status = "done"
    except Exception as e:
        doc.status = "error"
        doc.error_message = str(e)
    db.commit()
