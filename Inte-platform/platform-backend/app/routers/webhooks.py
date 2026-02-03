"""
Webhooks Router - Receive webhooks from external systems (ServiceNow, Salesforce, etc.)
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Dict, Any, Optional
from datetime import datetime
import httpx

from app.database import get_db
from app.models import Connector, IntegrationLog

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


class ServiceNowApprovalUpdate(BaseModel):
    """Webhook payload from ServiceNow when approval status changes"""
    ticket_number: str
    status: str  # approved, rejected, pending
    approval_id: int
    comments: Optional[str] = None
    timestamp: str
    source: str = "servicenow"


class WebhookResponse(BaseModel):
    """Standard webhook response"""
    success: bool
    message: str
    timestamp: str


async def update_salesforce_request_status(
    ticket_number: str,
    status: str,
    comments: Optional[str],
    db: Session
):
    """Update the corresponding Salesforce request with the approval status"""
    try:
        # Get Salesforce connector
        sf_connector = db.query(Connector).filter(
            Connector.connector_type == "salesforce"
        ).first()

        if not sf_connector or not sf_connector.connection_config:
            print("No Salesforce connector configured")
            return False

        sf_url = sf_connector.connection_config.get("server_url", "").rstrip("/")
        if not sf_url:
            print("No Salesforce URL configured")
            return False

        async with httpx.AsyncClient(timeout=15, verify=False) as client:
            # Authenticate with Salesforce
            auth_response = await client.post(
                f"{sf_url}/api/auth/login",
                json={"username": "admin", "password": "admin123"}
            )

            if auth_response.status_code != 200:
                print(f"Failed to authenticate with Salesforce: {auth_response.status_code}")
                return False

            sf_token = auth_response.json().get("access_token", "")

            # Map ServiceNow status to Salesforce main status
            main_status_map = {
                "approved": "APPROVED",
                "rejected": "REJECTED",
                "pending": "PENDING"
            }

            # Integration status should show COMPLETED when approved
            integration_status_map = {
                "approved": "COMPLETED",
                "rejected": "REJECTED",
                "pending": "PENDING_APPROVAL"
            }

            # Find and update the request by servicenow_ticket_id
            requests_response = await client.get(
                f"{sf_url}/api/accounts/requests",
                headers={"Authorization": f"Bearer {sf_token}"}
            )

            if requests_response.status_code == 200:
                response_data = requests_response.json()
                # Handle paginated response - items are in "items" key
                requests_list = response_data.get("items", response_data) if isinstance(response_data, dict) else response_data

                print(f"Searching for ticket {ticket_number} in {len(requests_list)} requests")

                for request in requests_list:
                    # Check if this request is associated with the ServiceNow ticket
                    # The field is servicenow_ticket_id in Salesforce
                    sn_ticket = request.get("servicenow_ticket_id")
                    print(f"Request {request.get('id')}: servicenow_ticket_id={sn_ticket}")

                    if sn_ticket == ticket_number:
                        request_id = request['id']

                        # If approved, call the mulesoft-callback endpoint to create the account
                        if status.lower() == "approved":
                            print(f"Calling mulesoft-callback to create account for request {request_id}")
                            callback_payload = {
                                "accepted": True,
                                "status": "APPROVED",
                                "message": comments or "Approved via ServiceNow"
                            }
                            callback_response = await client.post(
                                f"{sf_url}/api/accounts/requests/{request_id}/mulesoft-callback",
                                headers={
                                    "X-MuleSoft-Secret": "mulesoft-salesforce-shared-secret-2024",
                                    "Content-Type": "application/json"
                                },
                                json=callback_payload
                            )
                            print(f"Mulesoft callback response: {callback_response.status_code}")
                            if callback_response.status_code in [200, 201]:
                                print(f"Successfully created account for request {request_id}")
                                return True
                            else:
                                print(f"Failed to create account: {callback_response.text}")
                                return False

                        elif status.lower() == "rejected":
                            # For rejection, call callback with accepted=False
                            print(f"Calling mulesoft-callback to reject request {request_id}")
                            callback_payload = {
                                "accepted": False,
                                "status": "REJECTED",
                                "message": comments or "Rejected via ServiceNow"
                            }
                            callback_response = await client.post(
                                f"{sf_url}/api/accounts/requests/{request_id}/mulesoft-callback",
                                headers={
                                    "X-MuleSoft-Secret": "mulesoft-salesforce-shared-secret-2024",
                                    "Content-Type": "application/json"
                                },
                                json=callback_payload
                            )
                            print(f"Rejection callback response: {callback_response.status_code}")
                            return callback_response.status_code in [200, 201]

                        else:
                            # For pending status, just update the status fields
                            update_payload = {
                                "integration_status": integration_status_map.get(status.lower(), "PENDING_APPROVAL"),
                                "servicenow_status": status.upper(),
                                "status": main_status_map.get(status.lower(), "PENDING")
                            }

                            print(f"Updating Salesforce request {request_id} with: {update_payload}")

                            update_response = await client.put(
                                f"{sf_url}/api/accounts/requests/{request_id}",
                                headers={
                                    "Authorization": f"Bearer {sf_token}",
                                    "Content-Type": "application/json"
                                },
                                json=update_payload
                            )

                            print(f"Salesforce update response: {update_response.status_code}")

                            if update_response.status_code in [200, 201]:
                                print(f"Successfully updated Salesforce request {request_id} with status {status}")
                                return True
                            else:
                                print(f"Failed to update Salesforce: {update_response.text}")

            print(f"Could not find Salesforce request for ticket {ticket_number}")
            return False

    except Exception as e:
        print(f"Error updating Salesforce: {e}")
        import traceback
        traceback.print_exc()
        return False


async def process_user_creation_approval(
    ticket_number: str,
    status: str,
    comments: Optional[str],
    db: Session
):
    """Process approval callback for SAP user creation tickets"""
    try:
        from app.models import UserCreationApproval

        approval = db.query(UserCreationApproval).filter(
            UserCreationApproval.servicenow_ticket_number == ticket_number
        ).first()

        if not approval:
            return False

        # Update approval status
        approval.approval_status = status.lower()
        approval.updated_at = datetime.utcnow()

        if status.lower() == "approved":
            approval.approved_at = datetime.utcnow()
        elif status.lower() == "rejected":
            approval.rejection_reason = comments

        # Add to history
        history_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "status": status,
            "comments": comments,
            "source": "servicenow_webhook"
        }
        if not approval.history:
            approval.history = []
        approval.history.append(history_entry)

        db.commit()
        return True

    except Exception as e:
        print(f"Error processing user creation approval: {e}")
        return False


@router.post("/servicenow/approval-update", response_model=WebhookResponse)
async def servicenow_approval_webhook(
    payload: ServiceNowApprovalUpdate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Webhook endpoint to receive approval status updates from ServiceNow.
    When a ticket is approved/rejected in ServiceNow, this endpoint is called
    to propagate the status change to Salesforce and handle user creation approvals.
    """
    try:
        # Log the webhook receipt
        log = IntegrationLog(
            integration_id=1,
            level="INFO",
            message=f"Received ServiceNow approval webhook: ticket={payload.ticket_number}, status={payload.status}"
        )
        db.add(log)
        db.commit()

        # Try Salesforce handler (existing)
        background_tasks.add_task(
            update_salesforce_request_status,
            payload.ticket_number,
            payload.status,
            payload.comments,
            db
        )

        # Try user creation handler (new)
        background_tasks.add_task(
            process_user_creation_approval,
            payload.ticket_number,
            payload.status,
            payload.comments,
            db
        )

        return WebhookResponse(
            success=True,
            message=f"Approval status update received for ticket {payload.ticket_number}",
            timestamp=datetime.utcnow().isoformat() + "Z"
        )

    except Exception as e:
        # Log the error
        log = IntegrationLog(
            integration_id=1,
            level="ERROR",
            message=f"ServiceNow webhook error: {str(e)}"
        )
        db.add(log)
        db.commit()

        return WebhookResponse(
            success=False,
            message=str(e),
            timestamp=datetime.utcnow().isoformat() + "Z"
        )


@router.get("/health")
async def webhooks_health():
    """Health check for webhooks endpoint"""
    return {
        "status": "healthy",
        "service": "webhooks",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
