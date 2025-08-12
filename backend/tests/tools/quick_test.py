#!/usr/bin/env python3
"""
Quick Test Script for Authentication
快速测试脚本
"""

import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_path))

from signature_generator import SignatureGenerator
from app.core.hashids_utils import encode_tenant_id, encode_user_id


def quick_test():
    """快速测试"""
    print("=== 快速认证测试 ===\n")
    
    # 创建签名生成器
    generator = SignatureGenerator()
    generator.generate_key_pair()
    
    # 测试数据
    tenant_id = 1  # impeach
    user_id = 1    # 测试用户
    
    # 生成签名
    signature = generator.create_signature(
        method="GET",
        path="/api/v1/orders",
        tenant_id=tenant_id,
        user_id=user_id
    )
    
    # 输出结果
    print(f"Tenant ID: {tenant_id}")
    print(f"User ID: {user_id}")
    print(f"Tenant Hashid: {encode_tenant_id(tenant_id)}")
    print(f"User Hashid: {encode_user_id(user_id)}")
    print(f"\nX-Signature: {signature}")
    
    print(f"\ncurl命令:")
    print(f"curl -X GET 'http://localhost:8000/api/v1/orders' \\")
    print(f"  -H 'X-Signature: {signature}'")


if __name__ == "__main__":
    quick_test()
