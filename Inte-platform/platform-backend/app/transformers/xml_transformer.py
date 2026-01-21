"""
XML Transformer Module for MuleSoft Integration Platform
Converts JSON data (e.g., Salesforce events) to SAP-compatible XML/IDoc formats
"""

import xml.etree.ElementTree as ET
from xml.dom import minidom
from typing import Dict, Any, List, Optional
from datetime import datetime
import re

# SAP IDoc Templates for different message types
SAP_IDOC_TEMPLATES = {
    "DEBMAS": {
        "name": "Customer Master Data",
        "description": "SAP IDoc for customer master data synchronization",
        "segments": ["E1KNA1M", "E1KNA11", "E1KNVVM"]
    },
    "ORDERS": {
        "name": "Sales Order",
        "description": "SAP IDoc for sales order creation",
        "segments": ["E1EDK01", "E1EDK14", "E1EDP01"]
    },
    "SRCLST": {
        "name": "Service Request",
        "description": "SAP IDoc for service/case creation from Salesforce",
        "segments": ["E1BPSDHD1", "E1BPSDTEXT", "E1BPSDPARTY"]
    },
    "MATMAS": {
        "name": "Material Master",
        "description": "SAP IDoc for material master data",
        "segments": ["E1MARAM", "E1MAKTM", "E1MARCM"]
    },
    "CRMXIF_ORDER": {
        "name": "CRM Order",
        "description": "SAP CRM Order IDoc for case/ticket sync",
        "segments": ["E1CRMORDER", "E1CRMORDERHEADER", "E1CRMORDERITEM"]
    }
}

# Default field mappings from Salesforce to SAP
DEFAULT_SF_TO_SAP_MAPPING = {
    "caseId": "OBJECT_ID",
    "caseNumber": "EXT_REF_NO",
    "subject": "DESCRIPTION",
    "description": "LONG_TEXT",
    "status": "STAT_ORDERSTATUS",
    "priority": "PRIORITY",
    "origin": "CHANNEL",
    "account.id": "CUSTOMER_ID",
    "account.name": "CUSTOMER_NAME",
    "contact.id": "CONTACT_ID",
    "contact.name": "CONTACT_NAME",
    "owner.id": "RESPONSIBLE_ID",
    "owner.name": "RESPONSIBLE_NAME",
    "createdDate": "CREATED_AT",
    "lastModifiedDate": "CHANGED_AT"
}

# SAP Status mapping from Salesforce status
SF_TO_SAP_STATUS_MAP = {
    "New": "E0001",
    "Working": "E0002",
    "Escalated": "E0003",
    "On Hold": "E0004",
    "Closed": "E0005",
    "Resolved": "E0005"
}

# SAP Priority mapping from Salesforce priority
SF_TO_SAP_PRIORITY_MAP = {
    "Critical": "1",
    "High": "2",
    "Medium": "3",
    "Low": "4"
}


def prettify_xml(elem: ET.Element) -> str:
    """Return a pretty-printed XML string for the Element."""
    rough_string = ET.tostring(elem, encoding='unicode')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ")


def get_nested_value(data: Dict, path: str) -> Any:
    """Get nested value from dict using dot notation (e.g., 'account.name')"""
    keys = path.split('.')
    value = data
    for key in keys:
        if isinstance(value, dict):
            value = value.get(key)
        else:
            return None
    return value


def format_sap_date(iso_date: str) -> str:
    """Convert ISO date to SAP format (YYYYMMDD)"""
    if not iso_date:
        return ""
    try:
        # Handle various ISO formats
        date_str = iso_date.replace('Z', '+00:00')
        if 'T' in date_str:
            dt = datetime.fromisoformat(date_str.split('+')[0])
        else:
            dt = datetime.fromisoformat(date_str)
        return dt.strftime('%Y%m%d')
    except:
        return ""


