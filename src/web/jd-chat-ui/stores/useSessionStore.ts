import { create } from 'zustand';
import { Session } from '@/types/chat';
import { API_BASE } from '@/hooks/useChat'; // 复用 API base

interface SessionState {
  sessions: Session[];
  currentSessionId: number | null;
  token: string | null;
  username: string | null;
  hasHydrated: boolean; // 防止首屏 token 为空时误跳登录
  fetchSessions: () => Promise<void>;
  setCurrentSessionId: (id: number | null) => void;
  setToken: (token: string | null) => void;
  setUsername: (username: string | null) => void;
  initializeAuth: () => void;
  logout: () => void;
}

const canUseDOM = typeof window !== 'undefined';

export const useSessionStore = create<SessionState>((set, get) => ({
  sessions: [],
  currentSessionId: null,
  token: null,
  username: null,
  hasHydrated: false, // SSR 及首次渲染均为 false，初始化后再置为 true

  fetchSessions: async () => {
    const token = get().token;
    if (!token) return;

    try {
      const res = await fetch(`${API_BASE}/chat/history/sessions`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.status === 401) {
        get().logout();
        return;
      }
      if (res.ok) {
        const sessionsData = await res.json();
        set({ sessions: sessionsData });
      }
    } catch (e) {
      console.error("Failed to fetch sessions:", e);
    }
  },

  setCurrentSessionId: (id) => set({ currentSessionId: id }),

  setToken: (token) => set({ token }),

  setUsername: (username) => set({ username }),

  initializeAuth: () => {
    if (!canUseDOM) return;
    const storedToken = localStorage.getItem("token");
    const storedUsername = localStorage.getItem("username");
    if (storedToken && storedUsername) {
      set({ token: storedToken, username: storedUsername, hasHydrated: true });
      get().fetchSessions();
    } else {
      set({ hasHydrated: true });
    }
  },

  logout: () => {
    localStorage.removeItem("token");
    localStorage.removeItem("username");
    set({ token: null, username: null, sessions: [], currentSessionId: null, hasHydrated: true });
    // 在实际应用中，这里会触发路由跳转到登录页
    window.location.href = '/login';
  },
}));
