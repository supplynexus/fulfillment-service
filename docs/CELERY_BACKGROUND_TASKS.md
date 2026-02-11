# Celery 后台任务系统

## 概述

本系统使用 Celery 作为分布式任务队列，处理异步任务和定时任务。主要包含两个批处理进程：

1. **Celery Beat** - 定时任务调度器
2. **Celery Worker** - 任务执行器

## 系统架构

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   FastAPI       │    │   Celery Beat   │    │  Celery Worker  │
│   Web API       │    │   (Scheduler)   │    │   (Executor)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │     Redis       │
                    │  (Message Broker)│
                    └─────────────────┘
                                 │
                    ┌─────────────────┐
                    │   PostgreSQL    │
                    │   (Database)    │
                    └─────────────────┘
```

## 组件说明

### 1. FastAPI Web API 服务
- **作用**: 提供 RESTful API 接口
- **端口**: 8000
- **功能**: 处理 HTTP 请求，触发异步任务

### 2. Celery Beat (定时任务调度器)
- **作用**: 根据配置的定时规则触发任务
- **功能**: 
  - 每分钟同步 Shopify 产品
  - 每30分钟同步 Shopify 产品
  - 每小时同步订单
  - 每天凌晨2点全量同步

### 3. Celery Worker (任务执行器)
- **作用**: 执行具体的异步任务
- **队列**: `shopify`, `default`, `orders`
- **功能**: 处理产品同步、订单同步等任务

### 4. Redis (消息代理)
- **作用**: 存储任务队列和结果
- **端口**: 6380
- **功能**: 
  - 任务队列存储
  - 任务结果缓存
  - 分布式锁

### 5. PostgreSQL (数据库)
- **作用**: 存储业务数据
- **功能**: 
  - 产品数据
  - 订单数据
  - 同步配置
  - 用户数据

## 启动命令

### 1. 启动 Web API 服务
```bash
cd backend
source .venv/bin/activate
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. 启动 Celery Beat (定时任务调度器)
```bash
cd backend
source .venv/bin/activate
celery -A app.tasks.celery_app beat --loglevel=info
```

### 3. 启动 Celery Worker (任务执行器)
```bash
cd backend
source .venv/bin/activate
celery -A app.tasks.celery_app worker --loglevel=info -Q shopify,default,orders,order_automation
```

## 定时任务配置

### 产品同步任务
- **1分钟同步**: `sync-shopify-products-1min`
- **30分钟同步**: `sync-shopify-products-30min`
- **每小时同步**: `sync-shopify-products-hourly`
- **每天全量同步**: `sync-shopify-products-daily`

### 订单同步任务
- **30分钟同步**: `sync-shopify-orders`

## 队列说明

- **shopify**: Shopify 相关任务（产品同步、订单同步）
- **default**: 默认任务队列
- **orders**: 订单处理任务
- **order_automation**: 自动化管理中的定时/手动任务（如 Printify 商品同步、Printify–Shopify 商品自动绑定）

## 监控和调试

### 检查任务状态
```bash
# 检查 Redis 队列长度
redis-cli -p 6380 llen shopify
redis-cli -p 6380 llen default

# 检查 Celery 进程
ps aux | grep celery
```

### 查看日志
- Celery Beat 日志: 显示定时任务触发情况
- Celery Worker 日志: 显示任务执行情况
- FastAPI 日志: 显示 API 请求情况

## 故障排除

### 常见问题

1. **任务不执行**
   - 检查 Celery Worker 是否启动
   - 检查队列配置是否正确
   - 检查 Redis 连接是否正常

2. **时区问题**
   - 确保所有时间都使用 UTC
   - 检查数据库时区设置

3. **队列堆积**
   - 检查 Worker 是否正常运行
   - 检查任务是否有错误

### 重启服务
```bash
# 停止所有 Celery 进程
pkill -f celery

# 重新启动
cd backend
source .venv/bin/activate

# 启动 Beat
celery -A app.tasks.celery_app beat --loglevel=info &

# 启动 Worker
celery -A app.tasks.celery_app worker --loglevel=info -Q shopify,default,orders,order_automation,order_automation &
```

## 配置说明

### 环境变量
- `REDIS_URL`: Redis 连接地址
- `DATABASE_URL`: PostgreSQL 连接地址
- `CELERY_BROKER_URL`: Celery 消息代理地址

### 任务配置
- 任务超时时间: 30分钟
- 软超时时间: 25分钟
- Worker 并发数: 8
- 任务过期时间: 根据任务类型设置
