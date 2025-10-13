#!/usr/bin/env python3
"""
迁移现有 SCM 订单的 line_items 数据结构
将旧的格式转换为新的规范化格式
"""

import asyncio
import json
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

# 数据库连接配置
DATABASE_URL = "postgresql+asyncpg://supplynexus:supplynexus@localhost:5432/supplynexus_dev"

async def migrate_scm_orders():
    """迁移 SCM 订单的 line_items 数据"""
    
    # 创建异步数据库连接
    engine = create_async_engine(DATABASE_URL)
    
    async with AsyncSession(engine) as session:
        try:
            # 查询所有 SCM 订单
            result = await session.execute(text("""
                SELECT id, line_items, tenant_id 
                FROM scm_orders 
                WHERE line_items IS NOT NULL
                ORDER BY id
            """))
            
            scm_orders = result.fetchall()
            print(f"找到 {len(scm_orders)} 个 SCM 订单需要迁移")
            
            for scm_order in scm_orders:
                scm_id = scm_order[0]
                line_items = scm_order[1]
                tenant_id = scm_order[2]
                
                print(f"\n处理 SCM 订单 #{scm_id}")
                
                # 检查是否已经是新格式
                if line_items and len(line_items) > 0:
                    first_item = line_items[0]
                    if isinstance(first_item, dict) and 'metadata' in first_item:
                        print(f"  SCM 订单 #{scm_id} 已经是新格式，跳过")
                        continue
                
                # 转换旧格式到新格式
                new_line_items = []
                for item in line_items:
                    if isinstance(item, dict):
                        # 提取基本信息
                        title = item.get('title', '')
                        variant_title = item.get('variant_title', '')
                        sku = item.get('sku', '')
                        quantity = int(item.get('quantity', 1))
                        price = float(item.get('price', 0))
                        
                        # 构建新的规范化项目
                        normalized_item = {
                            "core_product_id": None,
                            "core_variant_id": None,
                            "quantity": max(1, quantity),
                            "metadata": {
                                "sku": sku,
                                "title": title,
                                "variant_label": variant_title,
                                "price": price,
                                "source_line_item_id": item.get('id'),
                                "vendor": item.get('vendor'),
                                "product_type": item.get('product_type'),
                            }
                        }
                        
                        new_line_items.append(normalized_item)
                
                # 更新数据库
                if new_line_items:
                    await session.execute(text("""
                        UPDATE scm_orders 
                        SET line_items = :line_items 
                        WHERE id = :scm_id
                    """), {
                        "line_items": json.dumps(new_line_items),
                        "scm_id": scm_id
                    })
                    
                    print(f"  SCM 订单 #{scm_id} 迁移完成，处理了 {len(new_line_items)} 个商品")
                else:
                    print(f"  SCM 订单 #{scm_id} 没有商品数据，跳过")
            
            # 提交更改
            await session.commit()
            print(f"\n✅ 迁移完成！共处理了 {len(scm_orders)} 个 SCM 订单")
            
        except Exception as e:
            print(f"❌ 迁移失败: {str(e)}")
            await session.rollback()
            raise
        finally:
            await session.close()

if __name__ == "__main__":
    asyncio.run(migrate_scm_orders())
