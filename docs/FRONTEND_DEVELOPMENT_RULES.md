# Frontend 开发规则

## 1. 技术栈规范

### 核心框架
- **Next.js 15.4.6** - React 全栈框架，使用 App Router
- **React 19.1.1** - 用户界面库
- **TypeScript 5.9.2** - 类型安全的 JavaScript 超集

### UI 组件库
- **Material-UI (MUI) 7.3.1** - React UI 组件库
- **MUI X Data Grid 8.10.0** - 高级数据表格组件
- **MUI X Date Pickers 8.10.0** - 日期选择器组件

### 状态管理和数据获取
- **Zustand 4.5.7** - 轻量级状态管理
- **TanStack React Query 5.85.3** - 服务端状态管理
- **SWR 2.3.6** - 数据获取库（备选）

### 表单和验证
- **React Hook Form 7.62.0** - 高性能表单库
- **Yup** - 表单验证（如需要）

### 样式和主题
- **Emotion 11.14.0** - CSS-in-JS 解决方案
- **MUI Theme** - 统一的设计系统

### 认证和 API 集成
- **RSA 签名认证** - 用于服务间通信
- **JWT 令牌** - 用于前端用户认证
- **Axios** - HTTP 客户端

## 2. 项目结构规范

### 目录结构
```
frontend/
├── src/
│   ├── app/                    # Next.js App Router 页面
│   │   ├── (auth)/            # 认证相关页面组
│   │   ├── (dashboard)/       # 仪表板页面组
│   │   ├── layout.tsx         # 根布局
│   │   └── page.tsx           # 首页
│   ├── components/            # 可复用组件
│   │   ├── ui/               # 基础 UI 组件
│   │   ├── forms/            # 表单组件
│   │   └── layout/           # 布局组件
│   ├── hooks/                # 自定义 React Hooks
│   ├── lib/                  # 工具库和配置
│   ├── services/             # API 服务层
│   ├── stores/               # Zustand 状态管理
│   ├── types/                # TypeScript 类型定义
│   └── utils/                # 工具函数
├── public/                   # 静态资源
├── keys/                     # RSA 密钥对（开发环境）
└── scripts/                  # 构建和部署脚本
```

### 文件命名规范
- **组件文件**: PascalCase (如 `UserProfile.tsx`)
- **页面文件**: kebab-case (如 `user-profile.tsx`)
- **工具文件**: camelCase (如 `formatDate.ts`)
- **类型文件**: camelCase (如 `userTypes.ts`)
- **常量文件**: UPPER_SNAKE_CASE (如 `API_ENDPOINTS.ts`)

## 3. 组件开发规范

### 组件设计原则
1. **单一职责** - 每个组件只负责一个功能
2. **可复用性** - 组件应该易于在不同场景中复用
3. **可测试性** - 组件应该易于单元测试
4. **可访问性** - 遵循 WCAG 2.1 标准

### 组件结构
```typescript
// 1. 导入依赖
import React from 'react';
import { Box, Typography } from '@mui/material';

// 2. 类型定义
interface UserCardProps {
  user: User;
  onEdit?: (user: User) => void;
  onDelete?: (userId: string) => void;
}

// 3. 组件定义
export function UserCard({ user, onEdit, onDelete }: UserCardProps) {
  // 4. 状态和副作用
  const [isLoading, setIsLoading] = useState(false);

  // 5. 事件处理函数
  const handleEdit = useCallback(() => {
    onEdit?.(user);
  }, [user, onEdit]);

  // 6. 渲染函数
  return (
    <Box>
      <Typography variant="h6">{user.name}</Typography>
      {/* 组件内容 */}
    </Box>
  );
}
```

### 组件分类
- **展示组件 (Presentational)**: 只负责渲染，不包含业务逻辑
- **容器组件 (Container)**: 包含业务逻辑和状态管理
- **布局组件 (Layout)**: 负责页面结构和导航
- **页面组件 (Page)**: 路由对应的页面组件

