import { useRef, useCallback } from 'react';

export function useAudioQueue() {
  const audioQueueRef = useRef<string[]>([]);
  const isPlayingRef = useRef(false);
  const currentAudioRef = useRef<HTMLAudioElement | null>(null);

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
        const audio = new Audio(url);
        currentAudioRef.current = audio;

        audio.onended = () => {
          isPlayingRef.current = false;
          processAudioQueue();
        };

        await audio.play();
      } else {
        isPlayingRef.current = false;
        processAudioQueue();
      }
    } catch (e) {
      console.error("TTS Play Error", e);
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
    if (currentAudioRef.current) {
      currentAudioRef.current.pause();
      currentAudioRef.current = null;
    }
    audioQueueRef.current = [];
    isPlayingRef.current = false;
  }, []);

  return { addToQueue, stopAudio };
}