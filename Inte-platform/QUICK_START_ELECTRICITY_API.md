# ⚡ Quick Start - Electricity Load Request API

## 🚀 Start the System

```bash
cd Inte-platform/deployments
docker-compose up --build
```

Wait 2-3 minutes for all services to start.

---

## 📤 SALESFORCE TO SAP INTEGRATION

**Endpoint:** `POST http://localhost:8081/camel/api/integration/mulesoft/load-request/xml`

**Request (JSON from Salesforce):**
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

**cURL Command:**
```bash
curl -X POST http://localhost:8081/camel/api/integration/mulesoft/load-request/xml \
  -H "Content-Type: application/json" \
  -d '{"requestId":"SF-REQ-10021","customerId":"CUST-88991","serviceType":"ELECTRICITY_LOAD_INCREASE","currentLoadKW":5,"requestedLoadKW":10,"propertyType":"RESIDENTIAL","address":{"city":"Hyderabad","pinCode":"500081"}}'
```

---

## 📥 RESPONSE (XML)

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

---

## 🔍 CHECK STATUS

**Get Single Request:**
```bash
curl http://localhost:8094/api/electricity-load-request/SF-REQ-10021
```

**List All Requests:**
```bash
curl http://localhost:8094/api/electricity-load-requests
```

---

## 🔄 What Happens Behind the Scenes

1. **Salesforce sends JSON** → Integration Engine (port 8081)
   - Endpoint: `/api/integration/mulesoft/load-request/xml`
2. **Engine transforms** → JSON to XML
3. **Engine sends XML** → SAP ERP (port 8094)
   - Endpoint: `/api/integration/mulesoft/load-request/xml`
4. **SAP processes** → Creates order
5. **SAP responds** → XML response
6. **Salesforce receives** → XML response

---

## 📊 Service URLs

| Service | URL |
|---------|-----|
| **Salesforce → Integration** | http://localhost:8081/camel/api/integration/mulesoft/load-request/xml |
| **Integration → SAP** | http://sap-erp-service:8094/api/integration/mulesoft/load-request/xml |
| **SAP ERP Docs** | http://localhost:8094/docs |
| **Health Check** | http://localhost:8081/camel/api/health |

---

## ✅ Test Examples

### Example 1: Residential Load Increase
```bash
curl -X POST http://localhost:8081/camel/api/integration/mulesoft/load-request/xml \
  -H "Content-Type: application/json" \
  -d '{"requestId":"SF-REQ-10021","customerId":"CUST-88991","serviceType":"ELECTRICITY_LOAD_INCREASE","currentLoadKW":5,"requestedLoadKW":10,"propertyType":"RESIDENTIAL","address":{"city":"Hyderabad","pinCode":"500081"}}'
```

### Example 2: Commercial Load Increase
```bash
curl -X POST http://localhost:8081/camel/api/integration/mulesoft/load-request/xml \
  -H "Content-Type: application/json" \
  -d '{"requestId":"SF-REQ-10022","customerId":"CUST-77882","serviceType":"ELECTRICITY_LOAD_INCREASE","currentLoadKW":50,"requestedLoadKW":100,"propertyType":"COMMERCIAL","address":{"city":"Bangalore","pinCode":"560001"}}'
```

### Example 3: Industrial Load Increase
```bash
curl -X POST http://localhost:8081/camel/api/integration/mulesoft/load-request/xml \
  -H "Content-Type: application/json" \
  -d '{"requestId":"SF-REQ-10023","customerId":"CUST-66773","serviceType":"ELECTRICITY_LOAD_INCREASE","currentLoadKW":200,"requestedLoadKW":500,"propertyType":"INDUSTRIAL","address":{"city":"Mumbai","pinCode":"400001"}}'
```

---

## 🐛 Troubleshooting

**Services not responding?**
```bash
docker-compose ps
docker-compose logs -f integration-engine sap-erp-service
```

**Restart services:**
```bash
docker-compose restart integration-engine sap-erp-service
```

**Full reset:**
```bash
docker-compose down -v
docker-compose up --build
```

---

## 📖 Full Documentation

See `ELECTRICITY_LOAD_API.md` for complete API documentation.
