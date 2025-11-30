"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Volume2 } from "lucide-react";
// 1. 引入 dynamic
import dynamic from "next/dynamic";

import Sidebar from "@/components/Sidebar";
import MessageList from "@/components/MessageList";
import { useAudioQueue } from "@/hooks/useAudioQueue";
import { Message, Session, ChatMode } from "@/types/chat";

// 2. 动态导入 ChatInput (禁用 SSR)
// 这是解决 Worker 报错的唯一方法，确保录音库只在浏览器加载
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

  // --- API: 获取历史会话列表 ---
  const fetchSessions = async (token: string) => {
    try {
      const res = await fetch("http://127.0.0.1:8000/api/v1/history/sessions", {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setSessions(data);
      }
    } catch (e) { console.error(e); }
  };

  // --- API: 加载会话 ---
  const loadSession = async (sessionId: number) => {
    const token = localStorage.getItem("token");
    if (!token) return;

    setCurrentSessionId(sessionId);
    stopAudio(); // 切换时停止播放
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

  // --- 交互: 文件上传 ---
  const handleFileUpload = async (file: File) => {
    const token = localStorage.getItem("token");
    if (!token) return;

    setIsLoading(true);
    setMessages(prev => [...prev, { role: "user", content: `📄 上传简历: **${file.name}**` }]);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch("http://127.0.0.1:8000/api/v1/upload-resume", {
        method: "POST",
        headers: { "Authorization": `Bearer ${token}` },
        body: formData
      });

      if (res.ok) {
        const data = await res.json();
        setMessages(prev => [...prev, {
            role: "assistant",
            content: `✅ **简历解析成功！**\n\n已提取并记忆 ${data.new_entries} 条关键信息。\n关键事实：\n${data.extracted_facts.map((f:string) => `- ${f}`).join('\n')}`
        }]);
      } else {
        throw new Error("上传失败");
      }
    } catch (e: any) {
      setMessages(prev => [...prev, { role: "assistant", content: `❌ 简历上传失败: ${e.message}` }]);
    } finally {
      setIsLoading(false);
    }
  };

  // --- 交互: 语音上传 (ASR) ---
  // 这里只负责接收 Blob 并上传，不负责录音过程
  const handleAudioUpload = async (blob: Blob) => {
      setIsLoading(true);
      const formData = new FormData();
      formData.append("file", blob, "voice.wav");

      try {
          const token = localStorage.getItem("token");
          const res = await fetch("http://127.0.0.1:8000/api/v1/audio/transcribe", {
              method: "POST",
              headers: { "Authorization": `Bearer ${token}` },
              body: formData
          });
          const data = await res.json();
          if (data.text) {
              // 识别成功后，直接调用发送逻辑
              handleSend(data.text);
          }
      } catch (e) {
          alert("语音识别失败");
          setIsLoading(false);
      }
  };

  // --- 交互: 核心发送逻辑 ---
  const handleSend = async (text: string) => {
    const token = localStorage.getItem("token");
    if (!token) return;

    stopAudio(); // 发送时停止之前的播放
    setIsLoading(true);
    setMessages(prev => [...prev, { role: "user", content: text }]);

    try {
        // A. 连续对话
        if (currentSessionId) {
            setMessages(prev => [...prev, { role: "assistant", content: "" }]);
            const res = await fetch("http://127.0.0.1:8000/api/v1/chat/stream", {
                method: "POST",
                headers: { "Content-Type": "application/json", "Authorization": `Bearer ${token}` },
                body: JSON.stringify({ session_id: currentSessionId, content: text })
            });
            await readStream(res, mode === 'mock');
            return;
        }

        // B. 新 JD 分析
        if (mode === 'guide') {
            const res = await fetch("http://127.0.0.1:8000/api/v1/generate-guide", {
                method: "POST",
                headers: { "Content-Type": "application/json", "Authorization": `Bearer ${token}` },
                body: JSON.stringify({ jd_text: text })
            });
            const data = await res.json();
            setMessages(prev => [...prev, { role: "assistant", content: formatReportToMarkdown(data), isJson: true }]);
            fetchSessions(token);
        }
        // C. 新模拟面试
        else {
            setMessages(prev => [...prev, { role: "assistant", content: "" }]);
            const res = await fetch("http://127.0.0.1:8000/api/v1/stream/mock-interview", {
                method: "POST",
                headers: { "Content-Type": "application/json", "Authorization": `Bearer ${token}` },
                body: JSON.stringify({ jd_text: text })
            });
            await readStream(res, true);
            fetchSessions(token);
        }

    } catch (e) {
        setMessages(prev => [...prev, { role: "assistant", content: "❌ 请求失败" }]);
    } finally {
        setIsLoading(false);
    }
  };

 // --- 5. 流式读取 (支持 DeepSeek 思考过程 + 分句 TTS) ---
  const readStream = async (res: Response, enableTTS: boolean) => {
      if (!res.body) return;
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let done = false;
      let bufferText = ""; // TTS 专用缓冲池

      while (!done) {
          const { value, done: d } = await reader.read();
          done = d;
          const chunk = decoder.decode(value, { stream: true });
          const lines = chunk.split("\n\n");

          for (const line of lines) {
              if (line.startsWith("data: ")) {
                  const dataStr = line.replace("data: ", "").trim();
                  if (dataStr === "[DONE]") break;
                  if (!dataStr) continue;

                  try {
                      // 1. 尝试解析为 JSON 事件
                      const payload = JSON.parse(dataStr);

                      setMessages(prev => {
                          const newMsgs = [...prev];
                          const lastMsg = newMsgs[newMsgs.length - 1];

                          if (lastMsg.role === "assistant") {
                              // --- A. 处理思考过程 (Thought) ---
                              if (payload.type === 'thought') {
                                  const currentThoughts = lastMsg.thoughts || [];
                                  // 去重：防止同样的思考步骤重复添加
                                  if (!currentThoughts.includes(payload.content)) {
                                      lastMsg.thoughts = [...currentThoughts, payload.content];
                                  }
                              }
                              // --- B. 处理正文内容 (Token/Result) ---
                              else if (payload.type === 'token' || payload.type === 'result') {
                                  // 如果是 result 类型(JSON字符串)，直接替换 content
                                  if (payload.type === 'result') {
                                      // 这是一个Hack，如果是最终JSON报告，我们暂存到content里
                                      // 实际渲染时 formatReportToMarkdown 会处理它
                                      lastMsg.content = payload.content;
                                      lastMsg.isJson = true; // 标记为 JSON
                                  } else {
                                      // 普通流式 token，追加
                                      lastMsg.content += payload.content;
                                  }
                              }
                          }
                          return newMsgs;
                      });

                      // --- C. TTS 处理 (只读正文，不读思考) ---
                      if (enableTTS && (payload.type === 'token' || !payload.type)) {
                          const text = payload.content || "";
                          bufferText += text;
                          // 分句检测
                          if (/[。！？\.\!\?\:\n]/.test(text)) {
                              addToQueue(bufferText);
                              bufferText = "";
                          }
                      }

                  } catch (e) {
                      // --- D. 兼容旧接口 (纯文本流) ---
                      // 如果 JSON.parse 失败，说明是旧接口发的纯文本
                      const text = dataStr;
                      setMessages(prev => {
                          const newMsgs = [...prev];
                          const lastMsg = newMsgs[newMsgs.length - 1];
                          if (lastMsg.role === "assistant") lastMsg.content += text;
                          return newMsgs;
                      });

                      if (enableTTS) {
                          bufferText += text;
                          if (/[。！？\.\!\?\:\n]/.test(text)) {
                              addToQueue(bufferText);
                              bufferText = "";
                          }
                      }
                  }
              }
          }
      }

      // 播放剩余的 TTS 缓冲
      if (enableTTS && bufferText.trim()) {
          addToQueue(bufferText);
      }
  };

  // --- Markdown 格式化 ---
  const formatReportToMarkdown = (data: any) => {
      const { meta, tech_questions, hr_questions, company_analysis, reference_sources } = data;
      return `## 📊 ${meta.company_name || '岗位'} 分析\n\n**技术栈**: \`${meta.tech_stack.join('`, `')}\`\n\n${company_analysis ? `> 🏢 **公司**: ${company_analysis}\n\n` : ''}### 🛠️ 技术题\n${tech_questions.map((q:any,i:number)=>`**Q${i+1}: ${q.question}**\n> ${q.reference_answer}`).join('\n\n')} \n\n ### 💬 行为面试\n${hr_questions.map((q:any,i:number)=>`**Q${i+1}: ${q.question}**`).join('\n\n')} ${reference_sources?.length ? `\n---\n📚 **推荐阅读**: ${reference_sources.join(', ')}` : ''}`;
  };

  // --- 交互: 退出 ---
  const handleLogout = () => {
    localStorage.removeItem("token");
    router.push("/login");
  };

  return (
    <div className="flex h-screen bg-[#f9fafb] text-gray-800 font-sans overflow-hidden">

      {/* 引用子组件: 侧边栏 */}
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

        {/* 引用子组件: 消息列表 */}
        <MessageList messages={messages} isLoading={isLoading} />

        {/* 引用子组件: 底部输入区 */}
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