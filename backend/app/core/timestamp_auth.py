"""
Timestamp-based signature authentication service
"""

import hashlib
import hmac
import time
import secrets
import base64
import json
from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend
from fastapi import HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update



from app.models.user import User
from app.models.tenant import Tenant
from app.models.user_tenant import UserTenant
from app.core.redis_client import redis_client
from app.core.logging import RequestLogger


class TimestampAuthService:
    """Service for timestamp-based signature authentication"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.logger = RequestLogger(__name__)

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
        Verify timestamp-based signature for tenant authentication
        
        Returns:
            Tuple[bool, int, int, str, int]: (is_valid, tenant_id, user_id, nonce, timestamp)
        """
        self.logger.info(
            "Starting signature verification",
            tenant_hashid=tenant_hashid,
            has_signature=bool(signature),
            key_id=key_id
        )
        
        try:
            # Decode tenant ID from hashid
            from app.core.config import settings
            from hashids import Hashids
            
            hashids = Hashids(settings.HASHIDS_SALT, min_length=settings.HASHIDS_MIN_LENGTH)
            tenant_id = hashids.decode(tenant_hashid)
            
            if not tenant_id:
                self.logger.warning(
                    "Signature verification failed - invalid tenant hashid",
                    tenant_hashid=tenant_hashid
                )
                return False, 0, 0, "", 0
            
            tenant_id = tenant_id[0]  # hashids.decode returns a list
            self.logger.info(
                "Tenant ID decoded",
                tenant_hashid=tenant_hashid,
                tenant_id=tenant_id
            )
            
            # Get timestamp and nonce from headers
            timestamp_str = request.headers.get("X-Timestamp")
            nonce = request.headers.get("X-Nonce")
            
            if not timestamp_str or not nonce:
                self.logger.warning(
                    "Signature verification failed - missing timestamp or nonce",
                    tenant_id=tenant_id,
                    has_timestamp=bool(timestamp_str),
                    has_nonce=bool(nonce)
                )
                return False, 0, 0, "", 0
            
            try:
                timestamp = int(timestamp_str)
            except ValueError:
                self.logger.warning(
                    "Signature verification failed - invalid timestamp format",
                    tenant_id=tenant_id,
                    timestamp_str=timestamp_str
                )
                return False, 0, 0, "", 0
            
            self.logger.info(
                "Headers parsed",
                tenant_id=tenant_id,
                timestamp=timestamp,
                nonce=nonce
            )
            
            # Check timestamp validity (within 5 minutes)
            current_time = int(time.time())
            if abs(current_time - timestamp) > 300:  # 5 minutes
                self.logger.warning(
                    "Signature verification failed - timestamp expired",
                    tenant_id=tenant_id,
                    timestamp=timestamp,
                    current_time=current_time,
                    time_diff=abs(current_time - timestamp)
                )
                return False, 0, 0, "", 0
            
            # Check nonce reuse
            nonce_key = f"nonce:{tenant_id}:{nonce}"
            if await redis_client.is_blacklisted(nonce_key):
                self.logger.warning(
                    "Signature verification failed - nonce reused",
                    tenant_id=tenant_id,
                    nonce=nonce
                )
                return False, 0, 0, "", 0
            
            # Get tenant public key
            tenant_result = await self.db.execute(
                select(Tenant).where(Tenant.id == tenant_id)
            )
            tenant = tenant_result.scalar_one_or_none()
            
            if not tenant:
                self.logger.warning(
                    "Signature verification failed - tenant not found",
                    tenant_id=tenant_id
                )
                return False, 0, 0, "", 0
            
            if not tenant.public_key:
                self.logger.warning(
                    "Signature verification failed - tenant has no public key",
                    tenant_id=tenant_id,
                    tenant_name=tenant.name
                )
                return False, 0, 0, "", 0
            
            self.logger.info(
                "Tenant found",
                tenant_id=tenant_id,
                tenant_name=tenant.name,
                has_public_key=bool(tenant.public_key)
            )
            
            # Get request body
            body = await request.body()
            body_str = body.decode('utf-8') if body else ""
            
            self.logger.info(
                "Request body retrieved",
                tenant_id=tenant_id,
                body_length=len(body_str)
            )
            
            # Construct signature string
            method = request.method.upper()
            path = request.url.path
            signature_string = f"{method}{path}{timestamp}{nonce}{tenant_id}{body_str}"
            
            self.logger.info(
                "Signature string constructed",
                tenant_id=tenant_id,
                method=method,
                path=path,
                signature_string_length=len(signature_string)
            )
            
            # Verify signature
            try:
                # Load public key
                public_key = serialization.load_pem_public_key(
                    tenant.public_key.encode(),
                    backend=default_backend()
                )
                
                # Decode signature
                signature_bytes = base64.b64decode(signature)
                
                # Verify signature
                public_key.verify(
                    signature_bytes,
                    signature_string.encode(),
                    padding.PKCS1v15(),
                    hashes.SHA256()
                )
                
                self.logger.info(
                    "Signature verification successful",
                    tenant_id=tenant_id,
                    tenant_name=tenant.name
                )
                
                # Store nonce to prevent reuse
                await redis_client.add_to_blacklist(
                    nonce_key, 
                    datetime.utcnow() + timedelta(minutes=10),  # 10 minutes TTL
                    user_id=0,  # Not applicable for nonce
                    customer_id=None
                )
                
                return True, tenant_id, 0, nonce, timestamp
                
            except Exception as e:
                self.logger.error(
                    "Signature verification failed",
                    tenant_id=tenant_id,
                    tenant_name=tenant.name,
                    error=str(e),
                    error_type=type(e).__name__,
                    exc_info=True
                )
                return False, 0, 0, "", 0
                
        except Exception as e:
            self.logger.error(
                "Signature verification failed with exception",
                tenant_hashid=tenant_hashid,
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True
            )
            return False, 0, 0, "", 0
    
    async def verify_timestamp_signature_with_body(
        self,
        signature: str,
        tenant_hashid: str,
        timestamp: str,
        nonce: str,
        method: str,
        path: str,
        body: str
    ) -> Tuple[bool, int, int, str, int]:
        """
        Verify timestamp-based signature for tenant authentication with provided body
        
        Returns:
            Tuple[bool, int, int, str, int]: (is_valid, tenant_id, user_id, nonce, timestamp)
        """
        self.logger.info(
            "Starting signature verification with body",
            tenant_hashid=tenant_hashid,
            has_signature=bool(signature),
            method=method,
            path=path,
            body_length=len(body)
        )
        
        try:
            # Decode tenant ID from hashid
            from app.core.config import settings
            from hashids import Hashids
            
            hashids = Hashids(settings.HASHIDS_SALT, min_length=settings.HASHIDS_MIN_LENGTH)
            tenant_id = hashids.decode(tenant_hashid)
            
            if not tenant_id:
                self.logger.warning(
                    "Signature verification failed - invalid tenant hashid",
                    tenant_hashid=tenant_hashid
                )
                return False, 0, 0, "", 0
            
            tenant_id = tenant_id[0]  # hashids.decode returns a list
            self.logger.info(
                "Tenant ID decoded",
                tenant_hashid=tenant_hashid,
                tenant_id=tenant_id
            )
            
            # Parse timestamp
            try:
                timestamp_int = int(timestamp)
            except ValueError:
                self.logger.warning(
                    "Signature verification failed - invalid timestamp format",
                    tenant_id=tenant_id,
                    timestamp=timestamp
                )
                return False, 0, 0, "", 0
            
            self.logger.info(
                "Parameters parsed",
                tenant_id=tenant_id,
                timestamp=timestamp_int,
                nonce=nonce
            )
            
            # Check timestamp validity (within 5 minutes)
            current_time = int(time.time())
            if abs(current_time - timestamp_int) > 300:  # 5 minutes
                self.logger.warning(
                    "Signature verification failed - timestamp expired",
                    tenant_id=tenant_id,
                    timestamp=timestamp_int,
                    current_time=current_time,
                    time_diff=abs(current_time - timestamp_int)
                )
                return False, 0, 0, "", 0
            
            # Check nonce reuse
            nonce_key = f"nonce:{tenant_id}:{nonce}"
            if await redis_client.is_blacklisted(nonce_key):
                self.logger.warning(
                    "Signature verification failed - nonce reused",
                    tenant_id=tenant_id,
                    nonce=nonce
                )
                return False, 0, 0, "", 0
            
            # Get tenant public key
            tenant_result = await self.db.execute(
                select(Tenant).where(Tenant.id == tenant_id)
            )
            tenant = tenant_result.scalar_one_or_none()
            
            if not tenant:
                self.logger.warning(
                    "Signature verification failed - tenant not found",
                    tenant_id=tenant_id
                )
                return False, 0, 0, "", 0
            
            if not tenant.public_key:
                self.logger.warning(
                    "Signature verification failed - tenant has no public key",
                    tenant_id=tenant_id,
                    tenant_name=tenant.name
                )
                return False, 0, 0, "", 0
            
            self.logger.info(
                "Tenant found",
                tenant_id=tenant_id,
                tenant_name=tenant.name,
                has_public_key=bool(tenant.public_key)
            )
            
            # Construct signature string
            signature_string = f"{method.upper()}{path}{timestamp_int}{nonce}{tenant_id}{body}"
            
            self.logger.info(
                "Signature string constructed",
                tenant_id=tenant_id,
                method=method.upper(),
                path=path,
                signature_string_length=len(signature_string)
            )
            
            # Verify signature
            try:
                # Load public key
                public_key = serialization.load_pem_public_key(
                    tenant.public_key.encode(),
                    backend=default_backend()
                )
                
                # Decode signature
                signature_bytes = base64.b64decode(signature)
                
                # Verify signature
                public_key.verify(
                    signature_bytes,
                    signature_string.encode(),
                    padding.PKCS1v15(),
                    hashes.SHA256()
                )
                
                self.logger.info(
                    "Signature verification successful",
                    tenant_id=tenant_id,
                    tenant_name=tenant.name
                )
                
                # Store nonce to prevent reuse
                await redis_client.add_to_blacklist(
                    nonce_key, 
                    datetime.utcnow() + timedelta(minutes=10),  # 10 minutes TTL
                    user_id=0,  # Not applicable for nonce
                    customer_id=None
                )
                
                return True, tenant_id, 0, nonce, timestamp_int
                
            except Exception as e:
                self.logger.error(
                    "Signature verification failed",
                    tenant_id=tenant_id,
                    tenant_name=tenant.name,
                    error=str(e),
                    error_type=type(e).__name__,
                    exc_info=True
                )
                return False, 0, 0, "", 0
                
        except Exception as e:
            self.logger.error(
                "Signature verification failed with exception",
                tenant_hashid=tenant_hashid,
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True
            )
            return False, 0, 0, "", 0
    

    

