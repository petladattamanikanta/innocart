export function getApiUrl(path) {
  const baseUrl = import.meta.env.VITE_BACKEND_URL || '';
  const cleanPath = path.startsWith('/') ? path : `/${path}`;
  return `${baseUrl.replace(/\/$/, '')}${cleanPath}`;
}
