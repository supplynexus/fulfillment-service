"""
User key management model for asymmetric key authentication
"""

from sqlalchemy import Boolean, Column, Integer, String, DateTime, ForeignKey, Text, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.core.database import Base


class UserKey(Base):
    __tablename__ = "user_keys"

    id = Column(Integer, primary_key=True, index=True)
    
    # User identification
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Key information
    key_id = Column(String, unique=True, index=True, nullable=False)  # UUID for key identification
    public_key = Column(Text, nullable=False)  # User's public key (PEM format)
    key_type = Column(String, nullable=False, default="rsa")  # rsa, ed25519, etc.
    key_size = Column(Integer, nullable=True)  # Key size in bits
    
    # Key metadata
    name = Column(String, nullable=False)  # Human readable name
    description = Column(Text, nullable=True)
    
    # Status and security
    is_active = Column(Boolean, default=True)
    is_primary = Column(Boolean, default=False)  # Primary key for the user
    expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # Usage tracking
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    usage_count = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="user_keys")