def format_sap_timestamp(iso_date: str) -> str:
    """Convert ISO date to SAP timestamp format (YYYYMMDDHHmmss)"""
    if not iso_date:
        return ""
    try:
        date_str = iso_date.replace('Z', '+00:00')
        if 'T' in date_str:
            dt = datetime.fromisoformat(date_str.split('+')[0])
        else:
            dt = datetime.fromisoformat(date_str)
        return dt.strftime('%Y%m%d%H%M%S')
    except:
        return ""


def json_to_xml(data: Dict[str, Any], root_name: str = "root") -> str:
    """
    Generic JSON to XML converter
    """
    def dict_to_xml(d: Any, parent: ET.Element):
        if isinstance(d, dict):
            for key, value in d.items():
                # Clean key for valid XML element name
                clean_key = re.sub(r'[^a-zA-Z0-9_]', '_', str(key))
                if clean_key[0].isdigit():
                    clean_key = '_' + clean_key
                child = ET.SubElement(parent, clean_key)
                dict_to_xml(value, child)
        elif isinstance(d, list):
            for i, item in enumerate(d):
                item_elem = ET.SubElement(parent, "item")
                dict_to_xml(item, item_elem)
        else:
            parent.text = str(d) if d is not None else ""

    root = ET.Element(root_name)
    dict_to_xml(data, root)
    return prettify_xml(root)


def salesforce_to_sap_xml(
    sf_data: Dict[str, Any],
    mapping: Optional[Dict[str, str]] = None,
    include_metadata: bool = True
) -> str:
    """
    Convert Salesforce case/event data to SAP-compatible XML format

    Args:
        sf_data: Salesforce case data (JSON/dict format)
        mapping: Custom field mapping (Salesforce field -> SAP field)
        include_metadata: Include transformation metadata in output

    Returns:
        SAP-compatible XML string
    """
    field_mapping = mapping or DEFAULT_SF_TO_SAP_MAPPING

    # Create root element
    root = ET.Element("SAP_SERVICE_REQUEST")
    root.set("xmlns", "urn:sap-com:document:sap:rfc:functions")

    # Add header
    header = ET.SubElement(root, "HEADER")
    ET.SubElement(header, "MESSAGE_TYPE").text = "SRCLST"
    ET.SubElement(header, "SENDER").text = "SALESFORCE"
    ET.SubElement(header, "RECEIVER").text = "SAP"
    ET.SubElement(header, "CREATED_AT").text = datetime.utcnow().strftime('%Y%m%d%H%M%S')

    # Add request data
    request = ET.SubElement(root, "SERVICE_REQUEST")

    # Map fields
    for sf_field, sap_field in field_mapping.items():
        value = get_nested_value(sf_data, sf_field)
        if value is not None:
            # Apply status/priority transformations
            if sf_field == "status" and value in SF_TO_SAP_STATUS_MAP:
                value = SF_TO_SAP_STATUS_MAP[value]
            elif sf_field == "priority" and value in SF_TO_SAP_PRIORITY_MAP:
                value = SF_TO_SAP_PRIORITY_MAP[value]
            elif "date" in sf_field.lower() or "Date" in sf_field:
                value = format_sap_timestamp(str(value))

            elem = ET.SubElement(request, sap_field)
            elem.text = str(value) if value else ""

    # Add account info if present
    if sf_data.get("account"):
        partner = ET.SubElement(root, "PARTNER")
        ET.SubElement(partner, "PARTNER_FUNCTION").text = "AG"  # Sold-to party
        ET.SubElement(partner, "PARTNER_NUMBER").text = str(sf_data["account"].get("id", ""))
        ET.SubElement(partner, "PARTNER_NAME").text = str(sf_data["account"].get("name", ""))

    # Add contact info if present
    if sf_data.get("contact"):
        contact = ET.SubElement(root, "CONTACT")
        ET.SubElement(contact, "CONTACT_ID").text = str(sf_data["contact"].get("id", ""))
        ET.SubElement(contact, "CONTACT_NAME").text = str(sf_data["contact"].get("name", ""))

    # Add metadata
    if include_metadata:
        metadata = ET.SubElement(root, "METADATA")
        ET.SubElement(metadata, "SOURCE_SYSTEM").text = "Salesforce"
        ET.SubElement(metadata, "TRANSFORM_TIME").text = datetime.utcnow().isoformat() + "Z"
        ET.SubElement(metadata, "TRANSFORM_VERSION").text = "1.0"
        ET.SubElement(metadata, "PLATFORM").text = "MuleSoft Integration Platform"

    return prettify_xml(root)


