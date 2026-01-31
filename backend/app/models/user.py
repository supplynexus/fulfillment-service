"""
User model
"""

from sqlalchemy import Boolean, Column, Integer, String, DateTime, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy.ext.hybrid import hybrid_property

from app.core.database import Base
from app.core.auth import hash_password, verify_password, is_password_strong


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Password security fields
    password_changed_at = Column(DateTime(timezone=True), nullable=True)
    password_expires_at = Column(DateTime(timezone=True), nullable=True)
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime(timezone=True), nullable=True)
    last_login_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user_tenants = relationship("UserTenant", back_populates="user")

    def set_password(self, password: str) -> tuple[bool, str]:
        """
        Set a new password for the user with validation.
        
        Args:
            password: Plain text password
            
        Returns:
            tuple: (success: bool, message: str)
        """
        # Check password strength
        is_strong, message = is_password_strong(password)
        if not is_strong:
            return False, message
        
        # Hash the password
        self.hashed_password = hash_password(password)
        self.password_changed_at = func.now()
        
        # Reset failed login attempts
        self.failed_login_attempts = 0
        self.locked_until = None
        
        return True, "Password updated successfully"

    def verify_password(self, password: str) -> bool:
        """
        Verify a password against the stored hash.
        
        Args:
            password: Plain text password to verify
            
        Returns:
            bool: True if password matches, False otherwise
        """
        return verify_password(password, self.hashed_password)

    @hybrid_property
    def is_locked(self) -> bool:
        """Check if the user account is locked due to failed login attempts."""
        if self.locked_until is None:
            return False
        return func.now() < self.locked_until

    @hybrid_property
    def is_password_expired(self) -> bool:
        """Check if the user's password has expired."""
        if self.password_expires_at is None:
            return False
        return func.now() > self.password_expires_at

    def record_failed_login(self) -> None:
        """Record a failed login attempt and potentially lock the account."""
        self.failed_login_attempts += 1
        
        # Lock account after 5 failed attempts for 30 minutes
        if self.failed_login_attempts >= 5:
            from datetime import timedelta
            self.locked_until = func.now() + timedelta(minutes=30)

    def record_successful_login(self) -> None:
        """Record a successful login."""
        self.failed_login_attempts = 0
        self.locked_until = None
        self.last_login_at = func.now()

    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}', is_active={self.is_active})>"
