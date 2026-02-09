import React, {
  createContext,
  useContext,
  useState,
  type ReactNode,
} from "react";

interface Project {
  id: number;
  name: string;
  boq_items?: number;
  rate_breakdowns?: number;
  schedule_tasks?: number;
  critical_path_activities?: number;
}

interface Session {
  id: number;
  session_key: string;
  status: string;
  created_at: string;
  session_metadata?: any;
}

interface Message {
  role: "user" | "ai";
  content: string;
  timestamp: string;
}

interface Proposal {
  item_id?: number;
  original_item?: string;
  new_item?: string;
  cost_impact?: number;
  time_impact?: number;
  variation_type?: string;
  eot_breakdown?: {
    justification?: string;
    affected_activity?: any;
    original_project_duration?: number;
    new_project_duration?: number;
    is_on_critical_path?: boolean;
  };
  gantt_chart_data?: {
    id: string;
    name: string;
    start_day: number;
    end_day: number;
    duration: number;
    is_critical: boolean;
    total_float: number;
  }[];
}

interface AppState {
  currentProject: Project | null;
  currentSession: Session | null;
  messages: Message[];
  proposal: Proposal | null;
  loading: boolean;
  error: string | null;
  uploadProgress: number;
}

interface AppContextType extends AppState {
  setCurrentProject: (project: Project | null) => void;
  setCurrentSession: (session: Session | null) => void;
  addMessage: (message: Message) => void;
  setMessages: (messages: Message[]) => void;
  setProposal: (proposal: Proposal | null) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  setUploadProgress: (progress: number) => void;
  resetState: () => void;
}

const AppContext = createContext<AppContextType | undefined>(undefined);

const initialState: AppState = {
  currentProject: null,
  currentSession: null,
  messages: [],
  proposal: null,
  loading: false,
  error: null,
  uploadProgress: 0,
};

export const AppProvider: React.FC<{ children: ReactNode }> = ({
  children,
}) => {
  const [state, setState] = useState<AppState>(initialState);

  const setCurrentProject = (project: Project | null) => {
    setState((prev) => ({ ...prev, currentProject: project }));
  };

  const setCurrentSession = (session: Session | null) => {
    setState((prev) => ({ ...prev, currentSession: session }));
  };

  const addMessage = (message: Message) => {
    setState((prev) => ({ ...prev, messages: [...prev.messages, message] }));
  };

  const setMessages = (messages: Message[]) => {
    setState((prev) => ({ ...prev, messages }));
  };

  const setProposal = (proposal: Proposal | null) => {
    setState((prev) => ({ ...prev, proposal }));
  };

  const setLoading = (loading: boolean) => {
    setState((prev) => ({ ...prev, loading }));
  };

  const setError = (error: string | null) => {
    setState((prev) => ({ ...prev, error }));
  };

  const setUploadProgress = (progress: number) => {
    setState((prev) => ({ ...prev, uploadProgress: progress }));
  };

  const resetState = () => {
    setState(initialState);
  };

  const value: AppContextType = {
    ...state,
    setCurrentProject,
    setCurrentSession,
    addMessage,
    setMessages,
    setProposal,
    setLoading,
    setError,
    setUploadProgress,
    resetState,
  };

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
};

export const useApp = () => {
  const context = useContext(AppContext);
  if (context === undefined) {
    throw new Error("useApp must be used within an AppProvider");
  }
  return context;
};
