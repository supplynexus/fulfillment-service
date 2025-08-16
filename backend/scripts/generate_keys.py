#!/usr/bin/env python3
"""
密钥对生成工具

用法:
    python generate_keys.py <tenant_name> [--type rsa] [--size 2048] [--save-db] [--output-dir ./keys]

示例:
    python generate_keys.py impeach --save-db
    python generate_keys.py test_tenant --type rsa --size 4096 --output-dir ./custom_keys
"""

import argparse
import os
import sys
import asyncio
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


class KeyGenerator:
    """密钥对生成器"""
    
    def __init__(self, tenant_name: str, key_type: str = 'rsa', key_size: int = 2048):
        self.tenant_name = tenant_name
        self.key_type = key_type.lower()
        self.key_size = key_size
        
        # 验证参数
        if self.key_type not in ['rsa']:
            raise ValueError(f"Unsupported key type: {key_type}. Only 'rsa' is supported.")
        
        if self.key_size not in [1024, 2048, 4096]:
            raise ValueError(f"Unsupported key size: {key_size}. Supported sizes: 1024, 2048, 4096")
    
    def generate_key_pair(self):
        """生成密钥对"""
        print(f"🔑 生成 {self.key_type.upper()} 密钥对 (大小: {self.key_size} bits)")
        print(f"   租户: {self.tenant_name}")
        print()
        
        if self.key_type == 'rsa':
            return self._generate_rsa_key_pair()
        else:
            raise ValueError(f"Unsupported key type: {self.key_type}")
    
    def _generate_rsa_key_pair(self):
        """生成 RSA 密钥对"""
        # 生成私钥
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=self.key_size,
            backend=default_backend()
        )
        
        # 获取公钥
        public_key = private_key.public_key()
        
        # 序列化私钥
        private_key_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ).decode('utf-8')
        
        # 序列化公钥
        public_key_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode('utf-8')
        
        return {
            'private_key': private_key_pem,
            'public_key': public_key_pem,
            'key_type': 'rsa',
            'key_size': self.key_size
        }
    
    def save_keys_to_files(self, keys: dict, output_dir: str = './keys'):
        """保存密钥到文件"""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # 生成文件名
        private_key_file = output_path / f"{self.tenant_name}_private_key.pem"
        public_key_file = output_path / f"{self.tenant_name}_public_key.pem"
        
        # 保存私钥
        with open(private_key_file, 'w') as f:
            f.write(keys['private_key'])
        
        # 保存公钥
        with open(public_key_file, 'w') as f:
            f.write(keys['public_key'])
        
        print(f"💾 密钥已保存到文件:")
        print(f"   私钥: {private_key_file}")
        print(f"   公钥: {public_key_file}")
        print()
        
        return {
            'private_key_file': str(private_key_file),
            'public_key_file': str(public_key_file)
        }
    
    async def save_public_key_to_db(self, keys: dict):
        """保存公钥到数据库"""
        print("🗄️  保存公钥到数据库...")
        
        # 创建数据库连接
        engine = create_async_engine(settings.DATABASE_URL)
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        
        async with async_session() as session:
            try:
                # 查找租户
                result = await session.execute(
                    select(Tenant).where(Tenant.name == self.tenant_name)
                )
                tenant = result.scalar_one_or_none()
                
                if not tenant:
                    print(f"❌ 租户 '{self.tenant_name}' 不存在")
                    return False
                
                # 更新公钥
                tenant.public_key = keys['public_key']
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
    
    def display_keys(self, keys: dict):
        """显示生成的密钥"""
        print("🔍 生成的密钥:")
        print("=" * 50)
        
        print("私钥:")
        print(keys['private_key'])
        print()
        
        print("公钥:")
        print(keys['public_key'])
        print()
        
        print(f"密钥信息:")
        print(f"   类型: {keys['key_type'].upper()}")
        print(f"   大小: {keys['key_size']} bits")
        print(f"   租户: {self.tenant_name}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="生成 RSA 密钥对工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python generate_keys.py impeach --save-db
  python generate_keys.py test_tenant --type rsa --size 4096 --output-dir ./custom_keys
  python generate_keys.py demo_tenant --save-db --output-dir ./tenant_keys
        """
    )
    
    parser.add_argument(
        'tenant_name',
        help='租户名称 (例如: impeach)'
    )
    
    parser.add_argument(
        '--type',
        choices=['rsa'],
        default='rsa',
        help='密钥类型 (默认: rsa)'
    )
    
    parser.add_argument(
        '--size',
        type=int,
        choices=[1024, 2048, 4096],
        default=2048,
        help='密钥大小 (默认: 2048)'
    )
    
    parser.add_argument(
        '--save-db',
        action='store_true',
        help='保存公钥到数据库'
    )
    
    parser.add_argument(
        '--output-dir',
        default='./keys',
        help='密钥文件输出目录 (默认: ./keys)'
    )
    
    parser.add_argument(
        '--display',
        action='store_true',
        help='显示生成的密钥'
    )
    
    args = parser.parse_args()
    
    try:
        # 创建密钥生成器
        generator = KeyGenerator(
            tenant_name=args.tenant_name,
            key_type=args.type,
            key_size=args.size
        )
        
        # 生成密钥对
        keys = generator.generate_key_pair()
        
        # 保存到文件
        file_paths = generator.save_keys_to_files(keys, args.output_dir)
        
        # 保存到数据库
        if args.save_db:
            success = asyncio.run(generator.save_public_key_to_db(keys))
            if not success:
                print("⚠️  公钥未保存到数据库，但文件已生成")
        
        # 显示密钥
        if args.display:
            generator.display_keys(keys)
        
        print("🎯 密钥生成完成！")
        print()
        print("📝 注意事项:")
        print("   1. 私钥文件已保存，请妥善保管")
        print("   2. 私钥文件不应提交到版本控制系统")
        print("   3. 建议将密钥目录添加到 .gitignore")
        print("   4. 在生产环境中，请使用更安全的密钥存储方式")
        
        if args.save_db:
            print("   5. 公钥已保存到数据库")
        
        return 0
        
    except Exception as e:
        print(f"❌ 错误: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
