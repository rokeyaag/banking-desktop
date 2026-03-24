import random
from uuid import UUID
from sqlalchemy.orm import Session
from app.db.models import Account, AccountType
import logging
_log = logging.getLogger(__name__)

def _gen_num() -> str:
    return "".join(str(random.randint(0,9)) for _ in range(12))

def _to_dict(a: Account) -> dict:
    return {
        "id": a.id,
        "account_number": str(a.account_number),
        "account_type": a.account_type,
        "balance": float(a.balance),
        "currency": str(a.currency),
        "is_active": bool(a.is_active),
        "created_at": a.created_at,
        "holder_name": a.holder_name or "",
        "photo_path": a.photo_path or "",
        "dob": a.dob or "",
        "nid": a.nid or "",
        "phone": a.phone or "",
        "address": a.address or "",
        "occupation": a.occupation or "",
    }

def open_account(db: Session, user_id: UUID, account_type: AccountType,
                 initial_deposit: float = 0.0, holder_name: str = "",
                 dob: str = "", nid: str = "", phone: str = "",
                 address: str = "", occupation: str = "", currency: str = "USD",
                 photo_path: str = "") -> tuple[bool, str, dict | None]:
    try:
        for _ in range(10):
            num = _gen_num()
            if not db.query(Account).filter(Account.account_number == num).first():
                break
        acct = Account(
            user_id=user_id,
            account_number=num,
            account_type=account_type,
            balance=max(0.0, initial_deposit),
            currency=currency or "USD",
            holder_name=holder_name or None,
            dob=dob or None,
            nid=nid or None,
            phone=phone or None,
            address=address or None,
            occupation=occupation or None,
            photo_path=photo_path or None,
        )
        db.add(acct)
        db.flush()
        db.refresh(acct)
        return True, "Account opened successfully.", _to_dict(acct)
    except Exception as e:
        return False, str(e), None

def list_accounts(db: Session, user_id: UUID) -> list[dict]:
    accounts = db.query(Account).filter(
        Account.user_id == user_id, Account.is_active == True
    ).all()
    return [_to_dict(a) for a in accounts]

def get_account(db: Session, account_id: UUID, user_id: UUID) -> Account | None:
    return db.query(Account).filter(
        Account.id == account_id, Account.user_id == user_id
    ).first()

def get_account_by_number(db: Session, account_number: str, user_id: UUID) -> Account | None:
    return db.query(Account).filter(
        Account.account_number == account_number, Account.user_id == user_id
    ).first()