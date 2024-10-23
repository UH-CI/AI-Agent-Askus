"use client";

import { useEffect, useState } from "react";
import { api } from "~/trpc/react";

type ChatMessages = {
  type: "human" | "ai";
  content: string;
}[];

export default function Home() {
  const [messages, setMessages] = useState<ChatMessages>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  const chat = api.chat.response.useMutation({
    onSuccess: (data) => {
      setMessages((prev) => [...prev, data.message]);
      setLoading(false);
    },
  });

  useEffect(() => {
    if (messages[messages.length - 1]?.type === "human") {
      chat.mutate({
        input: messages,
        retriever: "askus",
      });
    }
  }, [messages]);

  const handleKeyDown = (event: React.KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "Enter" && input.trim()) {
      setMessages((prev) => [...prev, { type: "human", content: input }]);
      setInput("");
      setLoading(true);
    }
  };

  return (
    <div className="flex h-screen flex-col p-4">
      <div className="mb-4 flex-1 overflow-y-auto rounded-lg border border-gray-300 p-4">
        {messages.map((msg, index) => (
          <div
            key={index}
            className={`my-2 ${msg.type === "ai" ? "text-blue-600" : "text-green-600"}`}
          >
            <strong>{msg.type === "ai" ? "AI" : "You"}:</strong> {msg.content}
          </div>
        ))}
        {loading && (
          <div className="my-2 animate-pulse text-blue-600">
            <strong>AI:</strong> Loading...
          </div>
        )}
      </div>
      <input
        type="text"
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Type your message and press Enter"
        className="rounded border p-2"
      />
    </div>
  );
}
