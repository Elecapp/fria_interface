// src/utils/config.js

// Prende l'URL in base all'ambiente, o usa localhost 
export const API_HOST = import.meta.env.VITE_API_HOST || `${API_HOST}`;