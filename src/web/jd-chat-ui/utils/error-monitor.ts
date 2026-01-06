/**
 * 前端错误监控系统
 * 用于捕获、记录和上报前端错误
 */

import log from 'loglevel';
import { saveAs } from 'file-saver';

// 错误类型枚举
export enum ErrorType {
  RUNTIME_ERROR = 'RUNTIME_ERROR',
  PROMISE_REJECTION = 'PROMISE_REJECTION',
  HTTP_ERROR = 'HTTP_ERROR',
  NETWORK_ERROR = 'NETWORK_ERROR',
  USER_INTERACTION_ERROR = 'USER_INTERACTION_ERROR',
  RESOURCE_LOAD_ERROR = 'RESOURCE_LOAD_ERROR',
  COMPONENT_ERROR = 'COMPONENT_ERROR',
}

// 错误严重性级别
export enum ErrorSeverity {
  CRITICAL = 'CRITICAL',
  HIGH = 'HIGH',
  MEDIUM = 'MEDIUM',
  LOW = 'LOW',
}

// 错误数据接口
export interface ErrorData {
  id: string;
  type: ErrorType;
  severity: ErrorSeverity;
  message: string;
  stack?: string;
  url: string;
  lineNumber?: number;
  columnNumber?: number;
  timestamp: string;
  userAgent?: string;
  context?: Record<string, any>;
  resolved?: boolean;
  resolvedAt?: string;
}

// 错误事件处理器类型
type ErrorHandler = (error: ErrorData) => void;

// 错误监控器类
class ErrorMonitor {
  private static instance: ErrorMonitor;
  private handlers: ErrorHandler[] = [];
  private errors: ErrorData[] = [];
  private maxStoredErrors = 1000;
  private apiBase = "http://localhost:8000/api/v1";
  private isReporting = false;

  private getWindowUrl(): string {
    return typeof window !== 'undefined' ? window.location.href : '';
  }

  private getUserAgent(): string {
    return typeof navigator !== 'undefined' ? navigator.userAgent : '';
  }

  // 单例模式
  public static getInstance(): ErrorMonitor {
    if (!ErrorMonitor.instance) {
      ErrorMonitor.instance = new ErrorMonitor();
    }
    return ErrorMonitor.instance;
  }

  // 私有构造函数，防止直接实例化
  private constructor() {
    this.initializeGlobalErrorHandlers();
  }

  // 初始化全局错误处理器
  private initializeGlobalErrorHandlers() {
    if (typeof window === 'undefined') return;
    
    window.addEventListener('error', (event) => {
      this.handleError({
        type: ErrorType.RUNTIME_ERROR,
        severity: ErrorSeverity.HIGH,
        message: event.message || 'Unknown runtime error',
        stack: event.error?.stack,
        url: event.filename || window.location.href,
        lineNumber: event.lineno,
        columnNumber: event.colno,
        context: { event: 'error' }
      });
    });

    window.addEventListener('unhandledrejection', (event) => {
      this.handleError({
        type: ErrorType.PROMISE_REJECTION,
        severity: ErrorSeverity.HIGH,
        message: `Unhandled promise rejection: ${event.reason}`,
        stack: event.reason?.stack,
        url: window.location.href,
        context: { event: 'unhandledrejection', reason: event.reason }
      });
    });
  }

  // 添加错误处理器
  public addHandler(handler: ErrorHandler) {
    this.handlers.push(handler);
  }

  // 移除错误处理器
  public removeHandler(handler: ErrorHandler) {
    this.handlers = this.handlers.filter(h => h !== handler);
  }

  // 处理错误
  public handleError(errorData: Partial<ErrorData>) {
    // 生成唯一ID
    const id = this.generateId();
    
    // 补全错误数据
    const fullError: ErrorData = {
      id,
      type: errorData.type || ErrorType.RUNTIME_ERROR,
      severity: errorData.severity || ErrorSeverity.MEDIUM,
      message: errorData.message || 'Unknown error',
      stack: errorData.stack,
      url: errorData.url || this.getWindowUrl(),
      lineNumber: errorData.lineNumber,
      columnNumber: errorData.columnNumber,
      timestamp: errorData.timestamp || new Date().toISOString(),
      userAgent: this.getUserAgent(),
      context: errorData.context || {},
      resolved: false
    };

    // 存储错误
    this.errors.push(fullError);

    // 如果存储超过最大限制，删除最旧的错误
    if (this.errors.length > this.maxStoredErrors) {
      this.errors = this.errors.slice(-this.maxStoredErrors);
    }

    // 记录错误日志
    this.logError(fullError);

    // 调用所有注册的处理器
    this.handlers.forEach(handler => handler(fullError));
  }

