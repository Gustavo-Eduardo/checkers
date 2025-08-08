/**
 * Computer Vision Checkers - Main Application
 */

class CheckersApp {
    constructor() {
        // Core game components
        this.game = null;
        this.coordinateMapper = null;
        this.interactionManager = null;
        this.renderer = null;
        
        // UI elements
        this.elements = {
            canvas: document.getElementById('gameCanvas'),
            resetBtn: document.getElementById('resetBtn'),
            calibrateBtn: document.getElementById('calibrateBtn'),
            debugBtn: document.getElementById('debugBtn'),
            visionInfo: document.getElementById('visionInfo'),
            modalOverlay: document.getElementById('modalOverlay'),
            calibrationNext: document.getElementById('calibrationNext'),
            calibrationCancel: document.getElementById('calibrationCancel'),
            calibrationInstructions: document.getElementById('calibrationInstructions'),
            // Status indicators
            cameraIndicator: document.getElementById('cameraIndicator'),
            visionIndicator: document.getElementById('visionIndicator'),
            gameIndicator: document.getElementById('gameIndicator'),
            // Vision info
            markerStatus: document.getElementById('markerStatus'),
            confidenceValue: document.getElementById('confidenceValue'),
            gestureState: document.getElementById('gestureState'),
            markerPosition: document.getElementById('markerPosition')
        };
        
        // Application state
        this.isInitialized = false;
        this.debugMode = false;
        this.calibrationMode = false;
        this.calibrationStep = 0;
        this.calibrationCorners = ['topLeft', 'topRight', 'bottomLeft', 'bottomRight'];
        
        // Vision data tracking
        this.lastVisionData = null;
        this.visionTimeout = null;
        this.cameraConnected = false;
        
        this.initialize();
    }
    
    /**
     * Initialize the application
     */
    initialize() {
        console.log('Initializing Computer Vision Checkers...');
        
        try {
            // Initialize game components
            this.game = new CheckersEngine();
            this.coordinateMapper = new CoordinateMapper({
                boardSize: 640,
                cellSize: 80,
                boardOffset: {x: 80, y: 80}
            });
            this.renderer = new CanvasRenderer('gameCanvas', {
                boardSize: 640,
                cellSize: 80,
                boardOffset: {x: 80, y: 80}
            });
            this.interactionManager = new InteractionManager(
                this.game,
                this.coordinateMapper,
                this.renderer
            );
            
            // Set up event listeners
            this.setupEventListeners();
            
            // Set up computer vision listener
            this.setupVisionListener();
            
            // Load saved calibration if available
            this.coordinateMapper.loadCalibration();
            
            // Initial render
            this.updateGameDisplay();
            
            this.isInitialized = true;
            this.updateStatus('gameIndicator', true);
            
            console.log('Application initialized successfully!');
            
        } catch (error) {
            console.error('Failed to initialize application:', error);
            this.showError('Failed to initialize game. Please refresh the page.');
        }
    }
    
    /**
     * Set up event listeners for UI controls
     */
    setupEventListeners() {
        // Game controls
        this.elements.resetBtn.addEventListener('click', () => this.resetGame());
        this.elements.calibrateBtn.addEventListener('click', () => this.startCalibration());
        this.elements.debugBtn.addEventListener('click', () => this.toggleDebugMode());
        
        // Calibration controls
        this.elements.calibrationNext.addEventListener('click', () => this.nextCalibrationStep());
        this.elements.calibrationCancel.addEventListener('click', () => this.cancelCalibration());
        
        // Keyboard shortcuts
        document.addEventListener('keydown', (event) => this.handleKeyPress(event));
        
        // Window resize handling
        window.addEventListener('resize', () => this.handleResize());
    }
    
    /**
     * Set up computer vision data listener
     */
    setupVisionListener() {
        window.detection.onUpdatePointer((data) => {
            try {
                const visionData = JSON.parse(data);
                this.handleVisionData(visionData);
            } catch (error) {
                console.error('Failed to parse vision data:', error);
            }
        });
    }
    
