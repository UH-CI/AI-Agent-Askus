"use client";

import { useEffect, useState, useRef } from "react";
import { api } from "~/trpc/react";

type ChatMessages = {
  message: {
    type: "human" | "ai";
    content: string;
  };
  sources: string[];
}[];

export default function Home() {
  const [messages, setMessages] = useState<ChatMessages>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [retriever, setRetriever] = useState<"askus" | "policies" | "graphdb">("askus");
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  const chat = api.chat.response.useMutation({
    onSuccess: (data) => {
      setMessages((prev) => [...prev, data]);
      setLoading(false);
    },
    onError: (error) => {
      setMessages((prev) => [
        ...prev,
        {
          message: {
            type: "ai",
            content: "Sorry, my services may be unavailable at this time.",
          },
          sources: [],
        },
      ]);
      setLoading(false);
    },
  });

  useEffect(() => {
    if (messages[messages.length - 1]?.message.type === "human") {
      chat.mutate({
        input: messages.map((message) => message.message),
        retriever: retriever,
      });
    }
  }, [messages]);

  const handleKeyDown = (event: React.KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "Enter" && input.trim()) {
      setMessages((prev) => [
        ...prev,
        {
          message: { type: "human", content: input },
          sources: [],
        },
      ]);
      setInput("");
      setLoading(true);
    }
  };

  return (
    <div className="flex h-screen flex-col bg-gray-50 p-4">
      <div className="mb-4">
        <div className="flex justify-center space-x-6">
          <label className="flex items-center space-x-2">
            <input
              type="radio"
              value="askus"
              checked={retriever === "askus"}
              onChange={(e) => setRetriever(e.target.value as "askus" | "policies" | "graphdb")}
              className="h-4 w-4 text-blue-600 focus:ring-blue-500"
            />
            <span className="text-sm font-medium text-gray-700">AskUs</span>
          </label>
          <label className="flex items-center space-x-2">
            <input
              type="radio"
              value="policies"
              checked={retriever === "policies"}
              onChange={(e) => setRetriever(e.target.value as "askus" | "policies" | "graphdb")}
              className="h-4 w-4 text-blue-600 focus:ring-blue-500"
            />
            <span className="text-sm font-medium text-gray-700">Policies</span>
          </label>
          <label className="flex items-center space-x-2">
            <input
              type="radio"
              value="graphdb"
              checked={retriever === "graphdb"}
              onChange={(e) => setRetriever(e.target.value as "askus" | "policies" | "graphdb")}
              className="h-4 w-4 text-blue-600 focus:ring-blue-500"
            />
            <span className="text-sm font-medium text-gray-700">GraphDB</span>
          </label>
        </div>
      </div>
      <div className="mb-4 flex-1 overflow-y-auto rounded-lg bg-white p-4 shadow-lg">
        <div className="space-y-4">
          {messages.map((msg, index) => (
            <div
              key={index}
              className={`flex ${msg.message.type === "ai" ? "justify-start" : "justify-end"}`}
            >
              <div
                className={`max-w-[80%] rounded-2xl px-4 py-2 ${msg.message.type === "ai"
                  ? "bg-blue-100 text-blue-900"
                  : "bg-green-100 text-green-900"
                  }`}
              >
                <div className="mb-1 text-sm font-semibold">
                  {msg.message.type === "ai" ? "Hoku" : "You"}
                </div>
                <div className="text-sm">{msg.message.content}</div>
                {msg.sources.length > 0 && (
                  <div className="mt-2 space-y-1">
                    {msg.sources.map((link, i) => (
                      <a
                        key={i}
                        className="block text-xs text-blue-600 hover:text-blue-800 hover:underline"
                        href={link}
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        {link}
                      </a>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ))}
          {loading && (
            <div className="flex justify-start">
              <div className="max-w-[80%] rounded-2xl bg-blue-100 px-4 py-2 text-blue-900">
                <div className="mb-1 text-sm font-semibold">AI Assistant</div>
                <div className="flex items-center space-x-2">
                  <div className="h-2 w-2 animate-bounce rounded-full bg-blue-600"></div>
                  <div
                    className="h-2 w-2 animate-bounce rounded-full bg-blue-600"
                    style={{ animationDelay: "0.2s" }}
                  ></div>
                  <div
                    className="h-2 w-2 animate-bounce rounded-full bg-blue-600"
                    style={{ animationDelay: "0.4s" }}
                  ></div>
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
      </div>
      <div className="relative">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Type your message and press Enter"
          className="w-full rounded-full border-2 border-gray-300 bg-white px-6 py-3 pr-12 text-sm shadow-sm transition-all focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-200"
        />
        <div className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-400">
          ↵
        </div>
      </div>
    </div>
  );
}
