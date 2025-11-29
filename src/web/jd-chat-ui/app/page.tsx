"use client";

import { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import ReactMarkdown from "react-markdown";
import {
  Send, Bot, User, Plus, MessageSquare,
  Loader2, Paperclip, LogOut, Mic, LayoutDashboard
} from "lucide-react";
import clsx from "clsx";

// --- 类型定义 ---
type Message = {
  role: "user" | "assistant";
  content: string;
  isJson?: boolean;
};

type Session = {
  id: number;
  title: string;
};

export default function Home() {
  const router = useRouter();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // --- 状态 ---
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [mode, setMode] = useState<'guide' | 'mock'>('guide'); // 模式
  const [username, setUsername] = useState("Guest");
  const [sessions, setSessions] = useState<Session[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<number | null>(null); // 当前会话ID

  // --- 初始化 ---
  useEffect(() => {
    const token = localStorage.getItem("token");
    const user = localStorage.getItem("username");
    if (!token) { router.push("/login"); return; }

    setUsername(user || "User");
    if (messages.length === 0) {
        setMessages([{
            role: "assistant",
            content: `你好 **${user}**！我是你的 AI 面试助手。\n\n请选择左侧模式，或者直接发送 JD 开始。`
        }]);
    }
    fetchSessions(token);
  }, []);

  // --- 自动滚动 ---
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  // --- API 调用 ---
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
    setIsLoading(true);
    try {
      const res = await fetch(`http://127.0.0.1:8000/api/v1/history/messages/${sessionId}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const msgs = await res.json();
        // 格式化历史消息
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

  // --- 核心逻辑: 发送消息 ---
  const handleSend = async () => {
    if (!input.trim() || isLoading) return;
    const token = localStorage.getItem("token");
    if (!token) return;

    const userMsg = input;
    setInput("");
    setMessages(prev => [...prev, { role: "user", content: userMsg }]);
    setIsLoading(true);

    try {
        // 场景 1: 已有会话 -> 进行连续多轮对话 (Chat)
        if (currentSessionId) {
            setMessages(prev => [...prev, { role: "assistant", content: "" }]); // 占位

            const res = await fetch("http://127.0.0.1:8000/api/v1/chat/stream", {
                method: "POST",
                headers: { "Content-Type": "application/json", "Authorization": `Bearer ${token}` },
                body: JSON.stringify({ session_id: currentSessionId, content: userMsg })
            });
            await readStream(res);
            return;
        }

        // 场景 2: 新会话 -> 模式 A: JD 指南
        if (mode === 'guide') {
            const res = await fetch("http://127.0.0.1:8000/api/v1/generate-guide", {
                method: "POST",
                headers: { "Content-Type": "application/json", "Authorization": `Bearer ${token}` },
                body: JSON.stringify({ jd_text: userMsg })
            });
            const data = await res.json();
            setMessages(prev => [...prev, { role: "assistant", content: formatReportToMarkdown(data), isJson: true }]);
            fetchSessions(token); // 刷新列表，获取新生成的 session_id (虽然前端此时还没拿到ID，下次点击历史记录即可)
            // 提示用户点击侧边栏
            alert("指南已生成！请点击左侧历史记录以继续对此话题进行对话。");
        }

        // 场景 3: 新会话 -> 模式 B: 开启模拟面试
        else {
            setMessages(prev => [...prev, { role: "assistant", content: "" }]);
            // 这里我们调用一个特殊的接口来"初始化"面试，并返回 Session ID (建议后端 mock-interview 返回 session_id)
            // 为了简化，这里我们假设后端 stream/mock-interview 只是个开场白，
            // 更好的做法是先创建一个 Session，然后开始 Chat。
            // 这里暂用临时方案：流式输出开场白。注意：因为没有 Session ID，下一句会因为没有 ID 而报错。
            // **修正方案**：为了支持连续对话，模拟面试的第一步应该是“创建 Session + 设定 System Prompt”。

            // 这里演示简单的流式回显，实际项目建议先 Create Session
            const res = await fetch("http://127.0.0.1:8000/api/v1/stream/mock-interview", {
                method: "POST",
                headers: { "Content-Type": "application/json", "Authorization": `Bearer ${token}` },
                body: JSON.stringify({ jd_text: userMsg })
            });
            await readStream(res);

            // ⚠️ 临时修补：为了让下一句能对话，提示用户刷新。
            // 完美方案是在 mock-interview 接口返回 session_id，前端 setSessionId。
            fetchSessions(token);
        }

    } catch (e) {
        setMessages(prev => [...prev, { role: "assistant", content: "❌ 请求失败" }]);
    } finally {
        setIsLoading(false);
    }
  };

  // --- 辅助：读取 SSE 流 ---
  const readStream = async (res: Response) => {
      if (!res.body) return;
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let done = false;
      let text = "";

      while (!done) {
          const { value, done: d } = await reader.read();
          done = d;
          const chunk = decoder.decode(value, { stream: true });
          const lines = chunk.split("\n\n");
          for (const line of lines) {
              if (line.startsWith("data: ")) {
                  const content = line.replace("data: ", "");
                  if (content === "[DONE]") break;
                  text += content;
                  setMessages(prev => {
                      const newMsgs = [...prev];
                      if (newMsgs[newMsgs.length-1].role === "assistant") {
                          newMsgs[newMsgs.length-1].content = text;
                      }
                      return newMsgs;
                  });
              }
          }
      }
  };

  // --- 辅助：Markdown 格式化 ---
  const formatReportToMarkdown = (data: any) => {
      // (保持之前的格式化逻辑不变)
      const { meta, tech_questions, hr_questions, company_analysis } = data;
      return `## 📊 ${meta.company_name || '岗位'} 分析\n\n**技术栈**: \`${meta.tech_stack.join('`, `')}\`\n\n${company_analysis ? `> 🏢 **公司**: ${company_analysis}\n\n` : ''}### 🛠️ 技术题\n${tech_questions.map((q:any,i:number)=>`**Q${i+1}: ${q.question}**\n> ${q.reference_answer}`).join('\n\n')}`;
  };

  return (
    <div className="flex h-screen bg-[#f9fafb] text-gray-800 font-sans overflow-hidden">

      {/* 左侧侧边栏 */}
      <div className="w-[260px] bg-[#fcfdfd] border-r border-gray-200 hidden md:flex flex-col flex-shrink-0">
        <div className="p-4 space-y-2">
            {/* 模式切换 Tab */}
            <div className="bg-gray-100 p-1 rounded-lg flex text-sm mb-4">
                <button onClick={() => setMode('guide')} className={clsx("flex-1 py-1.5 rounded-md transition-all flex justify-center gap-2", mode === 'guide' ? "bg-white shadow text-blue-600 font-bold" : "text-gray-500")}>
                    <LayoutDashboard size={14} /> JD 分析
                </button>
                <button onClick={() => setMode('mock')} className={clsx("flex-1 py-1.5 rounded-md transition-all flex justify-center gap-2", mode === 'mock' ? "bg-white shadow text-purple-600 font-bold" : "text-gray-500")}>
                    <Mic size={14} /> 模拟面试
                </button>
            </div>
            <button onClick={() => {setCurrentSessionId(null); setMessages([]);}} className="w-full py-2 bg-blue-50 text-blue-600 rounded-md text-sm font-medium border border-blue-100 flex justify-center items-center gap-2">
                <Plus size={16} /> 新建会话
            </button>
        </div>

        {/* 历史列表 */}
        <div className="flex-1 overflow-y-auto px-2 scrollbar-thin">
            {sessions.map(s => (
                <div key={s.id} onClick={() => loadSession(s.id)} className={clsx("px-3 py-2.5 text-sm rounded-md cursor-pointer mb-1 truncate flex items-center gap-2", currentSessionId === s.id ? "bg-gray-100 font-medium" : "hover:bg-gray-50 text-gray-600")}>
                    <MessageSquare size={14} /> {s.title}
                </div>
            ))}
        </div>

        {/* 用户信息 */}
        <div className="p-4 border-t flex justify-between items-center text-sm text-gray-600">
            <span className="font-bold">{username}</span>
            <LogOut size={16} className="cursor-pointer hover:text-red-500" onClick={() => {localStorage.clear(); router.push('/login')}}/>
        </div>
      </div>

      {/* 右侧主区域 (Flex Layout 修复核心) */}
      <div className="flex-1 flex flex-col h-full bg-white min-w-0">

        {/* 顶部 Header */}
        <div className="h-14 border-b flex items-center justify-between px-4 flex-shrink-0">
            <span className="font-bold text-lg">{mode === 'guide' ? '岗位分析' : '模拟面试'}</span>
            <span className="text-xs text-gray-400 bg-gray-100 px-2 py-1 rounded">
                {currentSessionId ? `会话 #${currentSessionId}` : '新会话'}
            </span>
        </div>

        {/* 消息列表 (flex-1 自动撑开，scroll 在这里) */}
        <div className="flex-1 overflow-y-auto p-4 md:p-6 scroll-smooth">
            <div className="max-w-3xl mx-auto space-y-6">
                {messages.map((msg, idx) => (
                    <div key={idx} className={clsx("flex gap-4", msg.role === "user" ? "flex-row-reverse" : "")}>
                        <div className={clsx("w-8 h-8 rounded-full flex-shrink-0 flex items-center justify-center border", msg.role === "assistant" ? "bg-white text-blue-600" : "bg-gray-800 text-white")}>
                            {msg.role === "assistant" ? <Bot size={18} /> : <User size={18} />}
                        </div>
                        <div className={clsx("max-w-[85%] rounded-2xl px-5 py-3 text-sm leading-7 shadow-sm border", msg.role === "user" ? "bg-blue-50 border-blue-100" : "bg-white border-gray-100")}>
                      {msg.role === "assistant" ? (
                        // 正确：样式给外层 div，ReactMarkdown 只负责渲染
                        <div className="prose prose-sm max-w-none prose-headings:text-gray-800 prose-p:text-gray-600 prose-li:text-gray-600">
                            <ReactMarkdown>{msg.content}</ReactMarkdown>
                        </div>
                    ) : msg.content}</div>
                    </div>
                ))}
                {isLoading && <div className="flex justify-center py-4"><Loader2 className="animate-spin text-blue-500" /></div>}
                <div ref={messagesEndRef} />
            </div>
        </div>

        {/* 底部输入框 (固定在底部，flex-shrink-0 防止被压缩) */}
        <div className="flex-shrink-0 p-4 border-t border-gray-100 bg-white">
            <div className="max-w-3xl mx-auto bg-white border border-gray-200 shadow-lg rounded-2xl p-2 focus-within:ring-2 focus-within:ring-blue-100 transition-shadow">
                <textarea
                    value={input}
                    onChange={e => setInput(e.target.value)}
                    onKeyDown={e => { if(e.key==='Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); } }}
                    placeholder={mode === 'guide' ? "发送岗位 JD..." : "请输入你的回答..."}
                    className="w-full resize-none border-none outline-none text-gray-700 px-3 py-2 max-h-[150px] min-h-[44px]"
                    rows={1}
                />
                <div className="flex justify-between items-center mt-1 px-1">
                    <div className="flex gap-2 text-gray-400">
                        <input type="file" ref={fileInputRef} className="hidden" accept=".pdf,.txt" />
                        <button onClick={() => fileInputRef.current?.click()} className="hover:text-blue-600 p-1.5 hover:bg-gray-50 rounded"><Paperclip size={18} /></button>
                    </div>
                    <button onClick={handleSend} disabled={!input.trim() || isLoading} className="bg-blue-600 text-white p-2 rounded-lg hover:bg-blue-700 disabled:opacity-50">
                        <Send size={16} />
                    </button>
                </div>
            </div>
            <div className="text-center text-xs text-gray-400 mt-2">AI生成内容仅供参考</div>
        </div>

      </div>
    </div>
  );
}