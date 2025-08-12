// MediaPipe Hand Detection Test - paste this in browser console
console.log('🚀 MediaPipe Hand Detection Test');

window.mediapipeTest = {
  startTest() {
    console.log('📹 Starting MediaPipe test...');
    
    // Switch to vision mode
    const visionRadio = document.querySelector('input[value="vision"]');
    if (visionRadio) {
      visionRadio.checked = true;
      visionRadio.dispatchEvent(new Event('change'));
      console.log('✅ Switched to vision mode');
    }

    // Start camera
    setTimeout(() => {
      const cameraBtn = document.getElementById('btn-toggle-camera');
      if (cameraBtn && cameraBtn.textContent.includes('Start')) {
        cameraBtn.click();
        console.log('✅ Camera started');
      }
    }, 500);
  },

  checkStatus() {
    console.log('📊 MediaPipe Status Check:');
    
    const debugPanel = document.getElementById('debug-panel');
    if (debugPanel) {
      const content = debugPanel.textContent;
      console.log('Debug panel found:', content.includes('MediaPipe'));
      console.log('Detection method:', content.match(/Method: (\w+)/)?.[1] || 'None');
      console.log('Hand detected:', content.match(/Hand: (\w+)/)?.[1] || 'None');
      console.log('Confidence:', content.match(/Confidence: (\d+%)/)?.[1] || 'N/A');
      console.log('Fingers:', content.match(/Fingers Up: (\d+)/)?.[1] || 'N/A');
    } else {
      console.log('❌ Debug panel not found');
    }

    // Check camera preview
    const preview = document.getElementById('camera-preview');
    if (preview) {
      console.log('Camera preview size:', preview.width, 'x', preview.height);
    }
  },

  monitorDetection() {
    console.log('🔍 Monitoring MediaPipe detection for 30 seconds...');
    
    let detectionCount = 0;
    let gestureCount = 0;
    
    const originalGestureUpdate = window.gameManager.updateGestureDisplay.bind(window.gameManager);
    window.gameManager.updateGestureDisplay = function(handData) {
      detectionCount++;
      if (handData.gesture !== 'none') {
        gestureCount++;
        console.log(`👋 Gesture detected: ${handData.gesture} (confidence: ${Math.round(handData.confidence * 100)}%)`);
      }
      return originalGestureUpdate(handData);
    };

    setTimeout(() => {
      console.log(`📈 Detection Summary:`);
      console.log(`Total detections: ${detectionCount}`);
      console.log(`Gesture events: ${gestureCount}`);
      console.log(`Detection rate: ${(detectionCount / 30).toFixed(1)} per second`);
      
      // Restore original function
      window.gameManager.updateGestureDisplay = originalGestureUpdate;
    }, 30000);
  },

  runFullTest() {
    console.log('🧪 Running complete MediaPipe test...');
    this.startTest();
    
    setTimeout(() => this.checkStatus(), 3000);
    setTimeout(() => this.monitorDetection(), 5000);
  }
};

// Auto-start test
setTimeout(() => {
  console.log('🎬 Auto-starting MediaPipe test in 2 seconds...');
  window.mediapipeTest.runFullTest();
}, 2000);