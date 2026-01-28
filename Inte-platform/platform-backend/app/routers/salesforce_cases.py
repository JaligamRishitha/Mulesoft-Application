from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime
import httpx
import base64
import json

from app.database import get_db
from app.models import SalesforceCase, Connector, IntegrationLog
from app.auth import get_current_user

router = APIRouter(prefix="/cases", tags=["Salesforce Cases"])

class SalesforceCaseResponse(BaseModel):
    id: int
    salesforce_id: str
    case_number: str
    subject: str
    description: Optional[str]
    status: str
    priority: str
    origin: str
    account_name: Optional[str]
    contact_name: Optional[str]
    owner_name: Optional[str]
    created_date: Optional[datetime]
    closed_date: Optional[datetime]
    synced_at: datetime

    class Config:
        from_attributes = True

class PlatformEventFormat(BaseModel):
    """MuleSoft Platform Event format for Salesforce Case"""
    eventType: str = "CaseUpdate"
    eventId: str
    eventTime: str
    source: str = "Salesforce"
    data: Dict[str, Any]
    metadata: Dict[str, Any]

class SalesforceAuthResponse(BaseModel):
    access_token: str
    instance_url: str
    token_type: str = "Bearer"

async def get_salesforce_token(config: Dict[str, Any]) -> SalesforceAuthResponse:
    """Connect to remote Salesforce backend application and verify connectivity"""
    server_url = config.get("server_url", "").rstrip("/")
    if not server_url:
        raise HTTPException(status_code=400, detail="Server URL is not configured")

    async with httpx.AsyncClient(verify=False) as client:
        try:
            response = await client.get(server_url, timeout=10)
            if response.status_code < 500:
                return SalesforceAuthResponse(
                    access_token="remote-server-connected",
                    instance_url=server_url,
                    token_type="Bearer"
                )
            else:
                raise HTTPException(status_code=400, detail=f"Remote server returned error: HTTP {response.status_code}")
        except httpx.RequestError as e:
            raise HTTPException(status_code=400, detail=f"Cannot connect to remote server: {str(e)}")

async def fetch_salesforce_cases(auth: SalesforceAuthResponse, limit: int = 100) -> List[Dict[str, Any]]:
    """Fetch cases/user account creation requests from remote Salesforce backend application"""
    server_url = auth.instance_url.rstrip("/")

    # Try common API paths to fetch cases and user account creation requests
    case_endpoints = [
        f"{server_url}/api/cases",
        f"{server_url}/cases",
        f"{server_url}/api/v1/cases",
        f"{server_url}/api/users",
        f"{server_url}/api/account-requests",
        f"{server_url}/api/user-requests",
        f"{server_url}/api/requests",
    ]

    async with httpx.AsyncClient(verify=False) as client:
        for endpoint in case_endpoints:
            try:
                response = await client.get(endpoint, timeout=10)
                if response.status_code == 200:
                    cases_data = response.json()
                    # Handle both list and dict responses
                    if isinstance(cases_data, list):
                        return cases_data[:limit]
                    elif isinstance(cases_data, dict):
                        if 'data' in cases_data:
                            return cases_data['data'][:limit]
                        elif 'cases' in cases_data:
                            return cases_data['cases'][:limit]
                        elif 'records' in cases_data:
                            return cases_data['records'][:limit]
                        else:
                            return [cases_data]
                    else:
                        return []
            except Exception as e:
                print(f"Failed to fetch from {endpoint}: {e}")
                continue

    print(f"Could not fetch cases from any endpoint on {server_url}")
    return []

