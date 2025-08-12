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
        tenant_id: int,
        user_id: Optional[int] = None,
        body: str = ""
    ) -> str:
        """Create the string to be signed"""
        # Format: METHOD + PATH + TIMESTAMP + NONCE + TENANT_ID + USER_ID + BODY
        user_part = f"{user_id}" if user_id else ""
        return f"{method.upper()}{path}{timestamp}{nonce}{tenant_id}{user_part}{body}"
    
    async def verify_timestamp_signature(
        self,
        request: Request,
        signature: str,
        tenant_hashid: str,
        key_id: Optional[str] = None
    ) -> Tuple[bool, int, int, str, int]:
        """
        Verify timestamp-based signature
        Args:
            request: FastAPI request object
            signature: X-Signature header value
            tenant_hashid: X-Tenant-ID header value (hashids encoded)
            key_id: Optional key ID to use
        Returns: (is_valid, tenant_id, user_id, nonce, timestamp)
        """
        """Verify timestamp-based signature"""
        
        # 1. Try to extract information from signature
        # For now, we'll use a simple approach - in production, you might want to use JWT or other structured format
        try:
            # Decode signature to extract information
            # This is a simplified approach - in real implementation, you might use JWT or structured format
            import base64
            import json
            
            # Assuming signature contains encoded information
            decoded_signature = base64.b64decode(signature).decode()
            signature_data = json.loads(decoded_signature)
            
            # Decode tenant ID from hashids
            from app.core.hashids_utils import decode_tenant_id
            tenant_id = decode_tenant_id(tenant_hashid)
            
            if not tenant_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid tenant ID"
                )
            
            timestamp = signature_data.get("timestamp")
            nonce = signature_data.get("nonce")
            user_id = signature_data.get("user_id")  # Optional
            actual_signature = signature_data.get("signature")
            
            if not all([timestamp, nonce, actual_signature]):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid signature format - missing required fields"
                )
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Failed to decode signature: {str(e)}"
            )
        
        # 2. Check timestamp validity (prevent replay attacks)
        current_time = int(time.time())
        time_diff = abs(current_time - timestamp)
        
        # Allow 5 minutes time difference
        if time_diff > 300:  # 5 minutes = 300 seconds
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Timestamp expired. Time difference: {time_diff} seconds"
            )
        
        # 3. Check nonce to prevent replay attacks
        nonce_key = f"used_nonce:{tenant_id}:{nonce}"
        is_used = await redis_client.client.get(nonce_key)
        if is_used:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Nonce already used"
            )
        
        # 4. Get user's public key (if user_id provided)
        if user_id:
            query = select(UserKey).where(
                UserKey.user_id == user_id,
                UserKey.is_active == True
            )
        else:
            # For tenant-only operations, we might use a different key or API key
            # For now, we'll require user_id for user key operations
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User ID required for user key authentication"
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
        
        # 5. Create signature string
        body = await request.body()
        body_str = body.decode() if body else ""
        
        signature_string = self.create_signature_string(
            method=request.method,
            path=str(request.url.path),
            timestamp=timestamp,
            nonce=nonce,
            tenant_id=tenant_id,
            user_id=user_id,
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
            
            return True, tenant_id, user_id, nonce, timestamp
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Signature verification failed: {str(e)}"
            )
    
    async def create_system_signature(
        self,
        method: str,
        path: str,
        tenant_id: int,
        user_id: Optional[int] = None,
        body: str = "",
        signature_type: SystemKeyType = SystemKeyType.API_SIGNING
    ) -> str:
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
            tenant_id=tenant_id,
            user_id=user_id,
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
        
        # Create structured signature with all information
        signature_data = {
            "timestamp": timestamp,
            "nonce": nonce,
            "tenant_id": tenant_id,
            "user_id": user_id,  # Optional
            "signature": signature.hex(),
            "key_id": system_key.key_id
        }
        
        # Encode as base64
        import base64
        import json
        encoded_signature = base64.b64encode(
            json.dumps(signature_data).encode()
        ).decode()
        
        # Update usage tracking
        system_key.last_used_at = datetime.utcnow()
        system_key.usage_count += 1
        await self.db.commit()
        
        return encoded_signature
    
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
