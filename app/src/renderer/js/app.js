// Main application entry point
class CheckersApp {
  constructor() {
    this.gameManager = null;
    this.initialized = false;
  }

  async initialize() {
    if (this.initialized) return;

    try {
      console.log('Initializing Checkers App...');
      
      // Wait for DOM to be ready
      if (document.readyState !== 'complete') {
        await new Promise(resolve => {
          window.addEventListener('load', resolve);
        });
      }

      // Initialize game manager
      this.gameManager = new GameManager();
      window.gameManager = this.gameManager; // Make globally accessible

      // Connect to backend
      const connected = await this.gameManager.initialize();
      
      if (connected) {
        console.log('Application initialized successfully');
        this.setupGlobalEventListeners();
        this.initialized = true;
        
        // Show welcome message
        this.showWelcomeMessage();
      } else {
        console.error('Failed to initialize application');
        this.showErrorMessage();
      }

    } catch (error) {
      console.error('Error initializing application:', error);
      this.showErrorMessage();
    }
  }

  setupGlobalEventListeners() {
    // Handle window close
    window.addEventListener('beforeunload', () => {
      if (this.gameManager) {
        this.gameManager.destroy();
      }
    });

    // Handle keyboard shortcuts
    document.addEventListener('keydown', (e) => {
      this.handleKeyboardShortcuts(e);
    });

    // Handle modal close on ESC
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        const modal = document.getElementById('help-modal');
        if (modal && modal.style.display === 'block') {
          modal.style.display = 'none';
        }
      }
    });

    // Handle modal background click
    document.getElementById('help-modal').addEventListener('click', (e) => {
      if (e.target === e.currentTarget) {
        e.currentTarget.style.display = 'none';
      }
    });

    // FPS counter
    this.startFPSCounter();
  }

  handleKeyboardShortcuts(e) {
    // Don't handle shortcuts in input fields
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
      return;
    }

    switch (e.key) {
      case 'n':
      case 'N':
        if (e.ctrlKey || e.metaKey) {
          e.preventDefault();
          document.getElementById('btn-new-game').click();
        }
        break;
      
      case 'r':
      case 'R':
        if (e.ctrlKey || e.metaKey) {
          e.preventDefault();
          document.getElementById('btn-reset').click();
        }
        break;
      
      case 'c':
      case 'C':
        if (e.ctrlKey || e.metaKey) {
          e.preventDefault();
          document.getElementById('btn-toggle-camera').click();
        }
        break;
      
      case 'h':
      case 'H':
        if (!e.ctrlKey && !e.metaKey) {
          e.preventDefault();
          document.getElementById('btn-help').click();
        }
        break;
      
      case 'F1':
        e.preventDefault();
        document.getElementById('btn-help').click();
        break;
      
      case '1':
        document.querySelector('input[value="vision"]').click();
        break;
      
      case '2':
        document.querySelector('input[value="mouse"]').click();
        break;
    }
  }

  startFPSCounter() {
    let frameCount = 0;
    let lastTime = performance.now();
    
    const updateFPS = () => {
      frameCount++;
      const currentTime = performance.now();
      
      if (currentTime - lastTime >= 1000) {
        const fps = Math.round((frameCount * 1000) / (currentTime - lastTime));
        document.getElementById('fps-counter').textContent = `FPS: ${fps}`;
        
        frameCount = 0;
        lastTime = currentTime;
      }
      
      requestAnimationFrame(updateFPS);
    };
    
    updateFPS();
  }

  showWelcomeMessage() {
    const welcomeDiv = document.createElement('div');
    welcomeDiv.className = 'welcome-message';
    welcomeDiv.innerHTML = `
      <div class="welcome-content">
        <h2>Welcome to Vision Checkers!</h2>
        <p>🎯 Use hand gestures or mouse to play checkers</p>
        <p>📹 Start the camera to use gesture controls</p>
        <p>❓ Press F1 or click Help for instructions</p>
        <button onclick="this.parentElement.parentElement.remove()">Get Started</button>
      </div>
    `;
    
    document.body.appendChild(welcomeDiv);
    
    // Auto-hide after 10 seconds
    setTimeout(() => {
      if (welcomeDiv.parentNode) {
        welcomeDiv.remove();
      }
    }, 10000);
  }

  showErrorMessage() {
    const errorDiv = document.createElement('div');
    errorDiv.className = 'error-message';
    errorDiv.innerHTML = `
      <div class="error-content">
        <h2>⚠️ Connection Error</h2>
        <p>Could not connect to the game backend.</p>
        <p>Please make sure the backend server is running.</p>
        <div class="error-actions">
          <button onclick="location.reload()">Retry</button>
          <button onclick="window.electronAPI.restartBackend()">Restart Backend</button>
        </div>
      </div>
    `;
    
    document.body.appendChild(errorDiv);
  }

  // Utility methods for debugging
  debugInfo() {
    return {
      initialized: this.initialized,
      gameManager: !!this.gameManager,
      websocketConnected: this.gameManager?.wsClient?.isConnected(),
      gameState: this.gameManager?.gameState,
      electronAPI: !!window.electronAPI
    };
  }
}

// Global app instance
let app;

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', async () => {
  console.log('DOM loaded, initializing application...');
  
  app = new CheckersApp();
  window.checkersApp = app; // Make globally accessible for debugging
  
  await app.initialize();
});

// Handle any uncaught errors
window.addEventListener('error', (e) => {
  console.error('Uncaught error:', e.error);
});

window.addEventListener('unhandledrejection', (e) => {
  console.error('Unhandled promise rejection:', e.reason);
});

// Export for potential use
if (typeof module !== 'undefined' && module.exports) {
  module.exports = CheckersApp;
}