## 4. 状态管理规范

### Zustand 使用规范
```typescript
// stores/userStore.ts
import { create } from 'zustand';
import { devtools } from 'zustand/middleware';

interface UserState {
  user: User | null;
  isLoading: boolean;
  error: string | null;
  setUser: (user: User | null) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
}

export const useUserStore = create<UserState>()(
  devtools(
    (set) => ({
      user: null,
      isLoading: false,
      error: null,
      setUser: (user) => set({ user }),
      setLoading: (isLoading) => set({ isLoading }),
      setError: (error) => set({ error }),
    }),
    { name: 'user-store' }
  )
);
```

### React Query 使用规范
```typescript
// hooks/useUsers.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { userService } from '@/services/userService';

export function useUsers() {
  return useQuery({
    queryKey: ['users'],
    queryFn: userService.getUsers,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

export function useCreateUser() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: userService.createUser,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
    },
  });
}
```

## 5. API 集成规范

### 服务层设计
```typescript
// services/apiClient.ts
import axios from 'axios';
import { createSignatureGenerator } from '@/lib/signature';

const apiClient = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL,
  timeout: 10000,
});

// 请求拦截器 - 添加认证头
apiClient.interceptors.request.use((config) => {
  const signatureGenerator = createSignatureGenerator();
  const headers = signatureGenerator.generateHeaders({
    method: config.method?.toUpperCase() || 'GET',
    path: config.url || '/',
    body: config.data ? JSON.stringify(config.data) : '',
  });
  
  config.headers = { ...config.headers, ...headers };
  return config;
});

// 响应拦截器 - 统一错误处理
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    // 统一错误处理逻辑
    return Promise.reject(error);
  }
);

export default apiClient;
```

### API 服务模块
```typescript
// services/userService.ts
import apiClient from './apiClient';
import type { User, CreateUserRequest } from '@/types/user';

export const userService = {
  getUsers: async (): Promise<User[]> => {
    const response = await apiClient.get('/api/v1/users');
    return response.data;
  },
  
  createUser: async (data: CreateUserRequest): Promise<User> => {
    const response = await apiClient.post('/api/v1/users', data);
    return response.data;
  },
  
  updateUser: async (id: string, data: Partial<User>): Promise<User> => {
    const response = await apiClient.put(`/api/v1/users/${id}`, data);
    return response.data;
  },
  
  deleteUser: async (id: string): Promise<void> => {
    await apiClient.delete(`/api/v1/users/${id}`);
  },
};
```

## 6. 样式和主题规范

### MUI 主题配置
```typescript
// lib/theme.ts
import { createTheme } from '@mui/material/styles';

export const theme = createTheme({
  palette: {
    primary: {
      main: '#1976d2',
      light: '#42a5f5',
      dark: '#1565c0',
    },
    secondary: {
      main: '#dc004e',
    },
  },
  typography: {
    fontFamily: '"Inter", "Roboto", "Helvetica", "Arial", sans-serif',
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          textTransform: 'none',
          borderRadius: 8,
        },
      },
    },
  },
});
```

### 样式编写规范
1. **优先使用 MUI 组件** - 避免自定义 CSS
2. **使用 sx 属性** - 内联样式使用 sx 属性
3. **主题变量** - 使用主题中定义的颜色和间距
4. **响应式设计** - 使用 MUI 的断点系统

```typescript
// 好的样式写法
<Box
  sx={{
    display: 'flex',
    flexDirection: { xs: 'column', md: 'row' },
    gap: 2,
    p: 3,
    bgcolor: 'background.paper',
    borderRadius: 2,
    boxShadow: 1,
  }}
>
```

## 7. 类型安全规范

### TypeScript 配置
- **严格模式**: 启用所有严格检查选项
- **类型定义**: 为所有 API 响应和组件 props 定义类型
- **泛型使用**: 合理使用泛型提高代码复用性

