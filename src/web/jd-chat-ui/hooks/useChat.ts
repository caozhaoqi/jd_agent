// hooks/useChat.ts
import { useRef, useEffect, useState } from "react";
import { useMessageStore } from "@/stores/useMessageStore";
import { useSessionStore } from "@/stores/useSessionStore";
import { useAudioQueue } from "@/hooks/useAudioQueue";
import { ChatMode } from "@/types/chat";
import { logger } from "@/utils/logger";

export const API_BASE = "http://localhost:8000/api/v1";

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

  // 跟踪上传的文件
  const [uploadedFiles, setUploadedFiles] = useState<Array<{name: string, id: string}>>([]);

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
    console.log("🌊 [Stream Reader] 开始读取流式响应", {
      sessionId: currentSessionId,
      responseStatus: res.status,
      responseHeaders: Object.fromEntries(res.headers.entries())
    });
    
    if (!res.body) {
      logger.error('stream', 'No response body received');
      setIsLoading(false);
      return;
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let bufferText = "";
    let reconnectAttempts = 0;
    const maxReconnectAttempts = 3;
    let hasReceivedData = false;
    let totalBytesReceived = 0;
    let chunksProcessed = 0;

    try {
      while (true) {
        try {
          const { value, done } = await reader.read();
          if (done) {
            console.log("🏁 [Stream Reader] 数据流结束", {
              totalChunks: chunksProcessed,
              totalBytes: totalBytesReceived,
              finalSessionId: currentSessionId
            });
            break;
          }

          // 统计信息
          chunksProcessed++;
          totalBytesReceived += value?.length || 0;
          
          console.log("📦 [Stream Reader] 接收数据块", {
            chunkNumber: chunksProcessed,
            chunkSize: value?.length || 0,
            totalBytes: totalBytesReceived,
            timestamp: new Date().toISOString()
          });

          // 【核心修复】只要有数据流到达，立即关闭全局 Loading 状态
          if (!hasReceivedData) {
            logger.debug('stream', '第一个数据块到达，关闭全局加载器');
            setIsLoading(false);
            hasReceivedData = true;
          }

          const chunk = decoder.decode(value, { stream: true });
          console.log("🔤 [Stream Reader] 解码数据块", {
            chunkLength: chunk.length,
            hasNewlines: chunk.includes('\n'),
            preview: chunk.substring(0, 100)
          });
          
          const lines = chunk.split("\n\n");
          console.log("📋 [Stream Reader] 分割后的行数:", lines.length);

          for (const line of lines) {
            if (line.startsWith("data: ")) {
              const dataStr = line.replace("data: ", "").trim();
              console.log("📄 [Stream Reader] 解析数据行", {
                lineLength: line.length,
                dataStrLength: dataStr.length,
                dataStrPreview: dataStr ? dataStr.substring(0, 200) : 'empty_or_null',
                isDoneSignal: dataStr === "[DONE]",
                isJson: dataStr ? dataStr.startsWith('{') : false
              });

              // 处理RAG结束信号
              if (dataStr === "[DONE]" || dataStr === '{"type": "end"}') {
                logger.debug('stream', '收到结束信号');
                updateLastMessage(msg => ({ ...msg, isThinkingFinished: true }));
                return;
              }
              
              // 跳过空数据行
              if (!dataStr) {
                logger.debug('stream', '跳过空数据行');
                continue;
              }

              try {
                const payload = JSON.parse(dataStr);
                logger.debug('stream', `解析JSON载荷: ${payload.type}`);

                // 1. 处理结构化监控数据
                if (payload.type === 'data') {
                  logger.debug('stream', `接收监控数据: ${payload.key}`);
                  onDashboardUpdate(payload.key, payload.value);
                }

                // 2. 处理思考内容 (DeepSeek 风格)
                else if (payload.type === 'thought') {
                  logger.debug('stream', `思考内容: ${payload.content?.length || 0} chars`);
                  
                  updateLastMessage(msg => {
                    const updatedMsg = {
                      ...msg,
                      isLoading: false,
                      thoughts: [...(msg.thoughts || []), payload.content],
                      isThinkingFinished: false,
                    };
                    return updatedMsg;
                  });
                }

                // 3. 处理报告/结果数据
                else if (payload.type === 'result') {
                  console.log("📊 [Result Data] 接收报告/结果数据", {
                    hasContent: !!payload.content,
                    contentType: typeof payload.content,
                    sessionId: currentSessionId,
                    timestamp: new Date().toISOString()
                  });
                  
                  const reportData: ReportData = payload.content;
                  console.log("📈 [Result Data] 报告数据结构", {
                    hasMeta: !!reportData.meta,
                    hasTechQuestions: !!reportData.tech_questions,
                    techQuestionsCount: reportData.tech_questions?.length || 0,
                    hasCompanyAnalysis: !!reportData.company_analysis,
                    sessionIdFromMeta: reportData.meta?.session_id
                  });
                  
                  updateLastMessage(msg => {
                    const formattedContent = formatReportToMarkdown(reportData);
                    console.log("📝 [Result Update] 更新消息为报告内容", {
                      originalContentLength: msg.content?.length || 0,
                      newContentLength: formattedContent.length,
                      isJson: true,
                      willFinishThinking: true
                    });
                    
                    return {
                      ...msg,
                      content: formattedContent,
                      isJson: true,
                      isThinkingFinished: true,
                    };
                  });

                  if (reportData.meta?.session_id) {
                    console.log("🔗 [Session Update] 更新会话ID", {
                      oldSessionId: currentSessionId,
                      newSessionId: reportData.meta.session_id,
                      willFetchSessions: true
                    });
                    setCurrentSessionId(reportData.meta.session_id);
                    fetchSessions();
                    if (onSessionCreated) onSessionCreated(reportData.meta.session_id);
                  }
                }

                // 4. 处理普通正文 Token
                else if (payload.type === 'token') {
                  const tokenContent = payload.content || "";
                  logger.debug('stream', `Token: ${tokenContent.length} chars`);
                  
                  updateLastMessage(msg => {
                    return {
                      ...msg,
                      content: (msg.content || "") + tokenContent,
                      isThinkingFinished: true
                    };
                  });

                  if (isTTSRef.current) {
                    bufferText += tokenContent;
                    const sentenceEndRegex = /[。！？\.\!\?\:\n]/;
                    const isSentenceEnd = sentenceEndRegex.test(tokenContent);
                    
                    if (isSentenceEnd) {
                      logger.debug('stream', `TTS添加到队列: ${bufferText.length} chars`);
                      addToQueue(bufferText);
                      bufferText = "";
                    }
                  }
                }

                // 5. 处理错误
                else if (payload.type === 'error') {
                  logger.error('stream', `后端错误: ${payload.content}`);
                  
                  updateLastMessage(msg => {
                    const errorMessage = `\n\n❌ 后端错误: ${payload.content}`;
                    return {
                      ...msg,
                      content: msg.content + errorMessage,
                      isThinkingFinished: true,
                    };
                  });
                  return;
                }

              } catch (parseError) {
                // 增强的JSON解析错误处理
                let safeDataStr = '';
                let isJSONFormat = false;
                let dataStrLength = 0;
                
                try {
                  safeDataStr = typeof dataStr === 'string' ? dataStr : String(dataStr);
                  isJSONFormat = safeDataStr.startsWith('{');
                  dataStrLength = safeDataStr.length;
                } catch (typeError) {
                  console.warn("⚠️ [Type Check Error] 类型检查失败:", typeError);
                  safeDataStr = '类型检查失败';
                }
                
                console.warn("⚠️ [JSON Parse Error] JSON解析错误", {
                  errorMessage: parseError instanceof Error ? parseError.message : 'Unknown error',
                  rawData: safeDataStr.substring(0, 200),
                  dataStrLength: dataStrLength,
                  startsWithBrace: isJSONFormat,
                  sessionId: currentSessionId
                });
                
                // 安全处理错误消息，避免包含undefined导致的问题
                const errorMsg = parseError instanceof Error ? parseError.message : 'Unknown error';
                const safeErrorMsg = errorMsg ? errorMsg.replace(/undefined/g, '未定义') : '未知错误';
                logger.error('stream', `JSON解析失败: ${safeErrorMsg}`);
                
                // 如果 JSON 解析失败，尝试作为普通文本处理
                if (safeDataStr && !safeDataStr.startsWith("{")) {
                  console.log("📝 [Fallback] 作为普通文本处理", {
                    fallbackText: safeDataStr.substring(0, 100),
                    willAppendToContent: true
                  });
                  
                  updateLastMessage(msg => {
                    const newContent = msg.content + safeDataStr;
                    console.log("📝 [Fallback Update] 更新消息内容", {
                      oldContentLength: msg.content?.length || 0,
                      newContentLength: newContent.length,
                      addedText: safeDataStr.substring(0, 50)
                    });
                    
                    return {
                      ...msg,
                      content: newContent
                    };
                  });
                } else {
                  // 超级安全的错误日志处理
                  try {
                    // 先进行最基本的安全检查
                    let safeDataStr = 'unknown';
                    let safeType = typeof dataStr;
                    
                    try {
                      if (typeof dataStr === 'string') {
                        safeDataStr = dataStr.substring(0, 100);
                      } else if (dataStr === null) {
                        safeDataStr = 'null';
                      } else if (dataStr === undefined) {
                        safeDataStr = 'undefined';
                      } else if (typeof dataStr === 'object' && dataStr !== null) {
                        const objectName = (dataStr as any).constructor?.name || 'Object';
                        safeDataStr = '[object ' + objectName + ']';
                      } else {
                        safeDataStr = String(dataStr);
                      }
                    } catch (strError) {
                      safeDataStr = '[string conversion failed]';
                    }
                    
                    // 构建安全的日志对象
                    const logData = {
                      dataStrPreview: safeDataStr,
                      isJSONFormat: typeof dataStr === 'string' ? dataStr.startsWith('{') : false,
                      dataStrLength: typeof dataStr === 'string' ? dataStr.length : 0,
                      dataStrType: safeType,
                      isEmptyString: dataStr === '',
                      isEmptyObject: safeDataStr === '[object Object]'
                    };
                    
                    console.error("🚨 [JSON Parse Error] 无法解析的数据格式", logData);
                  } catch (logError) {
                    // 最基本的错误日志，防止任何错误
                    try {
                      console.error("🚨 [JSON Parse Error] 数据解析失败");
                    } catch (basicError) {
                      // 如果连基本日志都失败，就什么都不做
                    }
                  }
                }
              }
            }
          }
        } catch (readError) {

          reconnectAttempts++;
          console.error(`❌ [Stream Read Error] 流读取错误`, {
            attemptNumber: reconnectAttempts,
            maxAttempts: maxReconnectAttempts,
            errorMessage: readError instanceof Error ? readError.message : 'Unknown error',
            errorStack: readError instanceof Error ? readError.stack : undefined,
            sessionId: currentSessionId,
            chunksProcessedSoFar: chunksProcessed,
            totalBytesSoFar: totalBytesReceived
          });
          
          logger.error('stream', `[Stream Error] 流读取错误 (第${reconnectAttempts}次尝试): ${readError instanceof Error ? readError.message : 'Unknown error'}`, { sessionId: currentSessionId?.toString() });
          
          if (reconnectAttempts >= maxReconnectAttempts) {
            console.error("💥 [Stream Failure] 流式传输彻底失败", {
              totalAttempts: reconnectAttempts,
              totalChunksProcessed: chunksProcessed,
              totalBytesReceived,
              finalSessionId: currentSessionId
            });
            throw new Error(`流式传输失败，已重试 ${maxReconnectAttempts} 次`);
          }
          
          // 计算延迟时间（指数退避）
          const delayMs = 1000 * reconnectAttempts;
          console.log("⏳ [Stream Retry] 准备重试", {
            attemptNumber: reconnectAttempts + 1,
            delayMs,
            willRetry: true
          });
          
          // 短暂延迟后重试
          await new Promise(resolve => setTimeout(resolve, delayMs));
        }
      }
    } catch (exception) {
      console.error("❌ [Stream Processing] 流处理失败", {
        errorMessage: exception instanceof Error ? exception.message : 'Unknown error',
        errorType: typeof exception,
        errorStack: exception instanceof Error ? exception.stack : undefined,
        sessionId: currentSessionId,
        chunksProcessed: chunksProcessed,
        totalBytesReceived,
        timestamp: new Date().toISOString()
      });
      
      const errorMessage = exception instanceof Error ? exception.message : "未知错误";
      logger.error('stream', `流处理失败: ${errorMessage}`);
      
      updateLastMessage(msg => {
        const errorText = `\n\n❌ 流式传输中断: ${errorMessage}`;
        console.log("🚨 [Stream Error Update] 更新错误消息", {
          originalContentLength: msg.content?.length || 0,
          errorMessage: errorMessage,
          willAddErrorText: true,
          willFinishThinking: true
        });
        
        return {
          ...msg,
          content: msg.content + errorText,
          isThinkingFinished: true,
        };
      });
    } finally {
      console.log("🏁 [Stream Processing] 流处理完成", {
        finalChunksProcessed: chunksProcessed,
        finalBytesReceived: totalBytesReceived,
        finalSessionId: currentSessionId,
        hasRemainingBuffer: !!bufferText.trim(),
        timestamp: new Date().toISOString()
      });
      
      setIsLoading(false);
      
      if (isTTSRef.current && bufferText.trim()) {
        console.log("🔊 [Final TTS] 处理剩余TTS缓冲区", {
          remainingText: bufferText.substring(0, 100),
          textLength: bufferText.length
        });
        addToQueue(bufferText);
      }
    }
  };

  const sendMessage = async (text: string) => {
    if (!text.trim() || isLoading || !token) return;

    unlockAudio();
    stopAudio();
    setIsLoading(true); // 开启初始加载动画

    // 构建消息内容，包含上传的文件信息
    let messageContent = text;
    if (uploadedFiles.length > 0) {
      const filesList = uploadedFiles.map(file => `- ${file.name}`).join('\n');
      messageContent = `[文件列表]\n${filesList}\n\n[问题]\n${text}`;
      // 发送消息后清空上传文件列表
      setUploadedFiles([]);
    }

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
      console.log("🚀 [Frontend] Sending request:", { mode, currentSessionId });
      if (mode === 'rag') {
        url = `${API_BASE}/qa/qa/stream`;  // 使用流式RAG端点
        body = { question: messageContent };
        console.log("🚀 [Frontend] Using RAG stream endpoint:", url);
      } else if (currentSessionId) {
        url = `${API_BASE}/chat/stream`;
        body = { session_id: currentSessionId, content: messageContent };
        console.log("🚀 [Frontend] Using chat stream endpoint:", url);
      } else if (mode === 'guide') {
        url = `${API_BASE}/jd/generate-guide`;
        body = { jd_text: messageContent };
        console.log("🚀 [Frontend] Using JD guide endpoint:", url);
      } else {
        url = `${API_BASE}/interview/mock-interview/stream`;
        body = { jd_text: messageContent };
        console.log("🚀 [Frontend] Using interview stream endpoint:", url);
      }

      console.log("🚀 [Frontend] Final request details:", {
        url,
        body,
        headers: Object.keys(headers),
        timestamp: Date.now()
      });

      const res = await fetch(url, {
        method: "POST",
        headers,
        body: JSON.stringify(body)
      });

      console.log("🚀 [Frontend] Response received:", {
        status: res.status,
        statusText: res.statusText,
        ok: res.ok,
        headers: Object.fromEntries(res.headers.entries())
      });

      if (!res.ok) {
        if (res.status === 401) onLogout();
        console.error("❌ [Frontend] API Error:", res.statusText, res.status);
        throw new Error(`API Error: ${res.statusText} (${res.status})`);
      }

      // 请求只要 res.ok，其实已经可以关闭全局 Loader 了，
      // 因为接下来的 readStream 会处理具体的思考 UI。
      // 但为了平滑，我们在 readStream 的第一个块处关闭。
      console.log("🚀 [Frontend] Starting to read stream...");
      await readStream(res);
      console.log("🚀 [Frontend] Stream reading completed");

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

  const uploadFile = async (file: File) => {
    if (!token) return;

    try {
      setIsLoading(true);
      
      const formData = new FormData();
      formData.append('file', file);

      const res = await fetch(`${API_BASE}/resume/upload`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        },
        body: formData
      });

      if (!res.ok) {
        if (res.status === 401) onLogout();
        
        // 尝试解析错误响应
        try {
          const errorData = await res.json();
          throw new Error(`文件处理失败: ${errorData.message || res.statusText}`);
        } catch {
          throw new Error(`文件上传失败: ${res.statusText}`);
        }
      }

      const data = await res.json();
      console.log('文件上传成功:', data);
      
      // 生成唯一文件ID并添加到上传文件列表
      const fileId = `file_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      setUploadedFiles(prev => [...prev, { name: file.name, id: fileId }]);
      
      // 添加成功消息到聊天界面
      addMessage({ 
        role: "assistant", 
        content: `📁 文件上传成功: ${file.name}\n\n${data.msg}${data.new_entries ? `，新增 ${data.new_entries} 条记录` : ''}\n\n提示: 现在你可以针对这个文件提问，我会基于文件内容给你解答。` 
      });

    } catch (e) {
      const errorMessage = e instanceof Error ? e.message : "文件上传失败";
      console.error('文件上传错误:', errorMessage);
      
      // 分析错误类型并给出更友好的提示
      let friendlyMessage = `❌ 文件上传失败: ${errorMessage}`;
      
      if (errorMessage.includes('文件内容为空或无法识别')) {
        friendlyMessage = `⚠️ 文件上传成功，但解析失败: ${file.name}\n\n原因: 文件内容为空或无法识别\n\n建议: 请尝试上传包含实际内容的文件，或检查文件格式是否正确。支持的格式包括：PDF、DOCX、TXT等。`;
      } else if (errorMessage.includes('不支持的文件格式')) {
        friendlyMessage = `⚠️ 文件格式不支持: ${file.name}\n\n原因: ${errorMessage}\n\n建议: 请上传支持的文件格式，包括：PDF、DOCX、TXT、JPG、PNG等。`;
      }
      
      // 添加错误消息到聊天界面
      addMessage({ 
        role: "assistant", 
        content: friendlyMessage 
      });
    } finally {
      setIsLoading(false);
    }
  };

  return { sendMessage, uploadFile, uploadedFiles };
}