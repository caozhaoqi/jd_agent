"use client";

import { useState, useEffect, useRef } from "react";
import { Brain, ChevronDown, ChevronRight } from "lucide-react";
import clsx from "clsx";

interface ThinkingRevealProps {
  thoughts: string[];
  isFinished: boolean;
}

export default function ThinkingReveal({ thoughts, isFinished }: ThinkingRevealProps) {
  const [isExpanded, setIsExpanded] = useState(true);
  const [duration, setDuration] = useState(0);
  const startTimeRef = useRef<number>(Date.now());
  const timerRef = useRef<NodeJS.Timeout | null>(null);

  // 添加调试信息
  console.log("🔍 [ThinkingReveal] Rendering with:", { 
    thoughts, 
    isFinished, 
    thoughtsLength: thoughts?.length || 0 
  });

  useEffect(() => {
    if (!isFinished) {
      timerRef.current = setInterval(() => {
        setDuration(Math.floor((Date.now() - startTimeRef.current) / 1000));
      }, 1000);
    } else {
      if (timerRef.current) clearInterval(timerRef.current);
      // 思考完成后，1秒后自动收起
      const timeout = setTimeout(() => setIsExpanded(false), 1000);
      return () => clearTimeout(timeout);
    }
    return () => { if (timerRef.current) clearInterval(timerRef.current); };
  }, [isFinished]);

  const fullContent = thoughts.join("");

  // 如果思考已结束且没有任何思考内容，则不渲染（防止历史记录中出现空的思考块）
  if (isFinished && !fullContent) return null;

  return (
    <div className="mb-4 group/thinking">
      <div
        onClick={() => setIsExpanded(!isExpanded)}
        className={clsx(
          "flex items-center gap-2 text-[12px] px-3 py-1.5 rounded-full transition-all cursor-pointer w-fit select-none border",
          isFinished
            ? "bg-gray-50 text-gray-500 border-gray-200 hover:bg-gray-100"
            : "bg-purple-50 text-purple-600 border-purple-100 shadow-sm animate-pulse"
        )}
      >
        <div className="relative">
          <Brain size={14} className={isFinished ? "text-gray-400" : "text-purple-500"} />
          {!isFinished && (
            <span className="absolute -top-1 -right-1 flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-purple-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-purple-500"></span>
            </span>
          )}
        </div>

        <span className="font-medium whitespace-nowrap">
          {isFinished ? `思考完成 (${duration}s)` : `正在思考... (${duration}s)`}
        </span>

        {isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
      </div>

      <div className={clsx(
          "transition-all duration-300 ease-in-out",
          isExpanded ? "max-h-[1000px] opacity-100 mt-3" : "max-h-0 opacity-0 mt-0 overflow-hidden"
      )}>
        <div className="relative pl-4 border-l-2 border-gray-100 py-1">
          <div className="text-[14px] text-gray-500 leading-relaxed font-serif italic whitespace-pre-wrap">
            {fullContent}
            {!isFinished && (
              <span className="inline-block w-1.5 h-4 ml-1 bg-purple-400 animate-pulse align-middle" />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}