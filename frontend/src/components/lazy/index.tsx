/**
 * 懒加载组件优化
 * 
 * 提供组件懒加载、代码分割和预加载功能
 */

import { lazy, Suspense, ComponentType, ReactNode } from 'react'
import { Box, CircularProgress, Typography } from '@mui/material'

// 加载中组件
function LoadingFallback({ message = '加载中...' }: { message?: string }) {
  return (
    <Box
      sx={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: 200,
        gap: 2,
      }}
    >
      <CircularProgress size={40} />
      <Typography variant="body2" color="text.secondary">
        {message}
      </Typography>
    </Box>
  )
}

// 错误边界组件
function ErrorFallback({ error, resetError }: { error: Error; resetError: () => void }) {
  return (
    <Box
      sx={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: 200,
        gap: 2,
        p: 3,
      }}
    >
      <Typography variant="h6" color="error">
        组件加载失败
      </Typography>
      <Typography variant="body2" color="text.secondary">
        {error.message}
      </Typography>
      <button onClick={resetError}>重试</button>
    </Box>
  )
}

// 懒加载高阶组件
export function withLazyLoading<T extends object>(
  importFunc: () => Promise<{ default: ComponentType<T> }>,
  fallbackMessage?: string
) {
  const LazyComponent = lazy(importFunc)
  
  return function LazyWrapper(props: T) {
    return (
      <Suspense fallback={<LoadingFallback message={fallbackMessage} />}>
        <LazyComponent {...props} />
      </Suspense>
    )
  }
}

// 预加载工具
export const preloadComponent = (importFunc: () => Promise<any>) => {
  // 在空闲时间预加载组件
  if ('requestIdleCallback' in window) {
    requestIdleCallback(() => {
      importFunc()
    })
  } else {
    setTimeout(() => {
      importFunc()
    }, 100)
  }
}

// 懒加载的页面组件
export const LazyProductCategoriesPage = withLazyLoading(
  () => import('@/app/product-categories/page'),
  '加载产品分类页面...'
)

export const LazySkusPage = withLazyLoading(
  () => import('@/app/skus/page'),
  '加载SKU管理页面...'
)

export const LazyDimensionTemplatesPage = withLazyLoading(
  () => import('@/app/dimension-templates/page'),
  '加载维度模板页面...'
)

export const LazyExternalSystemsPage = withLazyLoading(
  () => import('@/app/external-systems/page'),
  '加载外部系统页面...'
)

export const LazySkuBatchCreatePage = withLazyLoading(
  () => import('@/app/skus/batch-create/page'),
  '加载SKU批量创建页面...'
)

// 懒加载的对话框组件
export const LazyCategoryForm = withLazyLoading(
  () => import('@/components/product-categories/CategoryForm'),
  '加载分类表单...'
)

export const LazySkuForm = withLazyLoading(
  () => import('@/components/skus/SkuForm'),
  '加载SKU表单...'
)

export const LazyDimensionTemplateForm = withLazyLoading(
  () => import('@/components/dimension-templates/DimensionTemplateForm'),
  '加载维度模板表单...'
)

// 懒加载的复杂组件
export const LazyCategoryTree = withLazyLoading(
  () => import('@/components/product-categories/CategoryTree'),
  '加载分类树...'
)

export const LazySkuList = withLazyLoading(
  () => import('@/components/skus/SkuList'),
  '加载SKU列表...'
)

export const LazyDimensionTemplateList = withLazyLoading(
  () => import('@/components/dimension-templates/DimensionTemplateList'),
  '加载维度模板列表...'
)

// 预加载关键组件
export const preloadCriticalComponents = () => {
  // 预加载主要页面
  preloadComponent(() => import('@/app/product-categories/page'))
  preloadComponent(() => import('@/app/skus/page'))
  
  // 预加载常用组件
  preloadComponent(() => import('@/components/product-categories/CategoryForm'))
  preloadComponent(() => import('@/components/skus/SkuForm'))
}

// 路由级别的代码分割
export const routeComponents = {
  '/product-categories': LazyProductCategoriesPage,
  '/skus': LazySkusPage,
  '/skus/batch-create': LazySkuBatchCreatePage,
  '/dimension-templates': LazyDimensionTemplatesPage,
  '/external-systems': LazyExternalSystemsPage,
} as const

// 组件级别的代码分割
export const componentComponents = {
  CategoryForm: LazyCategoryForm,
  SkuForm: LazySkuForm,
  DimensionTemplateForm: LazyDimensionTemplateForm,
  CategoryTree: LazyCategoryTree,
  SkuList: LazySkuList,
  DimensionTemplateList: LazyDimensionTemplateList,
} as const
