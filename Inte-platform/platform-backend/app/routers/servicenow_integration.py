"""
ServiceNow Integration Router - Send tickets and approvals to ServiceNow application
Handles communication with ServiceNow ITSM
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from datetime import datetime
import httpx
import json

from app.database import get_db
from app.models import Connector, IntegrationLog
from app.auth import get_current_user

router = APIRouter(prefix="/servicenow", tags=["ServiceNow Integration"])

# ServiceNow Configuration - will be overridden by connector config
SERVICENOW_BASE_URL = "http://149.102.158.71:4780"
SERVICENOW_ENDPOINTS = {
    "incidents": "/api/incidents",
    "tickets": "/api/tickets",
    "approvals": "/api/approvals",
    "users": "/api/users",
    "requests": "/api/requests",
    "health": "/health"
}


class ServiceNowTicketRequest(BaseModel):
    """Request to create a ticket in ServiceNow"""
    case_data: Dict[str, Any]
    ticket_type: str = "incident"  # incident, request, change
    priority: Optional[str] = "3"
    assignment_group: Optional[str] = None
    additional_fields: Optional[Dict[str, Any]] = None


class ServiceNowApprovalRequest(BaseModel):
    """Request to create an approval in ServiceNow"""
    case_data: Dict[str, Any]
    approval_type: str = "user_account"  # user_account, access_request, change_request
    approver: Optional[str] = None
    additional_fields: Optional[Dict[str, Any]] = None


class ServiceNowResponse(BaseModel):
    """Response from ServiceNow"""
    success: bool
    servicenow_response: Optional[Dict[str, Any]] = None
    ticket_number: Optional[str] = None
    payload_sent: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    timestamp: str


def get_servicenow_base_url(db: Session) -> str:
    """Get ServiceNow base URL from connector config"""
    connector = db.query(Connector).filter(
        Connector.connector_type == "servicenow"
    ).first()
    if connector and connector.connection_config:
        return connector.connection_config.get("server_url", SERVICENOW_BASE_URL).rstrip("/")
    return SERVICENOW_BASE_URL


def transform_case_to_ticket(case_data: Dict[str, Any], ticket_type: str = "incident") -> Dict[str, Any]:
    """Transform Salesforce case / user account request to ServiceNow ticket format"""
    priority_map = {
        "Critical": "1",
        "High": "2",
        "Medium": "3",
        "Low": "4"
    }

    status_map = {
        "New": "1",
        "In Progress": "2",
        "Working": "2",
        "On Hold": "3",
        "Resolved": "6",
        "Closed": "7"
    }

    ticket = {
        "short_description": case_data.get("subject", "User Account Creation Request"),
        "description": case_data.get("description", ""),
        "priority": priority_map.get(case_data.get("priority", "Medium"), "3"),
        "state": status_map.get(case_data.get("status", "New"), "1"),
        "category": case_data.get("category", "User Account"),
        "subcategory": case_data.get("subcategory", "Account Creation"),
        "caller_id": case_data.get("contact", {}).get("name", "") if isinstance(case_data.get("contact"), dict) else case_data.get("contactName", ""),
        "assignment_group": case_data.get("assignmentGroup", "IT Service Desk"),
        "impact": priority_map.get(case_data.get("priority", "Medium"), "3"),
        "urgency": priority_map.get(case_data.get("priority", "Medium"), "3"),
        "ticket_type": ticket_type,
        "source": "Salesforce Integration Platform",
        "external_reference": case_data.get("id", case_data.get("caseId", "")),
        "correlation_id": f"SF-{case_data.get('id', case_data.get('caseId', 'UNKNOWN'))}",
        "opened_at": case_data.get("createdDate", datetime.utcnow().isoformat() + "Z"),
        "customer": {
            "name": case_data.get("account", {}).get("name", "") if isinstance(case_data.get("account"), dict) else case_data.get("accountName", ""),
            "id": case_data.get("account", {}).get("id", "") if isinstance(case_data.get("account"), dict) else case_data.get("accountId", "")
        },
        "contact": {
            "name": case_data.get("contact", {}).get("name", "") if isinstance(case_data.get("contact"), dict) else case_data.get("contactName", ""),
            "id": case_data.get("contact", {}).get("id", "") if isinstance(case_data.get("contact"), dict) else case_data.get("contactId", "")
        }
    }

    # Add user account specific fields if available
    if case_data.get("userName") or case_data.get("userEmail"):
        ticket["user_account_details"] = {
            "requested_username": case_data.get("userName", ""),
            "requested_email": case_data.get("userEmail", ""),
            "requested_role": case_data.get("userRole", "Standard User"),
            "department": case_data.get("department", ""),
            "manager": case_data.get("manager", "")
        }

    return ticket


def transform_case_to_approval(case_data: Dict[str, Any], approval_type: str = "user_account") -> Dict[str, Any]:
    """Transform case data to ServiceNow approval format"""
    approval = {
        "approval_type": approval_type,
        "short_description": f"Approval Required: {case_data.get('subject', 'User Account Creation')}",
        "description": case_data.get("description", ""),
        "priority": case_data.get("priority", "Medium"),
        "state": "requested",
        "requested_by": case_data.get("contact", {}).get("name", "") if isinstance(case_data.get("contact"), dict) else case_data.get("contactName", ""),
        "requested_for": case_data.get("account", {}).get("name", "") if isinstance(case_data.get("account"), dict) else case_data.get("accountName", ""),
        "source": "Salesforce Integration Platform",
        "external_reference": case_data.get("id", case_data.get("caseId", "")),
        "correlation_id": f"SF-APPROVAL-{case_data.get('id', case_data.get('caseId', 'UNKNOWN'))}",
        "requested_at": case_data.get("createdDate", datetime.utcnow().isoformat() + "Z"),
        "approval_details": {
            "type": approval_type,
            "case_subject": case_data.get("subject", ""),
            "case_priority": case_data.get("priority", "Medium"),
            "case_status": case_data.get("status", "New"),
            "account_name": case_data.get("account", {}).get("name", "") if isinstance(case_data.get("account"), dict) else case_data.get("accountName", ""),
            "contact_name": case_data.get("contact", {}).get("name", "") if isinstance(case_data.get("contact"), dict) else case_data.get("contactName", "")
        }
    }

    # Add user account specific approval fields
    if case_data.get("userName") or case_data.get("userEmail"):
        approval["user_account_details"] = {
            "requested_username": case_data.get("userName", ""),
            "requested_email": case_data.get("userEmail", ""),
            "requested_role": case_data.get("userRole", "Standard User"),
            "department": case_data.get("department", ""),
            "manager_approval_required": True
        }

    return approval


@router.get("/config")
async def get_servicenow_config(db: Session = Depends(get_db)):
    """Get ServiceNow integration configuration"""
    base_url = get_servicenow_base_url(db)
    return {
        "base_url": base_url,
        "endpoints": SERVICENOW_ENDPOINTS,
        "available_ticket_types": ["incident", "request", "change"],
        "available_approval_types": ["user_account", "access_request", "change_request"]
    }


@router.get("/test-connection")
async def test_servicenow_connection(
    db: Session = Depends(get_db)
):
    """Test connection to ServiceNow application"""
    base_url = get_servicenow_base_url(db)
    try:
        async with httpx.AsyncClient(timeout=10, verify=False) as client:
            # Try health endpoint first, then root
            for path in ["/health", "/", "/api"]:
                try:
                    response = await client.get(f"{base_url}{path}")
                    if response.status_code < 500:
                        return {
                            "success": True,
                            "status_code": response.status_code,
                            "message": f"ServiceNow application is reachable at {base_url}",
                            "base_url": base_url
                        }
                except Exception:
                    continue

            return {
                "success": False,
                "message": f"ServiceNow application returned errors at {base_url}",
                "base_url": base_url
            }
    except httpx.ConnectError:
        return {
            "success": False,
            "message": f"Cannot connect to ServiceNow at {base_url}",
            "suggestion": "Ensure ServiceNow application is running"
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Connection error: {str(e)}"
        }


@router.post("/send-ticket", response_model=ServiceNowResponse)
async def send_ticket_to_servicenow(
    request: ServiceNowTicketRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Transform Salesforce case/user account request and send as ticket to ServiceNow
    """
    base_url = get_servicenow_base_url(db)
    try:
        # Merge additional fields if provided
        case_data = {**request.case_data}
        if request.additional_fields:
            case_data.update(request.additional_fields)

        # Transform to ServiceNow ticket format
        ticket_payload = transform_case_to_ticket(case_data, request.ticket_type)

        if request.priority:
            ticket_payload["priority"] = request.priority
        if request.assignment_group:
            ticket_payload["assignment_group"] = request.assignment_group

        # Try multiple endpoints to send the ticket
        endpoints_to_try = [
            f"{base_url}{SERVICENOW_ENDPOINTS['tickets']}",
            f"{base_url}{SERVICENOW_ENDPOINTS['incidents']}",
            f"{base_url}{SERVICENOW_ENDPOINTS['requests']}",
            f"{base_url}/api/now/table/incident",
        ]

        async with httpx.AsyncClient(timeout=30, verify=False) as client:
            for endpoint_url in endpoints_to_try:
                try:
                    response = await client.post(
                        endpoint_url,
                        json=ticket_payload,
                        headers={"Content-Type": "application/json"}
                    )

                    if response.status_code in [200, 201]:
                        try:
                            sn_response = response.json()
                        except Exception:
                            sn_response = {"raw": response.text}

                        ticket_number = sn_response.get("ticket_number",
                                        sn_response.get("number",
                                        sn_response.get("result", {}).get("number",
                                        f"TKT-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}")))

                        # Log the integration
                        log = IntegrationLog(
                            integration_id=1,
                            level="INFO",
                            message=f"Sent ticket {ticket_number} to ServiceNow ({request.ticket_type}): Status {response.status_code}"
                        )
                        db.add(log)
                        db.commit()

                        return ServiceNowResponse(
                            success=True,
                            servicenow_response=sn_response,
                            ticket_number=ticket_number,
                            payload_sent=ticket_payload,
                            timestamp=datetime.utcnow().isoformat() + "Z"
                        )
                except httpx.ConnectError:
                    continue
                except Exception:
                    continue

            return ServiceNowResponse(
                success=False,
                error=f"Could not send ticket to ServiceNow at {base_url}. Tried multiple endpoints.",
                payload_sent=ticket_payload,
                timestamp=datetime.utcnow().isoformat() + "Z"
            )

    except httpx.ConnectError:
        return ServiceNowResponse(
            success=False,
            error=f"Cannot connect to ServiceNow application at {base_url}.",
            timestamp=datetime.utcnow().isoformat() + "Z"
        )
    except Exception as e:
        return ServiceNowResponse(
            success=False,
            error=str(e),
            timestamp=datetime.utcnow().isoformat() + "Z"
        )