  // 记录错误到日志系统
  private logError(error: ErrorData) {
    switch (error.severity) {
      case ErrorSeverity.CRITICAL:
        log.error(`[ERROR][${error.type}] ${error.message}`, error);
        break;
      case ErrorSeverity.HIGH:
        log.error(`[ERROR][${error.type}] ${error.message}`, error);
        break;
      case ErrorSeverity.MEDIUM:
        log.warn(`[WARNING][${error.type}] ${error.message}`, error);
        break;
      case ErrorSeverity.LOW:
        log.info(`[INFO][${error.type}] ${error.message}`, error);
        break;
    }
  }

  // 生成唯一ID
  private generateId(): string {
    return `${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
  }

  // 获取所有错误
  public getErrors(): ErrorData[] {
    return [...this.errors];
  }

  // 按类型获取错误
  public getErrorsByType(type: ErrorType): ErrorData[] {
    return this.errors.filter(error => error.type === type);
  }

  // 按严重性获取错误
  public getErrorsBySeverity(severity: ErrorSeverity): ErrorData[] {
    return this.errors.filter(error => error.severity === severity);
  }

  // 标记错误为已解决
  public markErrorAsResolved(id: string) {
    const errorIndex = this.errors.findIndex(e => e.id === id);
    if (errorIndex !== -1) {
      this.errors[errorIndex].resolved = true;
      this.errors[errorIndex].resolvedAt = new Date().toISOString();
      log.info(`Error ${id} marked as resolved`);
    }
  }

  // 清除已解决的错误
  public clearResolvedErrors() {
    const originalLength = this.errors.length;
    this.errors = this.errors.filter(error => !error.resolved);
    log.info(`Cleared ${originalLength - this.errors.length} resolved errors`);
  }

  // 导出错误日志为文件
  public exportErrorsAsFile(filename = 'error-log.json') {
    const blob = new Blob([JSON.stringify(this.errors, null, 2)], {
      type: 'application/json;charset=utf-8'
    });
    saveAs(blob, filename);
  }

  // 将错误发送到服务器
  public async sendErrorsToServer() {
    if (this.isReporting) {
      log.warn('Error report already in progress');
      return;
    }

    try {
      this.isReporting = true;
      
      // 只发送未解决的错误
      const unresolvedErrors = this.errors.filter(error => !error.resolved);
      
      if (unresolvedErrors.length === 0) {
        log.info('No unresolved errors to report');
        return;
      }
      
      const response = await fetch(`${this.apiBase}/logs/errors`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          errors: unresolvedErrors,
          timestamp: new Date().toISOString(),
          userAgent: this.getUserAgent(),
          url: this.getWindowUrl()
        })
      });
      
      if (!response.ok) {
        throw new Error(`Server responded with ${response.status}`);
      }
      
      log.info(`Successfully reported ${unresolvedErrors.length} errors to server`);
      
      // 可以在这里将已上报的错误标记为已解决
      // (可选，取决于是否需要服务器端确认)
      
    } catch (error) {
      log.error('Failed to send errors to server', error);
    } finally {
      this.isReporting = false;
    }
  }

  // 启动自动上报定时器
  public startAutoReport(intervalMs = 60000) {
    setInterval(() => {
      this.sendErrorsToServer();
    }, intervalMs);
    
    log.info(`Error auto reporting enabled with interval ${intervalMs/1000} seconds`);
  }
}

// 导出单例实例
export const errorMonitor = ErrorMonitor.getInstance();

// 导出便捷函数
export const handleError = (errorData: Partial<ErrorData>) => {
  errorMonitor.handleError(errorData);
};