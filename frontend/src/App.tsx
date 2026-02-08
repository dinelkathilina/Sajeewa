import React from "react";
import MultiFileUploader from "./components/MultiFileUploader";
import Chat from "./components/Chat";
import { Hammer } from "lucide-react";

function App() {
  return (
    <div className="min-h-screen bg-gray-50 font-sans text-gray-900">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="bg-blue-600 p-2 rounded-lg">
              <Hammer className="text-white w-5 h-5" />
            </div>
            <h1 className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-600 to-indigo-600">
              Construction Variation AI
            </h1>
          </div>
          <div className="flex items-center gap-4 text-sm text-gray-500">
            <span>Project: High-Rise A017</span>
            <span className="px-2 py-1 bg-green-100 text-green-700 rounded-md text-xs font-semibold">
              ONLINE
            </span>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        {/* Step 1: Upload Files */}
        <section>
          <MultiFileUploader />
        </section>

        {/* Step 2: Workspace */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 h-[700px]">
          {/* Left: Chat Interface */}
          <section className="h-full">
            <Chat />
          </section>

          {/* Right: Proposal Preview (Placeholder for now) */}
          <section className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 flex flex-col items-center justify-center text-center">
            <div className="bg-gray-50 p-6 rounded-full mb-4">
              <FileText className="w-10 h-10 text-gray-300" />
            </div>
            <h3 className="text-lg font-medium text-gray-900">
              Proposal Preview
            </h3>
            <p className="text-gray-500 max-w-xs mt-2">
              The generated variation proposal and cost breakdown will appear
              here after you instruct the assistant.
            </p>
          </section>
        </div>
      </main>
    </div>
  );
}

// Icon for placeholder
function FileText({ className }: { className?: string }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
    >
      <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z" />
      <polyline points="14 2 14 8 20 8" />
      <line x1="16" x2="8" y1="13" y2="13" />
      <line x1="16" x2="8" y1="17" y2="17" />
      <line x1="10" x2="8" y1="9" y2="9" />
    </svg>
  );
}

export default App;
