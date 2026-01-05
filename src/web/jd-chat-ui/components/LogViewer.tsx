"use client";

import { useState, useEffect } from 'react';
import { logger } from '@/utils/logger';

const API_BASE = "http://localhost:8000/api/v1";

export type LogFilter = {
  level?: string;
  category?: string;
  startDate?: Date;
  endDate?: Date;
  searchText?: string;
};

export type ExportFormat = 'json' | 'csv' | 'text' | 'stats';

export default function LogViewer() {
  const [logs, setLogs] = useState(logger.getLogs());
  const [filteredLogs, setFilteredLogs] = useState(logs);
  const [filter, setFilter] = useState<LogFilter>({});
  const [showFilters, setShowFilters] = useState(false);
  const [serverLogs, setServerLogs] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [logStats, setLogStats] = useState(logger.getStats());

  // 获取日志
  useEffect(() => {
    setLogs(logger.getLogs());
    setFilteredLogs(logger.getLogs());
    setLogStats(logger.getStats());
    
    // 设置定期更新日志
    const interval = setInterval(() => {
      setLogs(logger.getLogs());
      setLogStats(logger.getStats());
    }, 2000); // 每2秒更新一次
    
    return () => clearInterval(interval);
  }, []);

  // 应用过滤
  useEffect(() => {
    applyFilters();
  }, [filter, logs]);

  const applyFilters = () => {
    let result = [...logs];
    
    // 按级别过滤
    if (filter.level) {
      result = result.filter(log => log.level === filter.level);
    }
    
    // 按类别过滤
    if (filter.category) {
      result = result.filter(log => log.category === filter.category);
    }
    
    // 按日期范围过滤
    if (filter.startDate) {
      result = result.filter(log => new Date(log.timestamp) >= filter.startDate!);
    }
    
    if (filter.endDate) {
      result = result.filter(log => new Date(log.timestamp) <= filter.endDate!);
    }
    
    // 按搜索文本过滤
    if (filter.searchText) {
      const searchText = filter.searchText.toLowerCase();
      result = result.filter(log => 
        log.message.toLowerCase().includes(searchText) || 
        (log.data && JSON.stringify(log.data).toLowerCase().includes(searchText))
      );
    }
    
    setFilteredLogs(result);
  };

  const handleFilterChange = (key: keyof LogFilter, value: any) => {
    setFilter(prev => ({ ...prev, [key]: value }));
  };

  const clearFilters = () => {
    setFilter({});
  };

  const exportLogs = async (format: ExportFormat) => {
    const filename = `jd-agent-logs-${new Date().toISOString().split('T')[0]}`;
    
    try {
      switch (format) {
        case 'json':
          logger.exportToJSON(filename);
          break;
        case 'csv':
          logger.exportToCSV(filename);
          break;
        case 'text':
          logger.exportToText(filename);
          break;
        case 'stats':
          logger.exportStatsReport(filename);
          break;
      }
    } catch (error) {
      console.error(`导出 ${format} 格式日志失败:`, error);
    }
  };

  const exportServerLogs = async (format: ExportFormat) => {
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE}/logs/list`);
      const data = await response.json();
      
      if (data.status === 'success' && data.files && data.files.length > 0) {
        // 获取最新日志文件
        const latestLogFile = data.files[0];
        
        const downloadResponse = await fetch(`${API_BASE}/logs/download/${latestLogFile.filename}`);
        const downloadData = await downloadResponse.json();
        
        if (downloadData.status === 'success') {
          const logsData = JSON.parse(downloadData.content);
          const blob = new Blob([JSON.stringify(logsData, null, 2)], { type: 'application/json' });
          const url = URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = url;
          a.download = `server-logs-${new Date().toISOString().split('T')[0]}.json`;
          document.body.appendChild(a);
          a.click();
          document.body.removeChild(a);
          URL.revokeObjectURL(url);
        }
      } else {
        alert('没有找到服务器日志文件');
      }
    } catch (error) {
      console.error('导出服务器日志失败:', error);
      alert('导出服务器日志失败');
    } finally {
      setLoading(false);
    }
  };

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    return `${date.toLocaleDateString()} ${date.toLocaleTimeString()}`;
  };

  return (
    <div className="p-4 border rounded-lg bg-white dark:bg-gray-800 shadow-md">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-xl font-bold">日志查看器</h2>
        <div className="flex gap-2">
          <button 
            onClick={() => setShowFilters(!showFilters)}
            className="px-3 py-1 bg-blue-500 text-white rounded hover:bg-blue-600"
          >
            {showFilters ? '隐藏过滤器' : '显示过滤器'}
          </button>
          <button 
            onClick={() => logger.clear()}
            className="px-3 py-1 bg-red-500 text-white rounded hover:bg-red-600"
          >
            清空日志
          </button>
        </div>
      </div>
      
      {showFilters && (
        <div className="mb-4 p-3 bg-gray-100 dark:bg-gray-700 rounded">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-3">
            <div>
              <label className="block text-sm font-medium mb-1">级别</label>
              <select 
                value={filter.level || ''} 
                onChange={e => handleFilterChange('level', e.target.value || undefined)}
                className="w-full px-2 py-1 border rounded"
              >
                <option value="">全部</option>
                <option value="trace">Trace</option>
                <option value="debug">Debug</option>
                <option value="info">Info</option>
                <option value="warn">Warn</option>
                <option value="error">Error</option>
              </select>
            </div>
            
            <div>
              <label className="block text-sm font-medium mb-1">类别</label>
              <select 
                value={filter.category || ''} 
                onChange={e => handleFilterChange('category', e.target.value || undefined)}
                className="w-full px-2 py-1 border rounded"
              >
                <option value="">全部</option>
                <option value="stream">Stream</option>
                <option value="auth">Auth</option>
                <option value="ui">UI</option>
                <option value="network">Network</option>
                <option value="state">State</option>
                <option value="component">Component</option>
                <option value="general">General</option>
              </select>
            </div>
            
            <div>
              <label className="block text-sm font-medium mb-1">搜索文本</label>
              <input 
                type="text" 
                value={filter.searchText || ''} 
                onChange={e => handleFilterChange('searchText', e.target.value || undefined)}
                placeholder="搜索..."
                className="w-full px-2 py-1 border rounded"
              />
            </div>
          </div>
          
          <div className="flex justify-between">
            <button 
              onClick={clearFilters}
              className="px-3 py-1 bg-gray-300 text-gray-800 rounded hover:bg-gray-400"
            >
              清除过滤器
            </button>
            
            <div className="text-sm">
              <span>显示 {filteredLogs.length} / {logs.length} 条日志</span>
            </div>
          </div>
        </div>
      )}
      
      <div className="mb-4">
        <h3 className="text-lg font-semibold mb-2">日志统计</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="p-3 bg-blue-50 dark:bg-blue-900 rounded">
            <div className="text-sm text-gray-500">总日志数</div>
            <div className="text-xl font-bold">{logStats.total}</div>
          </div>
          <div className="p-3 bg-green-50 dark:bg-green-900 rounded">
            <div className="text-sm text-gray-500">Info 级别</div>
            <div className="text-xl font-bold">{logStats.byLevel.info || 0}</div>
          </div>
          <div className="p-3 bg-yellow-50 dark:bg-yellow-900 rounded">
            <div className="text-sm text-gray-500">Warn 级别</div>
            <div className="text-xl font-bold">{logStats.byLevel.warn || 0}</div>
          </div>
          <div className="p-3 bg-red-50 dark:bg-red-900 rounded">
            <div className="text-sm text-gray-500">Error 级别</div>
            <div className="text-xl font-bold">{logStats.byLevel.error || 0}</div>
          </div>
        </div>
      </div>
      
      <div className="mb-4">
        <h3 className="text-lg font-semibold mb-2">导出日志</h3>
        <div className="flex flex-wrap gap-2">
          <button 
            onClick={() => exportLogs('json')}
            className="px-3 py-1 bg-blue-500 text-white rounded hover:bg-blue-600"
          >
            导出 JSON
          </button>
          <button 
            onClick={() => exportLogs('csv')}
            className="px-3 py-1 bg-blue-500 text-white rounded hover:bg-blue-600"
          >
            导出 CSV
          </button>
          <button 
            onClick={() => exportLogs('text')}
            className="px-3 py-1 bg-blue-500 text-white rounded hover:bg-blue-600"
          >
            导出文本
          </button>
          <button 
            onClick={() => exportLogs('stats')}
            className="px-3 py-1 bg-blue-500 text-white rounded hover:bg-blue-600"
          >
            导出统计报告
          </button>
          <button 
            onClick={() => exportServerLogs('json')}
            disabled={loading}
            className="px-3 py-1 bg-green-500 text-white rounded hover:bg-green-600 disabled:opacity-50"
          >
            {loading ? '获取中...' : '获取服务器日志'}
          </button>
        </div>
      </div>
      
      <div className="max-h-96 overflow-auto">
        <table className="w-full border-collapse">
          <thead>
            <tr className="bg-gray-100 dark:bg-gray-700">
              <th className="border p-2 text-left">时间</th>
              <th className="border p-2 text-left">级别</th>
              <th className="border p-2 text-left">类别</th>
              <th className="border p-2 text-left">消息</th>
            </tr>
          </thead>
          <tbody>
            {filteredLogs.length === 0 ? (
              <tr>
                <td colSpan={4} className="border p-2 text-center">没有找到匹配的日志</td>
              </tr>
            ) : (
              filteredLogs.slice().reverse().map((log, index) => (
                <tr key={index} className={`${log.level === 'error' ? 'bg-red-50 dark:bg-red-900' : ''} ${log.level === 'warn' ? 'bg-yellow-50 dark:bg-yellow-900' : ''}`}>
                  <td className="border p-2 text-xs">{formatTimestamp(log.timestamp)}</td>
                  <td className="border p-2 text-xs">
                    <span className={`px-2 py-1 rounded text-white text-xs ${
                      log.level === 'error' ? 'bg-red-500' : 
                      log.level === 'warn' ? 'bg-yellow-500' : 
                      log.level === 'info' ? 'bg-blue-500' : 
                      log.level === 'debug' ? 'bg-green-500' : 'bg-gray-500'
                    }`}>
                      {log.level.toUpperCase()}
                    </span>
                  </td>
                  <td className="border p-2 text-xs">{log.category}</td>
                  <td className="border p-2 text-xs">{log.message}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}