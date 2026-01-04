/**
 * 调试日志系统
 * 用于追踪前后端数据流和状态变化
 */

type LogLevel = 'error' | 'warn' | 'info' | 'debug';
type LogCategory = 'stream' | 'auth' | 'ui' | 'network' | 'state' | 'component';

interface LogEntry {
  timestamp: number;
  level: LogLevel;
  category: LogCategory;
  message: string;
  data?: any;
  sessionId?: string;
  threadId?: string;
}

class DebugLogger {
  private logs: LogEntry[] = [];
  private maxLogs = 1000;
  private enabled = process.env.NODE_ENV === 'development' || localStorage.getItem('DEBUG_MODE') === 'true';

  private addLog(
    level: LogLevel,
    category: LogCategory,
    message: string,
    data?: any,
    sessionId?: string,
    threadId?: string
  ) {
    if (!this.enabled) return;

    const logEntry: LogEntry = {
      timestamp: Date.now(),
      level,
      category,
      message,
      data,
      sessionId,
      threadId,
    };

    this.logs.push(logEntry);

    // 保持日志数量在限制内
    if (this.logs.length > this.maxLogs) {
      this.logs = this.logs.slice(-this.maxLogs);
    }

    // 控制台输出
    const emoji = this.getEmoji(level, category);
    const timestamp = new Date(logEntry.timestamp).toLocaleTimeString();
    console.log(`${emoji} [${timestamp}] [${category.toUpperCase()}] ${message}`, data || '');
  }

  private getEmoji(level: LogLevel, category: LogCategory): string {
    const emojis = {
      error: { stream: '❌', auth: '🔒', ui: '🚨', network: '🌐', state: '📊', component: '🧩' },
      warn: { stream: '⚠️', auth: '🔐', ui: '⚡', network: '📡', state: '📈', component: '🔧' },
      info: { stream: '📡', auth: '🔑', ui: '💡', network: '🔗', state: '📋', component: '⚙️' },
      debug: { stream: '🔍', auth: '🔍', ui: '🔍', network: '🔍', state: '🔍', component: '🔍' },
    };
    return emojis[level][category];
  }

  // 公开方法
  error(category: LogCategory, message: string, data?: any, sessionId?: string, threadId?: string) {
    this.addLog('error', category, message, data, sessionId, threadId);
  }

  warn(category: LogCategory, message: string, data?: any, sessionId?: string, threadId?: string) {
    this.addLog('warn', category, message, data, sessionId, threadId);
  }

  info(category: LogCategory, message: string, data?: any, sessionId?: string, threadId?: string) {
    this.addLog('info', category, message, data, sessionId, threadId);
  }

  debug(category: LogCategory, message: string, data?: any, sessionId?: string, threadId?: string) {
    this.addLog('debug', category, message, data, sessionId, threadId);
  }

  // 流式数据专用方法
  streamIncoming(type: string, data: any, sessionId?: string, threadId?: string) {
    this.info('stream', `📥 接收流数据: ${type}`, data, sessionId, threadId);
  }

  streamOutgoing(type: string, data: any, sessionId?: string, threadId?: string) {
    this.info('stream', `📤 发送流数据: ${type}`, data, sessionId, threadId);
  }

  streamError(error: any, sessionId?: string, threadId?: string) {
    this.error('stream', '❌ 流式传输错误', error, sessionId, threadId);
  }

  // 认证专用方法
  authSuccess(username: string, sessionId?: string) {
    this.info('auth', `✅ 认证成功: ${username}`, undefined, sessionId);
  }

  authFailure(error: any, sessionId?: string) {
    this.error('auth', '❌ 认证失败', error, sessionId);
  }

  // UI状态专用方法
  uiStateChange(component: string, state: any) {
    this.debug('ui', `🔄 UI状态变更: ${component}`, state);
  }

  // 网络请求专用方法
  networkRequest(method: string, url: string, data?: any) {
    this.debug('network', `🌐 请求: ${method} ${url}`, data);
  }

  networkResponse(method: string, url: string, status: number, data?: any) {
    const level = status >= 400 ? 'error' : 'info';
    this.addLog(level, 'network', `📡 响应: ${method} ${url} (${status})`, data);
  }

  // 状态管理专用方法
  stateUpdate(store: string, action: string, payload: any) {
    this.debug('state', `📊 状态更新: ${store}.${action}`, payload);
  }

  // 组件生命周期专用方法
  componentMount(component: string, props?: any) {
    this.debug('component', `🧩 组件挂载: ${component}`, props);
  }

  componentUnmount(component: string) {
    this.debug('component', `🧩 组件卸载: ${component}`);
  }

  // 获取日志
  getLogs(filter?: { level?: LogLevel; category?: LogCategory; limit?: number }): LogEntry[] {
    let filteredLogs = this.logs;

    if (filter?.level) {
      filteredLogs = filteredLogs.filter(log => log.level === filter.level);
    }

    if (filter?.category) {
      filteredLogs = filteredLogs.filter(log => log.category === filter.category);
    }

    const limit = filter?.limit || 100;
    return filteredLogs.slice(-limit);
  }

