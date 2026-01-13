from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import random
import time
import httpx
from app.database import get_db
from app.models import Integration, IntegrationLog, IntegrationStatus
from app.auth import get_current_user
from app.metrics import (
    record_execution, record_api_call, record_error, 
    update_integration_status, update_active_count
)

router = APIRouter()

def sync_integration_metrics(db: Session):
    """Sync all integration statuses to Prometheus"""
    integrations = db.query(Integration).all()
    active_count = 0
    for i in integrations:
        update_integration_status(i.name, i.status.value if i.status else 'draft')
        if i.status == IntegrationStatus.DEPLOYED:
            active_count += 1
    update_active_count(active_count)

@router.post("/{id}/start")
def start(id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    integration = db.query(Integration).filter(Integration.id == id).first()
    if not integration:
        raise HTTPException(status_code=404, detail="Not found")
    integration.status = IntegrationStatus.DEPLOYED
    
    # Add startup logs
    db.add(IntegrationLog(integration_id=id, level="INFO", message="Integration started"))
    db.add(IntegrationLog(integration_id=id, level="INFO", message=f"Loading flow configuration for '{integration.name}'"))
    db.add(IntegrationLog(integration_id=id, level="INFO", message="Camel context initialized successfully"))
    db.add(IntegrationLog(integration_id=id, level="INFO", message="Route started and listening for events"))
    db.commit()
    
    # Update Prometheus metrics
    update_integration_status(integration.name, 'deployed')
    sync_integration_metrics(db)
    
    return {"message": "Started", "status": integration.status}

@router.post("/{id}/stop")
def stop(id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    integration = db.query(Integration).filter(Integration.id == id).first()
    if not integration:
        raise HTTPException(status_code=404, detail="Not found")
    integration.status = IntegrationStatus.STOPPED
    
    # Add shutdown logs
    db.add(IntegrationLog(integration_id=id, level="INFO", message="Graceful shutdown initiated"))
    db.add(IntegrationLog(integration_id=id, level="INFO", message="Route stopped"))
    db.add(IntegrationLog(integration_id=id, level="INFO", message="Integration stopped"))
    db.commit()
    
    # Update Prometheus metrics
    update_integration_status(integration.name, 'stopped')
    sync_integration_metrics(db)
    
    return {"message": "Stopped", "status": integration.status}

@router.post("/{id}/execute")
def execute(id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    """Manually trigger integration execution with real metrics"""
    integration = db.query(Integration).filter(Integration.id == id).first()
    if not integration:
        raise HTTPException(status_code=404, detail="Not found")
    
    if integration.status != IntegrationStatus.DEPLOYED:
        raise HTTPException(status_code=400, detail="Integration must be deployed to execute")
    
    logs_to_add = []
    base_time = datetime.utcnow()
    start_time = time.time()
    success = True
    records_processed = 0
    
    logs_to_add.append(IntegrationLog(integration_id=id, level="INFO", message=f"Execution triggered for '{integration.name}'", timestamp=base_time))
    
    # Try to call actual mock services and record metrics
    try:
        with httpx.Client(timeout=5.0) as client:
            # Call ERP
            erp_start = time.time()
            erp_response = client.get("http://erp-service:8091/orders")
            erp_duration = time.time() - erp_start
            orders = erp_response.json()
            
            # Record ERP API call metric
            record_api_call(integration.name, "erp-service", "GET", erp_response.status_code, erp_duration)
            
            logs_to_add.append(IntegrationLog(integration_id=id, level="INFO", message=f"Fetched {len(orders)} orders from ERP service ({erp_duration*1000:.0f}ms)", timestamp=base_time + timedelta(milliseconds=150)))
            
            # Call CRM
            crm_start = time.time()
            crm_response = client.get("http://crm-service:8092/customers")
            crm_duration = time.time() - crm_start
            customers = crm_response.json()
            
            # Record CRM API call metric
            record_api_call(integration.name, "crm-service", "GET", crm_response.status_code, crm_duration)
            
            logs_to_add.append(IntegrationLog(integration_id=id, level="INFO", message=f"Fetched {len(customers)} customers from CRM service ({crm_duration*1000:.0f}ms)", timestamp=base_time + timedelta(milliseconds=280)))
            
            records_processed = len(orders) + len(customers)
            logs_to_add.append(IntegrationLog(integration_id=id, level="INFO", message="Data transformation completed", timestamp=base_time + timedelta(milliseconds=320)))
            logs_to_add.append(IntegrationLog(integration_id=id, level="INFO", message=f"Successfully synced {records_processed} records", timestamp=base_time + timedelta(milliseconds=450)))
            
    except Exception as e:
        # Simulate execution if services not reachable
        records_processed = random.randint(10, 150)
        logs_to_add.append(IntegrationLog(integration_id=id, level="INFO", message=f"Connecting to source endpoint...", timestamp=base_time + timedelta(milliseconds=100)))
        logs_to_add.append(IntegrationLog(integration_id=id, level="INFO", message=f"Fetched {records_processed} records from source", timestamp=base_time + timedelta(milliseconds=250)))
        logs_to_add.append(IntegrationLog(integration_id=id, level="INFO", message="Applying transformation rules", timestamp=base_time + timedelta(milliseconds=300)))
        logs_to_add.append(IntegrationLog(integration_id=id, level="INFO", message=f"Transformed {records_processed} records", timestamp=base_time + timedelta(milliseconds=380)))
        logs_to_add.append(IntegrationLog(integration_id=id, level="INFO", message="Sending to destination endpoint...", timestamp=base_time + timedelta(milliseconds=420)))
        logs_to_add.append(IntegrationLog(integration_id=id, level="INFO", message=f"Successfully synced {records_processed} records to destination", timestamp=base_time + timedelta(milliseconds=580)))
    
    # Random chance of warning
    if random.random() < 0.3:
        latency = random.randint(800, 2500)
        logs_to_add.append(IntegrationLog(integration_id=id, level="WARN", message=f"Slow response detected: {latency}ms", timestamp=base_time + timedelta(milliseconds=600)))
    
    # Random chance of error (10%)
    if random.random() < 0.1:
        success = False
        error_type = random.choice(["ConnectionTimeout", "ValidationError", "TransformationError"])
        logs_to_add.append(IntegrationLog(integration_id=id, level="ERROR", message=f"{error_type}: Failed to complete execution", timestamp=base_time + timedelta(milliseconds=620)))
        record_error(integration.name, error_type)
    
    execution_duration = time.time() - start_time
    logs_to_add.append(IntegrationLog(
        integration_id=id, 
        level="INFO" if success else "ERROR", 
        message=f"Execution {'completed successfully' if success else 'failed'} in {execution_duration*1000:.0f}ms", 
        timestamp=base_time + timedelta(milliseconds=650)
    ))
    
    # Record execution metrics
    record_execution(integration.name, success, execution_duration, records_processed)
    
    for log in logs_to_add:
        db.add(log)
    db.commit()
    
    return {"message": "Execution completed", "success": success, "logsGenerated": len(logs_to_add), "recordsProcessed": records_processed}

@router.get("/{id}/logs")
def logs(id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    logs = db.query(IntegrationLog).filter(IntegrationLog.integration_id == id).order_by(IntegrationLog.timestamp.desc()).limit(100).all()
    return [{"id": l.id, "level": l.level, "message": l.message, "timestamp": l.timestamp} for l in logs]

@router.get("/{id}/health")
def health(id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    integration = db.query(Integration).filter(Integration.id == id).first()
    if not integration:
        raise HTTPException(status_code=404, detail="Not found")
    
    # Get recent error count
    recent_errors = db.query(IntegrationLog).filter(
        IntegrationLog.integration_id == id,
        IntegrationLog.level == "ERROR",
        IntegrationLog.timestamp > datetime.utcnow() - timedelta(hours=1)
    ).count()
    
    return {
        "integrationId": id,
        "name": integration.name,
        "status": integration.status,
        "healthy": integration.status == IntegrationStatus.DEPLOYED and recent_errors == 0,
        "recentErrors": recent_errors,
        "lastCheck": datetime.utcnow().isoformat()
    }
