# 🪟 Windows Testing Guide - Salesforce to SAP Integration

## 🚀 Quick Start

### Method 1: Run the Test Script (Easiest)

1. **Double-click** `test-integration.bat`
   
   OR

2. **Run in PowerShell:**
   ```powershell
   cd Inte-platform
   .\test-integration.ps1
   ```

---

## 📋 Manual Testing Commands

### Test 1: Health Check

```powershell
Invoke-RestMethod -Uri "http://localhost:8081/camel/api/health" -Method Get
```

**Expected Response:**
```json
{
  "status": "healthy",
  "engine": "camel-4.2.0",
  "features": ["json-to-xml", "electricity-load-integration"]
}
```

---

### Test 2: Submit Electricity Load Request

**Option A: Single Line**
```powershell
Invoke-RestMethod -Uri "http://localhost:8081/camel/api/integration/mulesoft/load-request/xml" -Method Post -ContentType "application/json" -Body '{"requestId":"SF-REQ-10021","customerId":"CUST-88991","serviceType":"ELECTRICITY_LOAD_INCREASE","currentLoadKW":5,"requestedLoadKW":10,"propertyType":"RESIDENTIAL","address":{"city":"Hyderabad","pinCode":"500081"}}'
```

**Option B: Multi-Line (Recommended)**
```powershell
$body = @{
  requestId = "SF-REQ-10021"
  customerId = "CUST-88991"
  serviceType = "ELECTRICITY_LOAD_INCREASE"
  currentLoadKW = 5
  requestedLoadKW = 10
  propertyType = "RESIDENTIAL"
  address = @{
    city = "Hyderabad"
    pinCode = "500081"
  }
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8081/camel/api/integration/mulesoft/load-request/xml" -Method Post -ContentType "application/json" -Body $body
```

**Expected Response (XML):**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<ElectricityLoadResponse>
  <Status>SUCCESS</Status>
  <Message>Electricity load request received and processed successfully</Message>
  <RequestID>SF-REQ-10021</RequestID>
  <SAPOrderID>SAP-EL-000001</SAPOrderID>
  <ProcessingTime>2024-01-20T10:30:00Z</ProcessingTime>
  <EstimatedCompletionDays>7</EstimatedCompletionDays>
  <ApprovalRequired>true</ApprovalRequired>
  <TechnicalFeasibility>PENDING_REVIEW</TechnicalFeasibility>
  <IntegrationSource>SALESFORCE_MULESOFT</IntegrationSource>
</ElectricityLoadResponse>
```

---

### Test 3: Check Request Status

```powershell
Invoke-RestMethod -Uri "http://localhost:8094/api/electricity-load-request/SF-REQ-10021" -Method Get
```

**Expected Response (JSON):**
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
  "source": "SALESFORCE_MULESOFT",
  "sap_order_id": "SAP-EL-000001"
}
```

---

### Test 4: List All Requests

```powershell
Invoke-RestMethod -Uri "http://localhost:8094/api/electricity-load-requests" -Method Get
```

**Filter by City:**
```powershell
Invoke-RestMethod -Uri "http://localhost:8094/api/electricity-load-requests?city=Hyderabad" -Method Get
```

---

## 🎯 Multiple Test Examples

### Example 1: Residential Load Increase
```powershell
$body1 = @{
  requestId = "SF-REQ-10021"
  customerId = "CUST-88991"
  serviceType = "ELECTRICITY_LOAD_INCREASE"
  currentLoadKW = 5
  requestedLoadKW = 10
  propertyType = "RESIDENTIAL"
  address = @{
    city = "Hyderabad"
    pinCode = "500081"
  }
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8081/camel/api/integration/mulesoft/load-request/xml" -Method Post -ContentType "application/json" -Body $body1
```

### Example 2: Commercial Load Increase
```powershell
$body2 = @{
  requestId = "SF-REQ-10022"
  customerId = "CUST-77882"
  serviceType = "ELECTRICITY_LOAD_INCREASE"
  currentLoadKW = 50
  requestedLoadKW = 100
  propertyType = "COMMERCIAL"
  address = @{
    city = "Bangalore"
    pinCode = "560001"
  }
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8081/camel/api/integration/mulesoft/load-request/xml" -Method Post -ContentType "application/json" -Body $body2
```

