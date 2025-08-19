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

  private async sendLog(logData: LogData): Promise<void> {
    if (!this.isEnabled) return;

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
      console.warn('Failed to send log to backend:', error);
    }
  }

  public info(message: string, data?: any): void {
    console.info(`[FRONTEND] ${message}`, data);
    this.sendLog({ level: 'info', message, data });
  }

  public warn(message: string, data?: any): void {
    console.warn(`[FRONTEND] ${message}`, data);
    this.sendLog({ level: 'warn', message, data });
  }

  public error(message: string, data?: any): void {
    console.error(`[FRONTEND] ${message}`, data);
    this.sendLog({ level: 'error', message, data });
  }

  public log(message: string, data?: any): void {
    this.info(message, data);
  }
}

export const frontendLogger = FrontendLogger.getInstance();
