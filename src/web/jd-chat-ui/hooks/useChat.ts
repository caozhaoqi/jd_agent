// hooks/useChat.ts
import { useState, useRef, useEffect } from "react";
import { Message, ChatMode } from "@/types/chat";
import { useAudioQueue } from "@/hooks/useAudioQueue";

// 定义后端 API 基础路径，使用相对路径通过Next.js代理转发
export const API_BASE = "/api/v1";

// API 请求配置
const API_CONFIG = {
  TIMEOUT: 60000, // 60秒超时
  MAX_RETRIES: 2, // 最大重试次数
  RETRY_DELAY: 2000, // 重试延迟
};

// 接口定义
interface UseChatProps {
  token: string | null;
  mode: ChatMode | 'rag';
  currentSessionId: number | null;
  isTTSEnabled: boolean;
  onDashboardUpdate: (key: string, value: string | string[] | { title: string; url: string; score: number }[]) => void;
  onSessionCreated: (id: number) => void;
}

interface ReportData {
  meta: {
    company_name: string;
    tech_stack: string[];
  };
  tech_questions: Array<{
    question: string;
    reference_answer: string;
  }>;
  hr_questions?: Array<{
    question: string;
    reference_answer: string;
  }>;
  company_analysis?: string;
}

interface RAGResponse {
  answer: string;
  sources: string[];
}

