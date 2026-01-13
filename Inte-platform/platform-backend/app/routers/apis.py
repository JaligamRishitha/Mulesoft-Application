from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
import secrets
from app.database import get_db
from app.models import APIEndpoint, APIKey, User
from app.auth import get_current_user

router = APIRouter()

class EndpointCreate(BaseModel):
    name: str
    path: str
    method: str
    rateLimit: int = 100
    ipWhitelist: Optional[List[str]] = []
    requiresAuth: bool = True

class KeyCreate(BaseModel):
    name: str

@router.get("/endpoints")
def list_endpoints(db: Session = Depends(get_db), _=Depends(get_current_user)):
    endpoints = db.query(APIEndpoint).all()
    return [{"id": e.id, "name": e.name, "path": e.path, "method": e.method, "rateLimit": e.rate_limit, 
             "ipWhitelist": e.ip_whitelist or [], "requiresAuth": e.requires_auth, "isActive": e.is_active} for e in endpoints]

@router.post("/endpoints")
def create_endpoint(req: EndpointCreate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    endpoint = APIEndpoint(name=req.name, path=req.path, method=req.method, rate_limit=req.rateLimit, 
                           ip_whitelist=req.ipWhitelist, requires_auth=req.requiresAuth)
    db.add(endpoint)
    db.commit()
    db.refresh(endpoint)
    return {"id": endpoint.id, "name": endpoint.name}

@router.delete("/endpoints/{id}")
def delete_endpoint(id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    endpoint = db.query(APIEndpoint).filter(APIEndpoint.id == id).first()
    if not endpoint:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(endpoint)
    db.commit()
    return {"message": "Deleted"}

@router.get("/keys")
def list_keys(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    keys = db.query(APIKey).filter(APIKey.user_id == current_user.id).all()
    return [{"id": k.id, "key": k.key, "name": k.name, "isActive": k.is_active, "createdAt": k.created_at} for k in keys]

@router.post("/keys")
def create_key(req: KeyCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    key = APIKey(key=secrets.token_hex(32), name=req.name, user_id=current_user.id)
    db.add(key)
    db.commit()
    db.refresh(key)
    return {"id": key.id, "key": key.key, "name": key.name}

@router.delete("/keys/{id}")
def revoke_key(id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    key = db.query(APIKey).filter(APIKey.id == id, APIKey.user_id == current_user.id).first()
    if not key:
        raise HTTPException(status_code=404, detail="Not found")
    key.is_active = False
    db.commit()
    return {"message": "Revoked"}
