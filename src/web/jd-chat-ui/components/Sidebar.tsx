import { Plus, MessageSquare, LogOut, LayoutDashboard, Mic } from "lucide-react";
import clsx from "clsx";
import { Session, ChatMode } from "@/types/chat";

interface SidebarProps {
  username: string;
  sessions: Session[];
  currentSessionId: number | null;
  mode: ChatMode;
  setMode: (mode: ChatMode) => void;
  onNewChat: () => void;
  onLoadSession: (id: number) => void;
  onLogout: () => void;
}

export default function Sidebar({
  username, sessions, currentSessionId, mode, setMode,
  onNewChat, onLoadSession, onLogout
}: SidebarProps) {
  return (
    <div className="w-[260px] bg-[#fcfdfd] border-r border-gray-200 hidden md:flex flex-col flex-shrink-0">
      <div className="p-4 space-y-2">
        {/* 模式切换 */}
        <div className="bg-gray-100 p-1 rounded-lg flex text-sm mb-4">
          <button
            onClick={() => setMode('guide')}
            className={clsx("flex-1 py-1.5 rounded-md transition-all flex justify-center gap-2", mode === 'guide' ? "bg-white shadow text-blue-600 font-bold" : "text-gray-500")}
          >
            <LayoutDashboard size={14} /> JD 分析
          </button>
          <button
            onClick={() => setMode('mock')}
            className={clsx("flex-1 py-1.5 rounded-md transition-all flex justify-center gap-2", mode === 'mock' ? "bg-white shadow text-purple-600 font-bold" : "text-gray-500")}
          >
            <Mic size={14} /> 模拟面试
          </button>
        </div>
        <button onClick={onNewChat} className="w-full py-2 bg-blue-50 text-blue-600 rounded-md text-sm font-medium border border-blue-100 flex justify-center items-center gap-2">
          <Plus size={16} /> 新建会话
        </button>
      </div>

      {/* 历史列表 */}
      <div className="flex-1 overflow-y-auto px-2 scrollbar-thin">
        {sessions.map(s => (
          <div key={s.id} onClick={() => onLoadSession(s.id)} className={clsx("px-3 py-2.5 text-sm rounded-md cursor-pointer mb-1 truncate flex items-center gap-2", currentSessionId === s.id ? "bg-gray-100 font-medium" : "hover:bg-gray-50 text-gray-600")}>
            <MessageSquare size={14} /> {s.title}
          </div>
        ))}
      </div>

      {/* 底部用户 */}
      <div className="p-4 border-t flex justify-between items-center text-sm text-gray-600">
        <span className="font-bold">{username}</span>
        <LogOut size={16} className="cursor-pointer hover:text-red-500" onClick={onLogout}/>
      </div>
    </div>
  );
}