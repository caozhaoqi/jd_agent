"use client";

import { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation"; // 路由跳转
import ReactMarkdown from "react-markdown";
import {
  Send, Bot, User, Plus, MessageSquare,
  Loader2, Paperclip, LogOut, History
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

        // 🔴 核心修改：处理历史数据的格式
        const formattedMsgs = msgs.map((m: any) => {
          let content = m.content;
          let isJson = false;

          // 如果是 AI 的回复，且内容看起来像 JSON，尝试解析并转 Markdown
          if (m.role === "assistant") {
            try {
              // 尝试把数据库里的字符串转回 JSON 对象
              const jsonData = JSON.parse(m.content);
              // 如果解析成功，且包含 meta 字段，说明是我们的报告
              if (jsonData.meta) {
                content = formatReportToMarkdown(jsonData);
                isJson = true;
              }
            } catch (e) {
              // 解析失败说明是普通文本（比如之前的测试数据），保持原样
              console.log("解析历史 JSON 失败，按普通文本显示");
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

    try {
      const response = await fetch("http://127.0.0.1:8000/api/v1/generate-guide", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}` // 🔴 必须带 Token
        },
        body: JSON.stringify({ jd_text: userMsg }),
      });

      if (!response.ok) throw new Error("API 请求失败");

      const data = await response.json();
      const markdownReport = formatReportToMarkdown(data);

      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: markdownReport, isJson: true },
      ]);

      // 发送成功后，刷新一下侧边栏历史 (如果后端实现了自动保存 Session)
      fetchSessions(token);

    } catch (error) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "❌ 生成失败。请检查后端服务或 Token 是否过期。" },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 flex bg-[#f9fafb] text-gray-800 font-sans">

      {/* --- 左侧侧边栏 --- */}
      <div className="w-[260px] bg-[#fcfdfd] border-r border-gray-200 hidden md:flex flex-col h-full transition-all">
        {/* 新建对话按钮 */}
        <div className="p-4">
          <button
            onClick={handleNewChat}
            className="flex items-center gap-2 w-full px-3 py-2 bg-blue-50 text-blue-600 rounded-md text-sm font-medium hover:bg-blue-100 transition-colors border border-blue-100"
          >
            <Plus size={16} /> 新建对话
          </button>
        </div>

        {/* 历史记录列表 */}
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

        {/* 底部用户栏 */}
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
             <button
                onClick={handleLogout}
                className="hover:bg-red-50 hover:text-red-500 p-2 rounded-md transition-colors"
                title="退出登录"
             >
                <LogOut size={16} />
             </button>
           </div>
        </div>
      </div>

      {/* --- 右侧主聊天区 --- */}
      <div className="flex-1 flex flex-col h-full relative bg-white">

        {/* 顶部标题 (移动端) */}
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
                {/* 头像 */}
                <div className={clsx(
                  "w-8 h-8 rounded-full flex-shrink-0 flex items-center justify-center shadow-sm",
                  msg.role === "assistant" ? "bg-white border border-gray-200 text-blue-600" : "bg-gray-800 text-white"
                )}>
                  {msg.role === "assistant" ? <Bot size={18} /> : <User size={18} />}
                </div>

                {/* 气泡内容 */}
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

            {/* Loading 状态 */}
            {isLoading && (
              <div className="flex gap-4">
                <div className="w-8 h-8 rounded-full bg-white border border-gray-200 text-blue-600 flex items-center justify-center shadow-sm">
                  <Bot size={18} />
                </div>
                <div className="flex items-center gap-2 text-gray-400 text-sm mt-2">
                   <Loader2 size={16} className="animate-spin" />
                   <span className="animate-pulse">正在拆解 JD 并生成面试题...</span>
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
                <button className="hover:text-blue-600 p-1.5 hover:bg-gray-50 rounded-lg transition-colors" title="上传简历 (开发中)">
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

// --- Markdown 格式化函数 (包含 RAG 引用) ---
function formatReportToMarkdown(data: any) {
  const { meta, tech_questions, hr_questions, system_design_question, reference_sources } = data;

  let markdown = `
## 📊 岗位核心画像
- **公司**: ${meta.company_name || '未识别'}
- **职级要求**: ${meta.years_required}
- **核心技术栈**: \`${meta.tech_stack.join('`, `')}\`
- **关键软技能**: ${meta.soft_skills.join(', ')}

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