export function useChat({ token, mode, currentSessionId, isTTSEnabled, onDashboardUpdate, onSessionCreated }: UseChatProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [showStartInterviewBtn, setShowStartInterviewBtn] = useState(false);

  const { addToQueue, stopAudio, unlockAudio } = useAudioQueue();
  const isTTSRef = useRef(isTTSEnabled);
  const abortControllerRef = useRef<AbortController | null>(null);

  // 同步 TTS 开关引用
  useEffect(() => {
    isTTSRef.current = isTTSEnabled;
    if (!isTTSEnabled) stopAudio();
  }, [isTTSEnabled, stopAudio]);

  // 清理函数
  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  // 超时处理函数
  const fetchWithTimeout = async (url: string, options: RequestInit = {}) => {
    const controller = new AbortController();
    abortControllerRef.current = controller;
    const timeoutId = setTimeout(() => controller.abort(), API_CONFIG.TIMEOUT);

    try {
      const response = await fetch(url, { ...options, signal: controller.signal });
      clearTimeout(timeoutId);
      return response;
    } catch (error) {
      clearTimeout(timeoutId);
      if (error instanceof Error && error.name === 'AbortError') {
        throw new Error(`请求超时 (${API_CONFIG.TIMEOUT}ms)`);
      }
      throw error;
    }
  };

  // 重试机制函数
  const fetchWithRetry = async (url: string, options: RequestInit = {}, retries = API_CONFIG.MAX_RETRIES): Promise<Response> => {
    try {
      const response = await fetchWithTimeout(url, options);
      if (!response.ok) {
        const errorText = await response.text();
        let errorMessage = `服务器错误: ${response.status}`;
        try {
          const errorData = JSON.parse(errorText);
          errorMessage = errorData.detail || errorData.message || errorMessage;
        } catch {
          errorMessage = errorText || errorMessage;
        }
        throw new Error(errorMessage);
      }
      return response;
    } catch (error) {
      if (retries > 0) {
        await new Promise(resolve => setTimeout(resolve, API_CONFIG.RETRY_DELAY));
        return fetchWithRetry(url, options, retries - 1);
      }
      throw error;
    }
  };

  // --- 辅助函数：格式化 Markdown ---
  const formatReportToMarkdown = (data: ReportData) => {
      const { meta, tech_questions, company_analysis } = data;
      return `## 📊 ${meta.company_name || '岗位'} 分析\n\n**技术栈**: \`${meta.tech_stack.join('`, `')}\`\n\n${company_analysis ? `> 🏢 **公司**: ${company_analysis}\n\n` : ''}### 🛠️ 推荐技术题\n${tech_questions.map((q,i)=>`**Q${i+1}: ${q.question}**\n> ${q.reference_answer}`).join('\n\n')}`;
  };

  const formatRAGResponse = (data: RAGResponse) => {
    const { answer, sources } = data;
    if (!sources || sources.length === 0) return answer;
    const sourceList = sources.map((s) => `- 📄 ${s}`).join("\n");
    return `${answer}\n\n---\n**📚 引用来源:**\n${sourceList}`;
  };

  // --- 核心：流式读取 ---
  const readStream = async (res: Response) => {
      if (!res.body) return;
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let done = false;
      let bufferText = "";

      try {
          while (!done) {
              const { value, done: d } = await reader.read();
              done = d;
              const chunk = decoder.decode(value, { stream: true });
              const lines = chunk.split("\n\n");

              for (const line of lines) {
                  if (line.startsWith("data: ")) {
                          const dataStr = line.replace("data: ", "").trim();
                          if (dataStr === "[DONE]") {
                              // 收到结束信号，标记思考过程为完成
                              setMessages(prev => {
                                  if (prev.length === 0) return prev;
                                  const newMsgs = [...prev];
                                  const lastIndex = newMsgs.length - 1;
                                  const lastMsg = { ...newMsgs[lastIndex] };
                                  
                                  if (lastMsg.role === "assistant") {
                                      lastMsg.isThinkingFinished = true;
                                      newMsgs[lastIndex] = lastMsg;
                                  }
                                  
                                  return newMsgs;
                              });
                              break;
                          }
                          if (!dataStr) continue;

                      try {
                          const payload = JSON.parse(dataStr);

                          // 更新 Dashboard
                          if (payload.type === 'data') {
                              onDashboardUpdate(payload.key, payload.value);
                              continue;
                          }

                          // 更新消息
                          setMessages(prev => {
                              if (prev.length === 0) return prev;
                              const newMsgs = [...prev];
                              // 注意：React 中直接修改对象引用可能导致不更新，这里浅拷贝最后一项
                              const lastIndex = newMsgs.length - 1;
                              const lastMsg = { ...newMsgs[lastIndex] };

                              if (lastMsg.role === "assistant") {
                                  if (payload.type === 'thought') {
                                    const currentThoughts = lastMsg.thoughts || [];
                                    if (currentThoughts[currentThoughts.length - 1] !== payload.content) {
                                        lastMsg.thoughts = [...currentThoughts, payload.content];
                                    }
                                    // 收到新的思考步骤，标记思考未完成
                                    lastMsg.isThinkingFinished = false;
                                    // 收到第一个思考过程后，隐藏全局加载指示器
                                    if (lastMsg.thoughts && lastMsg.thoughts.length === 1) {
                                        setIsLoading(false);
                                    }
                                }
                                  else if (payload.type === 'result') {
                                      const reportData = payload.content;
                                      lastMsg.content = formatReportToMarkdown(reportData);
                                      lastMsg.isJson = true;
                                      if (reportData.session_id) onSessionCreated(reportData.session_id);
                                      // 收到最终结果，标记思考完成
                                      lastMsg.isThinkingFinished = true;
                                  }
                                  else if (payload.type === 'token') {
                                      lastMsg.content += (payload.content || "");
                                      // 只有在明确知道思考过程已完成时才标记为true
                                      // 避免在开始生成内容时过早标记思考完成
                                      if (lastMsg.isThinkingFinished === undefined) {
                                          lastMsg.isThinkingFinished = false;
                                      }
                                  }
                                  newMsgs[lastIndex] = lastMsg;
                              }
                              return newMsgs;
                          });

                          // TTS
                          if (isTTSRef.current && payload.type === 'token') {
                              const text = payload.content || "";
                              bufferText += text;
                              if (/[。！？\.\!\?\:\n]/.test(text)) {
                                  addToQueue(bufferText);
                                  bufferText = "";
                              }
                          }
                      } catch (e) { console.warn("Stream parse error:", e); }
                  }
              }
          }
      } catch (err) {
          console.error("Stream failed:", err);
          setMessages(prev => {
            const lastMsg = prev[prev.length - 1];
            const errorMessage = err instanceof Error ? err.message : "未知错误";
            if (lastMsg?.role === "assistant") {
              const newMsgs = [...prev];
              newMsgs[newMsgs.length - 1] = { 
                ...lastMsg,
                content: lastMsg.content + `\n\n❌ 流式传输失败: ${errorMessage}`,
                isThinkingFinished: true
              };
              return newMsgs;
            }
            return [...prev, { role: "assistant", content: `❌ 流式传输失败: ${errorMessage}` }];
          });
        } finally {
            if (isTTSRef.current && bufferText.trim()) addToQueue(bufferText);
        }
  };

  // --- 发送消息主逻辑 ---
  const sendMessage = async (text: string) => {
    if (!text.trim() || isLoading || !token) return;

    unlockAudio();
    stopAudio();
    setIsLoading(true);
    setShowStartInterviewBtn(false);

    setMessages(prev => [...prev, { role: "user", content: text }]);

    try {
        const headers = { "Content-Type": "application/json", "Authorization": `Bearer ${token}` };

        // 🟢 场景 A: 知识库 RAG
        if (mode === 'rag') {
            // 添加带有思考过程的助手消息，与其他模式保持一致
            setMessages(prev => [...prev, { 
                role: "assistant", 
                content: "", 
                thoughts: ["🔍 正在检索知识库..."],
                isThinkingFinished: false 
            }]);
            
            // 关闭全局加载状态，显示思考过程
            setIsLoading(false);

            // 使用带重试机制的请求
            const res = await fetchWithRetry(`${API_BASE}/qa/qa`, {
                method: "POST",
                headers,
                body: JSON.stringify({ question: text })
            });

            console.log("RAG API Response Status:", res.status);
            console.log("RAG API Response Headers:", res.headers);

            const data = await res.json();
            console.log("RAG API Response Data:", data);

            const formatted = formatRAGResponse(data);
            setMessages(prev => {
                const newMsgs = [...prev];
                newMsgs[newMsgs.length - 1] = { 
                    role: "assistant", 
                    content: formatted, 
                    isJson: true,
                    thoughts: ["🔍 正在检索知识库...", "📝 整理检索结果...", "✅ 完成回答生成"],
                    isThinkingFinished: true 
                };
                return newMsgs;
            });
            if (isTTSEnabled) addToQueue(data.answer);
        }
        // 🔵 场景 B: 连续对话
        else if (currentSessionId) {
            setMessages(prev => [...prev, { role: "assistant", content: "", thoughts: ["🤔 正在分析对话上下文..."], isThinkingFinished: false }]);
            // 关闭全局加载状态，显示思考过程
            setIsLoading(false);
            const res = await fetchWithRetry(`${API_BASE}/chat/stream`, {
                method: "POST", headers, body: JSON.stringify({ session_id: currentSessionId, content: text })
            });
            await readStream(res);
        }
        // 🟡 场景 C: JD 指南生成
        else if (mode === 'guide') {
            setMessages(prev => [...prev, { role: "assistant", content: "", thoughts: ["📄 正在解析职位描述..."], isThinkingFinished: false }]);
            // 关闭全局加载状态，显示思考过程
            setIsLoading(false);
            const res = await fetchWithRetry(`${API_BASE}/jd/generate-guide`, {
                method: "POST", headers, body: JSON.stringify({ jd_text: text })
            });
            await readStream(res);
        }
        // 🟣 场景 D: 模拟面试
        else {
            setMessages(prev => [...prev, { role: "assistant", content: "", thoughts: ["🎯 正在准备模拟面试..."], isThinkingFinished: false }]);
            // 关闭全局加载状态，显示思考过程
            setIsLoading(false);
            const res = await fetchWithRetry(`${API_BASE}/interview/mock-interview/stream`, {
                method: "POST", headers, body: JSON.stringify({ jd_text: text })
            });
            await readStream(res);
        }

    } catch (e) {
        console.error(e);
        setMessages(prev => {
            const lastMsg = prev[prev.length - 1];
            const errorMessage = e instanceof Error ? e.message : "网络错误";
            let friendlyErrorMessage = errorMessage;
            
            // 友好的错误信息转换
            if (friendlyErrorMessage.includes("timeout")) {
                friendlyErrorMessage = "请求超时，请稍后重试或检查网络连接";
            } else if (friendlyErrorMessage.includes("401")) {
                friendlyErrorMessage = "登录已过期，请重新登录";
            } else if (friendlyErrorMessage.includes("500")) {
                friendlyErrorMessage = "服务器暂时无法处理请求，请稍后重试";
            } else if (friendlyErrorMessage.includes("Connection reset")) {
                friendlyErrorMessage = "网络连接中断，请检查网络并重新尝试";
            }

            if (lastMsg?.role === "assistant") {
                const newMsgs = [...prev];
                newMsgs[newMsgs.length - 1] = { 
                    role: "assistant", 
                    content: `❌ 请求失败: ${friendlyErrorMessage}`,
                    isThinkingFinished: true
                };
                return newMsgs;
            }
            return [...prev, { 
                role: "assistant", 
                content: `❌ 请求失败: ${friendlyErrorMessage}` 
            }];
        });
    } finally {
        setIsLoading(false);
    }
  };

  return {
    messages,
    setMessages,
    isLoading,
    showStartInterviewBtn,
    setShowStartInterviewBtn,
    sendMessage
  };
}