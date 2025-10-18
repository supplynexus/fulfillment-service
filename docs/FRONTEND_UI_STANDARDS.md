# 前端UI开发规范

## 1. 列表页面标准

### 1.1 必需功能
所有列表页面（List Pages）必须包含以下标准功能：

#### 1.1.1 刷新按钮
- **位置**: 操作按钮区域，位于主要操作按钮之前
- **样式**: `variant='outlined'`，使用 `RefreshIcon`
- **功能**: 重新加载列表数据
- **实现方式**: 使用 `refreshKey` 状态强制重新渲染列表组件

```typescript
// 状态定义
const [refreshKey, setRefreshKey] = useState(0);

// 刷新处理函数
const handleRefresh = () => {
  setRefreshKey(prev => prev + 1);
};

// 按钮实现
<Button
  variant='outlined'
  startIcon={<RefreshIcon />}
  onClick={handleRefresh}
  disabled={loading}
>
  刷新
</Button>

// 列表组件使用key强制重新渲染
<ComponentList key={refreshKey} />
```

#### 1.1.2 创建按钮
- **位置**: 操作按钮区域，位于刷新按钮之后
- **样式**: `variant='contained'`，使用 `AddIcon`
- **功能**: 打开创建表单

#### 1.1.3 加载状态
- **刷新按钮**: 在加载时禁用
- **创建按钮**: 在加载时禁用
- **列表组件**: 显示加载指示器

### 1.2 标准布局结构

```typescript
export default function ListPage() {
  const [refreshKey, setRefreshKey] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleRefresh = () => {
    setRefreshKey(prev => prev + 1);
  };

  return (
    <ProtectedRoute>
      <DashboardLayout>
        <Box sx={{ p: 3 }}>
          {/* 页面标题 */}
          <Typography variant='h4' component='h1'>
            页面标题
          </Typography>

          {/* 错误提示 */}
          {error && (
            <Alert severity='error' onClose={() => setError(null)}>
              {error}
            </Alert>
          )}

          {/* 操作按钮区域 */}
          <Box sx={{ mb: 3, display: 'flex', gap: 2 }}>
            <Button
              variant='outlined'
              startIcon={<RefreshIcon />}
              onClick={handleRefresh}
              disabled={loading}
            >
              刷新
            </Button>
            <Button
              variant='contained'
              startIcon={<AddIcon />}
              onClick={handleCreate}
              disabled={loading}
            >
              创建
            </Button>
          </Box>

          {/* 列表内容 */}
          <Paper sx={{ p: 2, height: 'calc(100vh - 200px)', overflow: 'auto' }}>
            <ComponentList key={refreshKey} />
          </Paper>
        </Box>
      </DashboardLayout>
    </ProtectedRoute>
  );
}
```

## 2. 表单页面标准

### 2.1 必需功能
所有表单页面（Form Pages）必须包含以下标准功能：

#### 2.1.1 保存按钮
- **样式**: `variant='contained'`，使用 `SaveIcon`
- **功能**: 提交表单数据
- **状态**: 加载时显示加载指示器

#### 2.1.2 取消按钮
- **样式**: `variant='outlined'`
- **功能**: 关闭表单，不保存数据

#### 2.1.3 重置按钮（可选）
- **样式**: `variant='text'`
- **功能**: 重置表单到初始状态

### 2.2 标准布局结构

```typescript
<DialogActions>
  <Button
    variant='outlined'
    onClick={handleCancel}
    disabled={loading}
  >
    取消
  </Button>
  <Button
    variant='contained'
    onClick={handleSubmit}
    disabled={loading}
    startIcon={loading ? <CircularProgress size={20} /> : <SaveIcon />}
  >
    {loading ? '保存中...' : '保存'}
  </Button>
</DialogActions>
```

## 3. 数据展示标准

### 3.1 列表组件
- **容器**: 使用 `Paper` 组件
- **高度**: `calc(100vh - 200px)`
- **滚动**: `overflow: 'auto'`
- **刷新**: 使用 `key` 属性强制重新渲染

