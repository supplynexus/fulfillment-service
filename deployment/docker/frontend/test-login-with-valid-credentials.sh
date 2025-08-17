#!/bin/bash

# 测试前端Docker容器的登录功能（使用正确凭据）
echo "=== 测试前端Docker容器登录功能（使用正确凭据） ==="

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

# 测试登录API（使用正确的凭据）
echo -e "\n5. 测试登录API（使用正确凭据）..."
echo "注意：这里需要使用正确的用户名和密码"
echo "请根据您的实际配置修改以下凭据："

# 使用环境变量或默认值
USERNAME=${TEST_USERNAME:-"frontend@supplynexus.store"}
PASSWORD=${TEST_PASSWORD:-"your_actual_password"}
TENANT_NAME=${TEST_TENANT_NAME:-"impeach"}

echo "用户名: $USERNAME"
echo "租户名: $TENANT_NAME"
echo "密码: [隐藏]"

curl -X POST http://localhost:3000/api/auth/login \
  -H "Content-Type: multipart/form-data" \
  -F "username=$USERNAME" \
  -F "password=$PASSWORD" \
  -F "tenant_name=$TENANT_NAME" \
  -w "\nHTTP状态码: %{http_code}\n" \
  -s | jq .

echo -e "\n=== 测试完成 ==="
echo "如果返回200状态码，说明登录成功"
echo "如果返回400状态码，请检查用户名、密码和租户名是否正确"
