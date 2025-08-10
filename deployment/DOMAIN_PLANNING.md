# SupplyNexus 域名规划

## 主域名
- **主域名**: `supplynexus.store`

## 环境域名规划

### 开发环境 (Development)
```
api.dev.supplynexus.store     # 后端 API
admin.dev.supplynexus.store   # 管理后台
app.dev.supplynexus.store     # 前端应用
```

### 测试环境 (Staging)
```
api.staging.supplynexus.store     # 后端 API
admin.staging.supplynexus.store   # 管理后台
app.staging.supplynexus.store     # 前端应用
```

### 生产环境 (Production)
```
api.supplynexus.store         # 后端 API
admin.supplynexus.store       # 管理后台
app.supplynexus.store         # 前端应用
```

## 服务端口映射

### 开发环境
- **后端 API**: `localhost:8000` → `api.dev.supplynexus.store`
- **前端应用**: `localhost:3000` → `app.dev.supplynexus.store`
- **管理后台**: `localhost:3001` → `admin.dev.supplynexus.store`

### 测试环境
- **后端 API**: `staging-server:8000` → `api.staging.supplynexus.store`
- **前端应用**: `staging-server:3000` → `app.staging.supplynexus.store`
- **管理后台**: `staging-server:3001` → `admin.staging.supplynexus.store`

### 生产环境
- **后端 API**: `prod-server:8000` → `api.supplynexus.store`
- **前端应用**: `prod-server:3000` → `app.supplynexus.store`
- **管理后台**: `prod-server:3001` → `admin.supplynexus.store`

## DNS 配置建议

### 开发环境
```bash
# 本地开发 (hosts 文件)
127.0.0.1 api.dev.supplynexus.store
127.0.0.1 app.dev.supplynexus.store
127.0.0.1 admin.dev.supplynexus.store
```

### 服务器环境
```bash
# 开发服务器
dev-server-ip api.dev.supplynexus.store
dev-server-ip app.dev.supplynexus.store
dev-server-ip admin.dev.supplynexus.store

# 测试服务器
staging-server-ip api.staging.supplynexus.store
staging-server-ip app.staging.supplynexus.store
staging-server-ip admin.staging.supplynexus.store

# 生产服务器
prod-server-ip api.supplynexus.store
prod-server-ip app.supplynexus.store
prod-server-ip admin.supplynexus.store
```

## SSL 证书配置

### 通配符证书
建议使用通配符证书覆盖所有子域名：
- `*.supplynexus.store` - 覆盖所有子域名
- `*.dev.supplynexus.store` - 开发环境子域名
- `*.staging.supplynexus.store` - 测试环境子域名

### Let's Encrypt 配置
```bash
# 申请通配符证书
certbot certonly --manual --preferred-challenges=dns \
  -d *.supplynexus.store \
  -d *.dev.supplynexus.store \
  -d *.staging.supplynexus.store
```

## 负载均衡配置

### 多实例部署
```nginx
upstream backend_api {
    server backend-1:8000;
    server backend-2:8000;
    server backend-3:8000;
}
```

### 健康检查
```nginx
upstream backend_api {
    server backend-1:8000 max_fails=3 fail_timeout=30s;
    server backend-2:8000 max_fails=3 fail_timeout=30s;
    server backend-3:8000 max_fails=3 fail_timeout=30s;
}
```

## 监控和日志

### 访问日志
- `/var/log/nginx/api.dev.supplynexus.store.access.log`
- `/var/log/nginx/app.dev.supplynexus.store.access.log`
- `/var/log/nginx/admin.dev.supplynexus.store.access.log`

### 错误日志
- `/var/log/nginx/api.dev.supplynexus.store.error.log`
- `/var/log/nginx/app.dev.supplynexus.store.error.log`
- `/var/log/nginx/admin.dev.supplynexus.store.error.log`

## 安全配置

### CORS 设置
```python
# 后端 CORS 配置
ALLOWED_ORIGINS = [
    "https://app.dev.supplynexus.store",
    "https://admin.dev.supplynexus.store",
    "https://app.staging.supplynexus.store",
    "https://admin.staging.supplynexus.store",
    "https://app.supplynexus.store",
    "https://admin.supplynexus.store",
]
```

### 安全头
```nginx
add_header X-Frame-Options DENY;
add_header X-Content-Type-Options nosniff;
add_header X-XSS-Protection "1; mode=block";
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
```
