from fastapi import FastAPI
from datetime import datetime

app = FastAPI(title="Mock ITSM Service")

@app.get("/")
def root():
    return {"service": "ITSM Mock API", "version": "1.0.0", "endpoints": ["/tickets", "/incidents", "/changes", "/health"]}

@app.get("/tickets")
def get_tickets():
    return [
        {"id": "TKT-001", "title": "API Gateway Timeout", "priority": "high", "status": "open", "assignee": "DevOps Team", "created": "2024-01-10"},
        {"id": "TKT-002", "title": "Integration Sync Failure", "priority": "critical", "status": "in-progress", "assignee": "Integration Team", "created": "2024-01-12"},
        {"id": "TKT-003", "title": "Dashboard Loading Slow", "priority": "medium", "status": "open", "assignee": "Frontend Team", "created": "2024-01-13"},
        {"id": "TKT-004", "title": "SSL Certificate Renewal", "priority": "high", "status": "resolved", "assignee": "Security Team", "created": "2024-01-08"},
        {"id": "TKT-005", "title": "Database Connection Pool", "priority": "medium", "status": "closed", "assignee": "DBA Team", "created": "2024-01-05"}
    ]

@app.get("/incidents")
def get_incidents():
    return [
        {"id": "INC-001", "title": "Production Outage - API Gateway", "severity": "P1", "status": "resolved", "duration": "45 min"},
        {"id": "INC-002", "title": "Data Sync Delay", "severity": "P2", "status": "investigating", "duration": "ongoing"},
        {"id": "INC-003", "title": "Authentication Service Degraded", "severity": "P3", "status": "monitoring", "duration": "2 hours"}
    ]

@app.get("/changes")
def get_changes():
    return [
        {"id": "CHG-001", "title": "Deploy v2.5.0 to Production", "status": "approved", "scheduledDate": "2024-01-20", "risk": "medium"},
        {"id": "CHG-002", "title": "Database Schema Migration", "status": "pending", "scheduledDate": "2024-01-25", "risk": "high"},
        {"id": "CHG-003", "title": "Kong Gateway Upgrade", "status": "implemented", "scheduledDate": "2024-01-15", "risk": "low"}
    ]

@app.get("/health")
def health():
    return {"status": "healthy", "service": "itsm-mock", "timestamp": datetime.utcnow().isoformat()}
