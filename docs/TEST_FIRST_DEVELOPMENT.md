# 测试优先开发规范 (Test-First Development)

## 概述

本项目强制执行测试优先开发（Test-First Development）规范，确保代码质量和可维护性。

## 开发流程

### 1. Red-Green-Refactor 循环

1. **Red（红色）**：编写失败的测试用例
2. **Green（绿色）**：编写最少的代码使测试通过
3. **Refactor（重构）**：重构代码，保持测试通过

### 2. 强制要求

- ✅ **在编写任何功能代码之前，必须先编写测试用例**
- ✅ **所有 API 端点必须有对应的测试用例**
- ✅ **所有服务层方法必须有单元测试**
- ✅ **所有数据库操作必须有集成测试**
- ✅ **前端组件必须有组件测试**

## 测试覆盖要求

### 后端测试

#### API 端点测试
```python
# 示例：测试产品映射创建 API
def test_create_product_mapping_success():
    """测试成功创建产品映射"""
    # Given: 准备测试数据
    # When: 调用 API
    # Then: 验证结果

def test_create_product_mapping_invalid_data():
    """测试无效数据创建产品映射"""
    # Given: 准备无效数据
    # When: 调用 API
    # Then: 验证错误响应

def test_create_product_mapping_unauthorized():
    """测试未授权创建产品映射"""
    # Given: 无认证信息
    # When: 调用 API
    # Then: 验证 401 错误
```

#### 服务层测试
```python
# 示例：测试 Printify 产品服务
def test_sync_products_from_api():
    """测试从 API 同步产品"""
    # Given: Mock API 响应
    # When: 调用同步方法
    # Then: 验证产品被正确保存

def test_filter_valid_variants():
    """测试过滤有效变体"""
    # Given: 包含有效和无效变体的数据
    # When: 调用过滤方法
    # Then: 验证只返回有效变体
```

#### 数据库测试
```python
# 示例：测试数据库操作
def test_create_printify_product():
    """测试创建 Printify 产品"""
    # Given: 产品数据
    # When: 保存到数据库
    # Then: 验证数据正确保存

def test_product_mapping_constraints():
    """测试产品映射约束"""
    # Given: 重复的映射数据
    # When: 尝试创建映射
    # Then: 验证约束错误
```

### 前端测试

#### 组件测试
```typescript
// 示例：测试变体映射对话框
describe('VariantMappingDialog', () => {
  it('should render variant mapping form', () => {
    // Given: 组件 props
    // When: 渲染组件
    // Then: 验证表单元素存在
  });

  it('should handle variant selection', () => {
    // Given: 组件已渲染
    // When: 选择变体
    // Then: 验证状态更新
  });

  it('should validate mapping data before submission', () => {
    // Given: 无效的映射数据
    // When: 提交表单
    // Then: 验证错误提示
  });
});
```

#### API 调用测试
```typescript
// 示例：测试 API 调用
describe('PrintifyProducts API', () => {
  it('should fetch products successfully', async () => {
    // Given: Mock API 响应
    // When: 调用 fetchProducts
    // Then: 验证数据正确返回
  });

  it('should handle API errors', async () => {
    // Given: Mock API 错误
    // When: 调用 fetchProducts
    // Then: 验证错误处理
  });
});
```

## 测试质量标准

### 1. 测试用例要求
- **清晰性**：测试用例名称和注释必须清晰描述测试目的
- **独立性**：每个测试用例必须独立，不依赖其他测试
- **可重复性**：测试用例必须能够重复执行并得到相同结果
- **快速性**：单元测试必须在毫秒级完成

### 2. 测试覆盖率
- **最低要求**：80% 代码覆盖率
- **目标**：90% 代码覆盖率
- **关键路径**：100% 覆盖率（如支付、订单处理等）

### 3. 测试组织
```
tests/
├── unit/                    # 单元测试
│   ├── test_services/      # 服务层测试
│   ├── test_models/        # 模型测试
│   └── test_utils/         # 工具函数测试
├── integration/            # 集成测试
│   ├── test_api/          # API 集成测试
│   └── test_database/     # 数据库集成测试
├── e2e/                   # 端到端测试
│   ├── test_product_flow/ # 产品流程测试
│   └── test_order_flow/   # 订单流程测试
└── fixtures/              # 测试数据
    ├── products.json
    └── orders.json
```

## 强制执行规则

### 1. 开发阶段
- ❌ **禁止**：在没有任何测试的情况下编写功能代码
- ❌ **禁止**：跳过测试直接部署
- ❌ **禁止**：提交没有对应测试的代码

### 2. 代码审查
- ✅ **必须**：所有 Pull Request 必须包含测试用例
- ✅ **必须**：所有测试必须通过才能合并代码
- ✅ **必须**：审查测试用例的质量和覆盖率

### 3. 持续集成
- ✅ **必须**：CI/CD 流水线必须运行所有测试
- ✅ **必须**：测试失败时阻止部署
- ✅ **必须**：定期生成测试覆盖率报告

## 测试工具和框架

### 后端测试
- **pytest**：Python 测试框架
- **pytest-asyncio**：异步测试支持
- **pytest-cov**：代码覆盖率
- **httpx**：HTTP 客户端测试
- **factory_boy**：测试数据工厂

### 前端测试
- **Jest**：JavaScript 测试框架
- **React Testing Library**：React 组件测试
- **Cypress**：端到端测试
- **MSW**：API 模拟

## 示例：实现新功能的测试优先流程

### 1. 编写测试用例（Red）
```python
def test_create_variant_mapping():
    """测试创建变体映射"""
    # Given
    core_product_id = "test-core-product"
    printify_variant_id = "test-printify-variant"
    
    # When
    result = create_variant_mapping(
        core_product_id=core_product_id,
        printify_variant_id=printify_variant_id
    )
    
    # Then
    assert result.success is True
    assert result.mapping_id is not None
```

### 2. 编写最少代码使测试通过（Green）
```python
def create_variant_mapping(core_product_id: str, printify_variant_id: str):
    """创建变体映射"""
    # 最简单的实现
    return MappingResult(success=True, mapping_id="temp-id")
```

### 3. 重构代码（Refactor）
```python
def create_variant_mapping(core_product_id: str, printify_variant_id: str):
    """创建变体映射"""
    # 完整的实现
    mapping = ProductMapping(
        core_product_id=core_product_id,
        printify_variant_id=printify_variant_id
    )
    db.add(mapping)
    db.commit()
    return MappingResult(success=True, mapping_id=mapping.id)
```

## 检查清单

在提交代码前，请确保：

- [ ] 所有新功能都有对应的测试用例
- [ ] 所有测试用例都能通过
- [ ] 测试覆盖率达到要求
- [ ] 测试用例覆盖正常情况、边界情况和异常情况
- [ ] 测试用例独立且可重复
- [ ] 测试用例名称清晰描述测试目的
- [ ] 代码审查包含测试用例审查

## 违反规范的后果

- **轻微违反**：代码审查时要求补充测试用例
- **严重违反**：拒绝合并 Pull Request
- **重复违反**：暂停开发权限，要求重新学习测试优先开发

---

**记住：测试不是负担，而是保障。好的测试让代码更可靠，开发更高效。**
