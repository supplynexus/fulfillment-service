# Shopify 订单同步功能实现总结

## 概述

本次实现了完整的 Shopify 订单同步功能，包括：
- 从 Shopify 获取订单数据
- 同步到本地数据库
- 定时任务调度（每分钟同步）
- API 端点管理
- 完整的错误处理和日志记录

## 实现的功能

### 1. 核心服务层

#### ShopifyOrderService (`app/services/shopify/order_service.py`)
- **凭据管理**: 从数据库获取和解密 Shopify 凭据
- **数据转换**: 将 Shopify 订单数据转换为本地 schema
- **同步逻辑**: 增量同步，支持更新现有订单和创建新订单
- **查询功能**: 按状态、时间范围查询订单

#### 主要方法：
- `get_shopify_credentials()` - 获取 Shopify 凭据
- `sync_orders()` - 同步订单到本地数据库
- `get_recent_orders()` - 获取最近订单
- `get_orders_by_status()` - 按状态获取订单

### 2. 任务调度层

#### Celery 任务 (`app/tasks/shopify_tasks.py`)
- **同步任务**: `sync_shopify_orders_task` - 手动触发同步
- **定时任务**: `sync_shopify_orders_1min_task` - 每分钟自动同步
- **进度跟踪**: 实时更新任务进度和状态
- **错误处理**: 完整的异常捕获和日志记录

#### 定时任务配置 (`app/tasks/celery_beat_schedule.py`)
- **每分钟同步**: 只同步最近1小时的订单
- **每小时同步**: 全量同步，最多1000个订单
- **每天同步**: 凌晨2点全量同步所有订单

### 3. API 接口层

#### 订单管理端点 (`app/api/v1/endpoints/orders.py`)
- `GET /orders/` - 获取订单列表
- `POST /orders/sync` - 手动触发同步
- `POST /orders/sync/background` - 后台异步同步
- `GET /orders/recent` - 获取最近订单
- `GET /orders/status/{status}` - 按状态获取订单

### 4. 数据模型层

#### 订单 Schema (`app/schemas/order.py`)
- `OrderCreate` - 创建订单的 schema
- `OrderResponse` - 订单响应 schema
- `OrderListResponse` - 订单列表响应
- `OrderSyncResponse` - 同步结果响应

## 技术架构

### 数据流
```
Shopify API → ShopifyOrderService → 本地数据库
                ↓
            Celery 任务
                ↓
            API 端点
```

### 组件关系
- **Shopify GraphQL Client**: 负责与 Shopify API 通信
- **ShopifyOrderService**: 业务逻辑处理和数据转换
- **Celery Tasks**: 异步任务执行和调度
- **API Endpoints**: 对外提供 RESTful 接口

## 配置说明

### 环境变量
```bash
# 数据库配置
DATABASE_URL=postgresql+asyncpg://...

# Redis 配置 (Celery)
REDIS_URL=redis://localhost:6380/0
CELERY_BROKER_URL=redis://localhost:6380/1
CELERY_RESULT_BACKEND=redis://localhost:6380/2

# Shopify 配置 (可选，优先使用数据库中的凭据)
SHOPIFY_SHOP_NAME=your-shop-name
SHOPIFY_ACCESS_TOKEN=your-access-token
```

### 数据库配置
需要在 `external_systems` 表中配置 Shopify 外部系统：
```sql
INSERT INTO external_systems (
    tenant_id, 
    system_type, 
    name, 
    credentials,
    is_active
) VALUES (
    1, 
    'shopify', 
    'Main Shopify Store',
    '{"access_token": "encrypted_token", "store_url": "your-store.myshopify.com"}',
    true
);
```

## 使用方法

### 1. 启动服务

#### 启动 Celery Worker 和 Beat
```bash
# 在 backend 目录下
./scripts/start_celery.sh
```

