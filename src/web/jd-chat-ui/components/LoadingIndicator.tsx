"use client";

import { Loader, Search, FileText, Brain } from "lucide-react";
import clsx from "clsx";

export type LoadingType = 'default' | 'searching' | 'thinking' | 'generating' | 'uploading';

interface LoadingIndicatorProps {
  type?: LoadingType;
  size?: 'small' | 'medium' | 'large';
  message?: string;
  className?: string;
}

export default function LoadingIndicator({
  type = 'default',
  size = 'medium',
  message,
  className
}: LoadingIndicatorProps) {
  // 设置不同类型的图标和消息
  const getLoadingConfig = () => {
    switch (type) {
      case 'searching':
        return {
          icon: <Search size={size === 'small' ? 14 : size === 'medium' ? 18 : 24} className="animate-pulse" />,
          text: message || "正在搜索相关知识..."
        };
      case 'thinking':
        return {
          icon: <Brain size={size === 'small' ? 14 : size === 'medium' ? 18 : 24} className="text-purple-500 animate-pulse" />,
          text: message || "AI 正在思考中..."
        };
      case 'generating':
        return {
          icon: <Loader size={size === 'small' ? 14 : size === 'medium' ? 18 : 24} className="text-blue-500 animate-spin" />,
          text: message || "正在生成回复..."
        };
      case 'uploading':
        return {
          icon: <FileText size={size === 'small' ? 14 : size === 'medium' ? 18 : 24} className="text-green-500 animate-pulse" />,
          text: message || "正在上传文件..."
        };
      default:
        return {
          icon: <Loader size={size === 'small' ? 14 : size === 'medium' ? 18 : 24} className="animate-spin text-gray-500" />,
          text: message || "加载中..."
        };
    }
  };

  const { icon, text } = getLoadingConfig();

  // 设置尺寸类
  const sizeClasses = {
    small: 'text-xs p-1',
    medium: 'text-sm p-2',
    large: 'text-base p-3'
  };

  // 设置动画类
  const animationClasses = {
    small: 'animate-in fade-in zoom-in-95 duration-300',
    medium: 'animate-in fade-in zoom-in-95 duration-500',
    large: 'animate-in fade-in zoom-in-95 duration-700'
  };

  return (
    <div className={clsx(
      "flex items-center justify-center gap-2 rounded-full border bg-white shadow-sm",
      sizeClasses[size],
      animationClasses[size],
      className
    )}>
      {icon}
      <span className="font-medium whitespace-nowrap">{text}</span>
    </div>
  );
}