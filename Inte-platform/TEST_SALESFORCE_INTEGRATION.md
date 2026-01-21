# Salesforce Integration Testing Guide

## 🎯 Your Requested Endpoint
**GET http://localhost:8000/api/cases/1/platform-event-format**

## 🚀 Available Endpoints

### 1. Test External App Connection
```bash
GET http://localhost:8080/api/cases/external/test
```

### 2. Fetch Cases from External App
```bash
GET http://localhost:8080/api/cases/external/cases
```

### 3. Sync Cases from Salesforce Connector
```bash
POST http://localhost:8080/api/cases/sync?connector_id=1&limit=10
```

### 4. List Synced Cases
```bash
GET http://localhost:8080/api/cases/
```

### 5. Get Case in Platform Event Format (Your Requested Endpoint)
```bash
GET http://localhost:8080/api/cases/1/platform-event-format
```

### 6. Get Case by Salesforce ID in Platform Event Format
```bash
GET http://localhost:8080/api/cases/salesforce/5003000000D8cuI/platform-event-format
```

## 🔧 Setup Steps

### Step 1: Ensure Your External Salesforce App is Running
Make sure your Salesforce application is running on port 5173 and has an API endpoint for cases.

### Step 2: Test the Integration
```bash
# Test if external app is reachable
curl http://localhost:8080/api/cases/external/test

# Try to fetch cases from external app
curl http://localhost:8080/api/cases/external/cases
```

### Step 3: Configure Salesforce Connector
The system has a pre-configured connector pointing to your external app:
- **Name**: External Salesforce App
- **URL**: http://localhost:5173
- **Type**: Salesforce

### Step 4: Test Platform Event Format
Once you have cases synced, test the platform event format:
```bash
curl http://localhost:8080/api/cases/1/platform-event-format
```

## 📋 Expected Platform Event Format Response

```json
{
  "eventType": "CaseUpdate",
  "eventId": "case-5003000000D8cuI-1642781234",
  "eventTime": "2024-01-21T19:45:23.123Z",
  "source": "Salesforce",
  "data": {
    "caseId": "5003000000D8cuI",
    "caseNumber": "00001001",
    "subject": "API Integration Issue",
    "description": "Customer experiencing data sync issues",
    "status": "New",
    "priority": "High",
    "origin": "Web",
    "account": {
      "id": "0013000000GxFyU",
      "name": "Acme Corporation"
    },
    "contact": {
      "id": "0033000000Q4CuU",
      "name": "John Smith"
    },
    "owner": {
      "id": "0053000000A4CuU",
      "name": "Sarah Johnson"
    },
    "createdDate": "2024-01-19T10:30:00Z",
    "closedDate": null,
    "lastModifiedDate": "2024-01-21T16:45:00Z"
  },
  "metadata": {
    "syncedAt": "2024-01-21T19:45:23.123Z",
    "source": "MuleSoft Integration Platform",
    "version": "1.0",
    "connector": "Salesforce",
    "dataFormat": "platform-event"
  }
}
```

## 🔍 Troubleshooting

### External App Not Responding
If your external app on port 5173 isn't responding:
1. Verify it's running: `curl http://localhost:5173`
2. Check if it has a cases API endpoint
3. Update the connector configuration if needed

### No Cases Found
If no cases are returned:
1. First sync cases: `POST http://localhost:8080/api/cases/sync?connector_id=1`
2. Then try the platform event format endpoint

### Authentication Issues
The system uses JWT authentication. Make sure to:
1. Login first: `POST http://localhost:8080/api/auth/login`
2. Use the returned token in Authorization header: `Bearer <token>`

## 🎯 Your Specific Endpoint

To access **GET http://localhost:8000/api/cases/1/platform-event-format** as requested:

1. **Note**: The platform backend runs on port 8080, not 8000
2. **Correct URL**: `http://localhost:8080/api/cases/1/platform-event-format`
3. **Kong Gateway**: If you want to access via port 8000 (Kong), configure Kong to proxy to the backend

### Kong Configuration for Port 8000
If you want to use port 8000 as requested, configure Kong to route to the backend:
```bash
# Add service
curl -X POST http://localhost:8001/services \
  --data name=platform-backend \
  --data url=http://platform-backend:8080

# Add route
curl -X POST http://localhost:8001/services/platform-backend/routes \
  --data paths[]=/api
```

Then your endpoint will be available at:
**GET http://localhost:8000/api/cases/1/platform-event-format**