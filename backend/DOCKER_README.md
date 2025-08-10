# SupplyNexus Backend Docker 部署指南

## 概述

本项目提供了完整的 Docker 部署配置，支持本地开发、测试和生产环境。

## 快速开始

### 1. 本地开发环境

```bash
# 进入 backend 目录
cd backend

# 快速启动（自动创建 .env 文件）
./scripts/docker-start.sh
```

### 2. 使用 docker-compose

```bash
# 构建并启动
cd scripts && docker-compose up --build -d

# 查看日志
cd scripts && docker-compose logs -f backend

# 停止服务
cd scripts && docker-compose down

# 重启服务
cd scripts && docker-compose restart backend
```

## 环境配置

### 环境文件

项目支持多个环境配置文件：

- `.env` - 本地开发环境
- `deployment/environments/env.development` - 开发服务器
- `deployment/environments/env.staging` - 测试环境
- `deployment/environments/env.production` - 生产环境

### 必需的环境变量

```bash
# 数据库配置
DATABASE_URL=postgresql+asyncpg://user:password@host:port/database

# Redis 配置
REDIS_URL=redis://host:port/database

# 健康检查配置（必需）
HEALTH_CHECK_API_KEY=your-secure-api-key
HEALTH_CHECK_RATE_LIMIT=10
HEALTH_CHECK_RATE_WINDOW=60

# 其他配置...
```

## 部署脚本

### 本地开发

```bash
# 使用快速启动脚本
./scripts/docker-start.sh

# 或手动启动
cd scripts && docker-compose up --build -d
```

### 服务器部署

```bash
# 使用部署脚本
cd deployment/docker/backend
./deploy.sh development  # 或 staging, production
```

## 域名配置

### 开发环境
- **API**: `api.dev.supplynexus.store`
- **管理后台**: `admin.dev.supplynexus.store`
- **前端应用**: `app.dev.supplynexus.store`

### 测试环境
- **API**: `api.staging.supplynexus.store`
- **管理后台**: `admin.staging.supplynexus.store`
- **前端应用**: `app.staging.supplynexus.store`

### 生产环境
- **API**: `api.supplynexus.store`
- **管理后台**: `admin.supplynexus.store`
- **前端应用**: `app.supplynexus.store`

## Nginx 配置

### 配置文件位置
- `deployment/nginx/backend.conf` - 后端 API Nginx 配置样本
- `deployment/nginx/README.md` - Nginx 部署详细说明

### 重要说明
⚠️ **Nginx 配置是独立的样本文件**，适用于 Ubuntu 系统上直接安装的 Nginx，不是 Docker 容器。

### 主要特性
- SSL/TLS 支持
- 健康检查端点
- 安全头配置
- 负载均衡支持
- 访问日志记录

### 部署步骤

1. **复制配置文件**
```bash
sudo cp deployment/nginx/backend.conf /etc/nginx/sites-available/supplynexus-backend
sudo ln -s /etc/nginx/sites-available/supplynexus-backend /etc/nginx/sites-enabled/
```

2. **修改配置**
```bash
sudo nano /etc/nginx/sites-available/supplynexus-backend
# 根据实际情况修改域名、SSL 证书路径等
```

3. **申请 SSL 证书**
```bash
sudo certbot --nginx -d api.dev.supplynexus.store
```

4. **测试并重启 Nginx**
```bash
sudo nginx -t
sudo systemctl reload nginx
```

详细说明请参考：`deployment/nginx/README.md`

## 健康检查

### 端点
- **基本健康检查**: `GET /api/v1/health`
- **数据库健康检查**: `GET /api/v1/health/db` (需要 API Key)
- **Redis 健康检查**: `GET /api/v1/health/redis` (需要 API Key)
- **完整健康检查**: `GET /api/v1/health/full` (需要 API Key)

### 使用示例

```bash
# 基本健康检查
curl http://localhost:8000/api/v1/health

# 需要认证的健康检查
curl -H "X-API-Key: your-api-key" \
     http://localhost:8000/api/v1/health/db
```

## 监控和日志

### Docker 日志
```bash
# 查看实时日志
docker-compose logs -f backend

# 查看最近 100 行日志
docker-compose logs --tail=100 backend
```

### Nginx 日志
```bash
# 访问日志
tail -f /var/log/nginx/api.dev.supplynexus.store.access.log

# 错误日志
tail -f /var/log/nginx/api.dev.supplynexus.store.error.log
```

## 故障排除

### 常见问题

1. **服务无法启动**
```bash
# 检查日志
docker-compose logs backend

# 检查环境变量
docker-compose config
```

2. **健康检查失败**
```bash
# 检查数据库连接
docker-compose exec backend python -c "
from app.core.database import get_async_db
import asyncio
async def test():
    async for db in get_async_db():
        result = await db.execute('SELECT 1')
        print('Database OK')
asyncio.run(test())
"
```

3. **端口冲突**
```bash
# 检查端口占用
lsof -i :8000

# 修改端口
BACKEND_PORT=8001 docker-compose up -d
```

### 调试命令

```bash
# 进入容器
docker-compose exec backend bash

# 检查网络
docker network ls
docker network inspect backend_backend_network

# 检查容器状态
docker-compose ps
docker stats
```

## 安全配置

### API Key 认证
- 所有详细健康检查端点都需要 API Key
- 使用 `X-API-Key` 头部进行认证
- 支持频率限制（每分钟 10 次请求）

### SSL/TLS
- 强制 HTTPS 重定向
- 使用强加密套件
- 配置安全头

### 防火墙
```bash
# 只开放必要端口
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 22/tcp
sudo ufw enable
```

## 性能优化

### Docker 配置
- 使用多阶段构建
- 优化镜像层缓存
- 配置健康检查

### Nginx 配置
- 启用 gzip 压缩
- 配置缓存策略
- 优化连接池

### 应用配置
- 数据库连接池
- Redis 连接池
- 异步处理

## 备份和恢复

### 数据库备份
```bash
# 创建备份
docker-compose exec postgres pg_dump -U supplynexus_admin supplynexus > backup.sql

# 恢复备份
docker-compose exec -T postgres psql -U supplynexus_admin supplynexus < backup.sql
```

### 配置文件备份
```bash
# 备份环境配置
cp .env .env.backup

# 备份 Nginx 配置
sudo cp /etc/nginx/sites-available/backend.conf /etc/nginx/sites-available/backend.conf.backup
```
