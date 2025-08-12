"""
System key management model for our system's asymmetric keys
"""

from sqlalchemy import Boolean, Column, Integer, String, DateTime, Text, JSON, Enum
from sqlalchemy.sql import func
import enum

from app.core.database import Base


class SystemKeyType(enum.Enum):
    """System key types for different purposes"""
    JWT_SIGNING = "jwt_signing"  # For JWT token signing
    API_SIGNING = "api_signing"  # For API request signing
    WEBHOOK_SIGNING = "webhook_signing"  # For webhook signing


class SystemKey(Base):
    __tablename__ = "system_keys"

    id = Column(Integer, primary_key=True, index=True)
    
    # Key identification
    key_id = Column(String, unique=True, index=True, nullable=False)  # UUID for key identification
    key_type = Column(Enum(SystemKeyType), nullable=False)
    
    # Key information
    public_key = Column(Text, nullable=False)  # Our public key (PEM format)
    private_key_encrypted = Column(Text, nullable=False)  # Encrypted private key
    key_type_algorithm = Column(String, nullable=False, default="rsa")  # rsa, ed25519, etc.
    key_size = Column(Integer, nullable=True)  # Key size in bits
    
    # Key metadata
    name = Column(String, nullable=False)  # Human readable name
    description = Column(Text, nullable=True)
    
    # Status and security
    is_active = Column(Boolean, default=True)
    is_current = Column(Boolean, default=False)  # Current key for this type
    expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # Rotation information
    rotation_date = Column(DateTime(timezone=True), nullable=True)
    replaced_by_key_id = Column(String, nullable=True)  # Key that replaced this one
    
    # Usage tracking
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    usage_count = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
