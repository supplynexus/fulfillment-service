"""
Security utilities for authentication and data encryption
"""

import base64
from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from cryptography.fernet import Fernet
import hashlib
import os

from app.core.database import get_async_db
from app.models.user import User

# OAuth2 scheme for JWT tokens (kept for compatibility but not used)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


# Encryption utilities for sensitive data
def get_encryption_key() -> bytes:
    """Get or generate encryption key for sensitive data"""
    # Use a combination of environment variables and system info as base
    key_base = (
        os.getenv("ENCRYPTION_SALT", "default-encryption-salt") +
        os.getenv("ENVIRONMENT", "dev") +
        "SupplyNexus"
    ).encode()
    
    # Generate a 32-byte key using SHA-256
    key = hashlib.sha256(key_base).digest()
    # Convert to base64 for Fernet
    return base64.urlsafe_b64encode(key)


def encrypt_data(data: str) -> str:
    """Encrypt sensitive data"""
    key = get_encryption_key()
    f = Fernet(key)
    encrypted_data = f.encrypt(data.encode())
    return encrypted_data.decode()


def decrypt_data(encrypted_data: str) -> str:
    """Decrypt sensitive data"""
    key = get_encryption_key()
    f = Fernet(key)
    decrypted_data = f.decrypt(encrypted_data.encode())
    return decrypted_data.decode()
