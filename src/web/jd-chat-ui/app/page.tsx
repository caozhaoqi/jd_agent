"use client";

import { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation"; // 路由跳转
import ReactMarkdown from "react-markdown";
import {
  Send, Bot, User, Plus, MessageSquare,
  Loader2, Paperclip, LogOut
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
  const fileInputRef = useRef<HTMLInputElement>(null); // 文件上传 Input 引用

  // --- 状态管理 ---
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);

  // 用户与会话状态
  const [username, setUsername] = useState("Guest");
  const [sessions, setSessions] = useState<Session[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<number | null>(null);

  // --- 1. 初始化: 检查登录 & 加载历史会话 ---
  useEffect(() => {
    const token = localStorage.getItem("token");
    const user = localStorage.getItem("username");

    // 未登录则跳转
    if (!token) {
      router.push("/login");
      return;
    }

    setUsername(user || "User");

    // 初始化默认消息
    if (messages.length === 0) {
      setMessages([{
        role: "assistant",
        content: `你好 **${user}**！我是你的 AI 面试助手。请把 **岗位描述 (JD)** 发给我，我将为你生成专属的面试突击指南。`
      }]);
    }

    // 加载侧边栏历史列表
    fetchSessions(token);
  }, []);

  // --- 自动滚动逻辑 ---
  useEffect(() => {
    const scrollToBottom = () => {
      messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };
    const timeoutId = setTimeout(scrollToBottom, 100);
    return () => clearTimeout(timeoutId);
  }, [messages, isLoading]);

  // --- 日志辅助函数 ---
  const logEvent = (stage: string, message: any, type: 'info' | 'error' | 'success' = 'info') => {
    const timestamp = new Date().toLocaleTimeString();
    const styles = {
      info: 'color: #3b82f6; font-weight: bold;',
      success: 'color: #10b981; font-weight: bold;',
      error: 'color: #ef4444; font-weight: bold;',
    };
    console.log(`%c[${timestamp}] [${stage}]`, styles[type], message);
  };

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

  // --- API: 加载某个具体会话的消息 ---
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

        // 处理数据库存的 JSON 字符串
        const formattedMsgs = msgs.map((m: any) => {
          let content = m.content;
          let isJson = false;

          if (m.role === "assistant") {
            try {
              const jsonData = JSON.parse(m.content);
              if (jsonData && jsonData.meta) {
                content = formatReportToMarkdown(jsonData);
                isJson = true;
              }
            } catch (e) {
              // 解析失败说明是普通文本，保持原样
            }
          }

          return {
            role: m.role,
            content: content,
            isJson: isJson
          };
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

    // 1. 检查 Token
    const token = localStorage.getItem("token");
    if (!token) {
      alert("登录已过期，请重新登录后上传简历！");
      router.push("/login");
      return;
    }

    setIsLoading(true);
    // 2. 立即在 UI 上反馈
    setMessages(prev => [...prev, { role: "user", content: `📄 正在上传并解析简历: **${file.name}** ...` }]);

    const formData = new FormData();
    formData.append("file", file);

    try {
      logEvent('UPLOAD', `Starting upload for ${file.name}`, 'info');

      const res = await fetch("http://127.0.0.1:8000/api/v1/upload-resume", {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${token}`
          // 浏览器会自动设置 Content-Type 为 multipart/form-data
        },
        body: formData
      });

      if (res.ok) {
        const data = await res.json();
        setMessages(prev => [...prev, {
            role: "assistant",
            content: `✅ **简历解析成功！**\n\n已提取并记忆以下信息 (长期记忆)：\n${data.extracted_facts.map((f:string) => `- ${f}`).join('\n')}\n\n现在您可以发送 JD，我会结合您的简历背景为您生成攻略。`
        }]);
      } else {
        const errData = await res.json();
        throw new Error(errData.detail || "上传失败");
      }
    } catch (e: any) {
      logEvent('UPLOAD_ERR', e, 'error');
      setMessages(prev => [...prev, { role: "assistant", content: `❌ 简历解析失败: ${e.message}` }]);
    } finally {
      setIsLoading(false);
      // 清空 input，防止无法连续上传同一个文件
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  // --- 交互: 新建对话 ---
  const handleNewChat = () => {
    setCurrentSessionId(null);
    setMessages([{
      role: "assistant",
      content: "你好！我是你的 AI 面试助手。请发送新的 JD。"
    }]);
  };

  // --- 交互: 退出登录 ---
  const handleLogout = () => {
    localStorage.removeItem("token");
    localStorage.removeItem("username");
    router.push("/login");
  };

  // --- 交互: 发送消息 ---
  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    const token = localStorage.getItem("token");
    if (!token) {
        router.push("/login");
        return;
    }

    const userMsg = input;
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: userMsg }]);
    setIsLoading(true);

    logEvent('API_START', { url: '/api/v1/generate-guide', payload: userMsg }, 'info');

    try {
      const startTime = performance.now();

      const response = await fetch("http://127.0.0.1:8000/api/v1/generate-guide", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({ jd_text: userMsg }),
      });

      const endTime = performance.now();
      const duration = (endTime - startTime).toFixed(0);

      if (!response.ok) {
        logEvent('API_ERROR', `Status: ${response.status} | Time: ${duration}ms`, 'error');
        throw new Error("API 请求失败");
      }

      const data = await response.json();
      logEvent('API_SUCCESS', { duration: `${duration}ms` }, 'success');

      const markdownReport = formatReportToMarkdown(data);

      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: markdownReport, isJson: true },
      ]);

      // 发送成功后，刷新侧边栏历史
      fetchSessions(token);

    } catch (error) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "❌ 生成失败。请检查后端服务或 Token 是否过期。" },
      ]);
      logEvent('EXCEPTION', error, 'error');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 flex bg-[#f9fafb] text-gray-800 font-sans">

      {/* --- 左侧侧边栏 --- */}
      <div className="w-[260px] bg-[#fcfdfd] border-r border-gray-200 hidden md:flex flex-col h-full transition-all">
        <div className="p-4">
          <button
            onClick={handleNewChat}
            className="flex items-center gap-2 w-full px-3 py-2 bg-blue-50 text-blue-600 rounded-md text-sm font-medium hover:bg-blue-100 transition-colors border border-blue-100"
          >
            <Plus size={16} /> 新建对话
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-2 scrollbar-thin">
          <div className="text-xs text-gray-400 px-3 py-2 font-medium">最近记录</div>
          {sessions.length === 0 ? (
            <div className="text-xs text-gray-400 px-3 text-center mt-4">暂无历史记录</div>
          ) : (
            sessions.map((s) => (
                <div
                    key={s.id}
                    onClick={() => loadSession(s.id)}
                    className={clsx(
                        "flex items-center gap-2 px-3 py-2.5 text-sm rounded-md cursor-pointer mb-1 transition-colors",
                        currentSessionId === s.id
                            ? "bg-gray-100 text-gray-900 font-medium"
                            : "text-gray-600 hover:bg-gray-50"
                    )}
                >
                  <MessageSquare size={14} className="flex-shrink-0" />
                  <span className="truncate">{s.title || "未命名对话"}</span>
                </div>
            ))
          )}
        </div>

        <div className="p-4 border-t border-gray-100">
           <div className="flex items-center justify-between text-sm text-gray-600">
             <div className="flex items-center gap-2 overflow-hidden">
                <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-full text-white flex-shrink-0 flex items-center justify-center font-bold shadow-sm">
                    {username[0]?.toUpperCase()}
                </div>
                <div className="flex flex-col truncate">
                    <span className="font-medium truncate text-gray-900">{username}</span>
                    <span className="text-xs text-gray-400">Pro Plan</span>
                </div>
             </div>
             <button onClick={handleLogout} className="hover:bg-red-50 hover:text-red-500 p-2 rounded-md transition-colors" title="退出登录">
                <LogOut size={16} />
             </button>
           </div>
        </div>
      </div>

      {/* --- 右侧主聊天区 --- */}
      <div className="flex-1 flex flex-col h-full relative bg-white">

        {/* 顶部标题 */}
        <div className="md:hidden h-14 border-b flex-shrink-0 flex items-center px-4 justify-between bg-white z-20">
          <span className="font-semibold text-gray-800">JD Agent</span>
          <div className="flex gap-3">
             <Plus size={20} onClick={handleNewChat} />
             <LogOut size={20} onClick={handleLogout} />
          </div>
        </div>

        {/* 消息列表 */}
        <div className="flex-1 overflow-y-auto p-4 md:p-6 pb-[200px] scroll-smooth">
          <div className="max-w-3xl mx-auto space-y-8">
            {messages.map((msg, idx) => (
              <div key={idx} className={clsx("flex gap-4", msg.role === "user" ? "flex-row-reverse" : "")}>
                <div className={clsx(
                  "w-8 h-8 rounded-full flex-shrink-0 flex items-center justify-center shadow-sm",
                  msg.role === "assistant" ? "bg-white border border-gray-200 text-blue-600" : "bg-gray-800 text-white"
                )}>
                  {msg.role === "assistant" ? <Bot size={18} /> : <User size={18} />}
                </div>

                <div className={clsx(
                  "relative max-w-[85%] rounded-2xl px-5 py-3 text-sm leading-relaxed shadow-sm border",
                  msg.role === "user"
                    ? "bg-[#f4f4f4] border-transparent text-gray-900 rounded-tr-none"
                    : "bg-white border-gray-100 text-gray-800 rounded-tl-none"
                )}>
                  {msg.role === "assistant" && idx !== 0 ? (
                    <div className="prose prose-sm max-w-none prose-headings:font-semibold prose-h2:text-blue-600 prose-h3:text-gray-700 prose-code:text-blue-600 prose-pre:bg-gray-50 prose-pre:border prose-pre:border-gray-100">
                      <ReactMarkdown>{msg.content}</ReactMarkdown>
                    </div>
                  ) : (
                    <div className="whitespace-pre-wrap">{msg.content}</div>
                  )}
                </div>
              </div>
            ))}

            {isLoading && (
              <div className="flex gap-4">
                <div className="w-8 h-8 rounded-full bg-white border border-gray-200 text-blue-600 flex items-center justify-center shadow-sm">
                  <Bot size={18} />
                </div>
                <div className="flex items-center gap-2 text-gray-400 text-sm mt-2">
                   <Loader2 size={16} className="animate-spin" />
                   <span className="animate-pulse">正在思考中...</span>
                </div>
              </div>
            )}

            <div className="h-20 flex-shrink-0" />
            <div ref={messagesEndRef} />
          </div>
        </div>

        {/* --- 底部输入框 --- */}
        <div className="absolute bottom-0 left-0 right-0 z-10 bg-gradient-to-t from-white via-white to-transparent pt-24 pb-6 px-4">
          <div className="max-w-3xl mx-auto bg-white border border-gray-200 shadow-[0_4px_20px_rgba(0,0,0,0.08)] rounded-2xl p-2 relative focus-within:ring-2 focus-within:ring-blue-100 transition-shadow">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                 if (e.key === 'Enter' && !e.shiftKey) {
                   e.preventDefault();
                   handleSend();
                 }
              }}
              placeholder="在此粘贴岗位描述 (JD)，Ctrl + Enter 发送..."
              className="w-full resize-none border-none outline-none text-gray-700 bg-transparent px-3 py-2 max-h-[200px] min-h-[50px] scrollbar-hide placeholder:text-gray-400"
              rows={input.length > 50 ? 3 : 1}
            />

            <div className="flex justify-between items-center mt-2 px-1">
              <div className="flex gap-2 text-gray-400">
                {/* 🔴 文件上传组件 (隐藏 Input + 触发按钮) */}
                <input
                    type="file"
                    ref={fileInputRef}
                    className="hidden"
                    accept=".pdf,.docx,.txt"
                    onChange={handleFileUpload}
                />
                <button
                    onClick={() => fileInputRef.current?.click()}
                    className="hover:text-blue-600 p-1.5 hover:bg-gray-50 rounded-lg transition-colors"
                    title="上传简历 (PDF/Word)"
                >
                  <Paperclip size={18} />
                </button>
              </div>
              <button
                onClick={handleSend}
                disabled={!input.trim() || isLoading}
                className={clsx(
                  "p-2 rounded-xl transition-all duration-200 flex items-center justify-center",
                  input.trim() && !isLoading
                    ? "bg-blue-600 text-white shadow-md hover:bg-blue-700 hover:scale-105 active:scale-95"
                    : "bg-gray-100 text-gray-300 cursor-not-allowed"
                )}
              >
                <Send size={18} />
              </button>
            </div>
          </div>
          <div className="text-center text-xs text-gray-400 mt-3 font-light">
             内容由 AI 生成，请仔细甄别。 | JD Agent Pro v1.0
          </div>
        </div>
      </div>
    </div>
  );
}

// --- Markdown 格式化函数 ---
function formatReportToMarkdown(data: any) {
  const { meta, tech_questions, hr_questions, system_design_question, reference_sources } = data;

  let markdown = `
## 📊 岗位核心画像
- **公司**: ${meta.company_name || '未识别'}
- **职级要求**: ${meta.years_required}
- **核心技术栈**: \`${meta.tech_stack.join('`, `')}\`
- **关键软技能**: ${meta.soft_skills.join(', ')}

---

${company_analysis ? `
---

## 🏢 公司背景情报 (AI 背调)
> ${company_analysis}
` : ''}

---

## 🛠️ 技术面试必考题 (Hardcore)
${tech_questions.map((q: any, i: number) => `
### Q${i + 1}: ${q.question}
> **参考回答要点**:
> ${q.reference_answer}
`).join('\n')}

---

## 💬 HR 行为面试 (Behavioral)
${hr_questions.map((q: any, i: number) => `
### Q${i + 1}: ${q.question}
> **参考回答要点**:
> ${q.reference_answer}
`).join('\n')}
`;

  if (system_design_question) {
    markdown += `
---

## 🏗️ 系统设计加分题
### ${system_design_question.question}
> **设计思路**:
> ${system_design_question.reference_answer}
`;
  }

  if (reference_sources && reference_sources.length > 0) {
    markdown += `
---

## 📚 个人知识库引用 (RAG)
本次分析检测到您的博客中有相关技术积累，**强烈建议复习以下文章**：
${reference_sources.map((src: string) => `- 📄 [**${src}**] (本地博客)`).join('\n')}
`;
  }

  markdown += `
---
> 💡 **提示**: 建议结合你的简历项目经验来回答上述问题。
`;

  return markdown;
}