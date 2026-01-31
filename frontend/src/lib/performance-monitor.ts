/**
 * 性能监控工具
 * 
 * 提供前端性能监控、优化建议和性能指标收集
 */

import { getCLS, getFID, getFCP, getLCP, getTTFB } from 'web-vitals'

// 性能指标接口
interface PerformanceMetrics {
  // Core Web Vitals
  cls: number | null
  fid: number | null
  fcp: number | null
  lcp: number | null
  ttfb: number | null
  
  // 自定义指标
  pageLoadTime: number
  domContentLoaded: number
  firstPaint: number
  firstContentfulPaint: number
  
  // 资源加载
  resourceCount: number
  resourceSize: number
  
  // 用户交互
  clickCount: number
  scrollDepth: number
  
  // 错误统计
  errorCount: number
  errorTypes: Record<string, number>
}

// 性能监控器类
class PerformanceMonitor {
  private metrics: Partial<PerformanceMetrics> = {}
  private observers: PerformanceObserver[] = []
  private startTime: number = 0
  private clickCount: number = 0
  private errorCount: number = 0
  private errorTypes: Record<string, number> = {}
  
  constructor() {
    this.startTime = performance.now()
    this.initializeMonitoring()
  }
  
  private initializeMonitoring() {
    // 监控Core Web Vitals
    this.monitorCoreWebVitals()
    
    // 监控资源加载
    this.monitorResourceLoading()
    
    // 监控用户交互
    this.monitorUserInteractions()
    
    // 监控错误
    this.monitorErrors()
    
    // 监控页面可见性
    this.monitorPageVisibility()
  }
  
  private monitorCoreWebVitals() {
    // 累积布局偏移 (CLS)
    getCLS((metric) => {
      this.metrics.cls = metric.value
      this.reportMetric('CLS', metric.value)
    })
    
    // 首次输入延迟 (FID)
    getFID((metric) => {
      this.metrics.fid = metric.value
      this.reportMetric('FID', metric.value)
    })
    
    // 首次内容绘制 (FCP)
    getFCP((metric) => {
      this.metrics.fcp = metric.value
      this.reportMetric('FCP', metric.value)
    })
    
    // 最大内容绘制 (LCP)
    getLCP((metric) => {
      this.metrics.lcp = metric.value
      this.reportMetric('LCP', metric.value)
    })
    
    // 首字节时间 (TTFB)
    getTTFB((metric) => {
      this.metrics.ttfb = metric.value
      this.reportMetric('TTFB', metric.value)
    })
  }
  
  private monitorResourceLoading() {
    const observer = new PerformanceObserver((list) => {
      const entries = list.getEntries()
      let resourceCount = 0
      let resourceSize = 0
      
      entries.forEach((entry) => {
        if (entry.entryType === 'resource') {
          resourceCount++
          resourceSize += (entry as PerformanceResourceTiming).transferSize || 0
        }
      })
      
      this.metrics.resourceCount = resourceCount
      this.metrics.resourceSize = resourceSize
    })
    
    observer.observe({ entryTypes: ['resource'] })
    this.observers.push(observer)
  }
  
  private monitorUserInteractions() {
    // 监控点击事件
    document.addEventListener('click', () => {
      this.clickCount++
      this.metrics.clickCount = this.clickCount
    })
    
    // 监控滚动深度
    let maxScrollDepth = 0
    window.addEventListener('scroll', () => {
      const scrollDepth = Math.round(
        (window.scrollY / (document.body.scrollHeight - window.innerHeight)) * 100
      )
      maxScrollDepth = Math.max(maxScrollDepth, scrollDepth)
      this.metrics.scrollDepth = maxScrollDepth
    })
  }
  
  private monitorErrors() {
    // 监控JavaScript错误
    window.addEventListener('error', (event) => {
      this.errorCount++
      const errorType = event.error?.name || 'Unknown'
      this.errorTypes[errorType] = (this.errorTypes[errorType] || 0) + 1
      this.metrics.errorCount = this.errorCount
      this.metrics.errorTypes = this.errorTypes
      
      this.reportError('JavaScript Error', {
        message: event.message,
        filename: event.filename,
        lineno: event.lineno,
        colno: event.colno,
        error: event.error?.stack
      })
    })
    
    // 监控Promise拒绝
    window.addEventListener('unhandledrejection', (event) => {
      this.errorCount++
      const errorType = 'Unhandled Promise Rejection'
      this.errorTypes[errorType] = (this.errorTypes[errorType] || 0) + 1
      this.metrics.errorCount = this.errorCount
      this.metrics.errorTypes = this.errorTypes
      
      this.reportError('Promise Rejection', {
        reason: event.reason,
        promise: event.promise
      })
    })
  }
  
  private monitorPageVisibility() {
    document.addEventListener('visibilitychange', () => {
      if (document.visibilityState === 'hidden') {
        // 页面隐藏时发送性能数据
        this.sendPerformanceData()
      }
    })
    
    // 页面卸载时发送数据
    window.addEventListener('beforeunload', () => {
      this.sendPerformanceData()
    })
  }
  
  private reportMetric(name: string, value: number) {
    console.log(`Performance Metric - ${name}: ${value}ms`)
    
    // 发送到分析服务
    if (typeof gtag !== 'undefined') {
      gtag('event', 'performance_metric', {
        metric_name: name,
        metric_value: value
      })
    }
  }
  
