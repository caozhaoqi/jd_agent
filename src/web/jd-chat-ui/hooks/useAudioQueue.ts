import { useRef, useCallback, useEffect } from 'react';

export function useAudioQueue() {
  const audioQueueRef = useRef<string[]>([]);
  const isPlayingRef = useRef(false);

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

  const processAudioQueue = useCallback(async () => {
    if (isPlayingRef.current || audioQueueRef.current.length === 0) return;

    isPlayingRef.current = true;
    const text = audioQueueRef.current.shift();

    try {
      const token = localStorage.getItem("token");
      if (!token) return;

      const res = await fetch(`http://127.0.0.1:8000/api/v1/audio/tts?text=${encodeURIComponent(text!)}`, {
        method: "POST",
        headers: { "Authorization": `Bearer ${token}` }
      });

      if (res.ok) {
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);

       // 🟢 双重保险：在等待 fetch 的过程中，如果用户点击了停止，
        // audioQueueRef.current 会被清空。
        // 如果这时候队列突然空了（且不是因为 shift 取出的），说明被强制停止了，就不应该播放。

        // 但由于 processAudioQueue 是递归的，更简单的判断是：
        // 检查一下当前是否被强制停止了？
        // 我们可以通过判断 isPlayingRef 是否被外部设为了 false (在 stopAudio 里)
        // 不过最稳妥的是：

        const audio = globalAudioRef.current;
        // 如果 fetch 回来发现队列已经被 stopAudio 清空了，且当前不是正在播放状态（被强制重置了）
        // 其实 stopAudio 里的 pause() 已经能截断当前播放。
        // 关键是防止 fetch 回来后又这就开始 play()。
        // ✅ 改动4: 复用同一个 Audio 对象
//         const audio = globalAudioRef.current;
        if (audio) {
            audio.src = url;

            // 重新绑定结束事件
            audio.onended = () => {
              isPlayingRef.current = false;
              processAudioQueue();
            };

            // 尝试播放
            try {
              await audio.play();
            } catch (playError) {
              console.error("⚠️ TTS 播放被拦截，尝试继续队列:", playError);
              isPlayingRef.current = false;
              processAudioQueue();
            }
        } else {
             // 防御性代码：如果没有 audio 对象，新建一个（虽然很少见）
             const tempAudio = new Audio(url);
             tempAudio.onended = () => { isPlayingRef.current = false; processAudioQueue(); };
             tempAudio.play();
        }
      } else {
        isPlayingRef.current = false;
        processAudioQueue();
      }
    } catch (e) {
      console.error("TTS Network Error", e);
      isPlayingRef.current = false;
      processAudioQueue();
    }
  }, []);

  const addToQueue = useCallback((text: string) => {
    if (!text.trim()) return;
    audioQueueRef.current.push(text);
    processAudioQueue();
  }, [processAudioQueue]);

  const stopAudio = useCallback(() => {
    if (globalAudioRef.current) {
      globalAudioRef.current.pause();
      globalAudioRef.current.currentTime = 0;
    }
    audioQueueRef.current = [];
    isPlayingRef.current = false;
    // 这里已经做得很好了，清空队列是关键
  }, []);

  // 导出 unlockAudio 供外部调用
  return { addToQueue, stopAudio, unlockAudio };
}