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
    name = Column(String(255), index=True)
    type = Column(Enum(ConnectorType))
    description = Column(Text)
    config = Column(JSON)  # Stores connection details (encrypted in production)
    status = Column(Enum(ConnectorStatus), default=ConnectorStatus.INACTIVE)
    last_tested = Column(DateTime)
    owner_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
