"""
SAP Integration Router - Send transformed data to SAP application
Handles communication with SAP ERP on port 2004
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from datetime import datetime
import httpx
import json

from app.database import get_db
from app.models import SalesforceCase, Integration, IntegrationLog, Connector, ConnectorType
from app.auth import get_current_user
from app.transformers import (
    salesforce_case_to_electricity_load_request,
    salesforce_case_to_sap_webhook,
    salesforce_to_sap_idoc
)

router = APIRouter(prefix="/sap", tags=["SAP Integration"])

# SAP Configuration
SAP_BASE_URL = "http://host.docker.internal:2004"
SAP_ENDPOINTS = {
    "load_request_xml": "/api/integration/mulesoft/load-request/xml",
    "load_request_json": "/api/integration/mulesoft/load-request",
    "webhook": "/api/integration/webhook"
}


class SAPConnectionConfig(BaseModel):
    """SAP connection configuration"""
    base_url: str = "http://host.docker.internal:2004"
    timeout: int = 30


class SendToSAPRequest(BaseModel):
    """Request to send data to SAP"""
    case_data: Dict[str, Any]
    endpoint_type: str = "load_request_xml"  # load_request_xml, load_request_json, webhook
    additional_fields: Optional[Dict[str, Any]] = None


class SendToSAPResponse(BaseModel):
    """Response from SAP"""
    success: bool
    sap_response: Optional[Dict[str, Any]] = None
    xml_sent: Optional[str] = None
    error: Optional[str] = None
    timestamp: str


@router.get("/config")
async def get_sap_config():
    """Get SAP integration configuration"""
    return {
        "base_url": SAP_BASE_URL,
        "endpoints": SAP_ENDPOINTS,
        "available_formats": ["xml", "json", "webhook"]
    }


@router.get("/test-connection")
async def test_sap_connection(
    base_url: str = Query(SAP_BASE_URL, description="SAP base URL")
):
    """Test connection to SAP application"""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            # Try to reach the SAP application
            response = await client.get(f"{base_url}/health")
            return {
                "success": True,
                "status_code": response.status_code,
                "message": "SAP application is reachable",
                "base_url": base_url
            }
    except httpx.ConnectError:
        return {
            "success": False,
            "message": f"Cannot connect to SAP at {base_url}",
            "suggestion": "Ensure SAP application is running on port 2004"
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Connection error: {str(e)}"
        }


@router.post("/send-load-request", response_model=SendToSAPResponse)
async def send_load_request_to_sap(
    request: SendToSAPRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Transform Salesforce case data and send to SAP as ElectricityLoadRequest
    """
    try:
        # Merge additional fields if provided
        case_data = {**request.case_data}
        if request.additional_fields:
            case_data.update(request.additional_fields)

        # Transform to ElectricityLoadRequest XML
        xml_payload = salesforce_case_to_electricity_load_request(case_data)

        # Send to SAP
        endpoint_url = f"{SAP_BASE_URL}{SAP_ENDPOINTS['load_request_xml']}"

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                endpoint_url,
                content=xml_payload,
                headers={"Content-Type": "application/xml"}
            )

            if response.status_code in [200, 201]:
                sap_response = response.json() if response.headers.get("content-type", "").startswith("application/json") else {"raw": response.text}
                return SendToSAPResponse(
                    success=True,
                    sap_response=sap_response,
                    xml_sent=xml_payload,
                    timestamp=datetime.utcnow().isoformat() + "Z"
                )
            else:
                return SendToSAPResponse(
                    success=False,
                    error=f"SAP returned status {response.status_code}: {response.text}",
                    xml_sent=xml_payload,
                    timestamp=datetime.utcnow().isoformat() + "Z"
                )

    except httpx.ConnectError:
        return SendToSAPResponse(
            success=False,
            error="Cannot connect to SAP application. Ensure it's running on port 2004.",
            timestamp=datetime.utcnow().isoformat() + "Z"
        )
    except Exception as e:
        return SendToSAPResponse(
            success=False,
            error=str(e),
            timestamp=datetime.utcnow().isoformat() + "Z"
        )


