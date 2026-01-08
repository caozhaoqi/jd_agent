/**
 * 用户友好的错误消息映射系统
 * 将技术性错误转换为用户可理解的提示和恢复建议
 */

import { ErrorType, ErrorSeverity } from './error-monitor';

// 错误消息映射接口
export interface ErrorMessageMapping {
  title: string;           // 用户友好的错误标题
  message: string;         // 错误描述
  suggestions: string[];   // 恢复建议
  icon: string;           // 图标名称
  color: string;          // 错误颜色
  retryable: boolean;     // 是否可以重试
}

// 错误消息映射
const ERROR_MESSAGE_MAP: Record<ErrorType, ErrorMessageMapping> = {
  [ErrorType.RUNTIME_ERROR]: {
    title: '页面运行错误',
    message: '页面遇到了一个意外错误，这可能影响正常使用。',
    suggestions: [
      '请刷新页面重试',
      '清除浏览器缓存后重试',
      '检查浏览器版本是否过低',
      '联系技术支持团队'
    ],
    icon: 'CircleAlert',
    color: 'red',
    retryable: true
  },

  [ErrorType.PROMISE_REJECTION]: {
    title: '网络请求失败',
    message: '某个操作未能成功完成，可能是网络连接问题。',
    suggestions: [
      '检查网络连接是否正常',
      '刷新页面重试',
      '稍后再试',
      '如果问题持续，请联系技术支持'
    ],
    icon: 'Wifi',
    color: 'orange',
    retryable: true
  },

  [ErrorType.HTTP_ERROR]: {
    title: '服务器响应错误',
    message: '服务器无法处理您的请求，请稍后重试。',
    suggestions: [
      '等待几分钟后重试',
      '检查网络连接',
      '确认操作是否合法',
      '联系技术支持团队'
    ],
    icon: 'Server',
    color: 'orange',
    retryable: true
  },

  [ErrorType.NETWORK_ERROR]: {
    title: '网络连接问题',
    message: '无法连接到服务器，请检查网络设置。',
    suggestions: [
      '检查网络连接是否正常',
      '尝试访问其他网站确认网络状态',
      '重启路由器或调制解调器',
      '联系网络管理员'
    ],
    icon: 'Wifi',
    color: 'red',
    retryable: true
  },

  [ErrorType.USER_INTERACTION_ERROR]: {
    title: '操作无效',
    message: '您执行的操作无法完成，请检查输入信息。',
    suggestions: [
      '检查输入内容是否正确',
      '确保所有必填项都已填写',
      '遵循页面上的操作指引',
      '尝试不同的操作方式'
    ],
    icon: 'AlertTriangle',
    color: 'yellow',
    retryable: false
  },

  [ErrorType.RESOURCE_LOAD_ERROR]: {
    title: '资源加载失败',
    message: '页面某些资源无法加载，可能影响功能使用。',
    suggestions: [
      '刷新页面重试',
      '清除浏览器缓存',
      '检查浏览器是否支持该功能',
      '尝试使用其他浏览器'
    ],
    icon: 'FileX',
    color: 'orange',
    retryable: true
  },

  [ErrorType.COMPONENT_ERROR]: {
    title: '组件错误',
    message: '页面某个功能组件出现问题。',
    suggestions: [
      '刷新页面重试',
      '尝试重新登录',
      '清除浏览器数据后重试',
      '联系技术支持团队'
    ],
    icon: 'Package',
    color: 'orange',
    retryable: true
  }
};

