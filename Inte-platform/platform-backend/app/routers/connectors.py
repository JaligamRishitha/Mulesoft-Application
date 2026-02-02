from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime
import httpx
import json

from app.database import get_db
from app.models import Connector
from app.auth import get_current_user

router = APIRouter(prefix="/connectors", tags=["connectors"])

# MCP Client Helper Functions
async def call_mcp_tool(mcp_server_url: str, tool_name: str, arguments: dict = None):
    """Call a tool on the MCP server"""
    async with httpx.AsyncClient(timeout=60, verify=False) as client:
        payload = {
            "tool": tool_name,
            "arguments": arguments or {}
        }
        response = await client.post(f"{mcp_server_url}/call", json=payload)
        return response.json()

async def list_mcp_tools(mcp_server_url: str):
    """List available tools from MCP server"""
    async with httpx.AsyncClient(timeout=30, verify=False) as client:
        response = await client.get(f"{mcp_server_url}/tools")
        return response.json()

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
        "description": "Connect to remote Salesforce backend application or MCP server",
        "config_schema": {
            "server_url": {"type": "string", "label": "Salesforce API URL", "required": False, "placeholder": "http://salesforce-server:port"},
            "mcp_server_url": {"type": "string", "label": "Salesforce MCP URL", "required": False, "placeholder": "http://salesforce-mcp:8095"},
            "mcp_server_name": {"type": "string", "label": "MCP Server Name", "required": False, "placeholder": "salesforce-crm", "default": "salesforce-crm"},
            "use_mcp": {"type": "boolean", "label": "Use MCP Integration", "required": False, "default": True, "description": "Enable MCP-based integration for enhanced tool support"}
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
        # Check if this connector uses MCP server
        mcp_server_url = config.get("mcp_server_url")
        server_url = config.get("server_url", "").rstrip("/")

        if mcp_server_url:
            # Test MCP server connection
            mcp_server_url = mcp_server_url.rstrip("/")
            async with httpx.AsyncClient(timeout=30, verify=False) as client:
                # Try to list tools to verify MCP server is working
                response = await client.get(f"{mcp_server_url}/tools")
                if response.status_code < 500:
                    success = True
                    tools = response.json()
                    tool_count = len(tools.get("tools", tools)) if isinstance(tools, dict) else len(tools)
                    message = f"MCP server connected. {tool_count} tools available."
                else:
                    message = f"MCP server error (HTTP {response.status_code})"
        elif server_url:
            # Direct server connection - try multiple health endpoints
            health_urls = []
            if connector.health_check_url:
                health_urls.append(connector.health_check_url)
            # Try multiple common health endpoints, including the base URL
            health_urls.extend([
                f"{server_url}/api/health",
                f"{server_url}/health",
                f"{server_url}/api/v1/health",
                server_url  # Fallback to base URL
            ])

            async with httpx.AsyncClient(timeout=30, verify=False) as client:
                for health_url in health_urls:
                    try:
                        response = await client.get(health_url)
                        if response.status_code < 500:
                            success = True
                            message = f"Connected to remote server at {health_url} (HTTP {response.status_code})"
                            break
                    except Exception:
                        continue

                if not success:
                    message = f"Could not connect to any health endpoint on {server_url}"
        else:
            message = "No server URL or MCP server URL configured"

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


# MCP Integration Endpoints
@router.post("/{connector_id}/mcp/call")
async def call_connector_mcp_tool(
    connector_id: int,
    tool_name: str = Body(..., embed=True),
    arguments: dict = Body(None, embed=True),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Call an MCP tool through the connector"""
    connector = db.query(Connector).filter(Connector.id == connector_id).first()
    if not connector:
        raise HTTPException(status_code=404, detail="Connector not found")

    config = connector.connection_config or {}
    mcp_server_url = config.get("mcp_server_url")

    if not mcp_server_url:
        raise HTTPException(status_code=400, detail="Connector does not have MCP server configured")

    try:
        result = await call_mcp_tool(mcp_server_url, tool_name, arguments)
        return {"success": True, "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{connector_id}/mcp/tools")
async def list_connector_mcp_tools(
    connector_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """List available MCP tools for the connector"""
    connector = db.query(Connector).filter(Connector.id == connector_id).first()
    if not connector:
        raise HTTPException(status_code=404, detail="Connector not found")

    config = connector.connection_config or {}
    mcp_server_url = config.get("mcp_server_url")

    if not mcp_server_url:
        raise HTTPException(status_code=400, detail="Connector does not have MCP server configured")

    try:
        tools = await list_mcp_tools(mcp_server_url)
        return {"success": True, "tools": tools}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
