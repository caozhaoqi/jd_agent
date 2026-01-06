"use client";

import { 
  LiveKitRoom, 
  BarVisualizer, 
  useVoiceAssistant,
  GridLayout,
  ParticipantTile,
  useTracks,
  ControlBar
} from "@livekit/components-react";
import "@livekit/components-styles";
import { useState, useEffect } from "react";
import { Track } from "livekit-client";
import { Mic, MicOff, Video, VideoOff, Monitor, MonitorOff, PhoneOff } from "lucide-react";

interface VideoInterviewProps {
  className?: string;
}

export default function LiveInterview({ className = "" }: VideoInterviewProps) {
  const [token, setToken] = useState("");
  const [url, setUrl] = useState("");
  const [isVideoEnabled, setIsVideoEnabled] = useState(true);
  const [isAudioEnabled, setIsAudioEnabled] = useState(true);
  const [isScreenSharing, setIsScreenSharing] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState("connecting");

  useEffect(() => {
    (async () => {
      try {
        const res = await fetch("/api/v1/webrtc/token", {
          headers: { Authorization: `Bearer ${localStorage.getItem("token")}` }
        });
        const data = await res.json();
        setToken(data.token);
        setUrl(data.url);
        setConnectionStatus("connected");
      } catch (error) {
        console.error("Failed to get token:", error);
        setConnectionStatus("error");
      }
    })();
  }, []);

  if (!token) {
    return (
      <div className={`h-96 w-full flex items-center justify-center bg-gray-900 rounded-xl text-white ${className}`}>
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-white mx-auto mb-4"></div>
          <p>正在连接视频面试...</p>
        </div>
      </div>
    );
  }

  return (
    <LiveKitRoom
      video={isVideoEnabled}
      audio={isAudioEnabled}
      token={token}
      serverUrl={url}
      data-lk-theme="default"
      connect={true}
      className={`h-96 w-full flex flex-col bg-gray-900 rounded-xl text-white ${className}`}
    >
      <div className="flex-1 relative">
        <VideoGridLayout />
      </div>

      <div className="h-16 flex items-center justify-center">
        <BarVisualizer barCount={7} />
      </div>

      <AgentStatus />

      <VideoInterviewControls
        isVideoEnabled={isVideoEnabled}
        isAudioEnabled={isAudioEnabled}
        isScreenSharing={isScreenSharing}
        onToggleVideo={() => setIsVideoEnabled(!isVideoEnabled)}
        onToggleAudio={() => setIsAudioEnabled(!isAudioEnabled)}
        onToggleScreenShare={() => setIsScreenSharing(!isScreenSharing)}
        onLeave={() => window.location.reload()}
      />
    </LiveKitRoom>
  );
}

function VideoGridLayout() {
  const tracks = useTracks([
    Track.Source.Camera, 
    Track.Source.Microphone,
    Track.Source.ScreenShare
  ]);
  
  return (
    <GridLayout
      tracks={tracks}
      className="h-full w-full"
      style={{
        height: "calc(100% - 60px)",
      }}
    >
      <ParticipantTile className="h-full w-full" />
    </GridLayout>
  );
}

function AgentStatus() {
  const { state } = useVoiceAssistant();
  
  return (
    <div className="py-2 text-center text-sm text-gray-400">
      {state === 'listening' && (
        <span className="text-green-400 flex items-center justify-center gap-2">
          <span className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></span>
          正在听你说话... (可随时打断)
        </span>
      )}
      {state === 'thinking' && (
        <span className="text-blue-400 flex items-center justify-center gap-2">
          <span className="w-2 h-2 bg-blue-400 rounded-full animate-pulse"></span>
          AI面试官思考中...
        </span>
      )}
      {state === 'speaking' && (
        <span className="text-purple-400 flex items-center justify-center gap-2">
          <span className="w-2 h-2 bg-purple-400 rounded-full animate-pulse"></span>
          AI面试官正在提问...
        </span>
      )}
    </div>
  );
}

interface VideoInterviewControlsProps {
  isVideoEnabled: boolean;
  isAudioEnabled: boolean;
  isScreenSharing: boolean;
  onToggleVideo: () => void;
  onToggleAudio: () => void;
  onToggleScreenShare: () => void;
  onLeave: () => void;
}

function VideoInterviewControls({
  isVideoEnabled,
  isAudioEnabled,
  isScreenSharing,
  onToggleVideo,
  onToggleAudio,
  onToggleScreenShare,
  onLeave,
}: VideoInterviewControlsProps) {
  return (
    <div className="bg-gray-800 px-6 py-3 flex items-center justify-between">
      <div className="flex items-center gap-4">
        <button
          onClick={onToggleVideo}
          className={`p-2 rounded-full transition-colors ${
            isVideoEnabled 
              ? 'bg-gray-600 hover:bg-gray-500' 
              : 'bg-red-600 hover:bg-red-500'
          }`}
          title={isVideoEnabled ? "关闭摄像头" : "开启摄像头"}
        >
          {isVideoEnabled ? (
            <Video className="w-5 h-5" />
          ) : (
            <VideoOff className="w-5 h-5" />
          )}
        </button>

        <button
          onClick={onToggleAudio}
          className={`p-2 rounded-full transition-colors ${
            isAudioEnabled 
              ? 'bg-gray-600 hover:bg-gray-500' 
              : 'bg-red-600 hover:bg-red-500'
          }`}
          title={isAudioEnabled ? "关闭麦克风" : "开启麦克风"}
        >
          {isAudioEnabled ? (
            <Mic className="w-5 h-5" />
          ) : (
            <MicOff className="w-5 h-5" />
          )}
        </button>

        <button
          onClick={onToggleScreenShare}
          className={`p-2 rounded-full transition-colors ${
            isScreenSharing 
              ? 'bg-blue-600 hover:bg-blue-500' 
              : 'bg-gray-600 hover:bg-gray-500'
          }`}
          title={isScreenSharing ? "停止屏幕共享" : "开始屏幕共享"}
        >
          {isScreenSharing ? (
            <MonitorOff className="w-5 h-5" />
          ) : (
            <Monitor className="w-5 h-5" />
          )}
        </button>
      </div>

      <button
        onClick={onLeave}
        className="p-2 rounded-full bg-red-600 hover:bg-red-500 transition-colors"
        title="结束面试"
      >
        <PhoneOff className="w-5 h-5" />
      </button>
    </div>
  );
}
