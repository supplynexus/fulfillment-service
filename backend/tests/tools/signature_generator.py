#!/usr/bin/env python3
"""
Signature Generator Tool for Testing
生成签名工具，用于测试认证系统
"""

import os
import sys
import time
import secrets
import base64
import json
from pathlib import Path
from typing import Optional

# Add backend to path
backend_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_path))

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from app.core.hashids_utils import encode_tenant_id, encode_user_id


class SignatureGenerator:
    """签名生成器"""
    
    def __init__(self):
        self.private_key = None
        self.public_key = None
        self.key_id = "test_key_001"
    
    def generate_key_pair(self, key_size: int = 2048) -> tuple[str, str]:
        """生成RSA密钥对"""
        # 生成私钥
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=key_size
        )
        
        # 获取公钥
        public_key = private_key.public_key()
        
        # 序列化私钥
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        # 序列化公钥
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        
        self.private_key = private_key
        self.public_key = public_key
        
        return private_pem.decode(), public_pem.decode()
    
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
        """创建签名字符串"""
        # Format: METHOD + PATH + TIMESTAMP + NONCE + TENANT_ID + USER_ID + BODY
        user_part = f"{user_id}" if user_id else ""
        return f"{method.upper()}{path}{timestamp}{nonce}{tenant_id}{user_part}{body}"
    
    def sign_data(self, data: str) -> str:
        """使用私钥签名数据"""
        if not self.private_key:
            raise ValueError("Private key not generated")
        
        signature = self.private_key.sign(
            data.encode(),
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        
        return signature.hex()
    
    def create_signature(
        self,
        method: str,
        path: str,
        tenant_id: int,
        user_id: Optional[int] = None,
        body: str = "",
        timestamp: Optional[int] = None,
        nonce: Optional[str] = None
    ) -> str:
        """创建完整的签名"""
        # 生成时间戳和随机数
        if timestamp is None:
            timestamp = int(time.time())
        
        if nonce is None:
            nonce = secrets.token_hex(16)
        
        # 创建签名字符串
        signature_string = self.create_signature_string(
            method=method,
            path=path,
            timestamp=timestamp,
            nonce=nonce,
            tenant_id=tenant_id,
            user_id=user_id,
            body=body
        )
        
        # 签名
        signature = self.sign_data(signature_string)
        
        # 创建签名数据结构
        signature_data = {
            "timestamp": timestamp,
            "nonce": nonce,
            "tenant_id": tenant_id,
            "user_id": user_id,  # Optional
            "signature": signature,
            "key_id": self.key_id
        }
        
        # 编码为base64
        encoded_signature = base64.b64encode(
            json.dumps(signature_data).encode()
        ).decode()
        
        return encoded_signature
    
    def save_keys(self, private_key_path: str = "test_private_key.pem", 
                  public_key_path: str = "test_public_key.pem"):
        """保存密钥到文件"""
        if not self.private_key or not self.public_key:
            self.generate_key_pair()
        
        # 保存私钥
        with open(private_key_path, 'w') as f:
            f.write(self.private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ).decode())
        
        # 保存公钥
        with open(public_key_path, 'w') as f:
            f.write(self.public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            ).decode())
        
        print(f"Keys saved to {private_key_path} and {public_key_path}")


def main():
    """主函数 - 演示签名生成"""
    print("=== 签名生成器工具 ===\n")
    
    # 创建签名生成器
    generator = SignatureGenerator()
    
    # 生成密钥对
    print("1. 生成RSA密钥对...")
    private_pem, public_pem = generator.generate_key_pair()
    print("✅ 密钥对生成成功")
    
    # 保存密钥
    print("\n2. 保存密钥到文件...")
    generator.save_keys()
    
    # 演示签名生成
    print("\n3. 生成测试签名...")
    
    # 租户级API签名（只有tenant_id）
    tenant_signature = generator.create_signature(
        method="GET",
        path="/api/v1/orders",
        tenant_id=1,  # impeach租户
        body=""
    )
    
    print(f"租户级API签名 (tenant_id=1):")
    print(f"X-Signature: {tenant_signature}")
    
    # 用户级API签名（tenant_id + user_id）
    user_signature = generator.create_signature(
        method="GET",
        path="/api/v1/user/profile",
        tenant_id=1,  # impeach租户
        user_id=1,    # 用户ID
        body=""
    )
    
    print(f"\n用户级API签名 (tenant_id=1, user_id=1):")
    print(f"X-Signature: {user_signature}")
    
    # 使用hashids编码的ID
    print(f"\n4. 使用Hashids编码的ID...")
    tenant_hashid = encode_tenant_id(1)
    user_hashid = encode_user_id(1)
    
    print(f"Tenant ID 1 -> Hashid: {tenant_hashid}")
    print(f"User ID 1 -> Hashid: {user_hashid}")
    
    # 生成curl命令
    print(f"\n5. 生成curl测试命令...")
    
    print(f"\n# 租户级API测试")
    print(f"curl -X GET 'http://localhost:8000/api/v1/orders' \\")
    print(f"  -H 'X-Signature: {tenant_signature}'")
    
    print(f"\n# 用户级API测试")
    print(f"curl -X GET 'http://localhost:8000/api/v1/user/profile' \\")
    print(f"  -H 'X-Signature: {user_signature}'")
    
    print(f"\n# 所有环境统一认证")
    print(f"curl -X GET 'http://localhost:8000/api/v1/orders' \\")
    print(f"  -H 'X-Signature: {tenant_signature}'")
    
    print(f"\n=== 工具使用完成 ===")


if __name__ == "__main__":
    main()
