# Enterprise Integration Platform

A comprehensive, production-ready enterprise integration platform inspired by MuleSoft Anypoint Platform. This platform provides API management, integration orchestration, real-time monitoring, and enterprise connectivity with a modern, intuitive interface.

## 🌟 Overview

This platform enables organizations to connect applications, data, and devices across on-premises and cloud environments. It combines API gateway capabilities, integration engine, observability tools, and mock enterprise systems for complete end-to-end integration testing and deployment.

### Key Features

- **Visual Integration Designer** - Build integration flows with YAML-based configuration
- **API Gateway** - Kong-powered API management with rate limiting, authentication, and routing
- **Real-time Monitoring** - Prometheus metrics with Grafana dashboards for complete observability
- **Enterprise Connectors** - Pre-built connectors for ERP, CRM, and ITSM systems
- **Authentication & Authorization** - JWT-based security with role-based access control
- **Integration Runtime** - Apache Camel-based execution engine for reliable message processing
- **Mock Services** - Fully functional mock ERP, CRM, and ITSM services with web UIs
- **Dashboard Analytics** - Real-time insights into integrations, APIs, and system health

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    UI Dashboard (React + Ant Design)                 │
│         Integration Management | API Management | Monitoring         │
└────────────────────────────────┬────────────────────────────────────┘
                                 │ REST API
┌────────────────────────────────▼────────────────────────────────────┐
│              Platform Backend (Python FastAPI)                       │
│   Auth | Integrations | APIs | Connectors | Dashboard | Runtime     │
└────────┬──────────────────────┬────────────────────┬────────────────┘
         │                      │                    │
┌────────▼────────┐  ┌──────────▼──────────┐  ┌─────▼──────────────┐
│  Integration    │  │   API Gateway       │  │   Observability    │
│  Engine         │  │   (Kong)            │  │   Stack            │
│  (Apache Camel) │  │   - Rate Limiting   │  │   - Prometheus     │
│  - HTTP/REST    │  │   - CORS            │  │   - Grafana        │
│  - Timers       │  │   - Auth            │  │   - Metrics        │
│  - Transforms   │  │   - Routing         │  │   - Dashboards     │
└────────┬────────┘  └──────────┬──────────┘  └────────────────────┘
         │                      │
┌────────▼──────────────────────▼─────────────────────────────────────┐
│                        Mock Enterprise Systems                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │  SAP ERP     │  │  CRM         │  │  ITSM                    │  │
│  │  - Orders    │  │  - Customers │  │  - Tickets               │  │
│  │  - Inventory │  │  - Leads     │  │  - Incidents             │  │
│  │  - Finance   │  │  - Pipeline  │  │  - Changes               │  │
│  │  - Vendors   │  │              │  │                          │  │
│  └──────────────┘  └──────────────┘  └──────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- Docker Desktop (Windows/Mac) or Docker Engine + Docker Compose (Linux)
- 8GB RAM minimum (16GB recommended)
- Ports available: 3000, 8000, 8001, 8080, 8081, 8091-8093, 9090, 3002, 1234

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd Inte-platform
   ```

2. **Start all services**
   ```bash
   cd deployments
   docker-compose up --build
   ```

3. **Wait for services to initialize** (approximately 2-3 minutes)

4. **Access the platform**
   - Main Dashboard: http://localhost:3000
   - Platform API: http://localhost:8080/docs
   - API Gateway: http://localhost:8000
   - Grafana: http://localhost:3002

### First Login

1. Navigate to http://localhost:3000
2. Use the pre-seeded test accounts:
   - **Admin**: `admin@mulesoft.io` / `admin123`
   - **Developer**: `developer@mulesoft.io` / `dev123`

## 📊 Services & Ports

| Service | Port | URL | Description |
|---------|------|-----|-------------|
| **UI Dashboard** | 3000 | http://localhost:3000 | React-based management console |
| **Platform Backend** | 8080 | http://localhost:8080 | FastAPI REST API with Swagger docs |
| **Integration Engine** | 8081 | http://localhost:8081 | Apache Camel runtime |
| **Kong Gateway** | 8000 | http://localhost:8000 | API Gateway proxy |
| **Kong Admin API** | 8001 | http://localhost:8001 | Kong administration |
| **SAP ERP Mock** | 8091 | http://localhost:8091 | Mock SAP ERP with web UI |
| **CRM Mock** | 8092 | http://localhost:8092 | Mock CRM with web UI |
| **ITSM Mock** | 8093 | http://localhost:8093 | Mock ITSM with web UI |
| **Prometheus** | 9090 | http://localhost:9090 | Metrics collection |
| **Grafana** | 3002 | http://localhost:3002 | Monitoring dashboards |
| **PostgreSQL** | 1234 | localhost:1234 | Platform database |

## 🎯 Core Features

### 1. Integration Management

Create, deploy, and monitor integration flows that connect your enterprise systems.

**Features:**
- Visual flow designer with YAML configuration
- Pre-built templates for common integration patterns
- Version control and deployment history
- Real-time execution logs and error tracking
- Support for timers, HTTP endpoints, and message transformations

**Example Integration Flow:**
```yaml
routes:
  - id: erp-crm-sync
    from:
      uri: timer:customerSync
      parameters:
        period: 300000
    steps:
      - to: http://erp-service:8091/orders
      - log: "Fetched ${body.size()} orders from ERP"
      - to: http://crm-service:8092/customers
      - log: "Synced to CRM successfully"
