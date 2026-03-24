from uuid import UUID
from sqlalchemy.orm import Session
from app.db.models import DocumentChunk

def retrieve(db: Session, user_id: UUID, query: str, top_k: int = 5) -> list[tuple[DocumentChunk, float]]:
    try:
        from app.llm.ollama_client import get_embedding
        from app.db.models import PGVECTOR_AVAILABLE
        if not PGVECTOR_AVAILABLE:
            return _keyword_fallback(db, user_id, query, top_k)
        q_emb = get_embedding(query)
        chunks = db.query(DocumentChunk).filter(DocumentChunk.user_id == user_id, DocumentChunk.embedding != None).all()
        scored = []
        for c in chunks:
            try:
                import numpy as np
                a, b = np.array(q_emb), np.array(c.embedding)
                score = float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-8))
                scored.append((c, score))
            except Exception:
                pass
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]
    except Exception:
        return _keyword_fallback(db, user_id, query, top_k)

def _keyword_fallback(db: Session, user_id: UUID, query: str, top_k: int) -> list[tuple[DocumentChunk, float]]:
    chunks = db.query(DocumentChunk).filter(DocumentChunk.user_id == user_id, DocumentChunk.content.ilike(f"%{query}%")).limit(top_k).all()
    return [(c, 1.0) for c in chunks]

def format_context(results: list[tuple[DocumentChunk, float]]) -> str:
    return "\n\n---\n\n".join(c.content for c, _ in results)
