#!/usr/bin/env python3
"""
从现有私钥更新数据库公钥
"""

import asyncio
import sys
import os
from pathlib import Path
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# 添加项目根目录到 Python 路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.config import settings
from app.models.tenant import Tenant


async def update_tenant_public_key(tenant_name: str, private_key_file: str):
    """从私钥文件更新数据库公钥"""
    
    print(f"🔑 更新租户公钥")
    print(f"   租户: {tenant_name}")
    print(f"   私钥文件: {private_key_file}")
    print()
    
    try:
        # 读取私钥文件
        with open(private_key_file, 'r') as f:
            private_key_pem = f.read()
        
        print("✅ 私钥文件读取成功")
        
        # 从私钥生成公钥
        private_key = serialization.load_pem_private_key(
            private_key_pem.encode('utf-8'),
            password=None,
            backend=default_backend()
        )
        
        public_key = private_key.public_key()
        public_key_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode('utf-8')
        
        print("✅ 从私钥生成公钥成功")
        print()
        print("🔍 生成的公钥:")
        print(public_key_pem)
        print()
        
        # 创建数据库连接
        engine = create_async_engine(settings.DATABASE_URL)
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        
        async with async_session() as session:
            try:
                # 查找租户
                result = await session.execute(
                    select(Tenant).where(Tenant.name == tenant_name)
                )
                tenant = result.scalar_one_or_none()
                
                if not tenant:
                    print(f"❌ 租户 '{tenant_name}' 不存在")
                    return False
                
                # 更新公钥
                tenant.public_key = public_key_pem
                await session.commit()
                
                print(f"✅ 公钥已更新到数据库")
                print(f"   租户: {tenant.name} (ID: {tenant.id})")
                return True
                
            except Exception as e:
                await session.rollback()
                print(f"❌ 保存公钥到数据库失败: {e}")
                return False
            finally:
                await engine.dispose()
        
    except FileNotFoundError:
        print(f"❌ 私钥文件不存在: {private_key_file}")
        return False
    except Exception as e:
        print(f"❌ 错误: {e}")
        return False


def main():
    """主函数"""
    if len(sys.argv) != 3:
        print("用法: python update_tenant_public_key.py <tenant_name> <private_key_file>")
        print("示例: python update_tenant_public_key.py impeach ../frontend/keys/impeach_private_key.pem")
        sys.exit(1)
    
    tenant_name = sys.argv[1]
    private_key_file = sys.argv[2]
    
    success = asyncio.run(update_tenant_public_key(tenant_name, private_key_file))
    
    if success:
        print("🎯 公钥更新完成！")
        sys.exit(0)
    else:
        print("❌ 公钥更新失败！")
        sys.exit(1)


if __name__ == "__main__":
    main()
