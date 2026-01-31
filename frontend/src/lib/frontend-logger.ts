interface LogData {
  level: 'info' | 'warn' | 'error';
  message: string;
  data?: any;
}

class FrontendLogger {
  private static instance: FrontendLogger;
  private isEnabled: boolean = true;

  private constructor() {}

  public static getInstance(): FrontendLogger {
    if (!FrontendLogger.instance) {
      FrontendLogger.instance = new FrontendLogger();
    }
    return FrontendLogger.instance;
  }

  public enable(): void {
    this.isEnabled = true;
  }

  public disable(): void {
    this.isEnabled = false;
  }

  private safeSerialize(data: any): any {
    if (data === null || data === undefined) {
      return data;
    }

    try {
      // 使用 JSON.parse(JSON.stringify()) 来深度克隆并移除循环引用
      return JSON.parse(JSON.stringify(data));
    } catch (error) {
      // 如果序列化失败，返回一个安全的字符串表示
      return {
        error: 'Failed to serialize data',
        type: typeof data,
        constructor: data?.constructor?.name || 'Unknown',
      };
    }
  }

  private async sendLog(logData: LogData): Promise<void> {
    if (!this.isEnabled) return;

    // 在服务器端（Next.js API route）不发送日志，避免 URL 解析错误
    if (typeof window === 'undefined') {
      return;
    }

    try {
      await fetch('/api/log', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(logData),
      });
    } catch (error) {
      // 静默失败，避免日志API错误影响主流程
      // 只在客户端显示警告，服务器端不显示
      if (typeof window !== 'undefined') {
        console.warn('Failed to send log to backend:', error);
      }
    }
  }

  public info(message: string, data?: any): void {
    const safeData = this.safeSerialize(data);
    console.info(`[FRONTEND] ${message}`, safeData);
    this.sendLog({ level: 'info', message, data: safeData });
  }

  public warn(message: string, data?: any): void {
    const safeData = this.safeSerialize(data);
    console.warn(`[FRONTEND] ${message}`, safeData);
    this.sendLog({ level: 'warn', message, data: safeData });
  }

  public error(message: string, data?: any): void {
    // 安全地序列化数据，避免循环引用
    const safeData = this.safeSerialize(data);
    console.error(`[FRONTEND] ${message}`, safeData);
    this.sendLog({ level: 'error', message, data: safeData });
  }

  public log(message: string, data?: any): void {
    this.info(message, data);
  }
}

export const frontendLogger = FrontendLogger.getInstance();
