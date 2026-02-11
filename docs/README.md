# SupplyNexus Documentation Index

本文件是 `docs/` 的唯一导航入口。  
规则：**未在本文件登记的文档，默认视为临时文档。**

## 1) Start Here

- **[快速开始](QUICK_START.md)** - 本地启动与基础操作
- **[开发指南](DEVELOPMENT.md)** - 开发流程与常用规范
- **[部署指南](DEPLOYMENT.md)** - 部署与环境说明

## 2) Core Ops

- **[数据库管理](DATABASE_MANAGEMENT.md)** - 迁移、备份、恢复
- **[环境配置速查](ENVIRONMENT_CONFIG_QUICK_REFERENCE.md)** - 环境变量说明
- **[Celery 后台任务](CELERY_BACKGROUND_TASKS.md)** - 异步任务与调度

## 3) Integrations

- **[Shopify 订单同步优化](SHOPIFY_ORDER_SYNC_OPTIMIZATION.md)**
- **[Printify MCP stdout issue](integrations/printify/printify-mcp-stdout-issue.md)**

## 4) Engineering Knowledge

- **[Celery 首次质量复盘](engineering/incidents/celery-automation-first-time-quality.md)**

## 5) Anti-Sprawl Rules (必须遵守)

- 每个新增文档必须在本文件登记；否则视为临时文档。
- 文档头部必须注明：用途、最后更新时间、是否仍有效（Active/Deprecated）。
- 相同主题只保留一个主文档，其他文档改为链接引用，不复制粘贴。
- 每月一次文档清理：过期文档移入 `docs/archive/` 或删除。
- 项目运行态文档（agent/rules/state）只放 `.cursor/`，长期知识统一放 `docs/`。

## 6) Folder Convention

- `engineering/`：技术方案、事故复盘、经验沉淀
- `integrations/`：第三方系统（Printify/Shopify 等）
- `runbooks/`：操作手册、故障处理、值守流程（后续扩展）

---

**Last updated**: 2026-02-11
