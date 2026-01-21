from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime
import httpx
import base64
import json

from app.database import get_db
from app.models import SalesforceCase, Connector, ConnectorType
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
    """Get Salesforce OAuth token or authenticate with external app"""
    # For external app on port 5173, authenticate with login endpoint
    if "5173" in config.get("instance_url", ""):
        auth_url = f"{config['instance_url']}{config.get('auth_endpoint', '/api/auth/login')}"
        
        login_data = {
            "username": config["username"],
            "password": config["password"]
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(auth_url, json=login_data, timeout=10)
                if response.status_code == 200:
                    auth_data = response.json()
                    # Extract token from response (adjust based on your app's response format)
                    token = auth_data.get("access_token") or auth_data.get("token") or auth_data.get("jwt")
                    
                    return SalesforceAuthResponse(
                        access_token=token or "authenticated",
                        instance_url=config["instance_url"],
                        token_type="Bearer"
                    )
                else:
                    raise HTTPException(status_code=400, detail=f"External app auth failed: {response.text}")
            except httpx.RequestError as e:
                raise HTTPException(status_code=400, detail=f"Cannot connect to external app: {str(e)}")
    
    # Standard Salesforce OAuth flow
    auth_url = f"{config['instance_url']}/services/oauth2/token"
    
    data = {
        "grant_type": "password",
        "client_id": config["client_id"],
        "client_secret": config["client_secret"],
        "username": config["username"],
        "password": config["password"] + config.get("security_token", "")
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(auth_url, data=data)
        if response.status_code != 200:
            raise HTTPException(status_code=400, detail=f"Salesforce auth failed: {response.text}")
        
        auth_data = response.json()
        return SalesforceAuthResponse(**auth_data)

async def fetch_salesforce_cases(auth: SalesforceAuthResponse, limit: int = 100) -> List[Dict[str, Any]]:
    """Fetch cases from Salesforce or external app"""
    # For external app on port 5173
    if "5173" in auth.instance_url:
        headers = {}
        if auth.access_token and auth.access_token != "authenticated":
            headers["Authorization"] = f"Bearer {auth.access_token}"
        
        async with httpx.AsyncClient() as client:
            try:
                # Try to fetch cases from your external app
                response = await client.get(
                    f"{auth.instance_url}/api/cases", 
                    headers=headers,
                    timeout=10
                )
                if response.status_code == 200:
                    cases_data = response.json()
                    # Handle both list and single object responses
                    if isinstance(cases_data, list):
                        return cases_data[:limit]
                    elif isinstance(cases_data, dict):
                        # If it's a dict with a 'data' or 'cases' key
                        if 'data' in cases_data:
                            return cases_data['data'][:limit]
                        elif 'cases' in cases_data:
                            return cases_data['cases'][:limit]
                        else:
                            return [cases_data]  # Single case object
                    else:
                        return []
                else:
                    print(f"External app returned status {response.status_code}: {response.text}")
                    return []
            except Exception as e:
                print(f"External app connection error: {e}")
                return []
    
    # Standard Salesforce SOQL query
    query = f"""
    SELECT Id, CaseNumber, Subject, Description, Status, Priority, Origin,
           Account.Id, Account.Name, Contact.Id, Contact.Name,
           Owner.Id, Owner.Name, CreatedDate, ClosedDate, LastModifiedDate
    FROM Case
    ORDER BY LastModifiedDate DESC
    LIMIT {limit}
    """
    
    headers = {
        "Authorization": f"Bearer {auth.access_token}",
        "Content-Type": "application/json"
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{auth.instance_url}/services/data/v58.0/query",
            params={"q": query},
            headers=headers
        )
        
        if response.status_code != 200:
            raise HTTPException(status_code=400, detail=f"Salesforce query failed: {response.text}")
        
        return response.json()["records"]

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
        Connector.type == ConnectorType.SALESFORCE
    ).first()
    
    if not connector:
        raise HTTPException(status_code=404, detail="Salesforce connector not found")
    
    try:
        # Get Salesforce auth token
        auth = await get_salesforce_token(connector.config)
        
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
            "externalAppUrl": "http://host.docker.internal:5173"
        }
    )
    
    return platform_event
async def test_external_salesforce_app():
    """Test connection to external Salesforce app on port 5173"""
    try:
        async with httpx.AsyncClient() as client:
            # Test basic connectivity using host.docker.internal
            response = await client.get("http://host.docker.internal:5173", timeout=5)
            return {
                "status": "success",
                "message": "External Salesforce app is reachable",
                "status_code": response.status_code,
                "app_running": True
            }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Cannot connect to external app: {str(e)}",
            "app_running": False
        }

@router.get("/external/cases")
async def fetch_external_cases():
    """Fetch cases directly from external Salesforce app with authentication"""
    try:
        async with httpx.AsyncClient() as client:
            # First authenticate
            auth_response = await client.post(
                "http://host.docker.internal:5173/api/auth/login",
                json={"username": "admin", "password": "admin123"},
                timeout=10
            )
            
            if auth_response.status_code != 200:
                return {
                    "status": "error",
                    "message": f"Authentication failed: {auth_response.text}",
                    "status_code": auth_response.status_code
                }
            
            auth_data = auth_response.json()
            token = auth_data.get("access_token") or auth_data.get("token") or auth_data.get("jwt")
            
            # Now fetch cases with authentication
            headers = {}
            if token:
                headers["Authorization"] = f"Bearer {token}"
            
            cases_response = await client.get(
                "http://host.docker.internal:5173/api/cases",
                headers=headers,
                timeout=10
            )
            
            if cases_response.status_code == 200:
                cases_data = cases_response.json()
                return {
                    "status": "success",
                    "authenticated": True,
                    "cases_count": len(cases_data) if isinstance(cases_data, list) else 1,
                    "cases": cases_data
                }
            else:
                return {
                    "status": "error",
                    "message": f"Failed to fetch cases: {cases_response.text}",
                    "status_code": cases_response.status_code,
                    "authenticated": True
                }
            
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error connecting to external app: {str(e)}"
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