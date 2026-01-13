# MuleSoft Integration Platform

Enterprise-grade MuleSoft Anypoint Platform clone with API Gateway, Integration Engine, and Observability.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      UI Dashboard (React)                        │
└─────────────────────────┬───────────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────────┐
│                   Platform Backend (Python/FastAPI)              │
│              Auth, Projects, Deployments, Config                 │
└─────────────────────────┬───────────────────────────────────────┘
                          │
┌──────────────┬──────────▼──────────┬────────────────────────────┐
│ Integration  │    API Gateway      │      Observability         │
│ Engine       │    (Kong)           │   (Prometheus + Grafana)   │
│ (Camel)      │                     │                            │
└──────┬───────┴──────────┬──────────┴─────────────┬──────────────┘
       │                  │                        │
┌──────▼───────┬──────────▼──────────┬─────────────▼──────────────┐
│  ERP Mock    │    CRM Mock         │       ITSM Mock            │
└──────────────┴─────────────────────┴────────────────────────────┘
```

## Quick Start

```bash
cd Inte-platform/deployments
docker-compose up --build
```

## Services

| Service | Port | Description |
|---------|------|-------------|
| UI Dashboard | 3000 | React + Ant Design |
| Platform Backend | 8080 | FastAPI (Python) |
| Integration Engine | 8081 | Apache Camel Runtime |
| Kong Gateway | 8000 | API Gateway Proxy |
| Kong Admin | 8001 | Kong Admin API |
| ERP Mock | 8091 | Mock ERP Service |
| CRM Mock | 8092 | Mock CRM Service |
| ITSM Mock | 8093 | Mock ITSM Service |
| Prometheus | 9090 | Metrics |
| Grafana | 3002 | Dashboards |

## Default Credentials

- Platform: Register a new account
- Grafana: admin / admin

## Project Structure

```
Inte-platform/
├── ui-dashboard/           # React + Ant Design UI
├── platform-backend/       # Python FastAPI Backend
├── integration-engine/     # Apache Camel (Java)
├── api-gateway/            # Kong Configuration
├── mock-services/          # ERP, CRM, ITSM Mocks
├── observability/          # Prometheus + Grafana
└── deployments/            # Docker Compose
```
