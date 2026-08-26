import os, sys
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
    db_url = config.get_db_url()

    is_sqlite = "sqlite" in db_url
    if not is_sqlite:
        try:
            test_engine = create_engine(
                db_url,
                pool_size=5, max_overflow=10,
                pool_pre_ping=True, echo=False,
                connect_args={"connect_timeout": 2}
            )
            with test_engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            _engine = test_engine
        except Exception as e:
            _log.warning(f"Database connection failed ({e}). Switching to SQLite fallback.")
            is_sqlite = True

    if is_sqlite or _engine is None:
        fallback_url = "sqlite:////tmp/nexabank.db" if os.name != 'nt' else "sqlite:///nexabank_local.db"
        _engine = create_engine(fallback_url, connect_args={"check_same_thread": False})

    _SessionLocal = sessionmaker(
        autocommit=False, autoflush=False,
        bind=_engine,
        expire_on_commit=False
    )

def get_engine():
    _init_engine()
    return _engine

def _ensure_database_exists():
    try:
        from app.config import config
        db_url = config.get_db_url()
        if "sqlite" in db_url or not config.DB_HOST or (config.DB_HOST in ["localhost", "127.0.0.1"] and os.name != 'nt'):
            return
        import psycopg2
        from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
        conn = psycopg2.connect(
            host=config.DB_HOST, port=config.DB_PORT,
            user=config.DB_USER, password=config.DB_PASSWORD,
            dbname="postgres",
            connect_timeout=2
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
        _log.warning(f"DB ensure warning: {e}")

def _try_pgvector() -> bool:
    try:
        from app.config import config
        if "sqlite" in config.get_db_url() or not _engine:
            return False
        with _engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.commit()
        return True
    except Exception:
        return False

def _auto_seed_demo_user():
    try:
        from app.db.models import User, Account, AccountType
        from app.security.hashing import hash_password
        from app.services.pin_service import set_pin
        with get_db() as db:
            admin = db.query(User).filter(User.email == "admin@nexabank.com").first()
            if not admin:
                user = User(
                    email="admin@nexabank.com",
                    password_hash=hash_password("Password123"),
                    full_name="Admin User",
                    phone="+1234567890",
                    is_admin=True,
                    is_active=True
                )
                db.add(user)
                db.flush()
                set_pin(db, user.id, "1234")
                acc1 = Account(user_id=user.id, account_number="100123456789", account_type=AccountType.CHECKING, balance=5000.0)
                acc2 = Account(user_id=user.id, account_number="200987654321", account_type=AccountType.SAVINGS, balance=12000.0)
                db.add_all([acc1, acc2])
                db.commit()
                _log.info("Demo user seeded successfully.")
    except Exception as e:
        _log.warning(f"Demo user auto-seed notice: {e}")

_initialized = False

def init_db():
    global _initialized, _engine, _SessionLocal
    if _initialized:
        return
    _init_engine()
    _ensure_database_exists()
    from app.db import models  # noqa
    if not _try_pgvector():
        try:
            from sqlalchemy import Text
            from app.db.models import DocumentChunk
            col = DocumentChunk.__table__.c.get("embedding")
            if col is not None:
                col.type = Text()
        except Exception:
            pass
    try:
        Base.metadata.create_all(bind=_engine)
    except Exception as e:
        _log.warning(f"create_all notice ({e}). Fallback to SQLite.")
        fallback_url = "sqlite:////tmp/nexabank.db" if os.name != 'nt' else "sqlite:///nexabank_local.db"
        _engine = create_engine(fallback_url, connect_args={"check_same_thread": False})
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine, expire_on_commit=False)
        Base.metadata.create_all(bind=_engine)

    _auto_seed_demo_user()
    _initialized = True
    _log.info("All tables created/verified.")

@contextmanager
def get_db():
    init_db()
    db = _SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
