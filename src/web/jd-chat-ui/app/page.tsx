"use client";

import { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Volume2 } from "lucide-react";
import dynamic from "next/dynamic"; // 1. 动态导入

// 引入组件和 Hook
import Sidebar from "@/components/Sidebar";
import MessageList from "@/components/MessageList";
import { useAudioQueue } from "@/hooks/useAudioQueue";
import { Message, Session, ChatMode } from "@/types/chat";

// 2. 解决 Worker 报错：动态导入 ChatInput 并禁用 SSR
const ChatInput = dynamic(() => import("@/components/ChatInput"), {
  ssr: false,
  loading: () => (
    <div className="p-4 border-t border-gray-100 bg-white">
      <div className="max-w-3xl mx-auto bg-gray-50 border border-gray-200 rounded-2xl h-[80px] animate-pulse flex items-center justify-center text-gray-400 text-sm">
        正在初始化输入组件...
      </div>
    </div>
  )
});

export default function Home() {
  const router = useRouter();

  // --- 状态定义 (确保 mode 在这里定义) ---
  const [isLoading, setIsLoading] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [mode, setMode] = useState<ChatMode>('guide'); // ✅ 修复: mode 定义在这里
  const [username, setUsername] = useState("Guest");
  const [sessions, setSessions] = useState<Session[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<number | null>(null);

  // 控制“开始模拟面试”按钮的状态
  const [showStartInterviewBtn, setShowStartInterviewBtn] = useState(false);

  // --- Hook ---
  const { addToQueue, stopAudio } = useAudioQueue();

  // --- 初始化逻辑 ---
  useEffect(() => {
    const token = localStorage.getItem("token");
    const user = localStorage.getItem("username");
    if (!token) { router.push("/login"); return; }

    setUsername(user || "User");
    if (messages.length === 0) {
        setMessages([{ role: "assistant", content: `你好 **${user}**！请发送岗位 JD，我将为你生成面试指南。` }]);
    }
    fetchSessions(token);
  }, []);

  // --- 解锁音频上下文 (解决 NotAllowedError) ---
  const unlockAudioContext = () => {
    const AudioContext = window.AudioContext || (window as any).webkitAudioContext;
    if (AudioContext) {
      const ctx = new AudioContext();
      const oscillator = ctx.createOscillator();
      const gainNode = ctx.createGain();
      gainNode.gain.value = 0; // 静音
      oscillator.connect(gainNode);
      gainNode.connect(ctx.destination);
      oscillator.start(0);
      oscillator.stop(0.001);
    }
  };

  // --- 核心发送逻辑 (修复 overrideInput 和 mode 引用) ---
  const handleSend = async (text: string) => {
    // 1. 直接使用传入的 text
    const msgToSend = text;
    if (!msgToSend?.trim() || isLoading) return;

    // 2. 解锁音频
    unlockAudioContext();

    const token = localStorage.getItem("token");
    if (!token) return;

    stopAudio(); // 停止旧播放
    setIsLoading(true);
    setShowStartInterviewBtn(false); // 隐藏按钮

    // 乐观更新 UI
    setMessages(prev => [...prev, { role: "user", content: msgToSend }]);

    try {
        // 🟢 场景 A: 已有会话 -> 连续对话
        if (currentSessionId) {
            setMessages(prev => [...prev, { role: "assistant", content: "" }]);
            const res = await fetch("http://127.0.0.1:8000/api/v1/chat/stream", {
                method: "POST",
                headers: { "Content-Type": "application/json", "Authorization": `Bearer ${token}` },
                body: JSON.stringify({ session_id: currentSessionId, content: msgToSend })
            });
            await readStream(res, true); // 始终启用 TTS
        }

        // 🔵 场景 B: 新会话 -> 生成指南
        else if (mode === 'guide') {
            const res = await fetch("http://127.0.0.1:8000/api/v1/generate-guide", {
                method: "POST",
                headers: { "Content-Type": "application/json", "Authorization": `Bearer ${token}` },
                body: JSON.stringify({ jd_text: msgToSend })
            });
            const data = await res.json();

            setMessages(prev => [...prev, { role: "assistant", content: formatReportToMarkdown(data), isJson: true }]);

            if (data.session_id) {
                setCurrentSessionId(data.session_id);
                setShowStartInterviewBtn(true); // 显示开始面试按钮
            }
            fetchSessions(token);
        }

        // 🟣 场景 C: 新会话 -> 模拟面试
        else {
            setMessages(prev => [...prev, { role: "assistant", content: "" }]);
            const res = await fetch("http://127.0.0.1:8000/api/v1/stream/mock-interview", {
                method: "POST",
                headers: { "Content-Type": "application/json", "Authorization": `Bearer ${token}` },
                body: JSON.stringify({ jd_text: msgToSend })
            });
            await readStream(res, true);
            fetchSessions(token);
        }

    } catch (e) {
        setMessages(prev => [...prev, { role: "assistant", content: "❌ 请求失败，请检查网络。" }]);
    } finally {
        setIsLoading(false);
    }
  };

  // --- 流式读取 (修复结巴问题) ---
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
                  let content = "";
                  const dataStr = line.replace("data: ", "").trim();

                  if (dataStr === "[DONE]") break;
                  if (!dataStr) continue;

                  try {
                      const json = JSON.parse(dataStr);
                      if (json.type === 'token' || json.type === 'result') {
                          content = json.content || "";
                      }
                  } catch (e) {
                      content = dataStr; // 兼容纯文本
                  }

                  if (!content) continue;

                  // ✅ 修复：使用不可变数据更新，防止文字重复
                  setMessages(prev => {
                      if (prev.length === 0) return prev;
                      const newMsgs = [...prev];
                      const lastIndex = newMsgs.length - 1;
                      const lastMsg = newMsgs[lastIndex];

                      if (lastMsg.role === "assistant") {
                          newMsgs[lastIndex] = {
                              ...lastMsg,
                              content: lastMsg.content + content
                          };
                      }
                      return newMsgs;
                  });

                  if (enableTTS) {
                      bufferText += content;
                      if (/[。！？\.\!\?\:\n]/.test(content)) {
                          addToQueue(bufferText);
                          bufferText = "";
                      }
                  }
              }
          }
      }

      if (enableTTS && bufferText.trim()) {
          addToQueue(bufferText);
      }
  };

  // --- 辅助函数 ---
  const startMockInterview = () => {
      setShowStartInterviewBtn(false);
      handleSend("我准备好了，请扮演面试官，基于上述 JD 对我进行模拟面试。");
  };

  const formatReportToMarkdown = (data: any) => {
      const { meta, tech_questions, hr_questions, company_analysis } = data;
      return `## 📊 ${meta.company_name || '岗位'} 分析\n\n**技术栈**: \`${meta.tech_stack.join('`, `')}\`\n\n${company_analysis ? `> 🏢 **公司**: ${company_analysis}\n\n` : ''}### 🛠️ 推荐技术题\n${tech_questions.map((q:any,i:number)=>`**Q${i+1}: ${q.question}**\n> ${q.reference_answer}`).join('\n\n')}`;
  };

  // --- API: 会话管理 ---
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
    setShowStartInterviewBtn(false);
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
      }
    } finally { setIsLoading(false); }
  };

  const handleFileUpload = async (file: File) => {
      // (保留你之前的文件上传逻辑，或者留空待填)
      console.log("Upload file:", file.name);
  };

  const handleAudioUpload = async (blob: Blob) => {
      // (保留你之前的ASR逻辑)
      console.log("Audio blob captured");
  };

  // --- 渲染 ---
  return (
    <div className="flex h-screen bg-[#f9fafb] text-gray-800 font-sans overflow-hidden">
      <Sidebar
        username={username} sessions={sessions} currentSessionId={currentSessionId}
        mode={mode} setMode={setMode}
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

        <MessageList
            messages={messages}
            isLoading={isLoading}
            showStartInterviewBtn={showStartInterviewBtn}
            onStartMockInterview={startMockInterview}
        />

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