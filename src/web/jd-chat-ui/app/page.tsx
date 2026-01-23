"use client";

import { useState, useEffect, lazy, Suspense } from "react";
import { useRouter } from "next/navigation";
import dynamic from "next/dynamic";
import clsx from "clsx";
import { Volume2, VolumeX, PanelRightOpen, PanelRightClose, Database, Menu, X } from "lucide-react";

import { useSessionStore } from "@/stores/useSessionStore";
import { useMessageStore } from "@/stores/useMessageStore";
import { useChatStream, API_BASE } from "@/hooks/useChat";
import { ChatMode } from "@/types/chat";

import Sidebar from "@/components/Sidebar";
import { DashboardState } from "@/components/BrainDashboard";

const MessageList = dynamic(() => import("@/components/MessageList"), {
  ssr: false,
  loading: () => <div className="flex-1 bg-gray-50 animate-pulse" />
});

const ChatInput = dynamic(() => import("@/components/ChatInput"), { ssr: false });

const BrainDashboard = dynamic(() => import("@/components/BrainDashboard"), {
  ssr: false,
  loading: () => <div className="w-[300px] bg-gray-50 animate-pulse" />
});

export default function Home() {
  const router = useRouter();

  // --- Global State from Stores ---
  const { token, isAuthenticated, isInitializing, currentSessionId, initializeAuth, logout, fetchSessions } = useSessionStore();
  const { messages, isLoading, showStartInterviewBtn, setMessages, resetMessages } = useMessageStore();

  // --- Local UI State ---
  const [mode, setMode] = useState<ChatMode | 'rag'>("guide");
  const [showDashboard, setShowDashboard] = useState(true);
  const [isTTSEnabled, setIsTTSEnabled] = useState(true);
  const [dashboardData, setDashboardData] = useState<DashboardState>({
    currentStep: "", userProfile: [], ragSources: []
  });
  const [showMobileSidebar, setShowMobileSidebar] = useState(false);

  // --- Core Logic Hook ---
  const { sendMessage, uploadFile, uploadedFiles } = useChatStream({
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

  // 修复竞态条件：只在认证状态完全初始化后才进行跳转判断
  useEffect(() => {
    if (isInitializing) {
      console.log("🔐 Home: Authentication still initializing, waiting...");
      return;
    }
    
    console.log("🔐 Home: Authentication initialized, isAuthenticated:", isAuthenticated);
    
    if (!isAuthenticated) {
      console.log("🔐 Home: Not authenticated, redirecting to login");
      router.push("/login");
    } else {
      console.log("🔐 Home: Authenticated, staying on home page");
      // 认证成功时刷新会话列表
      fetchSessions();
    }
  }, [isAuthenticated, isInitializing, router, fetchSessions]);

  // --- Event Handlers ---

  const handleModeChange = (newMode: ChatMode | 'rag') => {
    setMode(newMode);
    // 只有在切换到rag或mock模式时才重置消息，切换到guide模式时保留消息
    if (newMode === 'rag' || newMode === 'mock') {
      resetMessages();
      if (newMode === 'rag') {
        setMessages([{ role: "assistant", content: "📚 已切换到**知识库模式**。请问我任何关于技术栈或博客的问题。" }]);
      }
    }
  };

  const handleStartMock = () => {
    sendMessage("我准备好了，请开始模拟面试。");
  };

  return (
    <div className="flex h-screen bg-[#f8fafc] text-[#1e293b] font-sans overflow-hidden relative">
      {/* 移动端侧边栏遮罩 */}
      {showMobileSidebar && (
        <div 
          className="fixed inset-0 bg-black bg-opacity-50 z-20 md:hidden transition-opacity duration-300"
          onClick={() => setShowMobileSidebar(false)}
        />
      )}

      {/* 侧边栏 */}
      <div className={clsx(
        "fixed md:relative z-30 transition-all duration-300 ease-in-out shadow-lg md:shadow-none",
        showMobileSidebar ? "translate-x-0" : "-translate-x-full md:translate-x-0"
      )}>
        <Sidebar mode={mode as ChatMode} setMode={handleModeChange} />
      </div>

      {/* 主内容区域和右侧仪表盘的容器 */}
      <div className="flex-1 flex h-full min-w-0">
        {/* 主内容区域 */}
        <div className="flex-1 flex flex-col h-full bg-white min-w-0 rounded-l-xl shadow-md">
          {/* 顶部导航栏 */}
          <div className="h-16 border-b border-[#e2e8f0] flex items-center justify-between px-6 flex-shrink-0 bg-white">
            <div className="flex items-center gap-4">
              {/* 移动端菜单按钮 */}
              <button 
                className="md:hidden p-2 rounded-lg hover:bg-[#f1f5f9] text-[#64748b] transition-colors"
                onClick={() => setShowMobileSidebar(true)}
              >
                <Menu size={20} />
              </button>
              <div>
                <h1 className="font-bold text-xl text-[#1e293b] flex items-center gap-2">
                  <span className="text-[#3b82f6]">JD</span> Agent
                  <span className={clsx("text-xs px-3 py-0.5 rounded-full font-medium",
                    mode === 'mock' ? "bg-purple-100 text-purple-700" :
                    mode === 'rag' ? "bg-orange-100 text-orange-700" :
                    "bg-blue-100 text-blue-700"
                  )}>
                    {mode === 'guide' ? 'JD 分析' : mode === 'rag' ? '知识库检索' : '模拟面试'}
                  </span>
                </h1>
                {currentSessionId && (
                  <p className="text-sm text-[#64748b] mt-0.5">
                    会话 # {currentSessionId}
                  </p>
                )}
              </div>
            </div>
            <div className="flex items-center gap-3">
              <button
                onClick={() => handleModeChange(mode === 'rag' ? 'guide' : 'rag')}
                className={clsx("flex items-center gap-2 px-4 py-2 rounded-lg text-sm transition-all border",
                  mode === 'rag' ? "bg-orange-50 text-orange-700 border-orange-200 hover:bg-orange-100" : 
                  "bg-[#f1f5f9] border-[#e2e8f0] hover:bg-[#e2e8f0]"
                )}
              >
                <Database size={16} /> <span className="hidden sm:inline">{mode === 'rag' ? '返回对话' : '查知识库'}</span>
              </button>
              <button 
                onClick={() => setIsTTSEnabled(!isTTSEnabled)}
                className={clsx("flex items-center gap-2 px-4 py-2 rounded-lg text-sm border transition-all", 
                  isTTSEnabled 
                    ? "bg-green-50 text-green-700 border-green-200 hover:bg-green-100" 
                    : "bg-[#f1f5f9] border-[#e2e8f0] hover:bg-[#e2e8f0] text-[#64748b]"
                )}
              >
                {isTTSEnabled ? <Volume2 size={16} /> : <VolumeX size={16} />}
                <span className="hidden sm:inline">{isTTSEnabled ? '语音已开启' : '语音已关闭'}</span>
              </button>
              <button 
                onClick={() => setShowDashboard(!showDashboard)}
                className="p-2 rounded-lg hover:bg-[#f1f5f9] text-[#64748b] transition-colors"
              >
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

          {/* 上传文件列表 */}
          {uploadedFiles.length > 0 && (
            <div className="p-4 border-t border-[#e2e8f0] bg-[#f8fafc]">
              <div className="flex items-center gap-2 mb-2">
                <div className="w-5 h-5 rounded-full bg-blue-100 flex items-center justify-center">
                  <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-blue-600">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                    <polyline points="7 10 12 15 17 10" />
                    <line x1="12" y1="15" x2="12" y2="3" />
                  </svg>
                </div>
                <h3 className="font-medium text-sm text-[#1e293b]">已上传文件</h3>
              </div>
              <div className="flex flex-wrap gap-2">
                {uploadedFiles.map((file, index) => (
                  <div key={file.id} className="flex items-center gap-2 px-3 py-1.5 bg-white rounded-lg border border-[#e2e8f0] shadow-sm text-sm">
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-gray-500">
                      <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z" />
                      <polyline points="14 2 14 8 20 8" />
                    </svg>
                    <span className="text-gray-700 truncate max-w-[150px]">{file.name}</span>
                    <span className="text-gray-400 text-xs">{index + 1}</span>
                  </div>
                ))}
              </div>
              <div className="mt-2 text-xs text-gray-500">
                💡 提示: 现在你可以针对这些文件提问，我会基于文件内容给你解答。
              </div>
            </div>
          )}

          <ChatInput
            mode={mode as ChatMode}
            isLoading={isLoading}
            onSend={sendMessage}
            onFileUpload={uploadFile}
            onAudioUpload={() => {}}
            placeholder={mode === 'rag' ? "请输入问题查询知识库..." : uploadedFiles.length > 0 ? "请输入关于上传文件的问题..." : undefined}
          />
        </div>

        {/* 右侧仪表盘 */}
        <div className={clsx(
          "bg-white border-l border-[#e2e8f0] transition-all duration-300 ease-in-out flex flex-col h-full shadow-xl", 
          showDashboard 
            ? "w-[280px] md:w-[400px] flex-shrink-0"
            : "w-0 flex-shrink-0 overflow-hidden border-none"
        )}>
          <div className="p-4 border-b border-[#e2e8f0] flex justify-between items-center bg-white">
            <h2 className="font-bold text-lg text-[#1e293b] flex items-center gap-2">
              🧠 Agent 状态监控
            </h2>
            <button 
              className="md:hidden p-2 rounded-lg hover:bg-[#f1f5f9] text-[#64748b] transition-colors"
              onClick={() => setShowDashboard(false)}
            >
              <X size={18} />
            </button>
          </div>
          <BrainDashboard data={dashboardData} />
        </div>
      </div>
    </div>
  );
}
