import axios from "axios";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

const api = axios.create({
  baseURL: API_BASE_URL
});

// Attach JWT token automatically if present
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export const register = (email, password) =>
  api.post("/auth/register", { email, password }).then((res) => res.data);

export const login = (email, password) =>
  api
    .post(
      "/auth/login",
      new URLSearchParams({
        username: email,
        password
      }),
      {
        headers: { "Content-Type": "application/x-www-form-urlencoded" }
      }
    )
    .then((res) => res.data);

export const uploadDocument = (file) => {
  const formData = new FormData();
  formData.append("file", file);
  return api.post("/documents/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" }
  });
};

export const listDocuments = () =>
  api.get("/documents/list").then((res) => res.data);

export const askQuestion = (question, chatHistory) =>
  api.post("/chat/ask", { question, chat_history: chatHistory }).then((res) => res.data);

export default api;

