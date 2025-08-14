# SupplyNexus Fulfillment Service - 文档索引

## 📚 主要文档

### 🏠 [项目主页](../README.md)
项目的主要文档，包含：
- 项目概述和核心功能
- 快速开始指南
- 基本开发命令
- 基本部署命令
- 故障排除

### 🛠️ [本地开发环境搭建](DEVELOPMENT.md)
详细的开发指南，包含：
- 系统要求
- 一键安装和手动安装
- 开发命令详解
- 数据库管理
- 测试指南
- 配置说明
- 故障排除

### 🚀 [快速开始指南](QUICK_START.md)
完整的快速启动指南，包含：
- 项目概述和技术栈
- 环境设置和启动步骤
- 服务检查清单
- 常用命令和故障排除
- 监控端点和认证配置

### 🚢 [环境部署指南](DEPLOYMENT.md)
完整的部署指南，包含：
- 多环境部署（local/dev/staging/prod）
- 环境配置
- Docker部署
- SSL证书配置
- 监控和日志
- 故障排查

## 🔧 技术文档

### 核心文档
- [主项目文档](../README.md) - 一站式了解项目，包含快速开始、开发指南、部署指南等
- [系统架构](../deployment/ARCHITECTURE.md) - 系统架构和部署设计
- [健康检查安全配置](../backend/docs/HEALTH_CHECK_SECURITY.md) - 健康检查 API 安全配置

### 技术文档
- [Nginx配置](../deployment/nginx/api.dev.supplynexus.store.conf) - 生产环境nginx配置
- [数据库管理脚本](../scripts/db/alembic.sh) - 数据库迁移管理脚本
- [环境配置快速参考](ENVIRONMENT_CONFIG_QUICK_REFERENCE.md) - 环境配置使用指南
- [项目整理总结](PROJECT_CLEANUP_SUMMARY.md) - 项目整理和环境配置统一总结
- [脚本分析计划](SCRIPT_ANALYSIS_AND_CLEANUP.md) - 脚本分析和清理计划

### 安全文档
- [健康检查安全配置](../backend/docs/HEALTH_CHECK_SECURITY.md) - 健康检查 API 安全配置
- [健康检查指南](../backend/docs/HEALTH_CHECKS.md) - 健康检查功能说明

## 🚀 快速导航

### 新用户
1. 阅读 [项目主页](../README.md) 了解项目
2. 按照 [快速开始指南](QUICK_START.md) 设置开发环境
3. 查看 [开发指南](DEVELOPMENT.md) 开始开发

### 开发者
1. 查看 [数据库管理](../README.md#数据库管理) 了解数据库操作
2. 参考 [API 文档](../README.md#-api-文档) 了解接口
3. 查看 [故障排除](../README.md#-故障排除) 解决常见问题

### 运维人员
1. 查看 [部署指南](../README.md#-部署) 了解部署流程
2. 参考 [系统架构](../deployment/ARCHITECTURE.md) 了解架构设计
3. 查看 [环境配置](../deployment/ENVIRONMENTS.md) 配置多环境

## 📞 支持

如果您遇到问题或需要帮助：

- 📧 **邮箱**: support@supplynexus.store
- 📱 **GitHub Issues**: [创建 Issue](https://github.com/supplynexus/fulfillment-service/issues)
- 📚 **文档**: 查看本目录下的详细文档

---

**文档最后更新**: 2024年12月