  // 导出日志到文件
  exportToFile(filename?: string) {
    const logsText = this.logs.map(log => {
      const timestamp = new Date(log.timestamp).toISOString();
      const emoji = this.getEmoji(log.level, log.category);
      const dataStr = log.data ? ` | Data: ${JSON.stringify(log.data, null, 2)}` : '';
      const sessionStr = log.sessionId ? ` | Session: ${log.sessionId}` : '';
      const threadStr = log.threadId ? ` | Thread: ${log.threadId}` : '';
      
      return `[${timestamp}] ${emoji} [${log.level.toUpperCase()}] [${log.category.toUpperCase()}] ${log.message}${dataStr}${sessionStr}${threadStr}`;
    }).join('\n');

    const blob = new Blob([logsText], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename || `debug-log-${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    
    this.info('ui', `📄 日志已导出到文件: ${a.download}`);
  }

  // 将日志保存为可下载的文件（包括控制台输出）
  exportConsoleLogs(filename?: string) {
    const allOutput = this.logs.map(log => {
      const timestamp = new Date(log.timestamp).toISOString();
      const emoji = this.getEmoji(log.level, log.category);
      const dataStr = log.data ? `\n  Data: ${JSON.stringify(log.data, null, 2)}` : '';
      const sessionStr = log.sessionId ? `\n  Session: ${log.sessionId}` : '';
      const threadStr = log.threadId ? `\n  Thread: ${log.threadId}` : '';
      
      return `[${timestamp}] ${emoji} [${log.level.toUpperCase()}] [${log.category.toUpperCase()}] ${log.message}${dataStr}${sessionStr}${threadStr}`;
    }).join('\n\n');

    const blob = new Blob([allOutput], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename || `console-logs-${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    
    this.info('ui', `📄 控制台日志已导出到文件: ${a.download}`);
  }

  // 保存到localStorage（持久化）
  saveToLocalStorage() {
    try {
      const logsData = {
        timestamp: Date.now(),
        logs: this.logs
      };
      localStorage.setItem('debug_logs', JSON.stringify(logsData));
      this.info('ui', '💾 调试日志已保存到localStorage');
    } catch (error) {
      this.error('ui', '❌ 保存调试日志失败', error);
    }
  }

  // 从localStorage加载
  loadFromLocalStorage() {
    try {
      const savedData = localStorage.getItem('debug_logs');
      if (savedData) {
        const parsed = JSON.parse(savedData);
        this.logs = parsed.logs || [];
        this.info('ui', `📂 从localStorage加载了 ${this.logs.length} 条日志`);
      }
    } catch (error) {
    }
  }

  // 清除日志
  clearLogs() {
    this.logs = [];
    localStorage.removeItem('debug_logs');
    this.info('ui', '🗑️ 调试日志已清除');
  }

  // 清除日志
  clear() {
    this.logs = [];
    localStorage.removeItem('debug_logs');
    this.info('ui', '🗑️ 调试日志已清除');
  }

  // 捕获控制台输出并记录到日志
  setupConsoleCapture() {
    if (typeof window === 'undefined') return;

    const originalConsole = {
      log: console.log.bind(console),
      warn: console.warn.bind(console),
      error: console.error.bind(console),
      info: console.info.bind(console),
      debug: console.debug.bind(console),
    };

    // 捕获 console.log
    console.log = (...args) => {
      originalConsole.log(...args);
      this.info('ui', 'Console.log', args);
    };

    // 捕获 console.warn
    console.warn = (...args) => {
      originalConsole.warn(...args);
      this.warn('ui', 'Console.warn', args);
    };

    // 捕获 console.error
    console.error = (...args) => {
      originalConsole.error(...args);
      this.error('ui', 'Console.error', args);
    };

    // 捕获 console.info
    console.info = (...args) => {
      originalConsole.info(...args);
      this.info('ui', 'Console.info', args);
    };

    // 捕获 console.debug
    console.debug = (...args) => {
      originalConsole.debug(...args);
      this.debug('ui', 'Console.debug', args);
    };

    this.info('ui', '🔧 控制台输出捕获已启用');
  }

  // 导出日志
  export(): string {
    return JSON.stringify(this.logs, null, 2);
  }

  // 启用/禁用调试模式
  setEnabled(enabled: boolean) {
    this.enabled = enabled;
    localStorage.setItem('DEBUG_MODE', enabled.toString());
  }
}

// 导出单例实例
export const debugLogger = new DebugLogger();

// 导出便捷方法
export function error(category: LogCategory, message: string, data?: any, sessionId?: string, threadId?: string) {
  debugLogger.error(category, message, data, sessionId, threadId);
}

export function warn(category: LogCategory, message: string, data?: any, sessionId?: string, threadId?: string) {
  debugLogger.warn(category, message, data, sessionId, threadId);
}

export function info(category: LogCategory, message: string, data?: any, sessionId?: string, threadId?: string) {
  debugLogger.info(category, message, data, sessionId, threadId);
}

export function debug(category: LogCategory, message: string, data?: any, sessionId?: string, threadId?: string) {
  debugLogger.debug(category, message, data, sessionId, threadId);
}

export function streamIncoming(type: string, data: any, sessionId?: string, threadId?: string) {
  debugLogger.streamIncoming(type, data, sessionId, threadId);
}

export function streamOutgoing(type: string, data: any, sessionId?: string, threadId?: string) {
  debugLogger.streamOutgoing(type, data, sessionId, threadId);
}

export function streamError(error: any, sessionId?: string, threadId?: string) {
  debugLogger.streamError(error, sessionId, threadId);
}

export function authSuccess(username: string, sessionId?: string) {
  debugLogger.authSuccess(username, sessionId);
}

export function authFailure(error: any, sessionId?: string) {
  debugLogger.authFailure(error, sessionId);
}

export function uiStateChange(component: string, state: any) {
  debugLogger.uiStateChange(component, state);
}

export function networkRequest(method: string, url: string, data?: any) {
  debugLogger.networkRequest(method, url, data);
}

export function networkResponse(method: string, url: string, status: number, data?: any) {
  debugLogger.networkResponse(method, url, status, data);
}

export function stateUpdate(store: string, action: string, payload: any) {
  debugLogger.stateUpdate(store, action, payload);
}

export function componentMount(component: string, props?: any) {
  debugLogger.componentMount(component, props);
}

export function componentUnmount(component: string) {
  debugLogger.componentUnmount(component);
}