### 3.2 加载状态
- **全局加载**: 使用全屏遮罩层
- **局部加载**: 在组件内部显示加载指示器
- **按钮加载**: 使用 `CircularProgress` 图标

### 3.3 错误处理
- **错误提示**: 使用 `Alert` 组件
- **可关闭**: 提供关闭按钮
- **位置**: 页面顶部，操作按钮之前

## 4. 图标使用标准

### 4.1 标准图标映射
```typescript
import {
  Add as AddIcon,
  Refresh as RefreshIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  Save as SaveIcon,
  Cancel as CancelIcon,
  Search as SearchIcon,
  Filter as FilterIcon,
  Download as DownloadIcon,
  Upload as UploadIcon,
  Settings as SettingsIcon,
  MoreVert as MoreVertIcon,
} from '@mui/icons-material';
```

### 4.2 图标使用规范
- **刷新**: `RefreshIcon`
- **创建**: `AddIcon`
- **编辑**: `EditIcon`
- **删除**: `DeleteIcon`
- **保存**: `SaveIcon`
- **取消**: `CancelIcon`
- **搜索**: `SearchIcon`
- **过滤**: `FilterIcon`
- **设置**: `SettingsIcon`
- **更多操作**: `MoreVertIcon`

## 5. 响应式设计标准

### 5.1 断点设置
```typescript
const theme = createTheme({
  breakpoints: {
    values: {
      xs: 0,
      sm: 600,
      md: 900,
      lg: 1200,
      xl: 1536,
    },
  },
});
```

### 5.2 响应式布局
- **移动端**: 单列布局，按钮堆叠
- **平板端**: 双列布局，按钮并排
- **桌面端**: 多列布局，完整功能

## 6. 无障碍性标准

### 6.1 键盘导航
- **Tab键**: 按逻辑顺序导航
- **Enter键**: 激活按钮和链接
- **Escape键**: 关闭弹窗和菜单

### 6.2 屏幕阅读器支持
- **语义化标签**: 使用正确的HTML标签
- **ARIA属性**: 提供必要的无障碍信息
- **焦点管理**: 确保焦点可见和可预测

## 7. 性能优化标准

### 7.1 组件优化
- **React.memo**: 纯展示组件使用memo
- **useCallback**: 事件处理函数使用callback
- **useMemo**: 昂贵计算使用memo

### 7.2 数据加载
- **懒加载**: 大列表使用虚拟滚动
- **分页**: 大量数据使用分页
- **缓存**: 使用React Query缓存数据

## 8. 测试标准

### 8.1 单元测试
- **组件渲染**: 测试组件正确渲染
- **用户交互**: 测试点击、输入等交互
- **状态变化**: 测试状态更新逻辑

### 8.2 集成测试
- **API调用**: 测试与后端的交互
- **数据流**: 测试完整的数据流
- **错误处理**: 测试错误场景

## 9. 代码质量标准

### 9.1 TypeScript
- **类型定义**: 所有props和state都有类型
- **接口定义**: 复杂对象定义接口
- **泛型使用**: 适当使用泛型提高复用性

### 9.2 代码组织
- **组件拆分**: 单一职责原则
- **Hook提取**: 复杂逻辑提取为自定义Hook
- **常量提取**: 魔法数字和字符串提取为常量

## 10. 检查清单

### 10.1 新页面开发检查
- [ ] 页面标题正确显示
- [ ] 刷新按钮存在且功能正常
- [ ] 创建按钮存在且功能正常
- [ ] 加载状态正确处理
- [ ] 错误提示正确显示
- [ ] 响应式布局适配
- [ ] 键盘导航支持
- [ ] 无障碍性支持

### 10.2 代码审查检查
- [ ] TypeScript类型完整
- [ ] 组件职责单一
- [ ] 性能优化到位
- [ ] 测试覆盖充分
- [ ] 文档更新及时

---

**注意**: 本规范是强制性的，所有新开发的页面都必须遵循这些标准。现有页面在修改时也应逐步向这些标准靠拢。
