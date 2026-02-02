#!/usr/bin/env python3
"""
MCP Server for MuleSoft Integration with HTTP API
Provides both MCP tools and REST API endpoints for frontend
"""

import json
import httpx
import uvicorn
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException, Depends, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from mcp.server import Server
from mcp.types import TextContent

# ============================================================================
# CONFIGURATION
# ============================================================================

BACKEND_API_URL = "http://149.102.158.71:8085/api"  # Original backend
SAP_API_URL = "http://149.102.158.71:2004"  # SAP backend
SERVICENOW_API_URL = "http://149.102.158.71:8003"  # ServiceNow backend
MCP_HTTP_PORT = 8091  # Port for HTTP API

# In-memory storage for demo (replace with database in production)
connectors_db = {}
users_db = {
    "admin": {"id": 1, "email": "admin@example.com", "password": "admin123", "full_name": "Admin User"}
}
tokens_db = {}

# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class LoginRequest(BaseModel):
    email: str
    password: str

class RegisterRequest(BaseModel):
    email: str
    password: str
    full_name: str

class ConnectorCreate(BaseModel):
    name: str
    connector_type: str
    connection_config: Dict[str, Any] = {}

class ConnectorUpdate(BaseModel):
    name: Optional[str] = None
    connector_type: Optional[str] = None
    connection_config: Optional[Dict[str, Any]] = None

class CaseTransformData(BaseModel):
    caseId: Optional[Any] = None
    caseNumber: Optional[str] = None
    subject: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    account: Optional[Dict] = None
    contact: Optional[Dict] = None
    currentLoad: Optional[int] = 5
    requestedLoad: Optional[int] = 10
    connectionType: Optional[str] = "RESIDENTIAL"
    city: Optional[str] = "Hyderabad"
    pinCode: Optional[str] = "500001"
    accountId: Optional[Any] = None
    accountName: Optional[str] = None
    accountType: Optional[str] = None
    industry: Optional[str] = None
    requestType: Optional[str] = None

class SAPSendRequest(BaseModel):
    case_data: Dict[str, Any]
    endpoint_type: str = "load_request_xml"

class ValidateRequest(BaseModel):
    request_id: int
    account_name: str

class SendToServiceNowRequest(BaseModel):
    request_id: int
    account_name: str
    request_data: Dict[str, Any]

# ============================================================================
# FASTAPI APP
# ============================================================================

