#!/usr/bin/env python3
"""
简单的开发环境数据初始化
"""

import asyncio
import os
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import get_async_db
from app.models.tenant import Tenant
from app.models.user import User
from app.services.user_service import UserService
from sqlalchemy import select
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend


async def create_test_tenant():
    """创建测试租户"""
    print("🏢 创建测试租户...")

    async for db in get_async_db():
        try:
            # 检查租户是否已存在
            result = await db.execute(select(Tenant).where(Tenant.name == "impeach"))
            existing_tenant = result.scalar_one_or_none()

            if existing_tenant:
                print(
                    f"✅ 租户已存在: {existing_tenant.name} (ID: {existing_tenant.id})"
                )
                return existing_tenant

            # 生成RSA密钥对
            print("🔑 生成RSA密钥对...")
            private_key = rsa.generate_private_key(
                public_exponent=65537, key_size=2048, backend=default_backend()
            )

            public_key = private_key.public_key()
            public_pem = public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            ).decode("utf-8")

            # 创建租户
            tenant = Tenant(
                name="impeach",
                display_name="Impeach Test Tenant",
                description="用于测试的租户",
                settings={},
                is_active=True,
                public_key=public_pem,
                key_id="impeach_key_001",
                key_type="rsa",
                key_size=2048,
            )

            db.add(tenant)
            await db.commit()
            await db.refresh(tenant)

            print(f"✅ 租户创建成功: {tenant.name} (ID: {tenant.id})")

            # 保存私钥到文件
            private_pem = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            ).decode("utf-8")

            keys_dir = Path("./keys")
            keys_dir.mkdir(exist_ok=True)

            private_key_file = keys_dir / "impeach_private_key.pem"
            with open(private_key_file, "w") as f:
                f.write(private_pem)

            print(f"🔑 私钥已保存到: {private_key_file}")

            return tenant

        except Exception as e:
            print(f"❌ 创建租户失败: {e}")
            raise
        break


async def create_test_user():
    """创建测试用户"""
    print("👤 创建测试用户...")

    async for db in get_async_db():
        try:
            # 检查用户是否已存在
            result = await db.execute(
                select(User).where(User.email == "test@impeach.com")
            )
            existing_user = result.scalar_one_or_none()

            if existing_user:
                print(f"✅ 用户已存在: {existing_user.email} (ID: {existing_user.id})")
                return existing_user

            # 创建用户
            user_service = UserService(db)
            user, message = await user_service.create(
                {
                    "email": "test@impeach.com",
                    "password": "Test123456!",
                    "full_name": "Test User",
                    "is_active": True,
                    "is_superuser": False,
                }
            )

            if user:
                print(f"✅ 用户创建成功: {user.email} (ID: {user.id})")
                return user
            else:
                print(f"❌ 用户创建失败: {message}")
                return None

        except Exception as e:
            print(f"❌ 创建用户失败: {e}")
            raise
        break


async def main():
    """主函数"""
    print("🚀 开始初始化开发环境数据...")

    try:
        tenant = await create_test_tenant()
        user = await create_test_user()

        print("\n🎉 开发环境数据初始化完成!")
        print(f"   租户: {tenant.name} (ID: {tenant.id})")
        print(f"   用户: {user.email} (ID: {user.id})")
        print("\n📝 测试登录信息:")
        print(f"   用户名: {user.email}")
        print(f"   密码: Test123456!")
        print(f"   租户: {tenant.name}")

    except Exception as e:
        print(f"❌ 初始化失败: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
