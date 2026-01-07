"use client";

import { useState, useEffect } from 'react';
import { logger } from '@/utils/logger';
import LogViewer from '@/components/LogViewer';

export default function LogsPage() {
  const [isAutoSaveEnabled, setIsAutoSaveEnabled] = useState(true);
  const [autoSaveInterval, setAutoSaveInterval] = useState(30000); // 30秒
  const [isServerConnected, setIsServerConnected] = useState(false);
  const [testLogCount, setTestLogCount] = useState(0);

  useEffect(() => {
    // 检查服务器连接
    checkServerConnection();
    
    // 生成一些测试日志
    generateTestLogs();
  }, []);

  const checkServerConnection = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/v1/logs/list');
      setIsServerConnected(response.ok);
    } catch (error) {
      setIsServerConnected(false);
    }
  };

  const generateTestLogs = () => {
    // 生成测试日志（仅在开发环境）
    if (process.env.NODE_ENV === 'development') {
      logger.info('general', '日志系统测试页面已加载');
      logger.debug('ui', '生成测试日志功能', { timestamp: new Date().toISOString() });
      logger.warn('network', '这是一个测试警告日志', { test: true });
      
      // 模拟数据流日志
      logger.streamReceive({ chunk: 'test_chunk_1' }, { size: 100 });
      logger.streamSend({ message: '测试发送数据' }, { type: 'test' });
      
      // 模拟认证日志
      logger.authLogin('test_user', true);
      logger.authToken('test_token_123', '已设置');
      
      // 模拟状态更新日志
      logger.stateUpdate('test_store', 'SET_USER', { userId: '123' });
      
      setTestLogCount(7);
    }
  };

  const handleGenerateMoreLogs = () => {
    const count = Math.floor(Math.random() * 5) + 1;
    for (let i = 0; i < count; i++) {
      const levels = ['trace', 'debug', 'info', 'warn', 'error'] as const;
      const categories = ['stream', 'auth', 'ui', 'network', 'state', 'general'] as const;
      const level = levels[Math.floor(Math.random() * levels.length)];
      const category = categories[Math.floor(Math.random() * categories.length)];
      
      logger[level](category, `随机生成的测试日志 #${testLogCount + i + 1}`, {
        randomData: Math.random(),
        timestamp: new Date().toISOString()
      });
    }
    setTestLogCount(prev => prev + count);
  };

  const handleToggleAutoSave = () => {
    if (isAutoSaveEnabled) {
      logger.disableAutoSave();
      setIsAutoSaveEnabled(false);
    } else {
      logger.enableAutoSave(autoSaveInterval);
      setIsAutoSaveEnabled(true);
    }
  };

  const handleIntervalChange = (interval: number) => {
    setAutoSaveInterval(interval);
    if (isAutoSaveEnabled) {
      logger.disableAutoSave();
      logger.enableAutoSave(interval);
    }
  };

  const handleManualSave = async () => {
    logger.info('general', '手动保存日志');
    await logger.saveLogsManually();
  };

  const getCurrentStats = () => {
    return logger.getStats();
  };

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* 页面标题 */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">📊 日志系统测试页面</h1>
          <p className="text-gray-600">测试和调试JD Agent的日志功能</p>
        </div>

        {/* 系统状态卡片 */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <div className={`w-3 h-3 rounded-full ${isServerConnected ? 'bg-green-400' : 'bg-red-400'}`}></div>
              </div>
              <div className="ml-4">
                <h3 className="text-lg font-medium text-gray-900">服务器连接</h3>
                <p className="text-sm text-gray-600">
                  {isServerConnected ? '已连接' : '未连接'}
                </p>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <div className={`w-3 h-3 rounded-full ${isAutoSaveEnabled ? 'bg-blue-400' : 'bg-gray-400'}`}></div>
              </div>
              <div className="ml-4">
                <h3 className="text-lg font-medium text-gray-900">自动保存</h3>
                <p className="text-sm text-gray-600">
                  {isAutoSaveEnabled ? '已启用' : '已禁用'}
                </p>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <span className="text-2xl">📝</span>
              </div>
              <div className="ml-4">
                <h3 className="text-lg font-medium text-gray-900">测试日志数量</h3>
                <p className="text-sm text-gray-600">{testLogCount} 条</p>
              </div>
            </div>
          </div>
        </div>

        {/* 控制面板 */}
        <div className="bg-white rounded-lg shadow mb-8">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-xl font-semibold text-gray-900">🎛️ 日志控制面板</h2>
          </div>
          <div className="p-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* 自动保存控制 */}
              <div className="space-y-4">
                <h3 className="text-lg font-medium text-gray-900">自动保存设置</h3>
                
                <div className="flex items-center space-x-3">
                  <input
                    type="checkbox"
                    id="autoSave"
                    checked={isAutoSaveEnabled}
                    onChange={handleToggleAutoSave}
                    className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                  />
                  <label htmlFor="autoSave" className="text-sm font-medium text-gray-700">
                    启用自动保存
                  </label>
                </div>

                {isAutoSaveEnabled && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      自动保存间隔
                    </label>
                    <select
                      value={autoSaveInterval}
                      onChange={(e) => handleIntervalChange(Number(e.target.value))}
                      className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                    >
                      <option value={10000}>10秒</option>
                      <option value={30000}>30秒</option>
                      <option value={60000}>1分钟</option>
                      <option value={300000}>5分钟</option>
                    </select>
                  </div>
                )}

                <button
                  onClick={handleManualSave}
                  className="w-full bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  手动保存日志
                </button>
              </div>

              {/* 测试功能 */}
              <div className="space-y-4">
                <h3 className="text-lg font-medium text-gray-900">测试功能</h3>
                
                <button
                  onClick={handleGenerateMoreLogs}
                  className="w-full bg-green-600 text-white py-2 px-4 rounded-md hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500"
                >
                  生成更多测试日志
                </button>

                <button
                  onClick={checkServerConnection}
                  className="w-full bg-purple-600 text-white py-2 px-4 rounded-md hover:bg-purple-700 focus:outline-none focus:ring-2 focus:ring-purple-500"
                >
                  测试服务器连接
                </button>

                <div className="text-sm text-gray-600 space-y-1">
                  <p>📊 当前统计信息：</p>
                  <p>• 总日志数：{getCurrentStats().total}</p>
                  <p>• 错误日志：{getCurrentStats().byLevel.error || 0}</p>
                  <p>• 信息日志：{getCurrentStats().byLevel.info || 0}</p>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* 日志查看器 */}
        <div className="bg-white rounded-lg shadow">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-xl font-semibold text-gray-900">📋 日志查看器</h2>
          </div>
          <div className="p-6">
            <LogViewer />
          </div>
        </div>

        {/* 使用说明 */}
        <div className="mt-8 bg-blue-50 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-blue-900 mb-3">📖 使用说明</h3>
          <div className="text-sm text-blue-800 space-y-2">
            <p>• <strong>生成测试日志</strong>：点击按钮生成随机测试日志以验证日志系统</p>
            <p>• <strong>自动保存</strong>：启用后会自动将日志保存到服务器，支持多种时间间隔</p>
            <p>• <strong>手动保存</strong>：立即保存当前所有日志到服务器</p>
            <p>• <strong>日志查看</strong>：使用下方的日志查看器查看、过滤和导出日志</p>
            <p>• <strong>导出功能</strong>：支持JSON、CSV、文本和统计报告格式导出</p>
            <p>• <strong>服务器连接</strong>：检查与后端日志API的连接状态</p>
          </div>
        </div>
      </div>
    </div>
  );
}