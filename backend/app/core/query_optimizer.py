"""
数据库查询优化工具

提供常用的查询优化模式和缓存策略
"""

from typing import List, Dict, Any, Optional, Type, TypeVar
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload, joinedload
from functools import wraps
import asyncio
import time
import logging

from app.core.logging import get_logger

logger = get_logger(__name__)

T = TypeVar('T')


class QueryOptimizer:
    """查询优化器"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self._cache = {}
        self._cache_ttl = 300  # 5分钟缓存
    
    async def batch_load_relations(
        self, 
        entities: List[Any], 
        relation_attrs: List[str]
    ) -> List[Any]:
        """
        批量加载关联关系，避免N+1查询问题
        
        Args:
            entities: 实体列表
            relation_attrs: 需要加载的关联属性列表
            
        Returns:
            加载了关联关系的实体列表
        """
        if not entities:
            return entities
            
        entity_ids = [entity.id for entity in entities]
        entity_type = type(entities[0])
        
        # 构建查询，使用selectinload预加载关联关系
        query = select(entity_type)
        for attr in relation_attrs:
            query = query.options(selectinload(getattr(entity_type, attr)))
        
        query = query.where(entity_type.id.in_(entity_ids))
        
        result = await self.db.execute(query)
        optimized_entities = result.scalars().all()
        
        # 按ID排序，保持原始顺序
        entity_map = {entity.id: entity for entity in optimized_entities}
        return [entity_map[entity.id] for entity in entities if entity.id in entity_map]
    
    async def paginated_query(
        self,
        query,
        page: int = 1,
        page_size: int = 20,
        order_by: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        分页查询优化
        
        Args:
            query: SQLAlchemy查询对象
            page: 页码（从1开始）
            page_size: 每页大小
            order_by: 排序字段
            
        Returns:
            包含数据和分页信息的字典
        """
        # 添加排序
        if order_by:
            query = query.order_by(order_by)
        
        # 计算偏移量
        offset = (page - 1) * page_size
        
        # 获取总数（使用子查询优化）
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()
        
        # 获取数据
        data_query = query.offset(offset).limit(page_size)
        result = await self.db.execute(data_query)
        data = result.scalars().all()
        
        return {
            "data": data,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
            "has_next": page * page_size < total,
            "has_prev": page > 1
        }
    
    async def cached_query(
        self,
        cache_key: str,
        query_func,
        ttl: int = 300
    ) -> Any:
        """
        缓存查询结果
        
        Args:
            cache_key: 缓存键
            query_func: 查询函数
            ttl: 缓存时间（秒）
            
        Returns:
            查询结果
        """
        # 检查缓存
        if cache_key in self._cache:
            cached_data, timestamp = self._cache[cache_key]
            if time.time() - timestamp < ttl:
                logger.debug(f"缓存命中: {cache_key}")
                return cached_data
        
        # 执行查询
        result = await query_func()
        
        # 存储到缓存
        self._cache[cache_key] = (result, time.time())
        
        # 清理过期缓存
        self._cleanup_cache()
        
        return result
    
    def _cleanup_cache(self):
        """清理过期缓存"""
        current_time = time.time()
        expired_keys = [
            key for key, (_, timestamp) in self._cache.items()
            if current_time - timestamp > self._cache_ttl
        ]
        for key in expired_keys:
            del self._cache[key]
    
    async def bulk_operations(
        self,
        operations: List[callable],
        batch_size: int = 100
    ) -> List[Any]:
        """
        批量操作优化
        
        Args:
            operations: 操作列表
            batch_size: 批处理大小
            
        Returns:
            操作结果列表
        """
        results = []
        
        # 分批处理
        for i in range(0, len(operations), batch_size):
            batch = operations[i:i + batch_size]
            
            # 并行执行批次内的操作
            batch_results = await asyncio.gather(*batch, return_exceptions=True)
            results.extend(batch_results)
            
            # 每批次后提交事务
            await self.db.commit()
        
        return results


def query_performance_monitor(func):
    """查询性能监控装饰器"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            execution_time = time.time() - start_time
            
            logger.info(
                f"查询执行完成: {func.__name__}",
                execution_time=f"{execution_time:.3f}s",
                success=True
            )
            
            # 如果执行时间超过1秒，记录警告
            if execution_time > 1.0:
                logger.warning(
                    f"慢查询检测: {func.__name__}",
                    execution_time=f"{execution_time:.3f}s"
                )
            
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(
                f"查询执行失败: {func.__name__}",
                execution_time=f"{execution_time:.3f}s",
                error=str(e)
            )
            raise
    
    return wrapper


class DatabaseIndexOptimizer:
    """数据库索引优化器"""
    
    @staticmethod
    def get_recommended_indexes() -> List[Dict[str, Any]]:
        """
        获取推荐的数据库索引
        
        Returns:
            索引配置列表
        """
        return [
            # 产品分类索引
            {
                "table": "product_categories",
                "columns": ["tenant_id", "is_active"],
                "name": "idx_categories_tenant_active"
            },
            {
                "table": "product_categories",
                "columns": ["tenant_id", "category_code"],
                "name": "idx_categories_tenant_code",
                "unique": True
            },
            {
                "table": "product_categories",
                "columns": ["tenant_id", "is_root"],
                "name": "idx_categories_tenant_root"
            },
            
            # 分类关系索引
            {
                "table": "product_category_relations",
                "columns": ["parent_category_id"],
                "name": "idx_category_relations_parent"
            },
            {
                "table": "product_category_relations",
                "columns": ["child_category_id"],
                "name": "idx_category_relations_child"
            },
            
            # 产品变体索引
            {
                "table": "product_variants",
                "columns": ["tenant_id", "is_active"],
                "name": "idx_variants_tenant_active"
            },
            {
                "table": "product_variants",
                "columns": ["tenant_id", "sku"],
                "name": "idx_variants_tenant_sku",
                "unique": True
            },
            {
                "table": "product_variants",
                "columns": ["product_id"],
                "name": "idx_variants_product"
            },
            
            # 维度模板索引
            {
                "table": "product_dimension_templates",
                "columns": ["tenant_id", "is_active"],
                "name": "idx_dimension_templates_tenant_active"
            },
            {
                "table": "product_dimension_templates",
                "columns": ["tenant_id", "dimension_code"],
                "name": "idx_dimension_templates_tenant_code",
                "unique": True
            },
            
            # 维度值索引
            {
                "table": "product_dimension_values",
                "columns": ["template_id"],
                "name": "idx_dimension_values_template"
            },
            {
                "table": "product_dimension_values",
                "columns": ["template_id", "sort_order"],
                "name": "idx_dimension_values_template_order"
            }
        ]
    
    @staticmethod
    def generate_index_sql() -> List[str]:
        """
        生成索引创建SQL语句
        
        Returns:
            SQL语句列表
        """
        indexes = DatabaseIndexOptimizer.get_recommended_indexes()
        sql_statements = []
        
        for index in indexes:
            columns = ", ".join(index["columns"])
            unique = "UNIQUE " if index.get("unique", False) else ""
            sql = f"CREATE {unique}INDEX {index['name']} ON {index['table']} ({columns});"
            sql_statements.append(sql)
        
        return sql_statements
