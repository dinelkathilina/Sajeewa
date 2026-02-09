import { useNavigate } from "react-router-dom";
import {
  MessageSquare,
  Calendar,
  CheckCircle,
  XCircle,
  ArrowLeft,
} from "lucide-react";

const SessionsPage = () => {
  const navigate = useNavigate();

  // Mock sessions data - in real app, fetch from API
  const sessions = [
    {
      id: 1,
      name: "Guard Stones Variation",
      status: "active",
      created_at: "2 hours ago",
      messages: 12,
    },
    {
      id: 2,
      name: "Concrete Quality Change",
      status: "archived",
      created_at: "1 day ago",
      messages: 8,
    },
  ];

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "active":
        return (
          <span className="px-3 py-1 bg-green-100 text-green-800 rounded-full text-sm font-medium flex items-center space-x-1">
            <CheckCircle className="w-4 h-4" />
            <span>Active</span>
          </span>
        );
      case "archived":
        return (
          <span className="px-3 py-1 bg-gray-100 text-gray-800 rounded-full text-sm font-medium">
            Archived
          </span>
        );
      case "closed":
        return (
          <span className="px-3 py-1 bg-red-100 text-red-800 rounded-full text-sm font-medium flex items-center space-x-1">
            <XCircle className="w-4 h-4" />
            <span>Closed</span>
          </span>
        );
      default:
        return null;
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <button
                onClick={() => navigate("/")}
                className="text-gray-600 hover:text-gray-900"
              >
                <ArrowLeft className="w-6 h-6" />
              </button>
              <h1 className="text-2xl font-bold text-gray-900">My Sessions</h1>
            </div>
            <button onClick={() => navigate("/upload")} className="btn-primary">
              New Evaluation
            </button>
          </div>
        </div>
      </header>

      {/* Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Filter Tabs */}
        <div className="mb-6 flex items-center space-x-4">
          <button className="px-4 py-2 bg-blue-600 text-white rounded-lg font-medium">
            All
          </button>
          <button className="px-4 py-2 bg-white text-gray-700 rounded-lg font-medium hover:bg-gray-50">
            Active
          </button>
          <button className="px-4 py-2 bg-white text-gray-700 rounded-lg font-medium hover:bg-gray-50">
            Archived
          </button>
        </div>

        {/* Sessions List */}
        {sessions.length === 0 ? (
          <div className="card text-center py-12">
            <MessageSquare className="w-16 h-16 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-gray-900 mb-2">
              No Sessions Yet
            </h3>
            <p className="text-gray-600 mb-6">
              Start your first variation evaluation
            </p>
            <button onClick={() => navigate("/upload")} className="btn-primary">
              Start New Evaluation
            </button>
          </div>
        ) : (
          <div className="space-y-4">
            {sessions.map((session) => (
              <div
                key={session.id}
                className="card hover:shadow-xl transition-shadow"
              >
                <div className="flex items-center justify-between">
                  <div className="flex-1">
                    <div className="flex items-center space-x-3 mb-2">
                      <h3 className="text-lg font-semibold text-gray-900">
                        {session.name}
                      </h3>
                      {getStatusBadge(session.status)}
                    </div>
                    <div className="flex items-center space-x-6 text-sm text-gray-600">
                      <div className="flex items-center space-x-2">
                        <Calendar className="w-4 h-4" />
                        <span>Created {session.created_at}</span>
                      </div>
                      <div className="flex items-center space-x-2">
                        <MessageSquare className="w-4 h-4" />
                        <span>{session.messages} messages</span>
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center space-x-3">
                    {session.status === "active" ? (
                      <>
                        <button
                          onClick={() => navigate(`/chat/${session.id}`)}
                          className="btn-primary"
                        >
                          Continue
                        </button>
                        <button className="btn-secondary">Close</button>
                      </>
                    ) : (
                      <button className="btn-secondary">View Details</button>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default SessionsPage;
