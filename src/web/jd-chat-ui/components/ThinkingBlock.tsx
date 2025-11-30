import { useState } from "react";
import { ChevronDown, ChevronRight, BrainCircuit, Loader2 } from "lucide-react";

interface ThinkingBlockProps {
  steps: string[];
  isFinished: boolean; // 是否思考完成（如果有正文内容了，就算完成了）
}

export default function ThinkingBlock({ steps, isFinished }: ThinkingBlockProps) {
  const [isExpanded, setIsExpanded] = useState(true); // 默认展开

  if (!steps || steps.length === 0) return null;

  // 计算耗时（模拟）或者显示最后一步
  const statusText = isFinished ? `已深度思考 (共 ${steps.length} 步)` : "DeepSeek 正在思考...";

  return (
    <div className="mb-4 rounded-lg border border-gray-200 bg-gray-50 overflow-hidden">
      {/* 标题栏 */}
      <div
        className="flex items-center gap-2 px-3 py-2 cursor-pointer hover:bg-gray-100 transition-colors"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        {isFinished ? (
            <BrainCircuit size={16} className="text-gray-500" />
        ) : (
            <Loader2 size={16} className="animate-spin text-blue-600" />
        )}

        <span className="text-xs font-medium text-gray-500">{statusText}</span>

        <div className="ml-auto text-gray-400">
          {isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        </div>
      </div>

      {/* 思考内容区 */}
      {isExpanded && (
        <div className="px-3 py-2 border-t border-gray-200 bg-white/50">
          <ul className="space-y-2">
            {steps.map((step, idx) => (
              <li key={idx} className="flex gap-2 text-xs text-gray-600 animate-in fade-in slide-in-from-left-2 duration-300">
                <span className="text-gray-400 min-w-[16px]">{idx + 1}.</span>
                <span>{step}</span>
              </li>
            ))}
            {!isFinished && (
               <li className="flex gap-2 text-xs text-blue-500 animate-pulse">
                 <span className="min-w-[16px]"></span>
                 <span>...</span>
               </li>
            )}
          </ul>
        </div>
      )}
    </div>
  );
}