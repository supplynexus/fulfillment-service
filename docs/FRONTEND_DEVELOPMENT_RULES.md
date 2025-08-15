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
- **MUI Material Next.js 7.3.0** - Next.js 集成

### 状态管理和数据获取
- **Zustand 4.4.7** - 轻量级状态管理
- **TanStack React Query 5.12.2** - 服务端状态管理
- **SWR 2.2.4** - 数据获取库（备选）

### 表单和验证
- **React Hook Form 7.48.2** - 高性能表单库
- **Zod** - 表单验证（推荐）

### 样式和主题
- **Emotion 11.14.0** - CSS-in-JS 解决方案
- **MUI Theme** - 统一的设计系统

### 认证和 API 集成
- **RSA 签名认证** - 用于服务间通信
- **JWT 令牌** - 用于前端用户认证
- **Axios 1.6.2** - HTTP 客户端

### 工具库
- **Day.js 1.11.10** - 日期处理
- **React Hot Toast 2.4.1** - 通知组件
- **Recharts 2.8.0** - 图表库

## 2. 开发哲学和原则

### 核心原则
- **编写清洁、可维护、可扩展的代码**
- **遵循 SOLID 原则**
- **优先使用函数式和声明式编程模式**
- **强调类型安全和静态分析**
- **实践组件驱动开发**

### 方法论
1. **系统化思维**: 以分析严谨的方式处理问题
2. **思维树**: 评估多种可能的解决方案及其后果
3. **迭代优化**: 在最终确定代码之前考虑改进和优化

## 3. 代码风格和结构规范

### 代码风格（基于项目配置）
- **使用 2 空格缩进** (tabWidth: 2)
- **使用单引号表示字符串** (singleQuote: true)
- **使用分号** (semi: true) - 符合项目 Prettier 配置
- **限制行长度为 80 个字符** (printWidth: 80)
- **使用尾随逗号** (trailingComma: "es5")
- **避免箭头函数括号** (arrowParens: "avoid")
- **使用空格而非制表符** (useTabs: false)

### 命名约定

#### 通用规则
- **PascalCase 用于**: 组件、类型定义、接口
- **kebab-case 用于**: 目录名称、文件名称
- **camelCase 用于**: 变量、函数、方法、Hooks、属性、Props
- **UPPERCASE 用于**: 环境变量、常量、全局配置

#### 特定命名模式
- **事件处理函数前缀 'handle'**: `handleClick`, `handleSubmit`
- **布尔变量前缀动词**: `isLoading`, `hasError`, `canSubmit`
- **自定义 hooks 前缀 'use'**: `useAuth`, `useForm`
- **使用完整单词而非缩写**，除了：`err`, `req`, `res`, `props`, `ref`

### 项目结构
```
frontend/
├── src/
│   ├── app/                    # Next.js App Router 页面
│   │   ├── (auth)/            # 认证相关页面组
│   │   ├── (dashboard)/       # 仪表板页面组
│   │   ├── admin/             # 管理员页面
│   │   ├── customers/         # 客户管理页面
│   │   ├── orders/            # 订单管理页面
│   │   ├── settings/          # 设置页面
│   │   ├── layout.tsx         # 根布局
│   │   └── page.tsx           # 首页
│   ├── components/            # 可复用组件
│   ├── hooks/                 # 自定义 React Hooks
│   ├── lib/                   # 工具库和配置
│   │   ├── api.ts            # API 客户端
│   │   ├── auth-context.tsx  # 认证上下文
│   │   ├── query-client.tsx  # React Query 配置
│   │   ├── signature.ts      # RSA 签名工具
│   │   ├── signature-client.ts # 签名客户端
│   │   └── theme.ts          # MUI 主题配置
│   ├── types/                # TypeScript 类型定义
│   └── utils/                # 工具函数
├── public/                   # 静态资源
├── keys/                     # RSA 密钥对（开发环境）
├── scripts/                  # 构建和部署脚本
└── tests/                    # 测试文件
```

## 4. 组件开发规范

### 组件设计原则
1. **单一职责** - 每个组件只负责一个功能
2. **可复用性** - 组件应该易于在不同场景中复用
3. **可测试性** - 组件应该易于单元测试
4. **可访问性** - 遵循 WCAG 2.1 标准

### 组件架构
- **使用带有 TypeScript 接口的函数组件**
- **使用 function 关键字定义组件**
- **将可重用逻辑提取到自定义 hooks**
- **实现适当的组件组合**
- **战略性地使用 React.memo() 进行性能优化**
- **在 useEffect hooks 中实现适当的清理**

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

## 5. React 最佳实践

### 性能优化
- **使用 useCallback 记忆化回调函数**
- **实现 useMemo 进行昂贵计算**
- **避免在 JSX 中内联函数定义**
- **使用动态导入实现代码分割**
- **在列表中实现适当的 key props（避免使用索引作为 key）**

### 错误处理
- **使用错误边界优雅地捕获和处理 React 组件树中的错误**
- **将捕获的错误记录到外部服务（如 Sentry）进行跟踪和调试**
- **设计用户友好的后备 UI，在发生错误时显示，让用户了解情况而不破坏应用**

### 生命周期管理
- **在 useEffect 中实现适当的清理函数**
- **避免内存泄漏**
- **正确处理异步操作**

## 6. Next.js 最佳实践

### 核心概念
- **利用 App Router 进行路由**
- **实现适当的元数据管理**
- **使用适当的缓存策略**
- **实现适当的错误边界**

