// Use Vite's built-in mode detection or fallback to environment variable
const isDevelopment = import.meta.env.DEV || import.meta.env.VITE_ENV === 'development';

const API_BASE_URL = isDevelopment 
  ? (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api')
  : (import.meta.env.VITE_API_BASE_URL || '/api');

export { API_BASE_URL };