  private reportError(type: string, details: any) {
    console.error(`Performance Error - ${type}:`, details)
    
    // 发送到错误监控服务
    if (typeof gtag !== 'undefined') {
      gtag('event', 'exception', {
        description: type,
        fatal: false,
        custom_map: details
      })
    }
  }
  
  private sendPerformanceData() {
    const performanceData = {
      ...this.metrics,
      timestamp: Date.now(),
      url: window.location.href,
      userAgent: navigator.userAgent,
      viewport: {
        width: window.innerWidth,
        height: window.innerHeight
      }
    }
    
    // 发送到后端API
    fetch('/api/performance', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(performanceData)
    }).catch(error => {
      console.error('Failed to send performance data:', error)
    })
  }
  
  // 手动记录自定义指标
  recordCustomMetric(name: string, value: number, unit: string = 'ms') {
    console.log(`Custom Metric - ${name}: ${value}${unit}`)
    
    if (typeof gtag !== 'undefined') {
      gtag('event', 'custom_metric', {
        metric_name: name,
        metric_value: value,
        metric_unit: unit
      })
    }
  }
  
  // 记录页面加载时间
  recordPageLoadTime() {
    const loadTime = performance.now() - this.startTime
    this.metrics.pageLoadTime = loadTime
    this.recordCustomMetric('Page Load Time', loadTime)
  }
  
  // 记录DOM内容加载时间
  recordDOMContentLoaded() {
    const domContentLoaded = performance.timing.domContentLoadedEventEnd - performance.timing.navigationStart
    this.metrics.domContentLoaded = domContentLoaded
    this.recordCustomMetric('DOM Content Loaded', domContentLoaded)
  }
  
  // 记录首次绘制时间
  recordFirstPaint() {
    const paintEntries = performance.getEntriesByType('paint')
    const firstPaint = paintEntries.find(entry => entry.name === 'first-paint')
    if (firstPaint) {
      this.metrics.firstPaint = firstPaint.startTime
      this.recordCustomMetric('First Paint', firstPaint.startTime)
    }
  }
  
  // 记录首次内容绘制时间
  recordFirstContentfulPaint() {
    const paintEntries = performance.getEntriesByType('paint')
    const firstContentfulPaint = paintEntries.find(entry => entry.name === 'first-contentful-paint')
    if (firstContentfulPaint) {
      this.metrics.firstContentfulPaint = firstContentfulPaint.startTime
      this.recordCustomMetric('First Contentful Paint', firstContentfulPaint.startTime)
    }
  }
  
  // 获取当前性能指标
  getMetrics(): Partial<PerformanceMetrics> {
    return { ...this.metrics }
  }
  
  // 清理监控器
  cleanup() {
    this.observers.forEach(observer => observer.disconnect())
    this.observers = []
  }
}

// 性能优化建议
export const performanceOptimizations = {
  // 检查图片优化
  checkImageOptimization: () => {
    const images = document.querySelectorAll('img')
    const unoptimizedImages = Array.from(images).filter(img => {
      const src = img.getAttribute('src') || ''
      return !src.includes('webp') && !src.includes('avif')
    })
    
    if (unoptimizedImages.length > 0) {
      console.warn(`发现 ${unoptimizedImages.length} 个未优化的图片`)
    }
  },
  
  // 检查资源压缩
  checkResourceCompression: () => {
    const resources = performance.getEntriesByType('resource')
    const uncompressedResources = resources.filter(resource => {
      const size = (resource as PerformanceResourceTiming).transferSize
      const decodedSize = (resource as PerformanceResourceTiming).decodedBodySize
      return size && decodedSize && size === decodedSize
    })
    
    if (uncompressedResources.length > 0) {
      console.warn(`发现 ${uncompressedResources.length} 个未压缩的资源`)
    }
  },
  
  // 检查缓存策略
  checkCacheStrategy: () => {
    const resources = performance.getEntriesByType('resource')
    const cacheableResources = resources.filter(resource => {
      const name = resource.name
      return name.includes('.js') || name.includes('.css') || name.includes('.png') || name.includes('.jpg')
    })
    
    console.log(`发现 ${cacheableResources.length} 个可缓存的资源`)
  },
  
  // 检查重复请求
  checkDuplicateRequests: () => {
    const resources = performance.getEntriesByType('resource')
    const resourceMap = new Map()
    const duplicates = []
    
    resources.forEach(resource => {
      const name = resource.name
      if (resourceMap.has(name)) {
        duplicates.push(name)
      } else {
        resourceMap.set(name, resource)
      }
    })
    
    if (duplicates.length > 0) {
      console.warn(`发现 ${duplicates.length} 个重复请求`)
    }
  }
}

// 创建全局性能监控器实例
export const performanceMonitor = new PerformanceMonitor()

// 页面加载完成后记录指标
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    performanceMonitor.recordDOMContentLoaded()
    performanceMonitor.recordFirstPaint()
    performanceMonitor.recordFirstContentfulPaint()
  })
} else {
  performanceMonitor.recordDOMContentLoaded()
  performanceMonitor.recordFirstPaint()
  performanceMonitor.recordFirstContentfulPaint()
}

// 页面完全加载后记录指标
window.addEventListener('load', () => {
  performanceMonitor.recordPageLoadTime()
  
  // 运行性能优化检查
  performanceOptimizations.checkImageOptimization()
  performanceOptimizations.checkResourceCompression()
  performanceOptimizations.checkCacheStrategy()
  performanceOptimizations.checkDuplicateRequests()
})

// 导出性能监控器
export default performanceMonitor
