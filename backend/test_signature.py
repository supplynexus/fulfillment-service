#!/usr/bin/env python3
"""
测试签名生成和验证
"""
import asyncio
import sys
import os
import base64
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text
from app.core.config import settings

async def test_signature():
    """测试签名生成和验证"""
    
    # 读取前端私钥
    private_key_path = "../frontend/keys/impeach_private_key.pem"
    with open(private_key_path, 'r') as f:
        private_key_pem = f.read()
    
    print("🔑 读取前端私钥文件:", private_key_path)
    
    # 加载私钥
    private_key = serialization.load_pem_private_key(
        private_key_pem.encode('utf-8'),
        password=None,
        backend=default_backend()
    )
    
    print("✅ 前端私钥加载成功")
    
    # 生成公钥
    public_key = private_key.public_key()
    public_key_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode('utf-8')
    
    print("🔑 生成公钥:")
    print(public_key_pem)
    
    # 测试签名生成
    username = "frontend@supplynexus.store"
    password = "Impeach@2025"
    tenant_name = "impeach"
    timestamp = 1760660697
    nonce = "bqwz98mnzt"
    backend_path = "/api/v1/auth/login"
    body = f"username={username}&password={password}&tenant_name={tenant_name}"
    signature_string = f"POST{backend_path}{timestamp}{nonce}{tenant_name}{body}"
    
    print(f"\n🔍 签名字符串: {signature_string}")
    print(f"📏 签名字符串长度: {len(signature_string)}")
    
    # 生成签名
    signature = private_key.sign(
        signature_string.encode('utf-8'),
        padding.PKCS1v15(),
        hashes.SHA256()
    )
    signature_b64 = base64.b64encode(signature).decode('utf-8')
    
    print(f"🔐 生成的签名: {signature_b64}")
    print(f"📏 签名长度: {len(signature_b64)}")
    
    # 验证签名
    try:
        public_key.verify(
            signature,
            signature_string.encode('utf-8'),
            padding.PKCS1v15(),
            hashes.SHA256()
        )
        print("✅ 签名验证成功")
    except Exception as e:
        print(f"❌ 签名验证失败: {e}")
    
    # 检查数据库中的公钥
    engine = create_engine(settings.DATABASE_URL.replace('+asyncpg', ''))
    with engine.connect() as conn:
        result = conn.execute(text("SELECT public_key FROM tenants WHERE name = 'impeach'"))
        row = result.fetchone()
        if row:
            db_public_key_pem = row[0]
            print(f"\n🗄️ 数据库中的公钥:")
            print(db_public_key_pem)
            
            # 比较公钥
            if public_key_pem.strip() == db_public_key_pem.strip():
                print("✅ 公钥匹配")
            else:
                print("❌ 公钥不匹配")
                print("前端生成的公钥:")
                print(public_key_pem)
                print("数据库中的公钥:")
                print(db_public_key_pem)

if __name__ == "__main__":
    asyncio.run(test_signature())
