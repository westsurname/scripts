const SERVER_DOMAIN = window.location.hostname;
const IS_DEVELOPMENT = process.env.NODE_ENV === 'development';

export const getApiUrl = (path: string): string => {
  if (IS_DEVELOPMENT) {
    return `http://0.0.0.0:8000${path}`;
  }
  return `${window.location.protocol}//${SERVER_DOMAIN}${path}`;
};

export const getWebSocketUrl = (path: string): string => {
  if (IS_DEVELOPMENT) {
    return `ws://0.0.0.0:8000${path}`;
  }
  return `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${SERVER_DOMAIN}${path}`;
}; 