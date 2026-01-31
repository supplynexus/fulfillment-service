# 健康检查安全文档

## 安全概述

健康检查端点虽然用于监控，但也可能成为安全攻击的目标。本文档详细说明了 SupplyNexus Fulfillment Service 健康检查系统的安全措施和最佳实践。

## 安全威胁分析

### 潜在威胁

1. **信息泄露**: 健康检查端点可能泄露系统内部信息
2. **拒绝服务攻击**: 恶意请求可能导致系统资源耗尽
3. **枚举攻击**: 攻击者可能通过健康检查端点发现系统架构
4. **认证绕过**: 未正确保护的端点可能被滥用

### 攻击场景

- 攻击者通过健康检查端点获取数据库连接信息
- 恶意脚本频繁调用健康检查端点导致资源耗尽
- 攻击者利用健康检查端点进行端口扫描和服务发现

## 安全措施

### 1. API Key 认证

所有详细健康检查端点都要求有效的 API Key：

```python
# 时间安全的字符串比较
def verify_api_key(self, api_key: str) -> bool:
    if not api_key:
        return False
    
    expected_key = settings.HEALTH_CHECK_API_KEY
    if not expected_key:
        return False
    
    # 防止时序攻击
    if len(api_key) != len(expected_key):
        return False
    
    result = 0
    for a, b in zip(api_key, expected_key):
        result |= ord(a) ^ ord(b)
    
    return result == 0
```

### 2. 频率限制

基于 Redis 的滑动窗口频率限制：

```python
async def check_rate_limit(self, identifier: str) -> bool:
    # 滑动窗口实现
    current_time = int(time.time())
    window_start = current_time - settings.HEALTH_CHECK_RATE_WINDOW
    
    # 清理过期记录
    await redis_client.zremrangebyscore(
        f"health_check_rate_limit:{identifier}",
        0, window_start
    )
    
    # 检查当前窗口内的请求数
    current_count = await redis_client.zcard(
        f"health_check_rate_limit:{identifier}"
    )
    
    return current_count < settings.HEALTH_CHECK_RATE_LIMIT
```

### 3. 安全日志记录

记录所有健康检查访问，包括：

- IP 地址
- 用户代理
- API Key 哈希（部分）
- 访问时间
- 请求路径

```python
logger.warning(
    "Invalid health check API key",
    ip=request.client.host,
    user_agent=request.headers.get("User-Agent", ""),
    api_key_hash=hashlib.sha256(api_key.encode()).hexdigest()[:8] if api_key else "none"
)
```

### 4. 信息最小化

健康检查响应只包含必要信息：

```json
{
  "status": "healthy",
  "service": "database",
  "message": "Database connection successful"
}
```

**不包含的信息**：
- 数据库连接字符串
- 内部 IP 地址
- 系统版本详细信息
- 错误堆栈信息

## 配置安全

### 环境变量安全

```bash
# 生产环境必须使用强随机 API Key
HEALTH_CHECK_API_KEY=your-very-long-random-string-here

# 合理的频率限制
HEALTH_CHECK_RATE_LIMIT=10      # 每分钟最大请求数
HEALTH_CHECK_RATE_WINDOW=60     # 时间窗口（秒）
```

### API Key 生成

```bash
# 生成强随机 API Key
openssl rand -base64 32

# 或使用 Python
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

## 网络层安全

### 防火墙配置

```bash
# 只允许特定 IP 访问健康检查端点
iptables -A INPUT -p tcp --dport 8000 -s 10.0.0.0/8 -j ACCEPT
iptables -A INPUT -p tcp --dport 8000 -s 192.168.1.0/24 -j ACCEPT
iptables -A INPUT -p tcp --dport 8000 -j DROP
```

### 反向代理配置

```nginx
# Nginx 配置示例
location /api/v1/health {
    # 只允许内部网络访问
    allow 10.0.0.0/8;
    allow 192.168.1.0/24;
    deny all;
    
    proxy_pass http://backend;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
}
```

## 监控和告警

### 安全监控

1. **异常访问检测**：
   - 来自未知 IP 的访问
   - 异常的请求频率
   - 无效的 API Key 尝试

2. **日志分析**：
   ```bash
   # 检查无效 API Key 尝试
   grep "Invalid health check API key" /var/log/app.log
   
   # 检查频率限制触发
   grep "Health check rate limit exceeded" /var/log/app.log
   ```

### 告警配置

```yaml
# Prometheus 告警规则
groups:
  - name: health_check_security
    rules:
      - alert: HealthCheckAuthFailure
        expr: rate(health_check_auth_failures_total[5m]) > 0.1
        for: 1m
        labels:
          severity: warning
        annotations:
          summary: "Health check authentication failures detected"
          description: "Rate of health check auth failures is {{ $value }} per second"
```

## 最佳实践

### 1. API Key 管理

- ✅ 使用强随机 API Key
- ✅ 定期轮换 API Key
- ✅ 不同环境使用不同的 API Key
- ❌ 不要在代码中硬编码 API Key
- ❌ 不要将 API Key 提交到版本控制

### 2. 网络访问控制

- ✅ 限制健康检查端点的网络访问
- ✅ 使用 VPN 或专用网络
- ✅ 配置防火墙规则
- ❌ 不要将健康检查端点暴露到公网

### 3. 监控和日志

- ✅ 记录所有健康检查访问
- ✅ 设置异常访问告警
- ✅ 定期审查访问日志
- ✅ 监控频率限制触发情况

### 4. 响应安全

- ✅ 只返回必要信息
- ✅ 使用标准 HTTP 状态码
- ✅ 避免泄露内部系统信息
- ❌ 不要在响应中包含敏感数据

## 安全检查清单

### 部署前检查

- [ ] API Key 已配置且足够复杂
- [ ] 频率限制已合理设置
- [ ] 网络访问已限制
- [ ] 日志记录已启用
- [ ] 监控告警已配置

### 定期检查

- [ ] 审查健康检查访问日志
- [ ] 检查异常访问模式
- [ ] 验证频率限制有效性
- [ ] 更新 API Key（如需要）
- [ ] 检查防火墙规则

### 事件响应

- [ ] 记录安全事件
- [ ] 分析攻击模式
- [ ] 更新安全配置
- [ ] 通知相关团队
- [ ] 更新监控规则

## 故障排除

### 常见安全问题

1. **API Key 泄露**：
   - 立即轮换 API Key
   - 检查日志中的异常访问
   - 更新所有客户端配置

2. **频率限制绕过**：
   - 检查 Redis 连接状态
   - 验证频率限制配置
   - 考虑使用更严格的限制

3. **网络访问控制失效**：
   - 检查防火墙规则
   - 验证反向代理配置
   - 确认网络隔离设置

### 安全工具

```bash
# 检查 API Key 强度
echo "your-api-key" | wc -c  # 应该 >= 32

# 检查频率限制状态
redis-cli ZCARD "health_check_rate_limit:test"

# 检查访问日志
tail -f /var/log/app.log | grep "health_check"
```
