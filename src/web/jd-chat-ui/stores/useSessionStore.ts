import { create } from 'zustand';
import { Session } from '@/types/chat';
import { API_BASE } from '@/hooks/useChat';

const DEBUG = process.env.NODE_ENV === 'development';

interface SessionState {
  sessions: Session[];
  currentSessionId: number | null;
  token: string | null;
  username: string | null;
  isAuthenticated: boolean;
  isInitializing: boolean;
  fetchSessions: () => Promise<void>;
  setCurrentSessionId: (id: number | null) => void;
  setToken: (token: string | null) => void;
  setUsername: (username: string | null) => void;
  initializeAuth: () => void;
  logout: () => void;
}

const canUseDOM = typeof window !== 'undefined';

const log = (...args: any[]) => {
  if (DEBUG) console.log(...args);
};

export const useSessionStore = create<SessionState>((set, get) => ({
  sessions: [],
  currentSessionId: null,
  token: null,
  username: null,
  isAuthenticated: false,
  isInitializing: true,

  fetchSessions: async () => {
    const token = get().token;
    if (!token) {
      log("🔐 fetchSessions: No token found");
      return;
    }

    log("🔐 fetchSessions: Fetching sessions");
    try {
      const res = await fetch(`${API_BASE}/chat/history/sessions`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      
      if (res.status === 401) {
        log("🔐 fetchSessions: Token expired");
        get().logout();
        return;
      }
      
      if (res.ok) {
        const sessionsData = await res.json();
        log("🔐 fetchSessions: Success", sessionsData.length, "sessions");
        set({ sessions: sessionsData });
      } else {
        log("🔐 fetchSessions: Failed", res.status);
      }
    } catch (e) {
      log("🔐 fetchSessions: Network error", e);
    }
  },

  setCurrentSessionId: (id) => {
    log("🔐 setCurrentSessionId:", id);
    set({ currentSessionId: id });
  },

  setToken: (token) => {
    log("🔐 setToken:", token ? "received" : "cleared");
    set({ token });
  },

  setUsername: (username) => {
    log("🔐 setUsername:", username);
    set({ username });
  },

  initializeAuth: () => {
    log("🔐 initializeAuth: Starting");
    
    if (!canUseDOM) {
      log("🔐 initializeAuth: Not in browser environment");
      set({ isInitializing: false });
      return;
    }
    
    try {
      const storedToken = localStorage.getItem("token");
      const storedUsername = localStorage.getItem("username");
      
      log("🔐 initializeAuth: Stored credentials found:", !!storedToken);
      
      if (storedToken && storedUsername) {
        log("🔐 initializeAuth: Setting authenticated state");
        set({ 
          token: storedToken, 
          username: storedUsername, 
          isAuthenticated: true,
          isInitializing: false 
        });
        get().fetchSessions();
      } else {
        log("🔐 initializeAuth: No credentials, setting unauthenticated");
        set({ 
          isAuthenticated: false,
          isInitializing: false 
        });
      }
    } catch (error) {
      log("🔐 initializeAuth: Error", error);
      set({ 
        isAuthenticated: false,
        isInitializing: false 
      });
    }
  },

  logout: () => {
    log("🔐 logout: Logging out");
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
    window.location.href = '/login';
  },
}));
