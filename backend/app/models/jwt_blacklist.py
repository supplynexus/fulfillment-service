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
    tenant_id = Column(Integer, nullable=False, index=True)  # For multi-tenant
    
    # Expiration
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    
    # Reason for blacklisting
    reason = Column(Text, nullable=True)  # "logout", "security", "expired"
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        # Indexes will be handled by Alembic migration
    )
