"""
User service for business logic
"""

from typing import Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.auth import hash_password, verify_password, is_password_strong
from app.models.user import User


class UserService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get(self, id: int) -> Optional[User]:
        """Get user by ID"""
        result = await self.db.execute(select(User).where(User.id == id))
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_by_email_and_tenant(self, email: str, tenant_id: int) -> Optional[User]:
        """Get user by email and tenant ID (handling many-to-many relationship)"""
        from app.models.user_tenant import UserTenant
        
        # Join users with user_tenants to find user in specific tenant
        result = await self.db.execute(
            select(User)
            .join(UserTenant, User.id == UserTenant.user_id)
            .where(User.email == email, UserTenant.tenant_id == tenant_id, UserTenant.is_active == True)
        )
        return result.scalar_one_or_none()

    async def verify_password(self, password: str, hashed_password: str) -> bool:
        """Verify password against hashed password"""
        return verify_password(password, hashed_password)

    async def create(self, obj_in: dict) -> Tuple[Optional[User], str]:
        """
        Create new user with password validation
        
        Args:
            obj_in: Dictionary containing user data including 'password'
            
        Returns:
            Tuple: (user: Optional[User], message: str)
        """
        # Check password strength
        is_strong, message = is_password_strong(obj_in["password"])
        if not is_strong:
            return None, message
        
        # Hash the password
        hashed_password = hash_password(obj_in["password"])
        
        # Create user
        db_user = User(
            email=obj_in["email"],
            hashed_password=hashed_password,
            full_name=obj_in.get("full_name"),
            is_active=obj_in.get("is_active", True),
            is_superuser=obj_in.get("is_superuser", False),
            password_changed_at=func.now(),
        )
        
        self.db.add(db_user)
        await self.db.commit()
        await self.db.refresh(db_user)
        return db_user, "User created successfully"

    async def authenticate(self, email: str, password: str) -> Tuple[Optional[User], str]:
        """
        Authenticate user with email and password
        
        Args:
            email: User's email
            password: Plain text password
            
        Returns:
            Tuple: (user: Optional[User], message: str)
        """
        user = await self.get_by_email(email=email)
        if not user:
            return None, "User not found"
        
        # Check if account is locked
        if user.is_locked:
            return None, "Account is temporarily locked due to failed login attempts"
        
        # Check if password is expired
        if user.is_password_expired:
            return None, "Password has expired"
        
        # Verify password
        if not user.verify_password(password):
            # Record failed login attempt
            user.record_failed_login()
            await self.db.commit()
            return None, "Invalid password"
        
        # Record successful login
        user.record_successful_login()
        await self.db.commit()
        
        return user, "Authentication successful"

    async def change_password(self, user_id: int, current_password: str, new_password: str) -> Tuple[bool, str]:
        """
        Change user password
        
        Args:
            user_id: User ID
            current_password: Current password for verification
            new_password: New password to set
            
        Returns:
            Tuple: (success: bool, message: str)
        """
        user = await self.get(user_id)
        if not user:
            return False, "User not found"
        
        # Verify current password
        if not user.verify_password(current_password):
            return False, "Current password is incorrect"
        
        # Set new password
        success, message = user.set_password(new_password)
        if success:
            await self.db.commit()
        
        return success, message

    async def reset_password(self, user_id: int, new_password: str) -> Tuple[bool, str]:
        """
        Reset user password (admin function)
        
        Args:
            user_id: User ID
            new_password: New password to set
            
        Returns:
            Tuple: (success: bool, message: str)
        """
        user = await self.get(user_id)
        if not user:
            return False, "User not found"
        
        # Set new password
        success, message = user.set_password(new_password)
        if success:
            await self.db.commit()
        
        return success, message

    async def is_active(self, user: User) -> bool:
        """Check if user is active"""
        return user.is_active

    async def is_superuser(self, user: User) -> bool:
        """Check if user is superuser"""
        return user.is_superuser

    async def lock_user(self, user_id: int, duration_minutes: int = 30) -> Tuple[bool, str]:
        """
        Lock user account
        
        Args:
            user_id: User ID
            duration_minutes: Lock duration in minutes
            
        Returns:
            Tuple: (success: bool, message: str)
        """
        user = await self.get(user_id)
        if not user:
            return False, "User not found"
        
        user.locked_until = func.now() + timedelta(minutes=duration_minutes)
        await self.db.commit()
        
        return True, f"User locked for {duration_minutes} minutes"

    async def unlock_user(self, user_id: int) -> Tuple[bool, str]:
        """
        Unlock user account
        
        Args:
            user_id: User ID
            
        Returns:
            Tuple: (success: bool, message: str)
        """
        user = await self.get(user_id)
        if not user:
            return False, "User not found"
        
        user.locked_until = None
        user.failed_login_attempts = 0
        await self.db.commit()
        
        return True, "User unlocked successfully"
