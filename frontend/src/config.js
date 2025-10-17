// Конфигурация для работы в локальной сети
// Backend URL определяется автоматически на основе текущего hostname

const getBackendURL = () => {
  // Если есть переменная окружения - использовать её
  if (process.env.REACT_APP_BACKEND_URL) {
    return process.env.REACT_APP_BACKEND_URL;
  }
  
  // Иначе использовать текущий hostname с портом 8001
  const protocol = window.location.protocol;
  const hostname = window.location.hostname;
  
  return `${protocol}//${hostname}:8001`;
};

export const API_BASE_URL = getBackendURL();
export const WS_BASE_URL = API_BASE_URL.replace('http', 'ws');

console.log('Backend URL:', API_BASE_URL);
console.log('WebSocket URL:', WS_BASE_URL);
