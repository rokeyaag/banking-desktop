from sqlalchemy.orm import Session
from app.db.models import User
from app.security.hashing import hash_password, verify_password
from app.utils.validators import validate_email, validate_password, validate_full_name
import logging
_log = logging.getLogger(__name__)


class UserSession:
    """Plain Python object - no SQLAlchemy dependency."""
    def __init__(self, user: User):
        self.id        = user.id
        self.email     = str(user.email)
        self.full_name = str(user.full_name)
        self.phone     = str(user.phone) if user.phone else ""
        self.is_active = bool(user.is_active)
        self.is_admin  = bool(user.is_admin)
        self.created_at = user.created_at


_current_user: UserSession | None = None


def get_current_user() -> UserSession | None:
    return _current_user


def register_user(db: Session, email: str, password: str, full_name: str, phone: str = "") -> tuple[bool, str, UserSession | None]:
    try:
        ok, msg = validate_email(email)
        if not ok: return False, msg, None
        ok, msg = validate_password(password)
        if not ok: return False, msg, None
        ok, msg = validate_full_name(full_name)
        if not ok: return False, msg, None
        if db.query(User).filter(User.email == email.lower().strip()).first():
            return False, "Email already registered.", None
        user = User(email=email.lower().strip(), full_name=full_name.strip(),
                    password_hash=hash_password(password), phone=phone.strip() or None)
        db.add(user)
        db.flush()
        db.refresh(user)
        result = UserSession(user)
        _log.info(f"User registered: {user.email}")
        return True, "Registration successful!", result
    except Exception as e:
        _log.error(f"Register error: {e}")
        return False, f"Registration failed: {str(e)}", None


def login_user(db: Session, email: str, password: str) -> tuple[bool, str, UserSession | None]:
    global _current_user
    try:
        user = db.query(User).filter(User.email == email.lower().strip()).first()
        if not user or not verify_password(password, user.password_hash):
            return False, "Invalid email or password.", None
        if not user.is_active:
            return False, "Account is disabled.", None
        result = UserSession(user)
        _current_user = result
        _log.info(f"Login: {user.email}")
        return True, "Login successful!", result
    except Exception as e:
        _log.error(f"Login error: {e}")
        return False, f"Login failed: {str(e)}", None


def logout_user():
    global _current_user
    _current_user = None
