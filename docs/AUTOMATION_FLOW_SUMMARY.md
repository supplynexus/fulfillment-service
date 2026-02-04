# 自动化流程总结

## 完整的订单自动化流程（9个步骤）

所有步骤都是独立的，可以在画面上单独控制开关，默认每30分钟执行一次。

### 订单同步流程（步骤1-2）

#### 1. `sync_external_orders` - Shopify API → shopify_orders 本地表
- **任务函数**: `sync_shopify_orders_1min`
- **功能**: 从Shopify API同步订单到本地 `shopify_orders` 表
- **时间限制**: 只同步最近一周的订单
- **默认启用**: ✅ 是
- **调度**: 每30分钟

#### 2. `sync_to_core_orders` - shopify_orders 本地表 → 核心订单表
- **任务函数**: `sync_shopify_orders_to_core`
- **功能**: 从 `shopify_orders` 表同步订单到核心 `orders` 表（含地址验证）
- **默认启用**: ❌ 否（需要手动启用）
- **调度**: 每30分钟

### 订单处理流程（步骤3-4）

#### 3. `create_scm_orders` - 核心订单 → SCM订单
- **任务函数**: `process_new_orders_to_scm`
- **功能**: 从核心订单选择商品创建SCM订单
- **默认启用**: ✅ 是
- **调度**: 每30分钟

#### 4. `create_printify_orders_from_scm` - SCM订单 → Printify API
- **任务函数**: `create_printify_orders_from_scm`
- **功能**: 从SCM订单批量创建Printify订单（调用Printify API）
- **默认启用**: ✅ 是
- **调度**: 每30分钟

### Printify订单同步流程（步骤5-6）

#### 5. `sync_printify_orders_to_local` - Printify API → printify_orders 本地表
- **任务函数**: `sync_printify_orders_to_local`
- **功能**: 从Printify API同步订单到本地 `printify_orders` 表
- **时间限制**: 只同步最近一周的订单
- **默认启用**: ✅ 是
- **调度**: 每30分钟

#### 6. `sync_fulfillment_status` - printify_orders 本地表 → SCM订单
- **任务函数**: `sync_printify_orders_status`
- **功能**: 从 `printify_orders` 本地表同步发货信息到SCM订单
- **注意**: 已改为从本地表读取，不再直接从API读取
- **默认启用**: ✅ 是
- **调度**: 每30分钟

### Shopify发货信息同步流程（步骤7-9）

#### 7. `sync_to_external_fulfillment` - SCM订单 → Shopify API
- **任务函数**: `sync_scm_to_shopify_fulfillment`
- **功能**: 将SCM订单状态同步回Shopify履约系统（调用Shopify API）
- **默认启用**: ✅ 是
- **调度**: 每30分钟

#### 8. `sync_shopify_fulfillment_to_local` - Shopify API → shopify_orders 本地表
- **任务函数**: `sync_shopify_fulfillment_to_local`
- **功能**: 从Shopify API同步发货信息到 `shopify_orders` 本地表
- **时间限制**: 只同步最近一周的订单
- **默认启用**: ✅ 是
- **调度**: 每30分钟

#### 9. `sync_shopify_local_fulfillment_to_core` - shopify_orders 本地表 → 核心订单表
- **任务函数**: `sync_shopify_local_fulfillment_to_core`
- **功能**: 从 `shopify_orders` 本地表同步发货信息到核心订单表
- **默认启用**: ✅ 是
- **调度**: 每30分钟

---

## 流程架构原则

### 两步架构
所有外部系统同步都必须分为两步：
1. **步骤1**: 外部API → 本地表（如 `shopify_orders`、`printify_orders`）
2. **步骤2**: 本地表 → 核心表（如 `orders`）

**禁止直接从外部API同步到核心订单表**

### 单步可控
- 每个步骤都是独立的Celery任务
- 可以在画面上单独控制开关
- 每个步骤都有独立的调度配置

### 统一调度
- 所有步骤默认每30分钟执行一次
- 可以通过 `tenant_automation_configs` 表自定义调度时间

---

## 数据流向图

```
Shopify API
    ↓ (步骤1: sync_external_orders)
shopify_orders 表
    ↓ (步骤2: sync_to_core_orders)
核心 orders 表
    ↓ (步骤3: create_scm_orders)
SCM orders 表
    ↓ (步骤4: create_printify_orders_from_scm)
Printify API
    ↓ (步骤5: sync_printify_orders_to_local)
printify_orders 表
    ↓ (步骤6: sync_fulfillment_status)
SCM orders 表 (更新发货信息)
    ↓ (步骤7: sync_to_external_fulfillment)
Shopify API (更新履约信息)
    ↓ (步骤8: sync_shopify_fulfillment_to_local)
shopify_orders 表 (更新发货信息)
    ↓ (步骤9: sync_shopify_local_fulfillment_to_core)
核心 orders 表 (更新发货信息)
```

---

## 任务文件位置

- 订单自动化主流程任务：`backend/app/tasks/order_automation_tasks.py`
- Shopify订单同步（步骤1）：`backend/app/tasks/shopify_tasks.py`

---

## 配置管理

- **自动化步骤定义**: `backend/scripts/init_automation_steps.py`
- **任务映射**: `backend/app/services/automation_scheduler_service.py`
- **API端点映射**: `backend/app/api/v1/endpoints/automation.py`
- **租户配置**: `tenant_automation_configs` 表

---

## 自动化相关访问表清单

**自动化任务与调度会直接读写的表：**

- `shopify_orders`（Shopify订单本地表）
- `orders`（核心订单表）
- `order_items`（核心订单明细，随订单关系加载）
- `scm_orders`（SCM订单表）
- `scm_order_sources`（SCM订单来源关联表）
- `printify_orders`（Printify订单本地表）
- `external_systems`（外部系统凭据与同步状态）
- `tenants`（租户列表）
- `automation_steps`（自动化步骤定义）
- `tenant_automation_configs`（租户自动化配置）

---

## 迁移脚本

运行迁移脚本以更新数据库配置：
```bash
cd backend
python scripts/migrate_automation_steps.py
```

---

## 注意事项

1. **时间限制**: 所有从外部API同步的任务都只同步最近一周的订单
2. **两步架构**: 必须严格遵守两步架构，不能直接从API同步到核心表
3. **独立控制**: 每个步骤都可以在画面上单独控制开关
4. **统一调度**: 所有步骤默认每30分钟执行一次，可在画面上修改
