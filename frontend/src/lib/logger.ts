/**
 * 前端日志工具模块
 * 支持JSON格式日志输出和请求ID关联
 */

import { v4 as uuidv4 } from 'uuid';

// 请求ID上下文
let currentRequestId: string | null = null;

// 日志级别
export enum LogLevel {
  DEBUG = 'debug',
  INFO = 'info',
  WARN = 'warn',
  ERROR = 'error',
}

// 日志条目接口
interface LogEntry {
  timestamp: string;
  level: LogLevel;
  message: string;
  requestId?: string;
  module?: string;
  [key: string]: any;
}

/**
 * 设置当前请求ID
 */
export function setRequestId(requestId?: string): void {
  currentRequestId = requestId || uuidv4();
}

/**
 * 获取当前请求ID
 */
export function getRequestId(): string | null {
  return currentRequestId;
}

/**
 * 生成新的请求ID
 */
export function generateRequestId(): string {
  return uuidv4();
}

/**
 * 格式化日志条目为JSON字符串
 */
function formatLogEntry(entry: LogEntry): string {
  return JSON.stringify(entry, null, 0);
}

/**
 * 基础日志函数
 */
function log(
  level: LogLevel,
  message: string,
  data?: Record<string, any>,
  module?: string
): void {
  const entry: LogEntry = {
    timestamp: new Date().toISOString(),
    level,
    message,
    ...(currentRequestId && { requestId: currentRequestId }),
    ...(module && { module }),
    ...data,
  };

  const logString = formatLogEntry(entry);

  // 根据日志级别输出到控制台
  switch (level) {
    case LogLevel.DEBUG:
      console.debug(logString);
      break;
    case LogLevel.INFO:
      console.info(logString);
      break;
    case LogLevel.WARN:
      console.warn(logString);
      break;
    case LogLevel.ERROR:
      console.error(logString);
      break;
  }
}

/**
 * 日志记录器类
 */
export class Logger {
  private module: string;

  constructor(module?: string) {
    this.module = module || 'app';
  }

  debug(message: string, data?: Record<string, any>): void {
    log(LogLevel.DEBUG, message, data, this.module);
  }

  info(message: string, data?: Record<string, any>): void {
    log(LogLevel.INFO, message, data, this.module);
  }

  warn(message: string, data?: Record<string, any>): void {
    log(LogLevel.WARN, message, data, this.module);
  }

  error(message: string, data?: Record<string, any>): void {
    log(LogLevel.ERROR, message, data, this.module);
  }

  /**
   * 记录请求开始
   */
  requestStart(method: string, url: string, data?: Record<string, any>): void {
    this.info('Request started', {
      method,
      url,
      ...data,
    });
  }

  /**
   * 记录请求完成
   */
  requestComplete(
    method: string,
    url: string,
    statusCode: number,
    duration: number,
    data?: Record<string, any>
  ): void {
    this.info('Request completed', {
      method,
      url,
      statusCode,
      duration: `${duration.toFixed(3)}s`,
      ...data,
    });
  }

  /**
   * 记录请求错误
   */
  requestError(
    method: string,
    url: string,
    error: any,
    duration: number,
    data?: Record<string, any>
  ): void {
    this.error('Request failed', {
      method,
      url,
      error: error?.message || String(error),
      errorType: error?.constructor?.name || 'Unknown',
      duration: `${duration.toFixed(3)}s`,
      ...data,
    });
  }
}

/**
 * 创建模块日志记录器
 */
export function createLogger(module: string): Logger {
  return new Logger(module);
}

/**
 * 全局日志记录器
 */
export const logger = new Logger('global');
