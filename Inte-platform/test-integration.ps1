# PowerShell Test Script for Salesforce to SAP Integration
# Usage: .\test-integration.ps1

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Salesforce to SAP Integration Test" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Test 1: Health Check
Write-Host "1. Checking Integration Engine Health..." -ForegroundColor Yellow
try {
    $health = Invoke-RestMethod -Uri "http://localhost:8081/camel/api/health" -Method Get
    Write-Host "   ✓ Integration Engine is healthy" -ForegroundColor Green
    Write-Host "   Status: $($health.status)" -ForegroundColor Gray
} catch {
    Write-Host "   ✗ Integration Engine is not responding" -ForegroundColor Red
    Write-Host "   Error: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

Write-Host ""

# Test 2: Submit Electricity Load Request
Write-Host "2. Submitting Electricity Load Request..." -ForegroundColor Yellow

$requestBody = @{
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

Write-Host "   Request Body:" -ForegroundColor Gray
Write-Host $requestBody -ForegroundColor Gray
Write-Host ""

try {
    $response = Invoke-RestMethod -Uri "http://localhost:8081/camel/api/integration/mulesoft/load-request/xml" `
                                  -Method Post `
                                  -ContentType "application/json" `
                                  -Body $requestBody
    
    Write-Host "   ✓ Request submitted successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "   SAP Response (XML):" -ForegroundColor Cyan
    Write-Host $response -ForegroundColor White
    
    # Try to parse XML response
    try {
        [xml]$xmlResponse = $response
        $sapOrderId = $xmlResponse.ElectricityLoadResponse.SAPOrderID
        $status = $xmlResponse.ElectricityLoadResponse.Status
        
        Write-Host ""
        Write-Host "   ✓ SAP Order Created: $sapOrderId" -ForegroundColor Green
        Write-Host "   Status: $status" -ForegroundColor Green
    } catch {
        Write-Host "   (Could not parse XML response)" -ForegroundColor Yellow
    }
    
} catch {
    Write-Host "   ✗ Request failed" -ForegroundColor Red
    Write-Host "   Error: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

Write-Host ""

# Test 3: Check SAP ERP Health
Write-Host "3. Checking SAP ERP Health..." -ForegroundColor Yellow
try {
    $sapHealth = Invoke-RestMethod -Uri "http://localhost:8094/api/system/health" -Method Get
    Write-Host "   ✓ SAP ERP is healthy" -ForegroundColor Green
    Write-Host "   Service: $($sapHealth.service)" -ForegroundColor Gray
} catch {
    Write-Host "   ✗ SAP ERP is not responding" -ForegroundColor Red
}

Write-Host ""

# Test 4: List all requests in SAP
Write-Host "4. Listing all requests in SAP..." -ForegroundColor Yellow
try {
    $requests = Invoke-RestMethod -Uri "http://localhost:8094/api/electricity-load-requests" -Method Get
    Write-Host "   ✓ Found $($requests.total) request(s)" -ForegroundColor Green
    
    if ($requests.total -gt 0) {
        Write-Host ""
        Write-Host "   Recent Requests:" -ForegroundColor Cyan
        foreach ($req in $requests.requests | Select-Object -First 5) {
            Write-Host "   - Request ID: $($req.request_id)" -ForegroundColor White
            Write-Host "     SAP Order: $($req.sap_order_id)" -ForegroundColor Gray
            Write-Host "     Status: $($req.status)" -ForegroundColor Gray
            Write-Host "     City: $($req.city)" -ForegroundColor Gray
            Write-Host ""
        }
    }
} catch {
    Write-Host "   ✗ Could not retrieve requests" -ForegroundColor Red
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Test Complete!" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