    /**
     * Handle incoming computer vision data
     */
    handleVisionData(visionData) {
        console.log('[DEBUG] Received vision data:', JSON.stringify(visionData));
        
        this.lastVisionData = visionData;
        this.cameraConnected = true;
        this.updateStatus('cameraIndicator', true);
        
        // Reset vision timeout
        if (this.visionTimeout) {
            clearTimeout(this.visionTimeout);
        }
        this.visionTimeout = setTimeout(() => {
            this.cameraConnected = false;
            this.updateStatus('cameraIndicator', false);
            this.updateStatus('visionIndicator', false);
        }, 2000);
        
        // Update vision status
        const hasMarker = visionData.marker !== null;
        this.updateStatus('visionIndicator', hasMarker);
        console.log('[DEBUG] Has marker:', hasMarker);
        
        // Update vision info display
        this.updateVisionInfo(visionData);
        
        // Handle calibration mode
        if (this.calibrationMode) {
            this.handleCalibrationData(visionData);
            return;
        }
        
        // Update vision marker in renderer
        if (hasMarker) {
            const boardPos = this.coordinateMapper.cameraToBoard(
                visionData.marker.x,
                visionData.marker.y,
                visionData.camera_dimension.x,
                visionData.camera_dimension.y
            );
            
            console.log('[DEBUG] Board position calculated:', {
                camera: { x: visionData.marker.x, y: visionData.marker.y },
                board: { x: boardPos.pixel.x, y: boardPos.pixel.y },
                confidence: visionData.marker.confidence
            });
            
            this.renderer.updateVisionMarker({
                x: boardPos.pixel.x,
                y: boardPos.pixel.y,
                confidence: visionData.marker.confidence
            });
        } else {
            console.log('[DEBUG] Clearing vision marker');
            this.renderer.clearVisionMarker();
        }
        
        // Process interaction if game is active
        if (this.game && !this.game.isGameOver()) {
            this.interactionManager.updateVisionInput(visionData);
        }
    }
    
    /**
     * Handle calibration data
     */
    handleCalibrationData(visionData) {
        if (!visionData.marker) return;
        
        // Auto-advance calibration when marker is stable
        if (visionData.marker.stable && visionData.gesture.state === 'SELECT') {
            this.nextCalibrationStep();
        }
    }
    
    /**
     * Update vision information display
     */
    updateVisionInfo(visionData) {
        if (!this.debugMode) {
            this.elements.visionInfo.classList.add('hidden');
            return;
        }
        
        this.elements.visionInfo.classList.remove('hidden');
        
        if (visionData.marker) {
            this.elements.markerStatus.textContent = 'Detected';
            this.elements.confidenceValue.textContent = `${(visionData.marker.confidence * 100).toFixed(1)}%`;
            this.elements.markerPosition.textContent = `(${visionData.marker.x}, ${visionData.marker.y})`;
        } else {
            this.elements.markerStatus.textContent = 'Not Detected';
            this.elements.confidenceValue.textContent = '0%';
            this.elements.markerPosition.textContent = '-';
        }
        
        this.elements.gestureState.textContent = visionData.gesture.state;
    }
    
    /**
     * Update game display
     */
    updateGameDisplay() {
        if (this.renderer && this.game) {
            this.renderer.updateGameState(this.game.getGameState());
        }
    }
    
    /**
     * Reset the game
     */
    resetGame() {
        console.log('Resetting game...');
        
        if (this.game) {
            this.game.reset();
        }
        
        if (this.interactionManager) {
            this.interactionManager.reset();
        }
        
        this.updateGameDisplay();
        
        // Show reset feedback
        this.showNotification('New game started!');
    }
    
    /**
     * Start camera calibration
     */
    startCalibration() {
        console.log('Starting calibration...');
        
        this.calibrationMode = true;
        this.calibrationStep = 0;
        
        this.coordinateMapper.startCalibration();
        
        this.elements.modalOverlay.classList.add('active');
        this.updateCalibrationInstructions();
    }
    
    /**
     * Next calibration step
     */
    nextCalibrationStep() {
        if (!this.lastVisionData?.marker) {
            this.showNotification('Please ensure red marker is visible to camera');
            return;
        }
        
        const corner = this.calibrationCorners[this.calibrationStep];
        
        this.coordinateMapper.setCalibrationPoint(
            corner,
            this.lastVisionData.marker.x,
            this.lastVisionData.marker.y,
            this.lastVisionData.camera_dimension.x,
            this.lastVisionData.camera_dimension.y
        );
        
        this.calibrationStep++;
        
        if (this.calibrationStep >= this.calibrationCorners.length) {
            this.finishCalibration();
        } else {
            this.updateCalibrationInstructions();
        }
    }
    
