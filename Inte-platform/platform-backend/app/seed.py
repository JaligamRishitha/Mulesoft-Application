from sqlalchemy.orm import Session
from app.database import SessionLocal, engine, Base
from app.models import User, Integration, IntegrationLog, APIEndpoint, APIKey, Connector, UserRole, IntegrationStatus, ConnectorType, ConnectorStatus
from app.auth import get_password_hash
import secrets
from datetime import datetime, timedelta

def seed_database():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    
    # Check if already seeded
    if db.query(User).filter(User.email == "admin@mulesoft.io").first():
        print("Database already seeded")
        db.close()
        return
    
    # Create Users
    admin = User(email="admin@mulesoft.io", hashed_password=get_password_hash("admin123"), full_name="Admin User", role=UserRole.ADMIN)
    dev = User(email="developer@mulesoft.io", hashed_password=get_password_hash("dev123"), full_name="John Developer", role=UserRole.DEVELOPER)
    db.add_all([admin, dev])
    db.commit()
    db.refresh(admin)
    
    # Create Salesforce Integration (basic)
    integration = Integration(
        name="External Salesforce Integration",
        description="Real-time integration with external Salesforce application on port 5173",
        flow_config='routes:\n  - from: "rest:get:/api/cases/external/cases"\n    process: "salesforceDataProcessor"\n    to: "http://host.docker.internal:5173/api/cases"',
        status=IntegrationStatus.DEPLOYED,
        owner_id=admin.id
    )
    db.add(integration)
    db.commit()

    # Create Salesforce to SAP Integration with Transform
    sf_to_sap_integration = Integration(
        name="Salesforce Case to SAP Service Request",
        description="Transform Salesforce Case events to SAP IDoc XML format and send to SAP ERP",
        flow_config='''routes:
  - from: "salesforce:cases"
    description: "Fetch Salesforce Case events"
    transform:
      type: "sap_idoc"
      idoc_type: "SRCLST"
      include_metadata: true
    to: "sap:service-requests"
    error_handler: "dead-letter-queue"''',
        status=IntegrationStatus.DRAFT,
        owner_id=admin.id
    )
    db.add(sf_to_sap_integration)
    db.commit()
    
    # Create Salesforce Connector pointing to external app on port 5173
    salesforce_connector = Connector(
        name="External Salesforce App",
        type=ConnectorType.SALESFORCE,
        description="External Salesforce application connector",
        config={
            "instance_url": "http://host.docker.internal:5173",
            "client_id": "external_app",
            "client_secret": "external_secret",
            "username": "admin",
            "password": "admin123",
            "security_token": "",
            "auth_endpoint": "/api/auth/login",
            "cases_endpoint": "/api/cases"
        },
        status=ConnectorStatus.ACTIVE,
        owner_id=admin.id,
        last_tested=datetime.utcnow()
    )
    db.add(salesforce_connector)
    db.commit()

    # Create SAP Connector pointing to external app on port 2004
    sap_connector = Connector(
        name="SAP ERP System",
        type=ConnectorType.SAP,
        description="SAP ERP connector for electricity load requests",
        config={
            "host": "host.docker.internal",
            "port": "2004",
            "base_url": "http://host.docker.internal:2004",
            "endpoints": {
                "load_request_xml": "/api/integration/mulesoft/load-request/xml",
                "load_request_json": "/api/integration/mulesoft/load-request",
                "webhook": "/api/integration/webhook"
            },
            "api_type": "REST",
            "content_type": "application/xml",
            "partner_number": "SALESFORCE"
        },
        status=ConnectorStatus.ACTIVE,
        owner_id=admin.id,
        last_tested=datetime.utcnow()
    )
    db.add(sap_connector)
    db.commit()

    print("Database seeded successfully!")
    print("\nTest Accounts:")
    print("  admin@mulesoft.io / admin123")
    print("  developer@mulesoft.io / dev123")
    print("\nIntegrations Created:")
    print("  1. External Salesforce Integration - DEPLOYED")
    print("  2. Salesforce Case to SAP Service Request - DRAFT (with transform)")
    print("\nConnectors Created:")
    print("  1. External Salesforce App (port 5173) - ACTIVE")
    print("  2. SAP ERP System (port 2004) - ACTIVE")
    print("\nSAP Integration Endpoints:")
    print("  POST /api/sap/send-load-request - Send ElectricityLoadRequest XML to SAP")
    print("  POST /api/sap/preview-xml - Preview XML transformation")
    print("  GET  /api/sap/test-connection - Test SAP connection")
    print("\nTransform API Endpoints:")
    print("  POST /api/transform/preview - Preview JSON to XML transformation")
    print("  POST /api/transform/execute - Execute transformation")
    print("  GET  /api/transform/templates - Get available templates")
    print("\nSAP Target Endpoint:")
    print("  http://localhost:2004/api/integration/mulesoft/load-request/xml")
    
    db.close()

if __name__ == "__main__":
    seed_database()
