"""Add missing audit fields to all tables

Revision ID: add_missing_audit_fields
Revises: 6f98c9a0f611
Create Date: 2025-10-16 10:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "add_missing_audit_fields"
down_revision = "6f98c9a0f611"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    添加缺失的审计字段到所有表
    """
    
    # 需要添加审计字段的表列表
    tables_to_update = [
        "product_categories",
        "product_category_relations", 
        "product_category_dimensions",
        "product_category_assignments",
        "product_dimension_templates",
        "product_dimension_values",
        "product_variant_dimensions",
        "products",
        "product_variants",
        "product_attributes",
        "orders",
        "order_items",
        "customers",
        "external_systems",
        "external_data",
        "tenants",
        "users",
        "user_tenants",
        "suppliers",
        "printify_products",
        "printify_variants",
        "printify_orders",
        "shopify_orders",
        "scm_orders",
        "sync_configs",
        "jwt_blacklist"
    ]
    
    for table_name in tables_to_update:
        try:
            # 检查表是否存在
            connection = op.get_bind()
            result = connection.execute(
                sa.text(f"SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = '{table_name}')")
            )
            table_exists = result.scalar()
            
            if not table_exists:
                print(f"Table {table_name} does not exist, skipping...")
                continue
                
            # 添加 created_by 字段（如果不存在）
            result = connection.execute(sa.text(f"""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = '{table_name}' AND column_name = 'created_by'
            """))
            
            if not result.fetchone():
                try:
                    op.add_column(table_name, sa.Column('created_by', sa.Integer(), nullable=True))
                    op.create_foreign_key(
                        f'fk_{table_name}_created_by', 
                        table_name, 
                        'users', 
                        ['created_by'], 
                        ['id']
                    )
                    print(f"Added created_by to {table_name}")
                except Exception as e:
                    print(f"Failed to add created_by to {table_name}: {e}")
            else:
                print(f"created_by already exists in {table_name}")
            
            # 添加 updated_by 字段（如果不存在）
            result = connection.execute(sa.text(f"""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = '{table_name}' AND column_name = 'updated_by'
            """))
            
            if not result.fetchone():
                try:
                    op.add_column(table_name, sa.Column('updated_by', sa.Integer(), nullable=True))
                    op.create_foreign_key(
                        f'fk_{table_name}_updated_by', 
                        table_name, 
                        'users', 
                        ['updated_by'], 
                        ['id']
                    )
                    print(f"Added updated_by to {table_name}")
                except Exception as e:
                    print(f"Failed to add updated_by to {table_name}: {e}")
            else:
                print(f"updated_by already exists in {table_name}")
            
            # 添加 is_deleted 字段（如果不存在）
            result = connection.execute(sa.text(f"""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = '{table_name}' AND column_name = 'is_deleted'
            """))
            
            if not result.fetchone():
                try:
                    op.add_column(table_name, sa.Column('is_deleted', sa.Boolean(), nullable=True))
                    # 设置默认值
                    op.execute(f"UPDATE {table_name} SET is_deleted = false WHERE is_deleted IS NULL")
                    op.alter_column(table_name, 'is_deleted', nullable=False, server_default=sa.text('false'))
                    print(f"Added is_deleted to {table_name}")
                except Exception as e:
                    print(f"Failed to add is_deleted to {table_name}: {e}")
            else:
                print(f"is_deleted already exists in {table_name}")
            
            # 为没有 is_active 的表添加 is_active 字段
            try:
                # 检查 is_active 字段是否已存在
                result = connection.execute(
                    sa.text(f"SELECT column_name FROM information_schema.columns WHERE table_name = '{table_name}' AND column_name = 'is_active'")
                )
                has_is_active = result.fetchone() is not None
                
                if not has_is_active:
                    op.add_column(table_name, sa.Column('is_active', sa.Boolean(), nullable=True))
                    op.execute(f"UPDATE {table_name} SET is_active = true WHERE is_active IS NULL")
                    op.alter_column(table_name, 'is_active', nullable=False, server_default=sa.text('true'))
                    print(f"Added is_active to {table_name}")
                else:
                    print(f"is_active already exists in {table_name}")
            except Exception as e:
                print(f"Failed to add is_active to {table_name}: {e}")
                
        except Exception as e:
            print(f"Error processing table {table_name}: {e}")
            continue
    
    # 创建审计字段索引
    try:
        # 为常用查询创建复合索引
        for table_name in ["product_categories", "products", "orders"]:
            try:
                op.create_index(
                    f'idx_{table_name}_audit',
                    table_name,
                    ['created_at', 'updated_at'],
                    unique=False
                )
                op.create_index(
                    f'idx_{table_name}_active',
                    table_name,
                    ['is_active', 'is_deleted'],
                    unique=False
                )
                print(f"Created audit indexes for {table_name}")
            except Exception as e:
                print(f"Failed to create indexes for {table_name}: {e}")
    except Exception as e:
        print(f"Error creating indexes: {e}")


def downgrade() -> None:
    """
    回滚审计字段添加
    """
    
    tables_to_update = [
        "product_categories",
        "product_category_relations", 
        "product_category_dimensions",
        "product_category_assignments",
        "product_dimension_templates",
        "product_dimension_values",
        "product_variant_dimensions",
        "products",
        "product_variants",
        "product_attributes",
        "orders",
        "order_items",
        "customers",
        "external_systems",
        "external_data",
        "tenants",
        "users",
        "user_tenants",
        "suppliers",
        "printify_products",
        "printify_variants",
        "printify_orders",
        "shopify_orders",
        "scm_orders",
        "sync_configs",
        "jwt_blacklist"
    ]
    
    for table_name in tables_to_update:
        try:
            # 删除索引
            try:
                op.drop_index(f'idx_{table_name}_audit', table_name)
                op.drop_index(f'idx_{table_name}_active', table_name)
            except:
                pass
            
            # 删除外键约束
            try:
                op.drop_constraint(f'fk_{table_name}_created_by', table_name, type_='foreignkey')
                op.drop_constraint(f'fk_{table_name}_updated_by', table_name, type_='foreignkey')
            except:
                pass
            
            # 删除字段
            try:
                op.drop_column(table_name, 'created_by')
                op.drop_column(table_name, 'updated_by')
                op.drop_column(table_name, 'is_deleted')
            except:
                pass
                
        except Exception as e:
            print(f"Error processing table {table_name} in downgrade: {e}")
            continue
