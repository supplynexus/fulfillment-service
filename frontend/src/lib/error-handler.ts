/**
 * 统一错误处理系统
 * 
 * 提供全局错误处理、用户友好的错误提示和错误上报功能
 */

import { toast } from 'react-hot-toast'

// 错误类型枚举
export enum ErrorType {
  NETWORK_ERROR = 'NETWORK_ERROR',
  VALIDATION_ERROR = 'VALIDATION_ERROR',
  AUTHENTICATION_ERROR = 'AUTHENTICATION_ERROR',
  AUTHORIZATION_ERROR = 'AUTHORIZATION_ERROR',
  SERVER_ERROR = 'SERVER_ERROR',
  CLIENT_ERROR = 'CLIENT_ERROR',
  UNKNOWN_ERROR = 'UNKNOWN_ERROR'
}

// 错误严重程度
export enum ErrorSeverity {
  LOW = 'LOW',
  MEDIUM = 'MEDIUM',
  HIGH = 'HIGH',
  CRITICAL = 'CRITICAL'
}

// 错误信息接口
export interface ErrorInfo {
  type: ErrorType
  severity: ErrorSeverity
  message: string
  userMessage: string
  code?: string | number
  details?: any
  timestamp: number
  url: string
  userId?: string
  tenantId?: string
}

// 错误处理配置
interface ErrorHandlerConfig {
  enableToast: boolean
  enableConsole: boolean
  enableReporting: boolean
  reportEndpoint: string
  maxRetries: number
  retryDelay: number
}

// 默认配置
const defaultConfig: ErrorHandlerConfig = {
  enableToast: true,
  enableConsole: true,
  enableReporting: true,
  reportEndpoint: '/api/errors',
  maxRetries: 3,
  retryDelay: 1000
}

// 用户友好的错误消息映射
const userFriendlyMessages: Record<ErrorType, string> = {
  [ErrorType.NETWORK_ERROR]: '网络连接异常，请检查网络设置后重试',
  [ErrorType.VALIDATION_ERROR]: '输入信息有误，请检查后重新提交',
  [ErrorType.AUTHENTICATION_ERROR]: '登录已过期，请重新登录',
  [ErrorType.AUTHORIZATION_ERROR]: '权限不足，请联系管理员',
  [ErrorType.SERVER_ERROR]: '服务器暂时无法响应，请稍后重试',
  [ErrorType.CLIENT_ERROR]: '请求参数有误，请检查后重试',
  [ErrorType.UNKNOWN_ERROR]: '系统出现异常，请稍后重试'
}

// 错误处理类
class ErrorHandler {
  private config: ErrorHandlerConfig
  private errorQueue: ErrorInfo[] = []
  private isReporting: boolean = false

  constructor(config: Partial<ErrorHandlerConfig> = {}) {
    this.config = { ...defaultConfig, ...config }
    this.initializeGlobalHandlers()
  }

  private initializeGlobalHandlers() {
    // 全局错误处理
    window.addEventListener('error', (event) => {
      this.handleError({
        type: ErrorType.CLIENT_ERROR,
        severity: ErrorSeverity.HIGH,
        message: event.message,
        userMessage: '页面出现错误',
        details: {
          filename: event.filename,
          lineno: event.lineno,
          colno: event.colno,
          error: event.error?.stack
        },
        timestamp: Date.now(),
        url: window.location.href
      })
    })

    // Promise拒绝处理
    window.addEventListener('unhandledrejection', (event) => {
      this.handleError({
        type: ErrorType.CLIENT_ERROR,
        severity: ErrorSeverity.MEDIUM,
        message: event.reason?.message || 'Promise rejected',
        userMessage: '操作失败',
        details: {
          reason: event.reason,
          promise: event.promise
        },
        timestamp: Date.now(),
        url: window.location.href
      })
    })
  }

  // 处理错误
  handleError(errorInfo: ErrorInfo) {
    // 添加到错误队列
    this.errorQueue.push(errorInfo)

    // 控制台输出
    if (this.config.enableConsole) {
      this.logError(errorInfo)
    }

    // 用户提示
    if (this.config.enableToast) {
      this.showUserMessage(errorInfo)
    }

    // 错误上报
    if (this.config.enableReporting) {
      this.reportError(errorInfo)
    }
  }

