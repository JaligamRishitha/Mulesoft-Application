# MCP Server Deployment Guide

## Step 1: Prepare MCP for Server Deployment

1. **Update MCP Configuration** (already done):
   - Server runs on `0.0.0.0:8090` (accepts external connections)
   - Connects to remote backends on same server

## Step 2: Deploy to Server

### Option A: Manual Deployment
```bash
# 1. Copy files to server
scp -r Inte-platform/mcp-server/ user@149.102.158.71:/opt/mulesoft/

# 2. SSH to server
ssh user@149.102.158.71

# 3. Setup and run
cd /opt/mulesoft/mcp-server
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 mcp_mulesoft.py
```

### Option B: Docker Deployment
```bash
# Build and deploy with Docker
docker build -t mcp-server .
docker run -d -p 8090:8090 --name mcp-server mcp-server
```

## Step 3: Update Frontend Configuration

After MCP is deployed to server:

```javascript
// src/api.js
const api = axios.create({
  baseURL: 'http://149.102.158.71:8090/api',  // MCP on server
  headers: { 'Content-Type': 'application/json' },
});
```

## Step 4: Update Remote Backend Connector

```bash
# Create working Salesforce connector
curl -X POST http://149.102.158.71:4797/api/connectors/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "connector_name": "Salesforce Production",
    "connector_type": "salesforce", 
    "connection_config": {
      "server_url": "http://localhost:4799"
    }
  }'
```

## Final Architecture:
```
Frontend → MCP Server (149.102.158.71:8090) → Salesforce (149.102.158.71:4799)
        ↘ Remote Backend (149.102.158.71:4797) → SAP/ServiceNow
```
