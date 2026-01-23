// utils/logger.ts
import log from 'loglevel';
import { saveAs } from 'file-saver';

const API_BASE = "http://localhost:8000/api/v1";

export type LogLevel = 'trace' | 'debug' | 'info' | 'warn' | 'error';
export type LogCategory = 'stream' | 'auth' | 'ui' | 'network' | 'state' | 'component' | 'general';

export interface LogEntry {
  timestamp: string;
  level: LogLevel;
  category: LogCategory;
  message: string;
  data?: any;
}

class FileLogger {
  private logs: LogEntry[] = [];
  private maxLogs = 1000; // 最大保存日志数量
  private autoSaveInterval: number | null = null; // 自动保存定时器ID
  private lastAutoSaveTime: number = 0; // 上次自动保存的时间戳
  private logDirectory: string = 'logs'; // 默认日志保存目录

  // 设置日志级别
  setLevel(level: LogLevel) {
    log.setLevel(level);
  }

  // 获取当前日志级别
  getLevel(): LogLevel {
    return log.getLevel() as unknown as LogLevel;
  }

  // 设置自动保存功能
  enableAutoSave(intervalMs: number = 60000) {
    // 清除现有的定时器（如果存在）
    if (this.autoSaveInterval) {
      clearInterval(this.autoSaveInterval);
    }
    
    // 设置新的定时器
    this.autoSaveInterval = window.setInterval(() => {
      this.saveLogsToServer();
    }, intervalMs);
    
    this.info('general', `自动保存功能已启用，间隔 ${intervalMs/1000} 秒`);
  }
  
  // 禁用自动保存功能
  disableAutoSave() {
    if (this.autoSaveInterval) {
      clearInterval(this.autoSaveInterval);
      this.autoSaveInterval = null;
      this.info('general', '自动保存功能已禁用');
    }
  }
  
