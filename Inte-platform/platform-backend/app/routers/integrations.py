from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import yaml
from datetime import datetime, timezone, timedelta
from app.database import get_db
from app.models import Integration, IntegrationStatus, IntegrationLog, User
from app.auth import get_current_user

router = APIRouter()

# IST timezone (UTC+5:30)
IST = timezone(timedelta(hours=5, minutes=30))

class IntegrationCreate(BaseModel):
    name: str
    description: Optional[str] = None
    flowConfig: str

class LogCreate(BaseModel):
    integrationId: int
    level: str
    message: str

@router.get("/")
def list_integrations(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    integrations = db.query(Integration).filter(Integration.owner_id == current_user.id).all()
    return [{"id": i.id, "name": i.name, "description": i.description, "status": i.status, 
             "createdAt": i.created_at, "updatedAt": i.updated_at} for i in integrations]

@router.post("/")
def create_integration(req: IntegrationCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    integration = Integration(name=req.name, description=req.description, flow_config=req.flowConfig, owner_id=current_user.id)
    db.add(integration)
    db.commit()
    db.refresh(integration)
    return {"id": integration.id, "name": integration.name, "status": integration.status}

@router.post("/upload-yaml")
async def upload_yaml(file: UploadFile = File(...), _=Depends(get_current_user)):
    content = await file.read()
    try:
        parsed = yaml.safe_load(content)
        return {"valid": True, "config": parsed}
    except yaml.YAMLError as e:
        raise HTTPException(status_code=400, detail=f"Invalid YAML: {str(e)}")

@router.post("/{id}/validate")
def validate(id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    integration = db.query(Integration).filter(Integration.id == id).first()
    if not integration:
        raise HTTPException(status_code=404, detail="Not found")
    try:
        yaml.safe_load(integration.flow_config)
        return {"valid": True, "message": "Configuration is valid"}
    except:
        return {"valid": False, "message": "Invalid configuration"}

@router.post("/{id}/deploy")
def deploy(id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    integration = db.query(Integration).filter(Integration.id == id).first()
    if not integration:
        raise HTTPException(status_code=404, detail="Not found")
    integration.status = IntegrationStatus.DEPLOYED
    db.commit()
    return {"message": "Deployed", "status": integration.status}

@router.delete("/{id}")
def delete(id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    integration = db.query(Integration).filter(Integration.id == id).first()
    if not integration:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(integration)
    db.commit()
    return {"message": "Deleted"}

@router.post("/logs")
def create_log(req: LogCreate, db: Session = Depends(get_db)):
    """
    Create a new integration log entry (called by Integration Engine)
    No authentication required for internal service calls
    """
    # Convert to IST
    ist_time = datetime.now(IST)
    
    log = IntegrationLog(
        integration_id=req.integrationId,
        level=req.level,
        message=req.message,
        timestamp=ist_time
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return {"id": log.id, "message": "Log created", "timestamp": ist_time.isoformat()}

@router.get("/{id}/logs")
def get_logs(id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    """
    Get logs for a specific integration with IST timestamps
    """
    logs = db.query(IntegrationLog).filter(IntegrationLog.integration_id == id).order_by(IntegrationLog.timestamp.desc()).limit(100).all()
    return [{"id": l.id, "level": l.level, "message": l.message, 
             "timestamp": l.timestamp.replace(tzinfo=timezone.utc).astimezone(IST).isoformat()} for l in logs]

