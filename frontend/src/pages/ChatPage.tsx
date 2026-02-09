import { useState, useEffect, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useApp } from "../context/AppContext";
import { createSession, sendMessage, getSession } from "../services/api";
import { Send, Loader, FileText, ArrowLeft, RotateCcw } from "lucide-react";

const ChatPage = () => {
  const { sessionId } = useParams<{ sessionId: string }>();
  const navigate = useNavigate();
  const {
    currentProject,
    setCurrentSession,
    messages,
    addMessage,
    setMessages,
    setProposal,
    loading,
    setLoading,
  } = useApp();

  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (sessionId) {
      loadSession();
    }
  }, [sessionId]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const loadSession = async () => {
    if (!sessionId) return;

    setLoading(true);
    try {
      const session = await getSession(parseInt(sessionId));
      setCurrentSession({
        id: session.session_id,
        session_key: session.session_key || "",
        status: session.status,
        created_at: session.created_at || new Date().toISOString(),
      });
      if (session.conversation_history) {
        setMessages(session.conversation_history);
      }
    } catch (err) {
      console.error("Failed to load session:", err);
    } finally {
      setLoading(false);
    }
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const handleSend = async () => {
    if (!input.trim() || !currentProject || !sessionId) return;

    const userMessage = {
      role: "user" as const,
      content: input,
      timestamp: new Date().toISOString(),
    };

    addMessage(userMessage);
    setInput("");
    setIsTyping(true);

    try {
      const response = await sendMessage(
        input,
        currentProject.id,
        parseInt(sessionId),
      );

      const aiMessage = {
        role: "ai" as const,
        content: response.reply || "No response",
        timestamp: new Date().toISOString(),
      };

      addMessage(aiMessage);

      // Check if proposal was generated
      if (response.proposal) {
        setProposal(response.proposal);
      }
    } catch (err: any) {
      const errorMessage = {
        role: "ai" as const,
        content: `Error: ${err.response?.data?.detail || "Failed to get response"}`,
        timestamp: new Date().toISOString(),
      };
      addMessage(errorMessage);
    } finally {
      setIsTyping(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };
  const handleNewEvaluation = async () => {
    if (!currentProject) return;

    setLoading(true);
    try {
      const result = await createSession(currentProject.id);
      if (result.session_id) {
        setMessages([]);
        setProposal(null);
        setCurrentSession({
          id: result.session_id,
          session_key: result.session_key,
          status: result.status,
          created_at: new Date().toISOString(),
        });
        navigate(`/chat/${result.session_id}`);
      }
    } catch (err) {
      console.error("Failed to reset evaluation:", err);
      alert("Failed to start a new evaluation. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 flex flex-col">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <button
                onClick={() => navigate("/")}
                className="text-gray-600 hover:text-gray-900"
              >
                <ArrowLeft className="w-6 h-6" />
              </button>
              <div>
                <h1 className="text-xl font-bold text-gray-900">
                  Variation Evaluation Chat
                </h1>
                {currentProject && (
                  <p className="text-sm text-gray-600">
                    {currentProject.boq_items} BOQ items •{" "}
                    {currentProject.schedule_tasks} activities
                  </p>
                )}
              </div>
            </div>
            <div className="flex items-center space-x-4">
              <button
                onClick={handleNewEvaluation}
                disabled={loading}
                className="flex items-center space-x-2 px-4 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg transition-colors disabled:opacity-50"
              >
                <RotateCcw
                  className={`w-4 h-4 ${loading ? "animate-spin" : ""}`}
                />
                <span className="text-sm font-medium">New Evaluation</span>
              </button>
              <span className="px-3 py-1 bg-green-100 text-green-800 rounded-full text-sm font-medium">
                Active
              </span>
            </div>
          </div>
        </div>
      </header>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          {messages.length === 0 && !loading && (
            <div className="text-center py-12">
              <FileText className="w-16 h-16 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                Start Your Variation Evaluation
              </h3>
              <p className="text-gray-600 mb-4">
                I'll guide you through the FIDIC variation workflow
              </p>
              <div className="max-w-md mx-auto bg-blue-50 border border-blue-200 rounded-lg p-4 text-left">
                <p className="text-sm text-blue-900 font-medium mb-2">
                  I can help you with:
                </p>
                <ul className="text-sm text-blue-800 space-y-1">
                  <li>• Selecting the appropriate FIDIC variation type</li>
                  <li>• Collecting variation details</li>
                  <li>• Evaluating cost and time impacts</li>
                  <li>• Generating professional proposals</li>
                </ul>
              </div>
            </div>
          )}

          {messages.map((message, index) => (
            <div
              key={index}
              className={`mb-4 flex ${message.role === "user" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-3xl rounded-lg px-4 py-3 ${
                  message.role === "user"
                    ? "bg-blue-600 text-white"
                    : "bg-white shadow-md text-gray-900"
                }`}
              >
                <p className="whitespace-pre-wrap">{message.content}</p>
                <p
                  className={`text-xs mt-2 ${message.role === "user" ? "text-blue-100" : "text-gray-500"}`}
                >
                  {new Date(message.timestamp).toLocaleTimeString()}
                </p>
              </div>
            </div>
          ))}

          {isTyping && (
            <div className="mb-4 flex justify-start">
              <div className="bg-white shadow-md rounded-lg px-4 py-3">
                <div className="flex items-center space-x-2">
                  <Loader className="w-4 h-4 animate-spin text-blue-600" />
                  <span className="text-gray-600">AI is typing...</span>
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input Area */}
      <div className="bg-white border-t border-gray-200 shadow-lg">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-end space-x-4">
            <div className="flex-1">
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Type your message... (Press Enter to send)"
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none resize-none"
                rows={3}
                disabled={loading}
              />
            </div>
            <button
              onClick={handleSend}
              disabled={!input.trim() || loading}
              className="btn-primary px-6 py-3 disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
            >
              <Send className="w-5 h-5" />
              <span>Send</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ChatPage;
