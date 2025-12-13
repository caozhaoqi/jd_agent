"use client";

import { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
// 图标
import { Volume2, VolumeX, PanelRightOpen, PanelRightClose, Database } from "lucide-react";
import dynamic from "next/dynamic";
import clsx from "clsx";

// 引入组件和 Hook
import Sidebar from "@/components/Sidebar";
import MessageList from "@/components/MessageList";
import { useAudioQueue } from "@/hooks/useAudioQueue";
import { Message, Session, ChatMode } from "@/types/chat";
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

  // 🟢 修改 1: mode 类型扩展逻辑在实际使用中体现，默认 'guide'
  // 实际上 ChatMode 类型定义需要在 @/types/chat 中包含 'rag'
  const [mode, setMode] = useState<ChatMode | 'rag'>('guide');

  const [username, setUsername] = useState("Guest");
  const [sessions, setSessions] = useState<Session[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<number | null>(null);

  const [showDashboard, setShowDashboard] = useState(true);
  const [dashboardData, setDashboardData] = useState<DashboardState>({
    currentStep: "",
    userProfile: [],
    ragSources: []
  });

  const [isTTSEnabled, setIsTTSEnabled] = useState(true);
  const isTTSRef = useRef(isTTSEnabled);
  const [showStartInterviewBtn, setShowStartInterviewBtn] = useState(false);

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

  useEffect(() => {
    isTTSRef.current = isTTSEnabled;
    if (!isTTSEnabled) {
        stopAudio();
    }
  }, [isTTSEnabled, stopAudio]);


  const unlockAudioContext = () => {
    // ... (保持原有代码)
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

  // 🟢 修改 2: 核心发送逻辑，增加 RAG 分支
  const handleSend = async (text: string) => {
    const msgToSend = text;
    if (!msgToSend?.trim() || isLoading) return;

    unlockAudio();

    const token = localStorage.getItem("token");
    if (!token) return;

    stopAudio();
    setIsLoading(true);
    setShowStartInterviewBtn(false);
    setMessages(prev => [...prev, { role: "user", content: msgToSend }]);

    try {
        // 🟢 分支 A: 知识库问答 (RAG)
        if (mode === 'rag') {
            // 知识库问答通常不流式传输，或者流式逻辑不同，这里演示 JSON 响应
            // 先放一个 loading 占位
            setMessages(prev => [...prev, { role: "assistant", content: "🔍 正在检索知识库..." }]);

            const res = await fetch("http://127.0.0.1:8000/api/v1/qa/knowledge-base", {
                method: "POST",
                headers: { "Content-Type": "application/json", "Authorization": `Bearer ${token}` },
                body: JSON.stringify({ question: msgToSend }) // 注意字段名为 question
            });

           if (!res.ok) {
                // 读取后端返回的具体错误信息
                const errorText = await res.text();
                console.error("🔴 后端报错详情:", errorText);
                throw new Error(`RAG API Error: ${res.status} - ${errorText}`);
            }

            const data = await res.json();

            // 格式化 RAG 返回结果 (回答 + 来源)
            const formattedContent = formatRAGResponse(data);

            // 更新最后一条消息
            setMessages(prev => {
                const newMsgs = [...prev];
                newMsgs[newMsgs.length - 1] = {
                    role: "assistant",
                    content: formattedContent,
                    isJson: true // 标记为 Markdown 渲染
                };
                return newMsgs;
            });

            // 如果开启语音，朗读答案部分
            if (isTTSEnabled) {
                addToQueue(data.answer);
            }
        }
        // 🔵 分支 B: 连续对话 (Mock Interview)
        else if (currentSessionId) {
            setMessages(prev => [...prev, { role: "assistant", content: "" }]);
            const res = await fetch("http://127.0.0.1:8000/api/v1/chat/stream", {
                method: "POST",
                headers: { "Content-Type": "application/json", "Authorization": `Bearer ${token}` },
                body: JSON.stringify({ session_id: currentSessionId, content: msgToSend })
            });
            await readStream(res, isTTSEnabled);
        }
        // 🟡 分支 C: JD 分析指南
        else if (mode === 'guide') {
            setMessages(prev => [...prev, { role: "assistant", content: "" }]);
            const res = await fetch("http://127.0.0.1:8000/api/v1/stream/generate-guide", {
                method: "POST",
                headers: { "Content-Type": "application/json", "Authorization": `Bearer ${token}` },
                body: JSON.stringify({ jd_text: msgToSend })
            });
            await readStream(res, false);
            fetchSessions(token);
        }
        // 🟣 分支 D: 开启新模拟面试
        else {
            setMessages(prev => [...prev, { role: "assistant", content: "" }]);
            const res = await fetch("http://127.0.0.1:8000/api/v1/stream/mock-interview", {
                method: "POST",
                headers: { "Content-Type": "application/json", "Authorization": `Bearer ${token}` },
                body: JSON.stringify({ jd_text: msgToSend })
            });
            await readStream(res, isTTSEnabled);
            fetchSessions(token);
        }
    } catch (e) {
        console.error(e);
        setMessages(prev => {
            // 如果是 loading 占位，替换掉
            const newMsgs = [...prev];
            if (newMsgs[newMsgs.length - 1].role === "assistant") {
                 newMsgs[newMsgs.length - 1] = { role: "assistant", content: "❌ 请求失败，请检查网络或后端服务。" };
                 return newMsgs;
            }
            return [...prev, { role: "assistant", content: "❌ 请求失败。" }];
        });
    } finally {
        setIsLoading(false);
    }
  };

  // 🟢 新增辅助函数: 格式化 RAG 响应
  const formatRAGResponse = (data: { answer: string; sources: string[] }) => {
    const { answer, sources } = data;
    if (!sources || sources.length === 0) return answer;
    const sourceList = sources.map((s) => `- 📄 ${s}`).join("\n");
    return `${answer}\n\n---\n**📚 引用来源:**\n${sourceList}`;
  };

  // --- 流式读取 (保持不变) ---
  const readStream = async (res: Response, _ignore: boolean) => {
      // ... (代码与你提供的一致，此处省略以节省篇幅，逻辑不需要变)
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
                          const payload = JSON.parse(dataStr);
                          setMessages(prev => {
                              if (prev.length === 0) return prev;
                              const newMsgs = [...prev];
                              const lastIndex = newMsgs.length - 1;
                              const lastMsg = newMsgs[lastIndex];

                              if (lastMsg.role === "assistant") {
                                  if (payload.type === 'thought') {
                                      const currentThoughts = lastMsg.thoughts || [];
                                      if (currentThoughts[currentThoughts.length - 1] !== payload.content) {
                                          newMsgs[lastIndex] = { ...lastMsg, thoughts: [...currentThoughts, payload.content] };
                                      }
                                  }
                                  else if (payload.type === 'result') {
                                      try {
                                          const reportData = JSON.parse(payload.content);
                                          const markdown = formatReportToMarkdown(reportData);
                                          newMsgs[lastIndex] = { ...lastMsg, content: markdown, isJson: true };
                                          if (reportData.session_id) {
                                              setCurrentSessionId(reportData.session_id);
                                              setShowStartInterviewBtn(true);
                                          }
                                      } catch (e) { console.error("Report Parse Error", e); }
                                  }
                                  else if (payload.type === 'token') {
                                      newMsgs[lastIndex] = { ...lastMsg, content: lastMsg.content + (payload.content || "") };
                                  }
                              }
                              return newMsgs;
                          });

                          if (payload.type === 'data') {
                              const { key, value } = payload;
                              setDashboardData(prev => {
                                  if (key === 'user_profile') return { ...prev, userProfile: value };
                                  if (key === 'rag_sources') return { ...prev, ragSources: value };
                                  if (key === 'current_step') return { ...prev, currentStep: value };
                                  return prev;
                              });
                          }

                          if (isTTSRef.current && payload.type === 'token') {
                              const text = payload.content || "";
                              bufferText += text;
                              if (/[。！？\.\!\?\:\n]/.test(text)) {
                                  addToQueue(bufferText);
                                  bufferText = "";
                              }
                          }
                      } catch (e) { console.warn("Stream parse error:", e); }
                  }
              }
          }
      } catch (err) { console.error("Stream failed:", err); } finally {
          if (isTTSRef.current && bufferText.trim()) addToQueue(bufferText);
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
      const token = localStorage.getItem("token");
      if (!token) return;
      setCurrentSessionId(id);
      // 加载旧会话时，退出 RAG 模式，进入 mock 模式
      setMode('mock');
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
        username={username}
        sessions={sessions}
        currentSessionId={currentSessionId}
        mode={mode as ChatMode} // 类型断言适配 Sidebar
        setMode={(m) => {
            setMode(m);
            // 切换模式时清空上下文
            if(m !== 'mock') setCurrentSessionId(null);
            setMessages([]);
        }}
        onNewChat={() => { setCurrentSessionId(null); setMessages([]); stopAudio(); setShowStartInterviewBtn(false); }}
        onLoadSession={loadSession}
        onLogout={handleLogout}
      />

      <div className="flex-1 flex flex-col h-full bg-white min-w-0 relative">

        {/* --- Header --- */}
        <div className="h-14 border-b flex items-center justify-between px-4 flex-shrink-0">
            <div className="flex items-center gap-3">
                <span className="font-bold text-lg text-gray-800">
                    {currentSessionId ? `会话 #${currentSessionId}` : (mode === 'rag' ? '知识库问答' : '新会话')}
                </span>
                {/* 状态标签 */}
                <span className={clsx(
                    "text-xs px-2 py-0.5 rounded-full font-medium",
                    mode === 'mock' ? "bg-purple-100 text-purple-700" :
                    mode === 'rag' ? "bg-orange-100 text-orange-700" :
                    "bg-blue-100 text-blue-700"
                )}>
                    {mode === 'guide' ? 'JD 分析模式' : mode === 'rag' ? '知识库检索' : '模拟面试模式'}
                </span>
            </div>

            <div className="flex items-center gap-2">
                {/* 🟢 修改 3: 知识库切换按钮 */}
                <button
                    onClick={() => {
                        if (mode === 'rag') setMode('guide'); // 切回默认
                        else {
                            setMode('rag');
                            setCurrentSessionId(null);
                            setMessages([{ role: "assistant", content: "📚 已切换到**知识库模式**。请问我任何关于技术栈或博客的问题。" }]);
                        }
                    }}
                    className={clsx(
                        "flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm transition-all border",
                        mode === 'rag'
                            ? "bg-orange-50 text-orange-700 border-orange-200 hover:bg-orange-100"
                            : "bg-gray-50 text-gray-500 border-gray-200 hover:bg-gray-100"
                    )}
                    title="切换知识库问答模式"
                >
                    <Database size={16} />
                    <span className="hidden sm:inline">查知识库</span>
                </button>

                {/* 语音开关 */}
                <button
                    onClick={() => setIsTTSEnabled(!isTTSEnabled)}
                    className={clsx(
                        "flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm transition-all border",
                        isTTSEnabled
                            ? "bg-green-50 text-green-700 border-green-200 hover:bg-green-100"
                            : "bg-gray-50 text-gray-500 border-gray-200 hover:bg-gray-100"
                    )}
                >
                    {isTTSEnabled ? <Volume2 size={16} /> : <VolumeX size={16} />}
                </button>

                {/* Dashboard 开关 */}
                <button
                    onClick={() => setShowDashboard(!showDashboard)}
                    className="p-2 rounded-lg hover:bg-gray-100 text-gray-500"
                >
                    {showDashboard ? <PanelRightClose size={20}/> : <PanelRightOpen size={20}/>}
                </button>
            </div>
        </div>

        <MessageList
            messages={messages} isLoading={isLoading}
            showStartInterviewBtn={showStartInterviewBtn} onStartMockInterview={startMockInterview}
        />

        {/* 🟢 修改 4: 输入框 Placeholder 动态变化 */}
        <ChatInput
          mode={mode as ChatMode}
          isLoading={isLoading}
          onSend={handleSend}
          onFileUpload={()=>{}}
          onAudioUpload={(blob) => { /* ASR */ }}
          placeholder={mode === 'rag' ? "请输入问题查询知识库..." : undefined}
        />
      </div>

      {/* 右侧仪表盘 */}
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