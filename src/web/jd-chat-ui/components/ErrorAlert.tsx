"use client";

import React, { useState, useEffect } from 'react';
import {
  CircleAlert,
  FileX,
  Lock,
  Shield,
  Server,
  Wifi,
  ServerOff,
  Clock,
  FileText,
  Package,
  X,
  RefreshCw,
  ExternalLink,
  MessageCircle,
  Globe
} from 'lucide-react';

import { ErrorData, ErrorType, errorMonitor } from '../utils/error-monitor';
import {
  getErrorMessage,
  getHttpErrorMessage,
  classifyError,
  getColorClasses,
  ErrorMessageMapping
} from '../utils/error-messages';

interface ErrorAlertProps {
  error: string | ErrorData | any;
  onRetry?: () => void;
  onDismiss?: () => void;
  type?: 'inline' | 'modal' | 'banner';
  showDetails?: boolean;
  autoHide?: boolean;
  autoHideDelay?: number;
  context?: Record<string, any>;
}

// 图标映射
const iconMap = {
  CircleAlert,
  FileX,
  Lock,
  Shield,
  Server,
  Wifi,
  Globe,
  ServerOff,
  Clock,
  FileText,
  Package
};

export default function ErrorAlert({
  error,
  onRetry,
  onDismiss,
  type = 'inline',
  showDetails = false,
  autoHide = false,
  autoHideDelay = 5000,
  context = {}
}: ErrorAlertProps) {
  const [isVisible, setIsVisible] = useState(true);
  const [errorInfo, setErrorInfo] = useState<{
    data: ErrorData;
    mapping: ErrorMessageMapping;
  } | null>(null);

  useEffect(() => {
    if (!error) return;

    // 解析错误信息
    let errorData: ErrorData;
    let errorMapping: ErrorMessageMapping;

    // 处理不同的错误输入类型
    if (typeof error === 'string') {
      errorData = {
        id: `err_${Date.now()}`,
        type: ErrorType.RUNTIME_ERROR,
        severity: 'MEDIUM' as any,
        message: error,
        url: window.location.href,
        timestamp: new Date().toISOString(),
        context
      };
      errorMapping = getErrorMessage(ErrorType.RUNTIME_ERROR);
      // 报告错误到监控系统
      errorMonitor.handleError({
        type: ErrorType.RUNTIME_ERROR,
        message: error,
        context
      });
    } else if (error?.type && error?.message) {
      // 已经是ErrorData格式
      errorData = error;
      errorMapping = getErrorMessage(error.type);
    } else {
      // 原始错误对象，需要分类
      const classifiedType = classifyError(error);
      errorData = {
        id: `err_${Date.now()}`,
        type: classifiedType,
        severity: 'MEDIUM' as any,
        message: error?.message || 'Unknown error',
        stack: error?.stack,
        url: window.location.href,
        timestamp: new Date().toISOString(),
        context: { originalError: error, ...context }
      };
      errorMapping = getErrorMessage(classifiedType);
      // 报告错误到监控系统
      errorMonitor.handleError({
        type: classifiedType,
        message: error?.message || 'Unknown error',
        stack: error?.stack,
        context: { originalError: error, ...context }
      });
    }

    // 处理HTTP状态码错误
    if (error?.response?.status) {
      errorMapping = getHttpErrorMessage(error.response.status);
    }

    setErrorInfo({ data: errorData, mapping: errorMapping });

    // 自动隐藏逻辑
    if (autoHide && type === 'inline') {
      const timer = setTimeout(() => {
        handleDismiss();
      }, autoHideDelay);

      return () => clearTimeout(timer);
    }
  }, [error, autoHide, autoHideDelay, type, context]);

  const handleDismiss = () => {
    setIsVisible(false);
    onDismiss?.();
  };

  const handleRetry = () => {
    onRetry?.();
    handleDismiss();
  };

  const handleReport = () => {
    if (errorInfo?.data) {
      errorMonitor.sendErrorsToServer();
      // 显示报告成功提示
      alert('错误报告已发送，感谢您的反馈！');
    }
  };

  if (!isVisible || !errorInfo) {
    return null;
  }

  const { data: errorData, mapping: errorMapping } = errorInfo;
  const colors = getColorClasses(errorMapping.color);
  const IconComponent = iconMap[errorMapping.icon as keyof typeof iconMap] || CircleAlert;

  // 样式映射
  const typeStyles = {
    inline: 'rounded-lg border p-4',
    modal: 'rounded-lg border p-6 max-w-md mx-auto',
    banner: 'rounded-none border-l-4 p-4'
  };

  const containerClasses = `
    ${typeStyles[type]}
    ${colors.bg} ${colors.border}
    animate-in fade-in zoom-in-95 duration-300
    ${type === 'banner' ? 'sticky top-0 z-50' : ''}
  `;

  return (
    <div className={containerClasses} role="alert">
      <div className="flex items-start gap-3">
        {/* 图标 */}
        <div className={`flex-shrink-0 p-1 rounded-full ${colors.bg}`}>
          <IconComponent className={`h-5 w-5 ${colors.icon}`} />
        </div>

        {/* 错误内容 */}
        <div className="flex-1 min-w-0">
          {/* 标题和关闭按钮 */}
          <div className="flex items-start justify-between gap-2">
            <h3 className={`text-sm font-semibold ${colors.text}`}>
              {errorMapping.title}
            </h3>
            <div className="flex items-center gap-1">
              {onRetry && errorMapping.retryable && (
                <button
                  onClick={handleRetry}
                  className="p-1 text-xs hover:bg-black/5 rounded transition-colors"
                  title="重试"
                >
                  <RefreshCw className="h-3 w-3" />
                </button>
              )}
              {onDismiss && (
                <button
                  onClick={handleDismiss}
                  className="p-1 text-xs hover:bg-black/5 rounded transition-colors"
                  title="关闭"
                >
                  <X className="h-3 w-3" />
                </button>
              )}
            </div>
          </div>

          {/* 错误消息 */}
          <p className={`text-sm mt-1 ${colors.text} opacity-90`}>
            {errorMapping.message}
          </p>

          {/* 建议操作 */}
          {errorMapping.suggestions.length > 0 && (
            <div className="mt-3">
              <p className={`text-xs font-medium ${colors.text} mb-1`}>
                建议操作：
              </p>
              <ul className={`text-xs ${colors.text} opacity-80 space-y-1`}>
                {errorMapping.suggestions.slice(0, 3).map((suggestion, index) => (
                  <li key={index} className="flex items-start gap-1">
                    <span className="text-xs mt-1">•</span>
                    <span>{suggestion}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* 操作按钮 */}
          <div className="flex items-center gap-2 mt-4">
            {onRetry && errorMapping.retryable && (
              <button
                onClick={handleRetry}
                className={`inline-flex items-center gap-1 px-3 py-1 text-xs font-medium rounded-md transition-colors ${
                  errorMapping.color === 'red'
                    ? 'bg-red-100 text-red-700 hover:bg-red-200'
                    : errorMapping.color === 'orange'
                    ? 'bg-orange-100 text-orange-700 hover:bg-orange-200'
                    : 'bg-blue-100 text-blue-700 hover:bg-blue-200'
                }`}
              >
                <RefreshCw className="h-3 w-3" />
                重试
              </button>
            )}

            <button
              onClick={handleReport}
              className="inline-flex items-center gap-1 px-3 py-1 text-xs font-medium rounded-md bg-gray-100 text-gray-700 hover:bg-gray-200 transition-colors"
            >
              <MessageCircle className="h-3 w-3" />
              报告错误
            </button>

            {showDetails && errorData.stack && (
              <details className="mt-2">
                <summary className={`text-xs ${colors.text} cursor-pointer hover:underline`}>
                  查看技术详情
                </summary>
                <pre className="mt-2 text-xs bg-gray-100 p-2 rounded overflow-auto max-h-32">
                  {errorData.stack}
                </pre>
              </details>
            )}
          </div>

          {/* 时间戳 */}
          <p className="text-xs text-gray-500 mt-2">
            {new Date(errorData.timestamp).toLocaleString()}
          </p>
        </div>
      </div>
    </div>
  );
}