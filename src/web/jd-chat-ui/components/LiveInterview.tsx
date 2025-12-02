"use client";

import { LiveKitRoom, RoomAudioRenderer, BarVisualizer, useVoiceAssistant } from "@livekit/components-react";
import "@livekit/components-styles";
import { useState, useEffect } from "react";

export default function LiveInterview() {
  const [token, setToken] = useState("");
  const [url, setUrl] = useState("");

  useEffect(() => {
    // 获取 Token
    (async () => {
      const res = await fetch("/api/v1/webrtc/token", {
          headers: { Authorization: `Bearer ${localStorage.getItem("token")}` }
      });
      const data = await res.json();
      setToken(data.token);
      setUrl(data.url);
    })();
  }, []);

  if (!token) return <div>Loading Audio Room...</div>;

  return (
    <LiveKitRoom
      video={false}
      audio={true}
      token={token}
      serverUrl={url}
      data-lk-theme="default"
      connect={true}
      className="h-64 w-full flex flex-col items-center justify-center bg-gray-900 rounded-xl text-white"
    >
      {/* 音频可视化条 */}
      <div className="h-32 flex items-center">
          <BarVisualizer state="expanded" barCount={7} trackRef={...} />
      </div>

      {/* 状态显示 */}
      <AgentStatus />

      {/* 核心：播放远端音频 */}
      <RoomAudioRenderer />
    </LiveKitRoom>
  );
}

function AgentStatus() {
    const { state, audioTrack } = useVoiceAssistant();
    return (
        <div className="mt-4 text-sm text-gray-400">
            {state === 'listening' && <span className="text-green-400">🎤 正在听你说话... (可随时打断)</span>}
            {state === 'thinking' && <span className="text-blue-400">🧠 思考中...</span>}
            {state === 'speaking' && <span className="text-purple-400">🔊 面试官正在提问...</span>}
        </div>
    )
}