"""
User service for business logic
"""

from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.auth import get_password_hash, verify_password
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

    async def create(self, obj_in: dict) -> User:
        """Create new user"""
        hashed_password = get_password_hash(obj_in["password"])
        db_user = User(
            email=obj_in["email"],
            hashed_password=hashed_password,
            full_name=obj_in.get("full_name"),
            is_active=obj_in.get("is_active", True),
            is_superuser=obj_in.get("is_superuser", False),
        )
        self.db.add(db_user)
        await self.db.commit()
        await self.db.refresh(db_user)
        return db_user

    async def authenticate(self, email: str, password: str) -> Optional[User]:
        """Authenticate user with email and password"""
        user = await self.get_by_email(email=email)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user

    async def is_active(self, user: User) -> bool:
        """Check if user is active"""
        return user.is_active

    async def is_superuser(self, user: User) -> bool:
        """Check if user is superuser"""
        return user.is_superuser
