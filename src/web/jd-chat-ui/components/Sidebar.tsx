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
    <div className="w-[280px] bg-white border-r border-[#e2e8f0] hidden md:flex flex-col flex-shrink-0 h-full shadow-md">
      {/* 顶部模式切换和新建会话 */}
      <div className="p-4 space-y-4">
        {/* 模式切换 */}
        <div className="bg-[#f8fafc] p-1.5 rounded-xl flex text-sm">
          <button
            onClick={() => setMode('guide')}
            className={clsx(
              "flex-1 py-2 rounded-lg transition-all flex justify-center gap-2 items-center",
              mode === 'guide'
                ? "bg-white shadow-sm text-[#3b82f6] font-semibold"
                : "text-[#64748b] hover:bg-[#f1f5f9]"
            )}
          >
            <LayoutDashboard size={14} />
            <span>JD 分析</span>
          </button>
          <button
            onClick={() => setMode('mock')}
            className={clsx(
              "flex-1 py-2 rounded-lg transition-all flex justify-center gap-2 items-center",
              mode === 'mock'
                ? "bg-white shadow-sm text-[#8b5cf6] font-semibold"
                : "text-[#64748b] hover:bg-[#f1f5f9]"
            )}
          >
            <Mic size={14} />
            <span>模拟面试</span>
          </button>
        </div>
        
        {/* 新建会话按钮 */}
        <button 
          onClick={handleNewChat} 
          className="w-full py-3 bg-[#3b82f6] text-white rounded-xl text-sm font-semibold flex justify-center items-center gap-2 hover:bg-[#2563eb] transition-colors shadow-md hover:shadow-lg"
        >
          <Plus size={18} />
          <span>新建会话</span>
        </button>
      </div>

      {/* 会话列表 */}
      <div className="flex-1 overflow-y-auto px-3 space-y-1">
        <h3 className="text-xs font-semibold text-[#94a3b8] uppercase tracking-wider mb-2 px-3 py-1">
          历史会话
        </h3>
        {sessions.length === 0 ? (
          <div className="text-center py-12 text-[#94a3b8]">
            <MessageSquare size={24} className="mx-auto mb-2 opacity-50" />
            <p className="text-sm">暂无历史会话</p>
          </div>
        ) : (
          sessions.map(s => (
            <div 
              key={s.id} 
              onClick={() => handleLoadSession(s.id)} 
              className={clsx(
                "px-3 py-3 rounded-lg cursor-pointer truncate flex items-center gap-3 transition-all",
                currentSessionId === s.id
                  ? "bg-[#eff6ff] text-[#1e40af] font-medium"
                  : "hover:bg-[#f1f5f9] text-[#475569]"
              )}
            >
              <MessageSquare size={16} className={currentSessionId === s.id ? "text-[#3b82f6]" : "text-[#94a3b8]"} />
              <span className="truncate flex-1">{s.title}</span>
            </div>
          ))
        )}
      </div>

      {/* 底部操作区 */}
      <div className="p-4 border-t border-[#e2e8f0] space-y-3">
        <button
          onClick={navigateToTeam}
          className="w-full py-3 bg-[#f8fafc] text-[#475569] rounded-xl text-sm font-medium flex justify-center items-center gap-2 hover:bg-[#f1f5f9] transition-colors border border-[#e2e8f0]"
        >
          <Users size={16} />
          <span>团队管理</span>
        </button>
        <button
          onClick={navigateToReport}
          className="w-full py-3 bg-[#f8fafc] text-[#475569] rounded-xl text-sm font-medium flex justify-center items-center gap-2 hover:bg-[#f1f5f9] transition-colors border border-[#e2e8f0]"
        >
          <FileText size={16} />
          <span>报告导出</span>
        </button>
        
        {/* 用户信息和退出 */}
        <div className="pt-3 border-t border-[#e2e8f0] flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-[#3b82f6] rounded-full flex items-center justify-center text-white font-semibold">
              {username ? username.charAt(0).toUpperCase() : 'U'}
            </div>
            <span className="font-medium text-[#1e293b] text-sm">{username || '用户'}</span>
          </div>
          <button 
            onClick={logout}
            className="p-2 rounded-lg text-[#94a3b8] hover:bg-[#f1f5f9] hover:text-[#ef4444] transition-colors"
          >
            <LogOut size={18} />
          </button>
        </div>
      </div>
    </div>
  );
}
