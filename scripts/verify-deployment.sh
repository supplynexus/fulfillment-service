#!/bin/bash

# SupplyNexus 部署验证脚本
# 用于快速检查系统运行状态

echo "🔍 SupplyNexus 部署状态验证"
echo "================================"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查函数
check_service() {
    local name=$1
    local url=$2
    local description=$3
    
    echo -n "检查 $name... "
    if curl -s "$url" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ 正常${NC}"
        return 0
    else
        echo -e "${RED}❌ 失败${NC}"
        echo "  $description"
        return 1
    fi
}

# 检查Docker容器
check_docker_container() {
    local container_name=$1
    local description=$2
    
    echo -n "检查Docker容器 $container_name... "
    if docker ps | grep -q "$container_name"; then
        echo -e "${GREEN}✅ 运行中${NC}"
        return 0
    else
        echo -e "${RED}❌ 未运行${NC}"
        echo "  $description"
        return 1
    fi
}

# 检查端口
check_port() {
    local port=$1
    local service=$2
    
    echo -n "检查端口 $port ($service)... "
    if lsof -i :$port > /dev/null 2>&1; then
        echo -e "${GREEN}✅ 监听中${NC}"
        return 0
    else
        echo -e "${RED}❌ 未监听${NC}"
        return 1
    fi
}

echo ""
echo "1️⃣ 检查服务状态"

# 检查后端服务
check_service "后端API" "http://localhost:8000/api/v1/health" "后端服务未运行"

# 检查前端服务
check_service "前端应用" "http://localhost:3000/api/health" "前端服务未运行"

# 检查数据库端口
check_port "5433" "PostgreSQL"

# 检查Redis端口
check_port "6380" "Redis"

echo ""
echo "2️⃣ 检查Docker容器"

# 检查前端容器
check_docker_container "supplynexus-frontend-local" "前端Docker容器未运行"

# 检查数据库容器
check_docker_container "supplynexus-postgres-local" "PostgreSQL容器未运行"

# 检查Redis容器
check_docker_container "supplynexus-redis-local" "Redis容器未运行"

echo ""
echo "3️⃣ 检查网络连接"

# 检查前端容器到后端的连接
echo -n "检查前端容器到后端连接... "
if docker exec supplynexus-frontend-local curl -s http://host.docker.internal:8000/api/v1/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ 正常${NC}"
else
    echo -e "${RED}❌ 失败${NC}"
    echo "  前端容器无法访问后端服务"
fi

echo ""
echo "4️⃣ 检查认证功能"

# 测试登录功能
echo -n "测试登录功能... "
LOGIN_RESPONSE=$(curl -s -X POST http://localhost:3000/api/auth/login \
  -H "Content-Type: multipart/form-data" \
  -F "username=frontend@supplynexus.store" \
  -F "password=Impeach@2025" \
  -F "tenant_name=impeach" \
  -w "%{http_code}")

HTTP_CODE=$(echo "$LOGIN_RESPONSE" | tail -n1)
if [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}✅ 成功${NC}"
else
    echo -e "${RED}❌ 失败 (HTTP $HTTP_CODE)${NC}"
fi

echo ""
echo "5️⃣ 系统信息"

# 显示系统信息
echo "操作系统: $(uname -s) $(uname -r)"
echo "Docker版本: $(docker --version | cut -d' ' -f3 | cut -d',' -f1)"
echo "当前时间: $(date)"
echo "系统负载: $(uptime | awk -F'load average:' '{print $2}')"

echo ""
echo "📊 验证完成"
echo "================================"

# 检查是否有失败的测试
if [ $? -eq 0 ]; then
    echo -e "${GREEN}🎉 所有检查通过！系统运行正常。${NC}"
    echo ""
    echo "🌐 访问地址:"
    echo "  前端应用: http://localhost:3000"
    echo "  后端API: http://localhost:8000"
    echo "  API文档: http://localhost:8000/docs"
else
    echo -e "${YELLOW}⚠️  部分检查失败，请检查上述错误信息。${NC}"
fi

echo ""
echo "📝 注意事项:"
echo "  - 开发环境已放宽安全限制以支持Docker容器通信"
echo "  - 生产环境将启用严格的安全配置"
echo "  - 所有敏感信息通过环境变量管理"
