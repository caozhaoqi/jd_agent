import { Plus, MessageSquare, LogOut, LayoutDashboard, Mic, Users, FileText } from "lucide-react";
import clsx from "clsx";
import { ChatMode } from "@/types/chat";
import { useSessionStore } from "@/stores/useSessionStore";
import { useMessageStore } from "@/stores/useMessageStore";
import { useRouter } from "next/navigation";

interface SidebarProps {
  mode: ChatMode;
  setMode: (mode: ChatMode) => void;
}

export default function Sidebar({ mode, setMode }: SidebarProps) {
  const router = useRouter();
  const { username, sessions, currentSessionId, setCurrentSessionId, logout, fetchSessionMessages } = useSessionStore();
  const { resetMessages } = useMessageStore();

  const handleNewChat = () => {
    setCurrentSessionId(null);
    resetMessages();
    setMode('guide');
  };

  const handleLoadSession = async (id: number) => {
    resetMessages();
    setCurrentSessionId(id);
    // 加载该会话的消息
    await fetchSessionMessages(id);
    // 不再强制将模式设置为'mock'，保留当前模式
  };

  const navigateToTeam = () => {
    router.push('/team');
  };

  const navigateToReport = () => {
    router.push('/report');
  };

  return (
    <div className="w-[260px] bg-[#fcfdfd] border-r border-gray-200 hidden md:flex flex-col flex-shrink-0">
      <div className="p-4 space-y-2">
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

      <div className="flex-1 overflow-y-auto px-2 scrollbar-thin">
        {sessions.map(s => (
          <div key={s.id} onClick={() => handleLoadSession(s.id)} className={clsx("px-3 py-2.5 text-sm rounded-md cursor-pointer mb-1 truncate flex items-center gap-2", currentSessionId === s.id ? "bg-gray-100 font-medium" : "hover:bg-gray-50 text-gray-600")}>
            <MessageSquare size={14} /> {s.title}
          </div>
        ))}
      </div>

      <div className="p-4 border-t space-y-2">
        <button
          onClick={navigateToTeam}
          className="w-full py-2 bg-gray-50 text-gray-700 rounded-md text-sm font-medium flex justify-center items-center gap-2 hover:bg-gray-100 transition-colors"
        >
          <Users size={16} /> 团队管理
        </button>
        <button
          onClick={navigateToReport}
          className="w-full py-2 bg-gray-50 text-gray-700 rounded-md text-sm font-medium flex justify-center items-center gap-2 hover:bg-gray-100 transition-colors"
        >
          <FileText size={16} /> 报告导出
        </button>
        <div className="pt-2 border-t flex justify-between items-center text-sm text-gray-600">
          <span className="font-bold">{username}</span>
          <LogOut size={16} className="cursor-pointer hover:text-red-500" onClick={logout}/>
        </div>
      </div>
    </div>
  );
}
