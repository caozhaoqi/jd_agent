"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import dynamic from "next/dynamic";
import clsx from "clsx";
import { Volume2, VolumeX, PanelRightOpen, PanelRightClose, Database } from "lucide-react";

// Stores and Hooks
import { useSessionStore } from "@/stores/useSessionStore";
import { useMessageStore } from "@/stores/useMessageStore";
import { useChatStream, API_BASE } from "@/hooks/useChat";
import { ChatMode } from "@/types/chat";

// Components
import Sidebar from "@/components/Sidebar";
import MessageList from "@/components/MessageList";
import BrainDashboard, { DashboardState } from "@/components/BrainDashboard";

const ChatInput = dynamic(() => import("@/components/ChatInput"), { ssr: false });

export default function Home() {
  const router = useRouter();

  // --- Global State from Stores ---
  const { token, currentSessionId, initializeAuth, logout, fetchSessions } = useSessionStore();
  const { messages, isLoading, showStartInterviewBtn, setMessages, resetMessages } = useMessageStore();

  // --- Local UI State ---
  const [mode, setMode] = useState<ChatMode | 'rag'>("guide");
  const [showDashboard, setShowDashboard] = useState(true);
  const [isTTSEnabled, setIsTTSEnabled] = useState(true);
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
    onSessionCreated: (id) => {
      // 后端创建新会话后，刷新侧边栏列表
      fetchSessions();
    },
    onLogout: logout,
  });

  // --- Effects ---

  useEffect(() => {
    initializeAuth();
  }, [initializeAuth]);

  useEffect(() => {
    if (!token) {
      router.push("/login");
    }
  }, [token, router]);

  // --- Event Handlers ---

  const handleLoadSession = async (id: number) => {
    if (!token) return;

    // 核心修复：将加载逻辑移到这里
    resetMessages();
    useSessionStore.getState().setCurrentSessionId(id);
    setMode('mock');

    try {
      const res = await fetch(`${API_BASE}/chat/history/messages/${id}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const msgs = await res.json();
        setMessages(msgs);
      } else if (res.status === 401) {
        logout();
      }
    } catch (e) {
      console.error("Failed to fetch messages:", e);
    }
  };

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

  return (
    <div className="flex h-screen bg-[#f9fafb] text-gray-800 font-sans overflow-hidden">
      {/* 核心修复：将 handleLoadSession 传递给 Sidebar */}
      <Sidebar mode={mode as ChatMode} setMode={handleModeChange} onLoadSession={handleLoadSession} />

      <div className="flex-1 flex flex-col h-full bg-white min-w-0 relative">
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
