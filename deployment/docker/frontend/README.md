# SupplyNexus Frontend Docker 部署

## 概述

本目录包含 SupplyNexus 前端应用的 Docker 部署配置。

## 快速开始

### 1. 环境准备

确保以下文件存在：
- `../../../frontend/keys/` - 包含前端JWT密钥和租户密钥
- `environment.local` - 本地环境配置

### 2. 启动服务

```bash
# 启动前端容器
./deploy.sh local

# 或者直接使用 docker-compose
docker-compose up -d
```

### 3. 验证部署

```bash
# 运行测试脚本
./test-login.sh

# 检查容器状态
docker ps | grep supplynexus-frontend-local

# 检查健康状态
curl http://localhost:3000/api/health
```

## 配置说明

### 环境变量

- `BACKEND_API_URL` - 后端API地址（运行时环境变量）
- `NEXT_PUBLIC_API_URL` - 前端公共API地址（构建时环境变量）
- `FRONTEND_JWT_PRIVATE_KEY_PATH` - 前端JWT私钥路径
- `FRONTEND_JWT_PUBLIC_KEY_PATH` - 前端JWT公钥路径

### Volume 挂载

- `../../../frontend/keys:/app/keys:ro` - 密钥文件目录（只读）
- `./logs-local:/app/logs` - 应用日志目录
- `./logs-local:/var/log/app` - 系统日志目录

### 网络配置

- 容器端口：3000
- 宿主机端口：3000
- 后端连接：`http://host.docker.internal:8000`

## 故障排除

### 常见问题

1. **密钥文件未找到**
   ```bash
   # 检查密钥文件是否存在
   ls -la ../../../frontend/keys/
   
   # 检查容器内挂载
   docker exec supplynexus-frontend-local ls -la /app/keys/
   ```

2. **后端连接失败**
   ```bash
   # 检查环境变量
   docker exec supplynexus-frontend-local env | grep BACKEND_API_URL
   
   # 检查后端服务状态
   curl http://localhost:8000/api/v1/health
   ```

3. **容器启动失败**
   ```bash
   # 查看容器日志
   docker logs supplynexus-frontend-local
   
   # 重新构建镜像
   docker-compose up --build -d
   ```

### 测试工具

- `test-login.sh` - 完整的登录功能测试脚本
- `deploy.sh` - 部署脚本，支持不同环境

## 安全注意事项

1. **密钥文件**：通过 volume 挂载，不在镜像中包含
2. **环境变量**：敏感信息通过环境变量传递
3. **网络隔离**：使用 Docker 网络隔离
4. **权限控制**：容器以非 root 用户运行

## 更新日志

### 2025-08-17
- ✅ 修复环境变量问题：使用 `BACKEND_API_URL` 避免构建时内联
- ✅ 添加密钥文件 volume 挂载
- ✅ 添加日志目录 volume 挂载
- ✅ 创建测试脚本验证部署
- ✅ 更新部署文档
