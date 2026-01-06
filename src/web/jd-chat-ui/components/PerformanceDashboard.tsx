"use client";

import { useEffect, useState } from 'react';
import { XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area } from 'recharts';

interface PerformanceMetrics {
  cpu: {
    usage_percent: number;
    count: number;
    frequency: {
      current: number;
      min: number;
      max: number;
    } | null;
  };
  memory: {
    total_bytes: number;
    available_bytes: number;
    used_bytes: number;
    percent: number;
  };
  disk: {
    total_bytes: number;
    used_bytes: number;
    free_bytes: number;
    percent: number;
  };
  process: {
    memory_rss_bytes: number;
    cpu_percent: number;
    num_threads: number;
  };
}

interface AppMetrics {
  api: {
    total_requests: number;
    avg_duration: number;
  };
  cache: {
    hits: number;
    misses: number;
  };
  llm: {
    total_calls: number;
    avg_duration: number;
  };
}

export default function PerformanceDashboard({ className = "" }: { className?: string }) {
  const [systemMetrics, setSystemMetrics] = useState<PerformanceMetrics | null>(null);
  const [appMetrics, setAppMetrics] = useState<AppMetrics | null>(null);
  const [cpuHistory, setCpuHistory] = useState<{ time: string; value: number }[]>([]);
  const [memoryHistory, setMemoryHistory] = useState<{ time: string; value: number }[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());

  const fetchMetrics = async () => {
    try {
      const [systemRes, appRes] = await Promise.all([
        fetch('/api/v1/monitoring/system'),
        fetch('/api/v1/monitoring/performance')
      ]);

      const systemData = await systemRes.json();
      const appData = await appRes.json();

      setSystemMetrics(systemData);
      setAppMetrics(appData);
      setLastUpdate(new Date());

      const now = new Date();
      const timeStr = now.toLocaleTimeString('zh-CN');

      setCpuHistory(prev => {
        const newHistory = [...prev, { time: timeStr, value: systemData.cpu.usage_percent }];
        return newHistory.slice(-30);
      });

      setMemoryHistory(prev => {
        const newHistory = [...prev, { time: timeStr, value: systemData.memory.percent }];
        return newHistory.slice(-30);
      });

      setIsLoading(false);
    } catch (error) {
      console.error('Failed to fetch metrics:', error);
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchMetrics();
    const interval = setInterval(fetchMetrics, 5000);
    return () => clearInterval(interval);
  }, []);

  const formatBytes = (bytes: number) => {
    const gb = bytes / (1024 * 1024 * 1024);
    return `${gb.toFixed(2)} GB`;
  };

  return (
    <div className={`bg-gray-900 rounded-xl p-6 text-white ${className}`}>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-bold flex items-center gap-2">
          📊 性能监控仪表板
        </h2>
        <div className="text-sm text-gray-400">
          最后更新: {lastUpdate.toLocaleTimeString('zh-CN')}
        </div>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-white"></div>
        </div>
      ) : (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <MetricCard
              title="CPU 使用率"
              value={systemMetrics?.cpu.usage_percent?.toFixed(1) ?? '0.0'}
              unit="%"
              color={(systemMetrics?.cpu.usage_percent ?? 0) > 80 ? 'red' : 'blue'}
              trend={cpuHistory.length > 1 ? cpuHistory[cpuHistory.length - 1].value - cpuHistory[0].value : 0}
            />
            <MetricCard
              title="内存使用率"
              value={systemMetrics?.memory.percent?.toFixed(1) ?? '0.0'}
              unit="%"
              color={(systemMetrics?.memory.percent ?? 0) > 80 ? 'red' : 'green'}
              trend={memoryHistory.length > 1 ? memoryHistory[memoryHistory.length - 1].value - memoryHistory[0].value : 0}
            />
            <MetricCard
              title="磁盘使用率"
              value={systemMetrics?.disk.percent?.toFixed(1) ?? '0.0'}
              unit="%"
              color={(systemMetrics?.disk.percent ?? 0) > 80 ? 'red' : 'yellow'}
            />
            <MetricCard
              title="进程内存"
              value={formatBytes(systemMetrics?.process.memory_rss_bytes ?? 0)}
            />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="bg-gray-800 rounded-lg p-4">
              <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                🖥️ CPU 使用率趋势
              </h3>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={cpuHistory}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                    <XAxis dataKey="time" stroke="#9CA3AF" fontSize={12} />
                    <YAxis stroke="#9CA3AF" fontSize={12} domain={[0, 100]} />
                    <Tooltip
                      contentStyle={{ backgroundColor: '#1F2937', border: 'none', borderRadius: '8px' }}
                      labelStyle={{ color: '#9CA3AF' }}
                    />
                    <Area
                      type="monotone"
                      dataKey="value"
                      stroke="#3B82F6"
                      fill="#3B82F6"
                      fillOpacity={0.3}
                      strokeWidth={2}
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="bg-gray-800 rounded-lg p-4">
              <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                🧠 内存使用率趋势
              </h3>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={memoryHistory}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                    <XAxis dataKey="time" stroke="#9CA3AF" fontSize={12} />
                    <YAxis stroke="#9CA3AF" fontSize={12} domain={[0, 100]} />
                    <Tooltip
                      contentStyle={{ backgroundColor: '#1F2937', border: 'none', borderRadius: '8px' }}
                      labelStyle={{ color: '#9CA3AF' }}
                    />
                    <Area
                      type="monotone"
                      dataKey="value"
                      stroke="#10B981"
                      fill="#10B981"
                      fillOpacity={0.3}
                      strokeWidth={2}
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            <div className="bg-gray-800 rounded-lg p-4">
              <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                🔗 API 性能
              </h3>
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-gray-400">总请求数</span>
                  <span className="font-mono">{appMetrics?.api.total_requests?.toLocaleString() || 0}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">平均延迟</span>
                  <span className="font-mono">{(appMetrics?.api.avg_duration || 0).toFixed(3)}s</span>
                </div>
              </div>
            </div>

            <div className="bg-gray-800 rounded-lg p-4">
              <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                💾 缓存状态
              </h3>
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-gray-400">缓存命中</span>
                  <span className="font-mono text-green-400">{appMetrics?.cache.hits || 0}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">缓存未命中</span>
                  <span className="font-mono text-red-400">{appMetrics?.cache.misses || 0}</span>
                </div>
                <div className="mt-2 pt-2 border-t border-gray-700">
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-400">命中率</span>
                    <span className="font-mono">
                      {((appMetrics?.cache.hits || 0) / ((appMetrics?.cache.hits || 0) + (appMetrics?.cache.misses || 0)) * 100).toFixed(1)}%
                    </span>
                  </div>
                </div>
              </div>
            </div>

            <div className="bg-gray-800 rounded-lg p-4">
              <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                🤖 LLM 调用
              </h3>
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-gray-400">总调用次数</span>
                  <span className="font-mono">{appMetrics?.llm.total_calls || 0}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">平均响应时间</span>
                  <span className="font-mono">{(appMetrics?.llm.avg_duration || 0).toFixed(3)}s</span>
                </div>
              </div>
            </div>
          </div>

          <div className="flex items-center justify-between pt-4 border-t border-gray-700">
            <div className="flex items-center gap-4 text-sm text-gray-400">
              <span className="flex items-center gap-1">
                <span className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></span>
                监控中
              </span>
              <span>自动刷新: 5秒</span>
            </div>
            <button
              onClick={fetchMetrics}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-500 rounded-lg text-sm transition-colors"
            >
              立即刷新
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

interface MetricCardProps {
  title: string;
  value: string | number | undefined | null;
  unit?: string;
  color?: 'blue' | 'green' | 'red' | 'yellow';
  trend?: number;
}

function MetricCard({ title, value, unit = '', color = 'blue', trend = 0 }: MetricCardProps) {
  const colorClasses = {
    blue: 'border-blue-500 bg-blue-500/10 text-blue-400',
    green: 'border-green-500 bg-green-500/10 text-green-400',
    red: 'border-red-500 bg-red-500/10 text-red-400',
    yellow: 'border-yellow-500 bg-yellow-500/10 text-yellow-400'
  };

  const displayValue = value ?? '--';

  return (
    <div className={`bg-gray-800 rounded-lg p-4 border-l-4 ${colorClasses[color]}`}>
      <div className="flex items-center justify-between">
        <div>
          <div className="text-gray-400 text-sm">{title}</div>
          <div className="text-2xl font-bold mt-1">
            {displayValue}
            {unit && <span className="text-sm font-normal ml-1">{unit}</span>}
          </div>
        </div>
        {trend !== 0 && (
          <div className={`text-sm ${trend > 0 ? 'text-red-400' : 'text-green-400'}`}>
            {trend > 0 ? '↑' : '↓'} {Math.abs(trend).toFixed(1)}%
          </div>
        )}
      </div>
    </div>
  );
}
