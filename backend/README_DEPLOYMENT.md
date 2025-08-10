# SupplyNexus Backend 部署指南

## 📁 目录结构

```
backend/
├── logs-dev/          # 开发环境日志目录
├── logs-local/        # 本地环境日志目录
├── logs-prod/         # 生产环境日志目录
├── logs-stg/          # 测试环境日志目录
├── .env.local         # 本地环境配置
├── .env.dev           # 开发环境配置
├── .env.stg           # 测试环境配置
├── .env.prod          # 生产环境配置
└── scripts/
    └── db.py          # 数据库管理脚本
```

## 🚀 部署方式

### 方式一：使用 deploy.sh（推荐用于服务器部署）

```bash
# 在 deployment/docker/backend/ 目录下执行
./deploy.sh local        # 本地环境
./deploy.sh dev          # 开发环境
./deploy.sh stg          # 测试环境
./deploy.sh prod         # 生产环境
```

### 方式二：使用 run.sh（推荐用于本地开发）

```bash
# 在 backend/ 目录下执行
# 使用 deploy.sh（推荐）
cd ../deployment/docker/backend
./deploy.sh local up        # 启动本地环境
./deploy.sh local down      # 停止服务
./deploy.sh local restart   # 重启服务
./deploy.sh local logs      # 查看日志
./deploy.sh local status    # 查看状态
```

## 📋 环境文件配置

### 环境文件位置
- 本地环境：`backend/.env.local`
- 开发环境：`backend/.env.dev`
- 测试环境：`backend/.env.stg`
- 生产环境：`backend/.env.prod`

### 环境文件内容示例
```bash
# 数据库配置
DATABASE_URL=postgresql+asyncpg://user:password@host:port/database
REDIS_URL=redis://host:port/db

# API 密钥
SHOPIFY_API_KEY=your-shopify-api-key
SHOPIFY_API_SECRET=your-shopify-api-secret
PRINTIFY_API_TOKEN=your-printify-api-token

# JWT 配置
SECRET_KEY=your-secret-key
ACCESS_TOKEN_EXPIRE_MINUTES=30

# 环境设置
ENVIRONMENT=local
ALLOWED_ORIGINS=http://localhost:3000
ALLOWED_HOSTS=localhost,127.0.0.1

# 健康检查配置
HEALTH_CHECK_API_KEY=your-health-check-api-key
HEALTH_CHECK_RATE_LIMIT=10
HEALTH_CHECK_RATE_WINDOW=60
```

## 🔧 开发环境设置

### 1. 创建环境文件
```bash
# 复制示例文件
cp .env.example .env.local

# 编辑配置文件
vim .env.local
```

### 2. 启动服务
```bash
# 使用 deploy.sh（推荐）
cd ../deployment/docker/backend
./deploy.sh local up

# 或使用 deploy.sh
../deployment/docker/backend/deploy.sh local
```

### 3. 验证服务
```bash
# 健康检查
curl http://localhost:8000/api/v1/health

# API 文档
open http://localhost:8000/api/v1/docs
```

## 📊 服务信息

启动成功后，服务将在以下地址可用：
- **API**: http://localhost:8000
- **API 文档**: http://localhost:8000/api/v1/docs
- **健康检查**: http://localhost:8000/api/v1/health

## 🗂️ 日志管理

日志文件存储在对应的环境目录中：
- 本地环境：`logs-local/`
- 开发环境：`logs-dev/`
- 测试环境：`logs-stg/`
- 生产环境：`logs-prod/`

查看日志：
```bash
# 使用 deploy.sh
cd ../deployment/docker/backend
./deploy.sh local logs

# 或直接查看文件
tail -f logs-local/app.log
```

## 🔍 故障排除

### 1. 服务启动失败
```bash
# 查看详细日志
docker-compose logs backend

# 重新构建
cd ../deployment/docker/backend
./deploy.sh local build
```

### 2. 环境文件问题
```bash
# 检查环境文件是否存在
ls -la .env.*

# 检查环境文件内容
cat .env.local
```

### 3. 端口冲突
```bash
# 检查端口占用
lsof -i :8000

# 停止冲突的服务
docker-compose down
```

## 📝 注意事项

1. **环境文件安全**: 生产环境的环境文件包含敏感信息，请妥善保管
2. **日志轮转**: 生产环境建议配置日志轮转，避免日志文件过大
3. **健康检查**: 服务启动后会自动进行健康检查，确保服务正常运行
4. **数据持久化**: 数据库和 Redis 数据需要单独配置持久化存储
