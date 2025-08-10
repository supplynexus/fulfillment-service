# SupplyNexus Backend 快速启动指南

## 🚀 一键启动命令

### 开发模式（推荐）
```bash
cd backend && ./scripts/dev.sh
```

### 生产模式
```bash
cd backend && ./scripts/start.sh
```

### 手动启动
```bash
cd backend && source .venv/bin/activate && python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 📍 访问地址

- **API 文档**：http://localhost:8000/api/v1/docs
- **健康检查**：http://localhost:8000/api/v1/health
- **API 端点**：http://localhost:8000/api/v1/

## ⚠️ 重要提醒

1. **确保在 backend 目录下运行**
2. **确保虚拟环境已激活**
3. **确保 .env 文件已配置**
4. **确保 HEALTH_CHECK_API_KEY 已设置**

## 🔧 故障排除

### 虚拟环境问题
```bash
# 重新创建虚拟环境
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 端口占用问题
```bash
# 使用不同端口
PORT=8080 ./scripts/dev.sh
```

### 权限问题
```bash
# 给脚本执行权限
chmod +x scripts/*.sh
```

## 📚 更多信息

- [详细文档](./README_DATABASE.md)
- [健康检查安全配置](./docs/HEALTH_CHECK_SECURITY.md)
- [环境配置指南](./docs/HEALTH_CHECKS.md)
