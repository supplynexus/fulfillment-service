#!/bin/bash
# 生产环境配置文件上传脚本
# 将配置文件上传到服务器

set -e

SERVER="ubuntu@133.242.179.110"
DEPLOY_PATH="/opt/supplynexus"

echo "📤 上传生产环境配置文件到服务器..."

# 检查文件是否存在
if [ ! -f "deployment/environments/env.prod" ]; then
    echo "❌ 错误: deployment/environments/env.prod 文件不存在"
    exit 1
fi

if [ ! -f "docker-compose.prod.yml" ]; then
    echo "❌ 错误: docker-compose.prod.yml 文件不存在"
    exit 1
fi

# 创建服务器目录
echo "📁 在服务器上创建目录..."
ssh $SERVER "sudo mkdir -p $DEPLOY_PATH/deployment/environments"
ssh $SERVER "sudo mkdir -p $DEPLOY_PATH/scripts/prod"
ssh $SERVER "sudo mkdir -p /var/log/supplynexus/{backend,celery-worker,celery-beat,frontend}"
ssh $SERVER "sudo chown -R ubuntu:ubuntu $DEPLOY_PATH"
ssh $SERVER "sudo chown -R ubuntu:ubuntu /var/log/supplynexus"

# 上传配置文件
echo "📤 上传环境配置文件..."
scp deployment/environments/env.prod $SERVER:$DEPLOY_PATH/deployment/environments/
scp deployment/environments/frontend/env.prod $SERVER:$DEPLOY_PATH/deployment/environments/frontend/

# 上传 Docker Compose 配置
echo "📤 上传 Docker Compose 配置..."
scp docker-compose.prod.yml $SERVER:$DEPLOY_PATH/

# 上传防火墙配置脚本
echo "📤 上传防火墙配置脚本..."
scp scripts/prod/setup-ufw.sh $SERVER:$DEPLOY_PATH/scripts/prod/
ssh $SERVER "chmod +x $DEPLOY_PATH/scripts/prod/setup-ufw.sh"

echo "✅ 配置文件上传完成！"
echo ""
echo "📝 下一步："
echo "  1. SSH 到服务器: ssh $SERVER"
echo "  2. 进入部署目录: cd $DEPLOY_PATH"
echo "  3. 检查配置文件: cat deployment/environments/env.prod"
echo "  4. 配置防火墙: sudo ./scripts/prod/setup-ufw.sh"
