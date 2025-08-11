# SupplyNexus Fulfillment Service - 环境部署指南

## 🚀 快速开始

### 新的部署方式（推荐）

```bash
# 启动本地环境
./deployment/scripts/deploy.sh local start

# 启动开发环境
./deployment/scripts/deploy.sh dev start

# 运行数据库迁移
./deployment/scripts/deploy.sh local db-upgrade

# 查看服务状态
./deployment/scripts/deploy.sh local status

# 查看日志
./deployment/scripts/deploy.sh local logs

# 停止服务
./deployment/scripts/deploy.sh local stop
```

## 🌍 环境说明

### 支持的环境

- **local** - 本地开发环境（端口 5432）
- **dev** - 开发服务器环境（端口 5433）
- **staging** - 测试环境
- **production** - 生产环境

### 域名配置

#### 开发环境
- **API服务**: `api.dev.supplynexus.store`
- **前端管理后台**: `dev.supplynexus.store`
- **Webhook端点**: `api.dev.supplynexus.store/webhooks`

#### 测试环境
- **API服务**: `api.stg.supplynexus.store`
- **前端管理后台**: `stg.supplynexus.store`
- **Webhook端点**: `api.stg.supplynexus.store/webhooks`

#### 生产环境
- **API服务**: `api.supplynexus.store`
- **前端管理后台**: `supplynexus.store`
- **Webhook端点**: `api.supplynexus.store/webhooks`

## ⚙️ 环境配置

### 1. 复制环境配置文件

```bash
cp deployment/environments/env.example deployment/environments/env.local
cp deployment/environments/env.example deployment/environments/env.dev
cp deployment/environments/env.example deployment/environments/env.stg
cp deployment/environments/env.example deployment/environments/env.prod
```

### 2. 编辑配置文件

```bash
vim deployment/environments/env.local
vim deployment/environments/env.dev
vim deployment/environments/env.stg
vim deployment/environments/env.prod
```

### 3. 关键配置项

```bash
# 本地环境配置 (端口: 5432)
DATABASE_URL=postgresql+asyncpg://username:password@localhost:5432/database
DATABASE_URL_SYNC=postgresql://username:password@localhost:5432/database

# 开发环境配置 (端口: 5433)
DATABASE_URL=postgresql+asyncpg://username:password@localhost:5433/database
DATABASE_URL_SYNC=postgresql://username:password@localhost:5433/database

# Redis 配置
REDIS_URL=redis://:password@host:port/0
CELERY_BROKER_URL=redis://:password@host:port/1
CELERY_RESULT_BACKEND=redis://:password@host:port/2

# API 密钥
SHOPIFY_API_KEY=your-shopify-api-key
SHOPIFY_API_SECRET=your-shopify-api-secret
PRINTIFY_API_TOKEN=your-printify-api-token

# 健康检查配置（必需）
HEALTH_CHECK_API_KEY=your-secure-api-key
HEALTH_CHECK_RATE_LIMIT=10
HEALTH_CHECK_RATE_WINDOW=60
```

## 📋 可用命令

### 服务管理
- `start` - 启动所有服务
- `stop` - 停止所有服务
- `restart` - 重启所有服务
- `logs [service]` - 查看日志（可选指定服务名）

### 数据库管理
- `db-upgrade` - 运行数据库迁移
- `db-status` - 检查迁移状态
- `db-history` - 查看迁移历史

## 🔧 完整部署流程

### 1. 首次部署

```bash
# 1. 拉取代码
git pull origin develop

# 2. 配置环境文件
cp deployment/environments/env.example deployment/environments/env.dev
# 编辑配置文件...

# 3. 启动基础设施（PostgreSQL, Redis）
cd deployment/docker/postgresql && ./deploy.sh dev
cd deployment/docker/redis && ./deploy.sh dev

# 4. 运行数据库迁移
./deployment/scripts/deploy.sh dev db-upgrade

# 5. 启动应用服务
./deployment/scripts/deploy.sh dev start
```

### 2. 日常部署

```bash
# 1. 拉取最新代码
git pull origin develop

# 2. 运行数据库迁移（如果有）
./deployment/scripts/deploy.sh dev db-upgrade

# 3. 重启服务
./deployment/scripts/deploy.sh dev restart
```

### 3. 生产环境部署