```

### 2. API Management

Manage, secure, and monitor APIs through the Kong-powered gateway.

**Features:**
- API endpoint registration and documentation
- Rate limiting (configurable per endpoint)
- Authentication and authorization
- IP whitelisting
- CORS configuration
- Request/response logging
- API key management

**Supported Operations:**
- Create and manage API endpoints
- Configure rate limits and security policies
- Monitor API usage and performance
- Generate and revoke API keys

### 3. Enterprise Connectors

Pre-built connectors for common enterprise systems.

**Available Connectors:**
- **SAP ERP** - Sales orders, inventory, finance, purchasing, production
- **CRM** - Customers, leads, opportunities, sales pipeline
- **ITSM** - Tickets, incidents, change management

**SAP ERP Connector Capabilities:**
- Sales & Orders Management
- Inventory & Stock Control
- Customer & Vendor Management
- Financial Operations (Invoices, Payments, AR)
- Purchasing & Procurement
- Production Planning
- Business Intelligence Reports

### 4. Observability & Monitoring

Complete visibility into your integration landscape.

**Metrics Collected:**
- Integration execution count and duration
- API request rates and latency
- Error rates and types
- System resource utilization
- Database connection pool stats

**Dashboards:**
- Real-time integration status
- API performance metrics
- System health overview
- Custom Grafana dashboards

### 5. Security & Authentication

Enterprise-grade security built-in.

**Features:**
- JWT-based authentication
- Role-based access control (Admin, Developer, Viewer)
- API key management
- Password hashing with bcrypt
- Session management
- Audit logging

## 📁 Project Structure

```
Inte-platform/
├── ui-dashboard/                    # React Frontend
│   ├── src/
│   │   ├── pages/                   # Dashboard, Integrations, APIs, etc.
│   │   ├── components/              # Reusable UI components
│   │   └── App.js                   # Main application
│   ├── package.json
│   └── Dockerfile
│
├── platform-backend/                # Python FastAPI Backend
│   ├── app/
│   │   ├── routers/                 # API route handlers
│   │   │   ├── auth.py              # Authentication endpoints
│   │   │   ├── integrations.py     # Integration management
│   │   │   ├── apis.py              # API management
│   │   │   ├── connectors.py       # Connector endpoints
│   │   │   ├── dashboard.py        # Dashboard data
│   │   │   ├── runtime.py          # Runtime operations
│   │   │   └── proxy.py             # Service proxy
│   │   ├── models.py                # SQLAlchemy models
│   │   ├── database.py              # Database configuration
│   │   ├── auth.py                  # Auth utilities
│   │   ├── seed.py                  # Database seeding
│   │   └── main.py                  # FastAPI application
│   ├── requirements.txt
│   └── Dockerfile
│
├── integration-engine/              # Apache Camel Integration Runtime
│   ├── src/main/java/
│   │   └── com/openpoint/
│   │       └── integration/         # Camel routes and processors
│   ├── pom.xml                      # Maven dependencies
│   └── Dockerfile
│
├── api-gateway/                     # Kong API Gateway
│   ├── kong/
│   │   └── kong.yml                 # Kong declarative config
│   ├── setup-kong.sh                # Gateway setup script
│   └── README.md
│
├── mock-services/                   # Mock Enterprise Systems
│   ├── sap-erp-service/             # Comprehensive SAP ERP mock
│   │   ├── app.py                   # FastAPI application
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   ├── crm-service/                 # CRM mock with web UI
│   │   ├── app.py
│   │   ├── templates/               # HTML templates
│   │   └── Dockerfile
│   ├── erp-service/                 # Simple ERP mock
│   │   ├── app.py
│   │   └── Dockerfile
│   ├── itsm-service/                # ITSM mock with web UI
│   │   ├── app.py
│   │   └── Dockerfile
│   └── README.md
│
├── observability/                   # Monitoring Stack
│   ├── prometheus/
│   │   └── prometheus.yml           # Prometheus configuration
│   └── grafana/
│       └── provisioning/            # Grafana dashboards
│
├── sample-flows/                    # Example integration flows
│   └── erp-crm-sync.yaml
│
├── deployments/                     # Docker Compose
│   └── docker-compose.yml           # All services orchestration
│
└── README.md                        # This file
```

## 🔧 Configuration

### Environment Variables

**Platform Backend:**
```bash
DATABASE_URL=postgresql://openpoint:openpoint123@postgres:5432/openpoint
JWT_SECRET=openpoint-secret-key-change-in-production
```

**UI Dashboard:**
```bash
REACT_APP_API_URL=http://localhost:8080/api
```

### Database

The platform uses PostgreSQL for persistent storage:
- **Database**: openpoint
- **User**: openpoint
- **Password**: openpoint123
- **Port**: 1234 (mapped from container port 5432)

**Models:**
- Users (authentication and authorization)
- Integrations (flow definitions and status)
- Integration Logs (execution history)
- API Endpoints (API management)
- API Keys (authentication tokens)

### Kong Gateway Configuration

Kong routes are configured to proxy requests to backend services:

| Route Pattern | Target Service | Description |
|--------------|----------------|-------------|
| `/platform/*` | platform-backend:8080 | Platform API |
| `/engine/*` | integration-engine:8081 | Integration engine |
| `/erp/*` | erp-service:8091 | ERP mock service |
| `/crm/*` | crm-service:8092 | CRM mock service |
| `/itsm/*` | itsm-service:8093 | ITSM mock service |

**Plugins Enabled:**
- Rate Limiting: 100 requests/minute per service
- CORS: Allow all origins (configurable)

## 🧪 Testing & Development

### Running Individual Services

Start specific services for development:

```bash
# Start only the database
docker-compose up -d postgres

# Start backend services
docker-compose up -d platform-backend integration-engine

# Start mock services
docker-compose up -d erp-service crm-service itsm-service sap-erp-service

# Start monitoring
docker-compose up -d prometheus grafana
```

### Accessing Service Logs

```bash
# View all logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f platform-backend
docker-compose logs -f integration-engine
docker-compose logs -f sap-erp-service
```

### Database Access

Connect to PostgreSQL:
```bash
psql -h localhost -p 1234 -U openpoint -d openpoint
# Password: openpoint123
```

### API Documentation

Interactive API documentation is available at:
- Platform Backend: http://localhost:8080/docs (Swagger UI)
- SAP ERP Mock: http://localhost:8091/docs
- Integration Engine: http://localhost:8081/actuator

### Rebuilding Services

After code changes:
```bash
# Rebuild all services
docker-compose up --build

# Rebuild specific service
docker-compose up --build platform-backend
```

## 📖 Usage Examples

### Creating an Integration

1. Navigate to the Integrations page
2. Click "Create Integration"
3. Fill in the details:
   - Name: "Customer Sync"
   - Description: "Sync customers from ERP to CRM"
   - Flow Configuration (YAML):
   ```yaml
   routes:
     - from: "timer:sync?period=60000"
       to: "http://erp-service:8091/customers"
   ```
4. Click "Create" and then "Deploy"

### Managing APIs

1. Go to the APIs page
2. Click "Create API Endpoint"
3. Configure:
   - Name: "Customer API"
   - Path: "/api/v1/customers"
   - Method: GET
   - Rate Limit: 100 req/min
   - Authentication: Required
4. Save and test the endpoint

### Monitoring Integrations

1. Access the Dashboard for overview metrics
2. View detailed logs in the Integrations page
3. Check Grafana dashboards at http://localhost:3002
4. Query Prometheus metrics at http://localhost:9090

### Using Mock Services

**SAP ERP Service** (http://localhost:8091):
- Comprehensive REST API with 40+ endpoints
- Modules: Sales, Inventory, Finance, Purchasing, Production
- Authentication with JWT tokens
- Full CRUD operations

**CRM Service** (http://localhost:8092):
- Web UI for visual data exploration
- REST API for customers, leads, opportunities
- Auto-refresh every 30 seconds

**ITSM Service** (http://localhost:8093):
- Ticket management system
- Incident tracking
- Change request workflow

## 🔐 Security Considerations

### Production Deployment

Before deploying to production:

1. **Change default credentials**
   - Update JWT_SECRET in environment variables
   - Change database passwords
   - Update Grafana admin password

2. **Enable HTTPS**
   - Configure SSL certificates for Kong
   - Use HTTPS for all external endpoints

3. **Restrict network access**
   - Use firewall rules to limit access
   - Configure Kong IP whitelisting
   - Use VPN for internal services

4. **Enable audit logging**
   - Configure comprehensive logging
   - Set up log aggregation
   - Monitor security events

5. **Regular updates**
   - Keep Docker images updated
   - Apply security patches
   - Monitor CVE databases

## 🐛 Troubleshooting

### Services won't start

```bash
# Check if ports are already in use
netstat -an | findstr "3000 8080 8081"

# Remove old containers and volumes
docker-compose down -v
docker-compose up --build
```

### Database connection errors

```bash
# Verify PostgreSQL is running
docker-compose ps postgres

# Check database logs
docker-compose logs postgres

# Recreate database
docker-compose down -v postgres
docker-compose up -d postgres
```

### Integration engine not executing flows

```bash
# Check integration engine logs
docker-compose logs integration-engine

# Verify backend connectivity
curl http://localhost:8081/actuator/health

# Restart the service
docker-compose restart integration-engine
```

### Kong gateway not routing

```bash
# Check Kong status
curl http://localhost:8001/status

# List configured services
curl http://localhost:8001/services

# Restart Kong
docker-compose restart kong
```

## 🤝 Contributing

Contributions are welcome! Please follow these guidelines:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is provided as-is for educational and demonstration purposes.

## 🙏 Acknowledgments

This platform is inspired by:
- **MuleSoft Anypoint Platform** - Enterprise integration architecture
- **Apache Camel** - Integration patterns and routing engine
- **Kong Gateway** - API management capabilities
- **Grafana/Prometheus** - Observability best practices

## 📞 Support

For issues, questions, or contributions:
- Open an issue on GitHub
- Check existing documentation
- Review logs for error details

## 🗺️ Roadmap

Future enhancements planned:
- [ ] GraphQL API support
- [ ] Kafka/RabbitMQ connectors
- [ ] Advanced data transformation UI
- [ ] Multi-tenancy support
- [ ] CI/CD pipeline integration
- [ ] Kubernetes deployment manifests
- [ ] Additional enterprise connectors (Salesforce, ServiceNow, SAP S/4HANA)
- [ ] API versioning and lifecycle management
- [ ] Advanced security policies (OAuth2, SAML)
- [ ] Performance testing and load balancing

---

**Built with ❤️ for the enterprise integration community**
