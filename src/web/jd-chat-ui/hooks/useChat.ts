// hooks/useChat.ts
import { useState, useRef, useEffect } from "react";
import { Message, ChatMode } from "@/types/chat";
import { useAudioQueue } from "@/hooks/useAudioQueue";

// 定义后端 API 基础路径，使用相对路径通过Next.js代理转发
export const API_BASE = "/api/v1";

interface UseChatProps {
  token: string | null;
  mode: ChatMode | 'rag';
  currentSessionId: number | null;
  isTTSEnabled: boolean;
  onDashboardUpdate: (key: string, value: any) => void;
  onSessionCreated: (id: number) => void;
}

export function useChat({ token, mode, currentSessionId, isTTSEnabled, onDashboardUpdate, onSessionCreated }: UseChatProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [showStartInterviewBtn, setShowStartInterviewBtn] = useState(false);

  const { addToQueue, stopAudio, unlockAudio } = useAudioQueue();
  const isTTSRef = useRef(isTTSEnabled);

  // 同步 TTS 开关引用
  useEffect(() => {
    isTTSRef.current = isTTSEnabled;
    if (!isTTSEnabled) stopAudio();
  }, [isTTSEnabled, stopAudio]);

  // --- 辅助函数：格式化 Markdown ---
  const formatReportToMarkdown = (data: any) => {
      const { meta, tech_questions, hr_questions, company_analysis } = data;
      return `## 📊 ${meta.company_name || '岗位'} 分析\n\n**技术栈**: \`${meta.tech_stack.join('`, `')}\`\n\n${company_analysis ? `> 🏢 **公司**: ${company_analysis}\n\n` : ''}### 🛠️ 推荐技术题\n${tech_questions.map((q:any,i:number)=>`**Q${i+1}: ${q.question}**\n> ${q.reference_answer}`).join('\n\n')}`;
  };

  const formatRAGResponse = (data: { answer: string; sources: string[] }) => {
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
                      if (dataStr === "[DONE]") break;
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
                                  }
                                  else if (payload.type === 'result') {
                                      const reportData = JSON.parse(payload.content);
                                      lastMsg.content = formatReportToMarkdown(reportData);
                                      lastMsg.isJson = true;
                                      if (reportData.session_id) onSessionCreated(reportData.session_id);
                                  }
                                  else if (payload.type === 'token') {
                                      lastMsg.content += (payload.content || "");
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
      } catch (err) { console.error("Stream failed:", err); } finally {
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
            setMessages(prev => [...prev, { role: "assistant", content: "🔍 正在检索知识库..." }]);

            // 注意：这里使用了新的 API 路径结构，请确保后端 api_v1.py 配置正确
            // 如果后端前缀是 /qa，则路径为 /qa/knowledge-base
            const res = await fetch(`${API_BASE}/qa/qa`, {
                method: "POST",
                headers,
                body: JSON.stringify({ question: text })
            });

            if (!res.ok) throw new Error(await res.text());
            const data = await res.json();

            const formatted = formatRAGResponse(data);
            setMessages(prev => {
                const newMsgs = [...prev];
                newMsgs[newMsgs.length - 1] = { role: "assistant", content: formatted, isJson: true };
                return newMsgs;
            });
            if (isTTSEnabled) addToQueue(data.answer);
        }
        // 🔵 场景 B: 连续对话
        else if (currentSessionId) {
            setMessages(prev => [...prev, { role: "assistant", content: "" }]);
            const res = await fetch(`${API_BASE}/chat/stream`, {
                method: "POST", headers, body: JSON.stringify({ session_id: currentSessionId, content: text })
            });
            await readStream(res);
        }
        // 🟡 场景 C: JD 指南生成
        else if (mode === 'guide') {
            setMessages(prev => [...prev, { role: "assistant", content: "" }]);
            const res = await fetch(`${API_BASE}/interview/guide/stream`, {
                method: "POST", headers, body: JSON.stringify({ jd_text: text })
            });
            await readStream(res);
        }
        // 🟣 场景 D: 模拟面试
        else {
            setMessages(prev => [...prev, { role: "assistant", content: "" }]);
            const res = await fetch(`${API_BASE}/interview/mock-interview/stream`, {
                method: "POST", headers, body: JSON.stringify({ jd_text: text })
            });
            await readStream(res);
        }

    } catch (e: any) {
        console.error(e);
        setMessages(prev => {
            const lastMsg = prev[prev.length - 1];
            if (lastMsg?.role === "assistant") {
                const newMsgs = [...prev];
                newMsgs[newMsgs.length - 1] = { role: "assistant", content: `❌ 请求失败: ${e.message || "网络错误"}` };
                return newMsgs;
            }
            return [...prev, { role: "assistant", content: "❌ 请求失败。" }];
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