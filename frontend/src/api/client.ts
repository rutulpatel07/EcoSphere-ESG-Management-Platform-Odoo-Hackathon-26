import axios from "axios";

// Base URL is read from the Vite environment. Falls back to the local backend.
const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000/api";

export const apiClient = axios.create({
  baseURL: API_BASE,
  headers: {
    "Content-Type": "application/json",
  },
});

// Attach a bearer token from localStorage if present.
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem("ecosphere_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export default apiClient;
