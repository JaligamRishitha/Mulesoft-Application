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
    
    # Create only the Salesforce to SAP Integration
    integration = Integration(
        name="Salesforce to SAP Electricity Load", 
        description="Transform JSON electricity load requests from Salesforce to XML and send to SAP ERP", 
        flow_config='routes:\n  - from: "rest:post:/api/integration/mulesoft/load-request/xml"\n    process: "electricityLoadTransformer"\n    to: "http://host.docker.internal:8100/api/integration/mulesoft/load-request/xml"', 
        status=IntegrationStatus.DEPLOYED, 
        owner_id=admin.id
    )
    db.add(integration)
    db.commit()
    
    print("Database seeded successfully!")
    print("\nTest Accounts:")
    print("  admin@mulesoft.io / admin123")
    print("  developer@mulesoft.io / dev123")
    print("\nIntegration Created:")
    print("  Salesforce to SAP Electricity Load - DEPLOYED")
    
    db.close()

if __name__ == "__main__":
    seed_database()
