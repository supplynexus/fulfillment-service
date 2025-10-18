# Cursor Plan - PIM 核心架构实施

## 🎯 项目概述

基于 SupplyNexus Fulfillment Service 的 PIM（Product Information Management）核心架构重构，实现完整的产品信息管理系统，支持复杂的分类结构、维度管理和 SKU 批量操作。

## ✅ 已完成的核心功能

### 数据库架构
- ✅ **完整的 PIM 数据库设计** - 9个核心表，支持 DAG 分类、维度继承、属性合并
- ✅ **数据库迁移脚本** - Alembic 迁移，包含所有 PIM 核心表
- ✅ **索引优化策略** - 针对查询性能的索引设计

### 后端 Service 层
- ✅ **ProductCategoryService** - 分类管理 + 循环检测（BFS算法）
- ✅ **ProductDimensionService** - 维度管理 + 可选继承
- ✅ **ProductAttributeService** - 属性管理 + 合并逻辑
- ✅ **ProductVariantService** - SKU 批量创建 + 笛卡尔积生成
- ✅ **ProductCategorySwitchService** - 分类切换 + 维度迁移

### 后端 API 层
- ✅ **Product Categories API** - 分类 CRUD、树查询、关系管理
- ✅ **Product Dimensions API** - 维度模板、继承、维度值管理
- ✅ **Product Variants API** - SKU 管理、批量创建、笛卡尔积预览

## 🚀 下一步实施计划

### Phase 1: 前端核心页面（优先级：P0）

#### 1. SKU 列表页面 (`/skus`)
**目标**: 实现 SKU 中心的产品管理界面
- 动态列生成（根据分类维度）
- 筛选和排序功能
- 批量操作（删除、更新）
- 响应式设计

**技术要点**:
- 使用 React Query 管理数据状态
- 动态列组件支持维度列
- 虚拟滚动处理大量数据

#### 2. 产品分类配置页面 (`/product-categories`)
**目标**: 管理 DAG 分类结构
- 分类树展示（支持多父分类）
- 创建/编辑分类
- 添加/移除分类关系
- 分类维度管理

**技术要点**:
- 树形组件支持多父分类显示
- 拖拽排序和关系管理
- 循环检测提示

#### 3. 维度模板配置页面 (`/product-dimension-templates`)
**目标**: 管理维度模板和维度值
- 维度模板列表
- 创建/编辑维度模板
- 维度值管理
- 维度继承配置

**技术要点**:
- 表单验证和类型检查
- 维度值批量操作
- 继承关系可视化

#### 4. SKU 批量创建页面 (`/products/[id]/variants/batch-create`)
**目标**: 实现笛卡尔积 SKU 批量创建
- 维度值选择器
- 笛卡尔积预览表格
- 手动删除不需要的组合
- 批量创建功能

**技术要点**:
- 笛卡尔积算法实现
- 预览表格性能优化
- 批量操作进度显示

### Phase 2: 测试和优化（优先级：P1）

#### 5. 单元测试
- Service 层核心逻辑测试
- 循环检测算法测试
- 笛卡尔积生成测试
- 维度继承逻辑测试

#### 6. 集成测试
- API 端点测试
- 数据库操作测试
- 错误处理测试

#### 7. E2E 测试
- 完整的 SKU 创建流程
- 分类切换流程
- 维度继承流程

### Phase 3: 高级功能（优先级：P2）

#### 8. 分类切换警告对话框
- 不兼容维度检测
- 影响分析展示
- 处理方式选择

#### 9. 矩阵选择器（2维度）
- 可视化矩阵选择
- 精确控制组合
- 性能优化

#### 10. 列表视图配置
- 自定义列顺序
- 显示/隐藏列
- 用户偏好保存

## 🛠️ 技术架构

### 前端技术栈
- **Next.js 15.4.6** + **React 19.1.1** + **TypeScript 5.9.2**
- **MUI 7.3.1** - UI 组件库
- **TanStack React Query 5.12.2** - 数据状态管理
- **Zustand 4.4.7** - 全局状态管理
- **React Hook Form 7.48.2** + **Zod** - 表单处理

### 后端技术栈
- **FastAPI** - Web 框架
- **SQLAlchemy** - ORM
- **PostgreSQL** - 数据库
- **Alembic** - 数据库迁移

