# Electricity Load Request Integration API

## Overview

This integration system transforms JSON electricity load increase requests into XML format and sends them to SAP ERP for processing.

## Architecture Flow

```
Client (JSON) → Integration Engine (Transform) → SAP ERP (XML) → Response (XML)
```

---

## 🔵 REQUEST ENDPOINT

### POST Integration Engine - Submit Electricity Load Request

**URL:** `http://localhost:8081/camel/api/electricity-load-request`

**Method:** `POST`

**Content-Type:** `application/json`

**Request Body (JSON):**

```json
{
  "requestId": "SF-REQ-10021",
  "customerId": "CUST-88991",
  "serviceType": "ELECTRICITY_LOAD_INCREASE",
  "currentLoadKW": 5,
  "requestedLoadKW": 10,
  "propertyType": "RESIDENTIAL",
  "address": {
    "city": "Hyderabad",
    "pinCode": "500081"
  }
}
```

**Field Descriptions:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `requestId` | string | Yes | Unique request identifier from source system |
| `customerId` | string | Yes | Customer ID in the system |
| `serviceType` | string | Yes | Type of service (e.g., ELECTRICITY_LOAD_INCREASE) |
| `currentLoadKW` | integer | Yes | Current electricity load in kilowatts |
| `requestedLoadKW` | integer | Yes | Requested new load in kilowatts |
| `propertyType` | string | Yes | Property type (RESIDENTIAL, COMMERCIAL, INDUSTRIAL) |
| `address.city` | string | Yes | City name |
| `address.pinCode` | string | Yes | Postal/PIN code |

---

## 🔄 TRANSFORMATION

The integration engine automatically transforms the JSON to XML format:

**Transformed XML (sent to SAP):**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<ElectricityLoadRequest>
  <RequestID>SF-REQ-10021</RequestID>
  <CustomerID>CUST-88991</CustomerID>
  <CurrentLoad>5</CurrentLoad>
  <RequestedLoad>10</RequestedLoad>
  <ConnectionType>RESIDENTIAL</ConnectionType>
  <City>Hyderabad</City>
  <PinCode>500081</PinCode>
</ElectricityLoadRequest>
```

**Field Mapping:**

| JSON Field | XML Field |
|------------|-----------|
| `requestId` | `<RequestID>` |
| `customerId` | `<CustomerID>` |
| `currentLoadKW` | `<CurrentLoad>` |
| `requestedLoadKW` | `<RequestedLoad>` |
| `propertyType` | `<ConnectionType>` |
| `address.city` | `<City>` |
| `address.pinCode` | `<PinCode>` |

---

## 🟢 RESPONSE FROM SAP ERP

**Content-Type:** `application/xml`

**Success Response (HTTP 201):**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<ElectricityLoadResponse>
  <Status>SUCCESS</Status>
  <Message>Electricity load request received successfully</Message>
  <RequestID>SF-REQ-10021</RequestID>
  <SAPOrderID>SAP-EL-000001</SAPOrderID>
  <ProcessingTime>2024-01-20T10:30:00Z</ProcessingTime>
  <EstimatedCompletionDays>7</EstimatedCompletionDays>
  <ApprovalRequired>true</ApprovalRequired>
  <TechnicalFeasibility>PENDING_REVIEW</TechnicalFeasibility>
</ElectricityLoadResponse>
```

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `Status` | string | SUCCESS or FAILURE |
| `Message` | string | Human-readable status message |
| `RequestID` | string | Original request ID from source system |
| `SAPOrderID` | string | SAP-generated order ID for tracking |
| `ProcessingTime` | datetime | When SAP processed the request |
| `EstimatedCompletionDays` | integer | Estimated days to complete |
| `ApprovalRequired` | boolean | Whether approval is needed |
| `TechnicalFeasibility` | string | Feasibility status (PENDING_REVIEW, APPROVED, REJECTED) |

**Error Response (HTTP 400):**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<ElectricityLoadResponse>
  <Status>FAILURE</Status>
  <Message>Invalid XML format: missing required field</Message>
  <ErrorCode>ERR_INVALID_REQUEST</ErrorCode>
</ElectricityLoadResponse>
```

---

## 📋 ADDITIONAL SAP ERP ENDPOINTS

### 1. Get Request Status

**URL:** `http://localhost:8094/api/electricity-load-request/{requestId}`

**Method:** `GET`

**Example:**
```bash
curl http://localhost:8094/api/electricity-load-request/SF-REQ-10021
```

**Response (JSON):**
```json
{
  "request_id": "SF-REQ-10021",
  "customer_id": "CUST-88991",
  "current_load": 5,
  "requested_load": 10,
  "connection_type": "RESIDENTIAL",
  "city": "Hyderabad",
  "pin_code": "500081",
  "received_at": "2024-01-20T10:30:00Z",
  "status": "RECEIVED",
  "sap_order_id": "SAP-EL-000001"
}
```

### 2. List All Requests

**URL:** `http://localhost:8094/api/electricity-load-requests`

**Method:** `GET`

**Query Parameters:**
- `status` (optional): Filter by status (RECEIVED, PROCESSING, APPROVED, REJECTED)
- `city` (optional): Filter by city name

**Example:**
```bash
curl "http://localhost:8094/api/electricity-load-requests?city=Hyderabad&status=RECEIVED"
```

