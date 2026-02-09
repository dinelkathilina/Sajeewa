import axios from "axios";

const API_BASE_URL = "http://localhost:8000";

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

// Health & Info
export const getHealth = async () => {
  const response = await api.get("/health");
  return response.data;
};

export const getVariationTypes = async () => {
  const response = await api.get("/variation-types");
  return response.data;
};

// File Upload
export const uploadFiles = async (
  files: {
    boq?: File;
    breakdown?: File;
    schedule?: File;
  },
  onProgress?: (progress: number) => void,
) => {
  const formData = new FormData();

  if (files.boq) formData.append("boq", files.boq);
  if (files.breakdown) formData.append("breakdown", files.breakdown);
  if (files.schedule) formData.append("schedule", files.schedule);

  const response = await api.post("/upload/files", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
    onUploadProgress: (progressEvent) => {
      if (progressEvent.total && onProgress) {
        const percentCompleted = Math.round(
          (progressEvent.loaded * 100) / progressEvent.total,
        );
        onProgress(percentCompleted);
      }
    },
  });

  return response.data;
};

export const uploadAdditionalFiles = async (
  files: File[],
  variationId: number,
  onProgress?: (progress: number) => void,
) => {
  const formData = new FormData();
  files.forEach((file) => formData.append("files", file));
  formData.append("variation_id", variationId.toString());

  const response = await api.post("/upload/additional-files", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
    onUploadProgress: (progressEvent) => {
      if (progressEvent.total && onProgress) {
        const percentCompleted = Math.round(
          (progressEvent.loaded * 100) / progressEvent.total,
        );
        onProgress(percentCompleted);
      }
    },
  });

  return response.data;
};

// Chat
export const sendMessage = async (
  message: string,
  projectId: number,
  sessionId: number,
) => {
  const response = await api.post("/chat", {
    message,
    project_id: projectId,
    session_id: sessionId,
  });
  return response.data;
};

// Sessions
export const createSession = async (projectId: number, metadata?: any) => {
  const response = await api.post("/session/create", {
    project_id: projectId,
    metadata,
  });
  return response.data;
};

export const getSession = async (sessionId: number) => {
  const response = await api.get(`/session/${sessionId}`);
  return response.data;
};

export const continueSession = async (sessionId: number) => {
  const response = await api.post(`/session/${sessionId}/continue`);
  return response.data;
};

export const closeSession = async (sessionId: number) => {
  const response = await api.post(`/session/${sessionId}/close`);
  return response.data;
};

// Validation & Management
export const getVariation = async (variationId: number) => {
  const response = await api.get(`/variation/${variationId}`);
  return response.data;
};

export const updateVariationDetail = async (variationId: number, detailId: number, updates: any) => {
  const response = await api.put(`/variation/${variationId}/details/${detailId}`, updates);
  return response.data;
};

export const updateVariationStatus = async (variationId: number, status: string) => {
  const response = await api.post(`/variation/${variationId}/status`, { status });
  return response.data;
};

export const validateVariation = async (variationId: number) => {
  const response = await api.post(`/variation/validate/${variationId}`);
  return response.data;
};

// PDF Generation
export const generatePDF = async (proposalData: any) => {
  const response = await api.post("/generate-pdf", proposalData, {
    responseType: "blob",
  });
  return response.data;
};

export default api;
