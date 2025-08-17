# SupplyNexus Fulfillment Service

一个基于 FastAPI + Next.js 的 Shopify 到 Printify 订单履行自动化系统，支持多租户架构和完整的认证系统。

## 🚀 项目状态

**当前状态**: 核心功能已完成，准备进入业务功能开发阶段  
**最后更新**: 2025-08-17

### ✅ 已完成功能

- **认证系统**: RSA签名验证 + 前端JWT自主管理
- **前端应用**: Next.js + React + TypeScript，完整的登录流程
- **后端API**: FastAPI + PostgreSQL，完整的RESTful API
- **Docker部署**: 完整的容器化部署配置
- **开发环境**: 热重载、调试工具、环境管理

## 🏃‍♂️ 快速开始

### 开发环境

1. **启动后端服务**
   ```bash
   cd backend
   source .venv/bin/activate
   python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

2. **启动前端服务**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

3. **启动数据库和Redis**
   ```bash
   docker-compose up -d postgres redis
   ```

### Docker部署

```bash
cd deployment/docker/frontend
./deploy.sh local
```

### 验证部署

```bash
./scripts/verify-deployment.sh
```

## 🔐 认证系统

### 认证流程
1. 前端接收用户登录信息
2. 生成RSA签名（使用租户私钥）
3. 发送请求到后端API
4. 后端验证签名和用户凭据
5. 返回用户信息给前端
6. 前端生成JWT令牌（使用前端私钥）
7. 存储令牌到localStorage

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

## 📚 详细文档

- **项目进度**: [docs/PROGRESS_LOG.md](docs/PROGRESS_LOG.md)
- **快速开始**: [docs/QUICK_START.md](docs/QUICK_START.md)
- **开发指南**: [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md)
- **部署指南**: [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)

## 🤝 贡献

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

---

**项目状态**: 核心功能已完成，准备进入业务功能开发阶段  
**最后更新**: 2025-08-17  
**下一步重点**: Shopify和Printify集成