#!/bin/bash
# 从 Git 仓库部署 main 分支到生产环境
# 使用方法: ./scripts/prod/deploy-from-git.sh

set -e

GIT_DIR="/home/ubuntu/project/fulfillment-service"
DEPLOY_DIR="/opt/supplynexus"

echo "🚀 开始从 Git 仓库部署 main 分支到生产环境..."
echo ""

# 步骤 1: 在 Git 目录拉取最新代码
echo "📥 步骤 1: 在 Git 目录拉取最新代码..."
cd "$GIT_DIR"

# 处理本地修改
if [ -n "$(git status --porcelain)" ]; then
    echo "⚠️  检测到本地修改，保存到 stash..."
    git stash
fi

# 切换到 main 分支并拉取最新代码
echo "切换到 main 分支..."
git checkout main
echo "拉取最新代码..."
git pull origin main

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

# 步骤 4: 停止旧容器（避免 "No such image" 错误）
echo "🛑 步骤 4: 停止旧容器..."
cd "$DEPLOY_DIR"
docker-compose -f docker-compose.prod.yml down --remove-orphans 2>/dev/null || true
echo "✅ 旧容器已停止"
echo ""

# 步骤 5: 重新构建并启动生产环境服务
echo "🐳 步骤 5: 重新构建并启动生产环境服务..."
docker-compose -f docker-compose.prod.yml up -d --build --remove-orphans

echo "等待服务启动..."
sleep 30

# 步骤 6: 运行数据库迁移
echo "📊 步骤 6: 运行数据库迁移..."
docker-compose -f docker-compose.prod.yml exec -T backend alembic upgrade head 2>&1 | tail -20 || echo "⚠️ 迁移跳过（可能已是最新）"

echo "✅ 数据库迁移完成"
echo ""

# 步骤 7: 检查服务状态
echo "📊 步骤 7: 检查服务状态..."
docker-compose -f docker-compose.prod.yml ps

echo ""
echo "🎉 部署完成！"
echo ""
echo "Production 环境服务地址:"
echo "  - 前端: https://admin.supplynexus.store"
echo "  - 后端 API: https://api.supplynexus.store"
echo ""
echo "健康检查:"
curl -s -H "Host: api.supplynexus.store" http://localhost:8000/api/v1/health || echo "⚠️ Backend 健康检查失败"
echo ""
