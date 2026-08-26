from fastapi import APIRouter, Depends, HTTPException, status, Response
from pydantic import BaseModel, EmailStr
from typing import Optional
from sqlalchemy.orm import Session

from app.db.models import User
from app.services.auth_service import register_user, login_user
from app.services.pin_service import has_pin, set_pin, verify_user_pin, is_pin_locked
from web.security import get_db, create_access_token, get_current_user_from_token

router = APIRouter(prefix="/api/auth", tags=["auth"])

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    phone: Optional[str] = ""

class LoginRequest(BaseModel):
    email: str
    password: str

class PinRequest(BaseModel):
    pin: str

@router.post("/register")
def api_register(req: RegisterRequest, response: Response, db: Session = Depends(get_db)):
    ok, msg, session_user = register_user(db, req.email, req.password, req.full_name, req.phone or "")
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    
    token = create_access_token({"sub": str(session_user.id), "email": session_user.email})
    response.set_cookie(key="access_token", value=f"Bearer {token}", httponly=True, max_age=604800, samesite="lax")
    return {
        "success": True,
        "message": msg,
        "token": token,
        "user": {
            "id": str(session_user.id),
            "email": session_user.email,
            "full_name": session_user.full_name,
            "has_pin": False
        }
    }

@router.post("/login")
def api_login(req: LoginRequest, response: Response, db: Session = Depends(get_db)):
    ok, msg, session_user = login_user(db, req.email, req.password)
    if not ok:
        raise HTTPException(status_code=401, detail=msg)
    
    pin_status = has_pin(db, session_user.id)
    token = create_access_token({"sub": str(session_user.id), "email": session_user.email})
    response.set_cookie(key="access_token", value=f"Bearer {token}", httponly=True, max_age=604800, samesite="lax")
    return {
        "success": True,
        "message": msg,
        "token": token,
        "user": {
            "id": str(session_user.id),
            "email": session_user.email,
            "full_name": session_user.full_name,
            "has_pin": pin_status
        }
    }

@router.post("/logout")
def api_logout(response: Response):
    response.delete_cookie("access_token")
    return {"success": True, "message": "Logged out successfully"}

@router.get("/me")
def api_me(current_user: User = Depends(get_current_user_from_token), db: Session = Depends(get_db)):
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "full_name": current_user.full_name,
        "phone": current_user.phone or "",
        "is_admin": current_user.is_admin,
        "has_pin": has_pin(db, current_user.id),
        "is_pin_locked": is_pin_locked(db, current_user.id)
    }

@router.post("/pin/set")
def api_set_pin(req: PinRequest, current_user: User = Depends(get_current_user_from_token), db: Session = Depends(get_db)):
    ok, msg = set_pin(db, current_user.id, req.pin)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"success": True, "message": msg}

@router.post("/pin/verify")
def api_verify_pin(req: PinRequest, current_user: User = Depends(get_current_user_from_token), db: Session = Depends(get_db)):
    ok, msg = verify_user_pin(db, current_user.id, req.pin)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"success": True, "message": msg}