### 核心设计模式
- **DAG 分类结构** - 支持多父分类
- **维度继承** - 可选继承 + 覆盖
- **属性合并** - 维度值 > SKU 属性 > Product 属性
- **笛卡尔积生成** - SKU 批量创建

## 📋 关键文件清单

### 已完成的后端文件
```
backend/app/models/
├── product_dimension.py ✅
├── product_category.py ✅
└── product_attribute.py ✅

backend/app/services/
├── product_category_service.py ✅
├── product_dimension_service.py ✅
├── product_attribute_service.py ✅
├── product_variant_service.py ✅
└── product_category_switch_service.py ✅

backend/app/api/v1/endpoints/
├── product_categories.py ✅
├── product_dimensions.py ✅
└── product_variants.py ✅
```

### 待实现的前端文件
```
frontend/src/app/
├── skus/
│   ├── page.tsx 🔄
│   └── components/
│       ├── SkuList.tsx 🔄
│       └── DynamicColumns.tsx 🔄
├── product-categories/
│   ├── page.tsx 🔄
│   └── components/
│       ├── CategoryTree.tsx 🔄
│       └── CategoryDimensionManager.tsx 🔄
├── product-dimension-templates/
│   ├── page.tsx 🔄
│   └── components/
│       ├── DimensionTemplateList.tsx 🔄
│       └── DimensionValueManager.tsx 🔄
└── products/
    └── [id]/
        └── variants/
            └── batch-create/
                ├── page.tsx 🔄
                └── components/
                    ├── CartesianGenerator.tsx 🔄
                    └── SkuPreviewTable.tsx 🔄
```

## 🎯 验收标准

### Phase 1 (MVP) - 当前目标
- [ ] SKU 列表页面支持动态列
- [ ] 产品分类配置页面支持 DAG 结构
- [ ] 维度模板配置页面完整功能
- [ ] SKU 批量创建页面支持笛卡尔积
- [ ] 所有核心 API 正常工作
- [ ] 基础功能测试通过

### Phase 2 (增强)
- [ ] 完整的测试覆盖
- [ ] 性能优化
- [ ] 错误处理完善
- [ ] 用户体验优化

### Phase 3 (高级)
- [ ] 分类切换警告功能
- [ ] 矩阵选择器
- [ ] 列表视图配置
- [ ] 高级批量操作

## 🚨 风险与挑战

### 技术风险
1. **动态列性能** - 大量 SKU 时的渲染性能
2. **笛卡尔积组合爆炸** - 维度值过多时的性能问题
3. **DAG 循环检测** - 复杂分类关系的性能影响

### 缓解措施
1. **虚拟滚动** - 处理大量数据
2. **组合数量限制** - 前端限制最大组合数
3. **缓存优化** - 分类关系缓存
4. **分页加载** - 大数据集分页处理

## 📅 时间估算

### Phase 1: 前端核心页面
- SKU 列表页面：2 天
- 产品分类配置页面：2 天
- 维度模板配置页面：2 天
- SKU 批量创建页面：3 天
- **总计：9 天（约 2 周）**

### Phase 2: 测试和优化
- 单元测试：2 天
- 集成测试：2 天
- E2E 测试：2 天
- 性能优化：2 天
- **总计：8 天（约 1.5 周）**

### Phase 3: 高级功能
- 分类切换警告：1 天
- 矩阵选择器：2 天
- 列表视图配置：1 天
- **总计：4 天（约 1 周）**

**整体预计：21 天（约 4 周）**

## 🎉 项目亮点

### 技术创新
- **DAG 分类结构** - 支持复杂的产品分类关系
- **维度继承系统** - 灵活的产品属性管理
- **笛卡尔积生成** - 高效的 SKU 批量创建
- **属性合并逻辑** - 智能的属性优先级处理

### 业务价值
- **提升效率** - SKU 批量创建节省大量时间
- **灵活管理** - 支持复杂的产品分类需求
- **数据一致性** - 统一的 PIM 数据模型
- **用户体验** - 直观的界面设计

## 📞 下一步行动

1. **立即开始** - SKU 列表页面开发
2. **并行开发** - 分类配置和维度模板页面
3. **测试驱动** - 每个功能完成后立即测试
4. **持续优化** - 根据用户反馈调整功能

---

**状态**: 🚀 后端核心架构已完成，准备开始前端开发
**优先级**: P0 - 前端核心页面开发
**预计完成**: 4 周内完成 MVP 版本
