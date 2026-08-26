from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from sqlalchemy.orm import Session

from app.db.models import User, AccountType
from app.services.account_service import list_accounts, open_account, get_account
from web.security import get_db, get_current_user_from_token

router = APIRouter(prefix="/api/accounts", tags=["accounts"])

class OpenAccountRequest(BaseModel):
    account_type: str  # CHECKING, SAVINGS, BUSINESS
    initial_deposit: float = 0.0
    holder_name: Optional[str] = ""
    dob: Optional[str] = ""
    nid: Optional[str] = ""
    phone: Optional[str] = ""
    address: Optional[str] = ""
    occupation: Optional[str] = ""
    currency: Optional[str] = "USD"

@router.get("")
def api_list_accounts(current_user: User = Depends(get_current_user_from_token), db: Session = Depends(get_db)):
    accts = list_accounts(db, current_user.id)
    return {"accounts": accts}

@router.post("/open")
def api_open_account(req: OpenAccountRequest, current_user: User = Depends(get_current_user_from_token), db: Session = Depends(get_db)):
    try:
        acct_type_enum = AccountType(req.account_type.upper())
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid account type. Choose CHECKING, SAVINGS, or BUSINESS.")

    ok, msg, acct_data = open_account(
        db=db,
        user_id=current_user.id,
        account_type=acct_type_enum,
        initial_deposit=req.initial_deposit,
        holder_name=req.holder_name or current_user.full_name,
        dob=req.dob or "",
        nid=req.nid or "",
        phone=req.phone or current_user.phone or "",
        address=req.address or "",
        occupation=req.occupation or "",
        currency=req.currency or "USD"
    )
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"success": True, "message": msg, "account": acct_data}

@router.get("/{account_id}")
def api_get_account_detail(account_id: UUID, current_user: User = Depends(get_current_user_from_token), db: Session = Depends(get_db)):
    acct = get_account(db, account_id, current_user.id)
    if not acct:
        raise HTTPException(status_code=404, detail="Account not found")
    from app.services.account_service import _to_dict
    return {"account": _to_dict(acct)}