    /**
     * Update calibration instructions
     */
    updateCalibrationInstructions() {
        const corners = ['top-left', 'top-right', 'bottom-left', 'bottom-right'];
        const corner = corners[this.calibrationStep];
        
        this.elements.calibrationInstructions.textContent =
            `Point your red marker at the ${corner} corner of the game board area and hold steady`;
    }
    
    /**
     * Finish calibration
     */
    finishCalibration() {
        const success = this.coordinateMapper.finalizeCalibration();
        
        if (success) {
            this.coordinateMapper.saveCalibration();
            this.showNotification('Calibration completed successfully!');
        } else {
            this.showNotification('Calibration failed. Please try again.');
        }
        
        this.cancelCalibration();
    }
    
    /**
     * Cancel calibration
     */
    cancelCalibration() {
        this.calibrationMode = false;
        this.calibrationStep = 0;
        this.elements.modalOverlay.classList.remove('active');
    }
    
    /**
     * Toggle debug mode
     */
    toggleDebugMode() {
        this.debugMode = !this.debugMode;
        
        if (this.renderer) {
            this.renderer.setDebugMode(this.debugMode);
        }
        
        if (this.interactionManager) {
            this.interactionManager.setDebugMode(this.debugMode);
        }
        
        this.elements.debugBtn.textContent = this.debugMode ? 'Debug: ON' : 'Debug Mode';
        
        this.showNotification(`Debug mode ${this.debugMode ? 'enabled' : 'disabled'}`);
    }
    
    /**
     * Handle keyboard shortcuts
     */
    handleKeyPress(event) {
        switch (event.key.toLowerCase()) {
            case 'r':
                if (event.ctrlKey) {
                    event.preventDefault();
                    this.resetGame();
                }
                break;
            case 'c':
                if (event.ctrlKey) {
                    event.preventDefault();
                    this.startCalibration();
                }
                break;
            case 'd':
                if (event.ctrlKey) {
                    event.preventDefault();
                    this.toggleDebugMode();
                }
                break;
            case 'escape':
                if (this.calibrationMode) {
                    this.cancelCalibration();
                }
                break;
        }
    }
    
    /**
     * Handle window resize
     */
    handleResize() {
        // Could implement responsive canvas resizing here if needed
    }
    
    /**
     * Update status indicator
     */
    updateStatus(indicatorId, active) {
        const indicator = this.elements[indicatorId];
        if (indicator) {
            indicator.className = `status-indicator ${active ? 'active' : 'inactive'}`;
        }
    }
    
    /**
     * Show notification
     */
    showNotification(message) {
        console.log('Notification:', message);
        
        // Create temporary notification element
        const notification = document.createElement('div');
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: rgba(0,0,0,0.8);
            color: white;
            padding: 15px 20px;
            border-radius: 5px;
            z-index: 2000;
            font-size: 14px;
            max-width: 300px;
            transform: translateX(100%);
            transition: transform 0.3s ease;
        `;
        notification.textContent = message;
        
        document.body.appendChild(notification);
        
        // Animate in
        setTimeout(() => {
            notification.style.transform = 'translateX(0)';
        }, 100);
        
        // Remove after delay
        setTimeout(() => {
            notification.style.transform = 'translateX(100%)';
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
            }, 300);
        }, 3000);
    }
    
    /**
     * Show error message
     */
    showError(message) {
        console.error('Error:', message);
        this.showNotification('Error: ' + message);
    }
    
    /**
     * Get application state for debugging
     */
    getState() {
        return {
            isInitialized: this.isInitialized,
            debugMode: this.debugMode,
            calibrationMode: this.calibrationMode,
            cameraConnected: this.cameraConnected,
            gameState: this.game?.getGameState(),
            interactionState: this.interactionManager?.getState(),
            calibrationStatus: this.coordinateMapper?.getCalibrationStatus()
        };
    }
}

// Initialize the application when the page loads
let checkersApp;

document.addEventListener('DOMContentLoaded', () => {
    checkersApp = new CheckersApp();
    
    // Make app available globally for debugging
    window.checkersApp = checkersApp;
});

// Handle page unload
window.addEventListener('beforeunload', () => {
    if (checkersApp?.renderer) {
        checkersApp.renderer.destroy();
    }
});