### 类型定义示例
```typescript
// types/user.ts
export interface User {
  id: string;
  email: string;
  name: string;
  role: UserRole;
  tenant_id: string;
  created_at: string;
  updated_at: string;
}

export type UserRole = 'admin' | 'user' | 'viewer';

export interface CreateUserRequest {
  email: string;
  name: string;
  role: UserRole;
  password: string;
}

export interface UpdateUserRequest {
  email?: string;
  name?: string;
  role?: UserRole;
}
```

## 8. 性能优化规范

### 代码分割
- **页面级分割**: 使用 Next.js 的自动代码分割
- **组件级分割**: 使用 `React.lazy()` 和 `Suspense`
- **库分割**: 将大型第三方库进行分割

### 渲染优化
- **React.memo**: 用于纯展示组件
- **useMemo**: 用于昂贵的计算
- **useCallback**: 用于事件处理函数
- **虚拟化**: 大数据列表使用虚拟化

### 缓存策略
- **React Query**: 合理设置 staleTime 和 cacheTime
- **SWR**: 使用适当的缓存策略
- **浏览器缓存**: 静态资源使用适当的缓存头

## 9. 测试规范

### 测试类型
1. **单元测试**: 测试独立的函数和组件
2. **集成测试**: 测试组件间的交互
3. **端到端测试**: 测试完整的用户流程

### 测试工具
- **Jest**: 测试框架
- **React Testing Library**: 组件测试
- **MSW**: API 模拟

### 测试示例
```typescript
// __tests__/components/UserCard.test.tsx
import { render, screen, fireEvent } from '@testing-library/react';
import { UserCard } from '@/components/UserCard';

describe('UserCard', () => {
  const mockUser = {
    id: '1',
    name: 'John Doe',
    email: 'john@example.com',
  };

  it('renders user information correctly', () => {
    render(<UserCard user={mockUser} />);
    
    expect(screen.getByText('John Doe')).toBeInTheDocument();
    expect(screen.getByText('john@example.com')).toBeInTheDocument();
  });

  it('calls onEdit when edit button is clicked', () => {
    const onEdit = jest.fn();
    render(<UserCard user={mockUser} onEdit={onEdit} />);
    
    fireEvent.click(screen.getByRole('button', { name: /edit/i }));
    expect(onEdit).toHaveBeenCalledWith(mockUser);
  });
});
```

## 10. 错误处理规范

### 错误边界
```typescript
// components/ErrorBoundary.tsx
import React from 'react';
import { Box, Typography, Button } from '@mui/material';

interface ErrorBoundaryState {
  hasError: boolean;
  error?: Error;
}

export class ErrorBoundary extends React.Component<
  React.PropsWithChildren<{}>,
  ErrorBoundaryState
> {
  constructor(props: React.PropsWithChildren<{}>) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('Error caught by boundary:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <Box textAlign="center" p={4}>
          <Typography variant="h5" gutterBottom>
            出现错误
          </Typography>
          <Button onClick={() => window.location.reload()}>
            刷新页面
          </Button>
        </Box>
      );
    }

    return this.props.children;
  }
}
```

### 全局错误处理
```typescript
// lib/errorHandler.ts
export function handleError(error: unknown): string {
  if (error instanceof Error) {
    return error.message;
  }
  
  if (typeof error === 'string') {
    return error;
  }
  
  return '发生未知错误';
}
```

## 11. 安全规范

### 认证和授权
- **JWT 令牌**: 安全存储和传输
- **RSA 签名**: 用于 API 请求认证
- **权限检查**: 组件级别的权限控制

### 数据验证
- **输入验证**: 客户端和服务器端双重验证
- **XSS 防护**: 使用 React 的自动转义
- **CSRF 防护**: 使用适当的令牌

