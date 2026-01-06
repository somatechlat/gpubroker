const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:28080/ws';

export interface PriceUpdateMessage {
  offer_id: string;
  external_id?: string;
  gpu_type: string;
  region: string;
  new_price: number;
  old_price?: number;
  timestamp: string;
}

type PriceUpdateCallback = (data: PriceUpdateMessage) => void;

let socket: WebSocket | null = null;
let callbacks: PriceUpdateCallback[] = [];

export function connectPriceStream(onUpdate: PriceUpdateCallback): () => void {
  callbacks.push(onUpdate);

  if (!socket || socket.readyState === WebSocket.CLOSED) {
    try {
      socket = new WebSocket(WS_URL + '/prices');
      socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          callbacks.forEach(cb => cb(data));
        } catch (e) {
          console.error('Error parsing WebSocket message:', e);
        }
      };
      socket.onerror = (error) => {
        console.error('WebSocket error:', error);
      };
      socket.onclose = () => {
        console.log('WebSocket closed, reconnecting in 5s...');
        setTimeout(() => {
          if (callbacks.length > 0) {
            connectPriceStream(callbacks[0]);
          }
        }, 5000);
      };
    } catch (error) {
      console.error('Error connecting to WebSocket:', error);
    }
  }

  return () => {
    callbacks = callbacks.filter(cb => cb !== onUpdate);
    if (callbacks.length === 0 && socket) {
      socket.close();
      socket = null;
    }
  };
}

export function disconnectPriceStream(): void {
  if (socket) {
    socket.close();
    socket = null;
  }
  callbacks = [];
}
