"use client";

import { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
// 图标
import { Volume2, VolumeX } from "lucide-react";
import dynamic from "next/dynamic";
// 🟢 补上这一行！
import clsx from "clsx";

// 引入组件和 Hook
import Sidebar from "@/components/Sidebar";
import MessageList from "@/components/MessageList";
import { useAudioQueue } from "@/hooks/useAudioQueue";
import { Message, Session, ChatMode } from "@/types/chat";

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

  // --- 状态 ---
  const [isLoading, setIsLoading] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [mode, setMode] = useState<ChatMode>('guide');
  const [username, setUsername] = useState("Guest");
  const [sessions, setSessions] = useState<Session[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<number | null>(null);

  // ✅ 新增：全局 TTS 开关 (默认开启)
  const [isTTSEnabled, setIsTTSEnabled] = useState(true);

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
        setMessages([{ role: "assistant", content: `你好 **${user}**！我是你的 AI 面试助手。` }]);
    }
    fetchSessions(token);
  }, []);

  // ✅ 新增：监听开关变化，如果关闭则立即停止播放
  useEffect(() => {
    if (!isTTSEnabled) {
        stopAudio();
    }
  }, [isTTSEnabled, stopAudio]);

  // --- 解锁音频 ---
  const unlockAudioContext = () => {
    const AudioContext = window.AudioContext || (window as any).webkitAudioContext;
    if (AudioContext) {
      const ctx = new AudioContext();
      const oscillator = ctx.createOscillator();
      const gainNode = ctx.createGain();
      gainNode.gain.value = 0;
      oscillator.connect(gainNode);
      gainNode.connect(ctx.destination);
      oscillator.start(0);
      oscillator.stop(0.001);
    }
  };

  // --- 发送逻辑 ---
  const handleSend = async (text: string) => {
    const msgToSend = text;
    if (!msgToSend?.trim() || isLoading) return;

    unlockAudioContext();
    const token = localStorage.getItem("token");
    if (!token) return;

    stopAudio();
    setIsLoading(true);
    setShowStartInterviewBtn(false);
    setMessages(prev => [...prev, { role: "user", content: msgToSend }]);

    try {
        // 🟢 场景 A: 连续对话
        if (currentSessionId) {
            setMessages(prev => [...prev, { role: "assistant", content: "" }]);
            const res = await fetch("http://127.0.0.1:8000/api/v1/chat/stream", {
                method: "POST",
                headers: { "Content-Type": "application/json", "Authorization": `Bearer ${token}` },
                body: JSON.stringify({ session_id: currentSessionId, content: msgToSend })
            });
            // ✅ 修改：传入全局开关状态
            await readStream(res, isTTSEnabled);
        }
        // 🔵 场景 B: 指南
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
                setShowStartInterviewBtn(true);
            }
            fetchSessions(token);
        }
        // 🟣 场景 C: 模拟面试
        else {
            setMessages(prev => [...prev, { role: "assistant", content: "" }]);
            const res = await fetch("http://127.0.0.1:8000/api/v1/stream/mock-interview", {
                method: "POST",
                headers: { "Content-Type": "application/json", "Authorization": `Bearer ${token}` },
                body: JSON.stringify({ jd_text: msgToSend })
            });
            // ✅ 修改：传入全局开关状态
            await readStream(res, isTTSEnabled);
            fetchSessions(token);
        }
    } catch (e) {
        setMessages(prev => [...prev, { role: "assistant", content: "❌ 请求失败，请检查网络。" }]);
    } finally {
        setIsLoading(false);
    }
  };

  // --- 流式读取 ---
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
                  if (content === "[DONE]") break;

                  // 尝试解析 JSON
                  let textToShow = "";
                  try {
                      if (content.startsWith("{")) {
                        const json = JSON.parse(content);
                        if (json.type === 'token' || json.type === 'result') {
                            textToShow = json.content || "";
                        }
                      } else {
                          textToShow = content;
                      }
                  } catch(e) { textToShow = content; }

                  if (!textToShow) continue;

                  // 更新 UI
                  setMessages(prev => {
                      if (prev.length === 0) return prev;
                      const newMsgs = [...prev];
                      const lastIndex = newMsgs.length - 1;
                      const lastMsg = newMsgs[lastIndex];
                      if (lastMsg.role === "assistant") {
                          newMsgs[lastIndex] = { ...lastMsg, content: lastMsg.content + textToShow };
                      }
                      return newMsgs;
                  });

                  // TTS
                  if (enableTTS) {
                      bufferText += textToShow;
                      if (/[。！？\.\!\?\:\n]/.test(textToShow)) {
                          addToQueue(bufferText);
                          bufferText = "";
                      }
                  }
              }
          }
      }
      if (enableTTS && bufferText.trim()) addToQueue(bufferText);
  };

  const startMockInterview = () => {
      setShowStartInterviewBtn(false);
      handleSend("我准备好了，请扮演面试官，基于上述 JD 对我进行模拟面试。");
  };

  const formatReportToMarkdown = (data: any) => {
      const { meta, tech_questions, hr_questions, company_analysis } = data;
      return `## 📊 ${meta.company_name || '岗位'} 分析\n\n**技术栈**: \`${meta.tech_stack.join('`, `')}\`\n\n${company_analysis ? `> 🏢 **公司**: ${company_analysis}\n\n` : ''}### 🛠️ 推荐技术题\n${tech_questions.map((q:any,i:number)=>`**Q${i+1}: ${q.question}**\n> ${q.reference_answer}`).join('\n\n')}`;
  };

  const fetchSessions = async (token: string) => {
    try {
      const res = await fetch("http://127.0.0.1:8000/api/v1/history/sessions", { headers: { Authorization: `Bearer ${token}` } });
      if (res.ok) setSessions(await res.json());
    } catch (e) { console.error(e); }
  };
  const loadSession = async (id: number) => {
      /* 保持之前的代码 */
      const token = localStorage.getItem("token");
      if (!token) return;
      setCurrentSessionId(id);
      stopAudio();
      setIsLoading(true);
      try {
        const res = await fetch(`http://127.0.0.1:8000/api/v1/history/messages/${id}`, { headers: { Authorization: `Bearer ${token}` } });
        if (res.ok) {
            const msgs = await res.json();
            setMessages(msgs.map((m:any) => ({ role: m.role, content: m.content.startsWith('{') ? formatReportToMarkdown(JSON.parse(m.content)) : m.content, isJson: false })));
        }
      } finally { setIsLoading(false); }
  };

  const handleLogout = () => { localStorage.removeItem("token"); router.push("/login"); };

  return (
    <div className="flex h-screen bg-[#f9fafb] text-gray-800 font-sans overflow-hidden">
      <Sidebar
        username={username} sessions={sessions} currentSessionId={currentSessionId} mode={mode} setMode={setMode}
        onNewChat={() => { setCurrentSessionId(null); setMessages([]); stopAudio(); setShowStartInterviewBtn(false); }}
        onLoadSession={loadSession} onLogout={handleLogout}
      />

      <div className="flex-1 flex flex-col h-full bg-white min-w-0 relative">

        {/* --- Header (顶部工具栏) --- */}
        <div className="h-14 border-b flex items-center justify-between px-4 flex-shrink-0">
            <div className="flex items-center gap-3">
                <span className="font-bold text-lg text-gray-800">
                    {currentSessionId ? `会话 #${currentSessionId}` : '新会话'}
                </span>
                <span className={clsx("text-xs px-2 py-0.5 rounded-full font-medium", mode === 'mock' ? "bg-purple-100 text-purple-700" : "bg-blue-100 text-blue-700")}>
                    {mode === 'guide' ? 'JD 分析模式' : '模拟面试模式'}
                </span>
            </div>

            {/* ✅ 语音开关按钮 */}
            <button
                onClick={() => setIsTTSEnabled(!isTTSEnabled)}
                className={clsx(
                    "flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm transition-all border",
                    isTTSEnabled
                        ? "bg-green-50 text-green-700 border-green-200 hover:bg-green-100"
                        : "bg-gray-50 text-gray-500 border-gray-200 hover:bg-gray-100"
                )}
                title={isTTSEnabled ? "点击关闭语音播报" : "点击开启语音播报"}
            >
                {isTTSEnabled ? <Volume2 size={16} /> : <VolumeX size={16} />}
                <span className="hidden sm:inline">{isTTSEnabled ? "语音开" : "语音关"}</span>
            </button>
        </div>

        <MessageList
            messages={messages} isLoading={isLoading}
            showStartInterviewBtn={showStartInterviewBtn} onStartMockInterview={startMockInterview}
        />

        <ChatInput
          mode={mode} isLoading={isLoading} onSend={handleSend}
          onFileUpload={()=>{}} onAudioUpload={(blob) => { /* ASR */ }}
        />
      </div>
    </div>
  );
}