**Response (JSON):**
```json
{
  "requests": [
    {
      "request_id": "SF-REQ-10021",
      "customer_id": "CUST-88991",
      "current_load": 5,
      "requested_load": 10,
      "connection_type": "RESIDENTIAL",
      "city": "Hyderabad",
      "pin_code": "500081",
      "received_at": "2024-01-20T10:30:00Z",
      "status": "RECEIVED",
      "sap_order_id": "SAP-EL-000001"
    }
  ],
  "total": 1,
  "pagination": {
    "page": 1,
    "total_pages": 1,
    "total_records": 1
  }
}
```

---

## 🧪 TESTING

### Using cURL

**1. Submit a request:**

```bash
curl -X POST http://localhost:8081/camel/api/electricity-load-request \
  -H "Content-Type: application/json" \
  -d '{
    "requestId": "SF-REQ-10021",
    "customerId": "CUST-88991",
    "serviceType": "ELECTRICITY_LOAD_INCREASE",
    "currentLoadKW": 5,
    "requestedLoadKW": 10,
    "propertyType": "RESIDENTIAL",
    "address": {
      "city": "Hyderabad",
      "pinCode": "500081"
    }
  }'
```

**2. Check request status:**

```bash
curl http://localhost:8094/api/electricity-load-request/SF-REQ-10021
```

**3. List all requests:**

```bash
curl http://localhost:8094/api/electricity-load-requests
```

### Using Postman

1. **Create a new POST request**
   - URL: `http://localhost:8081/camel/api/electricity-load-request`
   - Headers: `Content-Type: application/json`
   - Body: Raw JSON (see example above)

2. **Send the request**
   - You should receive an XML response from SAP

3. **Verify in SAP**
   - GET: `http://localhost:8094/api/electricity-load-requests`

### Using Python

```python
import requests
import json

# Submit request
url = "http://localhost:8081/camel/api/electricity-load-request"
payload = {
    "requestId": "SF-REQ-10021",
    "customerId": "CUST-88991",
    "serviceType": "ELECTRICITY_LOAD_INCREASE",
    "currentLoadKW": 5,
    "requestedLoadKW": 10,
    "propertyType": "RESIDENTIAL",
    "address": {
        "city": "Hyderabad",
        "pinCode": "500081"
    }
}

response = requests.post(url, json=payload)
print(f"Status: {response.status_code}")
print(f"Response: {response.text}")

# Check status
status_url = f"http://localhost:8094/api/electricity-load-request/SF-REQ-10021"
status_response = requests.get(status_url)
print(f"Status: {status_response.json()}")
```

---

## 🔍 MONITORING & LOGS

### Integration Engine Logs

```bash
docker-compose logs -f integration-engine
```

**Expected log output:**
```
Received electricity load request: {"requestId":"SF-REQ-10021",...}
Transformed to XML: <?xml version="1.0"...
SAP Response: <?xml version="1.0"...
```

### SAP ERP Logs

```bash
docker-compose logs -f sap-erp-service
```

### Health Check

```bash
curl http://localhost:8081/camel/api/health
```

**Response:**
```json
{
  "status": "healthy",
  "engine": "camel-4.2.0",
  "features": ["json-to-xml", "electricity-load-integration"]
}
```

---

## 🚀 DEPLOYMENT

### Start the Services

```bash
cd Inte-platform/deployments
docker-compose up --build
```

### Verify Services are Running

```bash
# Check integration engine
curl http://localhost:8081/camel/api/health

# Check SAP ERP service
curl http://localhost:8094/api/system/health
```

### Stop the Services

```bash
docker-compose down
```

---

## ⚠️ ERROR HANDLING

### Common Errors

**1. Invalid JSON Format**
- **Status:** 400 Bad Request
- **Solution:** Verify JSON structure matches the schema

**2. Missing Required Fields**
- **Status:** 400 Bad Request
- **Solution:** Ensure all required fields are present

**3. SAP Service Unavailable**
- **Status:** 500 Internal Server Error
- **Solution:** Check if SAP ERP service is running

**4. XML Parsing Error**
- **Status:** 400 Bad Request
- **Solution:** Check transformation logic in ElectricityLoadTransformer

---

## 📊 SERVICE PORTS

| Service | Port | URL |
|---------|------|-----|
| Integration Engine | 8081 | http://localhost:8081/camel/api/electricity-load-request |
| SAP ERP Service | 8094 | http://localhost:8094/api/electricity-load-request |
| Platform Backend | 8080 | http://localhost:8080 |
| UI Dashboard | 3000 | http://localhost:3000 |

---

## 🔐 AUTHENTICATION

Currently, the electricity load request endpoint does not require authentication for testing purposes. 

For production deployment, add authentication by:
1. Implementing JWT token validation in the integration engine
2. Adding API key validation in SAP ERP service
3. Using Kong API Gateway for centralized authentication

---

## 📝 NOTES

- The integration engine automatically handles JSON-to-XML transformation
- All requests are logged for audit purposes
- SAP ERP stores all requests in memory (resets on restart)
- Response times are typically under 500ms
- The system supports concurrent requests

---

## 🆘 SUPPORT

For issues or questions:
1. Check the logs: `docker-compose logs -f integration-engine sap-erp-service`
2. Verify services are running: `docker-compose ps`
3. Test connectivity: `curl http://localhost:8081/camel/api/health`

---

**Last Updated:** January 20, 2026
**Version:** 1.0.0
