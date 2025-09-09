# SCM订单路由系统

## 概述

SCM订单路由系统是一个智能的订单分发解决方案，能够根据预设规则将Shopify订单自动路由到不同的供应链管理(SCM)系统，如Printify、自定义履约服务等。

## 核心功能

### 1. 智能路由策略
- **自动路由**: 基于商品类型、数量、供应商等条件自动分配
- **手动路由**: 指定目标系统进行精确控制
- **混合路由**: 结合自动和手动路由策略

### 2. 灵活的路由规则
- 支持多维度条件匹配（产品类型、数量、地区、供应商等）
- 优先级排序和规则冲突处理
- 动态规则启用/禁用

### 3. 完整的订单生命周期管理
- SCM订单创建和状态跟踪
- 履约状态同步
- 错误处理和重试机制

## API端点

### 订单路由
```http
# 单个订单路由
POST /api/v1/routing/orders/{order_id}/route-to-scm

# 批量订单路由
POST /api/v1/routing/orders/route-to-scm/batch

# 后台异步路由
POST /api/v1/routing/orders/{order_id}/route-to-scm/background

# 查询路由状态
GET /api/v1/routing/orders/{order_id}/routing-status
```

### SCM订单管理
```http
# 获取SCM订单列表
GET /api/v1/scm-orders/

# 获取SCM订单详情
GET /api/v1/scm-orders/{scm_order_id}

# 根据原始订单获取SCM订单
GET /api/v1/scm-orders/order/{order_id}

# 创建SCM订单
POST /api/v1/scm-orders/

# 更新SCM订单
PUT /api/v1/scm-orders/{scm_order_id}

# 删除SCM订单
DELETE /api/v1/scm-orders/{scm_order_id}
```

### 路由规则管理
```http
# 获取路由规则列表
GET /api/v1/routing-rules/

# 获取路由规则详情
GET /api/v1/routing-rules/{rule_id}

# 创建路由规则
POST /api/v1/routing-rules/

# 更新路由规则
PUT /api/v1/routing-rules/{rule_id}

# 删除路由规则
DELETE /api/v1/routing-rules/{rule_id}

# 测试路由规则
POST /api/v1/routing-rules/{rule_id}/test
```

## 使用示例

### 1. 创建路由规则

```json
POST /api/v1/routing-rules/
{
  "name": "Printify Apparel Rule",
  "description": "将服装类商品路由到Printify",
  "conditions": {
    "product_types": ["apparel", "clothing"],
    "max_quantity": 100,
    "vendors": ["BrandA", "BrandB"]
  },
  "target_system_type": "printify",
  "target_system_id": "printify_system_1",
  "priority": 1,
  "is_active": true
}
```

### 2. 自动路由订单

```json
POST /api/v1/routing/orders/123/route-to-scm
{
  "routing_strategy": "auto",
  "routing_rules": {
    "auto_route_enabled": true,
    "default_target_system": "printify"
  }
}
```

### 3. 手动路由订单

```json
POST /api/v1/routing/orders/123/route-to-scm
{
  "routing_strategy": "manual",
  "target_systems": [
    {
      "system_type": "printify",
      "system_id": "printify_system_1",
      "priority": 1,
      "conditions": {
        "product_types": ["apparel"],
        "max_quantity": 50
      }
    }
  ]
}
```

### 4. 批量路由订单

```json
POST /api/v1/routing/orders/route-to-scm/batch
{
  "order_ids": [123, 124, 125],
  "routing_strategy": "auto",
  "batch_processing": {
    "group_by_customer": true,
    "group_by_region": true,
    "optimize_shipping": true
  }
}
```

## 路由规则条件

### 支持的条件类型

1. **产品类型匹配**
   ```json
   {
     "product_types": ["apparel", "electronics", "accessories"]
   }
   ```

2. **数量限制**
   ```json
   {
     "max_quantity": 100,
     "min_quantity": 1
   }
   ```

3. **供应商匹配**
   ```json
   {
     "vendors": ["VendorA", "VendorB"]
   }
   ```

4. **SKU匹配**
   ```json
   {
     "skus": ["SKU001", "SKU002"]
   }
   ```

5. **地区匹配**
   ```json
   {
     "regions": ["US", "CA", "EU"]
   }
   ```

6. **价格范围**
   ```json
   {
     "min_price": 10.00,
     "max_price": 100.00
   }
   ```

## 系统集成

### 与Shopify集成

系统支持与Shopify FulfillmentOrder API集成：

1. **创建履约请求**
   ```python
   # 使用Shopify GraphQL API
   mutation = """
   mutation fulfillmentOrderSubmitFulfillmentRequest($id: ID!) {
     fulfillmentOrderSubmitFulfillmentRequest(id: $id) {
       submittedFulfillmentOrder {
         id
         status
       }
     }
   }
   """
   ```

2. **更新履约状态**
   ```python
   # 监听Shopify webhook
   @router.post("/webhooks/shopify/fulfillments/update")
   async def handle_fulfillment_update(webhook_data: dict):
       # 更新SCM订单状态
       pass
   ```

### 与外部SCM系统集成

支持多种SCM系统：

1. **Printify集成**
   - 自动创建Printify订单
   - 同步订单状态
   - 处理履约回调

2. **自定义履约服务**
   - RESTful API集成
   - Webhook回调处理
   - 自定义状态映射

## 监控和日志

### 路由状态跟踪

系统提供完整的路由状态跟踪：

```json
{
  "order_id": 123,
  "total_scm_orders": 2,
  "scm_orders": [
    {
      "scm_order_id": 456,
      "scm_order_number": "SCM-20240101-ABC123",
      "target_system": "printify",
      "status": "processing",
      "created_at": "2024-01-01T10:00:00Z"
    }
  ]
}
```

### 错误处理

- 自动重试机制
- 错误日志记录
- 失败通知
- 手动干预支持

## 部署和配置

### 数据库迁移

```bash
# 运行迁移
cd backend
python -m alembic upgrade head
```

### 环境配置

```env
# SCM系统配置
PRINTIFY_API_URL=https://api.printify.com
PRINTIFY_API_TOKEN=your_token

# 路由配置
DEFAULT_ROUTING_STRATEGY=auto
AUTO_ROUTE_ENABLED=true
```

### 后台任务

系统使用Celery进行后台任务处理：

```python
# 启动Celery worker
celery -A app.tasks.celery_app worker --loglevel=info

# 启动Celery beat (定时任务)
celery -A app.tasks.celery_app beat --loglevel=info
```

## 测试

运行测试脚本验证功能：

```bash
cd backend
python test_scm_routing.py
```

## 扩展性

### 添加新的SCM系统

1. 实现SCM系统接口
2. 添加路由规则支持
3. 配置webhook处理
4. 更新状态映射

### 自定义路由逻辑

1. 扩展路由条件
2. 实现自定义路由策略
3. 添加成本优化算法
4. 集成机器学习预测

## 最佳实践

1. **规则设计**
   - 使用明确的优先级
   - 避免规则冲突
   - 定期审查和优化

2. **性能优化**
   - 批量处理订单
   - 异步路由处理
   - 缓存路由规则

3. **错误处理**
   - 实现重试机制
   - 监控路由失败率
   - 提供手动干预接口

4. **安全考虑**
   - 验证外部系统调用
   - 加密敏感数据
   - 审计路由决策
