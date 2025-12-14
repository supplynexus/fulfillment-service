# SupplyNexus Fulfillment Service

一个基于 FastAPI + Next.js 的 Shopify 到 Printify 订单履行自动化系统，支持多租户架构和完整的认证系统。

## 🚀 项目状态

**当前状态**: 认证系统重构完成，开发工具优化，准备进入业务功能开发阶段  
**最后更新**: 2025-08-25

### ✅ 已完成功能

- **认证系统**: 重构完成，统一使用租户级别RSA签名认证
- **前端应用**: Next.js + React + TypeScript，完整的登录流程
- **后端API**: FastAPI + PostgreSQL，完整的RESTful API
- **Docker部署**: 完整的容器化部署配置
- **开发工具**: 完善的代码质量检查和密钥管理工具
- **开发环境**: 热重载、调试工具、环境管理

### 🔧 最近重构

- **认证系统重构**: 删除不必要的数据库表，统一使用租户级别认证
- **开发工具优化**: 重组工具到 scripts/ 目录，新增 shell 脚本
- **代码质量改进**: 修复导入错误，添加 pre-commit 配置
- **数据库清理**: 删除 system_keys、api_keys、api_key_access_logs、user_keys 表

## 🏃‍♂️ 快速开始

### 开发环境

#### Windows 用户 - 依赖安装

如果遇到 `pydantic-core` 编译错误，请使用以下方法：
```cmd
cd backend
# 升级 pip
python -m pip install --upgrade pip setuptools wheel

# 安装预编译的 pydantic
python -m pip install --only-binary=all pydantic>=2.8.0

# 安装其他依赖
python -m pip install -r requirements-minimal.txt
```

#### 启动服务

1. **启动后端服务**
   ```bash
   cd backend
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

2. **启动 Celery 服务** (可选，用于定时任务)
   
   **Windows 用户:**
   ```powershell
   # 终端1: 启动 Celery Beat (定时任务调度器)
   cd backend
   .\.venv\Scripts\Activate.ps1
   .\scripts\start_celery_beat_windows.ps1
   # 或使用批处理: scripts\start_celery_beat_windows.bat
   
   # 终端2: 启动 Celery Worker (任务执行器)
   cd backend
   .\.venv\Scripts\Activate.ps1
   .\scripts\start_celery_worker_windows.ps1
   # 或使用批处理: scripts\start_celery_worker_windows.bat
   # 或手动启动（使用 solo 池）:
   # celery -A app.tasks.celery_app worker --loglevel=info --pool=solo -Q default,shopify,orders,order_automation
   ```
   
   **Linux/Mac 用户:**
   ```bash
   # 终端1: 启动 Celery Beat (定时任务调度器)
   cd backend
   source .venv/bin/activate
   celery -A app.tasks.celery_app beat --loglevel=info
   
   # 终端2: 启动 Celery Worker (任务执行器)
   cd backend
   source .venv/bin/activate
   celery -A app.tasks.celery_app worker --loglevel=info -Q default,shopify,orders,order_automation
   ```

3. **启动前端服务**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

4. **启动数据库和Redis**
   ```bash
   docker-compose up -d postgres redis
   ```

### 代码质量检查

```bash
cd backend/scripts

# 快速检查
./quick_check.sh

# 详细导入检查
./check_imports.sh

# 语法检查
./check_syntax.sh

# 全面质量检查
./check_code_quality.sh
```

### Docker部署

```bash
cd deployment/docker/frontend
./deploy.sh dev up
```

### 验证部署

```bash
./scripts/verify-deployment.sh
```

## 🔐 认证系统

### 认证架构
- **统一认证**: 所有业务API使用租户级别RSA签名认证
- **简化架构**: 删除用户级别密钥管理，统一使用租户公钥
- **算法匹配**: 前端和后端统一使用 RSA-SHA256 + PKCS1v15 填充

### 认证流程
1. 前端接收用户登录信息
2. 生成RSA签名（使用租户私钥）
3. 发送请求到后端API
4. 后端验证签名和用户凭据
5. 返回用户信息给前端
6. 前端生成JWT令牌（使用前端私钥）
7. 存储令牌到localStorage

### 密钥管理
```bash
cd backend/scripts

# 更新租户公钥
./update_tenant_public_key.sh <tenant_name> <private_key_file>

# 生成新密钥对
./generate_keys.sh <tenant_name> --save-db
```

## 🌐 访问地址

- **前端应用**: http://localhost:3000
- **后端API**: http://localhost:8000
- **API文档**: http://localhost:8000/docs

## 📋 下一步计划

### 短期目标 (1-2周)
1. **完善仪表板**: 数据可视化界面
2. **用户管理**: 用户CRUD操作界面
3. **订单管理**: 基础订单管理功能

### 中期目标 (1个月)
1. **Shopify集成**: 商品和订单同步
2. **Printify集成**: 订单履行自动化
3. **监控系统**: 系统监控和告警

## 📝 重要说明

### 开发环境配置
- 开发环境已放宽安全限制以支持Docker容器通信
- 生产环境将启用严格的安全配置
- 所有敏感信息通过环境变量管理

### 密钥管理
- 密钥文件不打包到Docker镜像中
- 运行时通过卷挂载提供密钥
- 支持多租户密钥管理

### 文件结构
- `frontend/src/lib/`: 前端核心库文件（认证、API、主题等）
- `frontend/public/`: 静态资源目录
- `frontend/keys/`: JWT 密钥文件目录
- `backend/scripts/`: 开发工具和脚本目录

## 📚 详细文档

- **项目进度**: [docs/PROGRESS_LOG.md](docs/PROGRESS_LOG.md)
- **快速开始**: [docs/QUICK_START.md](docs/QUICK_START.md)
- **开发指南**: [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md)
- **部署指南**: [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)
- **架构说明**: [deployment/ARCHITECTURE.md](deployment/ARCHITECTURE.md)

## 🤝 贡献

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

---

**项目状态**: 认证系统重构完成，开发工具优化，准备进入业务功能开发阶段  
**最后更新**: 2025-08-25  
**下一步重点**: Shopify和Printify集成