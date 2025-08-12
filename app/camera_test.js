// Quick camera test script - paste this in browser console
console.log('🎥 Camera Test Helper');

window.cameraTest = {
  startCamera() {
    console.log('📹 Starting camera...');
    const btn = document.getElementById('btn-toggle-camera');
    if (btn && btn.textContent.includes('Start')) {
      btn.click();
      console.log('✅ Camera start button clicked');
    } else {
      console.log('❌ Camera button not found or already started');
    }
  },

  checkStatus() {
    console.log('📊 Camera Status Check:');
    
    // Check camera preview element
    const preview = document.getElementById('camera-preview');
    console.log('Preview element:', !!preview);
    if (preview) {
      console.log('Preview size:', preview.width, 'x', preview.height);
    }

    // Check debug panel
    const debugPanel = document.getElementById('debug-panel');
    console.log('Debug panel:', !!debugPanel);
    if (debugPanel) {
      console.log('Debug content:', debugPanel.textContent.substring(0, 100) + '...');
    }

    // Check WebSocket status
    if (window.gameManager?.wsClient) {
      console.log('WebSocket connected:', window.gameManager.wsClient.isConnected());
      console.log('Camera active:', window.gameManager.cameraActive);
    }
  },

  monitorFrames() {
    console.log('🔍 Monitoring camera frames...');
    let frameCount = 0;
    
    const originalUpdate = window.gameManager.updateCameraPreview.bind(window.gameManager);
    window.gameManager.updateCameraPreview = function(frameBase64) {
      frameCount++;
      console.log(`📸 Frame ${frameCount}: ${frameBase64 ? frameBase64.length : 0} bytes`);
      return originalUpdate(frameBase64);
    };

    setTimeout(() => {
      console.log(`📊 Received ${frameCount} frames in 10 seconds`);
    }, 10000);
  }
};

// Auto-check status
setTimeout(() => {
  window.cameraTest.checkStatus();
}, 1000);