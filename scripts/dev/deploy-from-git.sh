#!/bin/bash
# 从 Git 仓库部署 develop 分支到 dev 环境
# 使用方法: ./scripts/dev/deploy-from-git.sh

set -e

GIT_DIR="/home/ubuntu/project/fulfillment-service"
DEPLOY_DIR="/opt/supplynexus"

echo "🚀 开始从 Git 仓库部署 develop 分支到 dev 环境..."
echo ""

# 步骤 1: 在 Git 目录拉取最新代码
echo "📥 步骤 1: 在 Git 目录拉取最新代码..."
cd "$GIT_DIR"

# 处理本地修改
if [ -n "$(git status --porcelain)" ]; then
    echo "⚠️  检测到本地修改，保存到 stash..."
    git stash
fi

# 切换到 develop 分支并拉取最新代码
echo "切换到 develop 分支..."
git checkout develop
echo "拉取最新代码..."
git pull origin develop

echo "✅ Git 代码更新完成"
echo "最新提交:"
git log --oneline -3
echo ""

# 步骤 2: 删除冲突的 route.ts 文件（如果存在）
echo "🧹 步骤 2: 清理冲突文件..."
if [ -f "$GIT_DIR/frontend/src/app/route.ts" ]; then
    echo "删除冲突的 route.ts 文件..."
    rm -f "$GIT_DIR/frontend/src/app/route.ts"
fi
echo "✅ 清理完成"
echo ""

# 步骤 3: 同步代码到部署目录
echo "🔄 步骤 3: 同步代码到部署目录 ($DEPLOY_DIR)..."
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
    --exclude 'frontend/.monitor' \
    --exclude 'frontend/.update' \
    --exclude 'frontend/lrt' \
    "$GIT_DIR/" "$DEPLOY_DIR/"

echo "✅ 代码同步完成"
echo ""

# 步骤 4: 运行数据库迁移（如果需要）
echo "📊 步骤 4: 运行数据库迁移..."
cd "$DEPLOY_DIR"
docker-compose -f docker-compose.dev.yml exec -T backend_dev alembic upgrade head 2>&1 | tail -20

echo "✅ 数据库迁移完成"
echo ""

# 步骤 5: 重新构建并启动 dev 环境服务
echo "🐳 步骤 5: 重新构建并启动 dev 环境服务..."
cd "$DEPLOY_DIR"
docker-compose -f docker-compose.dev.yml up -d --build

echo "等待服务启动..."
sleep 20

# 步骤 6: 检查服务状态
echo "📊 步骤 6: 检查服务状态..."
docker-compose -f docker-compose.dev.yml ps

echo ""
echo "🎉 部署完成！"
echo ""
echo "Dev 环境服务地址:"
echo "  - 前端: https://admin.dev.supplynexus.store"
echo "  - 后端 API: https://api.dev.supplynexus.store"
echo ""
echo "服务日志（最后 10 行）:"
docker-compose -f docker-compose.dev.yml logs --tail 10