### 环境变量
```bash
# .env.local
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_APP_NAME=SupplyNexus Fulfillment Service
FRONTEND_PRIVATE_KEY=-----BEGIN PRIVATE KEY-----
FRONTEND_KEY_ID=frontend-server-1
NEXT_PUBLIC_TENANT_HASHID=PoRpOk2e
```

## 12. 部署规范

### 构建优化
- **代码压缩**: 启用生产环境代码压缩
- **图片优化**: 使用 Next.js 的图片优化
- **Bundle 分析**: 定期分析打包大小

### 环境配置
- **开发环境**: 本地开发配置
- **测试环境**: 集成测试配置
- **生产环境**: 生产部署配置

### 监控和日志
- **错误监控**: 集成错误监控服务
- **性能监控**: 监控页面加载性能
- **用户行为**: 分析用户交互数据

## 13. 代码审查清单

### 功能检查
- [ ] 功能按需求实现
- [ ] 边界情况已处理
- [ ] 错误处理完善
- [ ] 用户体验良好

### 代码质量
- [ ] 代码结构清晰
- [ ] 命名规范统一
- [ ] 注释充分
- [ ] 类型定义完整

### 性能检查
- [ ] 无不必要的重渲染
- [ ] 合理使用缓存
- [ ] 代码分割适当
- [ ] 加载性能良好

### 安全检查
- [ ] 输入验证完善
- [ ] 敏感信息保护
- [ ] 权限控制正确
- [ ] 无安全漏洞

## 14. 高级集成规范

### tRPC 集成（可选）

如果项目需要端到端类型安全的 API，可以考虑集成 tRPC：

#### 项目结构
```
src/
├── server/
│   ├── routers/
│   │   ├── _app.ts          # 主路由
│   │   ├── user.ts          # 用户相关路由
│   │   └── order.ts         # 订单相关路由
│   ├── context.ts           # 上下文创建
│   └── trpc.ts              # tRPC 配置
└── utils/
    └── trpc.ts              # 客户端配置
```

#### 服务器端设置
```typescript
// server/trpc.ts
import { initTRPC } from '@trpc/server';
import { z } from 'zod';

const t = initTRPC.create({
  transformer: superjson,
});

export const router = t.router;
export const publicProcedure = t.procedure;

// 认证中间件
const isAuthed = t.middleware(({ next, ctx }) => {
  if (!ctx.user) {
    throw new TRPCError({ code: 'UNAUTHORIZED' });
  }
  return next({ ctx: { user: ctx.user } });
});

export const protectedProcedure = t.procedure.use(isAuthed);
```

#### 客户端设置
```typescript
// utils/trpc.ts
import { createTRPCNext } from '@trpc/next';
import { httpBatchLink } from '@trpc/client';
import type { AppRouter } from '../server/routers/_app';

export const trpc = createTRPCNext<AppRouter>({
  config() {
    return {
      links: [
        httpBatchLink({
          url: `${getBaseUrl()}/api/trpc`,
        }),
      ],
    };
  },
  ssr: false,
});
```

#### 使用示例
```typescript
// hooks/useUsers.ts
import { trpc } from '@/utils/trpc';

export function useUsers() {
  return trpc.user.list.useQuery();
}

export function useCreateUser() {
  const utils = trpc.useUtils();
  
  return trpc.user.create.useMutation({
    onSuccess: () => {
      utils.user.list.invalidate();
    },
  });
}
```

### Supabase Auth 集成（可选）

如果需要更强大的认证功能，可以考虑集成 Supabase Auth：

#### 环境变量
```bash
NEXT_PUBLIC_SUPABASE_URL=your_supabase_url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key
```

#### 客户端配置
```typescript
// lib/supabase/client.ts
import { createBrowserClient } from '@supabase/ssr';

export function createClient() {
  return createBrowserClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
  );
}
```

