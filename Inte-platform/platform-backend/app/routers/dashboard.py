from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Integration, APIEndpoint, IntegrationStatus
from app.auth import get_current_user

router = APIRouter()

@router.get("/stats")
def get_stats(db: Session = Depends(get_db), _=Depends(get_current_user)):
    api_count = db.query(APIEndpoint).filter(APIEndpoint.is_active == True).count()
    active = db.query(Integration).filter(Integration.status == IntegrationStatus.DEPLOYED).count()
    total = db.query(Integration).count()
    errors = db.query(Integration).filter(Integration.status == IntegrationStatus.ERROR).count()
    error_rate = (errors / total * 100) if total > 0 else 0
    return {
        "apiCount": api_count,
        "activeIntegrations": active,
        "errorRate": round(error_rate, 2),
        "throughput": 1250
    }
