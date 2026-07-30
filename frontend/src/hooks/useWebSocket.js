import { useEffect, useRef, useState, useCallback } from 'react';

export function useWebSocket(cartId, onMessage) {
  const [isConnected, setIsConnected] = useState(false);
  const [isReconnecting, setIsReconnecting] = useState(false);
  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);

  const connect = useCallback(() => {
    if (!cartId) return;

    // Use cloud VITE_WS_URL if set, else construct from location or fallback to Production Render WS
    let wsUrl = import.meta.env.VITE_WS_URL;
    if (!wsUrl) {
      if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
        wsUrl = `ws://127.0.0.1:8000/ws/cart/${cartId}`;
      } else {
        wsUrl = `wss://innocart-backend.onrender.com/ws/cart/${cartId}`;
      }
    } else {
      if (!wsUrl.endsWith(`/ws/cart/${cartId}`)) {
        wsUrl = `${wsUrl.replace(/\/$/, '')}/ws/cart/${cartId}`;
      }
    }

    console.log(`Connecting WebSocket to ${wsUrl}...`);
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log(`WebSocket connected for cart ${cartId}`);
      setIsConnected(true);
      setIsReconnecting(false);
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (onMessage) onMessage(data);
      } catch (err) {
        console.error('Error parsing WS message:', err);
      }
    };

    ws.onclose = () => {
      console.warn(`WebSocket closed for cart ${cartId}. Scheduling reconnect...`);
      setIsConnected(false);
      setIsReconnecting(true);
      reconnectTimeoutRef.current = setTimeout(() => {
        connect();
      }, 2000);
    };

    ws.onerror = (err) => {
      console.error('WebSocket error:', err);
      ws.close();
    };
  }, [cartId, onMessage]);

  useEffect(() => {
    connect();
    return () => {
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
      if (wsRef.current) wsRef.current.close();
    };
  }, [connect]);

  const send = useCallback((data) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data));
    }
  }, []);

  return { isConnected, isReconnecting, send };
}
