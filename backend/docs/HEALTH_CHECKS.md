# 健康检查系统文档

## 概述

SupplyNexus Fulfillment Service 实现了完整的健康检查系统，用于监控服务状态和依赖项的健康状况。

## 健康检查端点

### 1. 基本健康检查

**端点**: `GET /api/v1/health`

**描述**: 基本健康检查，无需认证，用于负载均衡器和监控系统的基础检查。

**响应示例**:
```json
{
  "status": "healthy",
  "service": "fulfillment-service",
  "version": "1.0.0"
}
```

### 2. 数据库健康检查

**端点**: `GET /api/v1/health/db`

**描述**: 检查数据库连接状态，需要 API Key 认证。

**认证**: 需要 `X-API-Key` 或 `Authorization: Bearer <api-key>` 头部

**响应示例**:
```json
{
  "status": "healthy",
  "service": "database",
  "message": "Database connection successful"
}
```

### 3. Redis 健康检查

**端点**: `GET /api/v1/health/redis`

**描述**: 检查 Redis 连接状态，需要 API Key 认证。

**认证**: 需要 `X-API-Key` 或 `Authorization: Bearer <api-key>` 头部

**响应示例**:
```json
{
  "status": "healthy",
  "service": "redis",
  "message": "Redis connection successful"
}
```

### 4. 完整健康检查

**端点**: `GET /api/v1/health/full`

**描述**: 检查所有服务的健康状态，包括数据库和 Redis，需要 API Key 认证。

**认证**: 需要 `X-API-Key` 或 `Authorization: Bearer <api-key>` 头部

**响应示例**:
```json
{
  "status": "healthy",
  "service": "fulfillment-service",
  "version": "1.0.0",
  "timestamp": "2024-01-01T12:00:00.000Z",
  "checks": {
    "database": {
      "status": "healthy",
      "message": "Database connection successful"
    },
    "redis": {
      "status": "healthy",
      "message": "Redis connection successful"
    }
  }
}
```

## 安全配置

### 环境变量

在 `.env` 文件中配置以下变量：

```bash
# 健康检查 API Key（必须配置）
HEALTH_CHECK_API_KEY=your-secure-api-key-here

# 频率限制配置
HEALTH_CHECK_RATE_LIMIT=10      # 每分钟最大请求数
HEALTH_CHECK_RATE_WINDOW=60     # 时间窗口（秒）
```

### 安全特性

1. **API Key 认证**: 所有详细健康检查端点都需要有效的 API Key
2. **频率限制**: 基于 Redis 的滑动窗口频率限制
3. **安全日志**: 记录所有健康检查访问，包括 IP 地址和用户代理
4. **时间安全比较**: 使用时间安全的字符串比较防止时序攻击

## 使用方法

### 1. 基本健康检查（无需认证）

```bash
curl http://localhost:8000/api/v1/health
```

### 2. 详细健康检查（需要认证）

```bash
# 使用 X-API-Key 头部
curl -H "X-API-Key: your-api-key" http://localhost:8000/api/v1/health/db

# 或使用 Authorization 头部
curl -H "Authorization: Bearer your-api-key" http://localhost:8000/api/v1/health/redis
```

### 3. 完整健康检查

```bash
curl -H "X-API-Key: your-api-key" http://localhost:8000/api/v1/health/full
```

## 监控集成

### 负载均衡器配置

对于负载均衡器（如 Nginx、HAProxy），使用基本健康检查端点：

```nginx
# Nginx 配置示例
location /health {
    proxy_pass http://backend/api/v1/health;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
}
```

### 监控系统配置

对于监控系统（如 Prometheus、Datadog），使用详细健康检查端点：

```yaml
# Prometheus 配置示例
scrape_configs:
  - job_name: 'fulfillment-service'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/api/v1/health/full'
    authorization:
      type: 'Bearer'
      credentials: 'your-api-key'
```

## 错误处理

### HTTP 状态码

- `200 OK`: 服务健康
- `401 Unauthorized`: API Key 无效或缺失
- `429 Too Many Requests`: 频率限制超出
- `503 Service Unavailable`: 服务不健康（数据库或 Redis 连接失败）

### 错误响应示例

```json
{
  "detail": "Invalid API key or rate limit exceeded"
}
```

## 测试

### 运行测试脚本

```bash
# 简单测试
python backend/scripts/simple_health_test.py

# 详细测试
python backend/scripts/test_health_checks.py
```

### 手动测试

```bash
# 1. 启动服务
docker-compose -f docker-compose.dev.yml up -d

# 2. 测试基本健康检查
curl http://localhost:8000/api/v1/health

# 3. 测试认证端点（应该返回 401）
curl http://localhost:8000/api/v1/health/db

# 4. 测试带认证的端点
curl -H "X-API-Key: dev-health-check-api-key-123456" http://localhost:8000/api/v1/health/db
```

## 故障排除

### 常见问题

1. **401 Unauthorized**: 检查 API Key 是否正确配置
2. **503 Service Unavailable**: 检查数据库和 Redis 服务是否启动
3. **429 Too Many Requests**: 降低请求频率或调整频率限制配置

### 日志查看

```bash
# 查看应用日志
docker-compose -f docker-compose.dev.yml logs -f backend_dev

# 查看健康检查相关日志
docker-compose -f docker-compose.dev.yml logs backend_dev | grep "health_check"
```

## 最佳实践

1. **生产环境**: 使用强随机 API Key
2. **监控**: 设置适当的告警阈值
3. **日志**: 定期检查健康检查访问日志
4. **备份**: 配置多个健康检查端点用于冗余
5. **安全**: 定期轮换 API Key
