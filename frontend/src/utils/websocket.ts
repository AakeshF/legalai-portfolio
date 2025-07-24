/**
 * WebSocket utilities with auto-reconnection
 * Implements backend team's recommendations
 */

export class ReconnectingWebSocket {
  private ws: WebSocket | null = null;
  private url: string;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000; // Start with 1 second
  private listeners: Map<string, Set<(data: any) => void>> = new Map();
  private isIntentionallyClosed = false;

  constructor(url: string) {
    this.url = url;
    this.connect();
  }

  private connect(): void {
    try {
      this.ws = new WebSocket(this.url);
      
      this.ws.onopen = () => {
        this.reconnectAttempts = 0;
        this.reconnectDelay = 1000;
      };

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          this.emit(data.type || 'message', data);
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error);
        }
      };

      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error);
      };

      this.ws.onclose = () => {
        if (!this.isIntentionallyClosed) {
          this.handleReconnect();
        }
      };
    } catch (error) {
      console.error('Failed to create WebSocket:', error);
      this.handleReconnect();
    }
  }

  private handleReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('Max reconnection attempts reached');
      this.emit('maxReconnectAttemptsReached', null);
      return;
    }

    this.reconnectAttempts++;
    const delay = Math.min(this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1), 30000);
    
    // Reconnecting with exponential backoff
    
    setTimeout(() => {
      this.connect();
    }, delay);
  }

  public send(data: any): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    } else {
      console.error('WebSocket is not connected');
    }
  }

  public on(event: string, callback: (data: any) => void): void {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, new Set());
    }
    this.listeners.get(event)!.add(callback);
  }

  public off(event: string, callback: (data: any) => void): void {
    this.listeners.get(event)?.delete(callback);
  }

  private emit(event: string, data: any): void {
    this.listeners.get(event)?.forEach(callback => callback(data));
  }

  public close(): void {
    this.isIntentionallyClosed = true;
    this.ws?.close();
    this.ws = null;
  }

  public reconnect(): void {
    this.isIntentionallyClosed = false;
    this.reconnectAttempts = 0;
    this.ws?.close();
    this.connect();
  }
}

/**
 * Create WebSocket connection for prompt review updates
 */
export function createPromptReviewWebSocket(promptId: string): ReconnectingWebSocket {
  const wsUrl = process.env.REACT_APP_WS_URL || 'ws://localhost:8000';
  return new ReconnectingWebSocket(`${wsUrl}/api/prompts/ws/${promptId}`);
}