#!/bin/bash

# 测试前端Docker容器的登录功能
echo "=== 测试前端Docker容器登录功能 ==="

# 检查容器状态
echo "1. 检查容器状态..."
docker ps | grep supplynexus-frontend-local

# 检查健康状态
echo -e "\n2. 检查健康状态..."
docker exec supplynexus-frontend-local curl -s http://localhost:3000/api/health | jq .

# 检查环境变量
echo -e "\n3. 检查环境变量..."
docker exec supplynexus-frontend-local env | grep -E "(BACKEND_API_URL|NEXT_PUBLIC_API_URL)"

# 检查密钥文件
echo -e "\n4. 检查密钥文件..."
docker exec supplynexus-frontend-local ls -la /app/keys/

# 测试登录API（模拟请求）
echo -e "\n5. 测试登录API..."
curl -X POST http://localhost:3000/api/auth/login \
  -H "Content-Type: multipart/form-data" \
  -F "username=frontend@supplynexus.store" \
  -F "password=test123" \
  -F "tenant_name=impeach" \
  -w "\nHTTP状态码: %{http_code}\n" \
  -s

echo -e "\n=== 测试完成 ==="
