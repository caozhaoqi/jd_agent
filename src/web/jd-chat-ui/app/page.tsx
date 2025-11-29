"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Volume2 } from "lucide-react";

// 引入组件和 Hook
import Sidebar from "@/components/Sidebar";
import MessageList from "@/components/MessageList";
import ChatInput from "@/components/ChatInput";
import { useAudioQueue } from "@/hooks/useAudioQueue";
import { Message, Session, ChatMode } from "@/types/chat";

export default function Home() {
  const router = useRouter();

  // --- 状态 ---
  const [isLoading, setIsLoading] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [mode, setMode] = useState<ChatMode>('guide');
  const [username, setUsername] = useState("Guest");
  const [sessions, setSessions] = useState<Session[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<number | null>(null);

  // --- Hook ---
  const { addToQueue, stopAudio } = useAudioQueue();

  // --- 初始化逻辑 ---
  useEffect(() => {
    const token = localStorage.getItem("token");
    const user = localStorage.getItem("username");
    if (!token) { router.push("/login"); return; }

    setUsername(user || "User");
    if (messages.length === 0) {
        setMessages([{ role: "assistant", content: `你好 **${user}**！请选择模式或直接开始。` }]);
    }
    fetchSessions(token);
  }, []);

  // --- 业务逻辑方法 ---
  const fetchSessions = async (token: string) => { /* ...原 fetchSessions 代码... */ };

  const loadSession = async (sessionId: number) => {
      stopAudio(); // 切换时停止播放
      // ...原 loadSession 代码...
  };

  const handleFileUpload = async (file: File) => {
      // ...原 handleFileUpload 代码...
  };

  const handleAudioUpload = async (blob: Blob) => {
      // ...原 handleAudioUpload (ASR) 代码...
      // 成功后可直接调用 handleSend(text)
  };

  const handleSend = async (text: string) => {
      stopAudio(); // 发送时停止播放
      // ...原 handleSend 代码...
      // 注意：在 readStream 里调用 addToQueue(bufferText)
  };

  const handleLogout = () => {
    localStorage.removeItem("token");
    router.push("/login");
  };

  // --- 渲染 ---
  return (
    <div className="flex h-screen bg-[#f9fafb] text-gray-800 font-sans overflow-hidden">
      <Sidebar
        username={username}
        sessions={sessions}
        currentSessionId={currentSessionId}
        mode={mode}
        setMode={setMode}
        onNewChat={() => { setCurrentSessionId(null); setMessages([]); stopAudio(); }}
        onLoadSession={loadSession}
        onLogout={handleLogout}
      />

      <div className="flex-1 flex flex-col h-full bg-white min-w-0">
        {/* Header */}
        <div className="h-14 border-b flex items-center justify-between px-4 flex-shrink-0">
            <div className="flex items-center gap-2">
                <span className="font-bold text-lg">{mode === 'guide' ? '岗位分析' : '模拟面试'}</span>
                {mode === 'mock' && <span className="text-xs bg-purple-100 text-purple-600 px-2 py-0.5 rounded-full flex items-center gap-1"><Volume2 size={10}/> TTS On</span>}
            </div>
            <span className="text-xs text-gray-400 bg-gray-100 px-2 py-1 rounded">
                {currentSessionId ? `会话 #${currentSessionId}` : '新会话'}
            </span>
        </div>

        <MessageList messages={messages} isLoading={isLoading} />

        <ChatInput
          mode={mode}
          isLoading={isLoading}
          onSend={handleSend}
          onFileUpload={handleFileUpload}
          onAudioUpload={handleAudioUpload}
        />
      </div>
    </div>
  );
}