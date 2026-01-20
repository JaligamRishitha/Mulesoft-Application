# ⚡ Electricity Load Request - Visual API Guide

## 🎯 Complete Integration Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         ELECTRICITY LOAD REQUEST FLOW                    │
└─────────────────────────────────────────────────────────────────────────┘

Step 1: Client Sends JSON Request
┌──────────────┐
│   Client     │
│  (Postman/   │
│   cURL/App)  │
└──────┬───────┘
       │
       │ POST http://localhost:8081/camel/api/electricity-load-request
       │ Content-Type: application/json
       │
       │ {
       │   "requestId": "SF-REQ-10021",
       │   "customerId": "CUST-88991",
       │   "serviceType": "ELECTRICITY_LOAD_INCREASE",
       │   "currentLoadKW": 5,
       │   "requestedLoadKW": 10,
       │   "propertyType": "RESIDENTIAL",
       │   "address": {
       │     "city": "Hyderabad",
       │     "pinCode": "500081"
       │   }
       │ }
       ▼
┌──────────────────────────────────────────────────────────────┐
│          INTEGRATION ENGINE (Apache Camel)                   │
│                  Port: 8081                                  │
│                                                              │
│  Step 2: Receive JSON                                       │
│  ┌────────────────────────────────────────────────┐         │
│  │ IntegrationRoutes.java                         │         │
│  │ - Endpoint: POST /api/electricity-load-request │         │
│  │ - Accepts: application/json                    │         │
│  └────────────────────────────────────────────────┘         │
│                        ▼                                     │
│  Step 3: Transform JSON → XML                               │
│  ┌────────────────────────────────────────────────┐         │
│  │ ElectricityLoadTransformer.java                │         │
│  │                                                │         │
│  │ Field Mapping:                                 │         │
│  │ • requestId        → <RequestID>               │         │
│  │ • customerId       → <CustomerID>              │         │
│  │ • currentLoadKW    → <CurrentLoad>             │         │
│  │ • requestedLoadKW  → <RequestedLoad>           │         │
│  │ • propertyType     → <ConnectionType>          │         │
│  │ • address.city     → <City>                    │         │
│  │ • address.pinCode  → <PinCode>                 │         │
│  └────────────────────────────────────────────────┘         │
│                        ▼                                     │
│  Step 4: Generated XML                                      │
│  <?xml version="1.0" encoding="UTF-8"?>                     │
│  <ElectricityLoadRequest>                                   │
│    <RequestID>SF-REQ-10021</RequestID>                      │
│    <CustomerID>CUST-88991</CustomerID>                      │
│    <CurrentLoad>5</CurrentLoad>                             │
│    <RequestedLoad>10</RequestedLoad>                        │
│    <ConnectionType>RESIDENTIAL</ConnectionType>             │
│    <City>Hyderabad</City>                                   │
│    <PinCode>500081</PinCode>                                │
│  </ElectricityLoadRequest>                                  │
└──────────────────────┬───────────────────────────────────────┘
                       │
                       │ POST http://sap-erp-service:8094/api/electricity-load-request
                       │ Content-Type: application/xml
                       ▼
┌──────────────────────────────────────────────────────────────┐
│              SAP ERP SERVICE (FastAPI)                       │
│                    Port: 8094                                │
│                                                              │
│  Step 5: Receive & Parse XML                                │
│  ┌────────────────────────────────────────────────┐         │
│  │ app.py - POST /api/electricity-load-request    │         │
│  │                                                │         │
│  │ • Parse XML using ElementTree                  │         │
│  │ • Extract all fields                           │         │
│  │ • Validate data                                │         │
│  └────────────────────────────────────────────────┘         │
│                        ▼                                     │
│  Step 6: Process & Store                                    │
│  ┌────────────────────────────────────────────────┐         │
│  │ • Generate SAP Order ID: SAP-EL-000001         │         │
│  │ • Set status: RECEIVED                         │         │
│  │ • Store in database                            │         │
│  │ • Calculate processing time                    │         │
│  └────────────────────────────────────────────────┘         │
│                        ▼                                     │
│  Step 7: Generate XML Response                              │
│  <?xml version="1.0" encoding="UTF-8"?>                     │
│  <ElectricityLoadResponse>                                  │
│    <Status>SUCCESS</Status>                                 │
│    <Message>Request received successfully</Message>         │
│    <RequestID>SF-REQ-10021</RequestID>                      │
│    <SAPOrderID>SAP-EL-000001</SAPOrderID>                   │
│    <ProcessingTime>2024-01-20T10:30:00Z</ProcessingTime>   │
│    <EstimatedCompletionDays>7</EstimatedCompletionDays>    │
│    <ApprovalRequired>true</ApprovalRequired>                │
│    <TechnicalFeasibility>PENDING_REVIEW</TechnicalFeasibility>│
│  </ElectricityLoadResponse>                                 │
└──────────────────────┬───────────────────────────────────────┘
                       │
                       │ XML Response
                       ▼
┌──────────────────────────────────────────────────────────────┐
│          INTEGRATION ENGINE (Apache Camel)                   │
│                                                              │
│  Step 8: Forward Response                                   │
│  • Receive XML from SAP                                     │
│  • Log response                                             │
│  • Return to client                                         │
└──────────────────────┬───────────────────────────────────────┘
                       │
                       │ XML Response
                       ▼
┌──────────────┐
│   Client     │
│  Receives    │
│  XML Response│
└──────────────┘
```

---

## 📊 Data Transformation Example

### INPUT (JSON)
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

### ⬇️ TRANSFORMATION ⬇️

```
ElectricityLoadTransformer.java processes:

