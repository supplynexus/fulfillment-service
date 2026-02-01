#!/bin/bash
# 生产环境完整部署脚本
# 此脚本将代码和配置文件上传到服务器，并执行部署步骤

set -e

SERVER="ubuntu@133.242.179.110"
DEPLOY_PATH="/opt/supplynexus"
PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"

echo "🚀 开始生产环境部署流程..."
echo ""

# 检查必需文件
echo "📋 检查必需文件..."
if [ ! -f "$PROJECT_ROOT/deployment/environments/env.prod" ]; then
    echo "❌ 错误: deployment/environments/env.prod 文件不存在"
    exit 1
fi

if [ ! -f "$PROJECT_ROOT/deployment/environments/frontend/env.prod" ]; then
    echo "❌ 错误: deployment/environments/frontend/env.prod 文件不存在"
    exit 1
fi

if [ ! -f "$PROJECT_ROOT/docker-compose.prod.yml" ]; then
    echo "❌ 错误: docker-compose.prod.yml 文件不存在"
    exit 1
fi

echo "✅ 所有必需文件检查通过"
echo ""

# 步骤 1: 创建服务器目录结构
echo "📁 步骤 1: 创建服务器目录结构..."
ssh $SERVER "sudo mkdir -p $DEPLOY_PATH/{backend,frontend,deployment/environments/frontend,scripts/prod,scripts/db}"
ssh $SERVER "sudo mkdir -p /var/log/supplynexus/{backend,celery-worker,celery-beat,frontend}"
ssh $SERVER "sudo chown -R ubuntu:ubuntu $DEPLOY_PATH"
ssh $SERVER "sudo chown -R ubuntu:ubuntu /var/log/supplynexus"
echo "✅ 目录结构创建完成"
echo ""

# 步骤 2: 上传项目代码（排除敏感文件和构建产物）
echo "📤 步骤 2: 上传项目代码..."
cd "$PROJECT_ROOT"
rsync -avz --progress \
    --exclude '.git/' \
    --exclude '.gitignore' \
    --exclude 'node_modules/' \
    --exclude '.next/' \
    --exclude 'backend/.venv/' \
    --exclude 'backend/logs*/' \
    --exclude 'frontend/logs*/' \
    --exclude 'frontend/.next/' \
    --exclude 'frontend/keys/' \
    --exclude 'deployment/environments/env.prod' \
    --exclude 'deployment/environments/frontend/env.prod' \
    --exclude 'docker-compose.prod.yml' \
    --exclude '*.pyc' \
    --exclude '__pycache__/' \
    --exclude '.env*' \
    "$PROJECT_ROOT/" "$SERVER:$DEPLOY_PATH/"
echo "✅ 代码上传完成"
echo ""

# 步骤 3: 上传敏感配置文件
echo "📤 步骤 3: 上传生产环境配置文件..."
scp "$PROJECT_ROOT/deployment/environments/env.prod" "$SERVER:$DEPLOY_PATH/deployment/environments/"
scp "$PROJECT_ROOT/deployment/environments/frontend/env.prod" "$SERVER:$DEPLOY_PATH/deployment/environments/frontend/"
scp "$PROJECT_ROOT/docker-compose.prod.yml" "$SERVER:$DEPLOY_PATH/"
echo "✅ 配置文件上传完成"
echo ""

# 步骤 4: 上传部署脚本
echo "📤 步骤 4: 上传部署脚本..."
scp "$PROJECT_ROOT/scripts/prod/setup-ufw.sh" "$SERVER:$DEPLOY_PATH/scripts/prod/"
scp "$PROJECT_ROOT/scripts/db/alembic.sh" "$SERVER:$DEPLOY_PATH/scripts/db/"
ssh $SERVER "chmod +x $DEPLOY_PATH/scripts/prod/*.sh $DEPLOY_PATH/scripts/db/*.sh"
echo "✅ 部署脚本上传完成"
echo ""

# 步骤 5: 上传前端密钥（如果存在）
if [ -d "$PROJECT_ROOT/frontend/keys" ] && [ "$(ls -A $PROJECT_ROOT/frontend/keys 2>/dev/null)" ]; then
    echo "📤 步骤 5: 上传前端密钥..."
    ssh $SERVER "mkdir -p $DEPLOY_PATH/frontend/keys"
    rsync -avz "$PROJECT_ROOT/frontend/keys/" "$SERVER:$DEPLOY_PATH/frontend/keys/"
    echo "✅ 前端密钥上传完成"
else
    echo "⚠️  步骤 5: 前端密钥目录不存在或为空，跳过"
fi
echo ""

echo "✅ 所有文件上传完成！"
echo ""
echo "📝 下一步操作（在服务器上执行）："
echo ""
echo "1. SSH 到服务器:"
echo "   ssh $SERVER"
echo ""
echo "2. 进入部署目录:"
echo "   cd $DEPLOY_PATH"
echo ""
echo "3. 配置防火墙（首次部署）:"
echo "   sudo ./scripts/prod/setup-ufw.sh"
echo ""
echo "4. 运行数据库迁移:"
echo "   ./scripts/db/alembic.sh prod upgrade"
echo ""
echo "5. 启动生产环境服务:"
echo "   docker-compose -f docker-compose.prod.yml up -d"
echo ""
echo "6. 检查服务状态:"
echo "   docker-compose -f docker-compose.prod.yml ps"
echo "   docker-compose -f docker-compose.prod.yml logs -f"
echo ""