### 服务器组件
- **默认使用服务器组件**
- **使用 URL 查询参数进行数据获取和服务器状态管理**
- **仅在必要时使用 'use client' 指令**:
  - 事件监听器
  - 浏览器 API
  - 状态管理
  - 仅客户端库

### 组件和功能
- **使用 Next.js 内置组件**:
  - Image 组件用于优化图像
  - Link 组件用于客户端导航
  - Script 组件用于外部脚本
  - Head 组件用于元数据
- **实现适当的加载状态**
- **使用适当的数据获取方法**

## 7. TypeScript 实现规范

### 配置要求
- **启用严格模式**
- **为组件 props、状态和 Redux 状态结构定义清晰的接口**
- **使用类型守卫安全地处理潜在的 undefined 或 null 值**
- **在需要类型灵活性的地方对函数、操作和切片应用泛型**
- **利用 TypeScript 实用类型（Partial、Pick、Omit）创建更清洁和可重用的代码**
- **在定义对象结构时优先使用 interface 而不是 type，特别是在扩展时**
- **使用映射类型动态创建现有类型的变体**

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

## 8. 状态管理规范

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

## 9. API 集成规范

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

## 10. 样式和主题规范

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

## 11. 错误处理和验证规范

### 错误处理原则
- **优先处理错误和边缘情况**
- **在函数开始时处理错误和边缘情况**
- **使用早期返回处理错误条件，避免深度嵌套的 if 语句**
- **将快乐路径放在函数的最后以提高可读性**
- **避免不必要的 else 语句；使用 if-return 模式**
- **使用守卫子句早期处理前置条件和无效状态**
- **实现适当的错误日志记录和用户友好的错误消息**
- **考虑使用自定义错误类型或错误工厂进行一致的错误处理**

### 表单验证
- **使用 Zod 进行模式验证**
- **实现适当的错误消息**
- **使用 React Hook Form 进行表单管理**

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

## 12. 性能优化规范

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

### Web Vitals 优化
- **LCP (Largest Contentful Paint)**: 优化最大内容绘制
- **CLS (Cumulative Layout Shift)**: 减少累积布局偏移
- **FID (First Input Delay)**: 优化首次输入延迟

## 13. 测试规范

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

### 测试最佳实践
- **编写彻底的单元测试**来验证单个函数和组件
- **使用 Jest 和 React Testing Library**可靠高效地测试 React 组件
- **遵循 Arrange-Act-Assert 模式**确保测试的清晰性和一致性
- **模拟外部依赖和 API 调用**以隔离单元测试

## 14. 可访问性 (a11y) 规范

### 核心要求
- **使用语义化 HTML 进行有意义的结构**
- **在需要的地方应用准确的 ARIA 属性**
- **确保完整的键盘导航支持**
- **有效管理焦点顺序和可见性**
- **保持可访问的颜色对比度**
- **遵循逻辑的标题层次结构**
- **使所有交互元素都可访问**
- **提供清晰和可访问的错误反馈**

### 实现示例
```typescript
// 可访问的按钮组件
<Button
  aria-label="删除用户"
  onClick={handleDelete}
  onKeyDown={(e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      handleDelete();
    }
  }}
  tabIndex={0}
>
  删除
</Button>
```

## 15. 安全规范

### 认证和授权
- **JWT 令牌**: 安全存储和传输
- **RSA 签名**: 用于 API 请求认证
- **权限检查**: 组件级别的权限控制

### 数据验证
- **输入验证**: 客户端和服务器端双重验证
- **XSS 防护**: 使用 React 的自动转义
- **CSRF 防护**: 使用适当的令牌
- **实现输入清理**以防止 XSS 攻击
- **使用 DOMPurify 清理 HTML 内容**
- **使用适当的认证方法**

### 环境变量
```bash
# .env.local
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_APP_NAME=SupplyNexus Fulfillment Service
FRONTEND_PRIVATE_KEY=-----BEGIN PRIVATE KEY-----
FRONTEND_KEY_ID=frontend-server-1
NEXT_PUBLIC_TENANT_HASHID=PoRpOk2e
```

## 16. 国际化 (i18n) 规范

### 实现要求
- **使用 next-i18next 进行翻译**
- **实现适当的语言环境检测**
- **使用适当的数字和日期格式**
- **实现适当的 RTL 支持**
- **使用适当的货币格式**

## 17. 文档规范

### JSDoc 使用
- **使用 JSDoc 进行文档记录**
- **记录所有公共函数、类、方法和接口**
- **在适当时添加示例**
- **使用完整的句子和适当的标点符号**
- **保持描述清晰简洁**
- **使用适当的 markdown 格式**

### 文档示例
```typescript
/**
 * 用户卡片组件
 * 
 * 显示用户基本信息的卡片组件，支持编辑和删除操作
 * 
 * @param user - 用户对象，包含 id、name、email 等属性
 * @param onEdit - 编辑用户的回调函数
 * @param onDelete - 删除用户的回调函数
 * 
 * @example
 * ```tsx
 * <UserCard 
 *   user={user} 
 *   onEdit={handleEdit} 
 *   onDelete={handleDelete} 
 * />
 * ```
 */
export function UserCard({ user, onEdit, onDelete }: UserCardProps) {
  // 组件实现
}
```

## 18. 部署规范

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

## 19. 代码审查清单

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

### 可访问性检查
- [ ] 语义化 HTML 结构
- [ ] ARIA 属性正确
- [ ] 键盘导航支持
- [ ] 颜色对比度符合标准

## 20. 高级集成规范

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

## 21. 开发流程

### 标准流程
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
