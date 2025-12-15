import { useEffect, useRef } from "react";
import ReactMarkdown from "react-markdown";
import { Bot, User, Loader2, Play } from "lucide-react"; // 🟢 引入 Play 图标
import clsx from "clsx";
import { Message } from "@/types/chat";
import ThinkingBlock from "./ThinkingBlock"; // 导入组件

interface MessageListProps {
  messages: Message[];
  isLoading: boolean;
  // ✅ 新增 Props
  showStartInterviewBtn?: boolean;
  onStartMockInterview?: () => void;
}

export default function MessageList({
  messages,
  isLoading,
  showStartInterviewBtn,
  onStartMockInterview
}: MessageListProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // 自动滚动
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading, showStartInterviewBtn]); // 按钮出现时也滚动

  return (
    <div className="flex-1 overflow-y-auto p-4 md:p-6 scroll-smooth relative">
      <div className="max-w-3xl mx-auto space-y-6">
        {messages.map((msg, idx) => (
          <div key={idx} className={clsx("flex gap-4", msg.role === "user" ? "flex-row-reverse" : "")}>
            {/* 头像 */}
            <div className={clsx("w-8 h-8 rounded-full flex-shrink-0 flex items-center justify-center border", msg.role === "assistant" ? "bg-white text-blue-600" : "bg-gray-800 text-white")}>
              {msg.role === "assistant" ? <Bot size={18} /> : <User size={18} />}
            </div>

            {/* 气泡 */}
            <div className={clsx("max-w-[85%] rounded-2xl px-5 py-3 text-sm leading-7 shadow-sm border", msg.role === "user" ? "bg-blue-50 border-blue-100" : "bg-white border-gray-100")}>
                {msg.role === "assistant" ? (
                  <div className="prose prose-sm max-w-none ...">

                    {/* 思考过程显示在文本内容上方 */}
                    {(msg.thoughts?.length || 0) > 0 && (
                        <div className="mb-3 p-3 rounded-lg bg-gray-50 border border-gray-100 shadow-sm">
                            <ThinkingBlock
                                thoughts={msg.thoughts || []}
                                isFinished={msg.isThinkingFinished || false}
                            />
                        </div>
                    )}

                    <div className="prose prose-sm max-w-none">
                        <div className="animate-typewriter">
                            <ReactMarkdown>{msg.content}</ReactMarkdown>
                        </div>
                    </div>
                    
                    {/* 添加打字机动画样式 */}
                    <style jsx>{`
                        .animate-typewriter {
                            animation: typewriter 0.1s steps(1, end) forwards;
                        }
                        
                        @keyframes typewriter {
                            from {
                                opacity: 0.95;
                            }
                            to {
                                opacity: 1;
                            }
                        }
                    `}</style>
                  </div>
                ) : msg.content}
            </div>
          </div>
        ))}

        {/* Loading 状态 - 发送消息后立即显示 */}
        {isLoading && (
          <div className="flex items-center justify-center gap-2 py-6 text-blue-600">
            <Loader2 className="animate-spin" />
            <span className="text-sm font-medium">系统正在处理您的请求...</span>
          </div>
        )}

        {/* ✅ 核心修复：把“开始模拟面试”按钮加回来 */}
        {showStartInterviewBtn && !isLoading && (
          <div className="flex justify-center mt-8 fade-in pb-4">
            <button
              onClick={onStartMockInterview}
              className="group flex items-center gap-2 bg-gradient-to-r from-purple-600 to-blue-600 text-white px-8 py-3 rounded-full shadow-lg hover:shadow-xl hover:scale-105 transition-all font-medium"
            >
              <Play size={18} fill="currentColor" className="group-hover:animate-pulse" />
              <span>我准备好了，开始模拟面试</span>
            </button>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>
    </div>
  );
}