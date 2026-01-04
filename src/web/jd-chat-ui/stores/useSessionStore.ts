import { create } from 'zustand';
import { Session } from '@/types/chat';
import { API_BASE } from '@/hooks/useChat'; // 复用 API base

interface SessionState {
  sessions: Session[];
  currentSessionId: number | null;
  token: string | null;
  username: string | null;
  isAuthenticated: boolean; // 是否已认证
  isInitializing: boolean; // 是否正在初始化认证状态
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
  isAuthenticated: false,
  isInitializing: true, // 初始状态为正在初始化

  fetchSessions: async () => {
    const token = get().token;
    if (!token) {
      console.log("🔐 fetchSessions: No token found");
      return;
    }

    console.log("🔐 fetchSessions: Fetching sessions with token");
    try {
      const res = await fetch(`${API_BASE}/chat/history/sessions`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      
      if (res.status === 401) {
        console.log("🔐 fetchSessions: Token expired, logging out");
        get().logout();
        return;
      }
      
      if (res.ok) {
        const sessionsData = await res.json();
        console.log("🔐 fetchSessions: Sessions fetched successfully", sessionsData);
        set({ sessions: sessionsData });
      } else {
        console.error("🔐 fetchSessions: Failed to fetch sessions", res.status, res.statusText);
      }
    } catch (e) {
      console.error("🔐 fetchSessions: Network error", e);
    }
  },

  setCurrentSessionId: (id) => {
    console.log("🔐 setCurrentSessionId:", id);
    set({ currentSessionId: id });
  },

  setToken: (token) => {
    console.log("🔐 setToken: Token", token ? "received" : "cleared");
    set({ token });
  },

  setUsername: (username) => {
    console.log("🔐 setUsername:", username);
    set({ username });
  },

  initializeAuth: () => {
    if (!canUseDOM) {
      console.log("🔐 initializeAuth: Not in browser environment");
      set({ isInitializing: false });
      return;
    }
    
    console.log("🔐 initializeAuth: Starting authentication initialization");
    const storedToken = localStorage.getItem("token");
    const storedUsername = localStorage.getItem("username");
    
    console.log("🔐 initializeAuth: Stored token exists:", !!storedToken);
    console.log("🔐 initializeAuth: Stored username exists:", !!storedUsername);
    
    if (storedToken && storedUsername) {
      console.log("🔐 initializeAuth: Found stored credentials, setting authenticated state");
      set({ 
        token: storedToken, 
        username: storedUsername, 
        isAuthenticated: true,
        isInitializing: false 
      });
      get().fetchSessions();
    } else {
      console.log("🔐 initializeAuth: No stored credentials, setting unauthenticated state");
      set({ 
        isAuthenticated: false,
        isInitializing: false 
      });
    }
  },

  logout: () => {
    console.log("🔐 logout: Logging out user");
    localStorage.removeItem("token");
    localStorage.removeItem("username");
    set({ 
      token: null, 
      username: null, 
      sessions: [], 
      currentSessionId: null, 
      isAuthenticated: false,
      isInitializing: false
    });
    // 在实际应用中，这里会触发路由跳转到登录页
    window.location.href = '/login';
  },
}));
