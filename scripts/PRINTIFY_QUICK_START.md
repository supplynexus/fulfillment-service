# Printify API Key 快速获取指南

## 🚀 5 步快速获取 API Key

根据 [Printify 官方文档](https://developers.printify.com/#create-a-personal-access-token)：

### 步骤 1: 登录
访问 https://printify.com/app/dashboard 并登录

### 步骤 2: 进入 My Profile
- 点击右上角的**用户头像**
- 选择 **"My Profile"**（我的资料）

### 步骤 3: 进入 Connections
在 My Profile 页面中，找到并点击 **"Connections"**（连接）选项

### 步骤 4: 生成 Token
在 Connections 页面中，找到 **"Personal Access Tokens"** 部分
- 点击 **"Generate token"** 按钮
- 设置 Token Access Scopes（访问范围）
- 确认生成

### 步骤 5: 复制保存
⚠️ **立即复制生成的 API token 并保存到安全位置**（只显示一次！）
- Token 有效期为一年
- 如果丢失，需要重新生成

---

## 📍 详细路径（官方文档路径）

根据 [Printify 官方文档](https://developers.printify.com/#create-a-personal-access-token)：

```
登录 → 右上角用户头像 → My Profile → Connections → Generate token
```

**关键步骤**：
1. 点击右上角用户头像
2. 选择 **"My Profile"**（我的资料）
3. 进入 **"Connections"**（连接）部分
4. 在 **"Personal Access Tokens"** 部分生成 token

⚠️ **重要提示**：
- API Token 在 **My Profile → Connections** 中，不在 Store settings 中
- Token 只在生成时显示一次，请立即保存
- Token 有效期为一年

---

## 🔍 识别绿色店铺

### 方法 1: 使用脚本列出所有店铺

```bash
python scripts/get_printify_green_store_products.py \
  --api-key YOUR_API_KEY \
  --list-shops-only
```

### 方法 2: 在 Printify 界面查看

1. 进入 "My products" 页面
2. 查看页面顶部或左侧的店铺选择器
3. 找到有绿色标识或名称包含 "green" 的店铺

---

## 📦 获取绿色店铺商品

### 自动查找绿色店铺

```bash
python scripts/get_printify_green_store_products.py \
  --api-key YOUR_API_KEY \
  --output green_store_products.json
```

### 指定店铺 ID

```bash
python scripts/get_printify_green_store_products.py \
  --api-key YOUR_API_KEY \
  --shop-id SHOP_ID \
  --output green_store_products.json
```

---

## ❓ 常见问题

**Q: 找不到 API 设置？**
- 按照官方路径：右上角用户头像 → My Profile → Connections
- 检查账户是否有 API 访问权限

**Q: 如何确认哪个是绿色店铺？**
- 运行 `--list-shops-only` 查看所有店铺
- 根据店铺名称或 ID 确定

**Q: Token 在哪里显示？**
- 在 Connections 页面的 Personal Access Tokens 部分
- 创建后会立即显示，只显示一次，请立即复制保存

**Q: Token 有效期是多久？**
- Personal Access Token 有效期为**一年**
- 过期后需要重新生成

**Q: 如何使用 API Token？**
- 在请求头中添加：`Authorization: Bearer YOUR_TOKEN`
- 必须包含 `User-Agent` header
- API 基础 URL：`https://api.printify.com/v1/`

---

## ⚠️ 安全提醒

- API token 具有完整账户访问权限
- 不要提交到 Git 仓库
- 不要分享给他人
- 泄露后立即删除并重新生成
