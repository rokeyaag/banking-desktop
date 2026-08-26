from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.models import User, Account, Transaction, TransactionType, Transfer, TransferStatus
from app.services.pin_service import verify_user_pin
from web.security import get_db, get_current_user_from_token

router = APIRouter(prefix="/api/transactions", tags=["transactions"])

class DepositWithdrawRequest(BaseModel):
    account_id: UUID
    amount: float
    pin: str
    description: Optional[str] = ""

class TransferRequest(BaseModel):
    from_account_id: UUID
    to_account_number: str
    amount: float
    pin: str
    note: Optional[str] = ""

@router.post("/deposit")
def api_deposit(req: DepositWithdrawRequest, current_user: User = Depends(get_current_user_from_token), db: Session = Depends(get_db)):
    if req.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be greater than zero.")
    
    ok, msg = verify_user_pin(db, current_user.id, req.pin)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    
    acct = db.query(Account).filter(Account.id == req.account_id, Account.user_id == current_user.id, Account.is_active == True).first()
    if not acct:
        raise HTTPException(status_code=404, detail="Account not found.")
    
    acct.balance += req.amount
    tx = Transaction(
        account_id=acct.id,
        transaction_type=TransactionType.DEPOSIT,
        amount=req.amount,
        balance_after=acct.balance,
        description=req.description or "Deposit via Web"
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)
    return {
        "success": True,
        "message": f"Successfully deposited ${req.amount:,.2f}",
        "new_balance": acct.balance,
        "transaction_id": str(tx.id)
    }

@router.post("/withdraw")
def api_withdraw(req: DepositWithdrawRequest, current_user: User = Depends(get_current_user_from_token), db: Session = Depends(get_db)):
    if req.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be greater than zero.")
    
    ok, msg = verify_user_pin(db, current_user.id, req.pin)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    
    acct = db.query(Account).filter(Account.id == req.account_id, Account.user_id == current_user.id, Account.is_active == True).first()
    if not acct:
        raise HTTPException(status_code=404, detail="Account not found.")
    if acct.balance < req.amount:
        raise HTTPException(status_code=400, detail="Insufficient account balance.")
    
    acct.balance -= req.amount
    tx = Transaction(
        account_id=acct.id,
        transaction_type=TransactionType.WITHDRAWAL,
        amount=req.amount,
        balance_after=acct.balance,
        description=req.description or "Withdrawal via Web"
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)
    return {
        "success": True,
        "message": f"Successfully withdrew ${req.amount:,.2f}",
        "new_balance": acct.balance,
        "transaction_id": str(tx.id)
    }

@router.post("/transfer")
def api_transfer(req: TransferRequest, current_user: User = Depends(get_current_user_from_token), db: Session = Depends(get_db)):
    if req.amount <= 0:
        raise HTTPException(status_code=400, detail="Transfer amount must be greater than zero.")
    
    ok, msg = verify_user_pin(db, current_user.id, req.pin)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    
    sender = db.query(Account).filter(Account.id == req.from_account_id, Account.user_id == current_user.id, Account.is_active == True).first()
    if not sender:
        raise HTTPException(status_code=404, detail="Sender account not found.")
    
    if sender.balance < req.amount:
        raise HTTPException(status_code=400, detail="Insufficient balance.")
    
    receiver = db.query(Account).filter(Account.account_number == req.to_account_number.strip(), Account.is_active == True).first()
    if not receiver:
        raise HTTPException(status_code=404, detail="Destination account number not found.")
    
    if sender.id == receiver.id:
        raise HTTPException(status_code=400, detail="Cannot transfer funds to the same account.")
    
    sender.balance -= req.amount
    receiver.balance += req.amount
    
    transfer = Transfer(
        sender_account_id=sender.id,
        receiver_account_id=receiver.id,
        amount=req.amount,
        note=req.note or "Fund transfer",
        status=TransferStatus.COMPLETED
    )
    db.add(transfer)
    db.flush()
    
    tx_sender = Transaction(
        account_id=sender.id,
        transaction_type=TransactionType.TRANSFER,
        amount=-req.amount,
        balance_after=sender.balance,
        description=f"Transfer to {receiver.account_number} ({receiver.holder_name or 'Account'}): {req.note or ''}".strip(),
        reference_id=str(transfer.id)
    )
    tx_receiver = Transaction(
        account_id=receiver.id,
        transaction_type=TransactionType.TRANSFER,
        amount=req.amount,
        balance_after=receiver.balance,
        description=f"Transfer from {sender.account_number} ({sender.holder_name or 'Account'}): {req.note or ''}".strip(),
        reference_id=str(transfer.id)
    )
    db.add_all([tx_sender, tx_receiver])
    db.commit()
    
    return {
        "success": True,
        "message": f"Successfully transferred ${req.amount:,.2f} to {receiver.account_number}",
        "new_balance": sender.balance,
        "transfer_id": str(transfer.id)
    }

@router.get("/history")
def api_history(
    account_id: Optional[UUID] = None,
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db)
):
    user_accounts = db.query(Account).filter(Account.user_id == current_user.id).all()
    user_account_ids = [a.id for a in user_accounts]
    acct_map = {a.id: a.account_number for a in user_accounts}

    if not user_account_ids:
        return {"transactions": []}

    query = db.query(Transaction)
    if account_id:
        if account_id not in user_account_ids:
            raise HTTPException(status_code=403, detail="Unauthorized account access")
        query = query.filter(Transaction.account_id == account_id)
    else:
        query = query.filter(Transaction.account_id.in_(user_account_ids))

    txs = query.order_by(Transaction.created_at.desc()).limit(limit).all()

    result = []
    for t in txs:
        result.append({
            "id": str(t.id),
            "account_id": str(t.account_id),
            "account_number": acct_map.get(t.account_id, "N/A"),
            "transaction_type": str(t.transaction_type.value if hasattr(t.transaction_type, 'value') else t.transaction_type),
            "amount": float(t.amount),
            "balance_after": float(t.balance_after),
            "description": t.description or "",
            "created_at": t.created_at.strftime("%b %d, %Y %I:%M %p") if t.created_at else ""
        })

    return {"transactions": result}

@router.get("/summary")
def api_summary(current_user: User = Depends(get_current_user_from_token), db: Session = Depends(get_db)):
    user_accounts = db.query(Account).filter(Account.user_id == current_user.id).all()
    total_balance = sum(a.balance for a in user_accounts)
    user_account_ids = [a.id for a in user_accounts]

    start_date = datetime.utcnow() - timedelta(days=30)
    txs = db.query(Transaction).filter(
        Transaction.account_id.in_(user_account_ids),
        Transaction.created_at >= start_date
    ).all() if user_account_ids else []

    total_inflow = sum(t.amount for t in txs if t.amount > 0)
    total_outflow = sum(abs(t.amount) for t in txs if t.amount < 0 or t.transaction_type == TransactionType.WITHDRAWAL)

    # 7-day trend
    days_data = []
    for i in range(6, -1, -1):
        day = datetime.utcnow().date() - timedelta(days=i)
        day_txs = [t for t in txs if t.created_at and t.created_at.date() == day]
        credit = sum(t.amount for t in day_txs if t.amount > 0)
        debit = sum(abs(t.amount) for t in day_txs if t.amount < 0)
        days_data.append({
            "date": day.strftime("%a"),
            "income": round(credit, 2),
            "expense": round(debit, 2)
        })

    return {
        "total_balance": round(total_balance, 2),
        "accounts_count": len(user_accounts),
        "total_inflow_30d": round(total_inflow, 2),
        "total_outflow_30d": round(total_outflow, 2),
        "chart_data": days_data
    }
