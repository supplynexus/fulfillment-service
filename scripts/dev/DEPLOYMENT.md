# Develop 分支部署流程

## 📋 概述

本文档描述如何将 `develop` 分支的代码部署到 dev 环境（https://admin.dev.supplynexus.store）。

## 🔄 部署流程

### 前提条件

1. **代码已合并到 develop 分支**
   - 在 GitHub 上将 PR merge 到 `develop` 分支
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
./scripts/dev/deploy-from-git.sh
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

# 切换到 develop 分支并拉取最新代码
git checkout develop
git pull origin develop

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

#### 步骤 3: 运行数据库迁移

```bash
# 进入部署目录
cd /opt/supplynexus

# 运行数据库迁移
docker-compose -f docker-compose.dev.yml exec -T backend_dev alembic upgrade head
```

#### 步骤 4: 重新构建并启动服务

```bash
# 重新构建并启动所有 dev 环境服务
cd /opt/supplynexus
docker-compose -f docker-compose.dev.yml up -d --build

# 等待服务启动（约 20 秒）
sleep 20
```

#### 步骤 5: 验证部署

```bash
# 检查服务状态
docker-compose -f docker-compose.dev.yml ps

# 查看服务日志
docker-compose -f docker-compose.dev.yml logs --tail 50

# 检查后端健康状态
curl -H 'Host: api.dev.supplynexus.store' http://localhost:8001/api/v1/health

# 检查前端（通过浏览器访问）
# https://admin.dev.supplynexus.store
```

## 🔍 故障排查

### 服务启动失败

```bash
# 查看详细日志
docker-compose -f docker-compose.dev.yml logs backend_dev
docker-compose -f docker-compose.dev.yml logs frontend_dev

# 检查容器状态
docker-compose -f docker-compose.dev.yml ps

# 重启服务
docker-compose -f docker-compose.dev.yml restart
```

### 数据库迁移失败

```bash
# 查看迁移状态
docker-compose -f docker-compose.dev.yml exec -T backend_dev alembic current

# 查看迁移历史
docker-compose -f docker-compose.dev.yml exec -T backend_dev alembic history

# 手动执行迁移
docker-compose -f docker-compose.dev.yml exec -T backend_dev alembic upgrade head
```

### 端口冲突

如果遇到端口冲突，检查是否有其他服务占用：

```bash
# 检查端口占用
netstat -tlnp | grep -E ':(8001|3001|5433|6380)'

# 停止冲突的服务
docker-compose -f docker-compose.dev.yml down
```

## 📝 注意事项

1. **数据持久化**
   - Dev 环境的数据库和 Redis 数据存储在 Docker volumes 中
   - 数据不会因为代码更新而丢失

2. **环境配置**
   - Dev 环境使用 `docker-compose.dev.yml`
   - 环境变量在 `docker-compose.dev.yml` 中直接配置
   - 不需要额外的 `.env` 文件

3. **服务端口**
   - Backend: `8001` (避免与 prod 的 8000 冲突)
   - Frontend: `3001` (避免与 prod 的 3000 冲突)
   - PostgreSQL: `5433` (避免与 prod 的 5432 冲突)
   - Redis: `6380` (避免与 prod 的 6379 冲突)

4. **代码同步**
   - 使用 `rsync` 同步代码，排除构建产物和敏感文件
   - 确保不会覆盖服务器上的配置文件

5. **服务重启**
   - 代码更新后需要重新构建 Docker 镜像
   - 使用 `--build` 参数确保使用最新代码

## 🔄 回滚操作

如果需要回滚到之前的版本：

```bash
# 进入 Git 目录
cd /home/ubuntu/project/fulfillment-service

# 查看提交历史
git log --oneline -10

# 切换到之前的提交
git checkout <commit-hash>

# 重新同步和部署
cd /opt/supplynexus
./scripts/dev/deploy-from-git.sh
```

## 📊 服务状态检查

部署完成后，检查以下内容：

1. **容器状态**
   ```bash
   docker-compose -f docker-compose.dev.yml ps
   ```
   所有服务应该显示为 `Up` 状态

2. **健康检查**
   ```bash
   curl -H 'Host: api.dev.supplynexus.store' http://localhost:8001/api/v1/health
   ```
   应该返回 `{"status":"healthy",...}`

3. **前端访问**
   - 浏览器访问：https://admin.dev.supplynexus.store
   - 应该能看到登录页面，右上角显示 "DEV v1.0.0" 标识

4. **日志检查**
   ```bash
   docker-compose -f docker-compose.dev.yml logs --tail 50
   ```
   检查是否有错误信息

## 🆚 与生产环境部署的区别

| 项目 | Dev 环境 | Prod 环境 |
|------|----------|-----------|
| 分支 | `develop` | `main` |
| Docker Compose | `docker-compose.dev.yml` | `docker-compose.prod.yml` |
| Backend 端口 | 8001 | 8000 |
| Frontend 端口 | 3001 | 3000 |
| PostgreSQL 端口 | 5433 | 5432 |
| Redis 端口 | 6380 | 6379 |
| 域名 | admin.dev.supplynexus.store | admin.supplynexus.store |
| 部署脚本 | `scripts/dev/deploy-from-git.sh` | `scripts/prod/deploy-from-git.sh` |
