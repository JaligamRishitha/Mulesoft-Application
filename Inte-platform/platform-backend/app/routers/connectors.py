from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime
import httpx

from app.database import get_db
from app.models import Connector
from app.auth import get_current_user

router = APIRouter(prefix="/connectors", tags=["connectors"])

class ConnectorCreate(BaseModel):
    connector_name: str
    connector_type: str
    connection_config: Dict[str, Any]
    credentials_ref: Optional[str] = None
    health_check_url: Optional[str] = None

class ConnectorUpdate(BaseModel):
    connector_name: Optional[str] = None
    connection_config: Optional[Dict[str, Any]] = None
    credentials_ref: Optional[str] = None
    health_check_url: Optional[str] = None
    status: Optional[str] = None

class ConnectorResponse(BaseModel):
    id: int
    connector_name: str
    connector_type: str
    connection_config: Optional[Dict[str, Any]]
    credentials_ref: Optional[str]
    status: Optional[str]
    health_check_url: Optional[str]
    last_health_check: Optional[datetime]
    health_status: Optional[str]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True

# Connector type definitions with config schemas
CONNECTOR_TYPES = {
    "sap": {
        "name": "SAP",
        "icon": "🏢",
        "description": "Connect to remote SAP backend application",
        "config_schema": {
            "server_url": {"type": "string", "label": "Server URL", "required": True, "placeholder": "http://your-server-ip:port"}
        }
    },
    "salesforce": {
        "name": "Salesforce",
        "icon": "☁️",
        "description": "Connect to remote Salesforce backend application",
        "config_schema": {
            "server_url": {"type": "string", "label": "Server URL", "required": True, "placeholder": "http://your-server-ip:port"}
        }
    },
    "servicenow": {
        "name": "ServiceNow",
        "icon": "🎫",
        "description": "Connect to remote ServiceNow ITSM application for tickets and approvals",
        "config_schema": {
            "server_url": {"type": "string", "label": "Server URL", "required": True, "placeholder": "http://your-server-ip:port"}
        }
    },
    "database": {
        "name": "Database",
        "icon": "🗄️",
        "description": "Connect to remote Database backend application",
        "config_schema": {
            "server_url": {"type": "string", "label": "Server URL", "required": True, "placeholder": "http://your-server-ip:port"}
        }
    },
    "http": {
        "name": "HTTP/REST",
        "icon": "🌐",
        "description": "Connect to remote HTTP/REST backend application",
        "config_schema": {
            "server_url": {"type": "string", "label": "Server URL", "required": True, "placeholder": "http://your-server-ip:port"}
        }
    },
    "soap": {
        "name": "SOAP",
        "icon": "📄",
        "description": "Connect to remote SOAP backend application",
        "config_schema": {
            "server_url": {"type": "string", "label": "Server URL", "required": True, "placeholder": "http://your-server-ip:port"}
        }
    },
    "kafka": {
        "name": "Apache Kafka",
        "icon": "📨",
        "description": "Connect to remote Kafka backend application",
        "config_schema": {
            "server_url": {"type": "string", "label": "Server URL", "required": True, "placeholder": "http://your-server-ip:port"}
        }
    },
    "ftp": {
        "name": "FTP/SFTP",
        "icon": "📁",
        "description": "Connect to remote FTP/SFTP backend application",
        "config_schema": {
            "server_url": {"type": "string", "label": "Server URL", "required": True, "placeholder": "http://your-server-ip:port"}
        }
    },
    "email": {
        "name": "Email",
        "icon": "📧",
        "description": "Connect to remote Email backend application",
        "config_schema": {
            "server_url": {"type": "string", "label": "Server URL", "required": True, "placeholder": "http://your-server-ip:port"}
        }
    },
    "aws_s3": {
        "name": "AWS S3",
        "icon": "🪣",
        "description": "Connect to remote AWS S3 backend application",
        "config_schema": {
            "server_url": {"type": "string", "label": "Server URL", "required": True, "placeholder": "http://your-server-ip:port"}
        }
    },
    "azure_blob": {
        "name": "Azure Blob Storage",
        "icon": "☁️",
        "description": "Connect to remote Azure Blob backend application",
        "config_schema": {
            "server_url": {"type": "string", "label": "Server URL", "required": True, "placeholder": "http://your-server-ip:port"}
        }
    }
}

@router.get("/types")
async def get_connector_types():
    """Get all available connector types with their config schemas"""
    return CONNECTOR_TYPES

@router.get("/", response_model=List[ConnectorResponse])
async def list_connectors(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    """List all connectors"""
    return db.query(Connector).all()

@router.post("/", response_model=ConnectorResponse)
async def create_connector(connector: ConnectorCreate, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    """Create a new connector"""
    db_connector = Connector(
        connector_name=connector.connector_name,
        connector_type=connector.connector_type,
        connection_config=connector.connection_config,
        credentials_ref=connector.credentials_ref,
        health_check_url=connector.health_check_url,
        status="Active"
    )
    db.add(db_connector)
    db.commit()
    db.refresh(db_connector)
    return db_connector

@router.get("/{connector_id}", response_model=ConnectorResponse)
async def get_connector(connector_id: int, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    """Get connector by ID"""
    connector = db.query(Connector).filter(Connector.id == connector_id).first()
    if not connector:
        raise HTTPException(status_code=404, detail="Connector not found")
    return connector

@router.put("/{connector_id}", response_model=ConnectorResponse)
async def update_connector(connector_id: int, update: ConnectorUpdate, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    """Update a connector"""
    connector = db.query(Connector).filter(Connector.id == connector_id).first()
    if not connector:
        raise HTTPException(status_code=404, detail="Connector not found")

    if update.connector_name:
        connector.connector_name = update.connector_name
    if update.connection_config:
        connector.connection_config = update.connection_config
    if update.credentials_ref:
        connector.credentials_ref = update.credentials_ref
    if update.health_check_url:
        connector.health_check_url = update.health_check_url
    if update.status:
        connector.status = update.status

    db.commit()
    db.refresh(connector)
    return connector

@router.delete("/{connector_id}")
async def delete_connector(connector_id: int, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    """Delete a connector"""
    connector = db.query(Connector).filter(Connector.id == connector_id).first()
    if not connector:
        raise HTTPException(status_code=404, detail="Connector not found")
    
    db.delete(connector)
    db.commit()
    return {"message": "Connector deleted"}

@router.post("/{connector_id}/test")
async def test_connector(connector_id: int, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    """Test connector connectivity"""
    connector = db.query(Connector).filter(Connector.id == connector_id).first()
    if not connector:
        raise HTTPException(status_code=404, detail="Connector not found")

    config = connector.connection_config or {}
    success = False
    message = ""

    try:
        server_url = config.get("server_url", "").rstrip("/")
        if not server_url:
            message = "Server URL is not configured"
        else:
            async with httpx.AsyncClient(timeout=10, verify=False) as client:
                response = await client.get(server_url)
                success = response.status_code < 500
                message = f"Connected to remote server (HTTP {response.status_code})"

        # Update connector status
        connector.status = "Active" if success else "Error"
        connector.health_status = "healthy" if success else "unhealthy"
        connector.last_health_check = datetime.utcnow()
        db.commit()

    except Exception as e:
        connector.status = "Error"
        connector.health_status = "unhealthy"
        connector.last_health_check = datetime.utcnow()
        db.commit()
        message = str(e)

    return {"success": success, "message": message, "status": connector.status}
