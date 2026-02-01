# 生产环境部署流程

## 📋 概述

本文档描述如何将 `main` 分支的代码部署到生产环境（https://admin.supplynexus.store）。

## 🔄 部署流程

### 前提条件

1. **代码已合并到 main 分支**
   - 在 GitHub 上将 PR merge 到 `main` 分支
   - 确保所有测试通过

2. **服务器访问权限**
   - SSH 访问：`ssh ubuntu@133.242.179.110`
   - 服务器上的 Git 目录：`/home/ubuntu/project/fulfillment-service`
   - 部署目录：`/opt/supplynexus`

### 快速部署（推荐）

使用自动化脚本一键部署：

```bash
# SSH 到服务器
ssh ubuntu@133.242.179.110

# 执行部署脚本
cd /opt/supplynexus
./scripts/prod/deploy-from-git.sh
```

### 手动部署步骤

如果需要手动执行，按以下步骤操作：

#### 步骤 1: 拉取最新代码

```bash
# SSH 到服务器
ssh ubuntu@133.242.179.110

# 进入 Git 目录
cd /home/ubuntu/project/fulfillment-service

# 处理本地修改（如果有）
git stash

# 切换到 main 分支并拉取最新代码
git checkout main
git pull origin main

# 查看最新提交
git log --oneline -3
```

#### 步骤 2: 同步代码到部署目录

```bash
# 从 Git 目录同步代码到部署目录
rsync -avz --delete \
    --exclude '.git' \
    --exclude 'node_modules' \
    --exclude '.next' \
    --exclude 'backend/.venv' \
    --exclude 'backend/logs' \
    --exclude 'frontend/keys' \
    --exclude 'deployment/environments/env.prod' \
    --exclude 'deployment/environments/frontend/env.prod' \
    --exclude 'docker-compose.prod.yml' \
    /home/ubuntu/project/fulfillment-service/ \
    /opt/supplynexus/
```

#### 步骤 3: 上传环境配置文件（首次部署或配置变更时）

从本地执行：

```bash
# 上传后端环境配置
scp deployment/environments/env.prod ubuntu@133.242.179.110:/opt/supplynexus/deployment/environments/

# 上传前端环境配置
scp deployment/environments/frontend/env.prod ubuntu@133.242.179.110:/opt/supplynexus/deployment/environments/frontend/

# 上传 Docker Compose 配置
scp docker-compose.prod.yml ubuntu@133.242.179.110:/opt/supplynexus/
```

#### 步骤 4: 运行数据库迁移

```bash
# 进入部署目录
cd /opt/supplynexus

# 运行数据库迁移
docker-compose -f docker-compose.prod.yml exec -T backend alembic upgrade head
```

#### 步骤 5: 重新构建并启动服务

```bash
# 重新构建并启动所有生产环境服务
cd /opt/supplynexus
docker-compose -f docker-compose.prod.yml up -d --build

# 等待服务启动（约 30 秒）
sleep 30
```

#### 步骤 6: 验证部署

```bash
# 检查服务状态
docker-compose -f docker-compose.prod.yml ps

# 查看服务日志
docker-compose -f docker-compose.prod.yml logs --tail 50

# 检查后端健康状态
curl -H 'Host: api.supplynexus.store' http://localhost:8000/api/v1/health

# 检查前端（通过浏览器访问）
# https://admin.supplynexus.store
```

## 🔍 故障排查

参考 `scripts/dev/DEPLOYMENT.md` 中的故障排查部分，使用 `docker-compose.prod.yml` 替代 `docker-compose.dev.yml`。

## 📝 注意事项

1. **数据持久化**
   - 生产环境的数据库和 Redis 数据存储在 Docker volumes 中
   - 数据不会因为代码更新而丢失

2. **环境配置**
   - 生产环境使用 `docker-compose.prod.yml`
   - 环境变量从 `deployment/environments/env.prod` 和 `deployment/environments/frontend/env.prod` 加载
   - 这些文件包含敏感信息，不会提交到 Git

3. **服务端口**
   - Backend: `8000`
   - Frontend: `3000`
   - PostgreSQL: `5432` (仅内部访问)
   - Redis: `6379` (仅内部访问)

4. **防火墙配置**
   - 首次部署需要配置 UFW 防火墙
   - 执行：`sudo ./scripts/prod/setup-ufw.sh`

5. **SSL 证书**
   - 生产环境使用 Let's Encrypt SSL 证书
   - 证书自动续期已配置
