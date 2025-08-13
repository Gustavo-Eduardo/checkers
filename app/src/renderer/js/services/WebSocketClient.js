class WebSocketClient {
  constructor(url = 'ws://localhost:8765') {
    this.url = url;
    this.ws = null;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
    this.listeners = new Map();
    this.connected = false;
    this.reconnectTimeout = null;
  }

  connect() {
    return new Promise((resolve, reject) => {
      try {
        this.ws = new WebSocket(this.url);
        
        this.ws.onopen = () => {
          console.log('Connected to backend WebSocket');
          this.connected = true;
          this.reconnectAttempts = 0;
          this.updateStatus('connected');
          resolve();
        };
        
        this.ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            this.handleMessage(data);
          } catch (error) {
            console.error('Error parsing WebSocket message:', error);
          }
        };
        
        this.ws.onerror = (error) => {
          console.error('WebSocket error:', error);
          this.connected = false;
          this.updateStatus('error');
          reject(error);
        };
        
        this.ws.onclose = (event) => {
          console.log('WebSocket connection closed:', event.code, event.reason);
          this.connected = false;
          this.updateStatus('disconnected');
          this.attemptReconnect();
        };
      } catch (error) {
        console.error('Failed to create WebSocket connection:', error);
        this.updateStatus('error');
        reject(error);
      }
    });
  }

  handleMessage(data) {
    const { type, data: payload } = data;
    
    // LOG: All received messages for debugging
    if (type === 'piece_selected' || type === 'selection_cleared' || type === 'move_result') {
      console.warn(`FRONTEND: *** RECEIVED CRITICAL MESSAGE *** Type: ${type}, Payload:`, payload);
    } else {
      console.log(`FRONTEND: Received message - Type: ${type}`);
    }
    
    if (this.listeners.has(type)) {
      this.listeners.get(type).forEach(callback => {
        try {
          callback(payload);
        } catch (error) {
          console.error(`Error in ${type} listener:`, error);
        }
      });
    }
    
    // Also trigger 'any' listeners for all message types
    if (this.listeners.has('any')) {
      this.listeners.get('any').forEach(callback => {
        try {
          callback(data);
        } catch (error) {
          console.error('Error in any listener:', error);
        }
      });
    }
  }

  on(event, callback) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, []);
    }
    this.listeners.get(event).push(callback);
  }

  off(event, callback) {
    if (this.listeners.has(event)) {
      const callbacks = this.listeners.get(event);
      const index = callbacks.indexOf(callback);
      if (index !== -1) {
        callbacks.splice(index, 1);
      }
    }
  }

  send(type, data = {}) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      try {
        this.ws.send(JSON.stringify({ type, ...data }));
        return true;
      } catch (error) {
        console.error('Error sending WebSocket message:', error);
        return false;
      }
    } else {
      console.warn('WebSocket not connected, cannot send message:', type);
      return false;
    }
  }

  attemptReconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('Max reconnection attempts reached');
      this.updateStatus('failed');
      return;
    }

    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
    }

    this.reconnectAttempts++;
    const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 30000);
    
    console.log(`Reconnecting in ${delay}ms... (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
    this.updateStatus('reconnecting');
    
    this.reconnectTimeout = setTimeout(() => {
      this.connect().catch(() => {
        // Reconnection failed, will attempt again through onclose
      });
    }, delay);
  }

  updateStatus(status) {
    const statusElement = document.getElementById('ws-status');
    if (statusElement) {
      statusElement.textContent = status.charAt(0).toUpperCase() + status.slice(1);
      statusElement.className = `status-indicator ${status}`;
    }
  }

  disconnect() {
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }
    
    this.reconnectAttempts = this.maxReconnectAttempts; // Prevent reconnection
    
    if (this.ws) {
      this.ws.close(1000, 'Manual disconnect');
      this.ws = null;
    }
    
    this.connected = false;
    this.updateStatus('disconnected');
  }

  isConnected() {
    return this.connected && this.ws && this.ws.readyState === WebSocket.OPEN;
  }
}