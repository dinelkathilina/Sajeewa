import React, { useState } from "react";
import { Send, Bot, User } from "lucide-react";

interface Msg {
  sender: "user" | "bot";
  text: string;
}

const Chat: React.FC = () => {
  const [messages, setMessages] = useState<Msg[]>([
    {
      sender: "bot",
      text: "Hello! I am your Variation Assistant. Upload your files and tell me what changes you want to evaluate.",
    },
  ]);
  const [input, setInput] = useState("");

  const send = () => {
    if (!input.trim()) return;
    setMessages([...messages, { sender: "user", text: input }]);
    setInput("");
    // TODO: Call API
    setTimeout(() => {
      setMessages((prev) => [
        ...prev,
        { sender: "bot", text: "I am processing your request..." },
      ]);
    }, 1000);
  };

  return (
    <div className="flex flex-col h-[600px] bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
      <div className="bg-gray-50 p-4 border-b border-gray-100 font-medium text-gray-700 flex items-center gap-2">
        <Bot className="w-5 h-5 text-blue-600" /> Assistant
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((m, i) => (
          <div
            key={i}
            className={`flex ${m.sender === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-[80%] p-3 rounded-2xl text-sm ${
                m.sender === "user"
                  ? "bg-blue-600 text-white rounded-tr-none"
                  : "bg-gray-100 text-gray-800 rounded-tl-none"
              }`}
            >
              {m.text}
            </div>
          </div>
        ))}
      </div>

      <div className="p-4 border-t border-gray-100 flex gap-2">
        <input
          className="flex-1 border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
          placeholder="Type a variation (e.g., 'Change Lobby tiles to Granite')..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={(e) => e.key === "Enter" && send()}
        />
        <button
          onClick={send}
          className="bg-blue-600 text-white p-2 rounded-lg hover:bg-blue-700"
        >
          <Send className="w-5 h-5" />
        </button>
      </div>
    </div>
  );
};

export default Chat;
