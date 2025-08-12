"""
Hashids utilities for encoding/decoding IDs
"""

from hashids import Hashids
from app.core.config import settings


class HashidsEncoder:
    """Hashids encoder/decoder for ID obfuscation"""
    
    def __init__(self):
        self.hashids = Hashids(
            salt=settings.HASHIDS_SALT,
            min_length=settings.HASHIDS_MIN_LENGTH
        )
    
    def encode(self, *numbers: int) -> str:
        """Encode one or more integers to a hashid string"""
        return self.hashids.encode(*numbers)
    
    def decode(self, hashid: str) -> list[int]:
        """Decode a hashid string to a list of integers"""
        return self.hashids.decode(hashid)
    
    def encode_single(self, number: int) -> str:
        """Encode a single integer to a hashid string"""
        return self.hashids.encode(number)
    
    def decode_single(self, hashid: str) -> int:
        """Decode a hashid string to a single integer"""
        decoded = self.hashids.decode(hashid)
        return decoded[0] if decoded else None


# Global instance
hashids_encoder = HashidsEncoder()


def encode_id(number: int) -> str:
    """Encode a single ID to hashid"""
    return hashids_encoder.encode_single(number)


def decode_id(hashid: str) -> int:
    """Decode a hashid to ID"""
    return hashids_encoder.decode_single(hashid)


def encode_tenant_id(tenant_id: int) -> str:
    """Encode tenant ID to hashid"""
    return hashids_encoder.encode_single(tenant_id)


def decode_tenant_id(tenant_hashid: str) -> int:
    """Decode tenant hashid to ID"""
    return hashids_encoder.decode_single(tenant_hashid)


def encode_user_id(user_id: int) -> str:
    """Encode user ID to hashid"""
    return hashids_encoder.encode_single(user_id)


def decode_user_id(user_hashid: str) -> int:
    """Decode user hashid to ID"""
    return hashids_encoder.decode_single(user_hashid)