1. Parse JSON → Java Object (ElectricityLoadRequest)
2. Map fields → SAP format (SAPElectricityLoadRequest)
3. Convert to XML → String with XML declaration
```

### OUTPUT (XML)
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

---

## 🔄 Request/Response Cycle

```
┌─────────┐                                              ┌─────────┐
│ Client  │                                              │   SAP   │
└────┬────┘                                              └────┬────┘
     │                                                        │
     │ 1. POST JSON                                          │
     │────────────────────────────────────────────┐          │
     │                                            │          │
     │                                    ┌───────▼──────┐   │
     │                                    │ Integration  │   │
     │                                    │   Engine     │   │
     │                                    │              │   │
     │                                    │ 2. Transform │   │
     │                                    │   JSON→XML   │   │
     │                                    └───────┬──────┘   │
     │                                            │          │
     │                                            │ 3. POST  │
     │                                            │   XML    │
     │                                            └─────────>│
     │                                                       │
     │                                            4. Process │
     │                                               & Store │
     │                                                       │
     │                                            5. Generate│
     │                                            ┌─ Response│
     │                                            │          │
     │                                    ┌───────▼──────┐   │
     │                                    │ Integration  │   │
     │ 6. Return XML                      │   Engine     │   │
     │<───────────────────────────────────┤              │   │
     │                                    │ Forward XML  │   │
     │                                    └──────────────┘   │
     │                                                       │
```

---

## 🎨 Component Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    INTEGRATION ENGINE                            │
│                                                                  │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────┐  │
│  │     Models       │  │   Processor      │  │    Routes    │  │
│  │                  │  │                  │  │              │  │
│  │ • Electricity    │  │ • Electricity    │  │ • REST       │  │
│  │   LoadRequest    │  │   Load           │  │   Endpoint   │  │
│  │   (JSON)         │  │   Transformer    │  │              │  │
│  │                  │  │                  │  │ • Direct     │  │
│  │ • SAP            │  │ • JSON Parser    │  │   Routes     │  │
│  │   Electricity    │  │                  │  │              │  │
│  │   LoadRequest    │  │ • XML Generator  │  │ • HTTP       │  │
│  │   (XML)          │  │                  │  │   Client     │  │
│  └──────────────────┘  └──────────────────┘  └──────────────┘  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                      SAP ERP SERVICE                             │
│                                                                  │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────┐  │
│  │   Endpoints      │  │   Processing     │  │   Storage    │  │
│  │                  │  │                  │  │              │  │
│  │ • POST /api/     │  │ • XML Parser     │  │ • In-Memory  │  │
│  │   electricity-   │  │                  │  │   Database   │  │
│  │   load-request   │  │ • Validation     │  │              │  │
│  │                  │  │                  │  │ • Request    │  │
│  │ • GET /api/      │  │ • Order ID       │  │   History    │  │
│  │   electricity-   │  │   Generation     │  │              │  │
│  │   load-request/  │  │                  │  │ • Status     │  │
│  │   {id}           │  │ • Response       │  │   Tracking   │  │
│  │                  │  │   Builder        │  │              │  │
│  │ • GET /api/      │  │                  │  │              │  │
│  │   electricity-   │  │                  │  │              │  │
│  │   load-requests  │  │                  │  │              │  │
│  └──────────────────┘  └──────────────────┘  └──────────────┘  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🧪 Testing Scenarios

### Scenario 1: Successful Request
```
Input:  Valid JSON with all required fields
Output: XML response with SUCCESS status and SAP Order ID
```

### Scenario 2: Missing Fields
```
Input:  JSON missing required field (e.g., customerId)
Output: 400 Bad Request error
```

### Scenario 3: Invalid JSON
```
Input:  Malformed JSON
Output: 400 Bad Request - JSON parse error
```

### Scenario 4: SAP Service Down
```
Input:  Valid JSON
Output: 500 Internal Server Error - Connection refused
```

---

## 📈 Monitoring Points

```
┌─────────────────────────────────────────────────────────────┐
│                    MONITORING POINTS                         │
└─────────────────────────────────────────────────────────────┘

1. Integration Engine Logs
   └─> docker-compose logs -f integration-engine
       • Request received
       • Transformation complete
       • SAP response received

2. SAP ERP Logs
   └─> docker-compose logs -f sap-erp-service
       • XML received
       • Order created
       • Response sent

3. Health Checks
   └─> curl http://localhost:8081/camel/api/health
   └─> curl http://localhost:8094/api/system/health

4. Request Status
   └─> curl http://localhost:8094/api/electricity-load-requests
```

---

## 🚦 Status Codes

| Code | Meaning | When |
|------|---------|------|
| 201 | Created | Request successfully processed by SAP |
| 400 | Bad Request | Invalid JSON or XML format |
| 404 | Not Found | Request ID not found in SAP |
| 500 | Server Error | SAP service unavailable or processing error |

---

## 🔑 Key Files Reference

```
Inte-platform/
├── integration-engine/
│   └── src/main/java/com/openpoint/engine/
│       ├── model/
│       │   ├── ElectricityLoadRequest.java      ← JSON model
│       │   └── SAPElectricityLoadRequest.java   ← XML model
│       ├── processor/
│       │   └── ElectricityLoadTransformer.java  ← Transformation logic
│       └── routes/
│           └── IntegrationRoutes.java           ← API endpoint
│
├── mock-services/sap-erp-service/
│   └── app.py                                   ← SAP endpoints
│
└── Documentation/
    ├── ELECTRICITY_LOAD_API.md                  ← Full API docs
    ├── QUICK_START_ELECTRICITY_API.md           ← Quick reference
    └── ELECTRICITY_INTEGRATION_SUMMARY.md       ← Implementation summary
```

---

**Visual Guide Version:** 1.0.0  
**Last Updated:** January 20, 2026
