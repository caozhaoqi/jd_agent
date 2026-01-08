import { useEffect, useState } from 'react';
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import { Loader2, AlertTriangle, CheckCircle2 } from 'lucide-react';

interface MonitoringData {
  timestamp: number;
  cache_stats: {
    total_requests: number;
    hits: number;
    misses: number;
    hit_rate: number;
  };
  redis_info: any;
  query_cache_info: any;
  database_stats: {
    total_sessions: number;
    total_messages: number;
    recent_sessions_24h: number;
  };
}

interface HealthCheckData {
  status: string;
  timestamp: number;
  redis_connected: boolean;
}

export default function MonitoringPage() {
  const [monitoringData, setMonitoringData] = useState<MonitoringData | null>(null);
  const [healthCheck, setHealthCheck] = useState<HealthCheckData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchMonitoringData = async () => {
    try {
      setLoading(true);
      setError(null);

      // Fetch health check
      const healthRes = await fetch('/api/v1/monitoring/health');
      if (!healthRes.ok) throw new Error('Health check failed');
      const healthData = await healthRes.json();
      setHealthCheck(healthData);

      // Fetch monitoring stats
      const statsRes = await fetch('/api/v1/monitoring/dashboard/stats');
      if (!statsRes.ok) throw new Error('Failed to fetch monitoring stats');
      const statsData = await statsRes.json();
      setMonitoringData(statsData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMonitoringData();
    // Refresh every 30 seconds
    const interval = setInterval(fetchMonitoringData, 30000);
    return () => clearInterval(interval);
  }, []);

  // Prepare chart data
  const cacheChartData = monitoringData ? [
    {
      name: 'Cache Hits',
      value: monitoringData.cache_stats.hits,
      color: '#10b981'
    },
    {
      name: 'Cache Misses',
      value: monitoringData.cache_stats.misses,
      color: '#ef4444'
    }
  ] : [];

  const databaseChartData = monitoringData ? [
    {
      name: 'Total Sessions',
      value: monitoringData.database_stats.total_sessions,
      color: '#3b82f6'
    },
    {
      name: 'Recent Sessions (24h)',
      value: monitoringData.database_stats.recent_sessions_24h,
      color: '#8b5cf6'
    },
    {
      name: 'Total Messages',
      value: monitoringData.database_stats.total_messages,
      color: '#ec4899'
    }
  ] : [];

  return (
    <div className="container mx-auto p-4 max-w-7xl">
      <h1 className="text-3xl font-bold text-gray-800 mb-6">性能监控仪表板</h1>

      {/* Health Status */}
      <div className="mb-6 grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white rounded-lg shadow p-4 border-l-4 border-blue-500">
          <h3 className="text-lg font-semibold text-gray-700">系统状态</h3>
          {loading ? (
            <div className="flex items-center mt-2">
              <Loader2 className="h-5 w-5 animate-spin text-blue-500 mr-2" />
              <span className="text-gray-500">检查中...</span>
            </div>
          ) : healthCheck ? (
            <div className="flex items-center mt-2">
              <CheckCircle2 className="h-5 w-5 text-green-500 mr-2" />
              <span className="text-green-600 font-medium">{healthCheck.status}</span>
            </div>
          ) : (
            <div className="flex items-center mt-2">
              <AlertTriangle className="h-5 w-5 text-yellow-500 mr-2" />
              <span className="text-yellow-600">未知</span>
            </div>
          )}
        </div>

        <div className="bg-white rounded-lg shadow p-4 border-l-4 border-red-500">
          <h3 className="text-lg font-semibold text-gray-700">Redis 连接</h3>
          {loading ? (
            <div className="flex items-center mt-2">
              <Loader2 className="h-5 w-5 animate-spin text-red-500 mr-2" />
              <span className="text-gray-500">检查中...</span>
            </div>
          ) : healthCheck ? (
            healthCheck.redis_connected ? (
              <div className="flex items-center mt-2">
                <CheckCircle2 className="h-5 w-5 text-green-500 mr-2" />
                <span className="text-green-600 font-medium">已连接</span>
              </div>
            ) : (
              <div className="flex items-center mt-2">
                <AlertTriangle className="h-5 w-5 text-red-500 mr-2" />
                <span className="text-red-600 font-medium">未连接</span>
              </div>
            )
          ) : null}
        </div>

        <div className="bg-white rounded-lg shadow p-4 border-l-4 border-green-500">
          <h3 className="text-lg font-semibold text-gray-700">缓存命中率</h3>
          {loading ? (
            <div className="flex items-center mt-2">
              <Loader2 className="h-5 w-5 animate-spin text-green-500 mr-2" />
              <span className="text-gray-500">计算中...</span>
            </div>
          ) : monitoringData ? (
            <div className="mt-2">
              <div className="text-2xl font-bold text-green-600">
                {(monitoringData.cache_stats.hit_rate * 100).toFixed(1)}%
              </div>
              <div className="text-sm text-gray-500">
                基于 {monitoringData.cache_stats.total_requests.toLocaleString()} 次请求
              </div>
            </div>
          ) : null}
        </div>
      </div>

      {/* Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Cache Distribution */}
        <div className="bg-white rounded-lg shadow p-4">
          <h2 className="text-xl font-semibold text-gray-700 mb-4">缓存分布</h2>
          {loading ? (
            <div className="flex justify-center items-center h-64">
              <Loader2 className="h-8 w-8 animate-spin text-gray-500" />
            </div>
          ) : cacheChartData.length > 0 ? (
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={cacheChartData}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={100}
                    fill="#8884d8"
                    paddingAngle={5}
                    dataKey="value"
                    label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                  >
                    {cacheChartData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(value) => [value.toLocaleString(), '次数']} />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="flex justify-center items-center h-64 text-gray-500">
              <p>暂无缓存数据</p>
            </div>
          )}
        </div>

        {/* Database Statistics */}
        <div className="bg-white rounded-lg shadow p-4">
          <h2 className="text-xl font-semibold text-gray-700 mb-4">数据库统计</h2>
          {loading ? (
            <div className="flex justify-center items-center h-64">
              <Loader2 className="h-8 w-8 animate-spin text-gray-500" />
            </div>
          ) : databaseChartData.length > 0 ? (
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={databaseChartData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" />
                  <YAxis />
                  <Tooltip formatter={(value) => [value.toLocaleString(), '条记录']} />
                  <Legend />
                  <Bar dataKey="value" name="数量">
                    {databaseChartData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="flex justify-center items-center h-64 text-gray-500">
              <p>暂无数据库统计数据</p>
            </div>
          )}
        </div>
      </div>

      {/* Raw Data */}
      <div className="mt-8 bg-white rounded-lg shadow p-4">
        <h2 className="text-xl font-semibold text-gray-700 mb-4">系统信息</h2>
        {loading ? (
          <div className="flex justify-center items-center h-32">
            <Loader2 className="h-6 w-6 animate-spin text-gray-500" />
          </div>
        ) : monitoringData ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <h3 className="font-medium text-gray-700 mb-2">Redis 信息</h3>
              <pre className="bg-gray-50 p-3 rounded text-sm overflow-x-auto">
                {JSON.stringify(monitoringData.redis_info, null, 2)}
              </pre>
            </div>
            <div>
              <h3 className="font-medium text-gray-700 mb-2">查询缓存信息</h3>
              <pre className="bg-gray-50 p-3 rounded text-sm overflow-x-auto">
                {JSON.stringify(monitoringData.query_cache_info, null, 2)}
              </pre>
            </div>
          </div>
        ) : null}
      </div>

      {/* Error Display */}
      {error && (
        <div className="mt-6 p-4 bg-red-50 border border-red-200 rounded-lg">
          <div className="flex items-center">
            <AlertTriangle className="h-5 w-5 text-red-500 mr-2" />
            <h3 className="font-medium text-red-800">错误</h3>
          </div>
          <div className="mt-2 text-sm text-red-700">
            {error}
          </div>
        </div>
      )}

      {/* Refresh Button */}
      <div className="mt-6 flex justify-center">
        <button
          onClick={fetchMonitoringData}
          disabled={loading}
          className="flex items-center px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? (
            <Loader2 className="h-4 w-4 animate-spin mr-2" />
          ) : (
            <CheckCircle2 className="h-4 w-4 mr-2" />
          )}
          {loading ? '刷新中...' : '立即刷新'}
        </button>
      </div>
    </div>
  );
}
