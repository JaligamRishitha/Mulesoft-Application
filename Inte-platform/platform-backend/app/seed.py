from sqlalchemy.orm import Session
from app.database import SessionLocal, engine, Base
from app.models import User, Integration, IntegrationLog, APIEndpoint, APIKey, UserRole, IntegrationStatus
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
    
    # Create Integrations
    integrations = [
        Integration(name="SAP to Salesforce Sync", description="Real-time customer data sync between SAP ERP and Salesforce CRM", 
                    flow_config='routes:\n  - from: "timer:sync?period=60000"\n    to: "http://crm-api/customers"', 
                    status=IntegrationStatus.DEPLOYED, owner_id=admin.id),
        Integration(name="Order Processing Pipeline", description="Process orders from e-commerce to ERP", 
                    flow_config='routes:\n  - from: "kafka:orders"\n    to: "http://erp-api/orders"', 
                    status=IntegrationStatus.DEPLOYED, owner_id=admin.id),
        Integration(name="Inventory Alert System", description="Monitor inventory and send low stock alerts", 
                    flow_config='routes:\n  - from: "timer:check?period=300000"\n    to: "http://erp-api/inventory"', 
                    status=IntegrationStatus.STOPPED, owner_id=admin.id),
        Integration(name="Payment Gateway Integration", description="Connect payment processor with accounting", 
                    flow_config='routes:\n  - from: "webhook:payments"\n    to: "http://accounting-api/transactions"', 
                    status=IntegrationStatus.DEPLOYED, owner_id=admin.id),
        Integration(name="Customer 360 Aggregator", description="Aggregate customer data from multiple sources", 
                    flow_config='routes:\n  - from: "direct:aggregate"\n    multicast: ["crm", "erp", "support"]', 
                    status=IntegrationStatus.ERROR, owner_id=admin.id),
    ]
    db.add_all(integrations)
    db.commit()
    
    # Create Integration Logs
    logs = [
        IntegrationLog(integration_id=1, level="INFO", message="Integration started successfully", timestamp=datetime.utcnow() - timedelta(hours=2)),
        IntegrationLog(integration_id=1, level="INFO", message="Synced 150 customer records", timestamp=datetime.utcnow() - timedelta(hours=1)),
        IntegrationLog(integration_id=1, level="WARN", message="Slow response from SAP endpoint (2.3s)", timestamp=datetime.utcnow() - timedelta(minutes=30)),
        IntegrationLog(integration_id=2, level="INFO", message="Processed 45 orders", timestamp=datetime.utcnow() - timedelta(minutes=45)),
        IntegrationLog(integration_id=5, level="ERROR", message="Connection refused: CRM API unavailable", timestamp=datetime.utcnow() - timedelta(minutes=10)),
        IntegrationLog(integration_id=5, level="ERROR", message="Retry attempt 3/3 failed", timestamp=datetime.utcnow() - timedelta(minutes=5)),
    ]
    db.add_all(logs)
    db.commit()
    
    # Create API Endpoints
    endpoints = [
        APIEndpoint(name="Customer API", path="/api/v1/customers", method="GET", rate_limit=100, requires_auth=True),
        APIEndpoint(name="Create Customer", path="/api/v1/customers", method="POST", rate_limit=50, requires_auth=True),
        APIEndpoint(name="Orders API", path="/api/v1/orders", method="GET", rate_limit=200, requires_auth=True),
        APIEndpoint(name="Submit Order", path="/api/v1/orders", method="POST", rate_limit=100, requires_auth=True, ip_whitelist=["10.0.0.0/8"]),
        APIEndpoint(name="Inventory Check", path="/api/v1/inventory", method="GET", rate_limit=500, requires_auth=False),
        APIEndpoint(name="Webhook Receiver", path="/api/v1/webhooks/payments", method="POST", rate_limit=1000, requires_auth=True),
        APIEndpoint(name="Health Check", path="/api/v1/health", method="GET", rate_limit=1000, requires_auth=False),
    ]
    db.add_all(endpoints)
    db.commit()
    
    # Create API Keys
    api_keys = [
        APIKey(key=secrets.token_hex(32), name="Production App Key", user_id=admin.id, is_active=True),
        APIKey(key=secrets.token_hex(32), name="Mobile App Key", user_id=admin.id, is_active=True),
        APIKey(key=secrets.token_hex(32), name="Partner Integration Key", user_id=admin.id, is_active=True),
        APIKey(key=secrets.token_hex(32), name="Legacy System Key (Revoked)", user_id=admin.id, is_active=False),
    ]
    db.add_all(api_keys)
    db.commit()
    
    print("Database seeded successfully!")
    print("\nTest Accounts:")
    print("  admin@mulesoft.io / admin123")
    print("  developer@mulesoft.io / dev123")
    
    db.close()

if __name__ == "__main__":
    seed_database()
