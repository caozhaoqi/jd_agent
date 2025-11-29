import { useEffect, useRef } from "react";
import ReactMarkdown from "react-markdown";
import { Bot, User, Loader2 } from "lucide-react";
import clsx from "clsx";
import { Message } from "@/types/chat";

interface MessageListProps {
  messages: Message[];
  isLoading: boolean;
}

export default function MessageList({ messages, isLoading }: MessageListProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  return (
    <div className="flex-1 overflow-y-auto p-4 md:p-6 scroll-smooth">
      <div className="max-w-3xl mx-auto space-y-6">
        {messages.map((msg, idx) => (
          <div key={idx} className={clsx("flex gap-4", msg.role === "user" ? "flex-row-reverse" : "")}>
            <div className={clsx("w-8 h-8 rounded-full flex-shrink-0 flex items-center justify-center border", msg.role === "assistant" ? "bg-white text-blue-600" : "bg-gray-800 text-white")}>
              {msg.role === "assistant" ? <Bot size={18} /> : <User size={18} />}
            </div>
            <div className={clsx("max-w-[85%] rounded-2xl px-5 py-3 text-sm leading-7 shadow-sm border", msg.role === "user" ? "bg-blue-50 border-blue-100" : "bg-white border-gray-100")}>
              {msg.role === "assistant" ? (
                <div className="prose prose-sm max-w-none prose-headings:text-gray-800">
                  <ReactMarkdown>{msg.content}</ReactMarkdown>
                </div>
              ) : msg.content}
            </div>
          </div>
        ))}
        {isLoading && <div className="flex justify-center py-4"><Loader2 className="animate-spin text-blue-500" /></div>}
        <div ref={messagesEndRef} />
      </div>
    </div>
  );
}