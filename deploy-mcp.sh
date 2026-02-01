#!/bin/bash

# Deploy MCP Server to Remote Server
SERVER_IP="149.102.158.71"
MCP_PORT="8090"

echo "Deploying MCP Server to $SERVER_IP:$MCP_PORT"

# 1. Copy MCP files to server
scp -r Inte-platform/mcp-server/ user@$SERVER_IP:/opt/mulesoft/

# 2. SSH to server and setup
ssh user@$SERVER_IP << 'EOF'
cd /opt/mulesoft/mcp-server

# Install dependencies
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Update configuration for server deployment
sed -i 's/localhost/0.0.0.0/g' mcp_mulesoft.py

# Start MCP server as service
nohup python3 mcp_mulesoft.py > mcp.log 2>&1 &

echo "MCP Server deployed and running on port 8090"
EOF

echo "Deployment complete!"
echo "MCP Server URL: http://$SERVER_IP:$MCP_PORT/api"
