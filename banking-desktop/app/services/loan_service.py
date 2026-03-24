"""
loan_service.py
Loan application, eligibility check, EMI calculation, repayment tracking.
"""

from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from sqlalchemy.orm import Session
from db.models import Account, Loan, LoanRepayment


class LoanError(Exception):
    pass


# ---------------------------------------------------------------------------
# EMI & eligibility helpers
# ---------------------------------------------------------------------------

def calculate_emi(principal: float, annual_rate: float, tenure_months: int) -> float:
    """
    Standard reducing-balance EMI formula:
        EMI = P * r * (1+r)^n / ((1+r)^n - 1)
    where r = monthly rate, n = tenure in months.
    """
    if tenure_months <= 0:
        raise LoanError("Tenure must be at least 1 month.")
    if annual_rate < 0:
        raise LoanError("Interest rate cannot be negative.")

    p = Decimal(str(principal))
    r = Decimal(str(annual_rate)) / Decimal("1200")  # monthly rate

    if r == 0:
        emi = p / Decimal(str(tenure_months))
    else:
        n = Decimal(str(tenure_months))
        emi = p * r * (1 + r) ** n / ((1 + r) ** n - 1)

    return float(emi.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def check_eligibility(db: Session, user_id: int, requested_amount: float) -> dict:
    """
    Simple rule-based eligibility:
    - User must have at least one active account.
    - No active defaulted loan.
    - Total existing loan balance < 5× average account balance.
    Returns { eligible: bool, reason: str, max_amount: float }
    """
    accounts = db.query(Account).filter(
        Account.user_id == user_id, Account.status == "active"
    ).all()

    if not accounts:
        return {"eligible": False, "reason": "No active account found.", "max_amount": 0}

    avg_balance = sum(float(a.balance) for a in accounts) / len(accounts)

    # Check defaulted loans
    defaulted = db.query(Loan).filter(
        Loan.user_id == user_id, Loan.status == "defaulted"
    ).first()
    if defaulted:
        return {"eligible": False, "reason": "Existing defaulted loan.", "max_amount": 0}

    # Active loan total
    active_loans = db.query(Loan).filter(
        Loan.user_id == user_id, Loan.status == "active"
    ).all()
    total_outstanding = sum(float(l.outstanding_balance) for l in active_loans)

    max_allowed = avg_balance * 5
    available = max(0.0, max_allowed - total_outstanding)

    if requested_amount > available:
        return {
            "eligible": False,
            "reason": f"Requested amount exceeds limit. Max available: {available:.2f}",
            "max_amount": round(available, 2),
        }

    return {"eligible": True, "reason": "Eligible.", "max_amount": round(available, 2)}


# ---------------------------------------------------------------------------
# Loan lifecycle
# ---------------------------------------------------------------------------

def apply_loan(
    db: Session,
    user_id: int,
    amount: float,
    tenure_months: int,
    annual_rate: float,
    purpose: str = "",
) -> dict:
    """
    Apply for a new loan after eligibility check.
    Creates Loan record with status='pending'.
    """
    eligibility = check_eligibility(db, user_id, amount)
    if not eligibility["eligible"]:
        raise LoanError(eligibility["reason"])

    emi = calculate_emi(amount, annual_rate, tenure_months)
    now = datetime.utcnow()

    loan = Loan(
        user_id=user_id,
        principal=Decimal(str(amount)),
        outstanding_balance=Decimal(str(amount)),
        annual_rate=Decimal(str(annual_rate)),
        tenure_months=tenure_months,
        emi_amount=Decimal(str(emi)),
        purpose=purpose,
        status="pending",
        applied_at=now,
    )
    db.add(loan)
    db.commit()
    db.refresh(loan)

    return _serialize_loan(loan)


def approve_loan(db: Session, loan_id: int) -> dict:
    """
    Approve a pending loan (admin/system action).
    Sets status='active', start_date=today, calculates due dates.
    """
    loan = _get_loan(db, loan_id)
    if loan.status != "pending":
        raise LoanError(f"Cannot approve a loan with status '{loan.status}'.")

    loan.status = "active"
    loan.start_date = date.today()
    loan.next_due_date = date.today() + relativedelta(months=1)
    db.commit()
    db.refresh(loan)
    return _serialize_loan(loan)


def repay_loan(
    db: Session,
    loan_id: int,
    user_id: int,
    amount: float,
    account_id: int,
) -> dict:
    """
    Record a loan repayment.
    Deducts from account balance, reduces outstanding_balance.
    Marks loan 'closed' if fully paid.
    """
    loan = _get_loan(db, loan_id)

    if loan.user_id != user_id:
        raise LoanError("This loan does not belong to you.")
    if loan.status != "active":
        raise LoanError(f"Loan is not active (status: {loan.status}).")

    account = db.query(Account).filter(
        Account.id == account_id, Account.user_id == user_id
    ).first()
    if not account:
        raise LoanError("Account not found.")

    repay_amount = Decimal(str(amount))
    if account.balance < repay_amount:
        raise LoanError("Insufficient balance in account.")

    account.balance -= repay_amount
    loan.outstanding_balance -= repay_amount

    if loan.outstanding_balance <= Decimal("0"):
        loan.outstanding_balance = Decimal("0")
        loan.status = "closed"
        loan.closed_at = datetime.utcnow()
    else:
        loan.next_due_date = loan.next_due_date + relativedelta(months=1)

    repayment = LoanRepayment(
        loan_id=loan.id,
        amount=repay_amount,
        paid_at=datetime.utcnow(),
    )
    db.add(repayment)
    db.commit()
    db.refresh(loan)

    return {
        "loan_id": loan.id,
        "amount_paid": float(repay_amount),
        "outstanding_balance": float(loan.outstanding_balance),
        "status": loan.status,
    }


def get_user_loans(db: Session, user_id: int) -> list[dict]:
    loans = (
        db.query(Loan)
        .filter(Loan.user_id == user_id)
        .order_by(Loan.applied_at.desc())
        .all()
    )
    return [_serialize_loan(l) for l in loans]


def get_loan_schedule(db: Session, loan_id: int, user_id: int) -> list[dict]:
    """Generate full repayment schedule for a loan."""
    loan = _get_loan(db, loan_id)
    if loan.user_id != user_id:
        raise LoanError("Access denied.")

    schedule = []
    balance = float(loan.principal)
    monthly_rate = float(loan.annual_rate) / 1200
    emi = float(loan.emi_amount)
    due = loan.start_date or date.today()

    for month in range(1, loan.tenure_months + 1):
        interest = balance * monthly_rate
        principal_part = emi - interest
        balance = max(0.0, balance - principal_part)
        due = due + relativedelta(months=1)
        schedule.append({
            "month": month,
            "due_date": due.isoformat(),
            "emi": round(emi, 2),
            "principal": round(principal_part, 2),
            "interest": round(interest, 2),
            "balance": round(balance, 2),
        })

    return schedule


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_loan(db: Session, loan_id: int) -> Loan:
    loan = db.query(Loan).filter(Loan.id == loan_id).first()
    if not loan:
        raise LoanError("Loan not found.")
    return loan


def _serialize_loan(loan: Loan) -> dict:
    return {
        "id": loan.id,
        "user_id": loan.user_id,
        "principal": float(loan.principal),
        "outstanding_balance": float(loan.outstanding_balance),
        "annual_rate": float(loan.annual_rate),
        "tenure_months": loan.tenure_months,
        "emi_amount": float(loan.emi_amount),
        "purpose": loan.purpose,
        "status": loan.status,
        "applied_at": loan.applied_at.isoformat() if loan.applied_at else None,
        "start_date": loan.start_date.isoformat() if loan.start_date else None,
        "next_due_date": loan.next_due_date.isoformat() if loan.next_due_date else None,
        "closed_at": loan.closed_at.isoformat() if loan.closed_at else None,
    }