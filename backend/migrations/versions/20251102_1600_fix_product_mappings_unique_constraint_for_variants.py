"""fix_product_mappings_unique_constraint_for_variants

Revision ID: a1b2c3d4e5f6
Revises: d259bc6512c5
Create Date: 2025-11-02 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = 'd259bc6512c5'  # 基于最新的迁移版本
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    修复 product_mappings 表的唯一约束，支持商品级别和变体级别的映射
    
    新的约束设计：
    1. 商品级别映射（core_variant_id IS NULL）：(tenant_id, core_product_id, external_system_id) 唯一
    2. 变体级别映射（core_variant_id IS NOT NULL）：(tenant_id, core_product_id, core_variant_id, external_system_id) 唯一
    """
    connection = op.get_bind()
    
    # 1. 检查并删除旧的唯一约束
    result = connection.execute(sa.text("""
        SELECT constraint_name FROM information_schema.table_constraints
        WHERE table_name = 'product_mappings' AND constraint_name = 'uq_product_mappings_tenant_core_external'
    """))
    
    if result.fetchone():
        op.drop_constraint('uq_product_mappings_tenant_core_external', 'product_mappings', type_='unique')
        print("✅ 已删除旧的唯一约束: uq_product_mappings_tenant_core_external")
    else:
        print("ℹ️ 旧约束不存在，跳过删除")
    
    # 2. 检查是否存在旧的变体约束
    result = connection.execute(sa.text("""
        SELECT constraint_name FROM information_schema.table_constraints
        WHERE table_name = 'product_mappings' AND constraint_name = 'uq_product_mappings_tenant_core_variant_external'
    """))
    
    if result.fetchone():
        op.drop_constraint('uq_product_mappings_tenant_core_variant_external', 'product_mappings', type_='unique')
        print("✅ 已删除旧的变体约束: uq_product_mappings_tenant_core_variant_external")
    else:
        print("ℹ️ 旧变体约束不存在，跳过删除")
    
    # 3. 清理重复数据（保留最早创建的记录）
    print("🔍 开始清理重复数据...")
    connection.execute(sa.text("""
        DELETE FROM product_mappings pm1
        WHERE pm1.id NOT IN (
            SELECT MIN(pm2.id)
            FROM product_mappings pm2
            WHERE pm2.core_variant_id IS NULL
            GROUP BY pm2.tenant_id, pm2.core_product_id, pm2.external_system_id
        )
        AND pm1.core_variant_id IS NULL
    """))
    
    connection.execute(sa.text("""
        DELETE FROM product_mappings pm1
        WHERE pm1.id NOT IN (
            SELECT MIN(pm2.id)
            FROM product_mappings pm2
            WHERE pm2.core_variant_id IS NOT NULL
            GROUP BY pm2.tenant_id, pm2.core_product_id, pm2.core_variant_id, pm2.external_system_id
        )
        AND pm1.core_variant_id IS NOT NULL
    """))
    print("✅ 重复数据清理完成")
    
    # 4. 创建商品级别的部分唯一索引（core_variant_id IS NULL）
    print("📝 创建商品级别的部分唯一索引...")
    connection.execute(sa.text("""
        CREATE UNIQUE INDEX IF NOT EXISTS uq_product_mappings_product_level
        ON product_mappings (tenant_id, core_product_id, external_system_id)
        WHERE core_variant_id IS NULL
    """))
    print("✅ 商品级别唯一索引创建成功")
    
    # 5. 创建变体级别的部分唯一索引（core_variant_id IS NOT NULL）
    print("📝 创建变体级别的部分唯一索引...")
    connection.execute(sa.text("""
        CREATE UNIQUE INDEX IF NOT EXISTS uq_product_mappings_variant_level
        ON product_mappings (tenant_id, core_product_id, core_variant_id, external_system_id)
        WHERE core_variant_id IS NOT NULL
    """))
    print("✅ 变体级别唯一索引创建成功")
    
    print("✅ 唯一约束修复完成！")
    print("💡 现在支持：")
    print("   - 商品级别映射：每个商品和外部系统可以有一个映射（core_variant_id IS NULL）")
    print("   - 变体级别映射：每个变体和外部系统可以有一个映射（core_variant_id IS NOT NULL）")


def downgrade() -> None:
    """
    回滚到旧的唯一约束设计
    """
    connection = op.get_bind()
    
    # 删除部分唯一索引
    result = connection.execute(sa.text("""
        SELECT indexname FROM pg_indexes 
        WHERE tablename = 'product_mappings' AND indexname = 'uq_product_mappings_product_level'
    """))
    if result.fetchone():
        op.execute(sa.text("DROP INDEX IF EXISTS uq_product_mappings_product_level"))
        print("✅ 已删除商品级别唯一索引")
    
    result = connection.execute(sa.text("""
        SELECT indexname FROM pg_indexes 
        WHERE tablename = 'product_mappings' AND indexname = 'uq_product_mappings_variant_level'
    """))
    if result.fetchone():
        op.execute(sa.text("DROP INDEX IF EXISTS uq_product_mappings_variant_level"))
        print("✅ 已删除变体级别唯一索引")
    
    # 恢复旧的唯一约束
    op.create_unique_constraint(
        'uq_product_mappings_tenant_core_external',
        'product_mappings',
        ['tenant_id', 'core_product_id', 'external_system_id']
    )
    print("✅ 已恢复旧的唯一约束")

