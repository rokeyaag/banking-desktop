from uuid import UUID
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.db.models import UserPIN
from app.security.hashing import hash_pin, verify_pin
from app.config import config
import logging
_log = logging.getLogger(__name__)

def has_pin(db: Session, user_id: UUID) -> bool:
    return db.query(UserPIN).filter(UserPIN.user_id == user_id).first() is not None

def is_pin_locked(db: Session, user_id: UUID) -> bool:
    record = db.query(UserPIN).filter(UserPIN.user_id == user_id).first()
    if not record or not record.locked_until:
        return False
    return datetime.utcnow() < record.locked_until

def set_pin(db: Session, user_id: UUID, pin: str) -> tuple[bool, str]:
    from app.utils.validators import validate_pin
    ok, msg = validate_pin(pin)
    if not ok:
        return False, msg
    record = db.query(UserPIN).filter(UserPIN.user_id == user_id).first()
    if record:
        record.pin_hash = hash_pin(pin)
        record.failed_attempts = 0
        record.locked_until = None
    else:
        record = UserPIN(user_id=user_id, pin_hash=hash_pin(pin))
        db.add(record)
    return True, "PIN set successfully."

def verify_user_pin(db: Session, user_id: UUID, pin: str) -> tuple[bool, str]:
    record = db.query(UserPIN).filter(UserPIN.user_id == user_id).first()
    if not record:
        return False, "No PIN set. Please set a PIN first."
    if record.locked_until and datetime.utcnow() < record.locked_until:
        remaining = int((record.locked_until - datetime.utcnow()).seconds / 60) + 1
        return False, f"PIN locked. Try again in {remaining} minute(s)."
    if verify_pin(pin, record.pin_hash):
        record.failed_attempts = 0
        record.locked_until = None
        return True, "PIN verified."
    record.failed_attempts += 1
    if record.failed_attempts >= config.PIN_MAX_ATTEMPTS:
        record.locked_until = datetime.utcnow() + timedelta(minutes=config.PIN_LOCKOUT_MINUTES)
        return False, f"Too many attempts. PIN locked for {config.PIN_LOCKOUT_MINUTES} minutes."
    remaining = config.PIN_MAX_ATTEMPTS - record.failed_attempts
    return False, f"Wrong PIN. {remaining} attempt(s) remaining."
