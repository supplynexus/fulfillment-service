"""
JWT utilities for token generation and validation
"""

import jwt
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from app.core.config import settings


class JWTUtils:
    """JWT工具类"""

    def __init__(self):
        self.secret_key = settings.SECRET_KEY
        self.algorithm = "HS256"

    def generate_access_token(
        self,
        user_id: int,
        tenant_id: int,
        email: str,
        tenant_name: str,
        expires_in: int = 3600,
    ) -> str:
        """生成访问令牌"""
        payload = {
            "sub": str(user_id),
            "tenant_id": tenant_id,
            "email": email,
            "tenant_name": tenant_name,
            "type": "access",
            "exp": datetime.utcnow() + timedelta(seconds=expires_in),
            "iat": datetime.utcnow(),
        }

        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def generate_refresh_token(
        self,
        user_id: int,
        tenant_id: int,
        email: str,
        tenant_name: str,
        expires_in: int = 86400 * 7,
    ) -> str:
        """生成刷新令牌"""
        payload = {
            "sub": str(user_id),
            "tenant_id": tenant_id,
            "email": email,
            "tenant_name": tenant_name,
            "type": "refresh",
            "exp": datetime.utcnow() + timedelta(seconds=expires_in),
            "iat": datetime.utcnow(),
        }

        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def verify_token(self, token: str) -> Dict[str, Any]:
        """验证令牌"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            raise ValueError("Token has expired")
        except jwt.InvalidTokenError:
            raise ValueError("Invalid token")

    def get_user_from_token(self, token: str) -> Dict[str, Any]:
        """从令牌中获取用户信息"""
        payload = self.verify_token(token)
        return {
            "user_id": int(payload["sub"]),
            "tenant_id": payload["tenant_id"],
            "email": payload["email"],
            "tenant_name": payload["tenant_name"],
            "type": payload["type"],
        }


# 创建全局实例
jwt_utils = JWTUtils()
