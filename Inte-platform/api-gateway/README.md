# Kong API Gateway

## Routes

| Path | Service | Description |
|------|---------|-------------|
| /platform/* | platform-backend:8080 | Platform API |
| /engine/* | integration-engine:8081 | Camel Integration Engine |
| /erp/* | erp-service:8091 | Mock ERP Service |
| /crm/* | crm-service:8092 | Mock CRM Service |
| /itsm/* | itsm-service:8093 | Mock ITSM Service |

## Admin API

Kong Admin API is available at http://localhost:8001

### Useful Commands

```bash
# List services
curl http://localhost:8001/services

# List routes
curl http://localhost:8001/routes

# Add rate limiting to a service
curl -X POST http://localhost:8001/services/platform-api/plugins \
  --data "name=rate-limiting" \
  --data "config.minute=100"
```

## Plugins Enabled

- Rate Limiting (100 req/min)
- CORS