### Example 3: Industrial Load Increase
```powershell
$body3 = @{
  requestId = "SF-REQ-10023"
  customerId = "CUST-66773"
  serviceType = "ELECTRICITY_LOAD_INCREASE"
  currentLoadKW = 200
  requestedLoadKW = 500
  propertyType = "INDUSTRIAL"
  address = @{
    city = "Mumbai"
    pinCode = "400001"
  }
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8081/camel/api/integration/mulesoft/load-request/xml" -Method Post -ContentType "application/json" -Body $body3
```

---

## 🔍 Monitoring Commands

### View Integration Engine Logs
```powershell
docker-compose logs -f integration-engine
```

### View SAP ERP Logs
```powershell
docker-compose logs -f sap-erp-service
```

### Check All Services Status
```powershell
docker-compose ps
```

---

## 🐛 Troubleshooting

### Issue: "Connection Refused"

**Check if services are running:**
```powershell
docker-compose ps
```

**Restart services:**
```powershell
docker-compose restart integration-engine sap-erp-service
```

### Issue: "Cannot connect to Docker daemon"

**Start Docker Desktop:**
1. Open Docker Desktop application
2. Wait for it to start
3. Try again

### Issue: PowerShell Execution Policy Error

**Run this command:**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

---

## 📊 Using Postman (Recommended for Windows)

### Setup:
1. Download Postman: https://www.postman.com/downloads/
2. Create new POST request
3. URL: `http://localhost:8081/camel/api/integration/mulesoft/load-request/xml`
4. Headers: 
   - Key: `Content-Type`
   - Value: `application/json`
5. Body → Raw → JSON:
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
6. Click "Send"

---

## 🎨 Using VS Code REST Client Extension

### Install Extension:
1. Open VS Code
2. Install "REST Client" extension
3. Create file: `test-requests.http`

### Add this content:
```http
### Health Check
GET http://localhost:8081/camel/api/health

### Submit Electricity Load Request
POST http://localhost:8081/camel/api/integration/mulesoft/load-request/xml
Content-Type: application/json

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

### Check Request Status
GET http://localhost:8094/api/electricity-load-request/SF-REQ-10021

### List All Requests
GET http://localhost:8094/api/electricity-load-requests
```

4. Click "Send Request" above each request

---

## 📝 Save Response to File

```powershell
$response = Invoke-RestMethod -Uri "http://localhost:8081/camel/api/integration/mulesoft/load-request/xml" -Method Post -ContentType "application/json" -Body $body

$response | Out-File -FilePath "response.xml"
Write-Host "Response saved to response.xml"
```

---

## 🔄 Batch Testing Script

Create `batch-test.ps1`:
```powershell
# Test multiple requests
$cities = @("Hyderabad", "Bangalore", "Mumbai", "Delhi", "Chennai")
$counter = 10021

foreach ($city in $cities) {
    $body = @{
        requestId = "SF-REQ-$counter"
        customerId = "CUST-$(Get-Random -Minimum 10000 -Maximum 99999)"
        serviceType = "ELECTRICITY_LOAD_INCREASE"
        currentLoadKW = Get-Random -Minimum 5 -Maximum 50
        requestedLoadKW = Get-Random -Minimum 51 -Maximum 200
        propertyType = "RESIDENTIAL"
        address = @{
            city = $city
            pinCode = "$(Get-Random -Minimum 100000 -Maximum 999999)"
        }
    } | ConvertTo-Json
    
    Write-Host "Submitting request for $city..." -ForegroundColor Yellow
    $response = Invoke-RestMethod -Uri "http://localhost:8081/camel/api/integration/mulesoft/load-request/xml" -Method Post -ContentType "application/json" -Body $body
    
    [xml]$xmlResponse = $response
    Write-Host "✓ Created: $($xmlResponse.ElectricityLoadResponse.SAPOrderID)" -ForegroundColor Green
    
    $counter++
    Start-Sleep -Seconds 1
}

Write-Host "`nAll requests submitted!" -ForegroundColor Cyan
```

Run it:
```powershell
.\batch-test.ps1
```

---

## 📞 Quick Reference

| Command | Purpose |
|---------|---------|
| `.\test-integration.ps1` | Run automated test |
| `docker-compose up --build` | Start all services |
| `docker-compose ps` | Check service status |
| `docker-compose logs -f integration-engine` | View logs |
| `docker-compose restart integration-engine` | Restart service |
| `docker-compose down` | Stop all services |

---

**Windows Testing Guide Version:** 1.0.0  
**Last Updated:** January 20, 2026
