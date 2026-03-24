"""
transaction_service.py
Fetch, filter, and summarize transaction history.
"""

from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from db.models import Account, Transaction


class TransactionError(Exception):
    pass


def _owned_account_ids(db: Session, user_id: int) -> list[int]:
    accounts = db.query(Account).filter(Account.user_id == user_id).all()
    return [a.id for a in accounts]


def get_transactions(
    db: Session,
    user_id: int,
    account_id: int = None,
    txn_type: str = None,       # "debit" | "credit" | None (all)
    start_date: datetime = None,
    end_date: datetime = None,
    keyword: str = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict]:
    """
    Fetch transactions for a user with optional filters.
    - account_id: filter to one specific account (must be owned by user)
    - txn_type: 'debit' or 'credit'
    - start_date / end_date: date range filter
    - keyword: search in description
    """
    owned_ids = _owned_account_ids(db, user_id)

    if not owned_ids:
        return []

    if account_id:
        if account_id not in owned_ids:
            raise TransactionError("Account does not belong to this user.")
        filter_ids = [account_id]
    else:
        filter_ids = owned_ids

    query = db.query(Transaction).filter(Transaction.account_id.in_(filter_ids))

    if txn_type in ("debit", "credit"):
        query = query.filter(Transaction.type == txn_type)

    if start_date:
        query = query.filter(Transaction.created_at >= start_date)

    if end_date:
        # include full end day
        end = end_date.replace(hour=23, minute=59, second=59)
        query = query.filter(Transaction.created_at <= end)

    if keyword:
        query = query.filter(Transaction.description.ilike(f"%{keyword}%"))

    transactions = (
        query.order_by(Transaction.created_at.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )

    return [_serialize(t) for t in transactions]


def get_recent_transactions(db: Session, user_id: int, days: int = 30) -> list[dict]:
    """Return transactions from the last N days."""
    start = datetime.utcnow() - timedelta(days=days)
    return get_transactions(db, user_id, start_date=start)


def get_transaction_by_id(db: Session, txn_id: int, user_id: int) -> dict:
    """Fetch a single transaction, ensuring it belongs to the user."""
    owned_ids = _owned_account_ids(db, user_id)
    txn = (
        db.query(Transaction)
        .filter(Transaction.id == txn_id, Transaction.account_id.in_(owned_ids))
        .first()
    )
    if not txn:
        raise TransactionError("Transaction not found.")
    return _serialize(txn)


def get_summary(db: Session, user_id: int, days: int = 30) -> dict:
    """
    Return total credited, debited, and net for the last N days.
    """
    start = datetime.utcnow() - timedelta(days=days)
    txns = get_transactions(db, user_id, start_date=start, limit=10000)

    total_credit = sum(t["amount"] for t in txns if t["type"] == "credit")
    total_debit  = sum(t["amount"] for t in txns if t["type"] == "debit")

    return {
        "period_days": days,
        "total_credit": round(total_credit, 2),
        "total_debit": round(total_debit, 2),
        "net": round(total_credit - total_debit, 2),
        "transaction_count": len(txns),
    }


def count_transactions(
    db: Session,
    user_id: int,
    account_id: int = None,
    start_date: datetime = None,
    end_date: datetime = None,
) -> int:
    """Return total count (for pagination)."""
    owned_ids = _owned_account_ids(db, user_id)
    filter_ids = [account_id] if account_id else owned_ids

    query = db.query(Transaction).filter(Transaction.account_id.in_(filter_ids))
    if start_date:
        query = query.filter(Transaction.created_at >= start_date)
    if end_date:
        query = query.filter(Transaction.created_at <= end_date)

    return query.count()


def _serialize(t: Transaction) -> dict:
    return {
        "id": t.id,
        "account_id": t.account_id,
        "type": t.type,
        "amount": float(t.amount),
        "description": t.description,
        "reference_id": t.reference_id,
        "timestamp": t.created_at.isoformat(),
    }