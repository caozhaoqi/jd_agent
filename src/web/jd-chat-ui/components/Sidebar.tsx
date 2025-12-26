import { Plus, MessageSquare, LogOut, LayoutDashboard, Mic } from "lucide-react";
import clsx from "clsx";
import { ChatMode } from "@/types/chat";
import { useSessionStore } from "@/stores/useSessionStore";
import { useMessageStore } from "@/stores/useMessageStore";

interface SidebarProps {
  mode: ChatMode;
  setMode: (mode: ChatMode) => void;
}

export default function Sidebar({ mode, setMode }: SidebarProps) {
  // 从 store 中获取状态和 actions
  const { username, sessions, currentSessionId, setCurrentSessionId, logout, hasHydrated } = useSessionStore();
  const { resetMessages } = useMessageStore();

  const handleNewChat = () => {
    setCurrentSessionId(null);
    resetMessages();
    // 切换回 guide 模式作为新会话的默认模式
    setMode('guide');
  };

  const handleLoadSession = (id: number) => {
    setCurrentSessionId(id);
    // 加载会话时，自动切换到 mock 模式
    setMode('mock');
    // 实际加载消息的逻辑将在 page.tsx 中处理
  };

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
        <button onClick={handleNewChat} className="w-full py-2 bg-blue-50 text-blue-600 rounded-md text-sm font-medium border border-blue-100 flex justify-center items-center gap-2">
          <Plus size={16} /> 新建会话
        </button>
      </div>

      {/* 历史列表 */}
      <div className="flex-1 overflow-y-auto px-2 scrollbar-thin">
        {sessions.map(s => (
          <div key={s.id} onClick={() => handleLoadSession(s.id)} className={clsx("px-3 py-2.5 text-sm rounded-md cursor-pointer mb-1 truncate flex items-center gap-2", currentSessionId === s.id ? "bg-gray-100 font-medium" : "hover:bg-gray-50 text-gray-600")}>
            <MessageSquare size={14} /> {s.title}
          </div>
        ))}
      </div>

      {/* 底部用户 */}
      <div className="p-4 border-t flex justify-between items-center text-sm text-gray-600">
        <span className="font-bold" suppressHydrationWarning>
          {hasHydrated ? (username || "") : ""}
        </span>
        <LogOut size={16} className="cursor-pointer hover:text-red-500" onClick={logout}/>
      </div>
    </div>
  );
}
