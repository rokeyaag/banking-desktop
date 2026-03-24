import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from contextlib import contextmanager

_log = logging.getLogger(__name__)
Base = declarative_base()
_engine = None
_SessionLocal = None

def _init_engine():
    global _engine, _SessionLocal
    if _engine is not None:
        return
    from app.config import config
    _engine = create_engine(
        config.get_db_url(),
        pool_size=5, max_overflow=10,
        pool_pre_ping=True, echo=False,
    )
    _SessionLocal = sessionmaker(
        autocommit=False, autoflush=False,
        bind=_engine,
        expire_on_commit=False  # ← KEY FIX: objects stay alive after commit/close
    )

def get_engine():
    _init_engine()
    return _engine

def _ensure_database_exists():
    import psycopg2
    from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
    from app.config import config
    try:
        conn = psycopg2.connect(
            host=config.DB_HOST, port=config.DB_PORT,
            user=config.DB_USER, password=config.DB_PASSWORD,
            dbname="postgres",
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (config.DB_NAME,))
        if not cur.fetchone():
            cur.execute(f'CREATE DATABASE "{config.DB_NAME}"')
            _log.info(f"Created database '{config.DB_NAME}'")
        cur.close()
        conn.close()
    except Exception as e:
        _log.error(f"DB ensure error: {e}")
        raise

def _try_pgvector() -> bool:
    try:
        with _engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.commit()
        return True
    except Exception:
        return False

def init_db():
    _ensure_database_exists()
    _init_engine()
    from app.db import models  # noqa
    if not _try_pgvector():
        _log.warning("pgvector unavailable — embedding column will be Text")
        try:
            from sqlalchemy import Text
            from app.db.models import DocumentChunk
            col = DocumentChunk.__table__.c.get("embedding")
            if col is not None:
                col.type = Text()
        except Exception:
            pass
    Base.metadata.create_all(bind=_engine)
    _log.info("All tables created/verified.")

@contextmanager
def get_db():
    _init_engine()
    db = _SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
