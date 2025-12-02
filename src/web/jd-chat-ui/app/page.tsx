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
import { PanelRightOpen, PanelRightClose } from "lucide-react"; // 新图标
import BrainDashboard, { DashboardState } from "@/components/BrainDashboard";

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
 // ✅ Dashboard 状态
  const [showDashboard, setShowDashboard] = useState(true); // 控制面板开关
  const [dashboardData, setDashboardData] = useState<DashboardState>({
    currentStep: "",
    userProfile: [],
    ragSources: []
  });

  // ✅ 新增：全局 TTS 开关 (默认开启)
  const [isTTSEnabled, setIsTTSEnabled] = useState(true);

  const [showStartInterviewBtn, setShowStartInterviewBtn] = useState(false);

  // --- Hook ---
  const { addToQueue, stopAudio, unlockAudio } = useAudioQueue();

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

    // 2. ✅ 关键：用户点击瞬间，立即调用解锁
    // 这会播放那段静音，激活浏览器的 Audio 权限
    unlockAudio();

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
//             const res = await fetch("http://127.0.0.1:8000/api/v1/generate-guide", {
//                 method: "POST",
//                 headers: { "Content-Type": "application/json", "Authorization": `Bearer ${token}` },
//                 body: JSON.stringify({ jd_text: msgToSend })
//             });
//             const data = await res.json();

            // ✅ 新代码：使用流式接口
            // 1. 先创建一个空的 Assistant 消息占位
            setMessages(prev => [...prev, { role: "assistant", content: "" }]);

            const res = await fetch("http://127.0.0.1:8000/api/v1/stream/generate-guide", {
                method: "POST",
                headers: { "Content-Type": "application/json", "Authorization": `Bearer ${token}` },
                body: JSON.stringify({ jd_text: msgToSend })
            });

            // 2. 调用 readStream 读取流 (Dashboard 数据会在这里被解析)
            // 注意：生成指南时通常不需要 TTS 朗读全文，所以第二个参数传 false (或者 true 看你喜好)
            await readStream(res, false);

            // 3. 结束后刷新侧边栏
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

  // --- 5. 流式读取与分句 TTS (修复语法与逻辑) ---
  const readStream = async (res: Response, enableTTS: boolean) => {
      if (!res.body) return;
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let done = false;
      let bufferText = "";

      try {
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
                          // 尝试解析 JSON
                          const payload = JSON.parse(dataStr);

                          // 1. 更新消息 UI (思考流 / 结果 / Token)
                          setMessages(prev => {
                              if (prev.length === 0) return prev;
                              const newMsgs = [...prev];
                              const lastIndex = newMsgs.length - 1;
                              const lastMsg = newMsgs[lastIndex];

                              if (lastMsg.role === "assistant") {
                                  // A. 思考流 (Thought)
                                  if (payload.type === 'thought') {
                                      const currentThoughts = lastMsg.thoughts || [];
                                      // 简单去重
                                      if (currentThoughts[currentThoughts.length - 1] !== payload.content) {
                                          newMsgs[lastIndex] = {
                                              ...lastMsg,
                                              thoughts: [...currentThoughts, payload.content]
                                          };
                                      }
                                  }
                                  // B. 最终结果 (Result) -> 转 Markdown
                                  else if (payload.type === 'result') {
                                      try {
                                          const reportData = JSON.parse(payload.content);
                                          const markdown = formatReportToMarkdown(reportData);

                                          newMsgs[lastIndex] = {
                                              ...lastMsg,
                                              content: markdown,
                                              isJson: true
                                          };

                                          // 如果有 session_id，显示开始面试按钮
                                          if (reportData.session_id) {
                                              setCurrentSessionId(reportData.session_id);
                                              setShowStartInterviewBtn(true);
                                          }
                                      } catch (e) {
                                          console.error("Report Parse Error", e);
                                      }
                                  }
                                  // C. 普通内容流 (Token)
                                  else if (payload.type === 'token') {
                                      newMsgs[lastIndex] = {
                                          ...lastMsg,
                                          content: lastMsg.content + (payload.content || "")
                                      };
                                  }
                              }
                              return newMsgs;
                          });

                          // 2. 更新 Dashboard (Data)
                          if (payload.type === 'data') {
                              const { key, value } = payload;
                              setDashboardData(prev => {
                                  if (key === 'user_profile') return { ...prev, userProfile: value };
                                  if (key === 'rag_sources') return { ...prev, ragSources: value };
                                  if (key === 'current_step') return { ...prev, currentStep: value };
                                  return prev;
                              });
                          }

                          // 3. TTS 处理 (仅针对 token)
                          if (enableTTS && payload.type === 'token' && payload.content) {
                              const text = payload.content;
                              bufferText += text;
                              // 简单的分句检测
                              if (/[。！？\.\!\?\:\n]/.test(text)) {
                                  addToQueue(bufferText);
                                  bufferText = "";
                              }
                          }

                      } catch (e) {
                          // 兼容非 JSON 的纯文本流 (如果有的话)
                          console.warn("Stream parse error or plain text:", e);
                      }
                  }
              }
          }
      } catch (err) {
          console.error("Stream reading failed:", err);
      } finally {
          // 播放剩余的 TTS 缓冲
          if (enableTTS && bufferText.trim()) {
              addToQueue(bufferText);
          }
      }
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
            {/* ✅ Dashboard 开关 */}
               <button
                   onClick={() => setShowDashboard(!showDashboard)}
                   className="p-2 rounded-lg hover:bg-gray-100 text-gray-500"
                   title="切换大脑视图"
               >
                   {showDashboard ? <PanelRightClose size={20}/> : <PanelRightOpen size={20}/>}
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
       {/* ✅ 右侧仪表盘 (动画滑入) */}
      <div className={clsx(
          "bg-[#fcfdfd] border-l border-gray-200 transition-all duration-300 ease-in-out flex flex-col",
          showDashboard ? "w-[300px] translate-x-0" : "w-0 translate-x-full overflow-hidden border-none"
      )}>
          <div className="p-4 border-b border-gray-100 font-bold text-sm text-gray-700">
              🧠 Agent 状态监控
          </div>
          <BrainDashboard data={dashboardData} />
      </div>
    </div>
  );
}