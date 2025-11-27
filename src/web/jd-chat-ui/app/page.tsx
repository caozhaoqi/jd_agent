"use client";

import { useState, useRef, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import { Send, Bot, User, Plus, MessageSquare, Loader2, Paperclip } from "lucide-react";
import clsx from "clsx";

// 定义消息类型
type Message = {
  role: "user" | "assistant";
  content: string;
  isJson?: boolean; // 标记是否为结构化报告
};

export default function Home() {
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content: "你好！我是你的 AI 面试助手。请把 **岗位描述 (JD)** 发给我，我将为你生成专属的面试突击指南。",
    },
  ]);
  const messagesEndRef = useRef<HTMLDivElement>(null);

// 增加一个简单的日志辅助函数
const logEvent = (stage: string, message: any, type: 'info' | 'error' | 'success' = 'info') => {
  const timestamp = new Date().toLocaleTimeString();
  const styles = {
    info: 'color: #3b82f6; font-weight: bold;',
    success: 'color: #10b981; font-weight: bold;',
    error: 'color: #ef4444; font-weight: bold;',
  };
  console.log(`%c[${timestamp}] [${stage}]`, styles[type], message);
};


  // 自动滚动到底部
// 1. 修改 scrollIntoView 的逻辑，增加 timeout 确保渲染完再滚
  useEffect(() => {
    const scrollToBottom = () => {
      messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    // 延时 100ms，等待 React 渲染和 CSS 布局完成
    const timeoutId = setTimeout(scrollToBottom, 100);
    return () => clearTimeout(timeoutId);
  }, [messages, isLoading]); // 监听 messages 和 isLoading 变化

  // 处理发送
  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    const userMsg = input;
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: userMsg }]);
    setIsLoading(true);

   // 1. 记录开始
    logEvent('API_START', { url: '/api/v1/generate-guide', payload: userMsg }, 'info');

    try {
      const startTime = performance.now(); // 计时

      const response = await fetch("http://127.0.0.1:8000/api/v1/generate-guide", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ jd_text: userMsg }),
      });

      const endTime = performance.now();
      const duration = (endTime - startTime).toFixed(0);

      // 2. 记录网络层响应
      if (!response.ok) {
        logEvent('API_ERROR', `Status: ${response.status} | Time: ${duration}ms`, 'error');
        throw new Error(`API Error: ${response.statusText}`);
      }

      const data = await response.json();

      // 3. 记录数据成功接收
      logEvent('API_SUCCESS', { duration: `${duration}ms`, dataSize: JSON.stringify(data).length }, 'success');
      console.log('📦 Server Response Data:', data); // 单独打印详细数据对象方便展开查看

      const markdownReport = formatReportToMarkdown(data);

      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: markdownReport, isJson: true },
      ]);
    } catch (error) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "❌ 抱歉，生成指南时出错了。请检查后端服务是否启动，或者 API Key 是否有额度。" },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex h-screen bg-[#f9faib] text-gray-800 font-sans">
      {/* --- 左侧侧边栏 (DeepSeek 风格) --- */}
      <div className="w-[260px] bg-[#fcfdfd] border-r border-gray-200 hidden md:flex flex-col">
        <div className="p-4">
          <button 
            onClick={() => setMessages([{ role: "assistant", content: "你好！我是你的 AI 面试助手..." }])}
            className="flex items-center gap-2 w-full px-3 py-2 bg-blue-50 text-blue-600 rounded-md text-sm font-medium hover:bg-blue-100 transition-colors"
          >
            <Plus size={16} /> 新建对话
          </button>
        </div>
        
        <div className="flex-1 overflow-y-auto px-2">
          <div className="text-xs text-gray-400 px-3 py-2">最近记录</div>
          {/* 模拟历史记录 */}
          <div className="flex items-center gap-2 px-3 py-2 text-sm text-gray-700 hover:bg-gray-100 rounded-md cursor-pointer">
            <MessageSquare size={14} />
            <span className="truncate">Python 高级开发面试...</span>
          </div>
          <div className="flex items-center gap-2 px-3 py-2 text-sm text-gray-700 hover:bg-gray-100 rounded-md cursor-pointer">
            <MessageSquare size={14} />
            <span className="truncate">AI 训练师 JD 分析</span>
          </div>
        </div>

        <div className="p-4 border-t border-gray-100">
           <div className="flex items-center gap-2 text-sm text-gray-600">
             <div className="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center text-white font-bold">JD</div>
             <div className="flex-1">
               <div className="font-medium">JD Agent</div>
               <div className="text-xs text-gray-400">Pro Version</div>
             </div>
           </div>
        </div>
      </div>

      {/* --- 右侧主聊天区 --- */}
     <div className="flex-1 flex flex-col h-screen overflow-hidden relative bg-white">
        
        {/* 顶部标题 (移动端显示) */}
        <div className="md:hidden h-14 border-b flex items-center px-4 justify-between bg-white">
          <span className="font-semibold">JD Agent</span>
          <Plus size={20} />
        </div>

        {/* 消息列表 */}
        <div className="flex-1 overflow-y-auto p-4 md:p-6 pb-64 scroll-smooth">
          <div className="max-w-3xl mx-auto space-y-8">
            {messages.map((msg, idx) => (
              <div key={idx} className={clsx("flex gap-4", msg.role === "user" ? "flex-row-reverse" : "")}>
                {/* 头像 */}
                <div className={clsx(
                  "w-8 h-8 rounded-full flex-shrink-0 flex items-center justify-center",
                  msg.role === "assistant" ? "bg-blue-600 text-white" : "bg-gray-200 text-gray-600"
                )}>
                  {msg.role === "assistant" ? <Bot size={18} /> : <User size={18} />}
                </div>

                {/* 气泡内容 */}
                <div className={clsx(
                  "relative max-w-[85%] rounded-2xl px-5 py-3 text-sm leading-relaxed",
                  msg.role === "user" 
                    ? "bg-[#f4f4f4] text-gray-900 rounded-tr-none" 
                    : "bg-white text-gray-800 "
                )}>
                  {msg.role === "assistant" && idx !== 0 ? (
                    <div className="prose prose-sm max-w-none prose-headings:font-semibold prose-h2:text-blue-600 prose-h3:text-gray-700 prose-code:text-blue-600 prose-pre:bg-gray-50 prose-pre:border prose-pre:border-gray-100">
                      {/* 如果是 AI 回复，使用 Markdown 渲染 */}
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
                <div className="w-8 h-8 rounded-full bg-blue-600 text-white flex items-center justify-center">
                  <Bot size={18} />
                </div>
                <div className="flex items-center gap-2 text-gray-400 text-sm mt-2">
                   <Loader2 size={16} className="animate-spin" />
                   <span>正在深入分析 JD、生成面试题... (预计 10-15秒)</span>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        </div>

        {/* --- 底部输入框 (DeepSeek 风格悬浮) --- */}
        <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-white via-white to-transparent pt-10 pb-6 px-4">
          <div className="max-w-3xl mx-auto bg-white border border-gray-200 shadow-[0_0_15px_rgba(0,0,0,0.05)] rounded-2xl p-2 relative">
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
              className="w-full resize-none border-none outline-none text-gray-700 bg-transparent px-3 py-2 max-h-[200px] min-h-[50px] scrollbar-hide"
              rows={input.length > 50 ? 3 : 1}
            />
            
            <div className="flex justify-between items-center mt-2 px-1">
              <div className="flex gap-2 text-gray-400">
                <button className="hover:text-blue-600 p-1.5 hover:bg-gray-50 rounded-lg transition-colors">
                  <Paperclip size={18} />
                </button>
              </div>
              <button
                onClick={handleSend}
                disabled={!input.trim() || isLoading}
                className={clsx(
                  "p-2 rounded-lg transition-all duration-200",
                  input.trim() && !isLoading 
                    ? "bg-blue-600 text-white shadow-md hover:bg-blue-700" 
                    : "bg-gray-100 text-gray-300 cursor-not-allowed"
                )}
              >
                <Send size={18} />
              </button>
            </div>
          </div>
          <div className="text-center text-xs text-gray-400 mt-3">
             内容由 AI 生成，请仔细甄别。DeepSeek 风格界面 Demo.
          </div>
        </div>
      </div>
    </div>
  );
}

// --- 辅助函数：将后端 JSON 转换为美观的 Markdown ---
function formatReportToMarkdown(data: any) {
  const { meta, tech_questions, hr_questions, system_design_question } = data;

  return `
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

${system_design_question ? `
---

## 🏗️ 系统设计加分题
### ${system_design_question.question}
> **设计思路**:  
> ${system_design_question.reference_answer}
` : ''}

> 💡 **提示**: 建议结合你的简历项目经验来回答上述问题。
`;
}