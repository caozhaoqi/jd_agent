"use client";

import { useState, useEffect } from 'react';
import { API_BASE } from '../hooks/useChat';
import { useRouter } from 'next/navigation';

export default function MockInterviewPage() {
  const [jdText, setJdText] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [messages, setMessages] = useState<{ role: string; content: string }[]>([]);
  const router = useRouter();

  useEffect(() => {
    // 检查是否已登录
    const token = localStorage.getItem('token');
    if (!token) {
      router.push('/login');
      return;
    }
  }, [router]);

  const startMock = async () => {
    if (!jdText.trim()) {
      alert('请输入岗位JD内容');
      return;
    }

    setIsLoading(true);
    setMessages([]);

    const token = localStorage.getItem('token');
    if (!token) {
      router.push('/login');
      setIsLoading(false);
      return;
    }

    try {
      const response = await fetch(`${API_BASE}/interview/mock-interview/stream`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({ jd_text: jdText })
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error('No response body');
      }

      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        
        // 处理缓冲区中的完整事件
        while (true) {
          const eventEnd = buffer.indexOf("\n\n");
          if (eventEnd === -1) break;
          
          const event = buffer.substring(0, eventEnd);
          buffer = buffer.substring(eventEnd + 2);
          
          if (event.startsWith("data: ")) {
            const jsonStr = event.replace("data: ", "").trim();
            if (jsonStr === "[DONE]") break;

            try {
              const msg = JSON.parse(jsonStr);
              // msg.role 是 'interviewer' 或 'candidate'
              // msg.content 是 内容
              setMessages(prev => [...prev, { role: msg.role, content: msg.content }]);
            } catch (e) {
              console.error('Error parsing JSON:', e);
            }
          }
        }
      }
      
      // 处理缓冲区中剩余的最后一个事件
      if (buffer.trim()) {
        buffer = buffer.trim();
        if (buffer.startsWith("data: ")) {
          const jsonStr = buffer.replace("data: ", "").trim();
          if (jsonStr !== "[DONE]") {
            try {
              const msg = JSON.parse(jsonStr);
              setMessages(prev => [...prev, { role: msg.role, content: msg.content }]);
            } catch (e) {
              console.error('Error parsing final JSON:', e);
            }
          }
        }
      }
    } catch (error) {
      console.error('Stream failed:', error);
      setMessages(prev => [...prev, { role: 'system', content: '❌ 请求失败，请重试' }]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 p-4">
      <div className="max-w-4xl mx-auto bg-white rounded-lg shadow-lg p-6">
        <h1 className="text-2xl font-bold mb-4">模拟面试</h1>
        
        <div className="mb-4">
          <textarea
            value={jdText}
            onChange={(e) => setJdText(e.target.value)}
            placeholder="请输入岗位JD内容..."
            className="w-full h-40 p-2 border border-gray-300 rounded-lg"
          />
        </div>
        
        <button
          onClick={startMock}
          disabled={isLoading}
          className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 disabled:bg-gray-400"
        >
          {isLoading ? '正在启动...' : '开始模拟面试'}
        </button>
        
        <div className="mt-6">
          <h2 className="text-xl font-semibold mb-2">面试对话</h2>
          <div className="border border-gray-200 rounded-lg p-4 h-96 overflow-y-auto">
            {messages.map((msg, index) => (
              <div key={index} className={`mb-4 p-3 rounded-lg ${msg.role === 'interviewer' ? 'bg-blue-50' : msg.role === 'candidate' ? 'bg-green-50' : 'bg-gray-50'}`}>
                <p className="font-semibold">{msg.role === 'interviewer' ? '面试官' : msg.role === 'candidate' ? '候选人' : '系统'}</p>
                <p>{msg.content}</p>
              </div>
            ))}
            {isLoading && (
              <div className="text-gray-500">加载中...</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}