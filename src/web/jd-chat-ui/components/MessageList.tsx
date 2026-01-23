"use client";

import { useEffect, useRef } from "react";
import ReactMarkdown from "react-markdown";
import { Bot, User, Play, LayoutDashboard } from "lucide-react";
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
    <div className="flex-1 overflow-y-auto p-4 md:p-6 scroll-smooth relative bg-[#f8fafc]">
      <div className="max-w-3xl mx-auto space-y-6 pb-12">
        {/* 当消息为空时显示提示 */}
        {messages.length === 0 && !isLoading && !error && (
          <div className="text-center py-16 space-y-6">
            <div className="w-20 h-20 bg-gradient-to-br from-[#3b82f6] to-[#8b5cf6] rounded-2xl flex items-center justify-center mx-auto shadow-xl">
              <Bot size={40} className="text-white" />
            </div>
            <h3 className="text-xl font-bold text-[#1e293b]">欢迎使用 JD Agent</h3>
            <p className="text-[#64748b] max-w-md mx-auto leading-relaxed">
              请在下方输入框中粘贴或输入岗位 JD 内容，我将为您生成详细的岗位分析报告和面试准备建议。
            </p>
            <div className="mt-4 flex justify-center">
              <div className="inline-flex items-center gap-2 bg-[#e2e8f0] rounded-full px-4 py-2 text-sm text-[#64748b]">
                <LayoutDashboard size={16} />
                <span>支持 JD 分析和模拟面试模式</span>
              </div>
            </div>
          </div>
        )}
        
        {messages.map((msg, idx) => (
          <div key={idx} className={clsx("flex gap-4", msg.role === "user" ? "justify-end" : "justify-start")}>
            {msg.role === "assistant" && (
              <div className={clsx(
                "w-9 h-9 rounded-full flex-shrink-0 flex items-center justify-center shadow-md",
                "bg-gradient-to-br from-[#3b82f6] to-[#8b5cf6] text-white"
              )}>
                <Bot size={18} />
              </div>
            )}
            
            <div className={clsx(
              "max-w-[85%] rounded-2xl px-5 py-4 text-[14px] leading-7 shadow-sm",
              msg.role === "user"
                ? "bg-[#3b82f6] text-white"
                : "bg-white border border-[#e2e8f0] text-[#1e293b]"
            )}>
              {msg.role === "assistant" ? (
                <div className="flex flex-col gap-3">
                  {/* 气泡内的思考逻辑 */}
                   <ThinkingReveal
                     thoughts={msg.thoughts || []}
                     isFinished={msg.isThinkingFinished || false}
                   />

                  {/* 回复正文 */}
                  {(msg.content || msg.isThinkingFinished) && (
                    <div className="prose prose-sm max-w-none animate-in fade-in duration-500">
                      {/* 处理 JSON 格式的内容 */}
                      {(() => {
                        let contentToRender = msg.content;
                        // 检查内容是否为 JSON 格式
                        if (contentToRender && contentToRender.startsWith('{') && contentToRender.endsWith('}')) {
                          try {
                            const jsonData = JSON.parse(contentToRender);
                            // 如果是 JSON 格式，提取 useful 信息或格式化为易读形式
                            // 这里可以根据实际的 JSON 结构进行调整
                            if (jsonData.tech_questions && jsonData.tech_questions.length > 0) {
                              // 如果有技术问题，渲染为列表
                              return (
                                <div>
                                  <h4>技术问题：</h4>
                                  <ul>
                                    {jsonData.tech_questions.map((q: any, idx: number) => (
                                      <li key={idx}>{q.question}</li>
                                    ))}
                                  </ul>
                                </div>
                              );
                            } else {
                              // 否则，显示格式化的 JSON
                              contentToRender = JSON.stringify(jsonData, null, 2);
                              return <pre><code>{contentToRender}</code></pre>;
                            }
                          } catch (e) {
                            // 如果解析失败，作为普通文本处理
                          }
                        }
                        // 默认使用 ReactMarkdown 渲染
                        return <ReactMarkdown>{contentToRender}</ReactMarkdown>;
                      })()}
                    </div>
                  )}
                </div>
              ) : (
                <div className="whitespace-pre-wrap">{msg.content}</div>
              )}
            </div>
            
            {msg.role === "user" && (
              <div className={clsx(
                "w-9 h-9 rounded-full flex-shrink-0 flex items-center justify-center shadow-md",
                "bg-[#1e293b] text-white"
              )}>
                <User size={18} />
              </div>
            )}
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
          <div className="flex flex-col items-center justify-center gap-4 py-16 text-[#3b82f6] animate-in fade-in zoom-in-95 duration-300">
            <LoadingIndicator 
              type={loadingType || 'default'} 
              size="large" 
              message="AI 正在分析您的请求..." 
            />
          </div>
        )}

        {showStartInterviewBtn && !isLoading && (
          <div className="flex justify-center mt-8">
            <button
              onClick={onStartMockInterview}
              className="flex items-center gap-3 bg-gradient-to-r from-[#8b5cf6] to-[#3b82f6] text-white px-10 py-4 rounded-full shadow-xl hover:shadow-2xl hover:scale-105 transition-all font-semibold text-sm"
            >
              <Play size={20} fill="currentColor" />
              <span>我准备好了，开始模拟面试</span>
            </button>
          </div>
        )}

        <div ref={messagesEndRef} className="h-4" />
      </div>
    </div>
  );
}