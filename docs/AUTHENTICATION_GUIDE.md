# 认证机制规范文档

## 概述

本文档定义了SupplyNexus系统中前后端认证机制的完整规范，包括实现方式、调试方法和常见问题解决方案。

## 认证架构

### 认证流程
```
前端页面 → 前端API路由 → 后端API
    ↓           ↓          ↓
  JWT验证    JWT验证    签名验证
```

### 认证层次
1. **前端页面认证**: 使用`ProtectedRoute`组件
2. **前端API路由认证**: 使用`jwtUtilsServer.verifyToken()`
3. **后端API认证**: 使用`verify_jwt_auth`依赖

## 前端认证实现

### 1. 页面级认证

所有受保护的页面必须使用`ProtectedRoute`组件：

```typescript
import { ProtectedRoute } from '@/components/auth/ProtectedRoute';
import { DashboardLayout } from '@/components/layout/DashboardLayout';

export default function MyPage() {
  return (
    <ProtectedRoute>
      <DashboardLayout>
        {/* 页面内容 */}
      </DashboardLayout>
    </ProtectedRoute>
  );
}
```

### 2. API调用认证

#### 使用frontendApi（推荐）
```typescript
import { frontendApi } from '@/lib/api';

// GET请求
const data = await frontendApi.get('/api/my-endpoint');

// POST请求
const result = await frontendApi.post('/api/my-endpoint', requestData);

// PUT请求
const updated = await frontendApi.put('/api/my-endpoint', updateData);

// DELETE请求
await frontendApi.delete('/api/my-endpoint');
```

#### 使用fetch（不推荐，仅用于特殊情况）
```typescript
import { tokenManager } from '@/lib/auth';

const accessToken = await tokenManager.getValidAccessToken();
const response = await fetch('/api/my-endpoint', {
  method: 'GET',
  headers: {
    'Authorization': `Bearer ${accessToken}`,
    'Content-Type': 'application/json',
  },
});
```

### 3. 前端API路由认证

所有前端API路由必须实现以下认证模式：

```typescript
import { NextRequest, NextResponse } from 'next/server';
import { createLogger } from '@/lib/logger';
import { jwtUtilsServer } from '@/lib/jwt-utils-server';
import { backendApi } from '@/lib/api';

const logger = createLogger('api.my-endpoint');

export async function GET(request: NextRequest) {
  try {
    logger.requestStart(request.method, request.url);
    
    // 1. 验证前端JWT token
    const authHeader = request.headers.get('authorization');
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      logger.error('Missing or invalid authorization header');
      return NextResponse.json(
        { detail: 'Missing or invalid authorization header' },
        { status: 401 }
      );
    }

    const frontendToken = authHeader.substring(7);
    let decodedToken;
    try {
      decodedToken = jwtUtilsServer.verifyToken(frontendToken);
    } catch (error) {
      logger.error('Invalid frontend token', { error: String(error) });
      return NextResponse.json({ detail: 'Invalid token' }, { status: 401 });
    }

    const { tenant_name: tenantName, sub: userId } = decodedToken;
    logger.info('Frontend JWT verified successfully', {
      userId,
      tenantName,
    });

    // 2. 调用后端API
    const response = await backendApi.get('/api/v1/my-endpoint');
    
    logger.requestComplete(request.method, request.url, 200, Date.now() - startTime);
    return NextResponse.json(response.data);
    
  } catch (error: any) {
    logger.error('API request failed', { error: String(error) });
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: error.response?.status || 500 }
    );
  }
}
```

## 后端认证实现

### 1. API端点认证

所有后端API端点必须使用JWT认证：

```python
from app.core.jwt_auth_dependency import verify_jwt_auth

@router.get("/my-endpoint")
async def my_endpoint(
    db: AsyncSession = Depends(get_async_db),
    auth: tuple = Depends(verify_jwt_auth)
) -> Any:
    tenant, user = auth
    # 业务逻辑
    return {"message": "success"}
```

### 2. 认证依赖

- **JWT认证**: `verify_jwt_auth` - 用于前端API调用
- **签名认证**: `verify_tenant_auth` - 用于外部系统调用

## 调试和日志规范

### 1. 前端调试

#### 浏览器Console日志
```typescript
// 在组件中添加调试日志
console.log('🔍 认证状态检查:', {
  hasUser: !!user,
  isLoading,
  tokenExists: !!localStorage.getItem('access_token')
});
```

#### 使用frontendLogger
```typescript
import { frontendLogger } from '@/lib/frontend-logger';

frontendLogger.info('🚀 开始API调用', { endpoint: '/api/my-endpoint' });
frontendLogger.error('❌ API调用失败', { error: error.message });
```

#### 发送日志到后端
```typescript
import { frontendLogger } from '@/lib/frontend-logger';

// 重要错误会自动发送到后端 /api/log 端点
frontendLogger.error('认证失败', { 
  error: error.message,
  userId: user?.id,
  timestamp: new Date().toISOString()
});
```

### 2. 后端调试