def salesforce_to_sap_idoc(
    sf_data: Dict[str, Any],
    idoc_type: str = "SRCLST",
    mapping: Optional[Dict[str, str]] = None
) -> str:
    """
    Convert Salesforce case data to SAP IDoc XML format

    Args:
        sf_data: Salesforce case data
        idoc_type: SAP IDoc type (DEBMAS, ORDERS, SRCLST, etc.)
        mapping: Custom field mapping

    Returns:
        SAP IDoc XML string
    """
    field_mapping = mapping or DEFAULT_SF_TO_SAP_MAPPING
    template = SAP_IDOC_TEMPLATES.get(idoc_type, SAP_IDOC_TEMPLATES["SRCLST"])

    # Create IDoc structure
    root = ET.Element("IDOC")
    root.set("BEGIN", "1")

    # EDI_DC40 - Control record
    edi_dc = ET.SubElement(root, "EDI_DC40")
    edi_dc.set("SEGMENT", "1")
    ET.SubElement(edi_dc, "TABNAM").text = "EDI_DC40"
    ET.SubElement(edi_dc, "MANDT").text = "100"
    ET.SubElement(edi_dc, "DOCNUM").text = str(sf_data.get("caseId", ""))[:16]
    ET.SubElement(edi_dc, "IDOCTYP").text = idoc_type
    ET.SubElement(edi_dc, "MESTYP").text = idoc_type
    ET.SubElement(edi_dc, "SNDPOR").text = "SALESFORCE"
    ET.SubElement(edi_dc, "SNDPRT").text = "LS"
    ET.SubElement(edi_dc, "SNDPRN").text = "SFDC_SYSTEM"
    ET.SubElement(edi_dc, "RCVPOR").text = "SAP"
    ET.SubElement(edi_dc, "RCVPRT").text = "LS"
    ET.SubElement(edi_dc, "RCVPRN").text = "SAP_SYSTEM"
    ET.SubElement(edi_dc, "CREDAT").text = format_sap_date(sf_data.get("createdDate", datetime.utcnow().isoformat()))
    ET.SubElement(edi_dc, "CRETIM").text = datetime.utcnow().strftime('%H%M%S')

    # Data segments based on IDoc type
    if idoc_type == "SRCLST" or idoc_type == "CRMXIF_ORDER":
        # Service Request / CRM Order header
        header_seg = ET.SubElement(root, "E1BPSDHD1")
        header_seg.set("SEGMENT", "1")

        ET.SubElement(header_seg, "OBJECT_ID").text = str(sf_data.get("caseId", ""))
        ET.SubElement(header_seg, "OBJECT_TYPE").text = "BUS2000223"  # Service Request
        ET.SubElement(header_seg, "DESCRIPTION").text = str(sf_data.get("subject", ""))[:40]
        ET.SubElement(header_seg, "PROCESS_TYPE").text = "SRVO"  # Service Order

        # Map status
        status = sf_data.get("status", "New")
        ET.SubElement(header_seg, "STAT_ORDERSTATUS").text = SF_TO_SAP_STATUS_MAP.get(status, "E0001")

        # Map priority
        priority = sf_data.get("priority", "Medium")
        ET.SubElement(header_seg, "PRIORITY").text = SF_TO_SAP_PRIORITY_MAP.get(priority, "3")

        ET.SubElement(header_seg, "CREATED_AT").text = format_sap_timestamp(sf_data.get("createdDate", ""))
        ET.SubElement(header_seg, "CHANGED_AT").text = format_sap_timestamp(sf_data.get("lastModifiedDate", ""))

        # Text segment for description
        text_seg = ET.SubElement(root, "E1BPSDTEXT")
        text_seg.set("SEGMENT", "1")
        ET.SubElement(text_seg, "TEXT_ID").text = "S001"
        ET.SubElement(text_seg, "TEXT_LINE").text = str(sf_data.get("description", ""))[:132]
        ET.SubElement(text_seg, "LANGU").text = "E"

        # Partner segment for account
        if sf_data.get("account"):
            party_seg = ET.SubElement(root, "E1BPSDPARTY")
            party_seg.set("SEGMENT", "1")
            ET.SubElement(party_seg, "PARTNER_FCT").text = "00000001"  # Sold-to
            ET.SubElement(party_seg, "PARTNER_NO").text = str(sf_data["account"].get("id", ""))[:10]
            ET.SubElement(party_seg, "PARTNER_NAME").text = str(sf_data["account"].get("name", ""))[:40]

        # Contact segment
        if sf_data.get("contact"):
            contact_seg = ET.SubElement(root, "E1BPSDPARTY")
            contact_seg.set("SEGMENT", "1")
            ET.SubElement(contact_seg, "PARTNER_FCT").text = "00000014"  # Contact
            ET.SubElement(contact_seg, "PARTNER_NO").text = str(sf_data["contact"].get("id", ""))[:10]
            ET.SubElement(contact_seg, "PARTNER_NAME").text = str(sf_data["contact"].get("name", ""))[:40]

        # Responsible party segment
        if sf_data.get("owner"):
            owner_seg = ET.SubElement(root, "E1BPSDPARTY")
            owner_seg.set("SEGMENT", "1")
            ET.SubElement(owner_seg, "PARTNER_FCT").text = "00000015"  # Responsible
            ET.SubElement(owner_seg, "PARTNER_NO").text = str(sf_data["owner"].get("id", ""))[:10]
            ET.SubElement(owner_seg, "PARTNER_NAME").text = str(sf_data["owner"].get("name", ""))[:40]

    elif idoc_type == "DEBMAS":
        # Customer master data
        e1kna1m = ET.SubElement(root, "E1KNA1M")
        e1kna1m.set("SEGMENT", "1")

        if sf_data.get("account"):
            ET.SubElement(e1kna1m, "KUNNR").text = str(sf_data["account"].get("id", ""))[:10]
            ET.SubElement(e1kna1m, "NAME1").text = str(sf_data["account"].get("name", ""))[:35]

    elif idoc_type == "ORDERS":
        # Sales order
        e1edk01 = ET.SubElement(root, "E1EDK01")
        e1edk01.set("SEGMENT", "1")

        ET.SubElement(e1edk01, "BELNR").text = str(sf_data.get("caseNumber", ""))[:35]
        ET.SubElement(e1edk01, "BSART").text = "ZORD"  # Order type
        ET.SubElement(e1edk01, "CURCY").text = "USD"

    return prettify_xml(root)


