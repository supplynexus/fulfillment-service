# Frontend 开发规则 (精简版)

## 1. 技术栈
- **Next.js 15.4.6** + **React 19.1.1** + **TypeScript 5.9.2**
- **MUI 7.3.1** + **MUI Material Next.js 7.3.0**
- **Zustand 4.4.7** + **TanStack React Query 5.12.2**
- **React Hook Form 7.48.2** + **Zod**
- **Axios 1.6.2** + **RSA 签名认证**

## 2. 代码风格
- **2 空格缩进**，**单引号**，**使用分号**
- **80 字符行宽**，**尾随逗号**
- **PascalCase**: 组件、类型、接口
- **camelCase**: 变量、函数、Hooks
- **kebab-case**: 目录、文件名
- **事件处理函数前缀 'handle'**: `handleClick`
- **布尔变量前缀动词**: `isLoading`, `hasError`
- **自定义 hooks 前缀 'use'**: `useAuth`

## 3. 项目结构
```
frontend/src/
├── app/                    # Next.js App Router
│   ├── (auth)/            # 认证页面组
│   ├── (dashboard)/       # 仪表板页面组
│   ├── admin/             # 管理员页面
│   ├── customers/         # 客户管理
│   ├── orders/            # 订单管理
│   ├── settings/          # 设置页面
│   ├── layout.tsx         # 根布局
│   └── page.tsx           # 首页
├── components/            # 可复用组件
├── hooks/                 # 自定义 Hooks
├── lib/                   # 工具库配置
│   ├── api.ts            # API 客户端
│   ├── auth-context.tsx  # 认证上下文
│   ├── query-client.tsx  # React Query 配置
│   ├── signature.ts      # RSA 签名工具
│   └── theme.ts          # MUI 主题
├── types/                # TypeScript 类型
└── utils/                # 工具函数
```

## 4. 组件开发
```typescript
// 组件结构
interface UserCardProps {
  user: User;
  onEdit?: (user: User) => void;
}

export function UserCard({ user, onEdit }: UserCardProps) {
  const [isLoading, setIsLoading] = useState(false);

  const handleEdit = useCallback(() => {
    onEdit?.(user);
  }, [user, onEdit]);

  return (
    <Box>
      <Typography variant="h6">{user.name}</Typography>
    </Box>
  );
}
```

## 5. 状态管理
```typescript
// Zustand Store
export const useUserStore = create<UserState>()(
  devtools((set) => ({
    user: null,
    isLoading: false,
    setUser: (user) => set({ user }),
    setLoading: (isLoading) => set({ isLoading }),
  }))
);

// React Query
export function useUsers() {
  return useQuery({
    queryKey: ['users'],
    queryFn: userService.getUsers,
    staleTime: 5 * 60 * 1000,
  });
}
```

## 6. API 集成
```typescript
// API 客户端
const apiClient = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL,
  timeout: 10000,
});

// 请求拦截器 - RSA 签名
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
```

## 7. 错误处理
- **早期返回**处理错误条件
- **守卫子句**处理前置条件
- **错误边界**捕获组件错误
- **用户友好的错误消息**

```typescript
// 错误处理示例
function processUser(user: User | null) {
  if (!user) return null;
  if (!user.email) throw new Error('用户邮箱不能为空');
  
  // 正常处理逻辑
  return user;
}
```

## 8. 性能优化
- **useCallback** 记忆化回调函数
- **useMemo** 进行昂贵计算
- **React.memo** 纯展示组件
- **动态导入** 代码分割
- **避免内联函数** 在 JSX 中

## 9. 可访问性
- **语义化 HTML** 结构
- **ARIA 属性** 准确应用
- **键盘导航** 完整支持
- **颜色对比度** 符合标准

## 10. 安全规范
- **输入验证** 客户端和服务器端
- **XSS 防护** React 自动转义
- **JWT 令牌** 安全存储传输
- **RSA 签名** API 请求认证

## 11. 测试规范
```typescript
// 测试示例
describe('UserCard', () => {
  it('renders user information correctly', () => {
    render(<UserCard user={mockUser} />);
    expect(screen.getByText('John Doe')).toBeInTheDocument();
  });
});
```

## 12. 代码审查清单
- [ ] 功能按需求实现
- [ ] 边界情况已处理
- [ ] 错误处理完善
- [ ] 代码结构清晰
- [ ] 命名规范统一
- [ ] 类型定义完整
- [ ] 无不必要的重渲染
- [ ] 输入验证完善
- [ ] 语义化 HTML 结构
- [ ] 键盘导航支持

## 13. 开发流程
1. **需求分析** - 明确功能需求
2. **技术选型** - 选择合适技术栈
3. **架构设计** - 设计组件结构
4. **开发实现** - 按规范开发
5. **测试验证** - 单元和集成测试
6. **代码审查** - 使用审查清单
7. **部署上线** - 按环境配置

---

**注意**: 遵循这些规则确保代码质量、安全性和可维护性。
