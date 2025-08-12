// Debug helper script for testing checkers app functionality
// Add this to browser console to test features

console.log('🔧 Checkers App Debug Helper Loaded');

window.debugApp = {
  // Test mouse mode
  testMouseMode() {
    console.log('🖱️ Testing Mouse Mode...');
    const mouseRadio = document.querySelector('input[value="mouse"]');
    if (mouseRadio) {
      mouseRadio.checked = true;
      mouseRadio.dispatchEvent(new Event('change'));
      console.log('✅ Mouse mode activated');
    } else {
      console.log('❌ Mouse mode radio not found');
    }
  },

  // Test timer
  testTimer() {
    console.log('⏱️ Testing Timer...');
    if (window.gameManager) {
      window.gameManager.startNewGame();
      console.log('✅ Timer should be running');
    } else {
      console.log('❌ GameManager not found');
    }
  },

  // Test camera
  testCamera() {
    console.log('📷 Testing Camera...');
    const cameraBtn = document.getElementById('btn-toggle-camera');
    if (cameraBtn) {
      cameraBtn.click();
      console.log('✅ Camera toggle clicked');
    } else {
      console.log('❌ Camera button not found');
    }
  },

  // Check game state
  checkGameState() {
    console.log('🎮 Checking Game State...');
    if (window.gameManager) {
      console.log('GameManager:', {
        connected: window.gameManager.wsClient?.isConnected(),
        gameState: window.gameManager.gameState,
        mouseMode: window.gameManager.board?.mouseMode,
        cameraActive: window.gameManager.cameraActive,
        timerRunning: !!window.gameManager.gameTimer
      });
    } else {
      console.log('❌ GameManager not found');
    }
  },

  // Test piece movement via code
  testMove() {
    console.log('🚀 Testing Move...');
    if (window.gameManager && window.gameManager.wsClient.isConnected()) {
      // Try to move a red piece
      window.gameManager.makeMove([2, 1], [3, 2]);
      console.log('✅ Move command sent');
    } else {
      console.log('❌ Not connected to backend');
    }
  },

  // Show all available debugging info
  fullDiagnosis() {
    console.log('🔍 Full App Diagnosis');
    this.checkGameState();
    
    // Check DOM elements
    const elements = {
      'Game Board': !!document.getElementById('game-board'),
      'Camera Preview': !!document.getElementById('camera-preview'),
      'Timer Display': !!document.getElementById('game-timer'),
      'Mouse Radio': !!document.querySelector('input[value="mouse"]'),
      'Vision Radio': !!document.querySelector('input[value="vision"]'),
      'Camera Button': !!document.getElementById('btn-toggle-camera')
    };
    
    console.log('DOM Elements:', elements);
    
    // Check WebSocket
    if (window.gameManager?.wsClient) {
      console.log('WebSocket:', {
        connected: window.gameManager.wsClient.isConnected(),
        url: window.gameManager.wsClient.url,
        readyState: window.gameManager.wsClient.ws?.readyState
      });
    }
    
    console.log('To test features, use:');
    console.log('- debugApp.testMouseMode()');
    console.log('- debugApp.testTimer()');
    console.log('- debugApp.testCamera()');
    console.log('- debugApp.testMove()');
  }
};

// Auto-run diagnosis
setTimeout(() => {
  window.debugApp.fullDiagnosis();
}, 2000);