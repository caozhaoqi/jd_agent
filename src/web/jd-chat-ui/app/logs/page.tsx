"use client";

import { useState, useEffect } from 'react';
import { logger } from '@/utils/logger';
import LogViewer from '@/components/LogViewer';

export default function LogsPage() {
  const [isAutoSaveEnabled, setIsAutoSaveEnabled] = useState(true);
  const [autoSaveInterval, setAutoSaveInterval] = useState(30000); // 30 seconds
  const [isServerConnected, setIsServerConnected] = useState(false);
  const [testLogCount, setTestLogCount] = useState(0);

  useEffect(() => {
    // Check server connection
    checkServerConnection();

    // Generate some initial test logs
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
    // Generate test logs only in development
    if (process.env.NODE_ENV === 'development') {
      logger.info('general', 'Log System Test Page Loaded');
      logger.debug('ui', 'Generating Test Logs', { timestamp: new Date().toISOString() });
      logger.warn('network', 'This is a test warning log', { test: true });

      // Simulate stream logs
      logger.streamReceive({ chunk: 'test_chunk_1' }, { size: 100 });
      logger.streamSend({ message: 'Test send data' }, { type: 'test' });

      // Simulate auth logs
      logger.authLogin('test_user', true);
      logger.authToken('test_token_123', 'Set');

      // Simulate state update logs
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

      logger[level](category, `Randomly generated test log #${testLogCount + i + 1}`, {
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
    logger.info('general', 'Manual Log Save');
    await logger.saveLogsManually();
  };

  const getCurrentStats = () => {
    return logger.getStats();
  };

  return (
    <div className="h-screen overflow-y-auto bg-gray-50 py-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Page Title */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">📊 Log System Test Page</h1>
          <p className="text-gray-600">Test and debug JD Agent's logging functionality</p>
        </div>

        {/* System Status Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <div className={`w-3 h-3 rounded-full ${isServerConnected ? 'bg-green-400' : 'bg-red-400'}`}></div>
              </div>
              <div className="ml-4">
                <h3 className="text-lg font-medium text-gray-900">Server Connection</h3>
                <p className="text-sm text-gray-600">
                  {isServerConnected ? 'Connected' : 'Not Connected'}
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
                <h3 className="text-lg font-medium text-gray-900">Auto Save</h3>
                <p className="text-sm text-gray-600">
                  {isAutoSaveEnabled ? 'Enabled' : 'Disabled'}
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
                <h3 className="text-lg font-medium text-gray-900">Test Logs Count</h3>
                <p className="text-sm text-gray-600">{testLogCount} Logs</p>
              </div>
            </div>
          </div>
        </div>

        {/* Control Panel */}
        <div className="bg-white rounded-lg shadow mb-8">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-xl font-semibold text-gray-900">🎛️ Log Control Panel</h2>
          </div>
          <div className="p-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Auto Save Controls */}
              <div className="space-y-4">
                <h3 className="text-lg font-medium text-gray-900">Auto Save Settings</h3>

                <div className="flex items-center space-x-3">
                  <input
                    type="checkbox"
                    id="autoSave"
                    checked={isAutoSaveEnabled}
                    onChange={handleToggleAutoSave}
                    className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                  />
                  <label htmlFor="autoSave" className="text-sm font-medium text-gray-700">
                    Enable Auto Save
                  </label>
                </div>

                {isAutoSaveEnabled && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Auto Save Interval
                    </label>
                    <select
                      value={autoSaveInterval}
                      onChange={(e) => handleIntervalChange(Number(e.target.value))}
                      className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                    >
                      <option value={10000}>10 seconds</option>
                      <option value={30000}>30 seconds</option>
                      <option value={60000}>1 minute</option>
                      <option value={300000}>5 minutes</option>
                    </select>
                  </div>
                )}

                <button
                  onClick={handleManualSave}
                  className="w-full bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  Manual Save Logs
                </button>
              </div>

              {/* Test Functions */}
              <div className="space-y-4">
                <h3 className="text-lg font-medium text-gray-900">Test Functions</h3>

                <button
                  onClick={handleGenerateMoreLogs}
                  className="w-full bg-green-600 text-white py-2 px-4 rounded-md hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500"
                >
                  Generate More Test Logs
                </button>

                <button
                  onClick={checkServerConnection}
                  className="w-full bg-purple-600 text-white py-2 px-4 rounded-md hover:bg-purple-700 focus:outline-none focus:ring-2 focus:ring-purple-500"
                >
                  Test Server Connection
                </button>

                <div className="text-sm text-gray-600 space-y-1">
                  <p>📊 Current Statistics:</p>
                  <p>• Total Logs: {getCurrentStats().total}</p>
                  <p>• Error Logs: {getCurrentStats().byLevel.error || 0}</p>
                  <p>• Info Logs: {getCurrentStats().byLevel.info || 0}</p>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Log Viewer */}
        <div className="bg-white rounded-lg shadow">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-xl font-semibold text-gray-900">📋 Log Viewer</h2>
          </div>
          <div className="p-6">
            <LogViewer />
          </div>
        </div>

        {/* Usage Instructions */}
        <div className="mt-8 bg-blue-50 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-blue-900 mb-3">📖 Usage Instructions</h3>
          <div className="text-sm text-blue-800 space-y-2">
            <p>• <strong>Generate Test Logs</strong>: Click the button to generate random test logs to verify the logging system</p>
            <p>• <strong>Auto Save</strong>: Automatically saves logs to the server at specified intervals when enabled</p>
            <p>• <strong>Manual Save</strong>: Immediately saves all current logs to the server</p>
            <p>• <strong>Log Viewer</strong>: View, filter, and export logs using the viewer below</p>
            <p>• <strong>Export Function</strong>: Supports export in JSON, CSV, Text, and Stats Report formats</p>
            <p>• <strong>Server Connection</strong>: Checks the connection status with the backend logging API</p>
          </div>
        </div>
      </div>
    </div>
  );
}