#### 服务器端配置
```typescript
// lib/supabase/server.ts
import { createServerClient } from '@supabase/ssr';
import { cookies } from 'next/headers';

export async function createClient() {
  const cookieStore = await cookies();

  return createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return cookieStore.getAll();
        },
        setAll(cookiesToSet) {
          try {
            cookiesToSet.forEach(({ name, value, options }) =>
              cookieStore.set(name, value, options)
            );
          } catch {
            // 忽略服务器组件的 setAll 调用
          }
        },
      },
    }
  );
}
```

#### 中间件配置
```typescript
// middleware.ts
import { createServerClient } from '@supabase/ssr';
import { NextResponse, type NextRequest } from 'next/server';

export async function middleware(request: NextRequest) {
  let supabaseResponse = NextResponse.next({ request });

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return request.cookies.getAll();
        },
        setAll(cookiesToSet) {
          cookiesToSet.forEach(({ name, value, options }) => 
            request.cookies.set(name, value)
          );
          supabaseResponse = NextResponse.next({ request });
          cookiesToSet.forEach(({ name, value, options }) =>
            supabaseResponse.cookies.set(name, value, options)
          );
        },
      },
    }
  );

  const { data: { user } } = await supabase.auth.getUser();

  if (!user && !request.nextUrl.pathname.startsWith('/login')) {
    const url = request.nextUrl.clone();
    url.pathname = '/login';
    return NextResponse.redirect(url);
  }

  return supabaseResponse;
}
```

### Trigger.dev 集成（可选）

如果需要后台任务处理，可以考虑集成 Trigger.dev：

#### 安装和配置
```bash
npm install @trigger.dev/sdk@latest
npx trigger.dev@latest init
```

#### 任务定义
```typescript
// trigger/tasks/email.ts
import { task } from "@trigger.dev/sdk/v3";

export const sendWelcomeEmail = task({
  id: "send-welcome-email",
  run: async (payload: { email: string; name: string }) => {
    // 发送欢迎邮件的逻辑
    console.log(`Sending welcome email to ${payload.email}`);
  },
});

export const processOrder = task({
  id: "process-order",
  retry: {
    maxAttempts: 3,
    factor: 2,
  },
  run: async (payload: { orderId: string }) => {
    // 处理订单的逻辑
    console.log(`Processing order ${payload.orderId}`);
  },
});
```

#### 从后端触发任务
```typescript
// services/taskService.ts
import { tasks } from "@trigger.dev/sdk/v3";

export async function triggerWelcomeEmail(email: string, name: string) {
  return await tasks.trigger("send-welcome-email", { email, name });
}

export async function triggerOrderProcessing(orderId: string) {
  return await tasks.trigger("process-order", { orderId });
}
```

#### 实时监控
```typescript
// hooks/useTaskStatus.ts
import { useRun } from "@trigger.dev/react-hooks";

export function useTaskStatus(taskId: string) {
  return useRun(taskId);
}
```

## 15. 最佳实践总结

### 开发流程
1. **需求分析** - 明确功能需求和用户故事
2. **技术选型** - 根据需求选择合适的技术栈
3. **架构设计** - 设计组件结构和数据流
4. **开发实现** - 按照规范进行开发
5. **测试验证** - 单元测试和集成测试
6. **代码审查** - 使用审查清单进行检查
7. **部署上线** - 按环境配置进行部署

### 持续改进
- **定期回顾** - 定期回顾开发过程和代码质量
- **技术更新** - 关注技术栈的更新和最佳实践
- **性能优化** - 持续监控和优化应用性能
- **安全加固** - 定期进行安全审计和加固

### 团队协作
- **代码规范** - 统一代码风格和命名规范
- **文档维护** - 及时更新技术文档和 API 文档
- **知识分享** - 定期进行技术分享和培训
- **工具使用** - 合理使用开发工具和自动化流程

---

**注意**: 这些规则应该根据项目发展和团队反馈持续更新和改进。高级集成规范（tRPC、Supabase Auth、Trigger.dev）是可选的，应根据项目实际需求决定是否采用。
