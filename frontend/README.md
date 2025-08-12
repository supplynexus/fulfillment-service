# 🚀 SupplyNexus Frontend

SupplyNexus Fulfillment Service 的前端管理界面，基于 Next.js 构建。

## 📋 功能特性

- **多租户支持**: 支持多个客户租户的数据隔离
- **用户认证**: JWT 认证和权限管理
- **订单管理**: Shopify 订单查看和管理
- **库存管理**: 库存状态监控和补货提醒
- **发货管理**: 自动发货和 Printify 集成
- **响应式设计**: 支持桌面和移动设备

## 🛠️ 技术栈

- **框架**: Next.js 14 (React 18)
- **UI 组件**: Material-UI (MUI)
- **状态管理**: Zustand
- **数据获取**: SWR + React Query
- **表单处理**: React Hook Form
- **类型检查**: TypeScript
- **代码规范**: ESLint + Prettier

## 🚀 快速开始

### 1. 环境准备

```bash
# 确保 Node.js 版本 >= 18.0.0
node --version

# 安装依赖
npm install
```

### 2. 密钥配置

**重要**: 在开始开发之前，必须配置密钥文件：

```bash
# 进入frontend目录
cd frontend

# 生成RSA密钥对
mkdir -p keys
openssl genrsa -out keys/frontend_private_key.pem 2048
openssl rsa -in keys/frontend_private_key.pem -pubout -out keys/frontend_public_key.pem
```

### 3. 环境变量配置

```bash
# 复制环境配置示例
cp environment.example .env.local

# 编辑环境变量
nano .env.local
```

**必需的环境变量**:
```bash
# Backend API 配置
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_APP_NAME=SupplyNexus Fulfillment Service

# Frontend 服务器认证
FRONTEND_PRIVATE_KEY_PATH=./keys/frontend_private_key.pem
FRONTEND_KEY_ID=frontend-server-1
FRONTEND_USER_EMAIL=frontend@supplynexus.store

# 认证设置
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=your-nextauth-secret-change-this-in-prod
```

### 4. 启动开发服务器

```bash
# 启动开发服务器
npm run dev

# 访问应用
open http://localhost:3000
```

## 🔐 认证架构

### 前端-后端通信

1. **服务器端 API 调用**: 使用 RSA 密钥对进行签名认证
2. **客户端 API 调用**: 使用 JWT 令牌进行用户认证

### 密钥管理

- **私钥**: 存储在 `frontend/keys/frontend_private_key.pem` (不上传 Git)
- **公钥**: 存储在 Backend 数据库的 `user_keys` 表中
- **密钥轮换**: 支持密钥过期和轮换机制

## 📁 项目结构

```
frontend/
├── keys/                    # 密钥文件目录 (不上传 Git)
│   ├── frontend_private_key.pem
│   ├── frontend_public_key.pem
│   └── README.md
├── public/                  # 静态资源
├── src/
│   ├── app/                # Next.js App Router
│   ├── components/         # React 组件
│   ├── hooks/              # 自定义 Hooks
│   ├── lib/                # 工具库
│   ├── services/           # API 服务
│   ├── stores/             # Zustand 状态管理
│   └── types/              # TypeScript 类型定义
├── tests/                  # 测试文件
├── environment.example     # 环境变量示例
└── README.md              # 项目文档
```

## 🔧 开发命令

```bash
# 开发服务器
npm run dev

# 构建生产版本
npm run build

# 启动生产服务器
npm run start

# 代码检查
npm run lint
npm run lint:fix

# 类型检查
npm run type-check

# 运行测试
npm run test
npm run test:watch
npm run test:coverage
```

## 🌍 环境配置

### 本地开发环境
- **端口**: 3000
- **API URL**: http://localhost:8000
- **数据库**: 本地 PostgreSQL
- **密钥**: 本地生成的密钥对

### 开发服务器环境
- **端口**: 3000
- **API URL**: https://api.dev.supplynexus.store
- **数据库**: 开发服务器 PostgreSQL
- **密钥**: 服务器环境变量中的密钥

### 生产环境
- **端口**: 3000
- **API URL**: https://api.supplynexus.store
- **数据库**: 生产 PostgreSQL
- **密钥**: 生产环境变量中的密钥

## 🔒 安全注意事项

1. **密钥文件**: 永远不要将私钥文件提交到 Git 仓库
2. **环境变量**: 敏感信息使用环境变量，不要硬编码
3. **HTTPS**: 生产环境必须使用 HTTPS
4. **CORS**: 正确配置跨域请求策略
5. **输入验证**: 所有用户输入都要进行验证和清理

## 🧪 测试

```bash
# 运行所有测试
npm run test

# 运行测试并监听文件变化
npm run test:watch

# 生成测试覆盖率报告
npm run test:coverage
```

## 📦 部署

### Docker 部署

```bash
# 构建 Docker 镜像
docker build -t supplynexus-frontend .

# 运行容器
docker run -p 3000:3000 supplynexus-frontend
```

### 手动部署

```bash
# 构建生产版本
npm run build

# 启动生产服务器
npm run start
```

## 🤝 贡献指南

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add some amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 🆘 故障排除

### 常见问题

1. **密钥文件不存在**
   ```bash
   # 重新生成密钥
   openssl genrsa -out keys/frontend_private_key.pem 2048
   openssl rsa -in keys/frontend_private_key.pem -pubout -out keys/frontend_public_key.pem
   ```

2. **数据库连接失败**
   - 检查 Backend 服务是否运行
   - 验证 API URL 配置
   - 确认网络连接

3. **认证失败**
   - 检查密钥文件权限
   - 验证公钥是否已注册到 Backend
   - 确认环境变量配置

### 获取帮助

- 查看 [Backend 文档](../backend/README.md)
- 检查 [开发工作流文档](../docs/DEVELOPMENT_WORKFLOW.md)
- 提交 Issue 到项目仓库
