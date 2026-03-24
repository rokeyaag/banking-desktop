from uuid import UUID
from sqlalchemy.orm import Session
from app.db.models import Account, Transaction, TransactionType
from app.services.pin_service import verify_user_pin
import logging
_log = logging.getLogger(__name__)

def _tx_dict(t: Transaction) -> dict:
    return {
        "id": t.id,
        "transaction_type": t.transaction_type,
        "amount": float(t.amount),
        "balance_after": float(t.balance_after),
        "description": t.description,
        "created_at": t.created_at,
    }

def deposit(db: Session, user_id: UUID, account_id: UUID, amount_str: str, pin: str, description: str = "Deposit") -> tuple[bool, str, dict | None]:
    try:
        amount = float(amount_str)
        if amount <= 0: return False, "Amount must be greater than zero.", None
        acct = db.query(Account).filter(Account.id == account_id, Account.user_id == user_id, Account.is_active == True).first()
        if not acct: return False, "Account not found.", None
        ok, msg = verify_user_pin(db, user_id, pin)
        if not ok: return False, msg, None
        acct.balance += amount
        tx = Transaction(account_id=account_id, transaction_type=TransactionType.DEPOSIT, amount=amount, balance_after=acct.balance, description=description)
        db.add(tx)
        db.flush()
        db.refresh(tx)
        return True, f"Deposited ${amount:,.2f} successfully.", _tx_dict(tx)
    except Exception as e:
        return False, str(e), None

def withdraw(db: Session, user_id: UUID, account_id: UUID, amount_str: str, pin: str, description: str = "Withdrawal") -> tuple[bool, str, dict | None]:
    try:
        amount = float(amount_str)
        if amount <= 0: return False, "Amount must be greater than zero.", None
        acct = db.query(Account).filter(Account.id == account_id, Account.user_id == user_id, Account.is_active == True).first()
        if not acct: return False, "Account not found.", None
        if acct.balance < amount: return False, "Insufficient funds.", None
        ok, msg = verify_user_pin(db, user_id, pin)
        if not ok: return False, msg, None
        acct.balance -= amount
        tx = Transaction(account_id=account_id, transaction_type=TransactionType.WITHDRAWAL, amount=amount, balance_after=acct.balance, description=description)
        db.add(tx)
        db.flush()
        db.refresh(tx)
        return True, f"Withdrew ${amount:,.2f} successfully.", _tx_dict(tx)
    except Exception as e:
        return False, str(e), None

def get_transaction_history(db: Session, account_id: UUID, user_id: UUID, limit: int = 20) -> list[dict]:
    acct = db.query(Account).filter(Account.id == account_id, Account.user_id == user_id).first()
    if not acct: return []
    txs = db.query(Transaction).filter(Transaction.account_id == account_id).order_by(Transaction.created_at.desc()).limit(limit).all()
    return [_tx_dict(t) for t in txs]
