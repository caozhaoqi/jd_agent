"use client";

import { useState, useRef } from "react";
import { useReactMediaRecorder } from "react-media-recorder";
import { Send, Mic, Paperclip } from "lucide-react";
import clsx from "clsx";
import LoadingIndicator, { LoadingType } from "./LoadingIndicator";  // 添加加载状态指示器

interface ChatInputProps {
  mode: 'guide' | 'mock';
  isLoading: boolean;
  loadingType?: LoadingType;  // 添加加载状态类型
  onSend: (text: string) => void;
  onFileUpload: (file: File) => void;
  onAudioUpload: (blob: Blob) => void;
  placeholder?: string;
}

export default function ChatInput({ mode, isLoading, loadingType, onSend, onFileUpload, onAudioUpload, placeholder }: ChatInputProps) {
  const [input, setInput] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);

  // ✅ 录音 Hook 放在这里，安全！
  const { startRecording, stopRecording, status: recordingStatus } = useReactMediaRecorder({
    audio: true,
    onStop: (blobUrl, blob) => onAudioUpload(blob)
  });

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (input.trim()) {
        onSend(input);
        setInput("");
      }
    }
  };

  const handleClickSend = () => {
    if (input.trim()) {
      onSend(input);
      setInput("");
    }
  };

  return (
    <div className="flex-shrink-0 p-6 border-t border-[#e2e8f0] bg-white">
      <div className="max-w-3xl mx-auto">
        {/* 主输入容器 */}
        <div className="bg-white border border-[#e2e8f0] rounded-2xl p-3 shadow-lg focus-within:ring-2 focus-within:ring-[#3b82f6] focus-within:border-[#3b82f6] transition-all">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={placeholder || (mode === 'guide' ? "粘贴或输入岗位 JD 内容..." : "请输入你的回答...")}
            className="w-full resize-none border-none outline-none text-[#1e293b] px-4 py-3 max-h-[180px] min-h-[48px] leading-relaxed"
            rows={1}
            disabled={isLoading}  // 在加载时禁用输入框
          />
          <div className="flex justify-between items-center mt-2 px-2">
            <div className="flex gap-3">
              {/* 录音按钮 */}
              <button
                onMouseDown={startRecording}
                onMouseUp={stopRecording}
                onMouseLeave={stopRecording}
                disabled={isLoading}  // 在加载时禁用按钮
                className={clsx(
                  "p-2 rounded-xl transition-all flex items-center justify-center",
                  recordingStatus === 'recording'
                    ? "bg-[#fee2e2] text-[#ef4444] animate-pulse shadow-md"
                    : "hover:bg-[#f1f5f9] text-[#64748b] hover:text-[#3b82f6]",
                  isLoading && "opacity-50 cursor-not-allowed"
                )}
                title="按住说话"
              >
                <Mic size={20} />
              </button>

              {/* 文件上传 */}
              <input
                type="file"
                ref={fileInputRef}
                className="hidden"
                onChange={(e) => e.target.files?.[0] && onFileUpload(e.target.files[0])}
                accept=".pdf,.txt"
                disabled={isLoading}  // 在加载时禁用文件上传
              />
              <button 
                onClick={() => fileInputRef.current?.click()} 
                disabled={isLoading} 
                className={clsx(
                  "p-2 rounded-xl transition-all flex items-center justify-center",
                  "hover:bg-[#f1f5f9] text-[#64748b] hover:text-[#3b82f6]",
                  isLoading && "opacity-50 cursor-not-allowed"
                )}
                title="上传文件"
              >
                <Paperclip size={20} />
              </button>
            </div>
            <div className="flex items-center gap-3">
              {/* 显示加载状态指示器 */}
              {isLoading && loadingType && (
                <LoadingIndicator 
                  type={loadingType} 
                  size="small" 
                  message="处理中..." 
                />
              )}
              {/* 发送按钮 */}
              <button 
                onClick={handleClickSend} 
                disabled={!input.trim() || isLoading} 
                className={clsx(
                  "bg-gradient-to-r from-[#3b82f6] to-[#8b5cf6] text-white p-3 rounded-xl hover:shadow-lg transition-all",
                  (!input.trim() || isLoading) ? "opacity-50 cursor-not-allowed" : "hover:opacity-90 scale-105"
                )}
              >
                <Send size={18} />
              </button>
            </div>
          </div>
        </div>
        
        {/* 底部状态提示 */}
        <div className="text-center text-xs text-[#94a3b8] mt-3">
          {recordingStatus === 'recording' 
            ? "🎤 正在录音... 松开结束"
            : mode === 'guide'
            ? "支持粘贴 JD 文本或上传文件"
            : "AI 生成内容仅供参考"
          }
        </div>
      </div>
    </div>
  );
}