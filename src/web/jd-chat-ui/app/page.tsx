"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import dynamic from "next/dynamic";
import clsx from "clsx";
import { Volume2, VolumeX, PanelRightOpen, PanelRightClose, Database } from "lucide-react";

// Components
import Sidebar from "@/components/Sidebar";
import MessageList from "@/components/MessageList";
import BrainDashboard, { DashboardState } from "@/components/BrainDashboard";

// Hooks
import { useChat } from "@/hooks/useChat"; // 引入刚才写的 Hook
import { API_BASE } from "@/hooks/useChat";
import {  ChatMode, Session } from "@/types/chat";
// import { Session } from "inspector";

const ChatInput = dynamic(() => import("@/components/ChatInput"), { ssr: false });

export default function Home() {
  const router = useRouter();

  // --- 全局 UI 状态 ---
  const [username, setUsername] = useState(() => localStorage.getItem("username") || "Guest");
  const [token, setToken] = useState<string | null>(() => localStorage.getItem("token"));
  const [sessions, setSessions] = useState<Session[]>([]);

  const [mode, setMode] = useState<ChatMode | 'rag'>("guide");
  const [currentSessionId, setCurrentSessionId] = useState<number | null>(null);

  const [showDashboard, setShowDashboard] = useState(true);
  const [isTTSEnabled, setIsTTSEnabled] = useState(true);

  const [dashboardData, setDashboardData] = useState<DashboardState>({
    currentStep: "", userProfile: [], ragSources: []
  });

  // --- 会话相关功能 ---
  const fetchSessionsData = async (authToken: string): Promise<Session[]> => {
    try {
      const res = await fetch(`${API_BASE}/chat/history/sessions`, {
        headers: { Authorization: `Bearer ${authToken}` }
      });
      if (res.ok) return await res.json();
    } catch (e) {
      console.error(e);
    }
    return [];
  };

  // --- 初始化加载 ---
  useEffect(() => {
    const loadSessions = async () => {
      if (!token) return;
      const sessionsData = await fetchSessionsData(token);
      setSessions(sessionsData);
    };
    
    if (!token) {
      router.push("/login");
      return;
    }
    
    loadSessions();
  }, [router, token]);

  // --- 核心业务逻辑 (委托给 Hook) ---
  const {
    messages,
    setMessages,
    isLoading,
    showStartInterviewBtn,
    setShowStartInterviewBtn,
    sendMessage
  } = useChat({
    token,
    mode,
    currentSessionId,
    isTTSEnabled,
    onDashboardUpdate: (key, value) => {
        setDashboardData(prev => {
            if (key === 'user_profile') return { ...prev, userProfile: value as string[] };
            if (key === 'rag_sources') return { ...prev, ragSources: value as { title: string; url: string; score: number }[] };
            if (key === 'current_step') return { ...prev, currentStep: value as string };
            return prev;
        });
    },
  onSessionCreated: (id) => {
      setCurrentSessionId(id);
      setShowStartInterviewBtn(true);
      if(token) {
        const loadSessions = async () => {
          const sessionsData = await fetchSessionsData(token);
          setSessions(sessionsData);
        };
        loadSessions();
      }
  }
  });

  // --- 界面交互处理 ---
  const handleLoadSession = async (id: number) => {
      if (!token) return;
      setCurrentSessionId(id);
      setMode('mock'); // 加载旧会话默认进入对话模式

      // 加载历史消息逻辑可以放在这里，或者封装进 Hook
      const res = await fetch(`http://127.0.0.1:8000/api/v1/chat/history/messages/${id}`, {
          headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
          const msgs = await res.json();
          // 简单的格式处理，如果需要更复杂的可以复用 formatReportToMarkdown
          setMessages(msgs);
      }
  };

  const handleStartMock = () => {
      setShowStartInterviewBtn(false);
      sendMessage("我准备好了，请开始模拟面试。");
  };

  return (
    <div className="flex h-screen bg-[#f9fafb] text-gray-800 font-sans overflow-hidden">
      <Sidebar
        username={username}
        sessions={sessions}
        currentSessionId={currentSessionId}
        mode={mode as ChatMode}
        setMode={(m) => {
            setMode(m);
            if(m !== 'mock') setCurrentSessionId(null);
            setMessages([]);
        }}
        onNewChat={() => { setCurrentSessionId(null); setMessages([]); setShowStartInterviewBtn(false); }}
        onLoadSession={handleLoadSession}
        onLogout={() => { localStorage.removeItem("token"); router.push("/login"); }}
      />

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
                {/* 知识库切换 */}
                <button
                    onClick={() => {
                        if (mode === 'rag') setMode('guide');
                        else {
                            setMode('rag');
                            setCurrentSessionId(null);
                            setMessages([{ role: "assistant", content: "📚 已切换到**知识库模式**。请问我任何关于技术栈或博客的问题。" }]);
                        }
                    }}
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

        {/* 消息列表 */}
        <MessageList
            messages={messages}
            isLoading={isLoading}
            showStartInterviewBtn={showStartInterviewBtn}
            onStartMockInterview={handleStartMock}
        />

        {/* 输入框 */}
        <ChatInput
          mode={mode as ChatMode}
          isLoading={isLoading}
          onSend={sendMessage} // 直接调用 Hook 提供的发送方法
          onFileUpload={()=>{}}
          onAudioUpload={() => {}}
          placeholder={mode === 'rag' ? "请输入问题查询知识库..." : undefined}
        />
      </div>

      {/* 右侧 Dashboard */}
      <div className={clsx(
          "bg-[#fcfdfd] border-l border-gray-200 transition-all duration-300 ease-in-out flex flex-col",
          showDashboard ? "w-[300px] md:w-[350px] translate-x-0" : "w-0 translate-x-full overflow-hidden border-none"
      )}>
          <div className="p-4 border-b border-gray-100 font-bold text-sm text-gray-700">🧠 Agent 状态监控</div>
          <BrainDashboard data={dashboardData} />
      </div>
    </div>
  );
}