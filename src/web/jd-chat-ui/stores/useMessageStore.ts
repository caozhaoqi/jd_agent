import { create } from 'zustand';
import { Message } from '@/types/chat';
import { debugLogger, stateUpdate } from '@/utils/debugLogger';

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

  setMessages: (messages) => {
    console.log("🏪 [MessageStore] 设置消息数组", {
      messageCount: messages.length,
      hasUserMessages: messages.some(m => m.role === 'user'),
      hasAssistantMessages: messages.some(m => m.role === 'assistant'),
      firstMessagePreview: messages[0]?.content?.substring(0, 50),
      lastMessagePreview: messages[messages.length - 1]?.content?.substring(0, 50),
      timestamp: new Date().toISOString()
    });
    stateUpdate("messageStore", "setMessages", { 
      messageCount: messages.length,
      totalContentLength: messages.reduce((sum, msg) => sum + (msg.content?.length || 0), 0)
    });
    set({ messages });
  },

  addMessage: (message) => {
    console.log("➕ [MessageStore] 添加新消息", {
      role: message.role,
      contentLength: message.content?.length || 0,
      contentPreview: message.content?.substring(0, 100),
      hasThoughts: !!message.thoughts,
      thoughtCount: message.thoughts?.length || 0,
      isJson: !!message.isJson,
      isThinkingFinished: message.isThinkingFinished,
      timestamp: new Date().toISOString()
    });
    
    stateUpdate("messageStore", "addMessage", { 
      role: message.role, 
      contentLength: message.content?.length,
      hasThoughts: !!message.thoughts,
      thoughtCount: message.thoughts?.length || 0,
      isJson: !!message.isJson
    });
    
    set((state) => {
      const newMessages = [...state.messages, message];
      console.log("📋 [MessageStore] 更新后的消息数组", {
        previousCount: state.messages.length,
        newCount: newMessages.length,
        lastMessageRole: newMessages[newMessages.length - 1]?.role,
        timestamp: new Date().toISOString()
      });
      return { messages: newMessages };
    });
  },

  updateLastMessage: (updater) => {
    console.log("🔄 [MessageStore] 开始更新最后一条消息", {
      currentMessageCount: undefined, // 将在下面计算
      timestamp: new Date().toISOString()
    });
    
    stateUpdate("messageStore", "updateLastMessage", { 
      timestamp: Date.now(),
      operation: 'start_update'
    });
    
    set((state) => {
      if (state.messages.length === 0) {
        console.log("⚠️ [MessageStore] 消息数组为空，无法更新");
        return state;
      }
      
      const newMessages = [...state.messages];
      const lastIndex = newMessages.length - 1;
      const lastMessage = newMessages[lastIndex];
      
      console.log("🔍 [MessageStore] 更新前的最后一条消息", {
        messageIndex: lastIndex,
        role: lastMessage.role,
        contentLength: lastMessage.content?.length || 0,
        contentPreview: lastMessage.content?.substring(0, 100),
        thoughtCount: lastMessage.thoughts?.length || 0,
        isThinkingFinished: lastMessage.isThinkingFinished,
        isJson: lastMessage.isJson
      });
      
      const updatedMessage = updater(lastMessage);
      
      console.log("✅ [MessageStore] 更新后的消息", {
        messageIndex: lastIndex,
        role: updatedMessage.role,
        contentLength: updatedMessage.content?.length || 0,
        contentPreview: updatedMessage.content?.substring(0, 100),
        thoughtCount: updatedMessage.thoughts?.length || 0,
        isThinkingFinished: updatedMessage.isThinkingFinished,
        isJson: updatedMessage.isJson,
        contentChanged: updatedMessage.content !== lastMessage.content,
        thoughtsChanged: updatedMessage.thoughts !== lastMessage.thoughts
      });
      
      stateUpdate("messageStore", "lastMessageUpdated", {
        index: lastIndex,
        changes: {
          hasContent: !!updatedMessage.content,
          hasThoughts: !!updatedMessage.thoughts,
          thoughtCount: updatedMessage.thoughts?.length || 0,
          isThinkingFinished: updatedMessage.isThinkingFinished,
          isJson: updatedMessage.isJson,
          contentLength: updatedMessage.content?.length || 0
        },
        previousState: {
          contentLength: lastMessage.content?.length || 0,
          thoughtCount: lastMessage.thoughts?.length || 0,
          isThinkingFinished: lastMessage.isThinkingFinished
        }
      });
      
      newMessages[lastIndex] = updatedMessage;
      console.log("📝 [MessageStore] 消息数组更新完成", {
        totalMessages: newMessages.length,
        lastMessageIndex: lastIndex,
        timestamp: new Date().toISOString()
      });
      
      return { messages: newMessages };
    });
  },

  setIsLoading: (isLoading) => {
    console.log("🔍 [MessageStore] setIsLoading:", isLoading);
    stateUpdate("messageStore", "setIsLoading", { isLoading });
    set({ isLoading });
  },

  setShowStartInterviewBtn: (show) => {
    console.log("🔍 [MessageStore] setShowStartInterviewBtn:", show);
    stateUpdate("messageStore", "setShowStartInterviewBtn", { show });
    set({ showStartInterviewBtn: show });
  },

  resetMessages: () => {
    console.log("🔍 [MessageStore] resetMessages");
    stateUpdate("messageStore", "resetMessages", {});
    set({ messages: [], showStartInterviewBtn: false });
  },
}));