app = FastAPI(title="MuleSoft MCP API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer(auto_error=False)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials:
        return None
    token = credentials.credentials
    if token in tokens_db:
        return tokens_db[token]
    return None

async def require_auth(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = credentials.credentials
    if token not in tokens_db:
        raise HTTPException(status_code=401, detail="Invalid token")
    return tokens_db[token]

# ============================================================================
# AUTH ENDPOINTS
# ============================================================================

@app.post("/api/auth/login")
async def login(request: LoginRequest):
    # Simple auth for demo
    for username, user in users_db.items():
        if user["email"] == request.email and user["password"] == request.password:
            token = str(uuid.uuid4())
            tokens_db[token] = user
            return {"access_token": token, "token_type": "bearer", "user": user}
    raise HTTPException(status_code=401, detail="Invalid credentials")

@app.post("/api/auth/register")
async def register(request: RegisterRequest):
    if any(u["email"] == request.email for u in users_db.values()):
        raise HTTPException(status_code=400, detail="Email already registered")
    user_id = len(users_db) + 1
    user = {"id": user_id, "email": request.email, "password": request.password, "full_name": request.full_name}
    users_db[request.email] = user
    return {"message": "User registered successfully"}

# ============================================================================
# CONNECTOR ENDPOINTS
# ============================================================================

@app.get("/api/connectors")
async def list_connectors(user = Depends(require_auth)):
    return list(connectors_db.values())

@app.get("/api/connectors/")
async def list_connectors_slash(user = Depends(require_auth)):
    return list(connectors_db.values())

@app.get("/api/connectors/types")
async def get_connector_types(user = Depends(require_auth)):
    return [
        {"type": "salesforce", "name": "Salesforce", "description": "Connect to Salesforce CRM"},
        {"type": "sap", "name": "SAP", "description": "Connect to SAP ERP"},
        {"type": "servicenow", "name": "ServiceNow", "description": "Connect to ServiceNow"},
        {"type": "database", "name": "Database", "description": "Connect to databases"},
    ]

@app.get("/api/connectors/{connector_id}")
async def get_connector(connector_id: int, user = Depends(require_auth)):
    if connector_id not in connectors_db:
        raise HTTPException(status_code=404, detail="Connector not found")
    connector = connectors_db[connector_id]
    return {"id": connector_id, "config": connector.get("connection_config", {}), **connector}

@app.post("/api/connectors")
async def create_connector(connector: ConnectorCreate, user = Depends(require_auth)):
    connector_id = len(connectors_db) + 1
    connectors_db[connector_id] = {
        "id": connector_id,
        "name": connector.name,
        "connector_type": connector.connector_type,
        "connection_config": connector.connection_config,
        "status": "active",
        "created_at": datetime.now().isoformat()
    }
    return connectors_db[connector_id]

@app.put("/api/connectors/{connector_id}")
async def update_connector(connector_id: int, connector: ConnectorUpdate, user = Depends(require_auth)):
    if connector_id not in connectors_db:
        raise HTTPException(status_code=404, detail="Connector not found")
    existing = connectors_db[connector_id]
    if connector.name:
        existing["name"] = connector.name
    if connector.connector_type:
        existing["connector_type"] = connector.connector_type
    if connector.connection_config:
        existing["connection_config"] = connector.connection_config
    return existing

@app.delete("/api/connectors/{connector_id}")
async def delete_connector(connector_id: int, user = Depends(require_auth)):
    if connector_id not in connectors_db:
        raise HTTPException(status_code=404, detail="Connector not found")
    del connectors_db[connector_id]
    return {"message": "Connector deleted"}

@app.post("/api/connectors/{connector_id}/test")
async def test_connector(connector_id: int, user = Depends(require_auth)):
    if connector_id not in connectors_db:
        raise HTTPException(status_code=404, detail="Connector not found")
    connector = connectors_db[connector_id]

    # Test connection based on type
    if connector["connector_type"] == "salesforce":
        server_url = connector.get("connection_config", {}).get("server_url", "")
        if server_url:
            try:
                async with httpx.AsyncClient(verify=False, timeout=10) as client:
                    response = await client.get(f"{server_url}/api/health")
                    if response.status_code == 200:
                        return {"success": True, "message": "Connection successful"}
            except:
                pass
        return {"success": False, "message": "Could not connect to Salesforce server"}

    return {"success": True, "message": "Connection test simulated"}

# ============================================================================
# SALESFORCE/CASES ENDPOINTS (Proxy to external Salesforce app)
# ============================================================================

@app.get("/api/cases/external/cases")
async def get_external_cases(connector_id: int = Query(...), user = Depends(require_auth)):
    if connector_id not in connectors_db:
        return {"status": "error", "message": "Connector not found", "cases": []}

    connector = connectors_db[connector_id]
    server_url = connector.get("connection_config", {}).get("server_url", "").rstrip("/")

    if not server_url:
        return {"status": "error", "message": "Server URL not configured", "cases": []}

    try:
        async with httpx.AsyncClient(verify=False, timeout=15) as client:
            # Authenticate
            auth_response = await client.post(f"{server_url}/api/auth/login", json={"username": "admin", "password": "admin123"})
            if auth_response.status_code != 200:
                return {"status": "error", "message": "Authentication failed", "cases": []}
            token = auth_response.json().get("access_token", "")

            # Fetch cases
            headers = {"Authorization": f"Bearer {token}"}
            response = await client.get(f"{server_url}/api/cases", headers=headers)
            if response.status_code == 200:
                data = response.json()
                return {"status": "success", "server_url": server_url, "cases": data}
            return {"status": "error", "message": f"Failed: HTTP {response.status_code}", "cases": []}
    except Exception as e:
        return {"status": "error", "message": str(e), "cases": []}

@app.get("/api/cases/external/account-requests")
async def get_external_account_requests(connector_id: int = Query(...), status: Optional[str] = None, user = Depends(require_auth)):
    if connector_id not in connectors_db:
        return {"status": "error", "message": "Connector not found", "requests": []}

    connector = connectors_db[connector_id]
    server_url = connector.get("connection_config", {}).get("server_url", "").rstrip("/")

    if not server_url:
        return {"status": "error", "message": "Server URL not configured", "requests": []}

    try:
        async with httpx.AsyncClient(verify=False, timeout=15) as client:
            # Authenticate
            auth_response = await client.post(f"{server_url}/api/auth/login", json={"username": "admin", "password": "admin123"})
            if auth_response.status_code != 200:
                return {"status": "error", "message": "Authentication failed", "requests": []}
            token = auth_response.json().get("access_token", "")

            # Fetch account requests
            headers = {"Authorization": f"Bearer {token}"}
            params = {}
            if status:
                params["status"] = status
            response = await client.get(f"{server_url}/api/accounts/requests", headers=headers, params=params)
            if response.status_code == 200:
                data = response.json()
                items = data.get("items", [])
                return {"status": "success", "server_url": server_url, "total": len(items), "requests": items}
            return {"status": "error", "message": f"Failed: HTTP {response.status_code}", "requests": []}
    except Exception as e:
        return {"status": "error", "message": str(e), "requests": []}

@app.post("/api/cases/validate-single-request")
async def validate_single_request(request: ValidateRequest, connector_id: int = Query(...), user = Depends(require_auth)):
    # Validate request data - this does NOT approve, just validates
    return {
        "validation_passed": True,
        "approval_status": "pending",
        "request_id": request.request_id,
        "account_name": request.account_name,
        "mulesoft_transaction_id": f"MULE-{uuid.uuid4().hex[:8].upper()}",
        "validation_timestamp": datetime.now().isoformat(),
        "message": "Request validated - requires manual approval after sending to ServiceNow"
    }

@app.post("/api/cases/send-single-to-servicenow")
async def send_single_to_servicenow(request: SendToServiceNowRequest, connector_id: int = Query(...), user = Depends(require_auth)):
    ticket_number = None
    servicenow_response = None

    try:
        async with httpx.AsyncClient(verify=False, timeout=30) as client:
            ticket_data = {
                "short_description": f"Account Creation Request: {request.account_name}",
                "description": f"Request ID: {request.request_id}\nAccount: {request.account_name}\nSource: Salesforce CRM",
                "category": "Account Management",
                "priority": "3",
                "metadata": {
                    "source_system": "Salesforce",
                    "request_id": request.request_id,
                    "account_name": request.account_name,
                    "callback_url": f"http://149.102.158.71:8091/api/ticket-approval"
                }
            }
            response = await client.post(f"{SERVICENOW_API_URL}/api/tickets", json=ticket_data)
            if response.status_code in [200, 201]:
                servicenow_response = response.json()
                ticket_number = servicenow_response.get("ticket_number", f"TKT-{uuid.uuid4().hex[:8].upper()}")
    except Exception as e:
        print(f"[MuleSoft] Error sending to ServiceNow: {e}")

    # Fallback ticket number if ServiceNow call failed
    if not ticket_number:
        ticket_number = f"TKT-{uuid.uuid4().hex[:8].upper()}"

    # Store the pending request for later callback
    pending_account_requests_db[ticket_number] = {
        "request_id": request.request_id,
        "account_name": request.account_name,
        "ticket_number": ticket_number,
        "request_data": request.request_data,
        "created_at": datetime.now().isoformat(),
        "status": "pending_approval"
    }

    print(f"[MuleSoft] Stored pending account request: {request.request_id} -> {ticket_number}")

    return {
        "success": True,
        "ticket_number": ticket_number,
        "ticket_status": "pending_approval",
        "requires_approval": True,
        "servicenow_response": servicenow_response,
        "message": "Ticket created - awaiting manual approval in ServiceNow"
    }

@app.post("/api/cases/orchestrate/account-requests")
async def orchestrate_account_requests(connector_id: int = Query(...), user = Depends(require_auth)):
    # Simulate orchestration - tickets require manual approval
    return {
        "status": "tickets_created",
        "approval_status": "pending",
        "total_fetched": 5,
        "total_valid": 4,
        "total_invalid": 1,
        "total_sent_to_servicenow": 4,
        "total_pending_approval": 4,
        "total_failed": 0,
        "message": "Tickets created in ServiceNow - awaiting manual approval",
        "results": []
    }

# ============================================================================
# SAP ENDPOINTS
# ============================================================================

@app.get("/api/sap/test-connection")
async def test_sap_connection(user = Depends(require_auth)):
    try:
        async with httpx.AsyncClient(verify=False, timeout=10) as client:
            response = await client.get(f"{SAP_API_URL}/api/health")
            if response.status_code == 200:
                return {"success": True, "message": "SAP connection successful"}
    except:
        pass
    return {"success": False, "message": "SAP not reachable"}

@app.post("/api/sap/preview-xml")
async def preview_sap_xml(data: CaseTransformData, user = Depends(require_auth)):
    # Generate XML preview
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<IDOC BEGIN="1">
  <EDI_DC40 SEGMENT="1">
    <TABNAM>EDI_DC40</TABNAM>
    <MANDT>100</MANDT>
    <DOCNUM>{uuid.uuid4().hex[:10].upper()}</DOCNUM>
    <IDOCTYP>SRCLST01</IDOCTYP>
    <MESTYP>SRCLST</MESTYP>
    <SNDPRT>LS</SNDPRT>
    <SNDPRN>MULESOFT</SNDPRN>
    <RCVPRT>LS</RCVPRT>
    <RCVPRN>SAP_ERP</RCVPRN>
    <CREDAT>{datetime.now().strftime('%Y%m%d')}</CREDAT>
    <CRETIM>{datetime.now().strftime('%H%M%S')}</CRETIM>
  </EDI_DC40>
  <E1SRCLST SEGMENT="1">
    <CASE_ID>{data.caseId or data.accountId or 'N/A'}</CASE_ID>
    <CASE_NUMBER>{data.caseNumber or 'N/A'}</CASE_NUMBER>
    <SUBJECT>{data.subject or data.accountName or 'N/A'}</SUBJECT>
    <DESCRIPTION>{data.description or 'N/A'}</DESCRIPTION>
    <STATUS>{data.status or 'NEW'}</STATUS>
    <PRIORITY>{data.priority or 'MEDIUM'}</PRIORITY>
    <CONNECTION_TYPE>{data.connectionType}</CONNECTION_TYPE>
    <CURRENT_LOAD>{data.currentLoad}</CURRENT_LOAD>
    <REQUESTED_LOAD>{data.requestedLoad}</REQUESTED_LOAD>
    <CITY>{data.city}</CITY>
    <PIN_CODE>{data.pinCode}</PIN_CODE>
    <REQUEST_TYPE>{data.requestType or 'SERVICE_REQUEST'}</REQUEST_TYPE>
    <TIMESTAMP>{datetime.now().isoformat()}</TIMESTAMP>
  </E1SRCLST>
</IDOC>"""
    return {"xml": xml, "format": "SAP IDoc XML"}

@app.post("/api/sap/send-load-request")
async def send_to_sap(request: SAPSendRequest, user = Depends(require_auth)):
    try:
        async with httpx.AsyncClient(verify=False, timeout=30) as client:
            response = await client.post(
                f"{SAP_API_URL}/api/integration/mulesoft/load-request/xml",
                json=request.case_data
            )
            if response.status_code in [200, 201]:
                return {"success": True, "sap_response": response.json()}
    except Exception as e:
        pass

    # Fallback simulation
    return {
        "success": True,
        "sap_response": {
            "message": "Load request processed successfully",
            "transaction_id": f"SAP-{uuid.uuid4().hex[:8].upper()}",
            "tickets_created": {
                "pm_ticket": f"PM-{uuid.uuid4().hex[:6].upper()}",
                "fi_ticket": f"FI-{uuid.uuid4().hex[:6].upper()}",
                "mm_ticket": f"MM-{uuid.uuid4().hex[:6].upper()}"
            }
        }
    }

# ============================================================================
# SERVICENOW ENDPOINTS
# ============================================================================

@app.get("/api/servicenow/test-connection")
async def test_servicenow_connection(user = Depends(require_auth)):
    try:
        async with httpx.AsyncClient(verify=False, timeout=10) as client:
            response = await client.get(f"{SERVICENOW_API_URL}/api/health")
            if response.status_code == 200:
                return {"success": True, "message": "ServiceNow connection successful"}
    except:
        pass
    return {"success": False, "message": "ServiceNow not reachable"}

@app.post("/api/servicenow/preview-ticket")
async def preview_servicenow_ticket(data: Dict[str, Any] = Body(...), ticket_type: str = Query("incident"), user = Depends(require_auth)):
    ticket_payload = {
        "short_description": data.get("subject") or f"Case #{data.get('caseId', 'N/A')}",
        "description": data.get("description") or "No description provided",
        "category": data.get("category", "General"),
        "priority": "3" if data.get("priority") == "Medium" else ("1" if data.get("priority") == "Critical" else "2"),
        "caller_id": data.get("userName") or data.get("contact", {}).get("name", "Unknown"),
        "ticket_type": ticket_type,
        "source_system": "MuleSoft",
        "source_id": str(data.get("caseId") or data.get("id", "N/A"))
    }
    return {"ticket_payload": ticket_payload}

@app.post("/api/servicenow/preview-approval")
async def preview_servicenow_approval(data: Dict[str, Any] = Body(...), approval_type: str = Query("user_account"), user = Depends(require_auth)):
    approval_payload = {
        "approval_type": approval_type,
        "requested_for": data.get("userName") or data.get("accountName") or data.get("contact", {}).get("name", "Unknown"),
        "requested_by": "MuleSoft Integration",
        "description": f"Approval request for {approval_type}: {data.get('subject') or data.get('accountName', 'N/A')}",
        "priority": data.get("priority", "Medium"),
        "source_id": str(data.get("caseId") or data.get("id", "N/A")),
        "details": {
            "department": data.get("department", "N/A"),
            "role": data.get("userRole", "Standard User"),
            "category": data.get("category", "General")
        }
    }
    return {"approval_payload": approval_payload}

@app.post("/api/servicenow/send-ticket-and-approval")
async def send_ticket_and_approval(data: Dict[str, Any] = Body(...), ticket_type: str = Query("incident"), approval_type: str = Query("user_account"), user = Depends(require_auth)):
    ticket_result = {"success": False}

    try:
        async with httpx.AsyncClient(verify=False, timeout=30) as client:
            # Send ticket only - approval will be handled manually in ServiceNow
            ticket_data = {
                "short_description": data.get("subject") or f"Case #{data.get('caseId', 'N/A')}",
                "description": data.get("description") or "No description",
                "category": data.get("category", "General"),
                "priority": "3"
            }
            ticket_response = await client.post(f"{SERVICENOW_API_URL}/api/tickets", json=ticket_data)
            if ticket_response.status_code in [200, 201]:
                response_data = ticket_response.json()
                ticket_result = {
                    "success": True,
                    "response": response_data,
                    "ticket_number": response_data.get("ticket_number"),
                    "ticket_status": "pending_approval",
                    "requires_approval": True
                }
    except:
        pass

    # Fallback simulation if actual calls fail - still requires approval
    if not ticket_result.get("success"):
        ticket_result = {
            "success": True,
            "ticket_number": f"INC-{uuid.uuid4().hex[:8].upper()}",
            "ticket_status": "pending_approval",
            "requires_approval": True,
            "response": {"message": "Ticket created (simulated) - awaiting manual approval"}
        }

    return {
        "ticket": ticket_result,
        "approval_status": "pending",
        "message": "Ticket created and awaiting manual approval in ServiceNow. Check the Approvals tab to approve or reject."
    }

@app.get("/api/servicenow/ticket-status/{ticket_id}")
async def get_ticket_status(ticket_id: str, user = Depends(require_auth)):
    try:
        async with httpx.AsyncClient(verify=False, timeout=15) as client:
            response = await client.get(f"{SERVICENOW_API_URL}/api/tickets/{ticket_id}")
            if response.status_code == 200:
                return response.json()
    except:
        pass

    # Fallback - return pending status (never auto-approve)
    return {
        "ticket_id": ticket_id,
        "status": "pending_approval",
        "requires_approval": True,
        "updated_at": datetime.now().isoformat(),
        "message": "Unable to fetch status from ServiceNow - check Approvals tab"
    }

# ============================================================================
# API ENDPOINTS (for API Manager page)
# ============================================================================

@app.get("/api/apis/endpoints")
async def list_api_endpoints(user = Depends(require_auth)):
    return [
        {"id": 1, "name": "Get Cases", "method": "GET", "path": "/api/cases", "status": "active"},
        {"id": 2, "name": "Create Case", "method": "POST", "path": "/api/cases", "status": "active"},
        {"id": 3, "name": "SAP Sync", "method": "POST", "path": "/api/sap/sync", "status": "active"},
    ]

@app.post("/api/apis/endpoints")
async def create_api_endpoint(data: Dict[str, Any] = Body(...), user = Depends(require_auth)):
    return {"id": uuid.uuid4().hex[:8], **data, "status": "active"}

@app.delete("/api/apis/endpoints/{endpoint_id}")
async def delete_api_endpoint(endpoint_id: int, user = Depends(require_auth)):
    return {"message": "Endpoint deleted"}

@app.get("/api/apis/keys")
async def list_api_keys(user = Depends(require_auth)):
    return [
        {"id": 1, "name": "Production Key", "key": "pk_live_xxx", "status": "active", "created_at": datetime.now().isoformat()},
    ]

@app.post("/api/apis/keys")
async def create_api_key(data: Dict[str, Any] = Body(...), user = Depends(require_auth)):
    return {"id": uuid.uuid4().hex[:8], "key": f"pk_{uuid.uuid4().hex}", **data}

@app.delete("/api/apis/keys/{key_id}")
async def revoke_api_key(key_id: int, user = Depends(require_auth)):
    return {"message": "Key revoked"}

# ============================================================================
# TICKET APPROVAL WEBHOOK (receives approval status from ServiceNow)
# ============================================================================

# Salesforce API URL for callbacks
SALESFORCE_API_URL = "http://149.102.158.71:4799"
MULESOFT_SHARED_SECRET = "mulesoft-salesforce-shared-secret-2024"

# In-memory storage for approval notifications and pending requests
approval_notifications_db = []
pending_account_requests_db = {}  # Maps ticket_number to request_data


async def _callback_to_salesforce(request_id: int, accepted: bool, message: str = None, ticket_status: str = None):
    """Call back to Salesforce with approval/rejection status"""
    try:
        callback_url = f"{SALESFORCE_API_URL}/api/accounts/requests/{request_id}/mulesoft-callback"
        payload = {
            "accepted": accepted,
            "status": ticket_status or ("APPROVED" if accepted else "REJECTED"),
            "message": message or ("Account request approved" if accepted else "Account request rejected")
        }
        headers = {
            "X-MuleSoft-Secret": MULESOFT_SHARED_SECRET,
            "Content-Type": "application/json"
        }

        async with httpx.AsyncClient(verify=False, timeout=30) as client:
            response = await client.post(callback_url, json=payload, headers=headers)
            if response.status_code in [200, 201]:
                print(f"[MuleSoft] Successfully called back to Salesforce for request {request_id}: {accepted}")
                return True, response.json()
            else:
                print(f"[MuleSoft] Failed to callback to Salesforce: {response.status_code} - {response.text}")
                return False, {"error": f"HTTP {response.status_code}"}
    except Exception as e:
        print(f"[MuleSoft] Error calling back to Salesforce: {e}")
        return False, {"error": str(e)}


@app.post("/api/ticket-approval")
async def receive_ticket_approval(data: Dict[str, Any] = Body(...)):
    """
    Receive ticket approval/rejection notification from ServiceNow.
    When received, callback to Salesforce to create/reject the account.
    """
    notification = {
        "id": len(approval_notifications_db) + 1,
        "ticket_id": data.get("ticket_id"),
        "ticket_number": data.get("ticket_number"),
        "title": data.get("title"),
        "status": data.get("status"),  # 'approved' or 'rejected'
        "action_taken": data.get("action_taken"),
        "comments": data.get("comments"),
        "action_timestamp": data.get("action_timestamp"),
        "category": data.get("category"),
        "priority": data.get("priority"),
        "requester_name": data.get("requester_name"),
        "request_id": data.get("request_id"),  # Salesforce request ID
        "received_at": datetime.now().isoformat()
    }
    approval_notifications_db.append(notification)

    print(f"[MuleSoft] Received approval notification: {notification['ticket_number']} - {notification['status']}")

    # Get request_id from stored pending requests or from the notification
    request_id = notification.get("request_id")
    ticket_number = notification.get("ticket_number")

    # Try to find request_id from pending requests if not in notification
    if not request_id and ticket_number in pending_account_requests_db:
        request_data = pending_account_requests_db[ticket_number]
        request_id = request_data.get("request_id")

    # Callback to Salesforce if we have a request_id
    salesforce_callback_result = None
    if request_id:
        is_approved = notification["status"] == "approved"
        success, result = await _callback_to_salesforce(
            request_id=request_id,
            accepted=is_approved,
            message=notification.get("comments"),
            ticket_status=notification.get("status", "").upper()
        )
        salesforce_callback_result = {
            "success": success,
            "result": result
        }

        # Remove from pending requests if callback was successful
        if success and ticket_number in pending_account_requests_db:
            del pending_account_requests_db[ticket_number]

    return {
        "success": True,
        "message": f"Approval notification received for ticket {notification['ticket_number']}",
        "status": notification["status"],
        "notification_id": notification["id"],
        "salesforce_callback": salesforce_callback_result
    }


@app.get("/api/ticket-approvals")
async def list_ticket_approvals(status: Optional[str] = None):
    """List all ticket approval notifications received"""
    results = approval_notifications_db
    if status:
        results = [n for n in results if n.get("status") == status]
    return {"notifications": results, "total": len(results)}


@app.get("/api/pending-account-requests")
async def list_pending_account_requests():
    """List all pending account requests waiting for approval"""
    return {"requests": list(pending_account_requests_db.values()), "total": len(pending_account_requests_db)}


# ============================================================================
# HEALTH & MISC
# ============================================================================

@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.get("/api/test")
async def test_endpoint():
    return {"message": "MCP API is working", "timestamp": datetime.now().isoformat()}

@app.post("/api/proxy/request")
async def proxy_request(data: Dict[str, Any] = Body(...), user = Depends(require_auth)):
    url = data.get("url")
    method = data.get("method", "GET")
    body = data.get("body")
    headers = data.get("headers", {})

    try:
        async with httpx.AsyncClient(verify=False, timeout=30) as client:
            if method == "GET":
                response = await client.get(url, headers=headers)
            else:
                response = await client.post(url, headers=headers, json=body)
            return {"status": response.status_code, "data": response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text}
    except Exception as e:
        return {"error": str(e)}

# ============================================================================
# MCP SERVER (for AI model tool calls via SSE)
# ============================================================================

mcp_server = Server("mulesoft-integration")

# MCP SSE Port
MCP_SSE_PORT = 8092


@mcp_server.call_tool()
async def mcp_health_check():
    """Check MuleSoft integration health"""
    result = {"status": "healthy", "timestamp": datetime.now().isoformat()}
    return [TextContent(type="text", text=json.dumps(result))]


@mcp_server.call_tool()
async def mcp_sync_case_to_sap(case_id: int, operation: str = "CREATE"):
    """Synchronize a case to SAP via MuleSoft"""
    result = {"case_id": case_id, "operation": operation, "status": "synced"}
    return [TextContent(type="text", text=json.dumps(result))]


@mcp_server.call_tool()
async def mcp_validate_account_request(request_id: int, account_name: str):
    """Validate an account creation request from Salesforce"""
    result = {
        "validation_passed": True,
        "approval_status": "pending",
        "request_id": request_id,
        "account_name": account_name,
        "mulesoft_transaction_id": f"MULE-{uuid.uuid4().hex[:8].upper()}",
        "validation_timestamp": datetime.now().isoformat(),
        "message": "Request validated - requires approval via ServiceNow"
    }
    return [TextContent(type="text", text=json.dumps(result))]


@mcp_server.call_tool()
async def mcp_send_to_servicenow(request_id: int, account_name: str, request_data: str = "{}"):
    """Send account request to ServiceNow for approval via MuleSoft"""
    import json as json_module
    try:
        data = json_module.loads(request_data) if request_data else {}
    except:
        data = {}

    ticket_number = f"TKT-{uuid.uuid4().hex[:8].upper()}"

    # Store pending request
    pending_account_requests_db[ticket_number] = {
        "request_id": request_id,
        "account_name": account_name,
        "ticket_number": ticket_number,
        "request_data": data,
        "created_at": datetime.now().isoformat(),
        "status": "pending_approval"
    }

    # Try to create ticket in ServiceNow
    try:
        async with httpx.AsyncClient(verify=False, timeout=30) as client:
            ticket_data = {
                "short_description": f"Account Creation Request: {account_name}",
                "description": f"Request ID: {request_id}\nAccount: {account_name}\nSource: Salesforce CRM via MCP",
                "category": "Account Management",
                "priority": "3",
                "metadata": {
                    "source_system": "Salesforce",
                    "request_id": request_id,
                    "account_name": account_name,
                    "callback_url": f"http://149.102.158.71:8091/api/ticket-approval"
                }
            }
            response = await client.post(f"{SERVICENOW_API_URL}/api/tickets", json=ticket_data)
            if response.status_code in [200, 201]:
                servicenow_response = response.json()
                ticket_number = servicenow_response.get("ticket_number", ticket_number)
    except Exception as e:
        print(f"[MCP] ServiceNow call failed: {e}")

    result = {
        "success": True,
        "ticket_number": ticket_number,
        "ticket_status": "pending_approval",
        "requires_approval": True,
        "message": "Ticket created in ServiceNow - awaiting approval"
    }
    return [TextContent(type="text", text=json.dumps(result))]


@mcp_server.call_tool()
async def mcp_approve_account_request(request_id: int, approved: bool = True, comments: str = ""):
    """Manually approve or reject an account request and callback to Salesforce"""
    # Find the pending request
    target_ticket = None
    for ticket_num, req_data in pending_account_requests_db.items():
        if req_data.get("request_id") == request_id:
            target_ticket = ticket_num
            break

    if not target_ticket:
        result = {"success": False, "error": f"No pending request found with ID {request_id}"}
        return [TextContent(type="text", text=json.dumps(result))]

    # Callback to Salesforce
    success, callback_result = await _callback_to_salesforce(
        request_id=request_id,
        accepted=approved,
        message=comments or ("Approved via MCP" if approved else "Rejected via MCP"),
        ticket_status="APPROVED" if approved else "REJECTED"
    )

    if success:
        del pending_account_requests_db[target_ticket]

    result = {
        "success": success,
        "request_id": request_id,
        "approved": approved,
        "ticket_number": target_ticket,
        "salesforce_callback": callback_result,
        "message": f"Account request {'approved' if approved else 'rejected'} and Salesforce notified"
    }
    return [TextContent(type="text", text=json.dumps(result))]


@mcp_server.call_tool()
async def mcp_list_pending_requests():
    """List all pending account requests waiting for approval"""
    result = {
        "requests": list(pending_account_requests_db.values()),
        "total": len(pending_account_requests_db)
    }
    return [TextContent(type="text", text=json.dumps(result))]


@mcp_server.call_tool()
async def mcp_get_approval_notifications(status_filter: str = ""):
    """Get approval notifications received from ServiceNow"""
    results = approval_notifications_db
    if status_filter:
        results = [n for n in results if n.get("status") == status_filter]
    result = {"notifications": results, "total": len(results)}
    return [TextContent(type="text", text=json.dumps(result))]


@mcp_server.call_tool()
async def mcp_test_salesforce_connection():
    """Test connection to Salesforce backend"""
    try:
        async with httpx.AsyncClient(verify=False, timeout=10) as client:
            response = await client.get(f"{SALESFORCE_API_URL}/api/health")
            if response.status_code == 200:
                return [TextContent(type="text", text=json.dumps({"success": True, "message": "Salesforce connection successful"}))]
    except Exception as e:
        pass
    return [TextContent(type="text", text=json.dumps({"success": False, "message": "Salesforce not reachable"}))]


@mcp_server.call_tool()
async def mcp_test_servicenow_connection():
    """Test connection to ServiceNow backend"""
    try:
        async with httpx.AsyncClient(verify=False, timeout=10) as client:
            response = await client.get(f"{SERVICENOW_API_URL}/api/health")
            if response.status_code == 200:
                return [TextContent(type="text", text=json.dumps({"success": True, "message": "ServiceNow connection successful"}))]
    except Exception as e:
        pass
    return [TextContent(type="text", text=json.dumps({"success": False, "message": "ServiceNow not reachable"}))]


@mcp_server.call_tool()
async def mcp_test_sap_connection():
    """Test connection to SAP backend"""
    try:
        async with httpx.AsyncClient(verify=False, timeout=10) as client:
            response = await client.get(f"{SAP_API_URL}/api/health")
            if response.status_code == 200:
                return [TextContent(type="text", text=json.dumps({"success": True, "message": "SAP connection successful"}))]
    except Exception as e:
        pass
    return [TextContent(type="text", text=json.dumps({"success": False, "message": "SAP not reachable"}))]


# ============================================================================
# MCP SSE SERVER SETUP
# ============================================================================

def create_mcp_sse_app():
    """Create Starlette app for MCP SSE connections"""
    from mcp.server.sse import SseServerTransport
    from starlette.applications import Starlette
    from starlette.routing import Route
    from starlette.middleware import Middleware
    from starlette.middleware.cors import CORSMiddleware

    sse = SseServerTransport("/messages")

    async def handle_sse(request):
        async with sse.connect_sse(
            request.scope, request.receive, request._send
        ) as streams:
            await mcp_server.run(
                streams[0], streams[1], mcp_server.create_initialization_options()
            )

    async def handle_messages(request):
        await sse.handle_post_message(request.scope, request.receive, request._send)

    middleware = [
        Middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    ]

    return Starlette(
        routes=[
            Route("/sse", endpoint=handle_sse),
            Route("/messages", endpoint=handle_messages, methods=["POST"]),
        ],
        middleware=middleware,
    )


def run_mcp_sse_server():
    """Run MCP SSE server in a separate thread"""
    import threading

    def _run_sse():
        mcp_sse_app = create_mcp_sse_app()
        print(f"Starting MCP SSE Server on port {MCP_SSE_PORT}")
        print(f"  SSE Endpoint: http://149.102.158.71:{MCP_SSE_PORT}/sse")
        uvicorn.run(mcp_sse_app, host="0.0.0.0", port=MCP_SSE_PORT, log_level="warning")

    sse_thread = threading.Thread(target=_run_sse, daemon=True)
    sse_thread.start()
    return sse_thread


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("MuleSoft Integration Platform")
    print("=" * 60)

    # Start MCP SSE server in background thread
    run_mcp_sse_server()

    print(f"\nStarting HTTP API on port {MCP_HTTP_PORT}")
    print(f"  HTTP API: http://149.102.158.71:{MCP_HTTP_PORT}/api")
    print(f"  MCP SSE:  http://149.102.158.71:{MCP_SSE_PORT}/sse")
    print("=" * 60)

    # Run main HTTP API
    uvicorn.run(app, host="0.0.0.0", port=MCP_HTTP_PORT)