#### 添加详细日志
```python
from app.core.logging import get_logger

logger = get_logger(__name__)

@router.get("/my-endpoint")
async def my_endpoint(
    db: AsyncSession = Depends(get_async_db),
    auth: tuple = Depends(verify_jwt_auth)
) -> Any:
    tenant, user = auth
    
    logger.info("🔍 开始处理请求", 
                tenant_id=tenant.id, 
                user_id=user.id,
                endpoint="/my-endpoint")
    
    try:
        # 业务逻辑
        result = await some_business_logic()
        logger.info("✅ 请求处理成功", result_count=len(result))
        return result
    except Exception as e:
        logger.error("❌ 请求处理失败", 
                    error=str(e), 
                    tenant_id=tenant.id)
        raise HTTPException(status_code=500, detail=str(e))
```

### 3. 认证问题调试流程

#### 步骤1: 检查前端认证状态
```typescript
// 在浏览器Console中运行
console.log('认证状态:', {
  hasToken: !!localStorage.getItem('access_token'),
  tokenValue: localStorage.getItem('access_token'),
  hasRefreshToken: !!localStorage.getItem('refresh_token'),
  user: JSON.parse(localStorage.getItem('user') || 'null')
});
```

#### 步骤2: 检查API调用日志
```typescript
// 在API调用前后添加日志
console.log('🔍 API调用开始:', { url, method, headers });
const response = await frontendApi.get('/api/my-endpoint');
console.log('✅ API调用成功:', { status: response.status, data: response.data });
```

#### 步骤3: 检查后端日志
```bash
# 查看后端日志
tail -f backend/logs-dev/app.log | grep -E "(认证|JWT|token|auth)"
```

#### 步骤4: 检查网络请求
1. 打开浏览器开发者工具
2. 查看Network标签页
3. 检查请求头中的Authorization字段
4. 检查响应状态码和错误信息

## 常见问题和解决方案

### 1. 401 Unauthorized错误

#### 问题原因
- JWT token过期或无效
- 认证头格式错误
- 签名验证失败

#### 解决方案
```typescript
// 检查token有效性
const token = await tokenManager.getValidAccessToken();
if (!token) {
  // 尝试刷新token
  await tokenManager.refreshTokens();
}
```

### 2. 404 Not Found错误

#### 问题原因
- 路由路径错误
- 认证失败导致重定向
- 页面保护机制问题

#### 解决方案
```typescript
// 检查路由配置
// 检查ProtectedRoute组件
// 检查认证状态
```

### 3. 422 Unprocessable Entity错误

#### 问题原因
- 请求参数格式错误
- 认证头缺失
- 后端验证失败

#### 解决方案
```typescript
// 检查请求参数
// 检查认证头
// 查看后端日志
```

## 认证最佳实践

### 1. 前端最佳实践

#### 使用统一的API客户端
```typescript
// ✅ 推荐
const data = await frontendApi.get('/api/my-endpoint');

// ❌ 不推荐
const response = await fetch('/api/my-endpoint', {
  headers: { 'Authorization': `Bearer ${token}` }
});
```

#### 错误处理
```typescript
try {
  const data = await frontendApi.get('/api/my-endpoint');
  return data;
} catch (error) {
  console.error('API调用失败:', error);
  // 错误会自动处理（重定向到登录页等）
  throw error;
}
```

### 2. 后端最佳实践

#### 统一的认证依赖
```python
# ✅ 推荐
@router.get("/my-endpoint")
async def my_endpoint(
    db: AsyncSession = Depends(get_async_db),
    auth: tuple = Depends(verify_jwt_auth)
) -> Any:
    tenant, user = auth
    # 业务逻辑
```

#### 详细的日志记录
```python
# ✅ 推荐
logger.info("🔍 开始处理请求", 
            tenant_id=tenant.id, 
            user_id=user.id,
            request_data=request_data)

try:
    result = await business_logic()
    logger.info("✅ 请求处理成功", result_count=len(result))
    return result
except Exception as e:
    logger.error("❌ 请求处理失败", 
                error=str(e), 
                tenant_id=tenant.id)
    raise HTTPException(status_code=500, detail=str(e))
```

## 认证测试清单

### 新增API端点时检查
- [ ] 前端API路由是否正确实现认证
- [ ] 后端API端点是否使用正确的认证依赖
- [ ] 错误处理是否完善
- [ ] 日志记录是否详细
- [ ] 测试认证失败场景
- [ ] 测试认证成功场景

### 新增页面时检查
- [ ] 页面是否使用ProtectedRoute
- [ ] API调用是否使用frontendApi
- [ ] 错误处理是否完善
- [ ] 加载状态是否正确
- [ ] 认证失败时是否正确重定向

## 总结

认证机制是系统的核心安全组件，必须严格按照规范实现：

1. **前端**: 使用`frontendApi`进行API调用，使用`ProtectedRoute`保护页面
2. **后端**: 使用`verify_jwt_auth`进行认证验证
3. **调试**: 使用详细的日志记录，通过浏览器Console和后端日志进行问题定位
4. **测试**: 每次新增功能都要测试认证场景

遵循这些规范可以避免大部分认证相关的问题，提高开发效率和系统稳定性。
