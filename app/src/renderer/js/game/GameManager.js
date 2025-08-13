class GameManager {
  constructor() {
    this.wsClient = null;
    this.board = null;
    this.inputVisualizer = null;
    this.gameState = null;
    this.isVisionMode = true; // Start with vision mode (default from HTML)
    this.cameraActive = false;
    this.moveHistory = [];
    this.gameTimer = null;
    this.gameStartTime = null;
    
    this.initializeComponents();
    this.setupEventListeners();
  }

  initializeComponents() {
    // Initialize WebSocket client
    this.wsClient = new WebSocketClient('ws://localhost:8765');
    
    // Initialize board
    this.board = new CheckersBoard('game-board');
    
    // Initialize input visualizer
    this.inputVisualizer = new InputVisualizer('input-overlay');
    
    // Set up WebSocket event listeners
    this.setupWebSocketListeners();
    
    // Set initial input mode based on HTML default (vision)
    setTimeout(() => {
      const visionRadio = document.querySelector('input[value="vision"]:checked');
      const mouseRadio = document.querySelector('input[value="mouse"]:checked');
      
      if (visionRadio) {
        this.setInputMode('vision');
      } else if (mouseRadio) {
        this.setInputMode('mouse');
      } else {
        // Fallback to vision mode
        document.querySelector('input[value="vision"]').checked = true;
        this.setInputMode('vision');
      }
    }, 100);
  }

  setupWebSocketListeners() {
    this.wsClient.on('game_state', (data) => {
      this.updateGameState(data);
    });

    this.wsClient.on('move_result', (data) => {
      this.handleMoveResult(data);
    });

    this.wsClient.on('piece_selected', (data) => {
      console.warn(`FRONTEND: *** PIECE_SELECTED HANDLER *** Position: ${data.position}, Valid moves: ${data.valid_moves?.length || 0}`);
      this.board.updateSelection(data.position, data.valid_moves);
    });

    this.wsClient.on('hover_position', (data) => {
      this.board.updateHover(data.position);
    });

    this.wsClient.on('hand_position', (data) => {
      if (this.isVisionMode) {
        this.inputVisualizer.drawHandPosition(data);
        this.updateGestureDisplay(data);
      }
    });

    this.wsClient.on('camera_frame', (data) => {
      this.updateCameraPreview(data.frame);
      if (data.debug_info) {
        this.updateDebugInfo(data.debug_info);
      }
    });

    this.wsClient.on('camera_status', (data) => {
      this.updateCameraStatus(data.active);
    });

    this.wsClient.on('game_reset', (data) => {
      this.resetGame(data);
    });

    this.wsClient.on('valid_moves', (data) => {
      this.board.updateSelection(data.position, data.moves);
    });

    this.wsClient.on('selection_cleared', (data) => {
      // Handle gesture-based selection clearing (replicates right-click behavior)
      console.warn(`FRONTEND: *** SELECTION_CLEARED HANDLER *** Clearing board selection`);
      this.board.clearSelection();
    });
  }

  setupEventListeners() {
    // Camera controls
    document.getElementById('btn-toggle-camera').addEventListener('click', () => {
      this.toggleCamera();
    });

    // Game controls
    document.getElementById('btn-new-game').addEventListener('click', () => {
      this.startNewGame();
    });

    document.getElementById('btn-reset').addEventListener('click', () => {
      this.resetBoard();
    });

    // Input mode toggle
    document.querySelectorAll('input[name="input-mode"]').forEach(radio => {
      radio.addEventListener('change', (e) => {
        this.setInputMode(e.target.value);
      });
    });

    // Help modal
    document.getElementById('btn-help').addEventListener('click', () => {
      document.getElementById('help-modal').style.display = 'block';
    });

    // Backend status check
    this.checkBackendStatus();
    setInterval(() => this.checkBackendStatus(), 5000);

    // Window resize handler
    window.addEventListener('resize', () => {
      this.board.setupCanvas();
      this.inputVisualizer.resize();
    });
  }

  async initialize() {
    try {
      this.updateStatus('Connecting to backend...');
      await this.wsClient.connect();
      this.updateStatus('Connected - Ready to play!');
      return true;
    } catch (error) {
      console.error('Failed to connect to backend:', error);
      this.updateStatus('Failed to connect to backend. Please restart the application.');
      return false;
    }
  }

  updateGameState(gameState) {
    this.gameState = gameState;
    this.board.render(gameState);
    this.updateScoreDisplay(gameState.piece_counts || {});
    this.updateCurrentPlayerDisplay(gameState.current_player);
    
    // Start timer on first game state update if not already started
    if (!this.gameStartTime && !this.gameTimer) {
      this.gameStartTime = Date.now();
      this.startGameTimer();
      console.log('Game timer auto-started');
    }
    
    if (gameState.game_over) {
      this.handleGameOver(gameState.game_over);
    }
  }

  handleMoveResult(result) {
    if (result.valid) {
      // Animate the move
      this.board.animateMove(result.move.from, result.move.to, () => {
        this.updateGameState(result);
        this.addMoveToHistory(result.move);
      });
      
      if (result.move.captured) {
        this.playSound('capture');
      } else {
        this.playSound('move');
      }
      
      if (result.move.promoted) {
        this.playSound('promotion');
        this.showNotification('King promoted!');
      }
    } else {
      this.showNotification(`Invalid move: ${result.error}`, 'error');
    }
    
    this.board.clearSelection();
  }

  makeMove(from, to) {
    if (this.wsClient.isConnected()) {
      this.wsClient.send('move', { from, to });
    } else {
      this.showNotification('Not connected to backend', 'error');
    }
  }

  requestValidMoves(position) {
    if (this.wsClient.isConnected()) {
      this.wsClient.send('get_valid_moves', { position });
    }
  }

  toggleCamera() {
    if (this.cameraActive) {
      this.stopCamera();
    } else {
      this.startCamera();
    }
  }

  startCamera() {
    if (this.wsClient.isConnected()) {
      // Send actual board canvas dimensions to backend for coordinate alignment
      const boardDimensions = {
        width: this.board.canvas.clientWidth,
        height: this.board.canvas.clientHeight
      };
      
      this.wsClient.send('start_camera', { 
        board_dimensions: boardDimensions 
      });
      this.updateStatus('Starting camera...');
    } else {
      this.showNotification('Not connected to backend', 'error');
    }
  }

  stopCamera() {
    if (this.wsClient.isConnected()) {
      this.wsClient.send('stop_camera');
      this.updateStatus('Stopping camera...');
    }
  }

  updateCameraStatus(active) {
    this.cameraActive = active;
    const button = document.getElementById('btn-toggle-camera');
    const status = document.getElementById('camera-status');
    
    if (active) {
      button.textContent = 'Stop Camera';
      button.classList.add('active');
      status.textContent = 'Camera Active';
      status.classList.add('active');
      this.inputVisualizer.setActive(true);
    } else {
      button.textContent = 'Start Camera';
      button.classList.remove('active');
      status.textContent = 'Camera Off';
      status.classList.remove('active');
      this.inputVisualizer.setActive(false);
    }
  }

  updateCameraPreview(frameBase64) {
    const canvas = document.getElementById('camera-preview');
    const ctx = canvas.getContext('2d');
    
    console.log('Received camera frame, length:', frameBase64 ? frameBase64.length : 0);
    
    const img = new Image();
    img.onload = () => {
      console.log('Camera frame loaded, size:', img.width, 'x', img.height);
      canvas.width = img.width;
      canvas.height = img.height;
      ctx.drawImage(img, 0, 0);
    };
    img.onerror = (e) => {
      console.error('Error loading camera frame:', e);
    };
    img.src = 'data:image/jpeg;base64,' + frameBase64;
  }

  setInputMode(mode) {
    this.isVisionMode = (mode === 'vision');
    this.board.setMouseMode(!this.isVisionMode);
    
    console.log(`Input mode changed to: ${mode}, mouse mode: ${!this.isVisionMode}`);
    
    if (this.isVisionMode && !this.cameraActive) {
      this.showNotification('Vision mode enabled. Start camera to use gesture controls.');
    } else if (!this.isVisionMode) {
      this.showNotification('Mouse mode enabled. Click to select and move pieces.');
      this.inputVisualizer.setActive(false);
    }
  }

  startNewGame() {
    this.resetBoard();
    this.gameStartTime = Date.now();
    this.startGameTimer();
    this.updateStatus('New game started!');
    console.log('New game started, timer started');
  }

  resetBoard() {
    if (this.wsClient.isConnected()) {
      this.wsClient.send('reset');
    }
    this.moveHistory = [];
    this.updateMoveHistoryDisplay();
    this.board.clearSelection();
  }

  updateScoreDisplay(pieceCounts) {
    document.getElementById('red-count').textContent = pieceCounts.red || 0;
    document.getElementById('black-count').textContent = pieceCounts.black || 0;
    document.getElementById('red-kings').textContent = `${pieceCounts.red_kings || 0} Kings`;
    document.getElementById('black-kings').textContent = `${pieceCounts.black_kings || 0} Kings`;
  }

  updateCurrentPlayerDisplay(currentPlayer) {
    const playerName = currentPlayer === 1 ? 'Red' : 'Black';
    document.getElementById('current-player').textContent = `${playerName}'s Turn`;
    
    // Update player indicators
    document.querySelectorAll('.player-score').forEach(score => {
      score.classList.remove('active');
    });
    
    const activePlayer = currentPlayer === 1 ? '.red-player' : '.black-player';
    document.querySelector(activePlayer).classList.add('active');
  }

  updateGestureDisplay(handData) {
    document.getElementById('current-gesture').textContent = 
      handData.gesture.charAt(0).toUpperCase() + handData.gesture.slice(1);
    document.getElementById('gesture-confidence').textContent = 
      `${Math.round(handData.confidence * 100)}%`;
  }

  updateDebugInfo(debugInfo) {
    // Create or update debug info display
    let debugPanel = document.getElementById('debug-panel');
    if (!debugPanel) {
      debugPanel = document.createElement('div');
      debugPanel.id = 'debug-panel';
      debugPanel.style.cssText = `
        position: absolute;
        top: 10px;
        right: 10px;
        background: rgba(0, 0, 0, 0.8);
        color: white;
        padding: 10px;
        border-radius: 5px;
        font-family: monospace;
        font-size: 12px;
        max-width: 300px;
        z-index: 1000;
      `;
      document.body.appendChild(debugPanel);
    }

    const info = [
      `🚀 MediaPipe Hand Detection:`,
      `Method: ${debugInfo.detection_method || 'None'}`,
      `Hand: ${debugInfo.handedness || 'Unknown'}`,
      `Confidence: ${debugInfo.confidence ? Math.round(debugInfo.confidence * 100) + '%' : 'N/A'}`,
      `Fingers Up: ${debugInfo.finger_count || 0}`,
      `Area: ${debugInfo.all_areas ? debugInfo.all_areas.map(a => Math.round(a)).join('px') : 'None'}`,
      '',
      `🎯 MediaPipe Features:`,
      `• 21 hand landmarks per hand`,
      `• Accurate finger tracking`,
      `• Real-time gesture recognition`,
      `• No background interference`,
      `• Works in various lighting`,
      '',
      `✋ Gesture Detection:`,
      `• Point: Index finger extended`,
      `• Grab: Closed fist (0 fingers)`,
      `• Release: Open hand (4+ fingers)`,
      `• Hover: Hand moving around`
    ];

    debugPanel.innerHTML = info.join('<br>');
  }

  addMoveToHistory(move) {
    this.moveHistory.push(move);
    this.updateMoveHistoryDisplay();
  }

  updateMoveHistoryDisplay() {
    const moveList = document.getElementById('move-list');
    moveList.innerHTML = '';
    
    this.moveHistory.forEach((move, index) => {
      const moveElement = document.createElement('div');
      moveElement.className = 'move-item';
      
      const player = move.player === 1 ? 'Red' : 'Black';
      const from = `${String.fromCharCode(97 + move.from[1])}${8 - move.from[0]}`;
      const to = `${String.fromCharCode(97 + move.to[1])}${8 - move.to[0]}`;
      
      let moveText = `${index + 1}. ${player}: ${from} → ${to}`;
      if (move.captured) {
        moveText += ' (capture)';
      }
      if (move.promoted) {
        moveText += ' (king)';
      }
      
      moveElement.textContent = moveText;
      moveList.appendChild(moveElement);
    });
    
    // Scroll to bottom
    moveList.scrollTop = moveList.scrollHeight;
  }

  handleGameOver(winner) {
    const winnerName = winner === 1 ? 'Red' : 'Black';
    this.showNotification(`Game Over! ${winnerName} wins!`, 'success');
    this.stopGameTimer();
    
    // Disable input temporarily
    setTimeout(() => {
      if (confirm(`Game Over! ${winnerName} wins!\n\nWould you like to start a new game?`)) {
        this.startNewGame();
      }
    }, 1000);
  }

  startGameTimer() {
    if (this.gameTimer) {
      clearInterval(this.gameTimer);
    }
    
    this.gameTimer = setInterval(() => {
      if (this.gameStartTime) {
        const elapsed = Date.now() - this.gameStartTime;
        const minutes = Math.floor(elapsed / 60000);
        const seconds = Math.floor((elapsed % 60000) / 1000);
        document.getElementById('game-timer').textContent = 
          `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
      }
    }, 1000);
  }

  stopGameTimer() {
    if (this.gameTimer) {
      clearInterval(this.gameTimer);
      this.gameTimer = null;
    }
  }

  async checkBackendStatus() {
    try {
      const status = await window.electronAPI.getBackendStatus();
      const statusElement = document.getElementById('backend-status');
      if (status) {
        statusElement.textContent = 'Connected';
        statusElement.className = 'status-indicator connected';
      } else {
        statusElement.textContent = 'Disconnected';
        statusElement.className = 'status-indicator disconnected';
      }
    } catch (error) {
      console.error('Error checking backend status:', error);
    }
  }

  updateStatus(message) {
    document.getElementById('status-message').textContent = message;
    console.log('Status:', message);
  }

  showNotification(message, type = 'info') {
    // Simple notification system
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    
    document.body.appendChild(notification);
    
    // Animate in
    setTimeout(() => notification.classList.add('show'), 100);
    
    // Remove after 3 seconds
    setTimeout(() => {
      notification.classList.remove('show');
      setTimeout(() => document.body.removeChild(notification), 300);
    }, 3000);
  }

  playSound(soundType) {
    // Placeholder for sound effects
    console.log(`Playing sound: ${soundType}`);
  }

  destroy() {
    if (this.wsClient) {
      this.wsClient.disconnect();
    }
    if (this.gameTimer) {
      clearInterval(this.gameTimer);
    }
  }
}

// Global help function
function closeHelp() {
  document.getElementById('help-modal').style.display = 'none';
}