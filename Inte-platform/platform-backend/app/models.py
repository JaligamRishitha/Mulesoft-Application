from sqlalchemy import Column, Integer, String, DateTime, Boolean, Enum, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.database import Base

class UserRole(str, enum.Enum):
    ADMIN = "admin"
    DEVELOPER = "developer"
    VIEWER = "viewer"

class IntegrationStatus(str, enum.Enum):
    DRAFT = "draft"
    DEPLOYED = "deployed"
    STOPPED = "stopped"
    ERROR = "error"

class ConnectorType(str, enum.Enum):
    SAP = "sap"
    SALESFORCE = "salesforce"
    SERVICENOW = "servicenow"
    DATABASE = "database"
    HTTP = "http"
    SOAP = "soap"
    KAFKA = "kafka"
    FTP = "ftp"
    EMAIL = "email"
    AWS_S3 = "aws_s3"
    AZURE_BLOB = "azure_blob"

class ConnectorStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True)
    hashed_password = Column(String(255))
    full_name = Column(String(255))
    role = Column(Enum(UserRole), default=UserRole.DEVELOPER)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    integrations = relationship("Integration", back_populates="owner")
    api_keys = relationship("APIKey", back_populates="user")

class Integration(Base):
    __tablename__ = "integrations"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), index=True)
    description = Column(Text)
    flow_config = Column(Text)
    status = Column(Enum(IntegrationStatus), default=IntegrationStatus.DRAFT)
    owner_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    owner = relationship("User", back_populates="integrations")
    logs = relationship("IntegrationLog", back_populates="integration")

class IntegrationLog(Base):
    __tablename__ = "integration_logs"
    id = Column(Integer, primary_key=True, index=True)
    integration_id = Column(Integer, ForeignKey("integrations.id"))
    level = Column(String(20))
    message = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)
    integration = relationship("Integration", back_populates="logs")

class APIEndpoint(Base):
    __tablename__ = "api_endpoints"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255))
    path = Column(String(255))
    method = Column(String(10))
    rate_limit = Column(Integer, default=100)
    ip_whitelist = Column(JSON, default=list)
    requires_auth = Column(Boolean, default=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class APIKey(Base):
    __tablename__ = "api_keys"
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(64), unique=True, index=True)
    name = Column(String(255))
    user_id = Column(Integer, ForeignKey("users.id"))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User", back_populates="api_keys")


class Connector(Base):
    __tablename__ = "connectors"
    id = Column(Integer, primary_key=True, index=True)
    connector_name = Column(String(255), unique=True, index=True)
    connector_type = Column(String(50))
    connection_config = Column(JSON)  # Stores connection details (encrypted in production)
    credentials_ref = Column(String(255))
    status = Column(String(50), default="Active")
    health_check_url = Column(String(500))
    last_health_check = Column(DateTime)
    health_status = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class SalesforceCase(Base):
    __tablename__ = "salesforce_cases"
    id = Column(Integer, primary_key=True, index=True)
    salesforce_id = Column(String(18), unique=True, index=True)  # Salesforce 18-char ID
    case_number = Column(String(50))
    subject = Column(String(255))
    description = Column(Text)
    status = Column(String(50))
    priority = Column(String(50))
    origin = Column(String(50))
    account_id = Column(String(18))
    account_name = Column(String(255))
    contact_id = Column(String(18))
    contact_name = Column(String(255))
    owner_id = Column(String(18))
    owner_name = Column(String(255))
    created_date = Column(DateTime)
    closed_date = Column(DateTime)
    last_modified_date = Column(DateTime)
    synced_at = Column(DateTime, default=datetime.utcnow)
    raw_data = Column(JSON)  # Store complete Salesforce response


class PasswordResetTicket(Base):
    __tablename__ = "password_reset_tickets"
    id = Column(Integer, primary_key=True, index=True)
    correlation_id = Column(String(255), unique=True, index=True)
    servicenow_ticket_id = Column(String(255), index=True)
    sap_ticket_id = Column(String(255), index=True)
    username = Column(String(255))
    user_email = Column(String(255))
    requester_name = Column(String(255))
    requester_email = Column(String(255))
    reason = Column(Text)
    priority = Column(String(50))
    status = Column(String(50))  # pending, sent_to_sap, in_progress, completed, failed
    sap_status = Column(String(50))
    servicenow_updated = Column(Boolean, default=False)
    history = Column(JSON, default=list)  # List of status changes
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class UserCreationApproval(Base):
    __tablename__ = "user_creation_approvals"
    id = Column(Integer, primary_key=True, index=True)
    correlation_id = Column(String(255), unique=True, index=True)
    sap_username = Column(String(255), index=True)
    sap_roles = Column(JSON)
    servicenow_ticket_number = Column(String(255), index=True)
    servicenow_ticket_id = Column(String(255))
    approval_status = Column(String(50), default="pending")
    approved_by = Column(String(255))
    approved_at = Column(DateTime)
    rejection_reason = Column(Text)
    sap_event_id = Column(String(255))
    history = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
