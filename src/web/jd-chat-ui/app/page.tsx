"use client";

import { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import ReactMarkdown from "react-markdown";
import { useReactMediaRecorder } from "react-media-recorder";
import {
  Send, Bot, User, Plus, MessageSquare,
  Loader2, Paperclip, LogOut, Mic, Play
} from "lucide-react";
import clsx from "clsx";
import dynamic from "next/dynamic";

// 动态导入组件
const ChatInput = dynamic(() => import("@/components/ChatInput"), { ssr: false });
import Sidebar from "@/components/Sidebar";
import MessageList from "@/components/MessageList";
import { useAudioQueue } from "@/hooks/useAudioQueue";
import { Message, Session } from "@/types/chat";

export default function Home() {
  const router = useRouter();
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // --- 状态 ---
  const [messages, setMessages] = useState<Message[]>([]);
  const [username, setUsername] = useState("Guest");
  const [sessions, setSessions] = useState<Session[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  // 核心状态：是否显示“开始面试”引导按钮
  const [showStartInterviewBtn, setShowStartInterviewBtn] = useState(false);

  // --- Hook ---
  const { addToQueue, stopAudio } = useAudioQueue();

  // --- 初始化 ---
  useEffect(() => {
    const token = localStorage.getItem("token");
    const user = localStorage.getItem("username");
    if (!token) { router.push("/login"); return; }

    setUsername(user || "User");
    if (messages.length === 0) {
        setMessages([{ role: "assistant", content: `你好 **${user}**！请发送 **岗位描述 (JD)**，我将为你生成突击指南并准备模拟面试。` }]);
    }
    fetchSessions(token);
  }, []);

  // --- 业务逻辑 ---
  const fetchSessions = async (token: string) => {
    try {
      const res = await fetch("http://127.0.0.1:8000/api/v1/history/sessions", {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) setSessions(await res.json());
    } catch (e) { console.error(e); }
  };

  const loadSession = async (sessionId: number) => {
    const token = localStorage.getItem("token");
    if (!token) return;
    setCurrentSessionId(sessionId);
    setShowStartInterviewBtn(false); // 切换会话时隐藏按钮，除非逻辑判断需要显示
    stopAudio();
    setIsLoading(true);
    try {
      const res = await fetch(`http://127.0.0.1:8000/api/v1/history/messages/${sessionId}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const msgs = await res.json();
        const formatted = msgs.map((m: any) => {
             let content = m.content;
             let isJson = false;
             if (m.role === 'assistant') {
                 try {
                     const json = JSON.parse(m.content);
                     if (json.meta) { content = formatReportToMarkdown(json); isJson = true; }
                 } catch(e) {}
             }
             return { role: m.role, content, isJson };
        });
        setMessages(formatted);
        // 如果最后一条是 AI 发的，且包含 JD 分析，可以显示面试按钮（这里简单处理，用户手动触发也可）
      }
    } finally { setIsLoading(false); }
  };

  // --- 核心发送逻辑 (统一入口) ---
  const handleSend = async (text: string) => {
    const token = localStorage.getItem("token");
    if (!token || !text.trim()) return;

    stopAudio();
    setIsLoading(true);
    setShowStartInterviewBtn(false); // 发送新消息时隐藏引导按钮
    setMessages(prev => [...prev, { role: "user", content: text }]);

    try {
        // 🟢 情况 A: 已有会话 ID -> 走连续对话接口
        if (currentSessionId) {
            setMessages(prev => [...prev, { role: "assistant", content: "" }]);
            const res = await fetch("http://127.0.0.1:8000/api/v1/chat/stream", {
                method: "POST",
                headers: { "Content-Type": "application/json", "Authorization": `Bearer ${token}` },
                body: JSON.stringify({ session_id: currentSessionId, content: text })
            });
            // 只要是连续对话，都尝试朗读（模拟面试体验）
            await readStream(res, true);
        }

        // 🔵 情况 B: 新会话 (默认视为 JD) -> 走指南生成接口
        else {
            const res = await fetch("http://127.0.0.1:8000/api/v1/generate-guide", {
                method: "POST",
                headers: { "Content-Type": "application/json", "Authorization": `Bearer ${token}` },
                body: JSON.stringify({ jd_text: text })
            });
            const data = await res.json();

            // 1. 渲染 Markdown 报告
            setMessages(prev => [...prev, { role: "assistant", content: formatReportToMarkdown(data), isJson: true }]);

            // 2. 自动设置 Session ID (后端返回了)
            if (data.session_id) {
                setCurrentSessionId(data.session_id);
                // 3. 显示“开始模拟面试”按钮
                setShowStartInterviewBtn(true);
            }

            fetchSessions(token); // 刷新侧边栏
        }
    } catch (e) {
        setMessages(prev => [...prev, { role: "assistant", content: "❌ 请求失败，请检查网络。" }]);
    } finally {
        setIsLoading(false);
    }
  };

  // --- 触发模拟面试 ---
  const startMockInterview = () => {
      handleSend("我准备好了，请扮演面试官，基于上述 JD 对我进行模拟面试。");
  };

  // --- 流式读取 (复用之前的逻辑) ---
  const readStream = async (res: Response, enableTTS: boolean) => {
      if (!res.body) return;
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let done = false;
      let bufferText = "";

      while (!done) {
          const { value, done: d } = await reader.read();
          done = d;
          const chunk = decoder.decode(value, { stream: true });
          const lines = chunk.split("\n\n");
          for (const line of lines) {
              if (line.startsWith("data: ")) {
                  const content = line.replace("data: ", "").trim();
                  // 解析 JSON 事件 (Thought/Token)
                  try {
                      // 简单处理：如果是 JSON 且有 content，取 content；否则直接用
                      if (content.startsWith("{")) {
                          const json = JSON.parse(content);
                          if (json.type === 'token' || json.type === 'result') {
                              updateLastMsg(json.content);
                              if (enableTTS) bufferTTS(json.content);
                          }
                      } else if (content !== "[DONE]") {
                          updateLastMsg(content);
                          if (enableTTS) bufferTTS(content);
                      }
                  } catch(e) {}
              }
          }
      }

      // 内部函数：更新 UI
      function updateLastMsg(text: string) {
          setMessages(prev => {
              const newMsgs = [...prev];
              const last = newMsgs[newMsgs.length-1];
              if (last.role === 'assistant') last.content += text;
              return newMsgs;
          });
      }
      // 内部函数：TTS 缓冲
      function bufferTTS(text: string) {
          bufferText += text;
          if (/[。！？\.\!\?\:\n]/.test(text)) {
              addToQueue(bufferText);
              bufferText = "";
          }
      }
      // 结束清理
      if (enableTTS && bufferText.trim()) addToQueue(bufferText);
  };

  const formatReportToMarkdown = (data: any) => {
      const { meta, tech_questions, hr_questions, company_analysis } = data;
      return `## 📊 ${meta.company_name || '岗位'} 分析\n\n**技术栈**: \`${meta.tech_stack.join('`, `')}\`\n\n${company_analysis ? `> 🏢 **公司**: ${company_analysis}\n\n` : ''}### 🛠️ 推荐技术题\n${tech_questions.map((q:any,i:number)=>`**Q${i+1}: ${q.question}**\n> ${q.reference_answer}`).join('\n\n')}`;
  };

  return (
    <div className="flex h-screen bg-[#f9fafb] text-gray-800 font-sans overflow-hidden">

      {/* 侧边栏 (简化版，去掉了 Tab) */}
      <Sidebar
        username={username} sessions={sessions} currentSessionId={currentSessionId}
        mode={'guide'} setMode={()=>{}} // 兼容旧接口
        onNewChat={() => { setCurrentSessionId(null); setMessages([]); stopAudio(); setShowStartInterviewBtn(false); }}
        onLoadSession={loadSession}
        onLogout={() => { localStorage.clear(); router.push('/login'); }}
      />

      <div className="flex-1 flex flex-col h-full bg-white min-w-0 relative">
        <div className="h-14 border-b flex items-center justify-between px-4 flex-shrink-0">
            <span className="font-bold text-lg">JD Agent</span>
            <span className="text-xs text-gray-400 bg-gray-100 px-2 py-1 rounded">
                {currentSessionId ? `Session #${currentSessionId}` : 'New Chat'}
            </span>
        </div>

        {/* 消息列表 */}
        <div className="flex-1 overflow-y-auto p-4 md:p-6 scroll-smooth relative">
            <MessageList messages={messages} isLoading={isLoading} />

            {/* 🟢 悬浮按钮：引导开始模拟面试 */}
            {showStartInterviewBtn && !isLoading && (
                <div className="flex justify-center mt-6 fade-in">
                    <button
                        onClick={startMockInterview}
                        className="flex items-center gap-2 bg-gradient-to-r from-purple-600 to-blue-600 text-white px-6 py-3 rounded-full shadow-lg hover:shadow-xl hover:scale-105 transition-all font-medium animate-bounce-slow"
                    >
                        <Play size={18} fill="currentColor" />
                        开始模拟面试 (语音版)
                    </button>
                </div>
            )}
        </div>

        <ChatInput
          mode={currentSessionId ? 'mock' : 'guide'} // 只是为了 UI 提示
          isLoading={isLoading}
          onSend={handleSend}
          onFileUpload={()=>{}} // 暂时简化
          onAudioUpload={(blob) => { /* 实现 ASR 逻辑 */ }}
        />
      </div>
    </div>
  );
}