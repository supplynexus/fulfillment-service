"""
ProductCategoryService - 产品分类管理服务

实现功能：
1. 分类的 CRUD 操作
2. DAG 结构管理（多对多父子关系）
3. 循环检测（BFS 算法）
4. 分类树查询
5. 分类路径计算
6. 分类维度继承管理
"""

from typing import List, Optional, Dict, Set, Tuple, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import selectinload
from collections import deque
import logging

from app.models.product_category import (
    ProductCategory,
    ProductCategoryRelation,
    ProductCategoryDimension,
    ProductCategoryAssignment
)
from app.models.product_dimension import ProductDimensionTemplate
from app.core.logging import get_logger

logger = get_logger(__name__)


class ProductCategoryService:
    """产品分类管理服务"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_category(
        self,
        tenant_id: int,
        category_code: str,
        category_name: str,
        description: Optional[str] = None,
        parent_category_ids: Optional[List[int]] = None,
        is_root: bool = False,
        sort_order: int = 0
    ) -> ProductCategory:
        """
        创建产品分类
        
        Args:
            tenant_id: 租户ID
            category_code: 分类编码
            category_name: 分类名称
            description: 描述
            parent_category_ids: 父分类ID列表（支持多父分类）
            is_root: 是否为根分类
            sort_order: 排序
            
        Returns:
            ProductCategory: 创建的分类
            
        Raises:
            ValueError: 如果分类编码重复或循环引用
        """
        logger.info("🔍 开始创建产品分类", 
                   tenant_id=tenant_id, 
                   category_code=category_code,
                   parent_category_ids=parent_category_ids)
        
        # 检查分类编码是否重复
        existing = await self.get_category_by_code(tenant_id, category_code)
        if existing:
            raise ValueError(f"分类编码 '{category_code}' 已存在")
        
        # 创建分类
        category = ProductCategory(
            tenant_id=tenant_id,
            category_code=category_code,
            category_name=category_name,
            description=description,
            is_root=is_root,
            sort_order=sort_order
        )
        
        self.db.add(category)
        await self.db.flush()  # 获取ID
        
        # 创建父子关系
        if parent_category_ids:
            # 检查循环引用
            await self._check_cycle_detection(category.id, parent_category_ids)
            
            for parent_id in parent_category_ids:
                relation = ProductCategoryRelation(
                    parent_category_id=parent_id,
                    child_category_id=category.id
                )
                self.db.add(relation)
        
        await self.db.commit()
        
        logger.info("✅ 产品分类创建成功", 
                   category_id=category.id,
                   category_code=category_code)
        
        return category
    
    async def get_category_by_code(
        self, 
        tenant_id: int, 
        category_code: str
    ) -> Optional[ProductCategory]:
        """根据编码获取分类"""
        result = await self.db.execute(
            select(ProductCategory)
            .where(
                and_(
                    ProductCategory.tenant_id == tenant_id,
                    ProductCategory.category_code == category_code
                )
            )
        )
        return result.scalar_one_or_none()
    
    async def get_category_by_id(
        self, 
        category_id: int, 
        tenant_id: int
    ) -> Optional[ProductCategory]:
        """根据ID获取分类"""
        result = await self.db.execute(
            select(ProductCategory)
            .where(
                and_(
                    ProductCategory.id == category_id,
                    ProductCategory.tenant_id == tenant_id
                )
            )
        )
        return result.scalar_one_or_none()
    
    async def get_category_tree(
        self, 
        tenant_id: int, 
        include_inactive: bool = False
    ) -> List[Dict[str, Any]]:
        """
        获取分类树结构（优化版本）
        
        Returns:
            List[Dict]: 树形结构数据，包含 children 字段
        """
        logger.info("🔍 开始获取分类树", tenant_id=tenant_id)
        
        # 优化：使用一次查询获取所有分类和关系
        query = (
            select(ProductCategory)
            .options(
                selectinload(ProductCategory.parent_relations),
                selectinload(ProductCategory.child_relations)
            )
            .where(ProductCategory.tenant_id == tenant_id)
        )
        if not include_inactive:
            query = query.where(ProductCategory.is_active == True)
        
        result = await self.db.execute(query)
        categories = result.scalars().all()
        
        # 构建关系映射（避免重复查询）
        parent_to_children = {}
        for category in categories:
            for child_relation in category.child_relations:
                if category.id not in parent_to_children:
                    parent_to_children[category.id] = []
                parent_to_children[category.id].append(child_relation.child_category_id)
        
        # 构建树形结构
        category_dict = {cat.id: {
            "id": cat.id,
            "category_code": cat.category_code,
            "category_name": cat.category_name,
            "description": cat.description,
            "is_root": cat.is_root,
            "sort_order": cat.sort_order,
            "is_active": cat.is_active,
            "children": []
        } for cat in categories}
        
        # 添加子分类
        for parent_id, child_ids in parent_to_children.items():
            if parent_id in category_dict:
                for child_id in child_ids:
                    if child_id in category_dict:
                        category_dict[parent_id]["children"].append(category_dict[child_id])
        
        # 返回根分类
        root_categories = [cat for cat in category_dict.values() if cat["is_root"]]
        
        logger.info("✅ 分类树获取成功", 
                   total_categories=len(categories),
                   root_categories=len(root_categories))
        
        return root_categories
    
    async def get_category_path(
        self, 
        category_id: int, 
        tenant_id: int
    ) -> List[ProductCategory]:
        """
        获取分类的完整路径（从根到当前分类）
        
        Returns:
            List[ProductCategory]: 路径上的所有分类，从根到当前
        """
        logger.info("🔍 开始获取分类路径", category_id=category_id)
        
        # 使用 BFS 从当前分类向上查找根分类
        visited = set()
        queue = deque([category_id])
        parent_map = {}
        
        while queue:
            current_id = queue.popleft()
            if current_id in visited:
                continue
            visited.add(current_id)
            
            # 查找父分类
            result = await self.db.execute(
                select(ProductCategoryRelation)
                .where(ProductCategoryRelation.child_category_id == current_id)
            )
            relations = result.scalars().all()
            
            for relation in relations:
                parent_id = relation.parent_category_id
                if parent_id not in visited:
                    parent_map[parent_id] = current_id
                    queue.append(parent_id)
        
        # 构建路径
        path = []
        current = category_id
        
        # 从当前分类向上追溯到根
        while current in parent_map:
            parent = parent_map[current]
            parent_category = await self.get_category_by_id(parent, tenant_id)
            if parent_category:
                path.insert(0, parent_category)
            current = parent
        
        # 添加当前分类
        current_category = await self.get_category_by_id(category_id, tenant_id)
        if current_category:
            path.append(current_category)
        
        logger.info("✅ 分类路径获取成功", 
                   category_id=category_id,
                   path_length=len(path))
        
        return path
    
    async def _check_cycle_detection(
        self, 
        new_category_id: int, 
        parent_category_ids: List[int]
    ) -> None:
        """
        检查循环引用（BFS算法）
        
        Args:
            new_category_id: 新分类ID
            parent_category_ids: 父分类ID列表
            
        Raises:
            ValueError: 如果检测到循环引用
        """
        logger.info("🔍 开始循环检测", 
                   new_category_id=new_category_id,
                   parent_category_ids=parent_category_ids)
        
        # 检查每个父分类是否会导致循环
        for parent_id in parent_category_ids:
            if await self._would_create_cycle(new_category_id, parent_id):
                raise ValueError(f"添加父分类 {parent_id} 会导致循环引用")
        
        logger.info("✅ 循环检测通过")
    
    async def _would_create_cycle(
        self, 
        new_category_id: int, 
        potential_parent_id: int
    ) -> bool:
        """
        检查添加关系是否会导致循环
        
        Args:
            new_category_id: 新分类ID
            potential_parent_id: 潜在的父分类ID
            
        Returns:
            bool: 是否会导致循环
        """
        # 如果新分类ID等于潜在父分类ID，直接循环
        if new_category_id == potential_parent_id:
            return True
        
        # 使用 BFS 检查潜在父分类的所有祖先是否包含新分类
        visited = set()
        queue = deque([potential_parent_id])
        
        while queue:
            current_id = queue.popleft()
            if current_id in visited:
                continue
            visited.add(current_id)
            
            # 如果找到新分类ID，说明会形成循环
            if current_id == new_category_id:
                return True
            
            # 查找当前分类的所有父分类
            result = await self.db.execute(
                select(ProductCategoryRelation)
                .where(ProductCategoryRelation.child_category_id == current_id)
            )
            relations = result.scalars().all()
            
            for relation in relations:
                parent_id = relation.parent_category_id
                if parent_id not in visited:
                    queue.append(parent_id)
        
        return False
    
    async def add_parent_relation(
        self,
        category_id: int,
        parent_category_id: int,
        tenant_id: int
    ) -> ProductCategoryRelation:
        """
        添加父子关系
        
        Args:
            category_id: 子分类ID
            parent_category_id: 父分类ID
            tenant_id: 租户ID
            
        Returns:
            ProductCategoryRelation: 创建的关系
            
        Raises:
            ValueError: 如果会导致循环引用
        """
        logger.info("🔍 开始添加父子关系", 
                   category_id=category_id,
                   parent_category_id=parent_category_id)
        
        # 检查循环引用
        if await self._would_create_cycle(category_id, parent_category_id):
            raise ValueError("添加此关系会导致循环引用")
        
        # 检查关系是否已存在
        existing = await self.db.execute(
            select(ProductCategoryRelation)
            .where(
                and_(
                    ProductCategoryRelation.parent_category_id == parent_category_id,
                    ProductCategoryRelation.child_category_id == category_id
                )
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError("父子关系已存在")
        
        # 创建关系
        relation = ProductCategoryRelation(
            parent_category_id=parent_category_id,
            child_category_id=category_id
        )
        
        self.db.add(relation)
        await self.db.commit()
        
        logger.info("✅ 父子关系添加成功")
        
        return relation
    
    async def remove_parent_relation(
        self,
        category_id: int,
        parent_category_id: int
    ) -> bool:
        """
        移除父子关系
        
        Args:
            category_id: 子分类ID
            parent_category_id: 父分类ID
            
        Returns:
            bool: 是否成功移除
        """
        logger.info("🔍 开始移除父子关系", 
                   category_id=category_id,
                   parent_category_id=parent_category_id)
        
        result = await self.db.execute(
            select(ProductCategoryRelation)
            .where(
                and_(
                    ProductCategoryRelation.parent_category_id == parent_category_id,
                    ProductCategoryRelation.child_category_id == category_id
                )
            )
        )
        relation = result.scalar_one_or_none()
        
        if relation:
            await self.db.delete(relation)
            await self.db.commit()
            logger.info("✅ 父子关系移除成功")
            return True
        else:
            logger.warning("⚠️ 父子关系不存在")
            return False
    
    async def get_category_dimensions(
        self, 
        category_id: int, 
        tenant_id: int
    ) -> List[ProductCategoryDimension]:
        """
        获取分类的所有维度（包括继承的维度）
        
        Returns:
            List[ProductCategoryDimension]: 分类的维度列表
        """
        logger.info("🔍 开始获取分类维度", category_id=category_id)
        
        # 获取分类路径
        path = await self.get_category_path(category_id, tenant_id)
        category_ids = [cat.id for cat in path]
        
        # 获取所有维度
        result = await self.db.execute(
            select(ProductCategoryDimension)
            .where(ProductCategoryDimension.category_id.in_(category_ids))
            .options(selectinload(ProductCategoryDimension.dimension_template))
        )
        
        dimensions = result.scalars().all()
        
        logger.info("✅ 分类维度获取成功", 
                   category_id=category_id,
                   dimension_count=len(dimensions))
        
        return dimensions
    
    async def update_category(
        self,
        category_id: int,
        tenant_id: int,
        **update_data
    ) -> Optional[ProductCategory]:
        """
        更新分类信息
        
        Args:
            category_id: 分类ID
            tenant_id: 租户ID
            **update_data: 更新数据
            
        Returns:
            ProductCategory: 更新后的分类
        """
        logger.info("🔍 开始更新分类", category_id=category_id)
        
        category = await self.get_category_by_id(category_id, tenant_id)
        if not category:
            return None
        
        # 更新字段
        for key, value in update_data.items():
            if hasattr(category, key):
                setattr(category, key, value)
        
        await self.db.commit()
        
        logger.info("✅ 分类更新成功", category_id=category_id)
        
        return category
    
    async def delete_category(
        self,
        category_id: int,
        tenant_id: int,
        force: bool = False
    ) -> bool:
        """
        删除分类
        
        Args:
            category_id: 分类ID
            tenant_id: 租户ID
            force: 是否强制删除（包括子分类）
            
        Returns:
            bool: 是否成功删除
        """
        logger.info("🔍 开始删除分类", 
                   category_id=category_id,
                   force=force)
        
        category = await self.get_category_by_id(category_id, tenant_id)
        if not category:
            return False
        
        # 检查是否有子分类
        children_result = await self.db.execute(
            select(ProductCategoryRelation)
            .where(ProductCategoryRelation.parent_category_id == category_id)
        )
        children = children_result.scalars().all()
        
        if children and not force:
            raise ValueError("分类下有子分类，无法删除。使用 force=True 强制删除。")
        
        # 删除分类（级联删除关系）
        await self.db.delete(category)
        await self.db.commit()
        
        logger.info("✅ 分类删除成功", category_id=category_id)
        
        return True
