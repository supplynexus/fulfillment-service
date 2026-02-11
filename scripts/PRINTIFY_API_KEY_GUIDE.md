# Printify API Key 获取指南

## 如何获取 Printify API Key

### 步骤 1: 登录 Printify 账户

1. 访问 https://printify.com/
2. 点击右上角的 "Log in" 按钮
3. 使用您的账户登录：
   - 邮箱: leo.zhang7605@gmail.com
   - 密码: Impeach@2025
4. 登录成功后，您会看到 Dashboard 页面

### 步骤 2: 导航到 API 设置页面

根据 [Printify 官方文档](https://developers.printify.com/#create-a-personal-access-token)，Personal Access Token 的创建位置如下：

#### 详细导航步骤（官方路径）：

**方法 1: 通过 My Profile → Connections（官方推荐）**

根据 Printify 官方文档，正确的路径是：

1. **登录后，进入 "My Profile"（我的资料）**
   - 点击右上角的**用户头像**或**用户名**
   - 在下拉菜单中找到 **"My Profile"**（我的资料）
   - 点击进入个人资料页面

2. **进入 "Connections"（连接）部分**
   - 在 My Profile 页面中，找到 **"Connections"**（连接）选项
   - 点击进入 Connections 页面

3. **生成 Personal Access Token**
   - 在 Connections 页面中，您会看到 **"Personal Access Tokens"** 部分
   - 可以在这里：
     - 生成新的 Personal Access Tokens
     - 设置 Token Access Scopes（访问范围）
     - 查看已创建的 tokens（但不会显示完整 token，出于安全考虑）

**方法 2: 直接访问（如果知道 URL）**

- 尝试直接访问 Connections 页面（URL 可能类似：`https://printify.com/app/profile/connections`）

**方法 2: 通过左侧导航菜单（如果存在）**

1. **登录后，查看左侧导航栏**
   - 查找是否有独立的 "Settings"（设置）选项（不是 "Store settings"）
   - 或者查找 "Account"（账户）选项

2. **进入设置页面**
   - 点击 "Settings" 或 "Account"
   - 在设置页面中查找 "API" 选项

**方法 3: 检查 "Printify Connect" 标签页**

如果在 Store Settings 页面中：
1. 查看标签页列表，找到 **"Printify Connect"** 标签
2. 点击进入该标签页
3. 查看是否有 API 相关的设置选项

**方法 2: 通过右上角用户菜单**

1. **点击右上角的用户头像或菜单图标**
2. **在下拉菜单中找到 "Settings"（设置）**
3. **在设置页面左侧菜单中找到 "API" 选项**

**方法 4: 直接访问 URL（如果知道）**

- 尝试访问 Connections 页面（URL 可能类似：`https://printify.com/app/profile/connections`）
- 如果显示 404 或找不到页面，请使用上述方法 1 通过界面导航

**方法 5: 通过帮助文档查找**

1. 访问 Printify 帮助中心
2. 搜索 "API" 或 "API key"
3. 查看官方文档中的 API 设置位置说明

### 步骤 3: 创建或查看 Personal Access Token

根据 [Printify 官方文档](https://developers.printify.com/#create-a-personal-access-token)：

1. **进入 Connections 页面后，您会看到：**
   - "Personal Access Tokens" 部分
   - 现有的 tokens 列表（如果有）
   - "Generate token" 或类似的按钮

2. **创建新的 Personal Access Token：**
   - 点击 **"Generate token"** 按钮
   - 可以设置 **Token Access Scopes**（访问范围），控制 token 的权限
   - 可以创建多个 tokens，每个 token 可以设置不同的访问范围
   - 点击确认生成

3. **复制 API Token（非常重要！）：**
   - 创建成功后，会显示生成的 Personal Access Token
   - Token 通常是一串长字符串，格式类似：
     ```
     eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c
     ```
   - ⚠️ **立即复制并保存到安全位置**，因为**只显示一次**，关闭页面后就无法再查看
   - 如果忘记或丢失 token，需要删除旧 token 并重新生成

4. **Token 有效期：**
   - Personal Access Tokens 有效期为 **一年**
   - 一年后 token 会过期，需要生成新的 token 替换

5. **查看现有 Token（如果已有）：**
   - 在 Personal Access Tokens 列表中，您可以看到已创建的 tokens
   - 可以查看 token 名称、创建时间、访问范围等
   - **注意**：出于安全考虑，已创建的 token **不会完整显示**，只能看到部分字符或名称

⚠️ **重要提示**：
- API token 只显示一次，请妥善保存
- Token 有效期为**一年**，过期后需要重新生成
- 如果忘记或丢失 token，需要删除旧 token 并重新生成
- Token 具有完整的账户访问权限，请勿泄露
- 可以创建多个 tokens，每个 token 可以设置不同的 Access Scopes（访问范围）

### 步骤 4: 使用 API Token

根据 [Printify 官方文档](https://developers.printify.com/#create-a-personal-access-token)，使用 API Token 时需要注意：

1. **API 请求格式**
   - 所有 API 请求必须包含 `Authorization` header
   - 格式：`Authorization: Bearer YOUR_TOKEN`
   - API 基础 URL：`https://api.printify.com/v1/`

2. **User-Agent Header（必需）**
   - 所有请求必须指定 `User-Agent` header
   - 值可以是客户端类型（如 "NodeJS"、"PHP"）或您的应用程序名称

3. **示例请求**
   ```bash
   curl -X GET https://api.printify.com/v1/shops.json \
     --header "Authorization: Bearer YOUR_TOKEN" \
     --header "User-Agent: YourAppName"
   ```

4. **连接店铺到 API**
   - 生成 token 后，需要将店铺连接到 API
   - 进入 "My Stores" → "Add new store"
   - 选择 "API" 选项并点击 "Connect"
- 建议为不同用途创建不同的 tokens，便于管理

### 步骤 4: 识别绿色店铺

在 Printify 中，店铺可能有不同的标识。以下是详细的识别方法：

#### 方法 1: 通过 "My Products" 页面查看店铺

1. **进入 "My Products" 页面**
   - 在左侧导航栏点击 "My products"（我的商品）
   - 或直接访问: https://printify.com/app/products

2. **查看店铺选择器**
   - 在页面顶部或左侧，您会看到一个店铺选择器
   - 通常显示为下拉菜单或列表，显示所有店铺
   - 店铺名称旁边可能有颜色标识（绿色圆点或其他标识）

3. **识别绿色店铺**
   - 查找名称中包含 "green"、"Green" 或中文 "绿" 的店铺
   - 或者查找有绿色圆点标识的店铺
   - 注意：不是黑色店铺（black store）

#### 方法 2: 通过 "Store settings" 查看店铺列表

1. **进入 Store settings**
   - 点击左侧菜单的 "Store settings"
   - 查看店铺列表

2. **查看店铺信息**
   - 每个店铺会显示：
     - 店铺名称
     - 店铺 ID（可能需要点击查看详情）
     - 连接状态
     - 可能的颜色标识

#### 方法 3: 使用脚本自动列出所有店铺（推荐）

使用我们提供的脚本，可以自动获取所有店铺列表：

```bash
python scripts/get_printify_green_store_products.py \
  --api-key YOUR_API_KEY \
  --list-shops-only
```

脚本会显示：
- 所有店铺的 ID
- 店铺名称
- 连接状态
- 其他相关信息

根据输出结果，您可以：
- 根据店铺名称识别绿色店铺
- 记录绿色店铺的 ID
- 使用 `--shop-id` 参数指定该店铺获取商品

#### 方法 4: 通过店铺 ID 识别

如果您已经知道绿色店铺的 ID，可以直接使用：

```bash
python scripts/get_printify_green_store_products.py \
  --api-key YOUR_API_KEY \
  --shop-id GREEN_STORE_ID \
  --output green_store_products.json
```

## 使用脚本获取商品

### 安装依赖

```bash
cd /Volumes/WDC2T/supplynexus/fulfillment-service
pip install httpx
```

### 方法 1: 自动查找绿色店铺

```bash
python scripts/get_printify_green_store_products.py \
  --api-key YOUR_API_KEY \
  --output green_store_products.json
```

### 方法 2: 指定店铺 ID

```bash
python scripts/get_printify_green_store_products.py \
  --api-key YOUR_API_KEY \
  --shop-id SHOP_ID \
  --output green_store_products.json
```

### 方法 3: 仅列出店铺（用于查找绿色店铺）

```bash
python scripts/get_printify_green_store_products.py \
  --api-key YOUR_API_KEY \
  --list-shops-only
```

## 脚本输出

脚本会：
1. 获取所有店铺列表
2. 自动识别或使用指定的绿色店铺
3. 获取该店铺的所有商品
4. 将商品数据保存为 JSON 文件

输出文件格式：
```json
{
  "shop_id": "店铺ID",
  "total_count": 商品总数,
  "products": [
    {
      "id": "商品ID",
      "title": "商品名称",
      "is_visible": true/false,
      ...
    }
  ]
}
```

## 常见问题

### Q: 如何确认哪个是绿色店铺？
A: 运行 `--list-shops-only` 选项查看所有店铺，根据名称或 ID 确定。

### Q: API key 在哪里？
A: 通常在 Settings -> API 页面，或者直接访问 https://printify.com/app/settings/api

### Q: 脚本报错 "401 Unauthorized"
A: 检查 API key 是否正确，确保没有多余的空格或换行符。

### Q: 如何区分绿色店铺和黑色店铺？
A: 在 Printify 界面中查看店铺列表，绿色店铺可能有特殊的颜色标识或名称。

## 快速参考：获取 API Key 的完整步骤

### 完整操作流程（一步一步）

1. ✅ **登录 Printify**
   - 访问 https://printify.com/
   - 点击 "Log in"
   - 输入邮箱和密码登录

2. ✅ **找到设置入口**
   - 登录后，查看左侧导航栏
   - 找到并点击 **"Store settings"**（店铺设置）

3. ✅ **进入 API 页面**
   - 在 Store settings 页面中
   - 查找并点击 **"API"** 或 **"API Access"** 选项
   - 或者直接访问: https://printify.com/app/settings/api

4. ✅ **创建 API Token**
   - 点击 **"Create Token"** 或 **"Generate Token"** 按钮
   - （可选）输入 Token 名称
   - 点击确认创建

5. ✅ **复制并保存 Token**
   - 立即复制生成的 API token
   - 保存到安全的地方（只显示一次！）

6. ✅ **验证 Token**
   - 使用脚本测试 Token 是否有效：
   ```bash
   python scripts/get_printify_green_store_products.py \
     --api-key YOUR_API_KEY \
     --list-shops-only
   ```

### 常见界面元素位置

| 功能 | 位置 | 说明 |
|------|------|------|
| 登录按钮 | 右上角 | "Log in" 或 "Sign in" |
| 用户菜单 | 右上角 | 头像或用户名下拉菜单 |
| Store settings | 左侧导航栏 | 通常在底部，有齿轮图标 |
| API 设置 | Store settings 页面 | 左侧菜单中的 "API" 选项 |
| 店铺列表 | My products 页面 | 页面顶部或左侧的店铺选择器 |
| 创建 Token 按钮 | API 设置页面 | "Create Token" 或 "Generate Token" |

### 如果找不到 API 设置

根据您提供的截图，API 设置**不在 Store Settings 的标签页中**。请尝试以下方法：

1. **尝试账户级别的设置**
   - 点击右上角的用户头像
   - 查找 "Settings" 或 "Account Settings"
   - API 设置通常在账户级别，而不是店铺级别

2. **直接访问 API URL**
   - 尝试直接访问: https://printify.com/app/settings/api
   - 如果显示 404，说明可能不在这个路径

3. **检查 "Printify Connect" 标签页**
   - 在 Store Settings 页面中，点击 "Printify Connect" 标签
   - 查看是否有 API 相关的设置

4. **检查账户类型**
   - 某些账户类型可能没有 API 访问权限
   - 确认您的账户是否支持 API 访问
   - 可能需要升级到特定计划

5. **查看帮助文档**
   - 访问 Printify 帮助中心
   - 搜索 "API" 或 "API key"
   - 查看官方文档中的 API 设置位置说明

6. **联系支持**
   - 如果仍然找不到，联系 Printify 客服
   - 询问如何启用 API 访问
   - 询问 API 设置的具体位置

## 安全提示

⚠️ **重要安全提醒**：
- 不要将 API key 提交到 Git 仓库
- 不要在公共场合分享 API key
- 如果 API key 泄露，立即在 Printify 中删除并重新生成
- 建议为不同用途创建不同的 tokens，便于管理和撤销
