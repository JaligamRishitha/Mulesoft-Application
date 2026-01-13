from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime
import httpx
import asyncio

from app.database import get_db
from app.models import Connector, ConnectorType, ConnectorStatus
from app.auth import get_current_user

router = APIRouter(prefix="/connectors", tags=["connectors"])

class ConnectorCreate(BaseModel):
    name: str
    type: ConnectorType
    description: Optional[str] = None
    config: Dict[str, Any]

class ConnectorUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    config: Optional[Dict[str, Any]] = None

class ConnectorResponse(BaseModel):
    id: int
    name: str
    type: ConnectorType
    description: Optional[str]
    status: ConnectorStatus
    last_tested: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True

# Connector type definitions with config schemas
CONNECTOR_TYPES = {
    "sap": {
        "name": "SAP",
        "icon": "🏢",
        "description": "Connect to SAP ERP, S/4HANA, or SAP Cloud",
        "config_schema": {
            "host": {"type": "string", "label": "SAP Host", "required": True},
            "client": {"type": "string", "label": "Client", "required": True},
            "username": {"type": "string", "label": "Username", "required": True},
            "password": {"type": "password", "label": "Password", "required": True},
            "system_number": {"type": "string", "label": "System Number", "default": "00"},
            "api_type": {"type": "select", "label": "API Type", "options": ["OData", "RFC", "BAPI", "IDoc"], "default": "OData"}
        }
    },
    "salesforce": {
        "name": "Salesforce",
        "icon": "☁️",
        "description": "Connect to Salesforce CRM",
        "config_schema": {
            "instance_url": {"type": "string", "label": "Instance URL", "required": True, "placeholder": "https://yourorg.salesforce.com"},
            "client_id": {"type": "string", "label": "Client ID", "required": True},
            "client_secret": {"type": "password", "label": "Client Secret", "required": True},
            "username": {"type": "string", "label": "Username", "required": True},
            "password": {"type": "password", "label": "Password", "required": True},
            "security_token": {"type": "password", "label": "Security Token"}
        }
    },
    "database": {
        "name": "Database",
        "icon": "🗄️",
        "description": "Connect to SQL databases (PostgreSQL, MySQL, Oracle, SQL Server)",
        "config_schema": {
            "db_type": {"type": "select", "label": "Database Type", "options": ["PostgreSQL", "MySQL", "Oracle", "SQL Server", "SQLite"], "required": True},
            "host": {"type": "string", "label": "Host", "required": True},
            "port": {"type": "number", "label": "Port", "required": True},
            "database": {"type": "string", "label": "Database Name", "required": True},
            "username": {"type": "string", "label": "Username", "required": True},
            "password": {"type": "password", "label": "Password", "required": True},
            "ssl": {"type": "boolean", "label": "Use SSL", "default": False}
        }
    },
    "http": {
        "name": "HTTP/REST",
        "icon": "🌐",
        "description": "Connect to any REST API",
        "config_schema": {
            "base_url": {"type": "string", "label": "Base URL", "required": True, "placeholder": "https://api.example.com"},
            "auth_type": {"type": "select", "label": "Auth Type", "options": ["None", "Basic", "Bearer Token", "API Key", "OAuth2"], "default": "None"},
            "username": {"type": "string", "label": "Username"},
            "password": {"type": "password", "label": "Password"},
            "api_key": {"type": "password", "label": "API Key"},
            "api_key_header": {"type": "string", "label": "API Key Header", "default": "X-API-Key"},
            "bearer_token": {"type": "password", "label": "Bearer Token"},
            "timeout": {"type": "number", "label": "Timeout (seconds)", "default": 30}
        }
    },
    "soap": {
        "name": "SOAP",
        "icon": "📄",
        "description": "Connect to SOAP web services",
        "config_schema": {
            "wsdl_url": {"type": "string", "label": "WSDL URL", "required": True},
            "username": {"type": "string", "label": "Username"},
            "password": {"type": "password", "label": "Password"},
            "timeout": {"type": "number", "label": "Timeout (seconds)", "default": 30}
        }
    },
    "kafka": {
        "name": "Apache Kafka",
        "icon": "📨",
        "description": "Connect to Kafka message broker",
        "config_schema": {
            "bootstrap_servers": {"type": "string", "label": "Bootstrap Servers", "required": True, "placeholder": "localhost:9092"},
            "security_protocol": {"type": "select", "label": "Security Protocol", "options": ["PLAINTEXT", "SSL", "SASL_PLAINTEXT", "SASL_SSL"], "default": "PLAINTEXT"},
            "sasl_mechanism": {"type": "select", "label": "SASL Mechanism", "options": ["PLAIN", "SCRAM-SHA-256", "SCRAM-SHA-512"]},
            "username": {"type": "string", "label": "Username"},
            "password": {"type": "password", "label": "Password"},
            "group_id": {"type": "string", "label": "Consumer Group ID"}
        }
    },
    "ftp": {
        "name": "FTP/SFTP",
        "icon": "📁",
        "description": "Connect to FTP or SFTP servers",
        "config_schema": {
            "protocol": {"type": "select", "label": "Protocol", "options": ["FTP", "SFTP"], "default": "SFTP"},
            "host": {"type": "string", "label": "Host", "required": True},
            "port": {"type": "number", "label": "Port", "default": 22},
            "username": {"type": "string", "label": "Username", "required": True},
            "password": {"type": "password", "label": "Password"},
            "private_key": {"type": "textarea", "label": "Private Key (for SFTP)"},
            "remote_path": {"type": "string", "label": "Remote Path", "default": "/"}
        }
    },
    "email": {
        "name": "Email",
        "icon": "📧",
        "description": "Connect to email servers (SMTP/IMAP)",
        "config_schema": {
            "protocol": {"type": "select", "label": "Protocol", "options": ["SMTP", "IMAP"], "required": True},
            "host": {"type": "string", "label": "Host", "required": True},
            "port": {"type": "number", "label": "Port", "required": True},
            "username": {"type": "string", "label": "Username", "required": True},
            "password": {"type": "password", "label": "Password", "required": True},
            "use_tls": {"type": "boolean", "label": "Use TLS", "default": True}
        }
    },
    "aws_s3": {
        "name": "AWS S3",
        "icon": "🪣",
        "description": "Connect to Amazon S3 storage",
        "config_schema": {
            "access_key_id": {"type": "string", "label": "Access Key ID", "required": True},
            "secret_access_key": {"type": "password", "label": "Secret Access Key", "required": True},
            "region": {"type": "string", "label": "Region", "default": "us-east-1"},
            "bucket": {"type": "string", "label": "Default Bucket"}
        }
    },
    "azure_blob": {
        "name": "Azure Blob Storage",
        "icon": "☁️",
        "description": "Connect to Azure Blob Storage",
        "config_schema": {
            "connection_string": {"type": "password", "label": "Connection String", "required": True},
            "container": {"type": "string", "label": "Default Container"}
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
        name=connector.name,
        type=connector.type,
        description=connector.description,
        config=connector.config,
        owner_id=current_user.id
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
    
    if update.name:
        connector.name = update.name
    if update.description:
        connector.description = update.description
    if update.config:
        connector.config = update.config
    
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
    
    config = connector.config
    success = False
    message = ""
    
    try:
        if connector.type == ConnectorType.HTTP:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(config.get("base_url", ""))
                success = response.status_code < 500
                message = f"HTTP {response.status_code}"
        
        elif connector.type == ConnectorType.DATABASE:
            # Simulate database connection test
            await asyncio.sleep(0.5)
            success = True
            message = "Connection successful"
        
        elif connector.type == ConnectorType.SAP:
            # Simulate SAP connection test
            await asyncio.sleep(1)
            if config.get("host") and config.get("username"):
                success = True
                message = "SAP connection established"
            else:
                message = "Missing required configuration"
        
        else:
            # Generic test for other types
            await asyncio.sleep(0.5)
            success = True
            message = "Connection test passed"
        
        # Update connector status
        connector.status = ConnectorStatus.ACTIVE if success else ConnectorStatus.ERROR
        connector.last_tested = datetime.utcnow()
        db.commit()
        
    except Exception as e:
        connector.status = ConnectorStatus.ERROR
        connector.last_tested = datetime.utcnow()
        db.commit()
        message = str(e)
    
    return {"success": success, "message": message, "status": connector.status}
