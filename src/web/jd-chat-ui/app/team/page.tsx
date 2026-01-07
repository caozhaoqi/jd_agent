'use client';

import { useState, useEffect } from 'react';
import { Users, Plus, Copy, Check, Trash2, Crown, Shield, User, X } from 'lucide-react';
import { Team, TeamMember, TeamRole, ApiResponse } from '@/types/team';
import { handleAuthError } from '@/utils/auth-handler';

interface TeamPageProps {
  onNavigate: (page: string) => void;
}

export default function TeamPage({ onNavigate }: TeamPageProps) {
  const [teams, setTeams] = useState<Team[]>([]);
  const [currentTeam, setCurrentTeam] = useState<Team | null>(null);
  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showInviteModal, setShowInviteModal] = useState(false);
  const [showJoinModal, setShowJoinModal] = useState(false);
  const [newTeamName, setNewTeamName] = useState('');
  const [newTeamDesc, setNewTeamDesc] = useState('');
  const [inviteCode, setInviteCode] = useState('');
  const [joinCode, setJoinCode] = useState('');
  const [inviteRole, setInviteRole] = useState<TeamRole>('member');
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  useEffect(() => {
    fetchTeams();
  }, []);

  const fetchTeams = async () => {
    try {
      const res = await fetch('/api/v1/teams');
      if (res.status === 401) {
        handleAuthError();
        return;
      }
      const data = await res.json() as ApiResponse<Team[]>;
      if (data.code === 0 && data.data) {
        setTeams(data.data);
        if (data.data.length > 0 && !currentTeam) {
          setCurrentTeam(data.data[0]);
        }
      }
    } catch (err) {
      setError('获取团队列表失败');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateTeam = async () => {
    if (!newTeamName.trim()) {
      setError('请输入团队名称');
      return;
    }
    try {
      const res = await fetch('/api/v1/teams', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: newTeamName, description: newTeamDesc || null }),
      });
      if (res.status === 401) {
        handleAuthError();
        return;
      }
      const data = await res.json() as ApiResponse<Team>;
      if (data.code === 0 && data.data) {
        setTeams([...teams, data.data]);
        setCurrentTeam(data.data);
        setShowCreateModal(false);
        setNewTeamName('');
        setNewTeamDesc('');
        setSuccess('团队创建成功');
        setTimeout(() => setSuccess(''), 3000);
      } else {
        setError(data.message || '创建失败');
      }
    } catch (err) {
      setError('创建团队失败');
    }
  };

  const handleGenerateInvite = async () => {
    if (!currentTeam) return;
    try {
      const res = await fetch('/api/v1/teams/invitations/create', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ role: inviteRole }),
      });
      if (res.status === 401) {
        handleAuthError();
        return;
      }
      const data = await res.json() as ApiResponse<{ code: string }>;
      if (data.code === 0 && data.data) {
        setInviteCode(data.data.code);
        setShowInviteModal(true);
      } else {
        setError(data.message || '生成邀请码失败');
      }
    } catch (err) {
      setError('生成邀请码失败');
    }
  };

  const handleJoinTeam = async () => {
    if (!joinCode.trim()) {
      setError('请输入邀请码');
      return;
    }
    try {
      const res = await fetch('/api/v1/teams/join', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ invitation_code: joinCode }),
      });
      const data = await res.json() as ApiResponse<Team>;
      if (data.code === 0 && data.data) {
        setTeams([...teams, data.data]);
        setCurrentTeam(data.data);
        setShowJoinModal(false);
        setJoinCode('');
        setSuccess('加入团队成功');
        setTimeout(() => setSuccess(''), 3000);
      } else {
        setError(data.message || '加入失败');
      }
    } catch (err) {
      setError('加入团队失败');
    }
  };

  const handleRemoveMember = async (memberId: number) => {
    if (!currentTeam) return;
    if (!confirm('确定要移除该成员吗？')) return;
    try {
      const res = await fetch('/api/v1/teams/member/remove', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ member_id: memberId }),
      });
      if (res.status === 401) {
        handleAuthError();
        return;
      }
      const data = await res.json() as ApiResponse<null>;
      if (data.code === 0) {
        fetchTeams();
        setSuccess('成员已移除');
        setTimeout(() => setSuccess(''), 3000);
      } else {
        setError(data.message || '移除失败');
      }
    } catch (err) {
      setError('移除成员失败');
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const getRoleIcon = (role: TeamRole) => {
    switch (role) {
      case 'owner': return <Crown size={14} className="text-yellow-500" />;
      case 'admin': return <Shield size={14} className="text-blue-500" />;
      case 'member': return <User size={14} className="text-gray-500" />;
    }
  };

  const getRoleName = (role: TeamRole) => {
    switch (role) {
      case 'owner': return '所有者';
      case 'admin': return '管理员';
      case 'member': return '成员';
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto p-6">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <Users className="w-6 h-6 text-blue-500" />
          <h1 className="text-2xl font-bold">团队管理</h1>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setShowJoinModal(true)}
            className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors"
          >
            加入团队
          </button>
          <button
            onClick={() => setShowCreateModal(true)}
            className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors flex items-center gap-2"
          >
            <Plus size={16} /> 创建团队
          </button>
        </div>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-50 text-red-600 rounded-lg text-sm">{error}</div>
      )}
      {success && (
        <div className="mb-4 p-3 bg-green-50 text-green-600 rounded-lg text-sm">{success}</div>
      )}

      {teams.length === 0 ? (
        <div className="text-center py-12 bg-gray-50 rounded-lg">
          <Users className="w-12 h-12 text-gray-300 mx-auto mb-3" />
          <p className="text-gray-500">还没有团队</p>
          <p className="text-sm text-gray-400 mt-1">创建或加入一个团队开始协作</p>
        </div>
      ) : (
        <div className="space-y-4">
          {teams.map((team) => (
            <div
              key={team.id}
              className={`bg-white border rounded-lg p-4 cursor-pointer transition-all ${
                currentTeam?.id === team.id ? 'border-blue-500 shadow-md' : 'border-gray-200 hover:border-gray-300'
              }`}
              onClick={() => setCurrentTeam(team)}
            >
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-semibold text-lg">{team.name}</h3>
                  {team.description && <p className="text-gray-500 text-sm mt-1">{team.description}</p>}
                  <p className="text-gray-400 text-xs mt-2">{team.member_count} 名成员</p>
                </div>
                {currentTeam?.id === team.id && (
                  <span className="px-3 py-1 bg-blue-100 text-blue-600 rounded-full text-sm">当前团队</span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {currentTeam && (
        <div className="mt-8">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold">成员列表</h2>
            <button
              onClick={handleGenerateInvite}
              className="px-3 py-1.5 bg-green-500 text-white rounded-lg hover:bg-green-600 text-sm flex items-center gap-1"
            >
              <Plus size={14} /> 邀请成员
            </button>
          </div>
          <div className="bg-white border rounded-lg overflow-hidden">
            {currentTeam.members?.map((member) => (
              <div key={member.id} className="flex items-center justify-between p-4 border-b last:border-b-0 hover:bg-gray-50">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-gray-100 rounded-full flex items-center justify-center">
                    <User className="w-5 h-5 text-gray-500" />
                  </div>
                  <div>
                    <p className="font-medium">{member.username}</p>
                    <p className="text-sm text-gray-500">{member.email}</p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <span className="flex items-center gap-1 px-2 py-1 bg-gray-100 rounded text-sm">
                    {getRoleIcon(member.role)}
                    <span>{getRoleName(member.role)}</span>
                  </span>
                  {member.role !== 'owner' && (
                    <button
                      onClick={(e) => { e.stopPropagation(); handleRemoveMember(member.id); }}
                      className="p-2 text-red-500 hover:bg-red-50 rounded"
                    >
                      <Trash2 size={16} />
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {showCreateModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-md">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold">创建团队</h3>
              <button onClick={() => setShowCreateModal(false)} className="text-gray-400 hover:text-gray-600">
                <X size={20} />
              </button>
            </div>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">团队名称</label>
                <input
                  type="text"
                  value={newTeamName}
                  onChange={(e) => setNewTeamName(e.target.value)}
                  className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="请输入团队名称"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">团队描述（可选）</label>
                <textarea
                  value={newTeamDesc}
                  onChange={(e) => setNewTeamDesc(e.target.value)}
                  className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="请输入团队描述"
                  rows={3}
                />
              </div>
              <div className="flex gap-2 justify-end">
                <button
                  onClick={() => setShowCreateModal(false)}
                  className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg"
                >
                  取消
                </button>
                <button
                  onClick={handleCreateTeam}
                  className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
                >
                  创建
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {showInviteModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-md">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold">邀请成员</h3>
              <button onClick={() => setShowInviteModal(false)} className="text-gray-400 hover:text-gray-600">
                <X size={20} />
              </button>
            </div>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">邀请码</label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={inviteCode}
                    readOnly
                    className="flex-1 px-3 py-2 border rounded-lg bg-gray-50"
                  />
                  <button
                    onClick={() => copyToClipboard(inviteCode)}
                    className="px-3 py-2 bg-gray-100 rounded-lg hover:bg-gray-200"
                  >
                    {copied ? <Check size={18} className="text-green-500" /> : <Copy size={18} />}
                  </button>
                </div>
                <p className="text-sm text-gray-500 mt-2">复制邀请码分享给需要加入的成员</p>
              </div>
              <div className="flex justify-end">
                <button
                  onClick={() => setShowInviteModal(false)}
                  className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
                >
                  完成
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {showJoinModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-md">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold">加入团队</h3>
              <button onClick={() => setShowJoinModal(false)} className="text-gray-400 hover:text-gray-600">
                <X size={20} />
              </button>
            </div>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">邀请码</label>
                <input
                  type="text"
                  value={joinCode}
                  onChange={(e) => setJoinCode(e.target.value)}
                  className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="请输入邀请码"
                />
              </div>
              <div className="flex gap-2 justify-end">
                <button
                  onClick={() => setShowJoinModal(false)}
                  className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg"
                >
                  取消
                </button>
                <button
                  onClick={handleJoinTeam}
                  className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
                >
                  加入
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
