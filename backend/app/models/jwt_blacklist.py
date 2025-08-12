"""
JWT Blacklist model for token invalidation
"""

from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.sql import func

from app.core.database import Base


class JwtBlacklist(Base):
    __tablename__ = "jwt_blacklist"

    id = Column(Integer, primary_key=True, index=True)
    
    # Token information
    token_hash = Column(String, nullable=False, index=True)  # Hashed JWT token
    token_type = Column(String, nullable=False)  # "access" or "refresh"
    
    # User information
    user_id = Column(Integer, nullable=False, index=True)
    customer_id = Column(Integer, nullable=True, index=True)  # For multi-tenant
    
    # Expiration
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    
    # Reason for blacklisting
    reason = Column(Text, nullable=True)  # "logout", "security", "expired"
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    class Config:
        indexes = [
            ("token_hash", "token_type"),
            ("user_id", "customer_id"),
            ("expires_at",)
        ]