  // 处理API错误
  handleApiError(error: any, context?: string): ErrorInfo {
    const errorInfo: ErrorInfo = {
      type: this.determineErrorType(error),
      severity: this.determineErrorSeverity(error),
      message: error.message || 'Unknown error',
      userMessage: this.getUserFriendlyMessage(error),
      code: error.status || error.code,
      details: {
        context,
        response: error.response?.data,
        status: error.response?.status,
        url: error.config?.url,
        method: error.config?.method
      },
      timestamp: Date.now(),
      url: window.location.href,
      userId: this.getCurrentUserId(),
      tenantId: this.getCurrentTenantId()
    }

    this.handleError(errorInfo)
    return errorInfo
  }

  // 处理表单验证错误
  handleValidationError(errors: Record<string, string[]>): ErrorInfo {
    const errorInfo: ErrorInfo = {
      type: ErrorType.VALIDATION_ERROR,
      severity: ErrorSeverity.LOW,
      message: 'Validation failed',
      userMessage: '请检查输入信息',
      details: { validationErrors: errors },
      timestamp: Date.now(),
      url: window.location.href
    }

    this.handleError(errorInfo)
    return errorInfo
  }

  // 确定错误类型
  private determineErrorType(error: any): ErrorType {
    if (!error.response) {
      return ErrorType.NETWORK_ERROR
    }

    const status = error.response.status
    if (status === 401) {
      return ErrorType.AUTHENTICATION_ERROR
    }
    if (status === 403) {
      return ErrorType.AUTHORIZATION_ERROR
    }
    if (status >= 400 && status < 500) {
      return ErrorType.CLIENT_ERROR
    }
    if (status >= 500) {
      return ErrorType.SERVER_ERROR
    }

    return ErrorType.UNKNOWN_ERROR
  }

  // 确定错误严重程度
  private determineErrorSeverity(error: any): ErrorSeverity {
    const status = error.response?.status
    if (status === 401 || status === 403) {
      return ErrorSeverity.HIGH
    }
    if (status >= 500) {
      return ErrorSeverity.CRITICAL
    }
    if (status >= 400 && status < 500) {
      return ErrorSeverity.MEDIUM
    }
    return ErrorSeverity.LOW
  }

  // 获取用户友好消息
  private getUserFriendlyMessage(error: any): string {
    const errorType = this.determineErrorType(error)
    
    // 检查是否有自定义错误消息
    if (error.response?.data?.message) {
      return error.response.data.message
    }
    
    // 检查是否有验证错误
    if (error.response?.data?.errors) {
      const errors = error.response.data.errors
      if (typeof errors === 'object') {
        const firstError = Object.values(errors)[0]
        if (Array.isArray(firstError) && firstError.length > 0) {
          return firstError[0]
        }
      }
    }

    return userFriendlyMessages[errorType]
  }

  // 控制台输出
  private logError(errorInfo: ErrorInfo) {
    const logMethod = errorInfo.severity === ErrorSeverity.CRITICAL ? 'error' : 'warn'
    console[logMethod](`[${errorInfo.type}] ${errorInfo.message}`, {
      severity: errorInfo.severity,
      code: errorInfo.code,
      details: errorInfo.details,
      timestamp: new Date(errorInfo.timestamp).toISOString()
    })
  }

  // 显示用户消息
  private showUserMessage(errorInfo: ErrorInfo) {
    const toastOptions = {
      duration: this.getToastDuration(errorInfo.severity),
      position: 'top-right' as const,
      style: {
        background: this.getToastColor(errorInfo.severity),
        color: '#fff'
      }
    }

    if (errorInfo.severity === ErrorSeverity.CRITICAL) {
      toast.error(errorInfo.userMessage, toastOptions)
    } else if (errorInfo.severity === ErrorSeverity.HIGH) {
      toast.error(errorInfo.userMessage, toastOptions)
    } else if (errorInfo.severity === ErrorSeverity.MEDIUM) {
      toast.error(errorInfo.userMessage, toastOptions)
    } else {
      toast.error(errorInfo.userMessage, toastOptions)
    }
  }

