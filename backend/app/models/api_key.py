"""
API Key model for external system authentication
"""

from sqlalchemy import Boolean, Column, Integer, String, DateTime, ForeignKey, Text, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.core.database import Base


class ApiKey(Base):
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, index=True)
    
    # Key information
    key_id = Column(String, unique=True, index=True, nullable=False)  # UUID for key identification
    key_hash = Column(String, nullable=False)  # Hashed API key
    secret_hash = Column(String, nullable=False)  # Hashed API secret
    
    # Ownership and permissions
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    name = Column(String, nullable=False)  # Human readable name
    description = Column(Text, nullable=True)
    
    # Permissions (JSON format)
    permissions = Column(JSON, nullable=False, default=dict)  # {"orders": ["read"], "products": ["read", "write"]}
    
    # Security settings
    is_active = Column(Boolean, default=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    
    # IP restrictions
    allowed_ips = Column(JSON, nullable=True)  # List of allowed IP addresses
    rate_limit = Column(Integer, default=1000)  # Requests per hour
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    customer = relationship("Customer", back_populates="api_keys")
    access_logs = relationship("ApiKeyAccessLog", back_populates="api_key")


class ApiKeyAccessLog(Base):
    __tablename__ = "api_key_access_logs"

    id = Column(Integer, primary_key=True, index=True)
    
    # Access information
    api_key_id = Column(Integer, ForeignKey("api_keys.id"), nullable=False)
    endpoint = Column(String, nullable=False)  # API endpoint accessed
    method = Column(String, nullable=False)  # HTTP method
    status_code = Column(Integer, nullable=False)  # Response status code
    
    # Request details
    ip_address = Column(String, nullable=False)
    user_agent = Column(String, nullable=True)
    request_data = Column(JSON, nullable=True)  # Request payload (sanitized)
    
    # Performance
    response_time = Column(Integer, nullable=True)  # Response time in milliseconds
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    api_key = relationship("ApiKey", back_populates="access_logs")
