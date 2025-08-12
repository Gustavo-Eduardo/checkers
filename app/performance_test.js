// Optimized MediaPipe Performance Test
console.log('⚡ Testing Optimized MediaPipe Performance');

window.performanceTest = {
  startTime: null,
  frameCount: 0,
  gestureCount: 0,
  lastGesture: 'none',
  
  startTest() {
    console.log('🚀 Starting performance test...');
    this.startTime = Date.now();
    this.frameCount = 0;
    this.gestureCount = 0;
    
    // Switch to vision mode
    const visionRadio = document.querySelector('input[value="vision"]');
    if (visionRadio) {
      visionRadio.checked = true;
      visionRadio.dispatchEvent(new Event('change'));
    }
    
    // Start camera after a brief delay
    setTimeout(() => {
      const cameraBtn = document.getElementById('btn-toggle-camera');
      if (cameraBtn && cameraBtn.textContent.includes('Start')) {
        cameraBtn.click();
        console.log('📹 Camera started');
      }
    }, 1000);
    
    // Monitor frame rate
    this.monitorFrameRate();
  },
  
  monitorFrameRate() {
    const originalUpdate = window.gameManager.updateCameraPreview.bind(window.gameManager);
    window.gameManager.updateCameraPreview = (frameBase64) => {
      this.frameCount++;
      
      // Calculate FPS every 30 frames
      if (this.frameCount % 30 === 0) {
        const elapsed = (Date.now() - this.startTime) / 1000;
        const fps = this.frameCount / elapsed;
        console.log(`📊 FPS: ${fps.toFixed(1)} | Frames: ${this.frameCount} | Time: ${elapsed.toFixed(1)}s`);
      }
      
      return originalUpdate(frameBase64);
    };
    
    // Monitor gestures
    const originalGesture = window.gameManager.updateGestureDisplay.bind(window.gameManager);
    window.gameManager.updateGestureDisplay = (handData) => {
      if (handData.gesture !== this.lastGesture) {
        this.gestureCount++;
        this.lastGesture = handData.gesture;
        console.log(`✋ Gesture: ${handData.gesture} (${Math.round(handData.confidence * 100)}%) | Total changes: ${this.gestureCount}`);
      }
      return originalGesture(handData);
    };
  },
  
  checkStatus() {
    const elapsed = (Date.now() - this.startTime) / 1000;
    const fps = this.frameCount / elapsed;
    
    console.log('📈 Performance Summary:');
    console.log(`⏱️  Total time: ${elapsed.toFixed(1)}s`);
    console.log(`🎬 Total frames: ${this.frameCount}`);
    console.log(`📊 Average FPS: ${fps.toFixed(1)}`);
    console.log(`✋ Gesture changes: ${this.gestureCount}`);
    console.log(`🎯 Target: 10-15 FPS for smooth operation`);
    
    if (fps >= 10) {
      console.log('✅ Performance: GOOD - Smooth detection');
    } else if (fps >= 5) {
      console.log('⚠️  Performance: OK - Usable but could be better');
    } else {
      console.log('❌ Performance: POOR - Too slow for smooth use');
    }
  },
  
  testGestures() {
    console.log('🤏 Gesture Recognition Test:');
    console.log('Try these gestures:');
    console.log('👉 Point with index finger (hold still for 1 second)');
    console.log('✊ Make a fist (grab gesture)');
    console.log('✋ Open hand (release gesture)');
    console.log('👋 Move hand around (hover gesture)');
  },
  
  runFullTest() {
    this.startTest();
    
    setTimeout(() => {
      this.testGestures();
    }, 3000);
    
    setTimeout(() => {
      this.checkStatus();
    }, 30000);
  }
};

// Auto-start the test
setTimeout(() => {
  console.log('🎬 Starting optimized MediaPipe test...');
  window.performanceTest.runFullTest();
}, 1000);