// hooks/useChat.ts
import { useRef, useEffect } from "react";
import { useMessageStore } from "@/stores/useMessageStore";
import { useSessionStore } from "@/stores/useSessionStore";
import { useAudioQueue } from "@/hooks/useAudioQueue";
import { ChatMode } from "@/types/chat";

export const API_BASE = "/api/v1";

interface UseChatStreamProps {
  mode: ChatMode | 'rag';
  isTTSEnabled: boolean;
  onDashboardUpdate: (key: string, value: any) => void;
  onSessionCreated?: (id: number) => void;
  onLogout: () => void;
}

interface ReportData {
  meta: {
    company_name: string;
    tech_stack: string[];
    session_id?: number;
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

export function useChatStream({
  mode,
  isTTSEnabled,
  onDashboardUpdate,
  onSessionCreated,
  onLogout
}: UseChatStreamProps) {
  // 从 Store 获取状态和 actions
  const { token, currentSessionId, setCurrentSessionId, fetchSessions } = useSessionStore();
  const { addMessage, setIsLoading, updateLastMessage, isLoading } = useMessageStore();
  const { addToQueue, stopAudio, unlockAudio } = useAudioQueue({ token, onLogout });

  const isTTSRef = useRef(isTTSEnabled);
  useEffect(() => {
    isTTSRef.current = isTTSEnabled;
    if (!isTTSEnabled) stopAudio();
  }, [isTTSEnabled, stopAudio]);

  const formatReportToMarkdown = (data: ReportData) => {
    const { meta, tech_questions, company_analysis } = data;
    return `## 📊 ${meta.company_name || '岗位'} 分析\n\n**技术栈**: \`${meta.tech_stack.join('`, `')}\`\n\n${company_analysis ? `> 🏢 **公司**: ${company_analysis}\n\n` : ''}### 🛠️ 推荐技术题\n${tech_questions.map((q,i)=>`**Q${i+1}: ${q.question}**\n> ${q.reference_answer}`).join('\n\n')}`;
  };

  const readStream = async (res: Response) => {
    if (!res.body) return;
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let bufferText = "";

    // 标记是否已经接收到了第一个有效数据块
    let hasReceivedData = false;

    try {
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        // 【核心修复】只要有数据流到达，立即关闭全局 Loading 状态
        if (!hasReceivedData) {
          setIsLoading(false);
          hasReceivedData = true;
        }

        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split("\n\n");

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            const dataStr = line.replace("data: ", "").trim();

            if (dataStr === "[DONE]") {
              updateLastMessage(msg => ({ ...msg, isThinkingFinished: true }));
              return;
            }
            if (!dataStr) continue;

            try {
              const payload = JSON.parse(dataStr);

              // 1. 处理结构化监控数据
              if (payload.type === 'data') {
                onDashboardUpdate(payload.key, payload.value);
              }

              // 2. 处理思考内容 (DeepSeek 风格)
              else if (payload.type === 'thought') {
                updateLastMessage(msg => ({
                  ...msg,
                  // 只要开始有思考，就关闭 isLoading（双重保障）
                  isLoading: false,
                  thoughts: [...(msg.thoughts || []), payload.content],
                  isThinkingFinished: false,
                }));
              }

              // 3. 处理报告/结果数据
              else if (payload.type === 'result') {
                const reportData: ReportData = payload.content;
                updateLastMessage(msg => ({
                  ...msg,
                  content: formatReportToMarkdown(reportData),
                  isJson: true,
                  isThinkingFinished: true,
                }));

                if (reportData.meta.session_id) {
                  setCurrentSessionId(reportData.meta.session_id);
                  fetchSessions();
                  if (onSessionCreated) onSessionCreated(reportData.meta.session_id);
                }
              }

              // 4. 处理普通正文 Token
              else if (payload.type === 'token') {
                updateLastMessage(msg => ({
                  ...msg,
                  content: msg.content + (payload.content || ""),
                  // 一旦开始输出正式内容，思考标记为结束
                  isThinkingFinished: true
                }));

                if (isTTSRef.current) {
                  bufferText += payload.content || "";
                  if (/[。！？\.\!\?\:\n]/.test(payload.content)) {
                    addToQueue(bufferText);
                    bufferText = "";
                  }
                }
              }
            } catch (e) {
              console.warn("Stream JSON parse error:", e);
            }
          }
        }
      }
    } catch (err) {
      console.error("Stream failed:", err);
      const errorMessage = err instanceof Error ? err.message : "未知错误";
      updateLastMessage(msg => ({
        ...msg,
        content: msg.content + `\n\n❌ 流式传输中断: ${errorMessage}`,
        isThinkingFinished: true,
      }));
    } finally {
      setIsLoading(false);
      if (isTTSRef.current && bufferText.trim()) addToQueue(bufferText);
    }
  };

  const sendMessage = async (text: string) => {
    if (!text.trim() || isLoading || !token) return;

    unlockAudio();
    stopAudio();
    setIsLoading(true); // 开启初始加载动画

    // 预增加用户消息和助手占位消息
    addMessage({ role: "user", content: text });
    addMessage({
      role: "assistant",
      content: "",
      thoughts: [],
      isThinkingFinished: false
    });

    try {
      const headers = {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`
      };

      let url = "";
      let body: any = {};

      // 路由逻辑
      if (mode === 'rag') {
        url = `${API_BASE}/qa/qa`;
        body = { question: text };
      } else if (currentSessionId) {
        url = `${API_BASE}/chat/stream`;
        body = { session_id: currentSessionId, content: text };
      } else if (mode === 'guide') {
        url = `${API_BASE}/jd/generate-guide`;
        body = { jd_text: text };
      } else {
        url = `${API_BASE}/interview/mock-interview/stream`;
        body = { jd_text: text };
      }

      const res = await fetch(url, {
        method: "POST",
        headers,
        body: JSON.stringify(body)
      });

      if (!res.ok) {
        if (res.status === 401) onLogout();
        throw new Error(`API Error: ${res.statusText} (${res.status})`);
      }

      // 请求只要 res.ok，其实已经可以关闭全局 Loader 了，
      // 因为接下来的 readStream 会处理具体的思考 UI。
      // 但为了平滑，我们在 readStream 的第一个块处关闭。
      await readStream(res);

    } catch (e) {
      const errorContent = e instanceof Error ? e.message : "An unknown error occurred.";
      setIsLoading(false);
      updateLastMessage(msg => ({
        ...msg,
        content: `❌ 网络请求失败: ${errorContent}`,
        isThinkingFinished: true
      }));
    }
  };

  return { sendMessage };
}