@router.post("/send-approval", response_model=ServiceNowResponse)
async def send_approval_to_servicenow(
    request: ServiceNowApprovalRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Transform Salesforce case/user account request and send as approval to ServiceNow
    """
    base_url = get_servicenow_base_url(db)
    try:
        # Merge additional fields
        case_data = {**request.case_data}
        if request.additional_fields:
            case_data.update(request.additional_fields)

        # Transform to ServiceNow approval format
        approval_payload = transform_case_to_approval(case_data, request.approval_type)

        if request.approver:
            approval_payload["approver"] = request.approver

        # Try multiple endpoints
        endpoints_to_try = [
            f"{base_url}{SERVICENOW_ENDPOINTS['approvals']}",
            f"{base_url}/api/now/table/sysapproval_approver",
            f"{base_url}{SERVICENOW_ENDPOINTS['requests']}",
        ]

        async with httpx.AsyncClient(timeout=30, verify=False) as client:
            for endpoint_url in endpoints_to_try:
                try:
                    response = await client.post(
                        endpoint_url,
                        json=approval_payload,
                        headers={"Content-Type": "application/json"}
                    )

                    if response.status_code in [200, 201]:
                        try:
                            sn_response = response.json()
                        except Exception:
                            sn_response = {"raw": response.text}

                        approval_id = sn_response.get("approval_id",
                                      sn_response.get("sys_id",
                                      sn_response.get("result", {}).get("sys_id",
                                      f"APR-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}")))

                        # Log the integration
                        log = IntegrationLog(
                            integration_id=1,
                            level="INFO",
                            message=f"Sent approval {approval_id} to ServiceNow ({request.approval_type}): Status {response.status_code}"
                        )
                        db.add(log)
                        db.commit()

                        return ServiceNowResponse(
                            success=True,
                            servicenow_response=sn_response,
                            ticket_number=approval_id,
                            payload_sent=approval_payload,
                            timestamp=datetime.utcnow().isoformat() + "Z"
                        )
                except httpx.ConnectError:
                    continue
                except Exception:
                    continue

            return ServiceNowResponse(
                success=False,
                error=f"Could not send approval to ServiceNow at {base_url}. Tried multiple endpoints.",
                payload_sent=approval_payload,
                timestamp=datetime.utcnow().isoformat() + "Z"
            )

    except httpx.ConnectError:
        return ServiceNowResponse(
            success=False,
            error=f"Cannot connect to ServiceNow application at {base_url}.",
            timestamp=datetime.utcnow().isoformat() + "Z"
        )
    except Exception as e:
        return ServiceNowResponse(
            success=False,
            error=str(e),
            timestamp=datetime.utcnow().isoformat() + "Z"
        )


@router.post("/send-ticket-and-approval", response_model=Dict[str, Any])
async def send_ticket_and_approval_to_servicenow(
    case_data: Dict[str, Any],
    ticket_type: str = Query("incident", description="Ticket type"),
    approval_type: str = Query("user_account", description="Approval type"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Send both ticket and approval to ServiceNow in one call
    """
    base_url = get_servicenow_base_url(db)

    ticket_payload = transform_case_to_ticket(case_data, ticket_type)
    approval_payload = transform_case_to_approval(case_data, approval_type)

    ticket_result = {"success": False, "error": "Not attempted"}
    approval_result = {"success": False, "error": "Not attempted"}

    async with httpx.AsyncClient(timeout=30, verify=False) as client:
        # Send ticket
        for path in [SERVICENOW_ENDPOINTS['tickets'], SERVICENOW_ENDPOINTS['incidents']]:
            try:
                response = await client.post(
                    f"{base_url}{path}",
                    json=ticket_payload,
                    headers={"Content-Type": "application/json"}
                )
                if response.status_code in [200, 201]:
                    try:
                        sn_resp = response.json()
                    except Exception:
                        sn_resp = {"raw": response.text}
                    ticket_result = {
                        "success": True,
                        "response": sn_resp,
                        "ticket_number": sn_resp.get("ticket_number", sn_resp.get("number", f"TKT-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"))
                    }
                    break
            except Exception:
                continue

        # Send approval
        for path in [SERVICENOW_ENDPOINTS['approvals'], SERVICENOW_ENDPOINTS['requests']]:
            try:
                response = await client.post(
                    f"{base_url}{path}",
                    json=approval_payload,
                    headers={"Content-Type": "application/json"}
                )
                if response.status_code in [200, 201]:
                    try:
                        sn_resp = response.json()
                    except Exception:
                        sn_resp = {"raw": response.text}
                    approval_result = {
                        "success": True,
                        "response": sn_resp,
                        "approval_id": sn_resp.get("approval_id", sn_resp.get("sys_id", f"APR-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"))
                    }
                    break
            except Exception:
                continue

    # Log integration
    log_message = f"ServiceNow integration - Ticket: {'OK' if ticket_result['success'] else 'FAIL'}, Approval: {'OK' if approval_result['success'] else 'FAIL'}"
    log = IntegrationLog(
        integration_id=1,
        level="INFO" if ticket_result["success"] or approval_result["success"] else "ERROR",
        message=log_message
    )
    db.add(log)
    db.commit()

    return {
        "ticket": ticket_result,
        "approval": approval_result,
        "payload_sent": {
            "ticket": ticket_payload,
            "approval": approval_payload
        },
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }


@router.post("/preview-ticket")
async def preview_servicenow_ticket(
    case_data: Dict[str, Any],
    ticket_type: str = Query("incident", description="Ticket type")
):
    """
    Preview the ticket payload that would be sent to ServiceNow without actually sending
    """
    ticket_payload = transform_case_to_ticket(case_data, ticket_type)
    return {
        "ticket_payload": ticket_payload,
        "target_endpoint": f"{SERVICENOW_BASE_URL}{SERVICENOW_ENDPOINTS['tickets']}",
        "content_type": "application/json"
    }


@router.post("/preview-approval")
async def preview_servicenow_approval(
    case_data: Dict[str, Any],
    approval_type: str = Query("user_account", description="Approval type")
):
    """
    Preview the approval payload that would be sent to ServiceNow without actually sending
    """
    approval_payload = transform_case_to_approval(case_data, approval_type)
    return {
        "approval_payload": approval_payload,
        "target_endpoint": f"{SERVICENOW_BASE_URL}{SERVICENOW_ENDPOINTS['approvals']}",
        "content_type": "application/json"
    }
