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
  created_at: string;
};

export default function Home() {
  const router = useRouter();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // --- 状态管理 ---
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);

  // 模式切换: 'guide' (生成指南) | 'mock' (模拟面试)
  const [mode, setMode] = useState<'guide' | 'mock'>('guide');

  // 用户与会话状态
  const [username, setUsername] = useState("Guest");
  const [sessions, setSessions] = useState<Session[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<number | null>(null);

  // --- 1. 初始化: 检查登录 & 加载历史会话 ---
  useEffect(() => {
    const token = localStorage.getItem("token");
    const user = localStorage.getItem("username");

    if (!token) {
      router.push("/login");
      return;
    }

    setUsername(user || "User");

    // 初始化欢迎语
    if (messages.length === 0) {
      setMessages([{
        role: "assistant",
        content: `你好 **${user}**！我是你的 AI 面试助手。\n\n你可以：\n1. 发送 **岗位描述 (JD)**，获取面试突击指南。\n2. 点击回形针📎 **上传简历**，更新个人画像。\n3. 切换到 **“模拟面试”** 模式，进行实战演练。`
      }]);
    }

    fetchSessions(token);
  }, []);

  // --- 自动滚动逻辑 ---
  useEffect(() => {
    const scrollToBottom = () => {
      messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };
    // 稍微延迟以确保渲染完成
    const timeoutId = setTimeout(scrollToBottom, 100);
    return () => clearTimeout(timeoutId);
  }, [messages, isLoading]);

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
    } catch (e) {
      console.error("加载历史失败", e);
    }
  };

  // --- API: 加载会话 ---
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
        const formattedMsgs = msgs.map((m: any) => {
          let content = m.content;
          let isJson = false;

          // 尝试解析 JSON 格式的报告
          if (m.role === "assistant") {
            try {
              const jsonData = JSON.parse(m.content);
              if (jsonData && jsonData.meta) {
                content = formatReportToMarkdown(jsonData);
                isJson = true;
              }
            } catch (e) {
              // 普通文本
            }
          }
          return { role: m.role, content: content, isJson: isJson };
        });
        setMessages(formattedMsgs);
      }
    } catch (e) {
      console.error("加载消息失败", e);
    } finally {
      setIsLoading(false);
    }
  };

  // --- 交互: 文件上传 (简历解析) ---
  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

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
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  // --- 交互: 核心发送逻辑 (路由分发) ---
  const handleSend = async () => {
    if (!input.trim() || isLoading) return;
    const token = localStorage.getItem("token");
    if (!token) return;

    const userMsg = input;
    setInput("");
    setMessages(prev => [...prev, { role: "user", content: userMsg }]);
    setIsLoading(true);

    try {
      if (mode === 'guide') {
        // --- 模式 A: 生成面试指南 (普通请求) ---
        const response = await fetch("http://127.0.0.1:8000/api/v1/generate-guide", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}`
          },
          body: JSON.stringify({ jd_text: userMsg }),
        });

        if (!response.ok) throw new Error("生成失败");

        const data = await response.json();
        const markdownReport = formatReportToMarkdown(data);

        setMessages(prev => [...prev, { role: "assistant", content: markdownReport, isJson: true }]);
        fetchSessions(token); // 刷新历史

      } else {
        // --- 模式 B: 模拟面试 (流式请求 SSE) ---
        // 注意：这里我们只实现“开始模拟面试”的触发，真正多轮对话需要后端支持 Chat 接口
        // 这里演示调用 mock-interview 接口开启第一轮

        // 先添加一个空消息占位
        setMessages(prev => [...prev, { role: "assistant", content: "" }]);

        const response = await fetch("http://127.0.0.1:8000/api/v1/stream/mock-interview", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${token}`
            },
            body: JSON.stringify({ jd_text: userMsg }),
        });

        if (!response.ok || !response.body) throw new Error("流式请求失败");

        // 处理流
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let done = false;
        let fullText = "";

        while (!done) {
            const { value, done: doneReading } = await reader.read();
            done = doneReading;
            const chunkValue = decoder.decode(value, { stream: true });

            // 解析 SSE 格式 (data: ...)
            const lines = chunkValue.split("\n\n");
            for (const line of lines) {
                if (line.startsWith("data: ")) {
                    const content = line.replace("data: ", "");
                    if (content === "[DONE]") break;

                    fullText += content;

                    // 实时更新 UI
                    setMessages(prev => {
                        const newMsgs = [...prev];
                        const lastMsg = newMsgs[newMsgs.length - 1];
                        if (lastMsg.role === "assistant") {
                            lastMsg.content = fullText;
                        }
                        return newMsgs;
                    });
                }
            }
        }
      }

    } catch (error) {
      setMessages(prev => [...prev, { role: "assistant", content: "❌ 请求出错，请重试。" }]);
    } finally {
      setIsLoading(false);
    }
  };

  // --- 交互: 新建/退出 ---
  const handleNewChat = () => {
    setCurrentSessionId(null);
    setMessages([{ role: "assistant", content: "已开启新会话。请发送新的 JD。" }]);
  };

  const handleLogout = () => {
    localStorage.removeItem("token");
    router.push("/login");
  };

  return (
    <div className="fixed inset-0 flex bg-[#f9fafb] text-gray-800 font-sans">

      {/* --- 左侧侧边栏 --- */}
      <div className="w-[260px] bg-[#fcfdfd] border-r border-gray-200 hidden md:flex flex-col h-full">
        <div className="p-4 space-y-2">
            {/* 模式切换 */}
            <div className="bg-gray-100 p-1 rounded-lg flex text-sm mb-4">
                <button
                    onClick={() => setMode('guide')}
                    className={clsx(
                        "flex-1 py-1.5 rounded-md transition-all flex items-center justify-center gap-2",
                        mode === 'guide' ? "bg-white shadow-sm text-blue-600 font-medium" : "text-gray-500 hover:text-gray-700"
                    )}
                >
                    <LayoutDashboard size={14} /> JD 分析
                </button>
                <button
                    onClick={() => setMode('mock')}
                    className={clsx(
                        "flex-1 py-1.5 rounded-md transition-all flex items-center justify-center gap-2",
                        mode === 'mock' ? "bg-white shadow-sm text-purple-600 font-medium" : "text-gray-500 hover:text-gray-700"
                    )}
                >
                    <Mic size={14} /> 模拟面试
                </button>
            </div>

            <button onClick={handleNewChat} className="flex items-center gap-2 w-full px-3 py-2 bg-blue-50 text-blue-600 rounded-md text-sm font-medium hover:bg-blue-100 transition-colors border border-blue-100">
                <Plus size={16} /> 新建对话
            </button>
        </div>

        <div className="flex-1 overflow-y-auto px-2 scrollbar-thin">
          <div className="text-xs text-gray-400 px-3 py-2 font-medium">最近记录</div>
          {sessions.map((s) => (
            <div
                key={s.id}
                onClick={() => loadSession(s.id)}
                className={clsx(
                    "flex items-center gap-2 px-3 py-2.5 text-sm rounded-md cursor-pointer mb-1 truncate transition-colors",
                    currentSessionId === s.id ? "bg-gray-100 text-gray-900 font-medium" : "text-gray-600 hover:bg-gray-50"
                )}
            >
              <MessageSquare size={14} className="flex-shrink-0" />
              <span className="truncate">{s.title || "未命名对话"}</span>
            </div>
          ))}
        </div>

        <div className="p-4 border-t border-gray-100 flex items-center justify-between">
             <div className="flex items-center gap-2">
                <div className="w-8 h-8 bg-blue-600 rounded-full text-white flex items-center justify-center font-bold text-xs">{username[0]}</div>
                <span className="text-sm font-medium text-gray-700">{username}</span>
             </div>
             <button onClick={handleLogout} className="text-gray-400 hover:text-red-500"><LogOut size={16} /></button>
        </div>
      </div>

      {/* --- 右侧主聊天区 --- */}
      <div className="flex-1 flex flex-col h-full relative bg-white">

        {/* 顶部 (移动端) */}
        <div className="md:hidden h-14 border-b flex items-center px-4 justify-between bg-white z-20">
            <span className="font-bold">{mode === 'guide' ? 'JD 分析' : '模拟面试'}</span>
            <LogOut size={20} onClick={handleLogout} />
        </div>

        {/* 消息列表 */}
        <div className="flex-1 overflow-y-auto p-4 md:p-6 pb-[200px] scroll-smooth">
          <div className="max-w-3xl mx-auto space-y-6">
            {messages.map((msg, idx) => (
              <div key={idx} className={clsx("flex gap-4", msg.role === "user" ? "flex-row-reverse" : "")}>
                <div className={clsx("w-8 h-8 rounded-full flex-shrink-0 flex items-center justify-center shadow-sm", msg.role === "assistant" ? "bg-white border text-blue-600" : "bg-gray-900 text-white")}>
                  {msg.role === "assistant" ? <Bot size={18} /> : <User size={18} />}
                </div>
                <div className={clsx("max-w-[85%] rounded-2xl px-5 py-3 text-sm leading-relaxed shadow-sm border", msg.role === "user" ? "bg-gray-50 border-transparent" : "bg-white border-gray-100")}>
                  {msg.role === "assistant" ? (
                      <div className="prose prose-sm max-w-none prose-headings:text-gray-800 prose-p:text-gray-600 prose-li:text-gray-600">
                        <ReactMarkdown>{msg.content}</ReactMarkdown>
                      </div>
                  ) : msg.content}
                </div>
              </div>
            ))}
            {isLoading && <div className="flex justify-center"><Loader2 className="animate-spin text-blue-500" /></div>}
            <div ref={messagesEndRef} />
          </div>
        </div>

        {/* --- 底部输入框 --- */}
        <div className="absolute bottom-0 left-0 right-0 bg-white/80 backdrop-blur-md pt-4 pb-6 px-4 border-t border-gray-100">
          <div className="max-w-3xl mx-auto bg-white border border-gray-200 shadow-lg rounded-2xl p-2 relative focus-within:ring-2 focus-within:ring-blue-100">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); } }}
              placeholder={mode === 'guide' ? "粘贴岗位 JD..." : "输入你的回答..."}
              className="w-full resize-none border-none outline-none text-gray-700 bg-transparent px-3 py-2 min-h-[50px] max-h-[200px]"
              rows={1}
            />
            <div className="flex justify-between items-center mt-2 px-1">
              <div className="flex gap-2 text-gray-400">
                <input type="file" ref={fileInputRef} className="hidden" onChange={handleFileUpload} accept=".pdf,.docx,.txt" />
                <button onClick={() => fileInputRef.current?.click()} className="hover:text-blue-600 p-1.5 hover:bg-gray-50 rounded-lg"><Paperclip size={18} /></button>
              </div>
              <button onClick={handleSend} disabled={!input.trim() || isLoading} className="bg-blue-600 text-white p-2 rounded-xl hover:bg-blue-700 disabled:bg-gray-200 disabled:cursor-not-allowed">
                <Send size={18} />
              </button>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}

// --- 格式化函数 (修复了变量未定义的Bug) ---
function formatReportToMarkdown(data: any) {
  const { meta, tech_questions, hr_questions, system_design_question, company_analysis, reference_sources } = data;

  return `
## 📊 岗位画像
- **公司**: ${meta.company_name || '未识别'}
- **技术栈**: \`${meta.tech_stack.join('`, `')}\`

${company_analysis ? `\n> 🏢 **公司情报**: ${company_analysis}\n` : ''}

---
### 🛠️ 技术题
${tech_questions.map((q: any, i: number) => `**Q${i+1}: ${q.question}**\n> 💡 ${q.reference_answer}`).join('\n\n')}

---
### 💬 行为面试
${hr_questions.map((q: any, i: number) => `**Q${i+1}: ${q.question}**`).join('\n\n')}

${reference_sources?.length ? `\n---\n📚 **推荐阅读**: ${reference_sources.join(', ')}` : ''}
`;
}