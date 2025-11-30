export type Message = {
  role: "user" | "assistant";
  content: string;
  isJson?: boolean;
};

export type Message = {
  role: "user" | "assistant";
  content: string;
  isJson?: boolean;
  thoughts?: string[]; // ✅ 新增：存储思考步骤数组
};

export type ChatMode = 'guide' | 'mock';