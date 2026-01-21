"""
Transform Router - API endpoints for data transformation operations
Supports Salesforce to SAP XML/IDoc conversion and custom transformations
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from datetime import datetime

from app.database import get_db
from app.models import SalesforceCase, Integration, IntegrationLog
from app.auth import get_current_user
from app.transformers import (
    salesforce_to_sap_xml,
    salesforce_to_sap_idoc,
    json_to_xml,
    transform_with_mapping,
    salesforce_case_to_electricity_load_request,
    SAP_IDOC_TEMPLATES
)

router = APIRouter(prefix="/transform", tags=["Data Transformation"])


class TransformRequest(BaseModel):
    """Request body for transformation"""
    source_data: Dict[str, Any]
    target_format: str = "sap_xml"  # sap_xml, sap_idoc, generic_xml, electricity_load_request
    idoc_type: Optional[str] = "SRCLST"
    field_mapping: Optional[Dict[str, str]] = None
    include_metadata: bool = True


class TransformResponse(BaseModel):
    """Response from transformation"""
    success: bool
    output: str
    format: str
    source_records: int = 1
    transform_time: str
    warnings: List[str] = []


class TransformTemplate(BaseModel):
    """Transform template definition"""
    id: str
    name: str
    description: str
    source_system: str
    target_system: str
    target_format: str
    field_mapping: Dict[str, str]
    idoc_type: Optional[str] = None


# Pre-defined transform templates
TRANSFORM_TEMPLATES = {
    "sf_to_sap_service": TransformTemplate(
        id="sf_to_sap_service",
        name="Salesforce Case to SAP Service Request",
        description="Transform Salesforce Case events to SAP Service Request IDoc (SRCLST)",
        source_system="Salesforce",
        target_system="SAP",
        target_format="sap_idoc",
        idoc_type="SRCLST",
        field_mapping={
            "caseId": "OBJECT_ID",
            "caseNumber": "EXT_REF_NO",
            "subject": "DESCRIPTION",
            "description": "LONG_TEXT",
            "status": "STAT_ORDERSTATUS",
            "priority": "PRIORITY",
            "account.id": "CUSTOMER_ID",
            "account.name": "CUSTOMER_NAME",
            "contact.id": "CONTACT_ID",
            "contact.name": "CONTACT_NAME",
            "createdDate": "CREATED_AT",
            "lastModifiedDate": "CHANGED_AT"
        }
    ),
    "sf_to_sap_customer": TransformTemplate(
        id="sf_to_sap_customer",
        name="Salesforce Account to SAP Customer Master",
        description="Transform Salesforce Account to SAP Customer Master IDoc (DEBMAS)",
        source_system="Salesforce",
        target_system="SAP",
        target_format="sap_idoc",
        idoc_type="DEBMAS",
        field_mapping={
            "account.id": "KUNNR",
            "account.name": "NAME1",
            "contact.name": "CONTACT_NAME"
        }
    ),
    "sf_to_sap_order": TransformTemplate(
        id="sf_to_sap_order",
        name="Salesforce Opportunity to SAP Sales Order",
        description="Transform Salesforce Opportunity to SAP Sales Order IDoc (ORDERS)",
        source_system="Salesforce",
        target_system="SAP",
        target_format="sap_idoc",
        idoc_type="ORDERS",
        field_mapping={
            "caseNumber": "BELNR",
            "account.id": "KUNNR",
            "subject": "DESCRIPTION"
        }
    ),
    "sf_to_sap_crm": TransformTemplate(
        id="sf_to_sap_crm",
        name="Salesforce Case to SAP CRM Order",
        description="Transform Salesforce Case to SAP CRM Order IDoc",
        source_system="Salesforce",
        target_system="SAP CRM",
        target_format="sap_idoc",
        idoc_type="CRMXIF_ORDER",
        field_mapping={
            "caseId": "OBJECT_ID",
            "caseNumber": "EXT_REF_NO",
            "subject": "DESCRIPTION",
            "description": "LONG_TEXT",
            "status": "STAT_ORDERSTATUS",
            "priority": "PRIORITY"
        }
    ),
    "generic_json_to_xml": TransformTemplate(
        id="generic_json_to_xml",
        name="Generic JSON to XML",
        description="Convert any JSON payload to XML format",
        source_system="Any",
        target_system="Any",
        target_format="generic_xml",
        field_mapping={}
    )
}


@router.get("/templates")
async def get_transform_templates():
    """Get available transform templates"""
    return {
        "templates": [t.dict() for t in TRANSFORM_TEMPLATES.values()],
        "idoc_types": SAP_IDOC_TEMPLATES
    }


@router.get("/templates/{template_id}")
async def get_template(template_id: str):
    """Get a specific transform template"""
    if template_id not in TRANSFORM_TEMPLATES:
        raise HTTPException(status_code=404, detail="Template not found")
    return TRANSFORM_TEMPLATES[template_id].dict()


@router.post("/preview", response_model=TransformResponse)
async def preview_transform(request: TransformRequest):
    """
    Preview transformation without executing/sending to destination
    Use this to test and verify transformation output before deployment
    """
    try:
        start_time = datetime.utcnow()
        warnings = []

        if request.target_format == "sap_xml":
            output = salesforce_to_sap_xml(
                request.source_data,
                mapping=request.field_mapping,
                include_metadata=request.include_metadata
            )
        elif request.target_format == "sap_idoc":
            output = salesforce_to_sap_idoc(
                request.source_data,
                idoc_type=request.idoc_type or "SRCLST",
                mapping=request.field_mapping
            )
        elif request.target_format == "electricity_load_request":
            output = salesforce_case_to_electricity_load_request(
                request.source_data,
                mapping=request.field_mapping
            )
        elif request.target_format == "generic_xml":
            output = json_to_xml(request.source_data, "DATA")
        else:
            raise HTTPException(status_code=400, detail=f"Unknown format: {request.target_format}")

        # Check for potential issues
        if not request.source_data.get("caseId") and not request.source_data.get("id"):
            warnings.append("No caseId or id field found - SAP may require unique identifier")
        if not request.source_data.get("account"):
            warnings.append("No account data - SAP partner information may be incomplete")

        return TransformResponse(
            success=True,
            output=output,
            format=request.target_format,
            source_records=1,
            transform_time=datetime.utcnow().isoformat() + "Z",
            warnings=warnings
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transform failed: {str(e)}")


@router.post("/execute", response_model=TransformResponse)
async def execute_transform(
    request: TransformRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Execute transformation and log the operation
    """
    try:
        start_time = datetime.utcnow()
        warnings = []

        if request.target_format == "sap_xml":
            output = salesforce_to_sap_xml(
                request.source_data,
                mapping=request.field_mapping,
                include_metadata=request.include_metadata
            )
        elif request.target_format == "sap_idoc":
            output = salesforce_to_sap_idoc(
                request.source_data,
                idoc_type=request.idoc_type or "SRCLST",
                mapping=request.field_mapping
            )
        elif request.target_format == "electricity_load_request":
            output = salesforce_case_to_electricity_load_request(
                request.source_data,
                mapping=request.field_mapping
            )
        elif request.target_format == "generic_xml":
            output = json_to_xml(request.source_data, "DATA")
        else:
            raise HTTPException(status_code=400, detail=f"Unknown format: {request.target_format}")

        return TransformResponse(
            success=True,
            output=output,
            format=request.target_format,
            source_records=1,
            transform_time=datetime.utcnow().isoformat() + "Z",
            warnings=warnings
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transform failed: {str(e)}")


@router.post("/salesforce-case/{case_id}/to-sap-xml")
async def transform_salesforce_case_to_sap(
    case_id: int,
    idoc_type: str = Query("SRCLST", description="SAP IDoc type"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Transform a synced Salesforce case to SAP XML format
    """
    case = db.query(SalesforceCase).filter(SalesforceCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # Build source data from case
    source_data = {
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
        "lastModifiedDate": case.last_modified_date.isoformat() + "Z" if case.last_modified_date else None
    }

    # Transform to SAP IDoc
    xml_output = salesforce_to_sap_idoc(source_data, idoc_type=idoc_type)

    return {
        "success": True,
        "case_id": case_id,
        "salesforce_id": case.salesforce_id,
        "idoc_type": idoc_type,
        "xml": xml_output,
        "transform_time": datetime.utcnow().isoformat() + "Z"
    }


@router.post("/salesforce-event/to-sap-xml")
async def transform_salesforce_event_to_sap(
    event_data: Dict[str, Any],
    idoc_type: str = Query("SRCLST", description="SAP IDoc type"),
    template_id: Optional[str] = Query(None, description="Transform template ID")
):
    """
    Transform Salesforce Platform Event data to SAP XML
    This endpoint can be called directly from integration flows
    """
    # If template specified, use its mapping
    field_mapping = None
    if template_id and template_id in TRANSFORM_TEMPLATES:
        template = TRANSFORM_TEMPLATES[template_id]
        field_mapping = template.field_mapping
        idoc_type = template.idoc_type or idoc_type

    # Extract data from platform event format if needed
    source_data = event_data
    if "data" in event_data and "eventType" in event_data:
        # This is platform event format
        source_data = event_data["data"]

    # Transform to SAP IDoc
    xml_output = salesforce_to_sap_idoc(source_data, idoc_type=idoc_type, mapping=field_mapping)

    return {
        "success": True,
        "idoc_type": idoc_type,
        "template_used": template_id,
        "xml": xml_output,
        "transform_time": datetime.utcnow().isoformat() + "Z",
        "source_event_type": event_data.get("eventType", "Unknown")
    }


@router.post("/batch")
async def batch_transform(
    records: List[Dict[str, Any]],
    target_format: str = Query("sap_idoc"),
    idoc_type: str = Query("SRCLST"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Transform multiple records in batch
    """
    results = []
    errors = []

    for i, record in enumerate(records):
        try:
            if target_format == "sap_idoc":
                xml = salesforce_to_sap_idoc(record, idoc_type=idoc_type)
            else:
                xml = salesforce_to_sap_xml(record)

            results.append({
                "index": i,
                "success": True,
                "xml": xml
            })
        except Exception as e:
            errors.append({
                "index": i,
                "error": str(e)
            })

    return {
        "total": len(records),
        "success_count": len(results),
        "error_count": len(errors),
        "results": results,
        "errors": errors,
        "transform_time": datetime.utcnow().isoformat() + "Z"
    }


@router.get("/field-mappings")
async def get_field_mappings():
    """
    Get available field mappings for Salesforce to SAP transformation
    """
    return {
        "salesforce_fields": [
            {"field": "caseId", "description": "Salesforce Case ID", "type": "string"},
            {"field": "caseNumber", "description": "Case Number", "type": "string"},
            {"field": "subject", "description": "Case Subject", "type": "string"},
            {"field": "description", "description": "Case Description", "type": "text"},
            {"field": "status", "description": "Case Status", "type": "picklist"},
            {"field": "priority", "description": "Case Priority", "type": "picklist"},
            {"field": "origin", "description": "Case Origin Channel", "type": "picklist"},
            {"field": "account.id", "description": "Account ID", "type": "string"},
            {"field": "account.name", "description": "Account Name", "type": "string"},
            {"field": "contact.id", "description": "Contact ID", "type": "string"},
            {"field": "contact.name", "description": "Contact Name", "type": "string"},
            {"field": "owner.id", "description": "Owner ID", "type": "string"},
            {"field": "owner.name", "description": "Owner Name", "type": "string"},
            {"field": "createdDate", "description": "Created Date", "type": "datetime"},
            {"field": "lastModifiedDate", "description": "Last Modified Date", "type": "datetime"}
        ],
        "sap_fields": [
            {"field": "OBJECT_ID", "description": "SAP Object ID", "type": "string"},
            {"field": "EXT_REF_NO", "description": "External Reference Number", "type": "string"},
            {"field": "DESCRIPTION", "description": "Description (40 chars)", "type": "string"},
            {"field": "LONG_TEXT", "description": "Long Text", "type": "text"},
            {"field": "STAT_ORDERSTATUS", "description": "Status Code", "type": "string"},
            {"field": "PRIORITY", "description": "Priority (1-4)", "type": "string"},
            {"field": "CUSTOMER_ID", "description": "Customer/Partner ID", "type": "string"},
            {"field": "CUSTOMER_NAME", "description": "Customer Name", "type": "string"},
            {"field": "CONTACT_ID", "description": "Contact Person ID", "type": "string"},
            {"field": "CONTACT_NAME", "description": "Contact Person Name", "type": "string"},
            {"field": "CREATED_AT", "description": "Creation Timestamp", "type": "timestamp"},
            {"field": "CHANGED_AT", "description": "Change Timestamp", "type": "timestamp"}
        ],
        "status_mapping": {
            "New": "E0001",
            "Working": "E0002",
            "Escalated": "E0003",
            "On Hold": "E0004",
            "Closed": "E0005"
        },
        "priority_mapping": {
            "Critical": "1",
            "High": "2",
            "Medium": "3",
            "Low": "4"
        }
    }
