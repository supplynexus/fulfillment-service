# 订单自动化功能使用指南

## 概述

订单自动化功能实现了从Shopify订单到Printify发货的完整自动化流程，包括：

1. **Shopify订单同步** → 本地订单
2. **自动创建SCM订单** → 订单路由决策
3. **自动调用Printify API** → 创建发货单
4. **状态同步** → Printify状态同步到SCM
5. **Shopify履约更新** → 自动更新Shopify订单状态

## 核心功能

### 1. 订单追踪链

每个订单都有完整的追踪链：

```
Shopify订单ID → 本地Order.id → SCM订单ID → Printify订单ID
```

**关键字段映射：**
- `Order.shopify_order_id` - Shopify订单ID
- `SCMOrder.source_order_id` - 关联的本地订单ID
- `SCMOrder.shopify_order_id` - 直接引用Shopify订单ID
- `SCMOrder.printify_order_id` - Printify订单ID

### 2. 自动化任务

系统包含以下自动化任务：

#### 定时任务
- **每2分钟**：处理新的Shopify订单
- **每5分钟**：同步Printify订单状态
- **每10分钟**：同步SCM订单到Shopify履约

#### 手动触发任务
- 处理Shopify订单
- 同步Printify状态
- 同步Shopify履约
- 完整同步流程

### 3. API端点

#### 手动触发API

**处理Shopify订单**
```bash
POST /api/v1/automation/process-shopify-orders
?tenant_id=1&limit=50
```

**同步Printify状态**
```bash
POST /api/v1/automation/sync-printify-status
?tenant_id=1&limit=100
```

**同步Shopify履约**
```bash
POST /api/v1/automation/sync-shopify-fulfillment
?tenant_id=1&limit=100
```

**完整同步流程**
```bash
POST /api/v1/automation/sync-all
?tenant_id=1&process_limit=50&sync_limit=100
```

**查看任务状态**
```bash
GET /api/v1/automation/task-status/{task_id}
```

## 部署指南

### 1. 数据库迁移

在部署前，需要运行数据库迁移：

```bash
# 在Docker容器中运行
docker-compose run --rm backend python -m alembic upgrade head
```

### 2. 部署新功能

使用提供的部署脚本：

**Windows:**
```cmd
scripts\deploy_order_automation.bat
```

**Linux/Mac:**
```bash
./scripts/deploy_order_automation.sh
```

### 3. 验证部署

检查服务状态：
```bash
docker-compose ps
```

检查服务健康状态：
```bash
curl http://localhost:8000/health
```

## 配置说明

### 1. 环境变量

确保以下环境变量已正确配置：

```env
# 数据库配置
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/dbname

# Redis配置（Celery）
REDIS_URL=redis://localhost:6379/0

# Shopify配置
SHOPIFY_API_VERSION=2024-10

# Printify配置
PRINTIFY_API_URL=https://api.printify.com
```

### 2. 外部系统配置

在系统中配置以下外部系统：

1. **Shopify系统**
   - 系统类型：`SHOPIFY`
   - 必需字段：`access_token`, `store_url`

2. **Printify系统**
   - 系统类型：`PRINTIFY`
   - 必需字段：`access_token`, `shop_id`

### 3. 订单路由规则

配置订单路由规则，决定订单如何路由到不同的SCM系统：

```json
{
  "name": "Printify路由规则",
  "conditions": {
    "product_types": ["print_on_demand"],
    "regions": ["US", "CA", "EU"]
  },
  "target_system_type": "PRINTIFY",
  "priority": 1
}
```

## 监控和日志

### 1. 查看日志

**后端服务日志：**
```bash
docker-compose logs -f backend
```

**Celery Worker日志：**
```bash
docker-compose logs -f celery-worker
```

**Celery Beat日志：**
```bash
docker-compose logs -f celery-beat
```

### 2. 监控指标

系统提供以下监控指标：

- 订单处理成功率
- 各步骤执行时间
- 错误率和重试次数
- 队列长度和处理速度

### 3. 错误处理

系统包含完善的错误处理机制：

- **自动重试**：网络错误自动重试3次
- **指数退避**：重试间隔逐渐增加
- **错误日志**：详细记录错误信息和堆栈
- **手动干预**：支持手动重新处理失败的订单

## 故障排除

### 1. 常见问题

**订单没有自动处理**
- 检查Celery Worker是否运行
- 检查订单路由规则配置
- 查看错误日志

**Printify订单创建失败**
- 检查Printify凭据配置
- 验证商品ID和变体ID
- 检查地址格式

**Shopify履约更新失败**
- 检查Shopify凭据配置
- 验证订单ID格式
- 检查网络连接

### 2. 调试步骤

1. **检查服务状态**
   ```bash
   docker-compose ps
   ```

2. **查看错误日志**
   ```bash
   docker-compose logs backend | grep ERROR
   ```

3. **手动触发任务**
   ```bash
   curl -X POST "http://localhost:8000/api/v1/automation/process-shopify-orders?tenant_id=1&limit=1"
   ```

4. **检查数据库状态**
   ```sql
   SELECT * FROM orders WHERE shopify_order_id IS NOT NULL LIMIT 5;
   SELECT * FROM scm_orders WHERE printify_order_id IS NOT NULL LIMIT 5;
   ```

## 性能优化

### 1. 队列配置

建议为不同类型的任务配置不同的队列：

```python
# 高优先级队列
'queue': 'order_automation'

# 普通队列
'queue': 'shopify'

# 低优先级队列
'queue': 'sync'
```

### 2. 批处理大小

根据系统性能调整批处理大小：

- **订单处理**：50-100个/批次
- **状态同步**：100-500个/批次
- **履约同步**：100-500个/批次

### 3. 并发控制

控制并发任务数量，避免API限制：

```python
# Celery配置
CELERY_WORKER_CONCURRENCY = 4
CELERY_TASK_CONCURRENCY = 2
```

## 扩展功能

### 1. 自定义SCM系统

可以添加其他SCM系统支持：

1. 创建新的SCM服务类
2. 实现订单创建和状态同步方法
3. 配置路由规则

### 2. 通知系统

添加订单状态变更通知：

- 邮件通知
- 短信通知
- Webhook通知

### 3. 数据分析

添加订单处理数据分析：

- 处理时间统计
- 成功率分析
- 成本分析

## 安全考虑

### 1. 凭据安全

- 所有外部系统凭据都加密存储
- 使用环境变量管理敏感信息
- 定期轮换API密钥

### 2. 访问控制

- API端点需要认证
- 租户隔离
- 操作审计日志

### 3. 数据保护

- 敏感数据加密
- 定期备份
- 数据保留策略

## 更新和维护

### 1. 定期更新

- 监控外部API版本更新
- 及时更新依赖包
- 测试新功能兼容性

### 2. 性能监控

- 监控系统资源使用
- 分析处理性能
- 优化瓶颈环节

### 3. 备份策略

- 定期备份数据库
- 备份配置文件
- 测试恢复流程
