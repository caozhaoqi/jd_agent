"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import dynamic from "next/dynamic";
import clsx from "clsx";
import { Volume2, VolumeX, PanelRightOpen, PanelRightClose, Database, Search, Loader2 } from "lucide-react";

// Stores and Hooks
import { useSessionStore } from "@/stores/useSessionStore";
import { useMessageStore } from "@/stores/useMessageStore";
import { useChatStream, API_BASE } from "@/hooks/useChat"; // 修复：从正确的文件名 useChat 导入
import { ChatMode } from "@/types/chat";

// Components
import Sidebar from "@/components/Sidebar";
import MessageList from "@/components/MessageList";
import BrainDashboard, { DashboardState } from "@/components/BrainDashboard";

const ChatInput = dynamic(() => import("@/components/ChatInput"), { ssr: false });

export default function Home() {
  const router = useRouter();

  // --- Global State from Stores ---
  const { token, currentSessionId, initializeAuth, fetchSessions, hasHydrated } = useSessionStore();
  const { messages, isLoading, showStartInterviewBtn, setMessages, resetMessages } = useMessageStore();

  // --- Local UI State ---
  const [mode, setMode] = useState<ChatMode | 'rag'>("guide");
  const [showDashboard, setShowDashboard] = useState(true);
  const [isTTSEnabled, setIsTTSEnabled] = useState(true);
  const [isCrawling, setIsCrawling] = useState(false);
  const [crawlResults, setCrawlResults] = useState<any[]>([]);
  const [showCrawlResults, setShowCrawlResults] = useState(false);
  const [dashboardData, setDashboardData] = useState<DashboardState>({
    currentStep: "", userProfile: [], ragSources: []
  });

  // --- Core Logic Hook ---
  const { sendMessage } = useChatStream({
    mode,
    isTTSEnabled,
    onDashboardUpdate: (key, value) => {
      setDashboardData(prev => ({ ...prev, [key]: value }));
    },
  });

  // --- Effects ---

  // Initialize auth and fetch sessions on mount
  useEffect(() => {
    initializeAuth();
  }, [initializeAuth]);

  // Redirect to login if token is lost
  useEffect(() => {
    if (!hasHydrated) return; // 等待本地存储同步完成
    if (!token) {
      router.push("/login");
    }
  }, [token, router, hasHydrated]);

  // Fetch messages when session changes
  useEffect(() => {
    const loadMessages = async () => {
      if (!hasHydrated) return;
      if (currentSessionId && token) {
        try {
          const res = await fetch(`${API_BASE}/chat/history/messages/${currentSessionId}`, {
            headers: { Authorization: `Bearer ${token}` },
          });
          if (res.ok) {
            const msgs = await res.json();
            setMessages(msgs);
          } else if (res.status === 401) {
            useSessionStore.getState().logout();
          }
        } catch (e) {
          console.error("Failed to fetch messages:", e);
        }
      }
    };
    loadMessages();
  }, [currentSessionId, token, setMessages, hasHydrated]);

  // --- Event Handlers ---

  const handleModeChange = (newMode: ChatMode | 'rag') => {
    setMode(newMode);
    resetMessages();
    if (newMode === 'rag') {
      setMessages([{ role: "assistant", content: "📚 已切换到**知识库模式**。请问我任何关于技术栈或博客的问题。" }]);
    }
  };

  const handleStartMock = () => {
    sendMessage("我准备好了，请开始模拟面试。");
  };

  const handleCrawlJobs = async () => {
    if (!token) return;
    
    // 从最后一条用户消息中提取关键词，如果没有则使用默认值
    const lastUserMessage = messages.filter(m => m.role === "user").pop();
    const keywords = lastUserMessage?.content || "Python 后端开发";
    
    setIsCrawling(true);
    setShowCrawlResults(false);
    
    try {
      const res = await fetch(`${API_BASE}/jd/crawl-jobs`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          keywords: keywords,
          max_results: 10,
        }),
      });
      
      const data = await res.json();
      
      if (data.status === "success") {
        setCrawlResults(data.data || []);
        setShowCrawlResults(true);
        // 将结果添加到消息中
        const resultText = `## 📊 相关岗位数据 (共 ${data.data.length} 条)\n\n${data.data.map((job: any, idx: number) => 
          `### ${idx + 1}. ${job.title || '未知职位'}\n**来源**: [${job.url || '未知'}](${job.url || '#'})\n\n${job.content ? `**描述**: ${job.content.substring(0, 200)}...` : ''}\n\n`
        ).join('')}`;
        setMessages([...messages, { role: "assistant", content: resultText }]);
      } else {
        alert(`爬取失败: ${data.message}`);
      }
    } catch (e) {
      console.error("爬取岗位数据失败:", e);
      alert("爬取失败，请稍后重试");
    } finally {
      setIsCrawling(false);
    }
  };

  return (
    <div className="flex h-screen bg-[#f9fafb] text-gray-800 font-sans overflow-hidden">
      <Sidebar mode={mode as ChatMode} setMode={handleModeChange} />

      <div className="flex-1 flex flex-col h-full bg-white min-w-0 relative">
        {/* Header */}
        <div className="h-14 border-b flex items-center justify-between px-4 flex-shrink-0">
          <div className="flex items-center gap-3">
            <span className="font-bold text-lg text-gray-800">
              {currentSessionId ? `会话 #${currentSessionId}` : (mode === 'rag' ? '知识库问答' : '新会话')}
            </span>
            <span className={clsx("text-xs px-2 py-0.5 rounded-full font-medium",
              mode === 'mock' ? "bg-purple-100 text-purple-700" :
              mode === 'rag' ? "bg-orange-100 text-orange-700" :
              "bg-blue-100 text-blue-700"
            )}>
              {mode === 'guide' ? 'JD 分析' : mode === 'rag' ? '知识库检索' : '模拟面试'}
            </span>
          </div>
          <div className="flex items-center gap-2">
            {mode === 'guide' && (
              <button
                onClick={handleCrawlJobs}
                disabled={isCrawling || !token}
                className={clsx("flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm transition-all border",
                  isCrawling 
                    ? "bg-gray-100 text-gray-400 border-gray-200 cursor-not-allowed" 
                    : "bg-blue-50 text-blue-700 border-blue-200 hover:bg-blue-100"
                )}
              >
                {isCrawling ? (
                  <>
                    <Loader2 size={16} className="animate-spin" />
                    <span className="hidden sm:inline">爬取中...</span>
                  </>
                ) : (
                  <>
                    <Search size={16} />
                    <span className="hidden sm:inline">爬取岗位</span>
                  </>
                )}
              </button>
            )}
            <button
              onClick={() => handleModeChange(mode === 'rag' ? 'guide' : 'rag')}
              className={clsx("flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm transition-all border",
                mode === 'rag' ? "bg-orange-50 text-orange-700 border-orange-200" : "bg-gray-50 border-gray-200 hover:bg-gray-100"
              )}
            >
              <Database size={16} /> <span className="hidden sm:inline">查知识库</span>
            </button>
            <button onClick={() => setIsTTSEnabled(!isTTSEnabled)} className={clsx("flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm border", isTTSEnabled ? "bg-green-50 text-green-700 border-green-200" : "bg-gray-50 text-gray-500 border-gray-200")}>
              {isTTSEnabled ? <Volume2 size={16} /> : <VolumeX size={16} />}
            </button>
            <button onClick={() => setShowDashboard(!showDashboard)} className="p-2 rounded-lg hover:bg-gray-100 text-gray-500">
              {showDashboard ? <PanelRightClose size={20}/> : <PanelRightOpen size={20}/>}
            </button>
          </div>
        </div>

        <MessageList
          messages={messages}
          isLoading={isLoading}
          showStartInterviewBtn={showStartInterviewBtn}
          onStartMockInterview={handleStartMock}
        />

        <ChatInput
          mode={mode as ChatMode}
          isLoading={isLoading}
          onSend={sendMessage}
          onFileUpload={() => {}}
          onAudioUpload={() => {}}
          placeholder={mode === 'rag' ? "请输入问题查询知识库..." : undefined}
        />
      </div>

      <div className={clsx("bg-[#fcfdfd] border-l border-gray-200 transition-all duration-300 ease-in-out flex flex-col", showDashboard ? "w-[300px] md:w-[350px] translate-x-0" : "w-0 translate-x-full overflow-hidden border-none")}>
        <div className="p-4 border-b border-gray-100 font-bold text-sm text-gray-700">🧠 Agent 状态监控</div>
        <BrainDashboard data={dashboardData} />
      </div>
    </div>
  );
}
