import { useRef, useEffect } from "react";
import { useSessionStore } from "@/stores/useSessionStore";
import { useMessageStore } from "@/stores/useMessageStore";
import { useAudioQueue } from "@/hooks/useAudioQueue";
import { ChatMode, Message } from "@/types/chat";

export const API_BASE = "/api/v1";

interface UseChatStreamProps {
  mode: ChatMode | 'rag';
  isTTSEnabled: boolean;
  onDashboardUpdate: (key: string, value: any) => void;
}

export function useChatStream({ mode, isTTSEnabled, onDashboardUpdate }: UseChatStreamProps) {
  const { token, currentSessionId, setCurrentSessionId, logout } = useSessionStore();
  const { addMessage, setIsLoading, updateLastMessage, setShowStartInterviewBtn } = useMessageStore();
  const { addToQueue, stopAudio, unlockAudio } = useAudioQueue({ token, onLogout: logout });

  const isTTSRef = useRef(isTTSEnabled);
  useEffect(() => { isTTSRef.current = isTTSEnabled; if (!isTTSEnabled) stopAudio(); }, [isTTSEnabled, stopAudio]);

  const readStream = async (res: Response) => {
    // ... (stream reading logic remains the same, but uses store actions)
    if (!res.body) return;
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let bufferText = "";
    let hasReceivedAnyMessage = false; // 标记是否收到任何消息

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      const chunk = decoder.decode(value, { stream: true });
      const lines = chunk.split("\n\n");

      for (const line of lines) {
        if (line.startsWith("data: ")) {
          const dataStr = line.replace("data: ", "").trim();
          if (dataStr === "[DONE]") {
            updateLastMessage(msg => ({ ...msg, isThinkingFinished: true }));
            setIsLoading(false); // 确保结束时隐藏加载状态
            return;
          }
          if (!dataStr) continue;

          try {
            const payload = JSON.parse(dataStr);
            // 收到任何有效消息时，立即隐藏加载提示
            if (!hasReceivedAnyMessage) {
              hasReceivedAnyMessage = true;
              setIsLoading(false);
            }
            
            if (payload.type === 'data') {
              onDashboardUpdate(payload.key, payload.value);
            } else if (payload.type === 'thought') {
              // 收到思考消息时，更新思考过程，并在内容为空时填充可见提示
              const thoughtText = payload.content || payload.detail || '';
              updateLastMessage(msg => ({
                ...msg,
                thoughts: [...(msg.thoughts || []), thoughtText],
                // 如果当前内容为空，用思考文本填充，避免只显示“正在思考...”
                content: msg.content || thoughtText || '正在分析中...',
                isThinkingFinished: false,
              }));
            } else if (payload.type === 'result') {
              const reportData = payload.content;
              updateLastMessage(msg => ({
                ...msg,
                content: formatReportToMarkdown(reportData),
                isJson: true,
                isThinkingFinished: true,
              }));
              if (reportData.session_id) setCurrentSessionId(reportData.session_id);
            } else if (payload.type === 'token') {
              updateLastMessage(msg => ({ ...msg, content: msg.content + (payload.content || "") }));
              if (isTTSRef.current) {
                bufferText += payload.content || "";
                if (/[。！？\.\!\?\:\n]/.test(payload.content)) {
                  addToQueue(bufferText);
                  bufferText = "";
                }
              }
            }
          } catch (e) { console.warn("Stream parse error:", e); }
        }
      }
    }
    if (isTTSRef.current && bufferText.trim()) addToQueue(bufferText);
  };

  const sendMessage = async (text: string) => {
    if (!text.trim() || !token) return;
    unlockAudio();
    stopAudio();
    setIsLoading(true);
    setShowStartInterviewBtn(false);

    addMessage({ role: "user", content: text });
    addMessage({ role: "assistant", content: "", thoughts: [], isThinkingFinished: false });

    try {
      const headers = { "Content-Type": "application/json", Authorization: `Bearer ${token}` };
      let url = "";
      let body: any = {};

      if (mode === 'rag') {
        url = `${API_BASE}/qa/qa`;
        body = { question: text };
      } else if (currentSessionId) {
        url = `${API_BASE}/chat/stream`;
        body = { session_id: currentSessionId, content: text };
      } else if (mode === 'guide') {
        url = `${API_BASE}/jd/generate-guide`;
        body = { jd_text: text };
      } else { // mock interview
        url = `${API_BASE}/interview/mock-interview/stream`;
        body = { jd_text: text };
      }

      const res = await fetch(url, { method: "POST", headers, body: JSON.stringify(body) });

      if (!res.ok) {
        if (res.status === 401) logout();
        throw new Error(`API Error: ${res.statusText}`);
      }

      await readStream(res);

    } catch (e) {
      const errorContent = e instanceof Error ? e.message : "An unknown error occurred.";
      updateLastMessage(msg => ({ ...msg, content: `❌ Error: ${errorContent}`, isThinkingFinished: true }));
    } finally {
      setIsLoading(false);
    }
  };

  return { sendMessage };
}

// Helper function (can be moved to a utils file)
const formatReportToMarkdown = (data: any) => {
    const { meta, tech_questions, company_analysis } = data;
    return `## 📊 ${meta.company_name || '岗位'} 分析\n\n**技术栈**: \`${meta.tech_stack.join('`, `')}\`\n\n${company_analysis ? `> 🏢 **公司**: ${company_analysis}\n\n` : ''}### 🛠️ 推荐技术题\n${tech_questions.map((q:any,i:number)=>`**Q${i+1}: ${q.question}**\n> ${q.reference_answer}`).join('\n\n')}`;
};
