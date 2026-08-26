from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.models import User, Account, Loan, LoanStatus, LoanRepayment, Transaction, TransactionType
from app.services.pin_service import verify_user_pin
from web.security import get_db, get_current_user_from_token

router = APIRouter(prefix="/api/loans", tags=["loans"])

def calc_emi(principal: float, annual_rate: float, tenure_months: int) -> float:
    if tenure_months <= 0:
        return principal
    r = (annual_rate / 100.0) / 12.0
    if r == 0:
        return round(principal / tenure_months, 2)
    emi = principal * r * ((1 + r) ** tenure_months) / (((1 + r) ** tenure_months) - 1)
    return round(emi, 2)

class CalculateEMIRequest(BaseModel):
    principal: float
    annual_rate: float = 8.5
    tenure_months: int

class ApplyLoanRequest(BaseModel):
    principal: float
    tenure_months: int
    purpose: str
    annual_rate: float = 8.5

class RepayLoanRequest(BaseModel):
    loan_id: UUID
    account_id: UUID
    amount: float
    pin: str

@router.post("/calculate")
def api_calculate_emi(req: CalculateEMIRequest):
    if req.principal <= 0 or req.tenure_months <= 0:
        raise HTTPException(status_code=400, detail="Principal and tenure must be positive values.")
    emi = calc_emi(req.principal, req.annual_rate, req.tenure_months)
    total_payment = round(emi * req.tenure_months, 2)
    total_interest = round(total_payment - req.principal, 2)
    return {
        "emi": emi,
        "total_payment": total_payment,
        "total_interest": total_interest,
        "annual_rate": req.annual_rate,
        "tenure_months": req.tenure_months
    }

@router.get("")
def api_list_loans(current_user: User = Depends(get_current_user_from_token), db: Session = Depends(get_db)):
    loans = db.query(Loan).filter(Loan.user_id == current_user.id).order_by(Loan.applied_at.desc()).all()
    result = []
    for l in loans:
        repayments = [
            {"id": str(r.id), "amount": float(r.amount), "paid_at": r.paid_at.strftime("%b %d, %Y %I:%M %p") if r.paid_at else ""}
            for r in l.repayments
        ]
        result.append({
            "id": str(l.id),
            "principal": float(l.principal),
            "outstanding_balance": float(l.outstanding_balance),
            "annual_rate": float(l.annual_rate),
            "tenure_months": l.tenure_months,
            "emi_amount": float(l.emi_amount),
            "purpose": l.purpose or "Personal Loan",
            "status": str(l.status.value if hasattr(l.status, 'value') else l.status),
            "applied_at": l.applied_at.strftime("%b %d, %Y") if l.applied_at else "",
            "next_due_date": l.next_due_date.strftime("%b %d, %Y") if l.next_due_date else "",
            "repayments": repayments
        })
    return {"loans": result}

@router.post("/apply")
def api_apply_loan(req: ApplyLoanRequest, current_user: User = Depends(get_current_user_from_token), db: Session = Depends(get_db)):
    if req.principal < 100 or req.tenure_months < 1:
        raise HTTPException(status_code=400, detail="Minimum loan amount is $100 and tenure must be at least 1 month.")
    
    emi = calc_emi(req.principal, req.annual_rate, req.tenure_months)
    loan = Loan(
        user_id=current_user.id,
        principal=req.principal,
        outstanding_balance=req.principal,
        annual_rate=req.annual_rate,
        tenure_months=req.tenure_months,
        emi_amount=emi,
        purpose=req.purpose,
        status=LoanStatus.ACTIVE,
        start_date=datetime.utcnow(),
        next_due_date=datetime.utcnow() + timedelta(days=30)
    )
    db.add(loan)
    db.commit()
    db.refresh(loan)
    return {
        "success": True,
        "message": f"Loan of ${req.principal:,.2f} approved and active!",
        "loan_id": str(loan.id),
        "emi_amount": emi
    }

@router.post("/repay")
def api_repay_loan(req: RepayLoanRequest, current_user: User = Depends(get_current_user_from_token), db: Session = Depends(get_db)):
    if req.amount <= 0:
        raise HTTPException(status_code=400, detail="Repayment amount must be greater than zero.")
    
    ok, msg = verify_user_pin(db, current_user.id, req.pin)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    
    loan = db.query(Loan).filter(Loan.id == req.loan_id, Loan.user_id == current_user.id).first()
    if not loan:
        raise HTTPException(status_code=404, detail="Loan not found.")
    
    if loan.status != LoanStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Loan is not in active state.")
    
    acct = db.query(Account).filter(Account.id == req.account_id, Account.user_id == current_user.id, Account.is_active == True).first()
    if not acct:
        raise HTTPException(status_code=404, detail="Payment account not found.")
    
    pay_amount = min(req.amount, loan.outstanding_balance)
    if acct.balance < pay_amount:
        raise HTTPException(status_code=400, detail="Insufficient account balance for loan repayment.")
    
    acct.balance -= pay_amount
    loan.outstanding_balance -= pay_amount
    if loan.outstanding_balance <= 0.01:
        loan.outstanding_balance = 0.0
        loan.status = LoanStatus.CLOSED
        loan.closed_at = datetime.utcnow()
    else:
        loan.next_due_date = datetime.utcnow() + timedelta(days=30)
    
    repayment = LoanRepayment(loan_id=loan.id, amount=pay_amount, paid_at=datetime.utcnow())
    tx = Transaction(
        account_id=acct.id,
        transaction_type=TransactionType.WITHDRAWAL,
        amount=pay_amount,
        balance_after=acct.balance,
        description=f"Loan Repayment ({loan.purpose or 'Loan'})",
        reference_id=str(loan.id)
    )
    db.add_all([repayment, tx])
    db.commit()
    
    return {
        "success": True,
        "message": f"Successfully paid ${pay_amount:,.2f} towards your loan.",
        "outstanding_balance": loan.outstanding_balance,
        "is_closed": loan.status == LoanStatus.CLOSED
    }