```bash
# 1. 切换到生产分支
git checkout main
git pull origin main

# 2. 运行生产环境迁移
./deployment/scripts/deploy.sh prod db-upgrade

# 3. 启动生产服务
./deployment/scripts/deploy.sh prod start
```

## 🐳 Docker 部署

### 生产环境部署

```bash
# 构建和启动生产环境
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f
```

### 多环境部署

#### 使用新的部署脚本（推荐）

```bash
# 启动本地环境
./deployment/scripts/deploy.sh local start

# 启动开发环境
./deployment/scripts/deploy.sh dev start

# 运行数据库迁移
./deployment/scripts/deploy.sh local db-upgrade

# 查看服务状态
./deployment/scripts/deploy.sh local status

# 查看日志
./deployment/scripts/deploy.sh local logs

# 停止服务
./deployment/scripts/deploy.sh local stop
```

#### 使用传统 Docker Compose

```bash
# 本地开发环境
docker-compose -f docker-compose.dev.yml up -d

# 生产环境
docker-compose up -d

# 指定环境文件
docker-compose --env-file .env.prod up -d
```

## 🔒 SSL 证书配置

### 使用 Let's Encrypt

```bash
# 安装 certbot
sudo apt install certbot python3-certbot-nginx -y

# 获取 SSL 证书
sudo certbot --nginx -d api.dev.supplynexus.store

# 设置自动续期
sudo crontab -e
# 添加这行：
0 2 * * * /usr/bin/certbot renew --quiet
```

### Nginx 配置

```nginx
server {
    listen 80;
    server_name api.dev.supplynexus.store;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.dev.supplynexus.store;

    # SSL证书
    ssl_certificate /etc/letsencrypt/live/api.dev.supplynexus.store/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.dev.supplynexus.store/privkey.pem;

    # 代理配置
    location / {
        proxy_pass http://localhost:8001;
        proxy_set_header Host localhost:8001;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /health {
        proxy_pass http://localhost:8001/api/v1/health;
        proxy_set_header Host localhost:8001;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /docs {
        proxy_pass http://localhost:8001/api/v1/docs;
        proxy_set_header Host localhost:8001;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /redoc {
        proxy_pass http://localhost:8001/api/v1/redoc;
        proxy_set_header Host localhost:8001;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## 📊 监控

### 健康检查

- **基本健康检查**: `GET /api/v1/health`
- **数据库健康检查**: `GET /api/v1/health/db` (需要 API Key)
- **Redis 健康检查**: `GET /api/v1/health/redis` (需要 API Key)
- **完整健康检查**: `GET /api/v1/health/full` (需要 API Key)

### 使用示例

```bash
# 基本健康检查
curl https://api.dev.supplynexus.store/health

# 需要认证的健康检查
curl -H "X-API-Key: your-api-key" \
     https://api.dev.supplynexus.store/health/db
```

### 日志

- **应用日志**: Docker 容器日志
- **访问日志**: Nginx 访问日志
- **错误跟踪**: Sentry (如已配置)

## 🔍 故障排查

### 查看服务状态
```bash
# 查看所有服务日志
./deployment/scripts/deploy.sh dev logs

# 查看特定服务日志
./deployment/scripts/deploy.sh dev logs backend
```

### 数据库问题
```bash
# 检查迁移状态
./deployment/scripts/deploy.sh dev db-status

# 查看迁移历史
./deployment/scripts/deploy.sh dev db-history
```

### 重置数据库（谨慎使用）
```bash
cd backend
source .venv/bin/activate
python deployment/scripts/db.py reset
```

## 📝 注意事项

1. **环境文件安全**：不要将包含真实密码的环境文件提交到 git
2. **备份数据库**：在生产环境执行迁移前，建议先备份数据库
3. **测试迁移**：在 staging 环境测试迁移后再部署到生产环境
4. **权限检查**：确保脚本有执行权限：`chmod +x deployment/scripts/deploy.sh`

## 🔄 旧版本兼容性

旧的部署方式仍然支持：

```bash
# 旧方式（仍然可用）
ENV_FILE=env.dev ./deployment/scripts/deploy.sh start
ENV_FILE=env.dev ./deployment/scripts/deploy.sh db-upgrade
```

## 📞 支持

如果遇到问题，请检查：
1. 环境配置文件是否正确
2. 数据库和 Redis 服务是否正常运行
3. 网络连接是否正常
4. 查看服务日志获取详细错误信息