// HTTP状态码映射
const HTTP_STATUS_MAP: Record<number, ErrorMessageMapping> = {
  400: {
    title: '请求格式错误',
    message: '发送给服务器的请求格式不正确。',
    suggestions: [
      '检查输入参数是否正确',
      '确认所有必填字段都已填写',
      '检查请求格式是否符合要求'
    ],
    icon: 'FileText',
    color: 'yellow',
    retryable: false
  },

  401: {
    title: '未授权访问',
    message: '您需要登录才能访问此功能。',
    suggestions: [
      '请先登录您的账户',
      '检查登录信息是否正确',
      '尝试重新登录'
    ],
    icon: 'Lock',
    color: 'red',
    retryable: false
  },

  403: {
    title: '访问被拒绝',
    message: '您没有权限访问此功能。',
    suggestions: [
      '确认您有足够的权限',
      '联系管理员获取访问权限',
      '使用有权限的账户重新操作'
    ],
    icon: 'Shield',
    color: 'red',
    retryable: false
  },

  404: {
    title: '页面不存在',
    message: '请求的资源或页面不存在。',
    suggestions: [
      '检查URL地址是否正确',
      '返回上一页或首页',
      '使用搜索功能查找相关内容'
    ],
    icon: 'FileX',
    color: 'yellow',
    retryable: false
  },

  429: {
    title: '请求过于频繁',
    message: '您的请求过于频繁，请稍后再试。',
    suggestions: [
      '等待几分钟后重试',
      '减少操作频率',
      '稍后再次尝试'
    ],
    icon: 'Clock',
    color: 'yellow',
    retryable: true
  },

  500: {
    title: '服务器内部错误',
    message: '服务器遇到了一个错误，请稍后重试。',
    suggestions: [
      '等待几分钟后重试',
      '刷新页面',
      '联系技术支持团队'
    ],
    icon: 'Server',
    color: 'red',
    retryable: true
  },

  502: {
    title: '网关错误',
    message: '服务器网关出现问题。',
    suggestions: [
      '等待几分钟后重试',
      '刷新页面',
      '检查网络连接'
    ],
    icon: 'Globe',
    color: 'orange',
    retryable: true
  },

  503: {
    title: '服务不可用',
    message: '服务器当前不可用，请稍后重试。',
    suggestions: [
      '等待服务器恢复',
      '稍后再次尝试',
      '查看服务状态页面'
    ],
    icon: 'ServerOff',
    color: 'orange',
    retryable: true
  }
};

// 根据错误类型获取用户友好的错误信息
export function getErrorMessage(errorType: ErrorType): ErrorMessageMapping {
  return ERROR_MESSAGE_MAP[errorType] || ERROR_MESSAGE_MAP[ErrorType.RUNTIME_ERROR];
}

// 根据HTTP状态码获取用户友好的错误信息
export function getHttpErrorMessage(statusCode: number): ErrorMessageMapping {
  return HTTP_STATUS_MAP[statusCode] || {
    title: '未知错误',
    message: '发生了一个未知的错误，请重试。',
    suggestions: ['刷新页面重试', '联系技术支持团队'],
    icon: 'CircleAlert',
    color: 'gray',
    retryable: true
  };
}

// 根据原始错误信息智能判断错误类型
export function classifyError(error: any): ErrorType {
  const message = error?.message?.toLowerCase() || '';
  const stack = error?.stack?.toLowerCase() || '';

  // 网络相关错误
  if (message.includes('network') || message.includes('fetch') || message.includes('connection')) {
    return ErrorType.NETWORK_ERROR;
  }

  // Promise rejection
  if (message.includes('promise') || message.includes('rejection')) {
    return ErrorType.PROMISE_REJECTION;
  }

  // HTTP错误
  if (error?.response?.status) {
    return ErrorType.HTTP_ERROR;
  }

  // 资源加载错误
  if (message.includes('load') || message.includes('resource') || message.includes('script')) {
    return ErrorType.RESOURCE_LOAD_ERROR;
  }

  // 用户交互错误
  if (message.includes('invalid') || message.includes('permission') || message.includes('access')) {
    return ErrorType.USER_INTERACTION_ERROR;
  }

  // 组件错误
  if (stack?.includes('react') || stack?.includes('component')) {
    return ErrorType.COMPONENT_ERROR;
  }

  // 默认运行时错误
  return ErrorType.RUNTIME_ERROR;
}

// 获取颜色对应的Tailwind CSS类
export function getColorClasses(color: string) {
  const colorMap: Record<string, { bg: string; text: string; border: string; icon: string }> = {
    red: {
      bg: 'bg-red-50',
      text: 'text-red-700',
      border: 'border-red-200',
      icon: 'text-red-500'
    },
    orange: {
      bg: 'bg-orange-50',
      text: 'text-orange-700',
      border: 'border-orange-200',
      icon: 'text-orange-500'
    },
    yellow: {
      bg: 'bg-yellow-50',
      text: 'text-yellow-700',
      border: 'border-yellow-200',
      icon: 'text-yellow-500'
    },
    gray: {
      bg: 'bg-gray-50',
      text: 'text-gray-700',
      border: 'border-gray-200',
      icon: 'text-gray-500'
    }
  };

  return colorMap[color] || colorMap.gray;
}