#### 启动 FastAPI 服务
```bash
# 在 backend 目录下
source .venv/bin/activate
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. 测试功能

#### 测试订单同步
```bash
# 测试同步功能
PYTHONPATH=. python scripts/test_order_sync.py
```

#### 手动触发同步
```bash
# 使用 API
curl -X POST "http://localhost:8000/api/v1/orders/sync" \
  -H "Authorization: Bearer your-api-key"
```

### 3. 监控和日志

#### 查看 Celery 状态
```bash
./scripts/stop_celery.sh  # 选择选项 2
```

#### 查看日志
```bash
# Worker 日志
tail -f logs-local/celery-worker.log

# Beat 日志
tail -f logs-local/celery-beat.log
```

## 定时任务说明

### 任务频率
1. **每分钟同步** (`sync-shopify-orders-1min`)
   - 频率: 每60秒
   - 范围: 最近1小时的订单
   - 队列: shopify

2. **每小时同步** (`sync-shopify-orders-hourly`)
   - 频率: 每小时整点
   - 范围: 全量同步，最多1000个订单
   - 队列: shopify

3. **每天同步** (`sync-shopify-orders-daily`)
   - 频率: 每天凌晨2点
   - 范围: 全量同步所有订单
   - 队列: shopify

### 任务配置
- **并发数**: 2个 worker
- **队列**: default, shopify, orders
- **任务超时**: 30分钟
- **结果保存**: 1小时

## 错误处理

### 常见错误
1. **凭据错误**: 无法获取或解密 Shopify 凭据
2. **API 错误**: Shopify API 调用失败
3. **数据库错误**: 数据库连接或操作失败
4. **数据格式错误**: 订单数据格式不正确

### 重试机制
- Celery 任务支持自动重试
- 数据库事务回滚
- 详细的错误日志记录

## 性能优化

### 同步策略
- **增量同步**: 只同步最近1小时的订单
- **批量处理**: 支持限制同步订单数量
- **并发控制**: 使用 Celery 队列管理任务

### 数据库优化
- **索引**: 在关键字段上建立索引
- **事务**: 使用数据库事务确保数据一致性
- **连接池**: 使用异步数据库连接

## 监控和维护

### 监控指标
- 同步成功率
- 同步订单数量
- 任务执行时间
- 错误率

### 维护任务
- 定期清理过期任务结果
- 监控 Celery 进程状态
- 检查数据库连接健康状态

## 扩展计划

### 短期计划
1. **Webhook 支持**: 实现 Shopify webhook 处理
2. **订单状态更新**: 支持订单状态变更同步
3. **批量操作**: 支持批量订单处理

### 长期计划
1. **多租户支持**: 完善多租户订单隔离
2. **性能优化**: 进一步优化同步性能
3. **监控面板**: 开发订单同步监控界面

## 文件结构

```
backend/
├── app/
│   ├── services/shopify/
│   │   └── order_service.py          # 订单同步服务
│   ├── tasks/
│   │   ├── shopify_tasks.py          # Shopify 任务
│   │   ├── celery_app.py             # Celery 配置
│   │   └── celery_beat_schedule.py   # 定时任务配置
│   ├── api/v1/endpoints/
│   │   └── orders.py                 # 订单 API 端点
│   └── schemas/
│       └── order.py                  # 订单数据模型
├── scripts/
│   ├── test_order_sync.py            # 测试脚本
│   ├── start_celery.sh               # 启动脚本
│   └── stop_celery.sh                # 停止脚本
└── docs/
    └── SHOPIFY_ORDER_SYNC_IMPLEMENTATION.md  # 本文档
```

## 总结

本次实现提供了完整的 Shopify 订单同步解决方案，包括：

✅ **核心功能**: 订单数据获取、转换、存储
✅ **定时任务**: 每分钟自动同步
✅ **API 接口**: 完整的 RESTful API
✅ **错误处理**: 完善的异常处理和日志
✅ **监控工具**: Celery 状态监控和日志查看
✅ **测试工具**: 完整的测试脚本

该实现为 fulfillment service 提供了可靠的订单数据基础，支持后续的订单处理和履约功能开发。
