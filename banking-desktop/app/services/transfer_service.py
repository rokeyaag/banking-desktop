"""
transfer_service.py
Handles fund transfers between accounts.
"""

from decimal import Decimal
from datetime import datetime
from sqlalchemy.orm import Session
from db.models import Account, Transaction, Transfer
from services.pin_service import verify_pin


class TransferError(Exception):
    pass


def get_account_by_number(db: Session, account_number: str):
    account = db.query(Account).filter(Account.account_number == account_number).first()
    if not account:
        raise TransferError(f"Account not found: {account_number}")
    return account


def validate_transfer(
    db: Session,
    sender_account_number: str,
    receiver_account_number: str,
    amount: Decimal,
    pin: str,
    user_id: int,
):
    """
    Validate all conditions before executing a transfer.
    Raises TransferError on any failure.
    """
    if amount <= Decimal("0"):
        raise TransferError("Transfer amount must be greater than zero.")

    if sender_account_number == receiver_account_number:
        raise TransferError("Sender and receiver accounts cannot be the same.")

    sender = get_account_by_number(db, sender_account_number)

    # Ownership check
    if sender.user_id != user_id:
        raise TransferError("You do not own this sender account.")

    # PIN check
    if not verify_pin(pin, sender.pin_hash):
        raise TransferError("Invalid PIN.")

    # Balance check
    if sender.balance < amount:
        raise TransferError("Insufficient balance.")

    # Receiver must exist
    receiver = get_account_by_number(db, receiver_account_number)

    return sender, receiver


def execute_transfer(
    db: Session,
    sender_account_number: str,
    receiver_account_number: str,
    amount: Decimal,
    pin: str,
    user_id: int,
    note: str = "",
) -> dict:
    """
    Execute a fund transfer after validation.
    Creates Transfer record and two Transaction entries (debit + credit).
    Returns a summary dict.
    """
    amount = Decimal(str(amount))

    sender, receiver = validate_transfer(
        db,
        sender_account_number,
        receiver_account_number,
        amount,
        pin,
        user_id,
    )

    now = datetime.utcnow()

    # Debit sender
    sender.balance -= amount
    # Credit receiver
    receiver.balance += amount

    # Transfer record
    transfer = Transfer(
        sender_account_id=sender.id,
        receiver_account_id=receiver.id,
        amount=amount,
        note=note,
        status="completed",
        created_at=now,
    )
    db.add(transfer)
    db.flush()  # get transfer.id

    # Debit transaction
    debit_txn = Transaction(
        account_id=sender.id,
        user_id=user_id,
        type="debit",
        amount=amount,
        description=f"Transfer to {receiver_account_number}. {note}".strip(". "),
        reference_id=transfer.id,
        created_at=now,
    )

    # Credit transaction
    credit_txn = Transaction(
        account_id=receiver.id,
        user_id=receiver.user_id,
        type="credit",
        amount=amount,
        description=f"Transfer from {sender_account_number}. {note}".strip(". "),
        reference_id=transfer.id,
        created_at=now,
    )

    db.add_all([debit_txn, credit_txn])
    db.commit()
    db.refresh(transfer)

    return {
        "transfer_id": transfer.id,
        "from_account": sender_account_number,
        "to_account": receiver_account_number,
        "amount": float(amount),
        "sender_new_balance": float(sender.balance),
        "status": "completed",
        "timestamp": now.isoformat(),
    }


def get_transfer_history(db: Session, user_id: int, limit: int = 50) -> list:
    """
    Return all transfers (sent or received) for accounts owned by user_id.
    """
    user_accounts = db.query(Account).filter(Account.user_id == user_id).all()
    account_ids = [a.id for a in user_accounts]

    transfers = (
        db.query(Transfer)
        .filter(
            (Transfer.sender_account_id.in_(account_ids))
            | (Transfer.receiver_account_id.in_(account_ids))
        )
        .order_by(Transfer.created_at.desc())
        .limit(limit)
        .all()
    )

    result = []
    for t in transfers:
        direction = "sent" if t.sender_account_id in account_ids else "received"
        result.append(
            {
                "transfer_id": t.id,
                "direction": direction,
                "amount": float(t.amount),
                "note": t.note,
                "status": t.status,
                "timestamp": t.created_at.isoformat(),
            }
        )
    return result