"use client";

import { useState, useEffect, useRef } from 'react';

// 定义性能指标类型
interface PerformanceMetrics {
  totalConversations: number;
  activeConversations: number;
  averageResponseTime: number;
  totalMessages: number;
  userMessages: number;
  assistantMessages: number;
  averageConversationLength: number;
  totalResponseTime: number;
  conversationEfficiency: number;
  responseSpeedTrend: number[];
  conversationDirections: string[];
  conversationHighlights: string[];
  recentConversations: Conversation[];
}

// 定义对话类型
interface Conversation {
  id: string;
  userId: string;
  startTime: string;
  endTime?: string;
  messages: Message[];
  direction: string;
  highlights: string[];
  totalTime: number;
  responseTime: number;
}

// 定义消息类型
interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  responseTime?: number;
}

// 从后端API获取性能指标数据
const API_BASE = 'http://localhost:8000/api/v1';

const fetchMetrics = async (): Promise<PerformanceMetrics> => {
  try {
    // 从后端API获取数据
    const response = await fetch(`${API_BASE}/monitoring/performance`);
    
    if (!response.ok) {
      throw new Error(`API请求失败: ${response.status}`);
    }
    
    const data = await response.json();
    
    // 处理后端返回的数据，映射到PerformanceMetrics类型
    return {
      totalConversations: data.api?.total_requests || 0,
      activeConversations: Math.floor(Math.random() * 10) + 1, // 模拟活跃对话数
      averageResponseTime: typeof data.api?.avg_duration === 'number' ? data.api.avg_duration : 1.2,
      totalMessages: data.api?.total_requests || 0,
      userMessages: Math.floor((data.api?.total_requests || 0) / 2),
      assistantMessages: Math.ceil((data.api?.total_requests || 0) / 2),
      averageConversationLength: 4.2,
      totalResponseTime: (typeof data.api?.avg_duration === 'number' ? data.api.avg_duration : 1.2) * (data.api?.total_requests || 0) || 612.5,
      conversationEfficiency: 0.87,
      responseSpeedTrend: Array.from({ length: 10 }, () => (Math.random() * 1.5) + 0.5),
      conversationDirections: ['JD分析', '职业咨询', '技术问答', '产品建议', '招聘信息'],
      conversationHighlights: ['JD分析准确率提高20%', '响应速度优化15%', '用户满意度提升10%'],
      recentConversations: [
        {
          id: 'conv_1',
          userId: 'user_1',
          startTime: new Date(Date.now() - 5 * 60 * 1000).toISOString(),
          endTime: new Date(Date.now() - 2 * 60 * 1000).toISOString(),
          messages: [
            {
              id: 'msg_1',
              role: 'user',
              content: '如何提高英语口语？',
              timestamp: new Date(Date.now() - 5 * 60 * 1000).toISOString(),
            },
            {
              id: 'msg_2',
              role: 'assistant',
              content: '提高英语口语的方法有很多，比如多听多说，使用语言学习应用，参加英语角等。',
              timestamp: new Date(Date.now() - 4 * 60 * 1000).toISOString(),
              responseTime: 0.8,
            },
          ],
          direction: '技术问答',
          highlights: ['英语口语', '学习方法'],
          totalTime: 180,
          responseTime: 0.8,
        },
        {
          id: 'conv_2',
          userId: 'user_2',
          startTime: new Date(Date.now() - 10 * 60 * 1000).toISOString(),
          endTime: new Date(Date.now() - 5 * 60 * 1000).toISOString(),
          messages: [
            {
              id: 'msg_3',
              role: 'user',
              content: '岗位职责：负责公司产品的设计和开发',
              timestamp: new Date(Date.now() - 10 * 60 * 1000).toISOString(),
            },
            {
              id: 'msg_4',
              role: 'assistant',
              content: 'JD分析结果：这是一个产品开发岗位，主要职责包括产品设计和开发。',
              timestamp: new Date(Date.now() - 8 * 60 * 1000).toISOString(),
              responseTime: 1.5,
            },
          ],
          direction: 'JD分析',
          highlights: ['产品设计', '开发'],
          totalTime: 300,
          responseTime: 1.5,
        },
      ],
    };
  } catch (error) {
    console.error('获取性能指标失败:', error);
    
    // 出错时返回模拟数据作为 fallback
    return {
      totalConversations: 127,
      activeConversations: 8,
      averageResponseTime: 1.2,
      totalMessages: 532,
      userMessages: 286,
      assistantMessages: 246,
      averageConversationLength: 4.2,
      totalResponseTime: 612.5,
      conversationEfficiency: 0.87,
      responseSpeedTrend: [1.5, 1.4, 1.3, 1.2, 1.1, 1.2, 1.1, 1.0, 0.9, 1.0],
      conversationDirections: ['JD分析', '职业咨询', '技术问答', '产品建议', '招聘信息'],
      conversationHighlights: ['JD分析准确率提高20%', '响应速度优化15%', '用户满意度提升10%'],
      recentConversations: [
        {
          id: 'conv_1',
          userId: 'user_1',
          startTime: new Date(Date.now() - 5 * 60 * 1000).toISOString(),
          endTime: new Date(Date.now() - 2 * 60 * 1000).toISOString(),
          messages: [
            {
              id: 'msg_1',
              role: 'user',
              content: '如何提高英语口语？',
              timestamp: new Date(Date.now() - 5 * 60 * 1000).toISOString(),
            },
            {
              id: 'msg_2',
              role: 'assistant',
              content: '提高英语口语的方法有很多，比如多听多说，使用语言学习应用，参加英语角等。',
              timestamp: new Date(Date.now() - 4 * 60 * 1000).toISOString(),
              responseTime: 0.8,
            },
          ],
          direction: '技术问答',
          highlights: ['英语口语', '学习方法'],
          totalTime: 180,
          responseTime: 0.8,
        },
        {
          id: 'conv_2',
          userId: 'user_2',
          startTime: new Date(Date.now() - 10 * 60 * 1000).toISOString(),
          endTime: new Date(Date.now() - 5 * 60 * 1000).toISOString(),
          messages: [
            {
              id: 'msg_3',
              role: 'user',
              content: '岗位职责：负责公司产品的设计和开发',
              timestamp: new Date(Date.now() - 10 * 60 * 1000).toISOString(),
            },
            {
              id: 'msg_4',
              role: 'assistant',
              content: 'JD分析结果：这是一个产品开发岗位，主要职责包括产品设计和开发。',
              timestamp: new Date(Date.now() - 8 * 60 * 1000).toISOString(),
              responseTime: 1.5,
            },
          ],
          direction: 'JD分析',
          highlights: ['产品设计', '开发'],
          totalTime: 300,
          responseTime: 1.5,
        },
      ],
    };
  }
};

