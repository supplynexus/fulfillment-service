"""
Authentication utilities - password hashing and verification

This module provides secure password hashing and verification using bcrypt.
bcrypt is a strong, slow hashing function designed specifically for password storage.
"""

import bcrypt
from typing import Optional


def hash_password(password: str, rounds: int = 12) -> str:
    """
    Hash a password using bcrypt with a unique salt.
    
    Args:
        password: Plain text password to hash
        rounds: Number of bcrypt rounds (default: 12, higher = more secure but slower)
    
    Returns:
        str: Complete hash string including salt and algorithm info
        
    Example:
        >>> hashed = hash_password("my_password")
        >>> print(hashed)
        '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj4J/HS.iQeO'
    """
    if not password:
        raise ValueError("Password cannot be empty")
    
    # Convert password to bytes
    password_bytes = password.encode('utf-8')
    
    # Generate salt and hash password
    # bcrypt automatically generates a unique salt for each password
    salt = bcrypt.gensalt(rounds=rounds)
    hashed = bcrypt.hashpw(password_bytes, salt)
    
    # Return the complete hash string (includes salt)
    return hashed.decode('utf-8')


def verify_password(password: str, stored_hash: str) -> bool:
    """
    Verify a password against its stored hash.
    
    Args:
        password: Plain text password to verify
        stored_hash: Complete hash string from database (includes salt)
    
    Returns:
        bool: True if password matches, False otherwise
        
    Example:
        >>> stored_hash = '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj4J/HS.iQeO'
        >>> is_valid = verify_password("my_password", stored_hash)
        >>> print(is_valid)
        True
    """
    if not password or not stored_hash:
        return False
    
    try:
        # Convert inputs to bytes
        password_bytes = password.encode('utf-8')
        stored_hash_bytes = stored_hash.encode('utf-8')
        
        # Verify password against stored hash
        # bcrypt automatically extracts salt from stored hash
        return bcrypt.checkpw(password_bytes, stored_hash_bytes)
    except Exception:
        # Return False for any verification errors
        return False


def is_password_strong(password: str) -> tuple[bool, str]:
    """
    Check if a password meets security requirements.
    
    Args:
        password: Plain text password to check
    
    Returns:
        tuple: (is_strong: bool, message: str)
        
    Requirements:
        - At least 8 characters long
        - Contains at least one uppercase letter
        - Contains at least one lowercase letter
        - Contains at least one digit
        - Contains at least one special character
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter"
    
    if not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter"
    
    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one digit"
    
    if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
        return False, "Password must contain at least one special character"
    
    return True, "Password meets security requirements"


# Backward compatibility functions (for existing code)
def get_password_hash(password: str) -> str:
    """Backward compatibility function - use hash_password instead"""
    return hash_password(password)


# Legacy support for passlib (if needed)
try:
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    
    def verify_password_legacy(plain_password: str, hashed_password: str) -> bool:
        """Legacy password verification using passlib"""
        return pwd_context.verify(plain_password, hashed_password)
        
except ImportError:
    # passlib not available, use pure bcrypt
    pass