def transform_with_mapping(
    source_data: Dict[str, Any],
    field_mapping: Dict[str, str],
    output_format: str = "xml",
    root_element: str = "DATA"
) -> str:
    """
    Transform data using custom field mapping

    Args:
        source_data: Source data dictionary
        field_mapping: Dict mapping source fields to target fields
        output_format: Output format ('xml' or 'json')
        root_element: Root XML element name

    Returns:
        Transformed data as XML string or JSON string
    """
    transformed = {}

    for source_field, target_field in field_mapping.items():
        value = get_nested_value(source_data, source_field)
        if value is not None:
            transformed[target_field] = value

    if output_format == "xml":
        return json_to_xml(transformed, root_element)
    else:
        import json
        return json.dumps(transformed, indent=2, default=str)


def salesforce_case_to_electricity_load_request(
    sf_data: Dict[str, Any],
    mapping: Optional[Dict[str, str]] = None
) -> str:
    """
    Convert Salesforce Case data to SAP ElectricityLoadRequest XML format
    This is the format expected by SAP at /api/integration/mulesoft/load-request/xml

    Args:
        sf_data: Salesforce case data
        mapping: Optional custom field mapping

    Returns:
        ElectricityLoadRequest XML string
    """
    # Default mapping from Salesforce case to Electricity Load Request
    default_mapping = {
        "caseId": "RequestID",
        "account.id": "CustomerID",
        "currentLoad": "CurrentLoad",
        "requestedLoad": "RequestedLoad",
        "connectionType": "ConnectionType",
        "city": "City",
        "pinCode": "PinCode"
    }

    field_mapping = mapping or default_mapping

    # Create root element
    root = ET.Element("ElectricityLoadRequest")

    # Extract or generate RequestID
    request_id = sf_data.get("caseId") or sf_data.get("caseNumber") or sf_data.get("id") or f"SF-REQ-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    if not request_id.startswith("SF-"):
        request_id = f"SF-{request_id}"
    ET.SubElement(root, "RequestID").text = str(request_id)

    # Extract CustomerID from account or generate
    customer_id = None
    if sf_data.get("account"):
        customer_id = sf_data["account"].get("id") or sf_data["account"].get("name")
    customer_id = customer_id or sf_data.get("customerId") or sf_data.get("contact", {}).get("id") or "CUST-DEFAULT"
    if not customer_id.startswith("CUST-"):
        customer_id = f"CUST-{customer_id}"
    ET.SubElement(root, "CustomerID").text = str(customer_id)

    # Extract load values (use defaults if not present)
    current_load = sf_data.get("currentLoad") or sf_data.get("current_load") or "5"
    requested_load = sf_data.get("requestedLoad") or sf_data.get("requested_load") or "10"
    ET.SubElement(root, "CurrentLoad").text = str(current_load)
    ET.SubElement(root, "RequestedLoad").text = str(requested_load)

    # Connection type based on priority or explicit field
    connection_type = sf_data.get("connectionType") or sf_data.get("connection_type")
    if not connection_type:
        # Map from priority
        priority = sf_data.get("priority", "").upper()
        if priority in ["CRITICAL", "HIGH"]:
            connection_type = "COMMERCIAL"
        else:
            connection_type = "RESIDENTIAL"
    ET.SubElement(root, "ConnectionType").text = connection_type.upper()

    # Location info
    city = sf_data.get("city") or sf_data.get("location") or "Hyderabad"
    pin_code = sf_data.get("pinCode") or sf_data.get("pin_code") or sf_data.get("postalCode") or "500001"
    ET.SubElement(root, "City").text = str(city)
    ET.SubElement(root, "PinCode").text = str(pin_code)

    return prettify_xml(root)


