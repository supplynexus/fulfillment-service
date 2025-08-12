"""
Asymmetric key authentication service
"""

import jwt
import hashlib
import hmac
from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend
from fastapi import HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.models.user_key import UserKey
from app.models.system_key import SystemKey, SystemKeyType
from app.models.user import User
from app.models.tenant import Tenant
from app.models.user_tenant import UserTenant


class AsymmetricAuthService:
    """Service for asymmetric key authentication"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def verify_user_signature(
        self,
        user_id: int,
        signature: str,
        data: str,
        key_id: Optional[str] = None
    ) -> bool:
        """Verify signature using user's public key"""
        
        # Get user's public key
        query = select(UserKey).where(
            UserKey.user_id == user_id,
            UserKey.is_active == True
        )
        
        if key_id:
            query = query.where(UserKey.key_id == key_id)
        else:
            query = query.where(UserKey.is_primary == True)
        
        result = await self.db.execute(query)
        user_key = result.scalar_one_or_none()
        
        if not user_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User key not found"
            )
        
        try:
            # Load public key
            public_key = serialization.load_pem_public_key(
                user_key.public_key.encode(),
                backend=default_backend()
            )
            
            # Verify signature
            if user_key.key_type == "rsa":
                public_key.verify(
                    signature.encode(),
                    data.encode(),
                    padding.PKCS1v15(),
                    hashes.SHA256()
                )
            else:
                # Handle other key types
                raise NotImplementedError(f"Key type {user_key.key_type} not supported")
            
            # Update usage tracking
            user_key.last_used_at = datetime.utcnow()
            user_key.usage_count += 1
            await self.db.commit()
            
            return True
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Signature verification failed: {str(e)}"
            )
    
    async def create_system_signed_token(
        self,
        user_id: int,
        tenant_id: int,
        token_type: str = "access",
        expires_in: Optional[int] = None
    ) -> str:
        """Create JWT token signed with system's private key"""
        
        # Get current JWT signing key
        result = await self.db.execute(
            select(SystemKey).where(
                SystemKey.key_type == SystemKeyType.JWT_SIGNING,
                SystemKey.is_current == True,
                SystemKey.is_active == True
            )
        )
        system_key = result.scalar_one_or_none()
        
        if not system_key:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="No active JWT signing key found"
            )
        
        # Load private key
        private_key = serialization.load_pem_private_key(
            system_key.private_key_encrypted.encode(),
            password=None,  # Assuming key is not encrypted in DB
            backend=default_backend()
        )
        
        # Create token payload
        now = datetime.utcnow()
        if expires_in:
            expires_at = now + timedelta(seconds=expires_in)
        else:
            expires_at = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        
        payload = {
            "sub": str(user_id),
            "tenant_id": tenant_id,
            "type": token_type,
            "key_id": system_key.key_id,
            "iat": now,
            "exp": expires_at
        }
        
        # Sign token
        token = jwt.encode(
            payload,
            private_key,
            algorithm="RS256",
            headers={"kid": system_key.key_id}
        )
        
        # Update usage tracking
        system_key.last_used_at = datetime.utcnow()
        system_key.usage_count += 1
        await self.db.commit()
        
        return token
    
    async def verify_system_signed_token(
        self,
        token: str
    ) -> Tuple[User, Tenant]:
        """Verify JWT token signed with system's public key"""
        
        try:
            # Decode token header to get key ID
            header = jwt.get_unverified_header(token)
            key_id = header.get("kid")
            
            if not key_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token missing key ID"
                )
            
            # Get system's public key
            result = await self.db.execute(
                select(SystemKey).where(
                    SystemKey.key_id == key_id,
                    SystemKey.key_type == SystemKeyType.JWT_SIGNING,
                    SystemKey.is_active == True
                )
            )
            system_key = result.scalar_one_or_none()
            
            if not system_key:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid signing key"
                )
            
            # Load public key
            public_key = serialization.load_pem_public_key(
                system_key.public_key.encode(),
                backend=default_backend()
            )
            
            # Verify and decode token
            payload = jwt.decode(
                token,
                public_key,
                algorithms=["RS256"],
                options={"verify_signature": True}
            )
            
            # Get user and tenant
            user_result = await self.db.execute(
                select(User).where(User.id == int(payload["sub"]))
            )
            user = user_result.scalar_one_or_none()
            
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found"
                )
            
            tenant_result = await self.db.execute(
                select(Tenant).where(Tenant.id == payload["tenant_id"])
            )
            tenant = tenant_result.scalar_one_or_none()
            
            if not tenant:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Tenant not found"
                )
            
            # Verify user has access to this tenant
            user_tenant_result = await self.db.execute(
                select(UserTenant).where(
                    UserTenant.user_id == user.id,
                    UserTenant.tenant_id == tenant.id,
                    UserTenant.is_active == True
                )
            )
            user_tenant = user_tenant_result.scalar_one_or_none()
            
            if not user_tenant:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User does not have access to this tenant"
                )
            
            return user, tenant
            
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except jwt.InvalidTokenError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token: {str(e)}"
            )
    
    async def sign_webhook_payload(
        self,
        payload: str,
        webhook_type: str = "default"
    ) -> str:
        """Sign webhook payload with system's private key"""
        
        # Get current webhook signing key
        result = await self.db.execute(
            select(SystemKey).where(
                SystemKey.key_type == SystemKeyType.WEBHOOK_SIGNING,
                SystemKey.is_current == True,
                SystemKey.is_active == True
            )
        )
        system_key = result.scalar_one_or_none()
        
        if not system_key:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="No active webhook signing key found"
            )
        
        # Load private key
        private_key = serialization.load_pem_private_key(
            system_key.private_key_encrypted.encode(),
            password=None,
            backend=default_backend()
        )
        
        # Create signature
        signature = private_key.sign(
            payload.encode(),
            padding.PKCS1v15(),
            hashes.SHA256()
        )
        
        # Update usage tracking
        system_key.last_used_at = datetime.utcnow()
        system_key.usage_count += 1
        await self.db.commit()
        
        return signature.hex()
