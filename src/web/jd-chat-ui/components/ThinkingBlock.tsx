import { useState, useEffect } from "react";
import { ChevronDown, ChevronRight, BrainCircuit, Loader2, CheckCircle2 } from "lucide-react";
import clsx from "clsx";

interface ThinkingBlockProps {
  thoughts: string[]; // 思考步骤数组
  isFinished: boolean; // 是否思考完成
}

export default function ThinkingBlock({ thoughts, isFinished }: ThinkingBlockProps) {
  const [isExpanded, setIsExpanded] = useState(true);
  const [elapsed, setElapsed] = useState(0);

  // 计时器
  useEffect(() => {
    if (isFinished) return;
    const timer = setInterval(() => setElapsed(s => s + 0.1), 100);
    return () => clearInterval(timer);
  }, [isFinished]);

  // 思考完成后自动折叠 (可选)
  useEffect(() => {
    if (isFinished) {
      // 等待 1 秒后自动折叠，给用户一种“完成感”
      const timer = setTimeout(() => setIsExpanded(false), 1000);
      return () => clearTimeout(timer);
    }
  }, [isFinished]);

  if (!thoughts || thoughts.length === 0) return null;

  const statusText = isFinished
    ? `深度思考已完成 (耗时 ${elapsed.toFixed(1)}s)`
    : "DeepSeek 正在思考...";

  return (
    <div className="mb-4 rounded-xl border border-gray-200 bg-gray-50/50 overflow-hidden transition-all duration-300">
      {/* 标题栏 */}
      <div
        className="flex items-center gap-2 px-4 py-3 cursor-pointer hover:bg-gray-100/80 transition-colors select-none"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className={clsx("p-1 rounded", isFinished ? "text-green-600" : "text-blue-600 animate-pulse")}>
            {isFinished ? <BrainCircuit size={18} /> : <Loader2 size={18} className="animate-spin" />}
        </div>

        <span className="text-sm font-medium text-gray-600">{statusText}</span>

        <div className="ml-auto text-gray-400 transition-transform duration-200" style={{ transform: isExpanded ? 'rotate(180deg)' : 'rotate(0deg)' }}>
          <ChevronDown size={16} />
        </div>
      </div>

      {/* 思考内容区 (手风琴动画) */}
      <div className={clsx(
          "transition-[max-height,opacity] duration-500 ease-in-out overflow-hidden",
          isExpanded ? "max-h-[500px] opacity-100" : "max-h-0 opacity-0"
      )}>
        <div className="px-4 pb-4 pt-0 border-t border-gray-100 bg-white/50">
          <ul className="space-y-3 mt-3 relative">
            {/* 连线效果 */}
            <div className="absolute left-[7px] top-2 bottom-2 w-0.5 bg-gray-200" />

            {thoughts.map((step, idx) => (
              <li key={idx} className="flex gap-3 text-sm text-gray-600 items-start animate-in fade-in slide-in-from-left-2 duration-300 relative z-10">
                <div className={clsx(
                    "w-4 h-4 rounded-full border-2 flex-shrink-0 mt-0.5 bg-white",
                    idx === thoughts.length - 1 && !isFinished
                        ? "border-blue-500 animate-ping"
                        : "border-gray-300"
                )} />
                <span className={clsx(idx === thoughts.length - 1 && !isFinished && "text-blue-600 font-medium")}>
                    {step}
                </span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}