import { BrainCircuit, Loader, CircleCheck } from "lucide-react";
import clsx from "clsx";

interface ThinkingBlockProps {
  thoughts: string[]; // 思考步骤数组
  isFinished: boolean; // 是否思考完成
}

export default function ThinkingBlock({ thoughts, isFinished }: ThinkingBlockProps) {
  // 如果没有思考步骤，返回null
  if (!thoughts || thoughts.length === 0) return null;

  return (
    <div className="space-y-2 mb-3">
      {/* 思考过程标题 */}
      <div className="text-xs font-semibold text-gray-500 mb-1">思考过程</div>
      
      {/* 所有思考步骤列表 */}
      <div className="space-y-1.5">
        {thoughts.map((thought, index) => {
          const isCurrent = index === thoughts.length - 1;
          const isCompleted = index < thoughts.length - 1;
          
          return (
            <div 
              key={index} 
              className="flex items-center gap-2 text-sm transition-all duration-300 animate-fadeIn"
              style={{ animationDelay: `${index * 100}ms` }}
            >
              {/* 步骤指示器 */}
              <div className={clsx(
                "w-5 h-5 rounded-full flex items-center justify-center flex-shrink-0 transition-all duration-300",
                isCompleted ? "bg-green-100 text-green-600 scale-100" : 
                isCurrent && !isFinished ? "bg-blue-100 text-blue-600 scale-100 animate-pulse" : 
                "bg-gray-100 text-gray-400 scale-90"
              )}>
                {isCompleted ? (
                  <CircleCheck size={12} className="transition-all duration-300" />
                ) : isCurrent && !isFinished ? (
                  <Loader size={12} className="animate-spin" />
                ) : (
                  <BrainCircuit size={12} className="transition-all duration-300" />
                )}
              </div>

              {/* 思考步骤文本 */}
              <span className={clsx(
                "leading-relaxed transition-all duration-300",
                isCompleted ? "text-gray-600 opacity-100" : 
                isCurrent ? "text-blue-700 font-medium opacity-100" : 
                "text-gray-400 opacity-70"
              )}>
                {thought}
              </span>
            </div>
          );
        })}
      </div>
      
      {/* 添加全局动画样式 */}
      <style jsx>{`
        @keyframes fadeIn {
          from {
            opacity: 0;
            transform: translateY(5px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
        .animate-fadeIn {
          animation: fadeIn 0.3s ease-out forwards;
        }
      `}</style>
    </div>
  );
}