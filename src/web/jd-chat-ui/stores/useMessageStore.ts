import { create } from 'zustand';
import { Message } from '@/types/chat';

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

export const useMessageStore = create<MessageState>((set) => ({
  messages: [],
  isLoading: false,
  showStartInterviewBtn: false,

  setMessages: (messages) => set({ messages }),

  addMessage: (message) => set((state) => ({ messages: [...state.messages, message] })),

  updateLastMessage: (updater) =>
    set((state) => {
      if (state.messages.length === 0) return state;
      const newMessages = [...state.messages];
      const lastIndex = newMessages.length - 1;
      newMessages[lastIndex] = updater(newMessages[lastIndex]);
      return { messages: newMessages };
    }),

  setIsLoading: (isLoading) => set({ isLoading }),

  setShowStartInterviewBtn: (show) => set({ showStartInterviewBtn: show }),

  resetMessages: () => set({ messages: [], showStartInterviewBtn: false }),
}));
