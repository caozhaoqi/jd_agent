'use client';

import { useState, useEffect } from 'react';
import { FileText, Download, History, Loader, Check, Copy, Trash2, FileCode, File } from 'lucide-react';
import { ExportFormat, ExportRecord } from '@/types/report';
import { ApiResponse } from '@/types/team';
import { handleAuthError } from '@/utils/auth-handler';
import { useSessionStore } from '@/stores/useSessionStore';

interface ReportPageProps {
  onNavigate: (page: string) => void;
}

interface InterviewSession {
  id: number;
  title: string;
  job_position: string;
  created_at: string;
  message_count: number;
}

interface SessionResponse {
  sessions: InterviewSession[];
  total: number;
}

export default function ReportPage({ onNavigate }: ReportPageProps) {
  const [sessions, setSessions] = useState<InterviewSession[]>([]);
  const [history, setHistory] = useState<ExportRecord[]>([]);
  const [selectedSession, setSelectedSession] = useState<InterviewSession | null>(null);
  const [selectedFormat, setSelectedFormat] = useState<ExportFormat>('markdown');
  const [reportTitle, setReportTitle] = useState('');
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [copied, setCopied] = useState(false);
  const [generatedContent, setGeneratedContent] = useState<string | null>(null);
  const { token } = useSessionStore();

  useEffect(() => {
    fetchSessions();
    fetchHistory();
  }, []);

  const fetchSessions = async () => {
    try {
      const res = await fetch('/api/v1/reports/sessions', {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.status === 401) {
        handleAuthError();
        return;
      }
      const data = await res.json() as ApiResponse<SessionResponse>;
      if (data.code === 0 && data.data) {
        setSessions(data.data.sessions);
        if (data.data.sessions.length > 0) {
          const first = data.data.sessions[0];
          setSelectedSession(first);
          setReportTitle(`面试报告 - ${first.title}`);
        }
      }
    } catch (err) {
      setError('获取面试记录失败');
    } finally {
      setLoading(false);
    }
  };

  const fetchHistory = async () => {
    try {
      const res = await fetch('/api/v1/reports/history', {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.status === 401) {
        handleAuthError();
        return;
      }
      const data = await res.json() as ApiResponse<{ records: ExportRecord[] }>;
      if (data.code === 0 && data.data) {
        setHistory(data.data.records);
      }
    } catch (err) {
      console.error('获取导出历史失败');
    }
  };

  const handleExport = async () => {
    if (!selectedSession) {
      setError('请选择面试记录');
      return;
    }
    if (!reportTitle.trim()) {
      setError('请输入报告标题');
      return;
    }

    setExporting(true);
    setError('');
    setGeneratedContent(null);

    try {
      const res = await fetch('/api/v1/reports/export', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          session_id: selectedSession.id,
          format: selectedFormat,
          report_title: reportTitle,
        }),
      });

      if (res.status === 401) {
        handleAuthError();
        return;
      }

      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}));
        setError(errorData.message || '导出失败');
        return;
      }

      const blob = await res.blob();
      const content = await blob.text();
      setGeneratedContent(content);

      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${reportTitle}.${selectedFormat === 'markdown' ? 'md' : selectedFormat === 'html' ? 'html' : 'txt'}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);

      setSuccess('报告导出成功');
      setTimeout(() => setSuccess(''), 3000);
      fetchHistory();
    } catch (err) {
      setError('导出失败，请稍后重试');
    } finally {
      setExporting(false);
    }
  };

  const handleDownload = async (record: ExportRecord) => {
    try {
      const res = await fetch(`/api/v1/reports/exports/${record.id}/download`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.status === 401) {
        handleAuthError();
        return;
      }
      if (!res.ok) {
        setError('下载失败');
        return;
      }
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${record.report_title}.${record.format === 'markdown' ? 'md' : record.format === 'html' ? 'html' : 'txt'}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
      setSuccess('下载成功');
      setTimeout(() => setSuccess(''), 3000);
    } catch (err) {
      setError('下载失败');
    }
  };

  const handleDeleteHistory = async (recordId: number) => {
    if (!confirm('确定要删除这条导出记录吗？')) return;
    try {
      const res = await fetch(`/api/v1/reports/exports/${recordId}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.status === 401) {
        handleAuthError();
        return;
      }
      const data = await res.json() as ApiResponse<null>;
      if (data.code === 0) {
        setHistory(history.filter(h => h.id !== recordId));
        setSuccess('删除成功');
        setTimeout(() => setSuccess(''), 3000);
      } else {
        setError(data.message || '删除失败');
      }
    } catch (err) {
      setError('删除失败');
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleString('zh-CN');
  };

  const getFormatIcon = (format: ExportFormat) => {
    switch (format) {
      case 'markdown': return <FileText size={14} className="text-blue-500" />;
      case 'html': return <FileCode size={14} className="text-orange-500" />;
      case 'text': return <File size={14} className="text-gray-500" />;
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
    <div className="max-w-6xl mx-auto p-6">
      <div className="flex items-center gap-3 mb-6">
        <FileText className="w-6 h-6 text-blue-500" />
        <h1 className="text-2xl font-bold">面试报告导出</h1>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-50 text-red-600 rounded-lg text-sm">{error}</div>
      )}
      {success && (
        <div className="mb-4 p-3 bg-green-50 text-green-600 rounded-lg text-sm">{success}</div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="space-y-6">
          <div className="bg-white border rounded-lg p-6">
            <h2 className="text-lg font-semibold mb-4">选择面试记录</h2>
            <div className="space-y-2 max-h-64 overflow-y-auto">
              {sessions.map((session) => (
                <div
                  key={session.id}
                  className={`p-3 rounded-lg cursor-pointer transition-all ${
                    selectedSession?.id === session.id
                      ? 'bg-blue-50 border border-blue-500'
                      : 'bg-gray-50 border border-transparent hover:border-gray-300'
                  }`}
                  onClick={() => {
                    setSelectedSession(session);
                    setReportTitle(`面试报告 - ${session.title}`);
                  }}
                >
                  <p className="font-medium">{session.title}</p>
                  <p className="text-sm text-gray-500">{session.job_position}</p>
                  <p className="text-xs text-gray-400 mt-1">{formatDate(session.created_at)} · {session.message_count} 条消息</p>
                </div>
              ))}
            </div>
          </div>

          <div className="bg-white border rounded-lg p-6">
            <h2 className="text-lg font-semibold mb-4">导出设置</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">报告标题</label>
                <input
                  type="text"
                  value={reportTitle}
                  onChange={(e) => setReportTitle(e.target.value)}
                  className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="请输入报告标题"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">导出格式</label>
                <div className="flex gap-2">
                  {[
                  { value: 'markdown' as ExportFormat, label: 'Markdown', icon: FileText },
                  { value: 'html' as ExportFormat, label: 'HTML', icon: FileCode },
                  { value: 'text' as ExportFormat, label: '纯文本', icon: File },
                ].map((format) => (
                    <button
                      key={format.value}
                      onClick={() => setSelectedFormat(format.value)}
                      className={`flex-1 px-4 py-3 rounded-lg border-2 transition-all flex items-center justify-center gap-2 ${
                        selectedFormat === format.value
                          ? 'border-blue-500 bg-blue-50 text-blue-600'
                          : 'border-gray-200 hover:border-gray-300'
                      }`}
                    >
                      <format.icon size={18} />
                      <span>{format.label}</span>
                    </button>
                  ))}
                </div>
              </div>
              <button
                onClick={handleExport}
                disabled={exporting || !selectedSession}
                className="w-full py-3 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {exporting ? (
                  <>
                    <Loader size={18} className="animate-spin" />
                    导出中...
                  </>
                ) : (
                  <>
                    <Download size={18} />
                    导出报告
                  </>
                )}
              </button>
            </div>
          </div>
        </div>

        <div className="space-y-6">
          {generatedContent && (
            <div className="bg-white border rounded-lg p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold">预览</h2>
                <button
                  onClick={() => copyToClipboard(generatedContent)}
                  className="px-3 py-1.5 bg-gray-100 rounded-lg hover:bg-gray-200 text-sm flex items-center gap-1"
                >
                  {copied ? <Check size={14} className="text-green-500" /> : <Copy size={14} />}
                  复制内容
                </button>
              </div>
              <pre className="bg-gray-50 rounded-lg p-4 text-sm max-h-96 overflow-auto whitespace-pre-wrap break-words">
                {generatedContent}
              </pre>
            </div>
          )}

          <div className="bg-white border rounded-lg p-6">
            <div className="flex items-center gap-2 mb-4">
              <History className="w-5 h-5 text-gray-500" />
              <h2 className="text-lg font-semibold">导出历史</h2>
            </div>
            {history.length === 0 ? (
              <div className="text-center py-8 text-gray-500">
                <FileText className="w-10 h-10 text-gray-300 mx-auto mb-2" />
                <p>暂无导出记录</p>
              </div>
            ) : (
              <div className="space-y-2 max-h-96 overflow-y-auto">
                {history.map((record) => (
                  <div key={record.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                    <div className="flex items-center gap-3 min-w-0">
                      {getFormatIcon(record.format)}
                      <div className="min-w-0">
                        <p className="font-medium truncate">{record.report_title}</p>
                        <p className="text-xs text-gray-500">{formatDate(record.created_at)}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => handleDownload(record)}
                        className="p-2 text-blue-500 hover:bg-blue-50 rounded"
                        title="下载"
                      >
                        <Download size={16} />
                      </button>
                      <button
                        onClick={() => handleDeleteHistory(record.id)}
                        className="p-2 text-red-500 hover:bg-red-50 rounded"
                        title="删除"
                      >
                        <Trash2 size={16} />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
