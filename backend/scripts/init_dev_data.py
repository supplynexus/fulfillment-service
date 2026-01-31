#!/usr/bin/env python3
"""
初始化开发环境数据
创建租户、用户和密钥对
"""

import asyncio
import os
import sys
from pathlib import Path
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# 添加项目根目录到 Python 路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.models.tenant import Tenant
from app.models.user import User
from app.services.user_service import UserService


class DevDataInitializer:
    """开发环境数据初始化器"""

    def __init__(self):
        self.engine = create_async_engine(settings.DATABASE_URL)
        self.async_session = sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )

    async def generate_rsa_keypair(self, key_size: int = 2048) -> dict:
        """生成RSA密钥对"""
        print("🔑 生成RSA密钥对...")

        # 生成私钥
        private_key = rsa.generate_private_key(
            public_exponent=65537, key_size=key_size, backend=default_backend()
        )

        # 获取公钥
        public_key = private_key.public_key()

        # 序列化私钥
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ).decode("utf-8")

        # 序列化公钥
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode("utf-8")

        return {
            "private_key": private_pem,
            "public_key": public_pem,
            "key_type": "rsa",
            "key_size": key_size,
        }

    async def create_tenant(
        self, name: str, display_name: str, description: str = None
    ) -> Tenant:
        """创建租户"""
        print(f"🏢 创建租户: {name}")

        async with self.async_session() as db:
            try:
                # 检查租户是否已存在
                result = await db.execute(select(Tenant).where(Tenant.name == name))
                existing_tenant = result.scalar_one_or_none()

                if existing_tenant:
                    print(f"✅ 租户已存在: {name} (ID: {existing_tenant.id})")
                    return existing_tenant

                # 生成密钥对
                keys = await self.generate_rsa_keypair()

                # 创建租户
                tenant = Tenant(
                    name=name,
                    display_name=display_name,
                    description=description or f"开发环境租户: {display_name}",
                    settings={},
                    is_active=True,
                    public_key=keys["public_key"],
                    key_id=f"{name}_key_001",
                    key_type=keys["key_type"],
                    key_size=keys["key_size"],
                )

                db.add(tenant)
                await db.commit()
                await db.refresh(tenant)

                print(f"✅ 租户创建成功: {name} (ID: {tenant.id})")

                # 保存私钥到文件
                await self.save_private_key(keys["private_key"], name)

                return tenant

            except Exception as e:
                await db.rollback()
                print(f"❌ 创建租户失败: {e}")
                raise

    async def save_private_key(self, private_key: str, tenant_name: str):
        """保存私钥到文件"""
        keys_dir = Path("./keys")
        keys_dir.mkdir(exist_ok=True)

        private_key_file = keys_dir / f"{tenant_name}_private_key.pem"

        with open(private_key_file, "w") as f:
            f.write(private_key)

        print(f"🔑 私钥已保存到: {private_key_file}")

    async def create_user(
        self, email: str, password: str, full_name: str = None
    ) -> User:
        """创建用户"""
        print(f"👤 创建用户: {email}")

        async with self.async_session() as db:
            try:
                # 检查用户是否已存在
                result = await db.execute(select(User).where(User.email == email))
                existing_user = result.scalar_one_or_none()

                if existing_user:
                    print(f"✅ 用户已存在: {email} (ID: {existing_user.id})")
                    return existing_user

                # 创建用户
                user_service = UserService(db)
                user, message = await user_service.create(
                    {
                        "email": email,
                        "password": password,
                        "full_name": full_name,
                        "is_active": True,
                        "is_superuser": False,
                    }
                )

                if user:
                    print(f"✅ 用户创建成功: {email} (ID: {user.id})")
                    return user
                else:
                    print(f"❌ 用户创建失败: {message}")
                    return None

            except Exception as e:
                await db.rollback()
                print(f"❌ 创建用户失败: {e}")
                raise

    async def init_dev_data(self):
        """初始化开发环境数据"""
        print("🚀 开始初始化开发环境数据...")

        try:
            # 创建测试租户
            tenant = await self.create_tenant(
                name="impeach",
                display_name="Impeach Test Tenant",
                description="用于测试的租户",
            )

            # 创建测试用户
            user = await self.create_user(
                email="test@impeach.com", password="test123456", full_name="Test User"
            )

            print("\n🎉 开发环境数据初始化完成!")
            print(f"   租户: {tenant.name} (ID: {tenant.id})")
            print(f"   用户: {user.email} (ID: {user.id})")
            print(f"   私钥文件: ./keys/{tenant.name}_private_key.pem")
            print("\n📝 测试登录信息:")
            print(f"   用户名: {user.email}")
            print(f"   密码: test123456")
            print(f"   租户: {tenant.name}")

        except Exception as e:
            print(f"❌ 初始化失败: {e}")
            raise
        finally:
            await self.engine.dispose()


async def main():
    """主函数"""
    initializer = DevDataInitializer()
    await initializer.init_dev_data()


if __name__ == "__main__":
    asyncio.run(main())
