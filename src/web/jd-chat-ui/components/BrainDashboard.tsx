import { useState } from "react";
import { Brain, Database, Network, ExternalLink, ChevronRight, Activity } from "lucide-react";
import clsx from "clsx";

// 定义数据类型
export interface DashboardState {
  currentStep: string;      // parser | researcher | tech_lead | reviewer
  userProfile: string[];    // 用户画像标签
  ragSources: { title: string; url: string; score: number }[]; // RAG 来源
}

export default function BrainDashboard({ data }: { data: DashboardState }) {
  // 预定义的流程步骤
  const steps = [
    { id: "parser", label: "JD 解析" },
    { id: "researcher", label: "背景调查" },
    { id: "hr_agent", label: "行为出题" },
    { id: "tech_lead", label: "技术出题" },
    { id: "reviewer", label: "质量检测" },
  ];

  return (
    <div className="h-full flex flex-col gap-6 p-4 overflow-y-auto scrollbar-thin">

      {/* --- 模块 1: 思维状态机 (Workflow) --- */}
      <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm">
        <div className="flex items-center gap-2 mb-4 text-sm font-bold text-gray-700">
          <Activity size={16} className="text-blue-500" />
          <span>Agent 思维流转</span>
        </div>
        <div className="relative pl-2">
          {/* 连线 */}
          <div className="absolute left-[11px] top-2 bottom-2 w-0.5 bg-gray-100" />

          {steps.map((step, idx) => {
            const isActive = data.currentStep === step.id;
            const isPast = steps.findIndex(s => s.id === data.currentStep) > idx;

            return (
              <div key={step.id} className="relative flex items-center gap-3 mb-4 last:mb-0 z-10">
                <div className={clsx(
                  "w-5 h-5 rounded-full border-2 flex items-center justify-center transition-all duration-300 bg-white",
                  isActive ? "border-blue-500 scale-110 shadow-blue-200 shadow-md" :
                  isPast ? "border-green-500 bg-green-50" : "border-gray-300"
                )}>
                  {isPast && <div className="w-2 h-2 bg-green-500 rounded-full" />}
                  {isActive && <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse" />}
                </div>
                <span className={clsx(
                  "text-xs font-medium transition-colors",
                  isActive ? "text-blue-600" : isPast ? "text-gray-800" : "text-gray-400"
                )}>
                  {step.label}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* --- 模块 2: 长期记忆 (User Profile) --- */}
      <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm">
        <div className="flex items-center gap-2 mb-3 text-sm font-bold text-gray-700">
          <Brain size={16} className="text-purple-500" />
          <span>长期记忆 (LTM)</span>
        </div>
        <div className="flex flex-wrap gap-2">
          {data.userProfile.length > 0 ? (
            data.userProfile.map((tag, i) => (
              <span key={i} className="px-2 py-1 bg-purple-50 text-purple-700 text-xs rounded-md border border-purple-100">
                {tag}
              </span>
            ))
          ) : (
            <span className="text-xs text-gray-400 italic">暂无提取到的用户画像...</span>
          )}
        </div>
      </div>

      {/* --- 模块 3: 知识库引用 (RAG) --- */}
      <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm">
        <div className="flex items-center gap-2 mb-3 text-sm font-bold text-gray-700">
          <Database size={16} className="text-amber-500" />
          <span>知识库引用 (RAG)</span>
        </div>
        <div className="space-y-2">
          {data.ragSources.length > 0 ? (
            data.ragSources.map((source, i) => (
              <a
                key={i}
                href={source.url}
                target="_blank"
                className="block group p-2 rounded-lg hover:bg-gray-50 transition-colors border border-transparent hover:border-gray-100"
              >
                <div className="flex justify-between items-center mb-1">
                  <span className="text-xs font-medium text-gray-700 truncate max-w-[180px] md:max-w-[230px]">{source.title}</span>
                  <ExternalLink size={10} className="text-gray-300 group-hover:text-blue-400" />
                </div>
                <div className="flex items-center gap-2">
                  <div className="flex-1 h-1 bg-gray-100 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-amber-400 rounded-full"
                      style={{ width: `${source.score * 100}%` }}
                    />
                  </div>
                  <span className="text-[10px] text-gray-400">{(source.score * 100).toFixed(0)}%</span>
                </div>
              </a>
            ))
          ) : (
            <span className="text-xs text-gray-400 italic">本次回答未引用外部知识库</span>
          )}
        </div>
      </div>

    </div>
  );
}