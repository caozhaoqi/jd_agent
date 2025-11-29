export type Message = {
  role: "user" | "assistant";
  content: string;
  isJson?: boolean;
};

export type Session = {
  id: number;
  title: string;
  created_at?: string;
};

export type ChatMode = 'guide' | 'mock';