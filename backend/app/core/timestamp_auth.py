"""
Timestamp-based signature authentication service
"""

import hashlib
import hmac
import time
import secrets
from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend
from fastapi import HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.models.user_key import UserKey
from app.models.system_key import SystemKey, SystemKeyType
from app.models.user import User
from app.models.tenant import Tenant
from app.models.user_tenant import UserTenant
from app.core.redis_client import redis_client


class TimestampAuthService:
    """Service for timestamp-based signature authentication"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    def generate_nonce(self) -> str:
        """Generate a random nonce"""
        return secrets.token_urlsafe(32)
    
    def create_signature_string(
        self,
        method: str,
        path: str,
        timestamp: int,
        nonce: str,
        body: str = ""
    ) -> str:
        """Create the string to be signed"""
        # Format: METHOD + PATH + TIMESTAMP + NONCE + BODY
        return f"{method.upper()}{path}{timestamp}{nonce}{body}"
    
    async def verify_timestamp_signature(
        self,
        request: Request,
        signature: str,
        timestamp: int,
        nonce: str,
        key_id: Optional[str] = None
    ) -> Tuple[User, Tenant]:
        """Verify timestamp-based signature"""
        
        # 1. Check timestamp validity (prevent replay attacks)
        current_time = int(time.time())
        time_diff = abs(current_time - timestamp)
        
        # Allow 5 minutes time difference
        if time_diff > 300:  # 5 minutes = 300 seconds
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Timestamp expired. Time difference: {time_diff} seconds"
            )
        
        # 2. Check nonce to prevent replay attacks
        # We'll check nonce after we identify the user
        nonce_key = f"used_nonce:{nonce}"
        is_used = await redis_client.client.get(nonce_key)
        if is_used:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Nonce already used"
            )
        
        # 3. Try to find user by key_id first, then by signature verification
        user_key = None
        if key_id:
            # Try to find user by key_id
            result = await self.db.execute(
                select(UserKey).where(
                    UserKey.key_id == key_id,
                    UserKey.is_active == True
                )
            )
            user_key = result.scalar_one_or_none()
        
        if not user_key:
            # If no key_id or key not found, we need to verify signature first
            # This is a more complex scenario - we might need to try multiple keys
            # For now, we'll require key_id in production
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Key ID required for signature verification"
            )
        
        # user_key is already found above
        
        # 4. Create signature string
        body = await request.body()
        body_str = body.decode() if body else ""
        
        signature_string = self.create_signature_string(
            method=request.method,
            path=str(request.url.path),
            timestamp=timestamp,
            nonce=nonce,
            body=body_str
        )
        
        # 5. Verify signature
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
                    signature_string.encode(),
                    padding.PKCS1v15(),
                    hashes.SHA256()
                )
            else:
                raise NotImplementedError(f"Key type {user_key.key_type} not supported")
            
            # 6. Mark nonce as used (with TTL to prevent memory leaks)
            await redis_client.client.setex(nonce_key, 600, "1")  # 10 minutes TTL
            
            # 7. Update usage tracking
            user_key.last_used_at = datetime.utcnow()
            user_key.usage_count += 1
            await self.db.commit()
            
            # 8. Get user and tenant information
            user_result = await self.db.execute(
                select(User).where(User.id == user_key.user_id)
            )
            user = user_result.scalar_one_or_none()
            
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found"
                )
            
            # Get user's active tenant (you might want to get this from the request or token)
            user_tenant_result = await self.db.execute(
                select(UserTenant).where(
                    UserTenant.user_id == user.id,
                    UserTenant.is_active == True
                ).limit(1)
            )
            user_tenant = user_tenant_result.scalar_one_or_none()
            
            if not user_tenant:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User has no active tenant"
                )
            
            # Get tenant
            tenant_result = await self.db.execute(
                select(Tenant).where(Tenant.id == user_tenant.tenant_id)
            )
            tenant = tenant_result.scalar_one_or_none()
            
            if not tenant:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Tenant not found"
                )
            
            return user, tenant
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Signature verification failed: {str(e)}"
            )
    
    async def create_system_signature(
        self,
        method: str,
        path: str,
        body: str = "",
        signature_type: SystemKeyType = SystemKeyType.API_SIGNING
    ) -> Dict[str, str]:
        """Create system signature for outgoing requests"""
        
        # Get current signing key
        result = await self.db.execute(
            select(SystemKey).where(
                SystemKey.key_type == signature_type,
                SystemKey.is_current == True,
                SystemKey.is_active == True
            )
        )
        system_key = result.scalar_one_or_none()
        
        if not system_key:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"No active {signature_type.value} key found"
            )
        
        # Generate timestamp and nonce
        timestamp = int(time.time())
        nonce = self.generate_nonce()
        
        # Create signature string
        signature_string = self.create_signature_string(
            method=method,
            path=path,
            timestamp=timestamp,
            nonce=nonce,
            body=body
        )
        
        # Load private key
        private_key = serialization.load_pem_private_key(
            system_key.private_key_encrypted.encode(),
            password=None,
            backend=default_backend()
        )
        
        # Create signature
        signature = private_key.sign(
            signature_string.encode(),
            padding.PKCS1v15(),
            hashes.SHA256()
        )
        
        # Update usage tracking
        system_key.last_used_at = datetime.utcnow()
        system_key.usage_count += 1
        await self.db.commit()
        
        return {
            "signature": signature.hex(),
            "timestamp": str(timestamp),
            "nonce": nonce,
            "key_id": system_key.key_id
        }
    
    async def verify_system_signature(
        self,
        request: Request,
        signature: str,
        timestamp: int,
        nonce: str,
        key_id: str
    ) -> bool:
        """Verify system signature for incoming requests"""
        
        # 1. Check timestamp validity
        current_time = int(time.time())
        time_diff = abs(current_time - timestamp)
        
        if time_diff > 300:  # 5 minutes
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Timestamp expired"
            )
        
        # 2. Check nonce
        nonce_key = f"system_nonce:{key_id}:{nonce}"
        is_used = await redis_client.client.get(nonce_key)
        if is_used:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Nonce already used"
            )
        
        # 3. Get system's public key
        result = await self.db.execute(
            select(SystemKey).where(
                SystemKey.key_id == key_id,
                SystemKey.is_active == True
            )
        )
        system_key = result.scalar_one_or_none()
        
        if not system_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid signing key"
            )
        
        # 4. Create signature string
        body = await request.body()
        body_str = body.decode() if body else ""
        
        signature_string = self.create_signature_string(
            method=request.method,
            path=str(request.url.path),
            timestamp=timestamp,
            nonce=nonce,
            body=body_str
        )
        
        # 5. Verify signature
        try:
            # Load public key
            public_key = serialization.load_pem_public_key(
                system_key.public_key.encode(),
                backend=default_backend()
            )
            
            # Verify signature
            public_key.verify(
                signature.encode(),
                signature_string.encode(),
                padding.PKCS1v15(),
                hashes.SHA256()
            )
            
            # 6. Mark nonce as used
            await redis_client.client.setex(nonce_key, 600, "1")
            
            return True
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Signature verification failed: {str(e)}"
            )
