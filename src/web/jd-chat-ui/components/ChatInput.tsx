"use client";

import { useState, useRef } from "react";
import { useReactMediaRecorder } from "react-media-recorder";
import { Send, Mic, Paperclip } from "lucide-react";
import clsx from "clsx";

interface ChatInputProps {
  mode: 'guide' | 'mock';
  isLoading: boolean;
  onSend: (text: string) => void;
  onFileUpload: (file: File) => void;
  onAudioUpload: (blob: Blob) => void;
  placeholder?: string;
}

export default function ChatInput({ mode, isLoading, onSend, onFileUpload, onAudioUpload, placeholder }: ChatInputProps) {
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
    <div className="flex-shrink-0 p-4 border-t border-gray-100 bg-white">
      <div className="max-w-3xl mx-auto bg-white border border-gray-200 shadow-lg rounded-2xl p-2 focus-within:ring-2 focus-within:ring-blue-100 transition-shadow">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder || (mode === 'guide' ? "发送岗位 JD..." : "请输入你的回答...")}
          className="w-full resize-none border-none outline-none text-gray-700 px-3 py-2 max-h-[150px] min-h-[44px]"
          rows={1}
        />
        <div className="flex justify-between items-center mt-1 px-1">
          <div className="flex gap-2 text-gray-400">
            <button
              onMouseDown={startRecording}
              onMouseUp={stopRecording}
              onMouseLeave={stopRecording}
              className={clsx("p-1.5 rounded-lg transition-all flex items-center justify-center", recordingStatus === 'recording' ? "bg-red-100 text-red-500 animate-pulse" : "hover:bg-gray-100 text-gray-400 hover:text-gray-600")}
              title="按住说话"
            >
              <Mic size={18} />
            </button>

            <input
              type="file"
              ref={fileInputRef}
              className="hidden"
              onChange={(e) => e.target.files?.[0] && onFileUpload(e.target.files[0])}
              accept=".pdf,.txt"
            />
            <button onClick={() => fileInputRef.current?.click()} className="hover:text-blue-600 p-1.5 hover:bg-gray-50 rounded">
              <Paperclip size={18} />
            </button>
          </div>
          <button onClick={handleClickSend} disabled={!input.trim() || isLoading} className="bg-blue-600 text-white p-2 rounded-lg hover:bg-blue-700 disabled:opacity-50">
            <Send size={16} />
          </button>
        </div>
      </div>
      <div className="text-center text-xs text-gray-400 mt-2">
        {recordingStatus === 'recording' ? "🎤 正在录音... 松开结束" : "AI生成内容仅供参考"}
      </div>
    </div>
  );
}