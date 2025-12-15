export type Message = {
  role: "user" | "assistant";
  content: string;
  isJson?: boolean;
  thoughts?: string[]; // ✅ 新增：存储思考步骤数组
  isThinkingFinished?: boolean; // ✅ 新增：标记思考过程是否完成
};

export type ChatMode = 'guide' | 'mock';

export type Session = {
  id: number;
  title: string;
  created_at: string;
  mode: ChatMode;
};