  // 获取Toast持续时间
  private getToastDuration(severity: ErrorSeverity): number {
    switch (severity) {
      case ErrorSeverity.CRITICAL:
        return 10000
      case ErrorSeverity.HIGH:
        return 5000
      case ErrorSeverity.MEDIUM:
        return 3000
      default:
        return 2000
    }
  }

  // 获取Toast颜色
  private getToastColor(severity: ErrorSeverity): string {
    switch (severity) {
      case ErrorSeverity.CRITICAL:
        return '#d32f2f'
      case ErrorSeverity.HIGH:
        return '#f57c00'
      case ErrorSeverity.MEDIUM:
        return '#fbc02d'
      default:
        return '#757575'
    }
  }

  // 错误上报
  private async reportError(errorInfo: ErrorInfo) {
    if (this.isReporting) {
      return
    }

    this.isReporting = true

    try {
      await fetch(this.config.reportEndpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify(errorInfo)
      })
    } catch (error) {
      console.error('Failed to report error:', error)
    } finally {
      this.isReporting = false
    }
  }

  // 获取当前用户ID
  private getCurrentUserId(): string | undefined {
    try {
      const token = localStorage.getItem('token')
      if (token) {
        const payload = JSON.parse(atob(token.split('.')[1]))
        return payload.sub
      }
    } catch (error) {
      // 忽略解析错误
    }
    return undefined
  }

  // 获取当前租户ID
  private getCurrentTenantId(): string | undefined {
    try {
      const token = localStorage.getItem('token')
      if (token) {
        const payload = JSON.parse(atob(token.split('.')[1]))
        return payload.tenant_id
      }
    } catch (error) {
      // 忽略解析错误
    }
    return undefined
  }

  // 获取错误统计
  getErrorStats() {
    const stats = {
      total: this.errorQueue.length,
      byType: {} as Record<ErrorType, number>,
      bySeverity: {} as Record<ErrorSeverity, number>,
      recent: this.errorQueue.slice(-10)
    }

    this.errorQueue.forEach(error => {
      stats.byType[error.type] = (stats.byType[error.type] || 0) + 1
      stats.bySeverity[error.severity] = (stats.bySeverity[error.severity] || 0) + 1
    })

    return stats
  }

  // 清理错误队列
  clearErrorQueue() {
    this.errorQueue = []
  }
}

// 创建全局错误处理器实例
export const errorHandler = new ErrorHandler()

// 导出便捷方法
export const handleError = (error: any, context?: string) => {
  return errorHandler.handleApiError(error, context)
}

export const handleValidationError = (errors: Record<string, string[]>) => {
  return errorHandler.handleValidationError(errors)
}

// 创建错误边界组件
export class ErrorBoundary extends React.Component<
  { children: React.ReactNode; fallback?: React.ComponentType<{ error: Error }> },
  { hasError: boolean; error?: Error }
> {
  constructor(props: any) {
    super(props)
    this.state = { hasError: false }
  }

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    errorHandler.handleError({
      type: ErrorType.CLIENT_ERROR,
      severity: ErrorSeverity.HIGH,
      message: error.message,
      userMessage: '组件渲染错误',
      details: errorInfo,
      timestamp: Date.now(),
      url: window.location.href
    })
  }

  render() {
    if (this.state.hasError) {
      const FallbackComponent = this.props.fallback || DefaultErrorFallback
      return <FallbackComponent error={this.state.error!} />
    }

    return this.props.children
  }
}

// 默认错误回退组件
const DefaultErrorFallback: React.FC<{ error: Error }> = ({ error }) => (
  <div style={{ padding: '20px', textAlign: 'center' }}>
    <h2>出现错误</h2>
    <p>页面渲染出现问题，请刷新页面重试</p>
    <button onClick={() => window.location.reload()}>
      刷新页面
    </button>
  </div>
)

export default errorHandler
