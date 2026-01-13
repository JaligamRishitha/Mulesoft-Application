from fastapi import FastAPI
from datetime import datetime

app = FastAPI(title="Mock CRM Service")

@app.get("/")
def root():
    return {"service": "CRM Mock API", "version": "1.0.0", "endpoints": ["/customers", "/leads", "/opportunities", "/health"]}

@app.get("/customers")
def get_customers():
    return [
        {"id": "CUS-001", "name": "Acme Corporation", "email": "contact@acme.com", "tier": "enterprise", "revenue": 500000, "industry": "Manufacturing"},
        {"id": "CUS-002", "name": "TechStart Inc", "email": "info@techstart.io", "tier": "startup", "revenue": 50000, "industry": "Technology"},
        {"id": "CUS-003", "name": "Global Industries", "email": "sales@global.com", "tier": "enterprise", "revenue": 1200000, "industry": "Retail"},
        {"id": "CUS-004", "name": "DataFlow LLC", "email": "hello@dataflow.co", "tier": "professional", "revenue": 150000, "industry": "Finance"},
        {"id": "CUS-005", "name": "CloudNine Systems", "email": "support@cloudnine.io", "tier": "enterprise", "revenue": 800000, "industry": "Healthcare"}
    ]

@app.get("/leads")
def get_leads():
    return [
        {"id": "LEAD-001", "company": "NewCo Ventures", "contact": "John Smith", "email": "john@newco.com", "status": "qualified", "score": 85},
        {"id": "LEAD-002", "company": "FutureTech Labs", "contact": "Jane Doe", "email": "jane@futuretech.io", "status": "contacted", "score": 72},
        {"id": "LEAD-003", "company": "Innovate Inc", "contact": "Bob Wilson", "email": "bob@innovate.com", "status": "new", "score": 45},
        {"id": "LEAD-004", "company": "Scale Solutions", "contact": "Alice Brown", "email": "alice@scale.co", "status": "qualified", "score": 90}
    ]

@app.get("/opportunities")
def get_opportunities():
    return [
        {"id": "OPP-001", "name": "Enterprise Deal - Acme", "value": 250000, "stage": "negotiation", "probability": 75},
        {"id": "OPP-002", "name": "Platform Migration - Global", "value": 500000, "stage": "proposal", "probability": 50},
        {"id": "OPP-003", "name": "API Integration - CloudNine", "value": 100000, "stage": "closed-won", "probability": 100}
    ]

@app.get("/health")
def health():
    return {"status": "healthy", "service": "crm-mock", "timestamp": datetime.utcnow().isoformat()}
