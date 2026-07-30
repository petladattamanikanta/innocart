const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || "https://innocart-backend.onrender.com";

export const getApiUrl = (endpoint) => {
  const cleanEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
  return `${BACKEND_URL}/api${cleanEndpoint}`;
};

export const getMobileApiUrl = (endpoint) => {
  const cleanEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
  return `${BACKEND_URL}/api/mobile${cleanEndpoint}`;
};

