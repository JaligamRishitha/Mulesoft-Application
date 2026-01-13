from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from app.database import get_db
from app.models import User
from app.auth import get_password_hash, verify_password, create_access_token, get_current_user

router = APIRouter()

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

@router.post("/register")
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == req.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(email=req.email, hashed_password=get_password_hash(req.password), full_name=req.full_name)
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"message": "Registration successful", "user": {"id": user.id, "email": user.email}}

@router.post("/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email).first()
    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token(data={"sub": user.email})
    return {"token": token, "user": {"id": user.id, "email": user.email, "fullName": user.full_name, "role": user.role}}

@router.get("/me")
def me(current_user: User = Depends(get_current_user)):
    return {"id": current_user.id, "email": current_user.email, "fullName": current_user.full_name, "role": current_user.role}
