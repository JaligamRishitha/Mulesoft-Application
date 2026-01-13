#!/bin/bash
# Kong Gateway Setup Script

KONG_ADMIN="http://localhost:8001"

echo "Setting up Kong Gateway routes..."

# Platform Backend Service
curl -s -X POST $KONG_ADMIN/services \
  --data "name=platform-api" \
  --data "url=http://platform-backend:8080"

curl -s -X POST $KONG_ADMIN/services/platform-api/routes \
  --data "name=platform-route" \
  --data "paths[]=/platform" \
  --data "strip_path=true"

# ERP Service
curl -s -X POST $KONG_ADMIN/services \
  --data "name=erp-api" \
  --data "url=http://erp-service:8091"

curl -s -X POST $KONG_ADMIN/services/erp-api/routes \
  --data "name=erp-route" \
  --data "paths[]=/erp" \
  --data "strip_path=true"

# CRM Service
curl -s -X POST $KONG_ADMIN/services \
  --data "name=crm-api" \
  --data "url=http://crm-service:8092"

curl -s -X POST $KONG_ADMIN/services/crm-api/routes \
  --data "name=crm-route" \
  --data "paths[]=/crm" \
  --data "strip_path=true"

# ITSM Service
curl -s -X POST $KONG_ADMIN/services \
  --data "name=itsm-api" \
  --data "url=http://itsm-service:8093"

curl -s -X POST $KONG_ADMIN/services/itsm-api/routes \
  --data "name=itsm-route" \
  --data "paths[]=/itsm" \
  --data "strip_path=true"

# Integration Engine
curl -s -X POST $KONG_ADMIN/services \
  --data "name=engine-api" \
  --data "url=http://integration-engine:8081"

curl -s -X POST $KONG_ADMIN/services/engine-api/routes \
  --data "name=engine-route" \
  --data "paths[]=/engine" \
  --data "strip_path=true"

# Enable Rate Limiting Plugin
curl -s -X POST $KONG_ADMIN/plugins \
  --data "name=rate-limiting" \
  --data "config.minute=100" \
  --data "config.policy=local"

# Enable CORS Plugin
curl -s -X POST $KONG_ADMIN/plugins \
  --data "name=cors" \
  --data "config.origins=*" \
  --data "config.methods=GET,POST,PUT,DELETE,OPTIONS" \
  --data "config.headers=Authorization,Content-Type"

echo ""
echo "Kong setup complete!"
echo ""
echo "Routes configured:"
echo "  http://localhost:8000/platform/* -> Platform Backend"
echo "  http://localhost:8000/erp/*      -> ERP Mock Service"
echo "  http://localhost:8000/crm/*      -> CRM Mock Service"
echo "  http://localhost:8000/itsm/*     -> ITSM Mock Service"
echo "  http://localhost:8000/engine/*   -> Integration Engine"