def sync_case_to_db(case_data: Dict[str, Any], db: Session) -> SalesforceCase:
    """Sync a Salesforce case to local database"""
    existing_case = db.query(SalesforceCase).filter(
        SalesforceCase.salesforce_id == case_data["Id"]
    ).first()
    
    case_values = {
        "salesforce_id": case_data["Id"],
        "case_number": case_data.get("CaseNumber"),
        "subject": case_data.get("Subject"),
        "description": case_data.get("Description"),
        "status": case_data.get("Status"),
        "priority": case_data.get("Priority"),
        "origin": case_data.get("Origin"),
        "account_id": case_data.get("Account", {}).get("Id") if case_data.get("Account") else None,
        "account_name": case_data.get("Account", {}).get("Name") if case_data.get("Account") else None,
        "contact_id": case_data.get("Contact", {}).get("Id") if case_data.get("Contact") else None,
        "contact_name": case_data.get("Contact", {}).get("Name") if case_data.get("Contact") else None,
        "owner_id": case_data.get("Owner", {}).get("Id") if case_data.get("Owner") else None,
        "owner_name": case_data.get("Owner", {}).get("Name") if case_data.get("Owner") else None,
        "created_date": datetime.fromisoformat(case_data["CreatedDate"].replace("Z", "+00:00")) if case_data.get("CreatedDate") else None,
        "closed_date": datetime.fromisoformat(case_data["ClosedDate"].replace("Z", "+00:00")) if case_data.get("ClosedDate") else None,
        "last_modified_date": datetime.fromisoformat(case_data["LastModifiedDate"].replace("Z", "+00:00")) if case_data.get("LastModifiedDate") else None,
        "raw_data": case_data,
        "synced_at": datetime.utcnow()
    }
    
    if existing_case:
        for key, value in case_values.items():
            setattr(existing_case, key, value)
        db.commit()
        db.refresh(existing_case)
        return existing_case
    else:
        new_case = SalesforceCase(**case_values)
        db.add(new_case)
        db.commit()
        db.refresh(new_case)
        return new_case

