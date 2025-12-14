import { useRef, useCallback, useEffect, useState } from 'react';
import { API_BASE } from "@/hooks/useChat";

interface AudioQueueStatus {
  isPlaying: boolean;
  queueLength: number;
  isLoading: boolean;
  error: string | null;
}

export function useAudioQueue() {
  const audioQueueRef = useRef<string[]>([]);
  const isPlayingRef = useRef(false);
  const isLoadingRef = useRef(false);
  
  // 状态管理
  const [queueStatus, setQueueStatus] = useState<AudioQueueStatus>({
    isPlaying: false,
    queueLength: 0,
    isLoading: false,
    error: null
  });

  // ✅ 改动1: 全局单例 Audio 对象
  const globalAudioRef = useRef<HTMLAudioElement | null>(null);

  // ✅ 改动2: 初始化 Audio 对象 (仅客户端)
  useEffect(() => {
    if (typeof window !== 'undefined') {
      globalAudioRef.current = new Audio();
    }
  }, []);

  // ✅ 改动3: 暴露给外部的“预热”函数
  // 必须在 handleSend (点击事件) 中调用
  const unlockAudio = useCallback(() => {
    const audio = globalAudioRef.current;
    if (audio) {
      // 播放一个极短的静音 Base64，骗取浏览器信任
      // 这是一个 0.1秒的静音 WAV 文件
      audio.src = 'data:audio/wav;base64,UklGRigAAABXQVZFZm10IBIAAAABAAEAQB8AAEAfAAABAAgAAABmYWN0BAAAAAAAAABkYXRhAAAAAA==';
      audio.play().catch(e => {
          // 忽略预热失败，这很正常
          console.log("Audio warmup silent fail (expected)", e);
      });
    }
  }, []);

  // ✅ 优化1: 更新队列状态的辅助函数
  const updateQueueStatus = useCallback(() => {
    setQueueStatus({
      isPlaying: isPlayingRef.current,
      queueLength: audioQueueRef.current.length,
      isLoading: isLoadingRef.current,
      error: null
    });
  }, []);

  const processAudioQueue = useCallback(async () => {
    if (isPlayingRef.current || audioQueueRef.current.length === 0) return;

    isPlayingRef.current = true;
    isLoadingRef.current = true;
    const text = audioQueueRef.current.shift();
    
    // 更新状态
    updateQueueStatus();

    try {
      const token = localStorage.getItem("token");
      if (!token) {
        throw new Error("缺少认证令牌");
      }

      const res = await fetch(`${API_BASE}/audio/tts`, {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${token}`,
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ text: text! })
      });

      if (res.ok) {
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);

        const audio = globalAudioRef.current;
        if (audio) {
            audio.src = url;

            // 重新绑定结束事件
            audio.onended = () => {
              // 清理资源
              URL.revokeObjectURL(audio.src);
              isPlayingRef.current = false;
              isLoadingRef.current = false;
              updateQueueStatus();
              processAudioQueue();
            };

            // 尝试播放
            try {
              await audio.play();
              isLoadingRef.current = false;
              updateQueueStatus();
            } catch (playError) {
              console.error("⚠️ TTS 播放被拦截，尝试继续队列:", playError);
              // 播放失败时也清理资源
              URL.revokeObjectURL(url);
              isPlayingRef.current = false;
              isLoadingRef.current = false;
              setQueueStatus(prev => ({
                ...prev,
                error: "音频播放失败，可能被浏览器拦截",
                isPlaying: false,
                isLoading: false
              }));
              processAudioQueue();
            }
        } else {
             // 防御性代码：如果没有 audio 对象，新建一个（虽然很少见）
             const tempAudio = new Audio(url);
             tempAudio.onended = () => {
               // 清理资源
               URL.revokeObjectURL(tempAudio.src);
               isPlayingRef.current = false;
               isLoadingRef.current = false;
               updateQueueStatus();
               processAudioQueue();
             };
             tempAudio.onerror = () => {
               // 播放错误时清理资源
               URL.revokeObjectURL(url);
               isLoadingRef.current = false;
               setQueueStatus(prev => ({
                 ...prev,
                 error: "音频播放失败",
                 isPlaying: false,
                 isLoading: false
               }));
             };
             tempAudio.play();
             isLoadingRef.current = false;
             updateQueueStatus();
        }
      } else {
        const errorText = await res.text();
        throw new Error(errorText || `TTS服务错误: ${res.status}`);
      }
    } catch (e) {
      console.error("TTS Network Error", e);
      isPlayingRef.current = false;
      isLoadingRef.current = false;
      setQueueStatus(prev => ({
        ...prev,
        error: e instanceof Error ? e.message : "音频生成失败",
        isPlaying: false,
        isLoading: false
      }));
      processAudioQueue();
    }
  }, [updateQueueStatus]);

  const addToQueue = useCallback((text: string) => {
    if (!text.trim()) return;
    audioQueueRef.current.push(text);
    updateQueueStatus();
    processAudioQueue();
  }, [processAudioQueue, updateQueueStatus]);

  const stopAudio = useCallback(() => {
    if (globalAudioRef.current) {
      globalAudioRef.current.pause();
      globalAudioRef.current.currentTime = 0;
    }
    audioQueueRef.current = [];
    isPlayingRef.current = false;
    isLoadingRef.current = false;
    updateQueueStatus();
  }, [updateQueueStatus]);

  // ✅ 优化2: 暂停/继续功能
  const togglePause = useCallback(() => {
    const audio = globalAudioRef.current;
    if (!audio) return;
    
    if (isPlayingRef.current) {
      audio.pause();
      isPlayingRef.current = false;
    } else {
      audio.play().catch(e => {
        console.error("恢复播放失败:", e);
        setQueueStatus(prev => ({
          ...prev,
          error: "恢复播放失败"
        }));
      });
      isPlayingRef.current = true;
    }
    updateQueueStatus();
  }, [updateQueueStatus]);

  // ✅ 优化3: 清除错误信息
  const clearError = useCallback(() => {
    setQueueStatus(prev => ({
      ...prev,
      error: null
    }));
  }, []);

  // ✅ 优化4: 获取当前播放状态
  const getCurrentStatus = useCallback(() => {
    return {
      isPlaying: isPlayingRef.current,
      queueLength: audioQueueRef.current.length,
      isLoading: isLoadingRef.current
    };
  }, []);

  // 导出 unlockAudio 供外部调用
  return {
    addToQueue,
    stopAudio,
    unlockAudio,
    togglePause,
    clearError,
    getCurrentStatus,
    queueStatus
  };
}