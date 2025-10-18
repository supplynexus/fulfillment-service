# Token 管理策略

## 🎯 **存储策略**

### **前端 Token 存储**

#### **✅ 推荐方案：localStorage + 内存管理**

```typescript
// 使用 TokenManager 单例管理
const tokenManager = TokenManager.getInstance();

// 自动保存到 localStorage
tokenManager.setTokens({
  access_token: '...',
  refresh_token: '...',
  token_type: 'bearer',
});
```

**优点：**

- 简单易用
- 自动持久化
- 跨页面会话保持
- 自动过期检查

**缺点：**

- 易受 XSS 攻击
- 无法设置 HttpOnly

#### **🔒 安全增强方案：HttpOnly Cookies**

```typescript
// 使用 cookies 存储 refresh token
// 使用内存存储 access token
```

**优点：**

- 更安全，防止 XSS
- 自动发送到服务器

**缺点：**

- 实现复杂
- 需要服务器端配合

## 🔄 **Refresh Token 使用策略**

### **自动刷新机制**

```typescript
// 1. 检查 access token 是否过期
if (!tokenManager.isAccessTokenValid()) {
  // 2. 使用 refresh token 获取新的 access token
  const refreshed = await tokenManager.refreshAccessToken();
  if (!refreshed) {
    // 3. 刷新失败，清除所有 tokens
    tokenManager.clearTokens();
    // 4. 重定向到登录页
    router.push('/auth/login');
  }
}
```

### **刷新流程**

1. **Access Token 过期检测**
   - 每次 API 请求前检查
   - 使用 `jwt-decode` 解析过期时间

2. **自动刷新**
   - 调用 `/api/auth/refresh` 端点
   - 使用 refresh token 获取新的 access token

3. **失败处理**
   - 清除所有 tokens
   - 重定向到登录页

## 🏗️ **API 调用架构**

### **前端 → 后端 API 调用流程**

```
前端组件 → API 客户端 → 前端 API 路由 → 后端 API
    ↓           ↓              ↓            ↓
  用户界面   自动认证头     签名生成     业务逻辑
```

### **认证头自动添加**

```typescript
// 自动添加 Authorization 头
const authHeaders = await apiClient.getAuthHeaders();
// 返回: { 'Authorization': 'bearer eyJhbGciOiJIUzI1NiIs...' }
```

## 🔐 **Redis 使用建议**

### **当前架构分析**

#### **✅ 推荐：共享 Redis 实例**

```typescript
// 前端 API 路由可以使用相同的 Redis
// 用于缓存和会话管理
```

**优点：**

- 简化部署
- 数据一致性
- 成本效益

**缺点：**

- 单点故障风险
- 安全隔离问题

#### **🔒 生产环境：分离 Redis 实例**

```typescript
// 前端 Redis：会话缓存、用户状态
// 后端 Redis：业务缓存、队列
```

### **Redis 使用场景**

#### **前端 Redis 用途**

1. **会话缓存**

   ```typescript
   // 缓存用户会话信息
   await redis.set(`session:${userId}`, sessionData, 'EX', 3600);
   ```

2. **API 响应缓存**

   ```typescript
   // 缓存频繁请求的数据
   await redis.set(`cache:orders:${userId}`, ordersData, 'EX', 300);
   ```

3. **用户状态管理**
   ```typescript
   // 在线状态、偏好设置等
   await redis.set(`user:${userId}:status`, 'online', 'EX', 1800);
   ```

#### **后端 Redis 用途**

1. **Token 黑名单**

   ```python
   # 存储已撤销的 refresh tokens
   await redis.set(f"blacklist:{refresh_token}", "1", ex=86400)
   ```

2. **Nonce 防重放**

   ```python
   # 存储已使用的 nonce
   await redis.set(f"nonce:{nonce}", "1", ex=300)
   ```

3. **业务缓存**
   ```python
   # 缓存数据库查询结果
   await redis.set(f"cache:tenant:{tenant_id}", tenant_data, ex=3600)
   ```

### **Redis 配置建议**

#### **开发环境**

```yaml
# docker-compose.yml
redis:
  image: redis:7-alpine
  ports:
    - '6379:6379'
  volumes:
    - redis_data:/data
```

#### **生产环境**

```yaml
# 前端 Redis
redis-frontend:
  image: redis:7-alpine
  ports:
    - '6380:6379'
  volumes:
    - redis_frontend_data:/data

# 后端 Redis
redis-backend:
  image: redis:7-alpine
  ports:
    - '6379:6379'
  volumes:
    - redis_backend_data:/data
```

## 📋 **最佳实践**

### **1. Token 安全**

- ✅ 使用 HTTPS
- ✅ 设置合理的过期时间
- ✅ 实现自动刷新
- ✅ 及时清除过期 tokens

### **2. 错误处理**

- ✅ 网络错误重试
- ✅ 认证失败重定向
- ✅ 用户友好的错误消息

### **3. 性能优化**

- ✅ 缓存频繁请求
- ✅ 批量操作
- ✅ 懒加载

### **4. 监控和日志**

- ✅ 记录认证事件
- ✅ 监控 token 刷新频率
- ✅ 异常告警

## 🚀 **实施建议**

### **阶段 1：基础实现**

1. 实现 TokenManager
2. 配置自动刷新
3. 使用 localStorage 存储

### **阶段 2：安全增强**

1. 添加 HttpOnly cookies
2. 实现 token 轮换
3. 添加安全头部

### **阶段 3：性能优化**

1. 集成 Redis 缓存
2. 实现响应缓存
3. 添加监控

### **阶段 4：生产就绪**

1. 分离 Redis 实例
2. 添加负载均衡
3. 完善监控告警