def salesforce_case_to_sap_webhook(sf_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert Salesforce Case to SAP Webhook JSON format

    Args:
        sf_data: Salesforce case data

    Returns:
        Webhook payload dict
    """
    return {
        "event_type": "CASE_CREATED",
        "entity_type": "case",
        "entity_id": sf_data.get("caseId") or sf_data.get("id") or "SF-CASE-001",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "data": {
            "subject": sf_data.get("subject"),
            "description": sf_data.get("description"),
            "status": sf_data.get("status"),
            "priority": sf_data.get("priority"),
            "account": sf_data.get("account"),
            "contact": sf_data.get("contact"),
            "origin": sf_data.get("origin")
        }
    }


def create_sap_envelope(xml_content: str, sap_config: Optional[Dict] = None) -> str:
    """
    Wrap XML content in SAP RFC envelope for BAPI/RFC calls

    Args:
        xml_content: Inner XML content
        sap_config: SAP connection configuration

    Returns:
        Complete SAP RFC envelope XML
    """
    config = sap_config or {}

    envelope = ET.Element("asx:abap")
    envelope.set("xmlns:asx", "http://www.sap.com/abapxml")
    envelope.set("version", "1.0")

    values = ET.SubElement(envelope, "asx:values")

    # Parse and insert the content
    try:
        content_elem = ET.fromstring(xml_content.encode('utf-8'))
        values.append(content_elem)
    except ET.ParseError:
        # If parsing fails, wrap as CDATA
        data = ET.SubElement(values, "DATA")
        data.text = xml_content

    return prettify_xml(envelope)