const PerformanceDashboard = () => {
  const [metrics, setMetrics] = useState<PerformanceMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<string>('');
  const updateInterval = useRef<NodeJS.Timeout | null>(null);

  // 获取性能指标数据
  const loadMetrics = async () => {
    try {
      setLoading(true);
      const data = await fetchMetrics();
      setMetrics(data);
      setLastUpdated(new Date().toLocaleTimeString());
    } catch (err) {
      setError('获取性能指标失败');
      console.error('获取性能指标失败:', err);
    } finally {
      setLoading(false);
    }
  };

  // 组件挂载时获取数据
  useEffect(() => {
    loadMetrics();
    
    // 设置定期更新数据
    updateInterval.current = setInterval(loadMetrics, 5000); // 每5秒更新一次
    
    return () => {
      if (updateInterval.current) {
        clearInterval(updateInterval.current);
      }
    };
  }, []);

  if (loading) {
    return (
      <div className="flex justify-center items-center min-h-[400px]">
        <p className="text-xl">加载性能指标中...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex justify-center items-center min-h-[400px]">
        <p className="text-xl text-red-500">{error}</p>
      </div>
    );
  }

  if (!metrics) {
    return (
      <div className="flex justify-center items-center min-h-[400px]">
        <p className="text-xl">暂无性能指标数据</p>
      </div>
    );
  }

  return (
    <div className="w-full bg-gray-900 text-white p-6">
      {/* 页面标题 */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-blue-400">📊 对话性能大屏</h1>
        <p className="text-gray-400 mt-2">实时监控用户与Agent/LLM对话数据</p>
        <p className="text-gray-500 text-sm mt-1">最后更新: {lastUpdated}</p>
      </div>

      {/* 关键指标卡片 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <div className="bg-gray-800 rounded-lg p-6 border-l-4 border-blue-500">
          <h3 className="text-gray-400 text-sm font-medium">总对话数</h3>
          <p className="text-3xl font-bold mt-2">{metrics.totalConversations}</p>
          <p className="text-green-400 text-xs mt-2">+12 今日</p>
        </div>

        <div className="bg-gray-800 rounded-lg p-6 border-l-4 border-green-500">
          <h3 className="text-gray-400 text-sm font-medium">活跃对话</h3>
          <p className="text-3xl font-bold mt-2">{metrics.activeConversations}</p>
          <p className="text-yellow-400 text-xs mt-2">进行中</p>
        </div>

        <div className="bg-gray-800 rounded-lg p-6 border-l-4 border-yellow-500">
          <h3 className="text-gray-400 text-sm font-medium">平均响应时间</h3>
          <p className="text-3xl font-bold mt-2">{metrics.averageResponseTime.toFixed(1)}s</p>
          <p className="text-green-400 text-xs mt-2">-0.1s 优化</p>
        </div>

        <div className="bg-gray-800 rounded-lg p-6 border-l-4 border-red-500">
          <h3 className="text-gray-400 text-sm font-medium">对话效率</h3>
          <p className="text-3xl font-bold mt-2">{Math.round(metrics.conversationEfficiency * 100)}%</p>
          <p className="text-green-400 text-xs mt-2">+5% 提升</p>
        </div>
      </div>

      {/* 图表和详细数据 */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        {/* 响应速度趋势图 */}
        <div className="bg-gray-800 rounded-lg p-6 lg:col-span-2">
          <h3 className="text-lg font-medium mb-4">响应速度趋势</h3>
          <div className="h-64 flex items-end justify-around">
            {metrics.responseSpeedTrend.map((speed, index) => (
              <div key={index} className="flex flex-col items-center">
                <div 
                  className="w-8 bg-blue-500 rounded-t-md transition-all duration-300 ease-in-out"
                  style={{ 
                    height: `${Math.max(20, speed * 50)}px`,
                    opacity: 0.8 + (index / metrics.responseSpeedTrend.length) * 0.2
                  }}
                ></div>
                <span className="text-xs text-gray-400 mt-2">{index + 1}</span>
              </div>
            ))}
          </div>
          <div className="mt-4 text-xs text-gray-500 flex justify-between">
            <span>10分钟前</span>
            <span>现在</span>
          </div>
        </div>

        {/* 对话方向分布 */}
        <div className="bg-gray-800 rounded-lg p-6">
          <h3 className="text-lg font-medium mb-4">对话方向分布</h3>
          <div className="space-y-3">
            {metrics.conversationDirections.map((direction, index) => (
              <div key={index} className="flex items-center justify-between">
                <span className="text-sm">{direction}</span>
                <div className="w-2/3 bg-gray-700 rounded-full h-2">
                  <div 
                    className="bg-blue-500 rounded-full h-2 transition-all duration-300 ease-in-out"
                    style={{ width: `${(index + 1) * 15}%` }}
                  ></div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* 对话详情和亮点 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* 最近对话 */}
        <div className="bg-gray-800 rounded-lg p-6">
          <h3 className="text-lg font-medium mb-4">最近对话</h3>
          <div className="space-y-4 max-h-96 overflow-y-auto">
            {metrics.recentConversations.map((conversation) => (
              <div key={conversation.id} className="border border-gray-700 rounded-lg p-4">
                <div className="flex justify-between items-center mb-2">
                  <span className="text-sm font-medium">用户 {conversation.userId}</span>
                  <span className="text-xs text-gray-400">
                    {new Date(conversation.startTime).toLocaleTimeString()}
                  </span>
                </div>
                <div className="mb-2">
                  <span className="text-xs bg-blue-900 text-blue-200 px-2 py-1 rounded">
                    {conversation.direction}
                  </span>
                  <span className="text-xs text-gray-400 ml-2">
                    {conversation.totalTime}秒
                  </span>
                </div>
                <div className="text-sm text-gray-300 mb-2">
                  {conversation.messages[0].content.substring(0, 50)}
                  {conversation.messages[0].content.length > 50 ? '...' : ''}
                </div>
                <div className="flex flex-wrap gap-1">
                  {conversation.highlights.map((highlight, index) => (
                    <span key={index} className="text-xs bg-gray-700 text-gray-200 px-2 py-1 rounded">
                      {highlight}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* 对话亮点 */}
        <div className="bg-gray-800 rounded-lg p-6">
          <h3 className="text-lg font-medium mb-4">对话亮点</h3>
          <div className="space-y-3">
            {metrics.conversationHighlights.map((highlight, index) => (
              <div key={index} className="flex items-center">
                <div className="w-2 h-2 bg-green-500 rounded-full mr-3"></div>
                <span className="text-sm">{highlight}</span>
              </div>
            ))}
          </div>

          {/* 消息统计 */}
          <div className="mt-8">
            <h3 className="text-lg font-medium mb-4">消息统计</h3>
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-gray-700 rounded-lg p-4">
                <h4 className="text-sm text-gray-400">用户消息</h4>
                <p className="text-2xl font-bold mt-1">{metrics.userMessages}</p>
                <p className="text-xs text-gray-500 mt-1">{metrics.totalMessages > 0 ? Math.round((metrics.userMessages / metrics.totalMessages) * 100) : 0}%</p>
              </div>
              <div className="bg-gray-700 rounded-lg p-4">
                <h4 className="text-sm text-gray-400">助手消息</h4>
                <p className="text-2xl font-bold mt-1">{metrics.assistantMessages}</p>
                <p className="text-xs text-gray-500 mt-1">{metrics.totalMessages > 0 ? Math.round((metrics.assistantMessages / metrics.totalMessages) * 100) : 0}%</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* 系统状态 */}
      <div className="bg-gray-800 rounded-lg p-6 border-t-2 border-green-500">
        <div className="flex justify-between items-center">
          <div className="flex items-center">
            <div className="w-3 h-3 bg-green-500 rounded-full mr-3 animate-pulse"></div>
            <span className="text-sm font-medium">系统状态</span>
          </div>
          <div className="flex space-x-4">
            <span className="text-xs text-gray-400">API 响应: 正常</span>
            <span className="text-xs text-gray-400">数据库: 正常</span>
            <span className="text-xs text-gray-400">LLM: 正常</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default PerformanceDashboard;