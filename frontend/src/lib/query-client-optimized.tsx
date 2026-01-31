/**
 * 优化的React Query客户端配置
 * 
 * 提供缓存策略、预加载、错误重试等优化功能
 */

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ReactQueryDevtools } from '@tanstack/react-query-devtools'
import { ReactNode } from 'react'

// 创建优化的QueryClient配置
export const createOptimizedQueryClient = () => {
  return new QueryClient({
    defaultOptions: {
      queries: {
        // 缓存时间：5分钟
        staleTime: 5 * 60 * 1000,
        // 垃圾回收时间：10分钟
        gcTime: 10 * 60 * 1000,
        // 重试配置
        retry: (failureCount, error: any) => {
          // 对于4xx错误不重试
          if (error?.response?.status >= 400 && error?.response?.status < 500) {
            return false
          }
          // 最多重试3次
          return failureCount < 3
        },
        // 重试延迟：指数退避
        retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
        // 网络错误时重试
        refetchOnWindowFocus: false,
        // 网络恢复时重新获取
        refetchOnReconnect: true,
        // 后台重新获取
        refetchOnMount: true,
      },
      mutations: {
        // 失败重试
        retry: (failureCount, error: any) => {
          if (error?.response?.status >= 400 && error?.response?.status < 500) {
            return false
          }
          return failureCount < 2
        },
        // 重试延迟
        retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 10000),
      },
    },
  })
}

// 预定义查询键
export const queryKeys = {
  // 产品分类
  productCategories: {
    all: ['product-categories'] as const,
    lists: () => [...queryKeys.productCategories.all, 'list'] as const,
    list: (filters: Record<string, any>) => 
      [...queryKeys.productCategories.lists(), { filters }] as const,
    details: () => [...queryKeys.productCategories.all, 'detail'] as const,
    detail: (id: string) => [...queryKeys.productCategories.details(), id] as const,
  },
  
  // 产品变体（SKU）
  productVariants: {
    all: ['product-variants'] as const,
    lists: () => [...queryKeys.productVariants.all, 'list'] as const,
    list: (filters: Record<string, any>) => 
      [...queryKeys.productVariants.lists(), { filters }] as const,
    details: () => [...queryKeys.productVariants.all, 'detail'] as const,
    detail: (id: string) => [...queryKeys.productVariants.details(), id] as const,
  },
  
  // 维度模板
  dimensionTemplates: {
    all: ['dimension-templates'] as const,
    lists: () => [...queryKeys.dimensionTemplates.all, 'list'] as const,
    list: (filters: Record<string, any>) => 
      [...queryKeys.dimensionTemplates.lists(), { filters }] as const,
    details: () => [...queryKeys.dimensionTemplates.all, 'detail'] as const,
    detail: (id: string) => [...queryKeys.dimensionTemplates.details(), id] as const,
    values: (templateId: string) => 
      [...queryKeys.dimensionTemplates.detail(templateId), 'values'] as const,
  },
  
  // 外部系统
  externalSystems: {
    all: ['external-systems'] as const,
    lists: () => [...queryKeys.externalSystems.all, 'list'] as const,
    list: (systemType: string) => 
      [...queryKeys.externalSystems.lists(), { systemType }] as const,
    details: () => [...queryKeys.externalSystems.all, 'detail'] as const,
    detail: (id: string) => [...queryKeys.externalSystems.details(), id] as const,
  },
} as const

// 缓存配置
export const cacheConfig = {
  // 产品分类缓存
  productCategories: {
    staleTime: 5 * 60 * 1000, // 5分钟
    gcTime: 10 * 60 * 1000, // 10分钟
  },
  
  // 产品变体缓存
  productVariants: {
    staleTime: 2 * 60 * 1000, // 2分钟（更频繁变化）
    gcTime: 5 * 60 * 1000, // 5分钟
  },
  
  // 维度模板缓存
  dimensionTemplates: {
    staleTime: 10 * 60 * 1000, // 10分钟（相对稳定）
    gcTime: 30 * 60 * 1000, // 30分钟
  },
  
  // 外部系统缓存
  externalSystems: {
    staleTime: 1 * 60 * 1000, // 1分钟（外部数据）
    gcTime: 5 * 60 * 1000, // 5分钟
  },
} as const

// 预加载配置
export const preloadConfig = {
  // 关键数据的预加载
  critical: [
    'product-categories',
    'dimension-templates',
  ],
  
  // 用户操作后预加载的数据
  onUserAction: {
    'product-categories': ['product-variants'],
    'product-variants': ['external-systems'],
  },
} as const

// 错误处理配置
export const errorConfig = {
  // 网络错误重试
  networkError: {
    retry: 3,
    retryDelay: (attemptIndex: number) => Math.min(1000 * 2 ** attemptIndex, 30000),
  },
  
  // 服务器错误重试
  serverError: {
    retry: 2,
    retryDelay: (attemptIndex: number) => Math.min(2000 * 2 ** attemptIndex, 20000),
  },
  
  // 客户端错误不重试
  clientError: {
    retry: 0,
  },
} as const

// 优化的QueryClientProvider组件
interface OptimizedQueryClientProviderProps {
  children: ReactNode
}

export function OptimizedQueryClientProvider({ children }: OptimizedQueryClientProviderProps) {
  const queryClient = createOptimizedQueryClient()
  
  return (
    <QueryClientProvider client={queryClient}>
      {children}
      {process.env.NODE_ENV === 'development' && (
        <ReactQueryDevtools 
          initialIsOpen={false}
          position="bottom-right"
        />
      )}
    </QueryClientProvider>
  )
}

// 预加载工具函数
export const preloadUtils = {
  // 预加载产品分类
  preloadProductCategories: async (queryClient: QueryClient) => {
    await queryClient.prefetchQuery({
      queryKey: queryKeys.productCategories.lists(),
      queryFn: async () => {
        const response = await fetch('/api/product-categories')
        if (!response.ok) throw new Error('Failed to fetch product categories')
        return response.json()
      },
      staleTime: cacheConfig.productCategories.staleTime,
    })
  },
  
  // 预加载维度模板
  preloadDimensionTemplates: async (queryClient: QueryClient) => {
    await queryClient.prefetchQuery({
      queryKey: queryKeys.dimensionTemplates.lists(),
      queryFn: async () => {
        const response = await fetch('/api/dimension-templates')
        if (!response.ok) throw new Error('Failed to fetch dimension templates')
        return response.json()
      },
      staleTime: cacheConfig.dimensionTemplates.staleTime,
    })
  },
  
  // 预加载关键数据
  preloadCriticalData: async (queryClient: QueryClient) => {
    await Promise.all([
      preloadUtils.preloadProductCategories(queryClient),
      preloadUtils.preloadDimensionTemplates(queryClient),
    ])
  },
}

// 缓存清理工具
export const cacheUtils = {
  // 清理产品分类缓存
  invalidateProductCategories: (queryClient: QueryClient) => {
    queryClient.invalidateQueries({ queryKey: queryKeys.productCategories.all })
  },
  
  // 清理产品变体缓存
  invalidateProductVariants: (queryClient: QueryClient) => {
    queryClient.invalidateQueries({ queryKey: queryKeys.productVariants.all })
  },
  
  // 清理维度模板缓存
  invalidateDimensionTemplates: (queryClient: QueryClient) => {
    queryClient.invalidateQueries({ queryKey: queryKeys.dimensionTemplates.all })
  },
  
  // 清理所有缓存
  invalidateAll: (queryClient: QueryClient) => {
    queryClient.invalidateQueries()
  },
}
