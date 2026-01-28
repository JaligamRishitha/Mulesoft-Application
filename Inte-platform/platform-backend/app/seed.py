from sqlalchemy.orm import Session
from app.database import SessionLocal, engine, Base
from app.models import User, Integration, IntegrationLog, APIEndpoint, APIKey, Connector, UserRole, IntegrationStatus, ConnectorType, ConnectorStatus
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
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
        name="Remote Salesforce Integration",
        description="Real-time integration with remote Salesforce backend application",
        flow_config='routes:\n  - from: "rest:get:/api/cases/external/cases"\n    process: "salesforceDataProcessor"\n    to: "connector:salesforce:/api/cases"',
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
    
    # Create Salesforce Connector pointing to remote server
    salesforce_connector = Connector(
        name="Salesforce App",
        type=ConnectorType.SALESFORCE,
        description="Remote Salesforce backend application connector - User Account Creation Requests",
        config={
            "server_url": "http://salesforce-backend:8000"
        },
        status=ConnectorStatus.ACTIVE,
        owner_id=admin.id,
        last_tested=datetime.utcnow()
    )
    db.add(salesforce_connector)
    db.commit()

    # Create SAP Connector pointing to remote server
    sap_connector = Connector(
        name="SAP ERP System",
        type=ConnectorType.SAP,
        description="Remote SAP ERP backend application connector",
        config={
            "server_url": "http://host.docker.internal:2004"
        },
        status=ConnectorStatus.ACTIVE,
        owner_id=admin.id,
        last_tested=datetime.utcnow()
    )
    db.add(sap_connector)
    db.commit()

    # Create ServiceNow Connector pointing to remote server
    servicenow_connector = Connector(
        name="ServiceNow ITSM",
        type=ConnectorType.SERVICENOW,
        description="Remote ServiceNow ITSM application for tickets and approvals",
        config={
            "server_url": "http://servicenow-backend:4780"
        },
        status=ConnectorStatus.ACTIVE,
        owner_id=admin.id,
        last_tested=datetime.utcnow()
    )
    db.add(servicenow_connector)
    db.commit()

    # Create Salesforce to ServiceNow Integration
    sf_to_snow_integration = Integration(
        name="Salesforce to ServiceNow - User Account Requests",
        description="Fetch user account creation requests from Salesforce and send as tickets and approvals to ServiceNow ITSM",
        flow_config='''routes:
  - from: "salesforce:user-account-requests"
    description: "Fetch user account creation requests from Salesforce"
    transform:
      type: "servicenow_ticket"
      ticket_type: "incident"
    to: "servicenow:tickets"
    parallel:
      - transform:
          type: "servicenow_approval"
          approval_type: "user_account"
        to: "servicenow:approvals"
    error_handler: "dead-letter-queue"''',
        status=IntegrationStatus.DEPLOYED,
        owner_id=admin.id
    )
    db.add(sf_to_snow_integration)
    db.commit()

    print("Database seeded successfully!")
    print("\nTest Accounts:")
    print("  admin@mulesoft.io / admin123")
    print("  developer@mulesoft.io / dev123")
    print("\nIntegrations Created:")
    print("  1. Remote Salesforce Integration - DEPLOYED")
    print("  2. Salesforce Case to SAP Service Request - DRAFT (with transform)")
    print("  3. Salesforce to ServiceNow - User Account Requests - DEPLOYED")
    print("\nConnectors Created:")
    print("  1. Salesforce App (http://salesforce-backend:8000) - ACTIVE")
    print("  2. SAP ERP System (server_url configured) - ACTIVE")
    print("  3. ServiceNow ITSM (http://servicenow-backend:4780) - ACTIVE")
    print("\nServiceNow Integration Endpoints:")
    print("  POST /api/servicenow/send-ticket - Send ticket to ServiceNow")
    print("  POST /api/servicenow/send-approval - Send approval to ServiceNow")
    print("  POST /api/servicenow/send-ticket-and-approval - Send both")
    print("  GET  /api/servicenow/test-connection - Test ServiceNow connection")
    print("\nSAP Integration Endpoints:")
    print("  POST /api/sap/send-load-request - Send ElectricityLoadRequest XML to SAP")
    print("  POST /api/sap/preview-xml - Preview XML transformation")
    print("  GET  /api/sap/test-connection - Test SAP connection")
    print("\nTransform API Endpoints:")
    print("  POST /api/transform/preview - Preview JSON to XML transformation")
    print("  POST /api/transform/execute - Execute transformation")
    print("  GET  /api/transform/templates - Get available templates")
    
    db.close()

if __name__ == "__main__":
    seed_database()