  // 向服务器发送日志
  private async saveLogsToServer() {
    if (this.logs.length === 0) return;
    
    try {
      const currentTime = Date.now();
      // 避免过于频繁的保存操作（至少间隔10秒）
      if (currentTime - this.lastAutoSaveTime < 10000) {
        return;
      }
      
      const logsToSave = [...this.logs]; // 复制日志数组
      this.logs = []; // 清空当前日志数组
      
      this.lastAutoSaveTime = currentTime;
      
      const response = await fetch(`${API_BASE}/logs/save`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          logs: logsToSave,
          timestamp: new Date().toISOString()
        })
      });
      
      if (!response.ok) {
        throw new Error(`服务器响应错误: ${response.status}`);
      }
      
      this.info('general', `成功保存 ${logsToSave.length} 条日志到服务器`);
    } catch (error) {
      this.error('general', '保存日志到服务器失败', { error });
      console.error('保存日志到服务器失败:', error);
      // 恢复日志数组
      // this.logs = [...logsToSave];
    }
  }
  
  // 手动触发日志保存
  async saveLogsManually() {
    this.info('general', '手动触发日志保存');
    return await this.saveLogsToServer();
  }
  
  // 设置日志目录
  setLogDirectory(directory: string) {
    this.logDirectory = directory;
    this.info('general', `日志保存目录设置为: ${directory}`);
  }

  // 通用日志方法
  private log(level: LogLevel, category: LogCategory, message: string, data?: any) {
    const entry: LogEntry = {
      timestamp: new Date().toISOString(),
      level,
      category,
      message,
      data
    };

    // 添加到日志数组
    this.logs.push(entry);

    // 保持日志数量限制
    if (this.logs.length > this.maxLogs) {
      this.logs = this.logs.slice(-this.maxLogs);
    }

    // 使用loglevel输出到控制台
    const logMessage = `[${category.toUpperCase()}] ${message}`;
    
    switch (level) {
      case 'trace':
        log.trace(logMessage, data);
        break;
      case 'debug':
        log.debug(logMessage, data);
        break;
      case 'info':
        log.info(logMessage, data);
        break;
      case 'warn':
        log.warn(logMessage, data);
        break;
      case 'error':
        log.error(logMessage, data);
        break;
    }
  }

  // 便捷方法
  trace(category: LogCategory, message: string, data?: any) {
    this.log('trace', category, message, data);
  }

  debug(category: LogCategory, message: string, data?: any) {
    this.log('debug', category, message, data);
  }

  info(category: LogCategory, message: string, data?: any) {
    this.log('info', category, message, data);
  }

  warn(category: LogCategory, message: string, data?: any) {
    this.log('warn', category, message, data);
  }

  error(category: LogCategory, message: string, data?: any) {
    this.log('error', category, message, data);
  }

  // 专用方法 - 数据流相关
  streamReceive(chunk: any, metadata?: any) {
    this.info('stream', '接收数据流', { chunk, metadata });
  }

  streamSend(data: any, metadata?: any) {
    this.info('stream', '发送数据', { data, metadata });
  }

  streamError(error: string, context?: any) {
    this.error('stream', '数据流错误', { error, context });
  }

  // 认证相关
  authLogin(username: string, success: boolean) {
    this.info('auth', `登录尝试: ${username}`, { success });
  }

  authToken(token: string | null, action: string) {
    this.debug('auth', `Token ${action}`, { hasToken: !!token });
  }

  // 网络相关
  networkRequest(url: string, method: string, headers?: any) {
    this.debug('network', `请求: ${method} ${url}`, { headers });
  }

  networkResponse(url: string, status: number, data?: any) {
    this.debug('network', `响应: ${status} ${url}`, { data });
  }

  networkError(url: string, error: string) {
    this.error('network', `网络错误: ${url}`, { error });
  }

  // UI相关
  uiRender(component: string, props?: any) {
    this.debug('ui', `组件渲染: ${component}`, { props });
  }

  uiAction(action: string, data?: any) {
    this.info('ui', `用户操作: ${action}`, { data });
  }

  uiError(component: string, error: string) {
    this.error('ui', `UI错误: ${component}`, { error });
  }

  // 状态管理
  stateUpdate(store: string, action: string, payload?: any) {
    this.debug('state', `状态更新: ${store}`, { action, payload });
  }

  // 获取所有日志
  getLogs(): LogEntry[] {
    return [...this.logs];
  }

  // 清空日志
  clear() {
    this.logs = [];
    log.info('[LOGGER] 日志已清空');
  }
  
  // 销毁方法，用于清理资源
  destroy() {
    // 禁用自动保存
    this.disableAutoSave();
    
    // 在销毁前尝试保存剩余日志
    this.saveLogsToServer();
    
    this.info('general', '日志系统已销毁');
  }

  // 获取统计信息
  getStats() {
    const stats = {
      total: this.logs.length,
      byLevel: {} as Record<LogLevel, number>,
      byCategory: {} as Record<LogCategory, number>
    };

    for (const entry of this.logs) {
      stats.byLevel[entry.level] = (stats.byLevel[entry.level] || 0) + 1;
      stats.byCategory[entry.category] = (stats.byCategory[entry.category] || 0) + 1;
    }

    return stats;
  }

  // 导出为JSON格式
  exportToJSON(filename?: string): void {
    const data = {
      exportTime: new Date().toISOString(),
      stats: this.getStats(),
      logs: this.logs
    };

    const jsonString = JSON.stringify(data, null, 2);
    const blob = new Blob([jsonString], { type: 'application/json' });
    const fileName = filename || `jd-agent-logs-${new Date().toISOString().split('T')[0]}.json`;
    
    saveAs(blob, fileName);
  }

  // 导出为文本格式
  exportToText(filename?: string): void {
    const textContent = this.logs.map(entry => {
      const dataStr = entry.data ? `\n数据: ${JSON.stringify(entry.data, null, 2)}` : '';
      return `[${entry.timestamp}] [${entry.level.toUpperCase()}] [${entry.category.toUpperCase()}] ${entry.message}${dataStr}`;
    }).join('\n');

    const blob = new Blob([textContent], { type: 'text/plain;charset=utf-8' });
    const fileName = filename || `jd-agent-logs-${new Date().toISOString().split('T')[0]}.txt`;
    
    saveAs(blob, fileName);
  }

  // 导出为CSV格式
  exportToCSV(filename?: string): void {
    const headers = ['Timestamp', 'Level', 'Category', 'Message', 'Data'];
    const rows = this.logs.map(entry => [
      entry.timestamp,
      entry.level,
      entry.category,
      entry.message,
      entry.data ? JSON.stringify(entry.data).replace(/"/g, '""') : ''
    ]);

    const csvContent = [headers, ...rows]
      .map(row => row.map(field => `"${field}"`).join(','))
      .join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8' });
    const fileName = filename || `jd-agent-logs-${new Date().toISOString().split('T')[0]}.csv`;
    
    saveAs(blob, fileName);
  }

  // 导出统计报告
  exportStatsReport(filename?: string): void {
    const stats = this.getStats();
    const report = `
# JD Agent 日志分析报告

**生成时间**: ${new Date().toISOString()}

## 总体统计

- **日志总数**: ${stats.total}

## 按级别分布

${Object.entries(stats.byLevel).map(([level, count]) => `- ${level}: ${count}`).join('\n')}

## 按类别分布

${Object.entries(stats.byCategory).map(([category, count]) => `- ${category}: ${count}`).join('\n')}

## 最近10条日志

${this.logs.slice(-10).map(entry => 
  `- [${entry.timestamp}] [${entry.level.toUpperCase()}] [${entry.category.toUpperCase()}] ${entry.message}`
).join('\n')}
    `.trim();

    const blob = new Blob([report], { type: 'text/markdown;charset=utf-8' });
    const fileName = filename || `jd-agent-stats-${new Date().toISOString().split('T')[0]}.md`;
    
    saveAs(blob, fileName);
  }

  // 设置日志保存位置
  setStorageLocation(localStorage: boolean = true) {
    // 这里可以实现将日志保存到localStorage或其他存储方式
    if (localStorage) {
      this.saveToLocalStorage();
    }
  }

  private saveToLocalStorage() {
    if (typeof window !== 'undefined') {
      try {
        const data = {
          timestamp: Date.now(),
          logs: this.logs
        };
        localStorage.setItem('jd-agent-logs', JSON.stringify(data));
      } catch (e) {
        this.error('general', '保存日志到localStorage失败', { error: e });
      }
    }
  }

  // 从localStorage恢复日志
  restoreFromLocalStorage(): boolean {
    if (typeof window !== 'undefined') {
      try {
        const data = localStorage.getItem('jd-agent-logs');
        if (data) {
          const parsed = JSON.parse(data);
          // 检查是否是最近的日志（24小时内）
          if (Date.now() - parsed.timestamp < 24 * 60 * 60 * 1000) {
            this.logs = parsed.logs || [];
            this.info('general', '从本地存储恢复日志', { count: this.logs.length });
            return true;
          }
        }
      } catch (e) {
        this.error('general', '从localStorage恢复日志失败', { error: e });
      }
    }
    return false;
  }
}

// 创建全局日志实例
export const logger = new FileLogger();

// 设置默认日志级别
logger.setLevel('debug');

// 自动恢复日志
if (typeof window !== 'undefined') {
  logger.restoreFromLocalStorage();
}

// 导出便捷方法
export const {
  trace,
  debug,
  info,
  warn,
  error,
  streamReceive,
  streamSend,
  streamError,
  authLogin,
  authToken,
  networkRequest,
  networkResponse,
  networkError,
  uiRender,
  uiAction,
  uiError,
  stateUpdate,
  getLogs,
  clear,
  getStats,
  exportToJSON,
  exportToText,
  exportToCSV,
  exportStatsReport,
  setStorageLocation
} = logger;