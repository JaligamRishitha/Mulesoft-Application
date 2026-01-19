# Mock Services UI

This directory contains mock services for ERP, CRM, and ITSM systems with web-based UI interfaces.

## Services Overview

### 🏢 ERP Service (Port 8091)
**URL:** http://localhost:8091

Features:
- **Orders Management** - View and track customer orders
- **Inventory Management** - Monitor stock levels and warehouse data
- **Invoices** - Track payment status and due dates

### 👥 CRM Service (Port 8092)
**URL:** http://localhost:8092

Features:
- **Customers** - Manage customer database with revenue tracking
- **Leads** - Track potential customers with lead scoring
- **Opportunities** - Monitor sales pipeline and deal stages

### 🎫 ITSM Service (Port 8093)
**URL:** http://localhost:8093

Features:
- **Tickets** - IT support ticket management
- **Incidents** - Track production incidents and outages
- **Changes** - Manage change requests and deployments

## API Endpoints

Each service provides both UI and REST API endpoints:

### ERP Service
- `GET /` - Web UI
- `GET /orders` - JSON API for orders
- `GET /inventory` - JSON API for inventory
- `GET /invoices` - JSON API for invoices
- `GET /health` - Health check

### CRM Service
- `GET /` - Web UI
- `GET /customers` - JSON API for customers
- `GET /leads` - JSON API for leads
- `GET /opportunities` - JSON API for opportunities
- `GET /health` - Health check

### ITSM Service
- `GET /` - Web UI
- `GET /tickets` - JSON API for tickets
- `GET /incidents` - JSON API for incidents
- `GET /changes` - JSON API for changes
- `GET /health` - Health check

## Running the Services

### Using Docker Compose
```bash
cd Inte-platform/deployments
docker-compose up -d erp-service crm-service itsm-service
```

### Access the UIs
- ERP: http://localhost:8091
- CRM: http://localhost:8092
- ITSM: http://localhost:8093

### Rebuild After Changes
```bash
docker-compose up -d --build erp-service crm-service itsm-service
```

## Features

- **Real-time Data** - Auto-refreshes every 30 seconds
- **Responsive Design** - Works on desktop and mobile
- **Color-coded Status** - Visual indicators for different states
- **Statistics Dashboard** - Key metrics at a glance
- **Tab Navigation** - Easy switching between different data views

## Technology Stack

- **Backend:** FastAPI (Python)
- **Frontend:** Vanilla JavaScript + HTML5 + CSS3
- **Styling:** Custom CSS with gradient themes
- **Data Format:** JSON REST APIs
