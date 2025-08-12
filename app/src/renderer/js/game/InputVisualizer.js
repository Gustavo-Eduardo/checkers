class InputVisualizer {
  constructor(canvasId) {
    this.canvas = document.getElementById(canvasId);
    this.ctx = this.canvas.getContext('2d');
    this.gestureTrail = [];
    this.maxTrailLength = 20;
    this.currentGesture = null;
    this.isActive = false;
    
    this.setupCanvas();
  }

  setupCanvas() {
    // Make canvas overlay the game board
    const gameBoard = document.getElementById('game-board');
    if (gameBoard) {
      const rect = gameBoard.getBoundingClientRect();
      this.canvas.width = rect.width;
      this.canvas.height = rect.height;
      this.canvas.style.width = `${rect.width}px`;
      this.canvas.style.height = `${rect.height}px`;
    }
    
    // High DPI support
    const dpr = window.devicePixelRatio || 1;
    const displayWidth = this.canvas.clientWidth;
    const displayHeight = this.canvas.clientHeight;
    
    this.canvas.width = displayWidth * dpr;
    this.canvas.height = displayHeight * dpr;
    this.ctx.scale(dpr, dpr);
  }

  setActive(active) {
    this.isActive = active;
    if (!active) {
      this.clearCanvas();
      this.gestureTrail = [];
    }
  }

  drawHandPosition(handData) {
    if (!this.isActive || !handData) {
      this.clearCanvas();
      return;
    }
    
    this.clearCanvas();
    
    // Convert normalized position to canvas coordinates
    const x = handData.position[0] * (this.canvas.clientWidth / window.devicePixelRatio);
    const y = handData.position[1] * (this.canvas.clientHeight / window.devicePixelRatio);
    
    // Add to trail
    this.gestureTrail.push({ x, y, timestamp: Date.now() });
    if (this.gestureTrail.length > this.maxTrailLength) {
      this.gestureTrail.shift();
    }
    
    // Remove old trail points
    const now = Date.now();
    this.gestureTrail = this.gestureTrail.filter(point => now - point.timestamp < 2000);
    
    // Draw trail
    if (this.gestureTrail.length > 1) {
      this.drawTrail();
    }
    
    // Draw current position
    this.drawCurrentPosition(x, y, handData.gesture, handData.confidence);
    
    this.currentGesture = handData;
  }

  drawTrail() {
    if (this.gestureTrail.length < 2) return;
    
    this.ctx.strokeStyle = 'rgba(100, 200, 255, 0.6)';
    this.ctx.lineWidth = 3;
    this.ctx.lineCap = 'round';
    this.ctx.lineJoin = 'round';
    
    this.ctx.beginPath();
    
    for (let i = 0; i < this.gestureTrail.length; i++) {
      const point = this.gestureTrail[i];
      const age = Date.now() - point.timestamp;
      const alpha = Math.max(0, 1 - age / 2000); // Fade over 2 seconds
      
      if (i === 0) {
        this.ctx.moveTo(point.x, point.y);
      } else {
        // Create gradient for fading trail
        const prevPoint = this.gestureTrail[i - 1];
        const gradient = this.ctx.createLinearGradient(
          prevPoint.x, prevPoint.y, point.x, point.y
        );
        
        const prevAlpha = i > 1 ? Math.max(0, 1 - (Date.now() - this.gestureTrail[i-1].timestamp) / 2000) : alpha;
        gradient.addColorStop(0, `rgba(100, 200, 255, ${prevAlpha * 0.6})`);
        gradient.addColorStop(1, `rgba(100, 200, 255, ${alpha * 0.6})`);
        
        this.ctx.strokeStyle = gradient;
        this.ctx.beginPath();
        this.ctx.moveTo(prevPoint.x, prevPoint.y);
        this.ctx.lineTo(point.x, point.y);
        this.ctx.stroke();
      }
    }
  }

  drawCurrentPosition(x, y, gesture, confidence) {
    // Outer glow based on confidence
    const glowRadius = 30 * confidence;
    const gradient = this.ctx.createRadialGradient(x, y, 0, x, y, glowRadius);
    
    const color = this.getGestureColor(gesture);
    gradient.addColorStop(0, `${color}80`);
    gradient.addColorStop(0.5, `${color}40`);
    gradient.addColorStop(1, `${color}00`);
    
    this.ctx.fillStyle = gradient;
    this.ctx.beginPath();
    this.ctx.arc(x, y, glowRadius, 0, Math.PI * 2);
    this.ctx.fill();
    
    // Inner cursor
    const cursorRadius = 8 + confidence * 4;
    this.ctx.fillStyle = color;
    this.ctx.beginPath();
    this.ctx.arc(x, y, cursorRadius, 0, Math.PI * 2);
    this.ctx.fill();
    
    // Cursor border
    this.ctx.strokeStyle = 'rgba(255, 255, 255, 0.8)';
    this.ctx.lineWidth = 2;
    this.ctx.stroke();
    
    // Gesture indicator
    this.drawGestureIndicator(gesture, x, y, confidence);
    
    // Confidence ring
    if (confidence > 0.5) {
      this.drawConfidenceRing(x, y, confidence);
    }
  }

  getGestureColor(gesture) {
    const colors = {
      point: 'rgba(34, 197, 94',    // Green
      grab: 'rgba(239, 68, 68',     // Red
      release: 'rgba(59, 130, 246', // Blue
      hover: 'rgba(168, 85, 247',   // Purple
      none: 'rgba(156, 163, 175'    // Gray
    };
    
    return colors[gesture] || colors.none;
  }

  drawGestureIndicator(gesture, x, y, confidence) {
    const icons = {
      point: '👉',
      grab: '✊',
      release: '✋',
      hover: '👋',
      none: '❓'
    };
    
    const icon = icons[gesture] || icons.none;
    
    if (icon) {
      this.ctx.font = `${20 + confidence * 10}px Arial`;
      this.ctx.textAlign = 'center';
      this.ctx.textBaseline = 'middle';
      
      // Text shadow
      this.ctx.fillStyle = 'rgba(0, 0, 0, 0.5)';
      this.ctx.fillText(icon, x + 2, y - 28);
      
      // Main text
      this.ctx.fillStyle = 'white';
      this.ctx.fillText(icon, x, y - 30);
    }
  }

  drawConfidenceRing(x, y, confidence) {
    const radius = 15;
    const startAngle = -Math.PI / 2; // Start at top
    const endAngle = startAngle + (Math.PI * 2 * confidence);
    
    // Background ring
    this.ctx.strokeStyle = 'rgba(255, 255, 255, 0.3)';
    this.ctx.lineWidth = 3;
    this.ctx.beginPath();
    this.ctx.arc(x, y, radius, 0, Math.PI * 2);
    this.ctx.stroke();
    
    // Confidence ring
    this.ctx.strokeStyle = 'rgba(255, 255, 255, 0.8)';
    this.ctx.lineWidth = 3;
    this.ctx.beginPath();
    this.ctx.arc(x, y, radius, startAngle, endAngle);
    this.ctx.stroke();
  }

  drawBoardMapping(boardPosition) {
    if (!this.isActive || !boardPosition) return;
    
    const [row, col] = boardPosition;
    const squareSize = this.canvas.clientWidth / 8;
    const x = (col + 0.5) * squareSize;
    const y = (row + 0.5) * squareSize;
    
    // Draw board position highlight
    this.ctx.strokeStyle = 'rgba(255, 215, 0, 0.8)';
    this.ctx.lineWidth = 3;
    this.ctx.setLineDash([5, 5]);
    this.ctx.strokeRect(
      col * squareSize,
      row * squareSize,
      squareSize,
      squareSize
    );
    this.ctx.setLineDash([]);
    
    // Draw coordinate label
    this.ctx.fillStyle = 'rgba(255, 215, 0, 0.9)';
    this.ctx.font = 'bold 14px Arial';
    this.ctx.textAlign = 'center';
    this.ctx.textBaseline = 'middle';
    this.ctx.fillText(`${row},${col}`, x, y);
  }

  clearCanvas() {
    this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
  }

  updateFromCameraFrame(frameData) {
    // If camera frame data includes overlay information
    if (frameData && frameData.overlay) {
      this.clearCanvas();
      
      // Draw any computer vision debug overlays
      if (frameData.overlay.contours) {
        this.drawContours(frameData.overlay.contours);
      }
      
      if (frameData.overlay.hand_landmarks) {
        this.drawHandLandmarks(frameData.overlay.hand_landmarks);
      }
    }
  }

  drawContours(contours) {
    // Draw detected contours for debugging
    this.ctx.strokeStyle = 'rgba(255, 0, 0, 0.5)';
    this.ctx.lineWidth = 2;
    
    contours.forEach(contour => {
      this.ctx.beginPath();
      contour.forEach((point, index) => {
        const x = point[0] * this.canvas.clientWidth;
        const y = point[1] * this.canvas.clientHeight;
        
        if (index === 0) {
          this.ctx.moveTo(x, y);
        } else {
          this.ctx.lineTo(x, y);
        }
      });
      this.ctx.closePath();
      this.ctx.stroke();
    });
  }

  drawHandLandmarks(landmarks) {
    // Draw hand landmarks for debugging
    this.ctx.fillStyle = 'rgba(0, 255, 0, 0.8)';
    
    landmarks.forEach(landmark => {
      const x = landmark[0] * this.canvas.clientWidth;
      const y = landmark[1] * this.canvas.clientHeight;
      
      this.ctx.beginPath();
      this.ctx.arc(x, y, 3, 0, Math.PI * 2);
      this.ctx.fill();
    });
  }

  resize() {
    // Recalculate canvas size when window resizes
    this.setupCanvas();
  }
}