@router.post("/sync")
async def sync_salesforce_cases(
    connector_id: int = Query(..., description="Salesforce connector ID"),
    limit: int = Query(100, description="Number of cases to sync"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Sync cases from Salesforce to local database"""
    # Get Salesforce connector
    connector = db.query(Connector).filter(
        Connector.id == connector_id,
        Connector.connector_type == "salesforce"
    ).first()

    if not connector:
        raise HTTPException(status_code=404, detail="Salesforce connector not found")

    try:
        # Get Salesforce auth token
        auth = await get_salesforce_token(connector.connection_config or {})
        
        # Fetch cases from Salesforce
        cases_data = await fetch_salesforce_cases(auth, limit)
        
        # Sync cases to database
        synced_cases = []
        for case_data in cases_data:
            synced_case = sync_case_to_db(case_data, db)
            synced_cases.append(synced_case)
        
        return {
            "message": f"Successfully synced {len(synced_cases)} cases",
            "synced_count": len(synced_cases),
            "cases": [SalesforceCaseResponse.from_orm(case) for case in synced_cases[:10]]  # Return first 10
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")

@router.get("/", response_model=List[SalesforceCaseResponse])
async def list_cases(
    skip: int = Query(0, description="Number of cases to skip"),
    limit: int = Query(100, description="Number of cases to return"),
    status: Optional[str] = Query(None, description="Filter by case status"),
    priority: Optional[str] = Query(None, description="Filter by case priority"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """List synced Salesforce cases"""
    query = db.query(SalesforceCase)
    
    if status:
        query = query.filter(SalesforceCase.status == status)
    if priority:
        query = query.filter(SalesforceCase.priority == priority)
    
    cases = query.order_by(SalesforceCase.synced_at.desc()).offset(skip).limit(limit).all()
    return cases

@router.get("/{case_id}", response_model=SalesforceCaseResponse)
async def get_case(
    case_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get a specific case by ID"""
    case = db.query(SalesforceCase).filter(SalesforceCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return case

@router.get("/{case_id}/platform-event-format", response_model=PlatformEventFormat)
async def get_case_platform_event_format(
    case_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get case in MuleSoft Platform Event format - This is your requested endpoint!"""
    case = db.query(SalesforceCase).filter(SalesforceCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    # Create platform event format
    platform_event = PlatformEventFormat(
        eventId=f"case-{case.salesforce_id}-{int(datetime.utcnow().timestamp())}",
        eventTime=datetime.utcnow().isoformat() + "Z",
        data={
            "caseId": case.salesforce_id,
            "caseNumber": case.case_number,
            "subject": case.subject,
            "description": case.description,
            "status": case.status,
            "priority": case.priority,
            "origin": case.origin,
            "account": {
                "id": case.account_id,
                "name": case.account_name
            } if case.account_id else None,
            "contact": {
                "id": case.contact_id,
                "name": case.contact_name
            } if case.contact_id else None,
            "owner": {
                "id": case.owner_id,
                "name": case.owner_name
            } if case.owner_id else None,
            "createdDate": case.created_date.isoformat() + "Z" if case.created_date else None,
            "closedDate": case.closed_date.isoformat() + "Z" if case.closed_date else None,
            "lastModifiedDate": case.last_modified_date.isoformat() + "Z" if case.last_modified_date else None
        },
        metadata={
            "syncedAt": case.synced_at.isoformat() + "Z",
            "source": "MuleSoft Integration Platform",
            "version": "1.0",
            "connector": "Salesforce",
            "dataFormat": "platform-event"
        }
    )
    
    return platform_event

@router.get("/test-platform-event")
async def test_platform_event_format():
    """Test endpoint to demonstrate platform event format without authentication"""
    # Create a sample case data from your external app structure
    sample_case = {
        "id": "test-case-001",
        "subject": "Planned Power Outage - Canary Wharf Substation Maintenance",
        "description": "Scheduled maintenance on primary substation affecting Canary Wharf district",
        "status": "New",
        "priority": "High",
        "origin": "Web",
        "account": {"id": "ACC-001", "name": "London Power Grid"},
        "contact": {"id": "CON-001", "name": "Operations Manager"},
        "owner": {"id": "OWN-001", "name": "Grid Maintenance Team"},
        "createdDate": "2024-01-21T10:30:00Z",
        "lastModifiedDate": "2024-01-21T15:45:00Z"
    }
    
    # Create platform event format
    platform_event = PlatformEventFormat(
        eventId=f"case-{sample_case['id']}-{int(datetime.utcnow().timestamp())}",
        eventTime=datetime.utcnow().isoformat() + "Z",
        data={
            "caseId": sample_case["id"],
            "caseNumber": "00001001",
            "subject": sample_case["subject"],
            "description": sample_case["description"],
            "status": sample_case["status"],
            "priority": sample_case["priority"],
            "origin": sample_case["origin"],
            "account": sample_case.get("account"),
            "contact": sample_case.get("contact"),
            "owner": sample_case.get("owner"),
            "createdDate": sample_case.get("createdDate"),
            "closedDate": None,
            "lastModifiedDate": sample_case.get("lastModifiedDate")
        },
        metadata={
            "syncedAt": datetime.utcnow().isoformat() + "Z",
            "source": "MuleSoft Integration Platform",
            "version": "1.0",
            "connector": "External Salesforce App",
            "dataFormat": "platform-event",
            "externalAppUrl": "configured-via-connector"
        }
    )
    
    return platform_event
async def authenticate_with_salesforce(server_url: str, username: str = "admin", password: str = "admin123") -> str:
    """Authenticate with the external Salesforce application and return a bearer token"""
    async with httpx.AsyncClient(verify=False) as client:
        response = await client.post(
            f"{server_url}/api/auth/login",
            json={"username": username, "password": password},
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            return data.get("access_token", "")
        raise HTTPException(
            status_code=401,
            detail=f"Failed to authenticate with Salesforce app: HTTP {response.status_code}"
        )

@router.get("/external/account-requests")
async def fetch_external_account_requests(
    connector_id: int = Query(..., description="Salesforce connector ID"),
    status: Optional[str] = Query(None, description="Filter by status: PENDING, COMPLETED, REJECTED, FAILED"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Fetch new account creation requests from the external Salesforce application"""
    connector = db.query(Connector).filter(
        Connector.id == connector_id,
        Connector.connector_type == "salesforce"
    ).first()

    if not connector:
        raise HTTPException(status_code=404, detail="Salesforce connector not found")

    server_url = (connector.connection_config or {}).get("server_url", "").rstrip("/")
    if not server_url:
        raise HTTPException(status_code=400, detail="Server URL is not configured")

    try:
        # Authenticate with the external Salesforce app
        sf_token = await authenticate_with_salesforce(server_url)

        async with httpx.AsyncClient(verify=False) as client:
            params = {}
            if status:
                params["status"] = status

            response = await client.get(
                f"{server_url}/api/accounts/requests",
                headers={"Authorization": f"Bearer {sf_token}"},
                params=params,
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                items = data.get("items", [])
                return {
                    "status": "success",
                    "server_url": server_url,
                    "endpoint": "/api/accounts/requests",
                    "total": data.get("total", len(items)),
                    "page": data.get("page", 1),
                    "requests": items
                }
            else:
                return {
                    "status": "error",
                    "message": f"Failed to fetch account requests: HTTP {response.status_code}",
                    "detail": response.text
                }
    except HTTPException:
        raise
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error connecting to Salesforce app: {str(e)}"
        }

@router.get("/external/cases")
async def fetch_external_cases(
    connector_id: int = Query(..., description="Connector ID to fetch cases from"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Fetch cases from remote Salesforce backend application using connector config"""
    connector = db.query(Connector).filter(
        Connector.id == connector_id,
        Connector.connector_type == "salesforce"
    ).first()

    if not connector:
        raise HTTPException(status_code=404, detail="Salesforce connector not found")

    server_url = (connector.connection_config or {}).get("server_url", "").rstrip("/")
    if not server_url:
        raise HTTPException(status_code=400, detail="Server URL is not configured")

    try:
        # Authenticate with the external Salesforce app
        sf_token = await authenticate_with_salesforce(server_url)
        headers = {"Authorization": f"Bearer {sf_token}"}

        async with httpx.AsyncClient(verify=False) as client:
            # Try authenticated endpoints to fetch cases and user account creation requests
            for path in ["/api/cases", "/api/accounts/requests", "/cases", "/api/v1/cases", "/api/users", "/api/account-requests", "/api/user-requests", "/api/requests"]:
                try:
                    response = await client.get(f"{server_url}{path}", headers=headers, timeout=10)
                    if response.status_code == 200:
                        cases_data = response.json()
                        # Handle various response formats
                        if isinstance(cases_data, dict):
                            if 'items' in cases_data:
                                items = cases_data['items']
                            elif 'data' in cases_data:
                                items = cases_data['data']
                            elif 'cases' in cases_data:
                                items = cases_data['cases']
                            elif 'records' in cases_data:
                                items = cases_data['records']
                            elif 'requests' in cases_data:
                                items = cases_data['requests']
                            elif 'users' in cases_data:
                                items = cases_data['users']
                            else:
                                items = cases_data
                        else:
                            items = cases_data
                        return {
                            "status": "success",
                            "server_url": server_url,
                            "endpoint": path,
                            "cases_count": len(items) if isinstance(items, list) else 1,
                            "cases": items
                        }
                except Exception:
                    continue

            return {
                "status": "error",
                "message": f"Could not fetch cases from {server_url}"
            }
    except HTTPException:
        raise
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error connecting to remote server: {str(e)}"
        }
async def authenticate_with_servicenow(server_url: str, email: str = "admin@company.com", password: str = "admin123") -> str:
    """Authenticate with the external ServiceNow application and return a bearer token"""
    async with httpx.AsyncClient(verify=False) as client:
        response = await client.post(
            f"{server_url}/token",
            data={"username": email, "password": password},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            return data.get("access_token", "")
        raise HTTPException(
            status_code=401,
            detail=f"Failed to authenticate with ServiceNow app: HTTP {response.status_code}"
        )


def validate_account_request(request: Dict[str, Any]) -> Dict[str, Any]:
    """Thorough validation of an account creation request."""
    errors = []
    warnings = []

    # Required field: account name
    name = request.get("name", "")
    if not name or not str(name).strip():
        errors.append("Account name is required and cannot be empty")
    elif len(str(name).strip()) < 2:
        errors.append(f"Account name is too short: '{name}' (minimum 2 characters)")

    # Status must be PENDING
    status = request.get("status")
    if status != "PENDING":
        errors.append(f"Request status must be PENDING, got: '{status}'")

    # Must have a requesting user
    requested_by = request.get("requested_by_id")
    if not requested_by:
        errors.append("Requesting user ID is missing")

    # Must have a correlation ID for tracking
    correlation_id = request.get("correlation_id")
    if not correlation_id:
        warnings.append("Missing correlation ID - traceability will be limited")

    # Check if integration already completed (duplicate processing guard)
    integration_status = request.get("integration_status")
    if integration_status == "COMPLETED":
        errors.append("Request was already processed (integration_status=COMPLETED)")

    # Check for already-created account (idempotency guard)
    if request.get("created_account_id"):
        errors.append(f"Account already created (account_id={request['created_account_id']})")

    # Warn if ServiceNow ticket already exists from a prior attempt
    if request.get("servicenow_ticket_id"):
        warnings.append(f"ServiceNow ticket already exists: {request['servicenow_ticket_id']}")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "request_id": request.get("id"),
        "account_name": name,
        "checks_performed": [
            "account_name_present",
            "account_name_length",
            "status_is_pending",
            "requesting_user_present",
            "correlation_id_present",
            "not_already_processed",
            "no_duplicate_account",
            "prior_servicenow_ticket_check"
        ]
    }


class SingleRequestPayload(BaseModel):
    request_id: int
    account_name: str


class SingleRequestWithData(BaseModel):
    request_id: int
    account_name: str
    request_data: Optional[Dict[str, Any]] = None


@router.post("/validate-single-request")
async def validate_single_request_endpoint(
    payload: SingleRequestPayload,
    connector_id: int = Query(..., description="Salesforce connector ID"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Validate a single account creation request.
    Returns validation result with any errors or warnings.
    """
    # Get Salesforce connector
    sf_connector = db.query(Connector).filter(
        Connector.id == connector_id,
        Connector.connector_type == "salesforce"
    ).first()
    if not sf_connector:
        raise HTTPException(status_code=404, detail="Salesforce connector not found")

    sf_url = (sf_connector.connection_config or {}).get("server_url", "").rstrip("/")
    if not sf_url:
        raise HTTPException(status_code=400, detail="Salesforce server URL is not configured")

    async with httpx.AsyncClient(verify=False, timeout=30) as client:
        try:
            # Authenticate with Salesforce
            sf_token = await authenticate_with_salesforce(sf_url)

            # Fetch all requests and filter by ID (Salesforce doesn't have single request endpoint)
            sf_response = await client.get(
                f"{sf_url}/api/accounts/requests",
                headers={"Authorization": f"Bearer {sf_token}"}
            )

            if sf_response.status_code != 200:
                raise HTTPException(
                    status_code=502,
                    detail=f"Failed to fetch requests from Salesforce: HTTP {sf_response.status_code}"
                )

            all_requests = sf_response.json()
            items = all_requests.get("items", all_requests) if isinstance(all_requests, dict) else all_requests

            # Find the specific request by ID
            account_req = None
            for req in items:
                if req.get("id") == payload.request_id:
                    account_req = req
                    break

            if not account_req:
                raise HTTPException(
                    status_code=404,
                    detail=f"Request with ID {payload.request_id} not found in Salesforce"
                )

            # Validate the request
            validation = validate_account_request(account_req)

            # Generate a MuleSoft transaction ID for tracking
            import uuid
            mulesoft_tx_id = f"MULE-{uuid.uuid4().hex[:12]}"

            # Update integration status in Salesforce
            new_status = "VALIDATED" if validation["valid"] else "VALIDATION_FAILED"
            try:
                update_response = await client.put(
                    f"{sf_url}/api/accounts/requests/{payload.request_id}",
                    headers={
                        "Authorization": f"Bearer {sf_token}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "integration_status": new_status,
                        "mulesoft_transaction_id": mulesoft_tx_id
                    }
                )
                status_updated = update_response.status_code in [200, 201]
            except Exception as e:
                print(f"Warning: Could not update Salesforce request status: {e}")
                status_updated = False

            # Log validation
            log = IntegrationLog(
                integration_id=1,
                level="INFO" if validation["valid"] else "WARNING",
                message=(
                    f"Single request validation {'PASSED' if validation['valid'] else 'FAILED'} - "
                    f"Account: {account_req.get('name', 'N/A')}, "
                    f"SF Request ID: {payload.request_id}, "
                    f"TX ID: {mulesoft_tx_id}"
                )
            )
            db.add(log)
            db.commit()

            return {
                **validation,
                "mulesoft_transaction_id": mulesoft_tx_id,
                "integration_status": new_status,
                "status_updated": status_updated,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Validation error: {str(e)}")


@router.post("/send-single-to-servicenow")
async def send_single_to_servicenow_endpoint(
    payload: SingleRequestWithData,
    connector_id: int = Query(..., description="Salesforce connector ID"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Send a single validated account request to ServiceNow.
    The request must have been validated first.
    """
    # Get Salesforce connector
    sf_connector = db.query(Connector).filter(
        Connector.id == connector_id,
        Connector.connector_type == "salesforce"
    ).first()
    if not sf_connector:
        raise HTTPException(status_code=404, detail="Salesforce connector not found")

    sf_url = (sf_connector.connection_config or {}).get("server_url", "").rstrip("/")
    if not sf_url:
        raise HTTPException(status_code=400, detail="Salesforce server URL is not configured")

    # Get ServiceNow connector URL
    sn_url = "http://servicenow-backend:4780"
    try:
        all_connectors = db.query(Connector).all()
        for c in all_connectors:
            if c.connector_type == "servicenow" and c.connection_config:
                sn_url = c.connection_config.get("server_url", sn_url).rstrip("/")
                break
    except Exception:
        pass

    async with httpx.AsyncClient(verify=False, timeout=30) as client:
        try:
            # Authenticate with Salesforce
            sf_token = await authenticate_with_salesforce(sf_url)

            # Fetch all requests and filter by ID (Salesforce doesn't have single request endpoint)
            sf_response = await client.get(
                f"{sf_url}/api/accounts/requests",
                headers={"Authorization": f"Bearer {sf_token}"}
            )

            if sf_response.status_code != 200:
                raise HTTPException(
                    status_code=502,
                    detail=f"Failed to fetch requests from Salesforce: HTTP {sf_response.status_code}"
                )

            all_requests = sf_response.json()
            items = all_requests.get("items", all_requests) if isinstance(all_requests, dict) else all_requests

            # Find the specific request by ID
            account_req = None
            for req in items:
                if req.get("id") == payload.request_id:
                    account_req = req
                    break

            if not account_req:
                return {
                    "success": False,
                    "error": f"Request with ID {payload.request_id} not found in Salesforce"
                }

            # Re-validate to ensure request hasn't changed
            validation = validate_account_request(account_req)
            if not validation["valid"]:
                return {
                    "success": False,
                    "error": f"Request is no longer valid: {'; '.join(validation['errors'])}",
                    "validation": validation
                }

            # Authenticate with ServiceNow
            try:
                sn_token = await authenticate_with_servicenow(sn_url)
            except Exception as e:
                return {
                    "success": False,
                    "error": f"Cannot authenticate with ServiceNow: {str(e)}"
                }

            # Create ServiceNow ticket
            import uuid
            mulesoft_tx_id = f"MULE-{uuid.uuid4().hex[:12]}"

            sn_ticket_payload = {
                "title": f"Account Creation Approval - {account_req['name']}",
                "description": (
                    f"APPROVAL REQUIRED: New account creation request from Salesforce.\n\n"
                    f"Account Name: {account_req['name']}\n"
                    f"Requested By: User ID {account_req.get('requested_by_id')}\n"
                    f"Correlation ID: {account_req.get('correlation_id')}\n"
                    f"Salesforce Request ID: {account_req['id']}\n"
                    f"MuleSoft Transaction ID: {mulesoft_tx_id}\n"
                    f"Created At: {account_req.get('created_at')}\n\n"
                    f"This request has been validated by MuleSoft Integration Platform.\n"
                    f"Please review and approve/reject this account creation in ServiceNow."
                ),
                "ticket_type": "service_request",
                "priority": "medium",
                "category": "Account Management",
                "subcategory": "New Account Creation",
                "urgency": "medium",
                "business_justification": f"Salesforce account creation request for '{account_req['name']}' - requires manual approval"
            }

            sn_response = await client.post(
                f"{sn_url}/tickets/",
                headers={
                    "Authorization": f"Bearer {sn_token}",
                    "Content-Type": "application/json"
                },
                json=sn_ticket_payload
            )

            if sn_response.status_code not in [200, 201]:
                return {
                    "success": False,
                    "error": f"Failed to create ServiceNow ticket: HTTP {sn_response.status_code}",
                    "detail": sn_response.text
                }

            sn_ticket_data = sn_response.json()
            ticket_id = sn_ticket_data.get("id")
            ticket_number = sn_ticket_data.get("ticket_number")

            # Set ticket to pending_approval
            if ticket_id:
                try:
                    await client.put(
                        f"{sn_url}/tickets/{ticket_id}",
                        headers={
                            "Authorization": f"Bearer {sn_token}",
                            "Content-Type": "application/json"
                        },
                        json={"status": "pending_approval"}
                    )
                except Exception:
                    pass  # Non-critical

            # Update the request in Salesforce with ServiceNow ticket info
            try:
                await client.put(
                    f"{sf_url}/api/accounts/requests/{payload.request_id}",
                    headers={
                        "Authorization": f"Bearer {sf_token}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "servicenow_ticket_id": ticket_number or f"TKT{ticket_id}",
                        "servicenow_status": "REQUESTED",
                        "mulesoft_transaction_id": mulesoft_tx_id,
                        "integration_status": "COMPLETED"
                    }
                )
            except Exception as e:
                print(f"Warning: Could not update Salesforce request: {e}")

            # Log the integration
            log = IntegrationLog(
                integration_id=1,
                level="INFO",
                message=(
                    f"Single request sent to ServiceNow - "
                    f"Account: {account_req['name']}, "
                    f"SF Request ID: {payload.request_id}, "
                    f"SN Ticket: {ticket_number}, "
                    f"TX ID: {mulesoft_tx_id}"
                )
            )
            db.add(log)
            db.commit()

            return {
                "success": True,
                "ticket_id": ticket_id,
                "ticket_number": ticket_number,
                "mulesoft_transaction_id": mulesoft_tx_id,
                "message": "Request sent to ServiceNow for manual approval",
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }

        except HTTPException:
            raise
        except Exception as e:
            # Log the error
            log = IntegrationLog(
                integration_id=1,
                level="ERROR",
                message=f"Failed to send request to ServiceNow - Request ID: {payload.request_id}, Error: {str(e)}"
            )
            db.add(log)
            db.commit()

            return {
                "success": False,
                "error": str(e)
            }


async def get_case_by_salesforce_id_platform_event_format(
    salesforce_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get case by Salesforce ID in Platform Event format"""
    case = db.query(SalesforceCase).filter(SalesforceCase.salesforce_id == salesforce_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    # Create platform event format
    platform_event = PlatformEventFormat(
        eventId=f"case-{case.salesforce_id}-{int(datetime.utcnow().timestamp())}",
        eventTime=datetime.utcnow().isoformat() + "Z",
        data={
            "caseId": case.salesforce_id,
            "caseNumber": case.case_number,
            "subject": case.subject,
            "description": case.description,
            "status": case.status,
            "priority": case.priority,
            "origin": case.origin,
            "account": {
                "id": case.account_id,
                "name": case.account_name
            } if case.account_id else None,
            "contact": {
                "id": case.contact_id,
                "name": case.contact_name
            } if case.contact_id else None,
            "owner": {
                "id": case.owner_id,
                "name": case.owner_name
            } if case.owner_id else None,
            "createdDate": case.created_date.isoformat() + "Z" if case.created_date else None,
            "closedDate": case.closed_date.isoformat() + "Z" if case.closed_date else None,
            "lastModifiedDate": case.last_modified_date.isoformat() + "Z" if case.last_modified_date else None
        },
        metadata={
            "syncedAt": case.synced_at.isoformat() + "Z",
            "source": "MuleSoft Integration Platform",
            "version": "1.0",
            "connector": "Salesforce",
            "dataFormat": "platform-event"
        }
    )
    
    return platform_event