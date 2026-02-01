# 生产环境部署步骤

## 部署流程概览

1. **在服务器上拉取代码**（git pull from main）
2. **上传环境配置文件**（env.prod, frontend/env.prod, docker-compose.prod.yml）
3. **配置防火墙**（UFW）
4. **确保数据持久化**（Docker volumes 已配置）
5. **运行数据库迁移**（Alembic）
6. **启动 Docker 服务**（docker-compose.prod.yml）
7. **验证部署状态**

## 详细步骤

### 步骤 1: 在服务器上拉取代码

```bash
# SSH 到服务器
ssh ubuntu@133.242.179.110

# 进入部署目录（如果不存在则创建）
cd /opt/supplynexus

# 如果目录不存在，克隆仓库
if [ ! -d ".git" ]; then
    git clone https://github.com/supplynexus/fulfillment-service.git .
fi

# 切换到 main 分支并拉取最新代码
git checkout main
git pull origin main
```

### 步骤 2: 上传环境配置文件

从本地执行：

```bash
# 上传后端环境配置
scp deployment/environments/env.prod ubuntu@133.242.179.110:/opt/supplynexus/deployment/environments/

# 上传前端环境配置
scp deployment/environments/frontend/env.prod ubuntu@133.242.179.110:/opt/supplynexus/deployment/environments/frontend/

# 上传 Docker Compose 配置
scp docker-compose.prod.yml ubuntu@133.242.179.110:/opt/supplynexus/
```

### 步骤 3: 配置防火墙

在服务器上执行：

```bash
cd /opt/supplynexus
sudo ./scripts/prod/setup-ufw.sh
```

### 步骤 4: 检查数据持久化配置

Docker Compose 已配置：
- `postgres_prod_data` volume - PostgreSQL 数据持久化
- `redis_prod_data` volume - Redis 数据持久化

### 步骤 5: 运行数据库迁移

在服务器上执行：

```bash
cd /opt/supplynexus
./scripts/db/alembic.sh prod upgrade
```

### 步骤 6: 启动 Docker 服务

在服务器上执行：

```bash
cd /opt/supplynexus
docker-compose -f docker-compose.prod.yml up -d
```

### 步骤 7: 验证部署状态

在服务器上执行：

```bash
# 检查容器状态
docker-compose -f docker-compose.prod.yml ps

# 查看日志
docker-compose -f docker-compose.prod.yml logs -f

# 检查服务健康状态
curl http://localhost:8000/api/v1/health
curl http://localhost:3000/api/health
```
