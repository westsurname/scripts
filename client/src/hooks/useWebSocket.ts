import { useEffect, useRef, useState } from 'react';

const getWebSocketUrl = () => {
  const wsProtocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
  return `${wsProtocol}://${window.location.host}/ws`;
};

const useWebSocket = (url: string, onMessage: (data: any) => void) => {
  const [connectionStatus, setConnectionStatus] = useState<string>('Connecting...');
  const ws = useRef<WebSocket | null>(null);
  const reconnectTimeout = useRef<NodeJS.Timeout>();
  const pingInterval = useRef<NodeJS.Timeout>();
  const wsUrl = getWebSocketUrl();

  useEffect(() => {
    let mounted = true;

    const connect = () => {
      if (!mounted) return;
      if (ws.current?.readyState === WebSocket.OPEN) return;

      ws.current = new WebSocket(wsUrl);

      ws.current.onopen = () => {
        if (!mounted) return;
        setConnectionStatus('Connected');
        if (pingInterval.current) clearInterval(pingInterval.current);
        pingInterval.current = setInterval(() => {
          if (ws.current?.readyState === WebSocket.OPEN) {
            ws.current.send(JSON.stringify({ type: 'ping' }));
          }
        }, 30000);
      };

      ws.current.onclose = () => {
        if (!mounted) return;
        setConnectionStatus('Reconnecting...');
        if (pingInterval.current) clearInterval(pingInterval.current);
        if (reconnectTimeout.current) clearTimeout(reconnectTimeout.current);
        reconnectTimeout.current = setTimeout(connect, 1000);
      };

      ws.current.onmessage = (event) => {
        if (!mounted) return;
        try {
          const data = JSON.parse(event.data);
          console.log('WebSocket message received:', data);
          onMessage(data);
        } catch (error) {
          console.error('Error parsing message:', error);
        }
      };
    };

    connect();

    return () => {
      mounted = false;
      if (pingInterval.current) clearInterval(pingInterval.current);
      if (reconnectTimeout.current) clearTimeout(reconnectTimeout.current);
      if (ws.current) {
        ws.current.close();
        ws.current = null;
      }
    };
  }, [wsUrl, onMessage]);

  return connectionStatus;
};

export default useWebSocket; 