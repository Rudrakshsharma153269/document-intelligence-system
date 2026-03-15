import React, { useState } from "react";
import { askQuestion } from "../api";

const ChatBox = () => {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);

  const handleSend = async (e) => {
    e.preventDefault();
    const question = input.trim();
    if (!question) return;

    const newMessages = [...messages, { role: "user", content: question }];
    setMessages(newMessages);
    setInput("");
    setLoading(true);
    try {
      const res = await askQuestion(question, newMessages);
      setMessages([
        ...newMessages,
        {
          role: "assistant",
          content: res.answer,
          sources: res.sources
        }
      ]);
    } catch (err) {
      console.error(err);
      setMessages([
        ...newMessages,
        { role: "assistant", content: "Something went wrong while generating the answer." }
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-white rounded shadow flex flex-col h-[500px]">
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {messages.map((m, idx) => (
          <div
            key={idx}
            className={`max-w-xl px-3 py-2 rounded text-sm ${
              m.role === "user" ? "ml-auto bg-blue-600 text-white" : "mr-auto bg-gray-100 text-gray-800"
            }`}
          >
            <div>{m.content}</div>
            {m.role === "assistant" && m.sources && m.sources.length > 0 && (
              <div className="mt-2 text-xs text-gray-600">
                Sources:{" "}
                {m.sources.map((s, i) => (
                  <span key={i} className="mr-1">
                    [Doc {s.doc_id}, Page {s.page}]
                  </span>
                ))}
              </div>
            )}
          </div>
        ))}
        {loading && <div className="text-xs text-gray-500">Thinking...</div>}
      </div>
      <form onSubmit={handleSend} className="border-t p-3 flex gap-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask a question about your documents..."
          className="flex-1 border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <button
          type="submit"
          disabled={loading}
          className="px-4 py-2 rounded bg-blue-600 text-white text-sm hover:bg-blue-700 disabled:bg-gray-300"
        >
          Send
        </button>
      </form>
    </div>
  );
};

export default ChatBox;

