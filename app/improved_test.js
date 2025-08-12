// Test the improved MediaPipe system
console.log('🚀 Testing Improved MediaPipe System');

window.improvedTest = {
  gestureChanges: 0,
  lastGesture: 'none',
  startTime: Date.now(),
  
  startTest() {
    console.log('📋 Improvements Made:');
    console.log('✅ Camera horizontally mirrored');
    console.log('✅ Faster pointing recognition (8 frames vs 15)');
    console.log('✅ More sensitive movement detection (15px vs 20px)');
    console.log('✅ Immediate pointing without waiting');
    console.log('✅ Faster action cooldown (0.3s vs 0.5s)');
    console.log('✅ Increased frame rate (20 FPS vs 15 FPS)');
    console.log('✅ Processing every frame (no skipping)');
    console.log('');
    
    // Start vision mode
    const visionRadio = document.querySelector('input[value="vision"]');
    if (visionRadio) {
      visionRadio.checked = true;
      visionRadio.dispatchEvent(new Event('change'));
    }
    
    // Start camera
    setTimeout(() => {
      const cameraBtn = document.getElementById('btn-toggle-camera');
      if (cameraBtn && cameraBtn.textContent.includes('Start')) {
        cameraBtn.click();
        console.log('📹 Camera started with mirroring');
      }
    }, 1000);
    
    this.monitorResponsiveness();
  },
  
  monitorResponsiveness() {
    const originalGesture = window.gameManager.updateGestureDisplay.bind(window.gameManager);
    window.gameManager.updateGestureDisplay = (handData) => {
      const gesture = handData.gesture;
      
      if (gesture !== this.lastGesture) {
        this.gestureChanges++;
        const elapsed = (Date.now() - this.startTime) / 1000;
        console.log(`⚡ Gesture: ${gesture} | Confidence: ${Math.round(handData.confidence * 100)}% | Time: ${elapsed.toFixed(1)}s`);
        this.lastGesture = gesture;
      }
      
      return originalGesture(handData);
    };
  },
  
  testMirroring() {
    console.log('🪞 Testing Camera Mirroring:');
    console.log('Move your RIGHT hand - it should appear on the RIGHT side of the screen');
    console.log('Move your LEFT hand - it should appear on the LEFT side of the screen');
    console.log('This makes interaction more natural and intuitive');
  },
  
  testResponsiveness() {
    console.log('⚡ Testing Responsiveness:');
    console.log('👉 Point with index finger - should detect immediately');
    console.log('✊ Make a fist - should detect quickly');
    console.log('✋ Open hand - should detect fast');
    console.log('👋 Move between board squares - should follow smoothly');
  },
  
  checkPerformance() {
    const elapsed = (Date.now() - this.startTime) / 1000;
    const gestureRate = this.gestureChanges / elapsed;
    
    console.log('📊 Performance Results:');
    console.log(`⏱️  Total time: ${elapsed.toFixed(1)}s`);
    console.log(`🔄 Gesture changes: ${this.gestureChanges}`);
    console.log(`📈 Gesture rate: ${gestureRate.toFixed(1)} changes/second`);
    
    if (gestureRate > 2) {
      console.log('🚀 Excellent responsiveness!');
    } else if (gestureRate > 1) {
      console.log('✅ Good responsiveness');
    } else {
      console.log('⚠️  Could be more responsive');
    }
  },
  
  runFullTest() {
    this.startTest();
    
    setTimeout(() => this.testMirroring(), 3000);
    setTimeout(() => this.testResponsiveness(), 6000);
    setTimeout(() => this.checkPerformance(), 20000);
  }
};

// Auto-start test
setTimeout(() => {
  window.improvedTest.runFullTest();
}, 1000);