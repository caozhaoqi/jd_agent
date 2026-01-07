import { create } from 'zustand';
import { Message } from '@/types/chat';

const DEBUG = process.env.NODE_ENV === 'development';

interface MessageState {
  messages: Message[];
  isLoading: boolean;
  showStartInterviewBtn: boolean;
  setMessages: (messages: Message[]) => void;
  addMessage: (message: Message) => void;
  updateLastMessage: (updater: (lastMessage: Message) => Message) => void;
  setIsLoading: (isLoading: boolean) => void;
  setShowStartInterviewBtn: (show: boolean) => void;
  resetMessages: () => void;
}

const log = (...args: any[]) => {
  if (DEBUG) console.log(...args);
};

export const useMessageStore = create<MessageState>((set) => ({
  messages: [],
  isLoading: false,
  showStartInterviewBtn: false,

  setMessages: (messages) => {
    log("🏪 [MessageStore] setMessages:", messages.length, "messages");
    set({ messages });
  },

  addMessage: (message) => {
    log("➕ [MessageStore] addMessage:", message.role, message.content?.length || 0, "chars");
    set((state) => ({ messages: [...state.messages, message] }));
  },

  updateLastMessage: (updater) => {
    log("🔄 [MessageStore] updateLastMessage");
    set((state) => {
      if (state.messages.length === 0) {
        log("⚠️ [MessageStore] Empty messages array");
        return state;
      }
      const newMessages = [...state.messages];
      newMessages[newMessages.length - 1] = updater(newMessages[newMessages.length - 1]);
      return { messages: newMessages };
    });
  },

  setIsLoading: (isLoading) => {
    log("🔍 [MessageStore] setIsLoading:", isLoading);
    set({ isLoading });
  },

  setShowStartInterviewBtn: (show) => {
    log("🔍 [MessageStore] setShowStartInterviewBtn:", show);
    set({ showStartInterviewBtn: show });
  },

  resetMessages: () => {
    log("🔍 [MessageStore] resetMessages");
    set({ messages: [], showStartInterviewBtn: false });
  },
}));