@router.post("/send-webhook")
async def send_webhook_to_sap(
    case_data: Dict[str, Any],
    event_type: str = Query("CASE_CREATED", description="Event type"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Send Salesforce case data to SAP webhook endpoint
    """
    try:
        # Create webhook payload
        webhook_payload = salesforce_case_to_sap_webhook(case_data)
        webhook_payload["event_type"] = event_type

        # Send to SAP webhook
        endpoint_url = f"{SAP_BASE_URL}{SAP_ENDPOINTS['webhook']}"

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                endpoint_url,
                json=webhook_payload,
                headers={"Content-Type": "application/json"}
            )

            return {
                "success": response.status_code in [200, 201],
                "status_code": response.status_code,
                "sap_response": response.json() if response.status_code == 200 else response.text,
                "payload_sent": webhook_payload,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }


@router.post("/send-case/{case_id}")
async def send_salesforce_case_to_sap(
    case_id: int,
    format: str = Query("xml", description="Format: xml, json, or webhook"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Send a synced Salesforce case to SAP
    This reads the case from the database and sends it to SAP
    """
    # Get the case from database
    case = db.query(SalesforceCase).filter(SalesforceCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # Build case data
    case_data = {
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
        "createdDate": case.created_date.isoformat() + "Z" if case.created_date else None
    }

    # Add any raw data fields that might have load request info
    if case.raw_data:
        case_data.update({
            "currentLoad": case.raw_data.get("currentLoad"),
            "requestedLoad": case.raw_data.get("requestedLoad"),
            "connectionType": case.raw_data.get("connectionType"),
            "city": case.raw_data.get("city"),
            "pinCode": case.raw_data.get("pinCode")
        })

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            if format == "xml":
                # Transform and send as XML
                xml_payload = salesforce_case_to_electricity_load_request(case_data)
                response = await client.post(
                    f"{SAP_BASE_URL}{SAP_ENDPOINTS['load_request_xml']}",
                    content=xml_payload,
                    headers={"Content-Type": "application/xml"}
                )
                payload_sent = xml_payload
            elif format == "json":
                # Send as JSON load request
                json_payload = {
                    "RequestID": f"SF-{case.salesforce_id}",
                    "CustomerID": f"CUST-{case.account_id or 'DEFAULT'}",
                    "CurrentLoad": case_data.get("currentLoad") or 5,
                    "RequestedLoad": case_data.get("requestedLoad") or 10,
                    "ConnectionType": case_data.get("connectionType") or ("COMMERCIAL" if case.priority in ["Critical", "High"] else "RESIDENTIAL"),
                    "City": case_data.get("city") or "Hyderabad",
                    "PinCode": case_data.get("pinCode") or "500001"
                }
                response = await client.post(
                    f"{SAP_BASE_URL}{SAP_ENDPOINTS['load_request_json']}",
                    json=json_payload,
                    headers={"Content-Type": "application/json"}
                )
                payload_sent = json_payload
            else:  # webhook
                webhook_payload = salesforce_case_to_sap_webhook(case_data)
                response = await client.post(
                    f"{SAP_BASE_URL}{SAP_ENDPOINTS['webhook']}",
                    json=webhook_payload,
                    headers={"Content-Type": "application/json"}
                )
                payload_sent = webhook_payload

            # Log the integration
            log = IntegrationLog(
                integration_id=1,  # Default integration
                level="INFO" if response.status_code in [200, 201] else "ERROR",
                message=f"Sent case {case.case_number} to SAP ({format}): Status {response.status_code}"
            )
            db.add(log)
            db.commit()

            return {
                "success": response.status_code in [200, 201],
                "case_id": case_id,
                "salesforce_id": case.salesforce_id,
                "format": format,
                "status_code": response.status_code,
                "sap_response": response.json() if response.status_code in [200, 201] and "application/json" in response.headers.get("content-type", "") else response.text,
                "payload_sent": payload_sent,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }

    except httpx.ConnectError:
        return {
            "success": False,
            "case_id": case_id,
            "error": "Cannot connect to SAP. Ensure the application is running on port 2004.",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    except Exception as e:
        return {
            "success": False,
            "case_id": case_id,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }


@router.post("/batch-send")
async def batch_send_to_sap(
    case_ids: List[int],
    format: str = Query("xml", description="Format: xml, json, or webhook"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Send multiple Salesforce cases to SAP in batch
    """
    results = []
    success_count = 0
    error_count = 0

    for case_id in case_ids:
        case = db.query(SalesforceCase).filter(SalesforceCase.id == case_id).first()
        if not case:
            results.append({
                "case_id": case_id,
                "success": False,
                "error": "Case not found"
            })
            error_count += 1
            continue

        case_data = {
            "caseId": case.salesforce_id,
            "caseNumber": case.case_number,
            "subject": case.subject,
            "status": case.status,
            "priority": case.priority,
            "account": {"id": case.account_id, "name": case.account_name} if case.account_id else None
        }

        try:
            xml_payload = salesforce_case_to_electricity_load_request(case_data)

            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    f"{SAP_BASE_URL}{SAP_ENDPOINTS['load_request_xml']}",
                    content=xml_payload,
                    headers={"Content-Type": "application/xml"}
                )

                if response.status_code in [200, 201]:
                    success_count += 1
                    results.append({
                        "case_id": case_id,
                        "salesforce_id": case.salesforce_id,
                        "success": True,
                        "sap_response": response.json() if "application/json" in response.headers.get("content-type", "") else {"status": "sent"}
                    })
                else:
                    error_count += 1
                    results.append({
                        "case_id": case_id,
                        "success": False,
                        "error": f"SAP returned {response.status_code}"
                    })

        except Exception as e:
            error_count += 1
            results.append({
                "case_id": case_id,
                "success": False,
                "error": str(e)
            })

    return {
        "total": len(case_ids),
        "success_count": success_count,
        "error_count": error_count,
        "results": results,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }


@router.post("/preview-xml")
async def preview_sap_xml(case_data: Dict[str, Any]):
    """
    Preview the XML that would be sent to SAP without actually sending
    """
    xml_output = salesforce_case_to_electricity_load_request(case_data)
    return {
        "xml": xml_output,
        "endpoint": f"{SAP_BASE_URL}{SAP_ENDPOINTS['load_request_xml']}",
        "content_type": "application/xml"
    }
