"""
statement_service.py
Generate account statements (monthly / date-range).
Supports export to plain text and CSV.
"""

import csv
import io
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from sqlalchemy.orm import Session
from db.models import Account, Transaction


class StatementError(Exception):
    pass


# ---------------------------------------------------------------------------
# Core statement builder
# ---------------------------------------------------------------------------

def generate_statement(
    db: Session,
    user_id: int,
    account_id: int,
    start_date: date,
    end_date: date,
) -> dict:
    """
    Build a full statement dict for one account over a date range.
    Includes opening balance, all transactions, closing balance.
    """
    account = db.query(Account).filter(
        Account.id == account_id,
        Account.user_id == user_id,
    ).first()

    if not account:
        raise StatementError("Account not found or access denied.")

    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt   = datetime.combine(end_date,   datetime.max.time())

    # Transactions in range
    txns = (
        db.query(Transaction)
        .filter(
            Transaction.account_id == account_id,
            Transaction.created_at >= start_dt,
            Transaction.created_at <= end_dt,
        )
        .order_by(Transaction.created_at.asc())
        .all()
    )

    # Opening balance = current balance minus net of transactions in range
    net_in_range = sum(
        float(t.amount) if t.type == "credit" else -float(t.amount)
        for t in txns
    )
    opening_balance = float(account.balance) - net_in_range
    closing_balance = float(account.balance)

    # Build running balance
    rows = []
    running = opening_balance
    for t in txns:
        if t.type == "credit":
            running += float(t.amount)
        else:
            running -= float(t.amount)
        rows.append({
            "date": t.created_at.strftime("%Y-%m-%d"),
            "time": t.created_at.strftime("%H:%M:%S"),
            "type": t.type,
            "amount": float(t.amount),
            "description": t.description or "",
            "balance": round(running, 2),
        })

    total_credit = sum(r["amount"] for r in rows if r["type"] == "credit")
    total_debit  = sum(r["amount"] for r in rows if r["type"] == "debit")

    return {
        "account_number": account.account_number,
        "account_holder": account.holder_name if hasattr(account, "holder_name") else "",
        "account_type": account.account_type if hasattr(account, "account_type") else "",
        "period": {
            "from": start_date.isoformat(),
            "to": end_date.isoformat(),
        },
        "opening_balance": round(opening_balance, 2),
        "closing_balance": round(closing_balance, 2),
        "total_credit": round(total_credit, 2),
        "total_debit": round(total_debit, 2),
        "transaction_count": len(rows),
        "transactions": rows,
    }


# ---------------------------------------------------------------------------
# Convenience wrappers
# ---------------------------------------------------------------------------

def generate_monthly_statement(
    db: Session,
    user_id: int,
    account_id: int,
    year: int,
    month: int,
) -> dict:
    """Generate statement for a specific calendar month."""
    start = date(year, month, 1)
    end   = start + relativedelta(months=1) - relativedelta(days=1)
    return generate_statement(db, user_id, account_id, start, end)


def generate_last_n_months(
    db: Session,
    user_id: int,
    account_id: int,
    months: int = 3,
) -> dict:
    """Generate statement for the last N months up to today."""
    end   = date.today()
    start = end - relativedelta(months=months)
    return generate_statement(db, user_id, account_id, start, end)


# ---------------------------------------------------------------------------
# Export helpers
# ---------------------------------------------------------------------------

def export_to_csv(statement: dict) -> str:
    """
    Convert a statement dict to CSV string.
    Suitable for saving as .csv or sending to UI.
    """
    output = io.StringIO()
    writer = csv.writer(output)

    # Header block
    writer.writerow(["Account Number", statement["account_number"]])
    writer.writerow(["Period", f"{statement['period']['from']} to {statement['period']['to']}"])
    writer.writerow(["Opening Balance", statement["opening_balance"]])
    writer.writerow(["Closing Balance", statement["closing_balance"]])
    writer.writerow(["Total Credit", statement["total_credit"]])
    writer.writerow(["Total Debit", statement["total_debit"]])
    writer.writerow([])  # blank line

    # Column headers
    writer.writerow(["Date", "Time", "Type", "Amount", "Balance", "Description"])

    # Rows
    for t in statement["transactions"]:
        writer.writerow([
            t["date"],
            t["time"],
            t["type"].upper(),
            f"{t['amount']:.2f}",
            f"{t['balance']:.2f}",
            t["description"],
        ])

    return output.getvalue()


def export_to_text(statement: dict) -> str:
    """
    Convert a statement dict to a plain text bank-statement style string.
    """
    sep = "=" * 60
    lines = [
        sep,
        "ACCOUNT STATEMENT",
        sep,
        f"Account Number : {statement['account_number']}",
        f"Period         : {statement['period']['from']}  →  {statement['period']['to']}",
        f"Opening Balance: {statement['opening_balance']:>12.2f}",
        f"Closing Balance: {statement['closing_balance']:>12.2f}",
        f"Total Credit   : {statement['total_credit']:>12.2f}",
        f"Total Debit    : {statement['total_debit']:>12.2f}",
        sep,
        f"{'Date':<12} {'Type':<8} {'Amount':>12}  {'Balance':>12}  Description",
        "-" * 60,
    ]

    for t in statement["transactions"]:
        lines.append(
            f"{t['date']:<12} {t['type'].upper():<8} {t['amount']:>12.2f}  {t['balance']:>12.2f}  {t['description']}"
        )

    lines.append(sep)
    return "\n".join(lines)


def save_statement_to_file(statement: dict, filepath: str, fmt: str = "csv") -> str:
    """
    Save statement to a file.
    fmt: 'csv' or 'txt'
    Returns the filepath written.
    """
    if fmt == "csv":
        content = export_to_csv(statement)
        mode = "w"
    elif fmt == "txt":
        content = export_to_text(statement)
        mode = "w"
    else:
        raise StatementError(f"Unsupported format: {fmt}. Use 'csv' or 'txt'.")

    with open(filepath, mode, encoding="utf-8") as f:
        f.write(content)

    return filepath