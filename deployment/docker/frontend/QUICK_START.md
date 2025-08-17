# Frontend 快速部署指南

## 🚀 本地环境快速部署

### 1. 准备环境

```bash
# 进入前端部署目录
cd deployment/docker/frontend

# 确保密钥目录存在
mkdir -p ../../../frontend/keys

# 将私钥文件放入 keys 目录
# 例如: ../../../frontend/keys/impeach_private_key.pem
```

### 2. 配置环境变量

```bash
# 复制本地环境配置
cp ../../environments/env.frontend.local ../../environments/env.frontend.local

# 编辑配置文件
vim ../../environments/env.frontend.local
```

**重要配置项**：
```bash
# 后端 API 地址 - 确保后端在 localhost:8000 运行
NEXT_PUBLIC_API_URL=http://localhost:8000

# 前端端口
FRONTEND_PORT=3000

# 密钥路径
KEYS_PATH=../../frontend/keys
```

### 3. 部署

```bash
# 完整部署（构建 + 启动）
./deploy.sh local deploy

# 或者分步执行
./deploy.sh local build
./deploy.sh local start
```

### 4. 验证

```bash
# 查看服务状态
./deploy.sh local status

# 查看日志
./deploy.sh local logs
```

# 健康检查
curl http://localhost:3000/api/health
```

## 📁 目录映射说明

### 密钥目录映射
```
宿主机: ../../../frontend/keys
容器内: /app/keys (只读)
```

### 日志目录映射
```
宿主机: ./logs-local/
容器内: /var/log/app
```

### 环境变量文件映射
```
宿主机: ../../environments/env.frontend.local
容器内: /app/.env.local (只读)
```

## 🔧 配置详解

### 后端 API URL 配置
- **位置**: `deployment/environments/env.frontend.local`
- **配置项**: `NEXT_PUBLIC_API_URL=http://localhost:8000`
- **说明**: 前端容器通过 `localhost:8000` 访问宿主机上运行的后端服务

### 密钥文件配置
- **宿主机路径**: `frontend/keys/`
- **容器内路径**: `/app/keys/`
- **权限**: 只读 (`:ro`)
- **文件**: `impeach_private_key.pem` 等

### 日志配置
- **宿主机路径**: `deployment/docker/frontend/logs-local/`
- **容器内路径**: `/var/log/app`
- **轮转**: 最大 10MB，保留 3 个文件

## 🌐 访问地址

- **前端应用**: http://localhost:3000
- **健康检查**: http://localhost:3000/api/health
- **后端 API**: http://localhost:8000 (需要单独启动)

## 🚨 常见问题

### 1. 后端连接失败
```bash
# 确保后端服务正在运行
curl http://localhost:8000/health

# 检查网络连接
docker-compose exec frontend curl http://host.docker.internal:8000/health
```

### 2. 密钥文件问题
```bash
# 检查密钥文件权限
ls -la ../../../frontend/keys/

# 检查密钥文件内容
cat ../../../frontend/keys/impeach_private_key.pem
```

### 3. 端口冲突
```bash
# 检查端口占用
netstat -tulpn | grep :3000

# 修改端口
vim ../../environments/env.frontend.local
# 修改 FRONTEND_PORT=3001
```

## 📊 管理命令

```bash
# 启动服务
./deploy.sh local start

# 停止服务
./deploy.sh local stop

# 重启服务
./deploy.sh local restart

# 查看状态
./deploy.sh local status

# 查看日志
./deploy.sh local logs

# 清理资源
./deploy.sh local cleanup
```
