"use client";

import { useEffect, useRef } from "react";
import ReactMarkdown from "react-markdown";
import { Bot, User, Loader2, Play } from "lucide-react";
import clsx from "clsx";
import { Message } from "@/types/chat";
import ThinkingReveal from "./ThinkingReveal";
import LoadingIndicator, { LoadingType } from "./LoadingIndicator";  // 添加加载状态指示器
import ErrorAlert from "./ErrorAlert";  // 添加错误提示组件

interface MessageListProps {
  messages: Message[];
  isLoading: boolean;
  loadingType?: LoadingType;  // 添加加载状态类型
  error?: string | null;  // 添加错误信息
  showStartInterviewBtn?: boolean;
  onStartMockInterview?: () => void;
  onRetry?: () => void;  // 添加重试回调
}

export default function MessageList({
  messages,
  isLoading,
  loadingType,
  error,
  showStartInterviewBtn,
  onStartMockInterview,
  onRetry
}: MessageListProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // --- 核心修复判断 ---
  const lastMessage = messages[messages.length - 1];

  // 只要最后一条消息已经是 assistant 了（说明气泡已创建），就关闭中心巨大的加载动画
  // 气泡内部会通过 ThinkingReveal 自己展示加载状态
  const shouldShowGlobalLoader = isLoading && lastMessage?.role !== "assistant";


useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    // 将 showStartInterviewBtn 加入依赖，因为它的出现会改变内容高度
}, [messages, isLoading, showStartInterviewBtn]);

useEffect(() => {
  // 调试：打印所有消息及其思考内容
  messages.forEach((msg, idx) => {
    if (msg.role === 'assistant') {
      console.log(`🔍 [MessageList] Assistant message #${idx}:`, { 
        hasThoughts: !!msg.thoughts, 
        thoughtsLength: msg.thoughts?.length || 0,
        isThinkingFinished: msg.isThinkingFinished 
      });
    }
  });
}, [messages]);

  return (
    <div className="flex-1 overflow-y-auto p-4 md:p-6 scroll-smooth relative bg-white">
      <div className="max-w-3xl mx-auto space-y-8 pb-10">
        {messages.map((msg, idx) => (
          <div key={idx} className={clsx("flex gap-4", msg.role === "user" ? "flex-row-reverse" : "")}>
            <div className={clsx(
              "w-8 h-8 rounded-full flex-shrink-0 flex items-center justify-center border shadow-sm",
              msg.role === "assistant" ? "bg-white text-blue-600 border-blue-100" : "bg-gray-800 text-white"
            )}>
              {msg.role === "assistant" ? <Bot size={18} /> : <User size={18} />}
            </div>

            <div className={clsx(
              "max-w-[85%] rounded-2xl px-5 py-3 text-[14px] leading-7 shadow-sm border",
              msg.role === "user" ? "bg-blue-600 text-white border-blue-500" : "bg-white border-gray-100 text-gray-800"
            )}>
              {msg.role === "assistant" ? (
                <div className="flex flex-col">
                  {/* 气泡内的思考逻辑 */}
                   <ThinkingReveal
                     thoughts={msg.thoughts || []}
                     isFinished={msg.isThinkingFinished || false}
                   />

                  {/* 回复正文 */}
                  {(msg.content || msg.isThinkingFinished) && (
                    <div className="prose prose-sm max-w-none animate-in fade-in duration-500">
                      <ReactMarkdown>{msg.content}</ReactMarkdown>
                    </div>
                  )}
                </div>
              ) : (
                <div className="whitespace-pre-wrap">{msg.content}</div>
              )}
            </div>
          </div>
        ))}

        {/* 错误提示区域 - 使用新的ErrorAlert组件 */}
        {error && (
          <ErrorAlert
            error={error}
            onRetry={onRetry}
            type="inline"
            autoHide={false}
            showDetails={false}
          />
        )}

        {/* 居中大 Loader：仅在 AI 还没出现在列表中时显示 */}
        {shouldShowGlobalLoader && (
          <div className="flex flex-col items-center justify-center gap-3 py-10 text-blue-500 animate-in fade-in zoom-in-95 duration-300">
            <LoadingIndicator 
              type={loadingType || 'default'} 
              size="large" 
              message="AI 正在处理请求..." 
            />
          </div>
        )}

        {showStartInterviewBtn && !isLoading && (
          <div className="flex justify-center mt-4">
            <button
              onClick={onStartMockInterview}
              className="flex items-center gap-2 bg-gradient-to-r from-purple-600 to-blue-600 text-white px-8 py-3 rounded-full shadow-lg hover:scale-105 transition-all font-medium"
            >
              <Play size={18} fill="currentColor" />
              <span>我准备好了，开始模拟面试</span>
            </button>
          </div>
        )}

        <div ref={messagesEndRef} className="h-2" />
      </div>
    </div>
  );
}