"""
Run this script once to load nexabank_faq_policy.txt into the database.
Usage:
  cd F:\\ICTBD_02\\PycharmProjects\\banking-desktop (2)\\banking-desktop
  C:\\Users\\User\\AppData\\Local\\Programs\\Python\\Python314\\python.exe scripts\\seed_faq.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import init_db, get_db
from app.db.models import UploadedDocument, DocumentChunk, User

# ── Config ────────────────────────────────────────────────────
FAQ_FILE   = os.path.join(os.path.dirname(__file__), "nexabank_faq_policy.txt")
CHUNK_SIZE = 512
OVERLAP    = 64

def chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = OVERLAP) -> list[str]:
    words  = text.split()
    chunks = []
    i = 0
    while i < len(words):
        chunk = " ".join(words[i:i+size])
        chunks.append(chunk)
        i += size - overlap
    return [c for c in chunks if c.strip()]

def get_embedding(text: str) -> list[float] | None:
    try:
        from app.llm.ollama_client import get_embedding as _emb
        return _emb(text)
    except Exception as e:
        print(f"  ⚠ Embedding failed: {e}")
        return None

def main():
    print("🚀 NexaBank FAQ Seeder")
    print("=" * 40)

    # Check file exists
    if not os.path.exists(FAQ_FILE):
        print(f"❌ File not found: {FAQ_FILE}")
        print(f"   Please put nexabank_faq_policy.txt in the scripts/ folder")
        sys.exit(1)

    # Init DB
    print("📦 Initializing database...")
    init_db()

    with get_db() as db:
        # Get first admin/any user (or None for shared doc)
        user = db.query(User).first()
        user_id = user.id if user else None
        user_name = user.email if user else "system"
        print(f"👤 Using user: {user_name}")

        # Check if already seeded
        existing = db.query(UploadedDocument).filter(
            UploadedDocument.filename == "nexabank_faq_policy.txt"
        ).first()
        if existing:
            print("⚠  FAQ already seeded! Deleting old version...")
            db.delete(existing)
            db.flush()

        # Read file
        with open(FAQ_FILE, "r", encoding="utf-8") as f:
            content = f.read()
        print(f"📄 File loaded: {len(content)} characters")

        # Create document record
        doc = UploadedDocument(
            user_id   = user_id,
            filename  = "nexabank_faq_policy.txt",
            file_path = FAQ_FILE,
            file_size = len(content.encode("utf-8")),
            status    = "processing",
        )
        db.add(doc)
        db.flush()
        print(f"✅ Document record created: {doc.id}")

        # Chunk text
        chunks = chunk_text(content, CHUNK_SIZE, OVERLAP)
        print(f"🔪 Created {len(chunks)} chunks")

        # Embed and save
        print("🤖 Generating embeddings (this may take a minute)...")
        success = 0
        for i, chunk_text_val in enumerate(chunks):
            emb = get_embedding(chunk_text_val)
            c = DocumentChunk(
                document_id = doc.id,
                user_id     = user_id,
                chunk_index = i,
                content     = chunk_text_val,
                embedding   = emb,
            )
            db.add(c)
            if emb:
                print(f"  ✅ Chunk {i+1}/{len(chunks)} embedded")
                success += 1
            else:
                print(f"  ⚠  Chunk {i+1}/{len(chunks)} saved without embedding")

        doc.status = "completed"
        print(f"\n🎉 Done! {success}/{len(chunks)} chunks embedded successfully.")
        print(f"   You can now use AI Search on the dashboard!")

if __name__ == "__main__":
    main()