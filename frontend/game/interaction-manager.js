class InteractionManager {
    constructor(game, coordinateMapper, renderer) {
        this.game = game;
        this.coordinateMapper = coordinateMapper;
        this.renderer = renderer;
        
        // Interaction state
        this.state = 'IDLE'; // IDLE, HOVERING, SELECTING, DRAGGING, RELEASING
        this.selectedPiece = null;
        this.hoveredSquare = null;
        this.validMoves = [];
        this.dragPreview = null;
        
        // Timing and threshold settings
        this.dwellThreshold = 1000; // ms to trigger selection
        this.dragThreshold = 20; // pixels to start drag
        this.stabilityThreshold = 10; // pixels for stable position
        
        // State tracking
        this.dwellTimer = null;
        this.lastPosition = null;
        this.dragStart = null;
        this.stateStartTime = null;
        this.positionHistory = [];
        
        // Debug settings
        this.debugMode = false;
        
        this.log('InteractionManager initialized');
    }
    
    /**
     * Main update method called with enhanced vision data
     */
    updateVisionInput(visionData) {
        if (!visionData) return;
        
        const timestamp = visionData.timestamp || Date.now();
        
        // Enhanced marker validation - require high confidence detection
        if (!visionData.marker || visionData.marker.confidence < 0.75) {
            this.handleMarkerLost();
            return;
        }
        
        // Additional validation for confirmed detection state
        if (visionData.marker.detection_state === 'SEARCHING') {
            this.log('Marker detection state is SEARCHING - waiting for confirmation');
            this.handleMarkerLost();
            return;
        }
        
        // Convert camera coordinates to board coordinates
        const boardPos = this.coordinateMapper.cameraToBoard(
            visionData.marker.x,
            visionData.marker.y,
            visionData.camera_dimension.x,
            visionData.camera_dimension.y
        );
        
        // Update position history
        this.updatePositionHistory(boardPos, timestamp);
        
        // Enhanced gesture state handling with quality validation
        const gestureState = visionData.gesture.state;
        const isStable = visionData.marker.stable || false;
        const isHighQuality = this.validateMarkerQuality(visionData);
        
        // Only process interaction with high-quality detections
        if (isHighQuality) {
            this.processInteraction(boardPos, gestureState, isStable, timestamp);
        } else {
            this.log('Marker quality insufficient for interaction');
        }
        
        this.lastPosition = boardPos;
    }
    
    /**
     * Validate marker quality for reliable interaction
     */
    validateMarkerQuality(visionData) {
        if (!visionData.quality_metrics) return true; // Fallback if no metrics
        
        const metrics = visionData.quality_metrics;
        
        // Minimum quality thresholds for interaction
        const minGeometric = 0.7;
        const minColor = 0.6;
        const minUniformity = 0.6;
        const minTemporal = 0.5;
        
        const qualityOk = (
            metrics.geometric_score >= minGeometric &&
            metrics.color_score >= minColor &&
            metrics.uniformity_score >= minUniformity &&
            metrics.temporal_score >= minTemporal
        );
        
        if (!qualityOk) {
            this.log(`Quality check failed: G:${(metrics.geometric_score*100).toFixed(0)} C:${(metrics.color_score*100).toFixed(0)} U:${(metrics.uniformity_score*100).toFixed(0)} T:${(metrics.temporal_score*100).toFixed(0)}`);
        }
        
        return qualityOk;
    }
    
    /**
     * Process interaction based on current state and input
     */
    processInteraction(boardPos, gestureState, isStable, timestamp) {
        switch (this.state) {
            case 'IDLE':
                this.handleIdleState(boardPos, gestureState, isStable, timestamp);
                break;
            case 'HOVERING':
                this.handleHoveringState(boardPos, gestureState, isStable, timestamp);
                break;
            case 'SELECTING':
                this.handleSelectingState(boardPos, gestureState, isStable, timestamp);
                break;
            case 'DRAGGING':
                this.handleDraggingState(boardPos, gestureState, isStable, timestamp);
                break;
            case 'RELEASING':
                this.handleReleasingState(boardPos, gestureState, isStable, timestamp);
                break;
        }
    }
    
    /**
     * Handle IDLE state - waiting for marker
     */
    handleIdleState(boardPos, gestureState, isStable, timestamp) {
        if (gestureState === 'HOVER' && boardPos.isOnBoard) {
            this.setState('HOVERING', timestamp);
            this.updateHover(boardPos);
        }
    }
    
    /**
     * Handle HOVERING state - marker detected, checking for selection
     */
    handleHoveringState(boardPos, gestureState, isStable, timestamp) {
        this.updateHover(boardPos);
        
        if (!boardPos.isOnBoard) {
            this.setState('IDLE', timestamp);
            this.clearHover();
            return;
        }
        
        // Enhanced selection criteria - require stable marker with sufficient dwell time
        const dwellTime = this.getStateDuration(timestamp);
        const isReadyForSelection = (
            (gestureState === 'SELECT') ||
            (gestureState === 'HOVER' && isStable && dwellTime > this.dwellThreshold)
        );
        
        if (isReadyForSelection) {
            const {x: gridX, y: gridY} = boardPos.grid;
            
            if (this.coordinateMapper.isDarkSquare(gridX, gridY)) {
                const piece = this.game.getPieceAt(gridY, gridX);
                
                if (piece && piece.includes(this.game.currentPlayer)) {
                    this.setState('SELECTING', timestamp);
                    this.selectPiece(gridX, gridY);
                    this.log(`Selected piece at (${gridX}, ${gridY}) after ${(dwellTime/1000).toFixed(1)}s dwell`);
                } else {
                    // Clicked on empty square or opponent piece
                    this.showInvalidSelection(gridX, gridY);
                    this.log(`Invalid selection at (${gridX}, ${gridY}) - ${piece ? 'opponent piece' : 'empty square'}`);
                }
            } else {
                this.log(`Selection ignored - not on dark square (${gridX}, ${gridY})`);
            }
        } else if (gestureState === 'NONE') {
            this.setState('IDLE', timestamp);
            this.clearHover();
        }
        
        // Debug logging for selection process
        if (this.debugMode && dwellTime > 500) {
            this.log(`Hovering: dwellTime=${(dwellTime/1000).toFixed(1)}s, stable=${isStable}, gesture=${gestureState}`);
        }
    }
    
    /**
     * Handle SELECTING state - piece selected, waiting for drag or release
     */
    handleSelectingState(boardPos, gestureState, isStable, timestamp) {
        if (gestureState === 'DRAG') {
            this.setState('DRAGGING', timestamp);
            this.startDrag(boardPos);
        } else if (gestureState === 'NONE') {
            // Lost marker - cancel selection after brief delay
            if (this.getStateDuration(timestamp) > 500) {
                this.setState('IDLE', timestamp);
                this.clearSelection();
            }
        } else if (!boardPos.isOnBoard) {
            this.setState('IDLE', timestamp);
            this.clearSelection();
        }
        
        // Update hover position while selected
        this.updateHover(boardPos);
    }
    
    /**
     * Handle DRAGGING state - piece being dragged
     */
    handleDraggingState(boardPos, gestureState, isStable, timestamp) {
        this.updateDrag(boardPos);
        
        // Enhanced drag handling with stability requirements
        if (gestureState === 'HOVER' || gestureState === 'SELECT') {
            const dragTime = this.getStateDuration(timestamp);
            
            // Require stability for a reasonable time before allowing drop
            if (isStable && dragTime > 300) {
                this.setState('RELEASING', timestamp);
                this.attemptMove(boardPos);
                this.log(`Attempting drop after ${(dragTime/1000).toFixed(1)}s drag`);
            } else if (this.debugMode) {
                this.log(`Dragging: stable=${isStable}, dragTime=${(dragTime/1000).toFixed(1)}s`);
            }
        } else if (gestureState === 'NONE') {
            // Lost marker during drag
            this.log('Lost marker during drag - canceling');
            this.setState('IDLE', timestamp);
            this.cancelDrag();
        }
    }
    
    /**
     * Handle RELEASING state - attempting to complete move
     */
    handleReleasingState(boardPos, gestureState, isStable, timestamp) {
        if (gestureState === 'DRAG') {
            // Marker moved again - back to dragging
            this.setState('DRAGGING', timestamp);
        } else if (gestureState === 'NONE' || this.getStateDuration(timestamp) > 1000) {
            // Complete the release
            this.completeMoveAttempt(boardPos);
        }
    }
    
    /**
     * Update hover state and visual feedback
     */
    updateHover(boardPos) {
        const {x: gridX, y: gridY} = boardPos.grid;
        
        if (this.coordinateMapper.isValidGrid(gridX, gridY) && 
            this.coordinateMapper.isDarkSquare(gridX, gridY)) {
            
            if (!this.hoveredSquare || 
                this.hoveredSquare.x !== gridX || this.hoveredSquare.y !== gridY) {
                
                this.hoveredSquare = {x: gridX, y: gridY};
                this.renderer?.updateHover(this.hoveredSquare);
            }
        } else {
            this.clearHover();
        }
    }
    
    /**
     * Select a piece at the given grid position
     */
    selectPiece(gridX, gridY) {
        const piece = this.game.getPieceAt(gridY, gridX);
        
        if (piece && piece.includes(this.game.currentPlayer)) {
            this.selectedPiece = {x: gridX, y: gridY};
            this.validMoves = this.game.getValidMoves(gridY, gridX);
            
            this.log(`Selected piece at (${gridX}, ${gridY}), ${this.validMoves.length} valid moves`);
            
            this.renderer?.updateSelection(this.selectedPiece, this.validMoves);
            
            return true;
        }
        
        return false;
    }
    
    /**
     * Start dragging operation
     */
    startDrag(boardPos) {
        if (!this.selectedPiece) return;
        
        this.dragStart = boardPos;
        this.dragPreview = {
            piece: this.selectedPiece,
            position: boardPos.pixel
        };
        
        this.log(`Started dragging piece from (${this.selectedPiece.x}, ${this.selectedPiece.y})`);
        
        this.renderer?.startDrag(this.selectedPiece, boardPos.pixel);
    }
    
    /**
     * Update drag position
     */
    updateDrag(boardPos) {
        if (!this.dragPreview) return;
        
        this.dragPreview.position = boardPos.pixel;
        this.renderer?.updateDrag(boardPos.pixel);
        
        // Highlight potential drop target
        const {x: gridX, y: gridY} = boardPos.grid;
        if (this.coordinateMapper.isValidGrid(gridX, gridY) && 
            this.coordinateMapper.isDarkSquare(gridX, gridY)) {
            
            const isValidTarget = this.validMoves.some(move => 
                move.to.col === gridX && move.to.row === gridY
            );
            
            this.renderer?.updateDropTarget({x: gridX, y: gridY}, isValidTarget);
        }
    }
    
    /**
     * Attempt to complete a move
     */
    attemptMove(boardPos) {
        if (!this.selectedPiece) return;
        
        const {x: targetX, y: targetY} = boardPos.grid;
        
        if (!this.coordinateMapper.isValidGrid(targetX, targetY) || 
            !this.coordinateMapper.isDarkSquare(targetX, targetY)) {
            this.cancelDrag();
            return;
        }
        
        // Find matching valid move
        const validMove = this.validMoves.find(move => 
            move.to.col === targetX && move.to.row === targetY
        );
        
        if (validMove) {
            this.executeMove(validMove);
        } else {
            this.cancelDrag();
        }
    }
    
    /**
     * Complete the move attempt
     */
    completeMoveAttempt(boardPos) {
        this.attemptMove(boardPos);
        this.setState('IDLE');
    }
    
    /**
     * Execute a valid move
     */
    executeMove(move) {
        this.log(`Executing move: (${move.from.col}, ${move.from.row}) -> (${move.to.col}, ${move.to.row})`);
        
        const result = this.game.makeMove(move);
        
        if (result.success) {
            // Animate the move
            this.renderer?.animateMove(move, () => {
                // Animation complete callback
                if (result.additionalJumps) {
                    // Continue turn with mandatory jumps
                    this.selectedPiece = {x: move.to.col, y: move.to.row};
                    this.validMoves = result.mustJump || [];
                    this.setState('SELECTING');
                    this.renderer?.updateSelection(this.selectedPiece, this.validMoves);
                } else {
                    // Turn complete
                    this.clearSelection();
                    this.renderer?.updateGameState(this.game.getGameState());
                    
                    if (result.gameEnd) {
                        this.renderer?.showGameEnd(result.winner);
                    }
                }
            });
        } else {
            this.log(`Move failed: ${result.error}`);
            this.cancelDrag();
        }
    }
    
    /**
     * Cancel current drag operation
     */
    cancelDrag() {
        this.log('Drag cancelled');
        
        this.dragPreview = null;
        this.renderer?.cancelDrag();
        
        if (this.selectedPiece) {
            // Return to selection state
            this.setState('SELECTING');
        } else {
            this.setState('IDLE');
        }
    }
    
    /**
     * Clear hover state
     */
    clearHover() {
        if (this.hoveredSquare) {
            this.hoveredSquare = null;
            this.renderer?.clearHover();
        }
    }
    
    /**
     * Clear selection state
     */
    clearSelection() {
        this.selectedPiece = null;
        this.validMoves = [];
        this.dragPreview = null;
        this.renderer?.clearSelection();
    }
    
    /**
     * Show invalid selection feedback
     */
    showInvalidSelection(gridX, gridY) {
        this.log(`Invalid selection at (${gridX}, ${gridY})`);
        this.renderer?.showInvalidSelection({x: gridX, y: gridY});
    }
    
    /**
     * Handle marker lost with enhanced recovery
     */
    handleMarkerLost() {
        if (this.state !== 'IDLE') {
            this.log(`Marker lost while in state: ${this.state}`);
            
            // Different grace periods based on current state
            let gracePeriod = 200; // Default
            if (this.state === 'SELECTING') gracePeriod = 500; // Longer for selections
            if (this.state === 'DRAGGING') gracePeriod = 300; // Medium for drags
            
            // Clear any existing timeout
            if (this.markerLostTimeout) {
                clearTimeout(this.markerLostTimeout);
            }
            
            // Set new timeout with appropriate grace period
            this.markerLostTimeout = setTimeout(() => {
                if (this.state !== 'IDLE') {
                    this.log(`Grace period expired - resetting to IDLE from ${this.state}`);
                    this.setState('IDLE');
                    this.clearHover();
                    this.clearSelection();
                }
                this.markerLostTimeout = null;
            }, gracePeriod);
        }
    }
    
    /**
     * Set interaction state
     */
    setState(newState, timestamp = Date.now()) {
        if (newState !== this.state) {
            this.log(`State transition: ${this.state} -> ${newState}`);
            this.state = newState;
            this.stateStartTime = timestamp;
        }
    }
    
    /**
     * Get duration of current state
     */
    getStateDuration(timestamp = Date.now()) {
        return this.stateStartTime ? timestamp - this.stateStartTime : 0;
    }
    
    /**
     * Update position history for stability analysis
     */
    updatePositionHistory(position, timestamp) {
        this.positionHistory.push({
            position: position,
            timestamp: timestamp
        });
        
        // Keep only recent history (last 2 seconds)
        const cutoff = timestamp - 2000;
        this.positionHistory = this.positionHistory.filter(entry => 
            entry.timestamp > cutoff
        );
    }
    
    /**
     * Check if position is stable based on history
     */
    isPositionStable(threshold = this.stabilityThreshold) {
        if (this.positionHistory.length < 5) return false;
        
        const recent = this.positionHistory.slice(-5);
        const avgX = recent.reduce((sum, entry) => sum + entry.position.pixel.x, 0) / recent.length;
        const avgY = recent.reduce((sum, entry) => sum + entry.position.pixel.y, 0) / recent.length;
        
        return recent.every(entry => {
            const distance = this.coordinateMapper.getPixelDistance(
                entry.position.pixel.x, entry.position.pixel.y, avgX, avgY
            );
            return distance < threshold;
        });
    }
    
    /**
     * Get current interaction state
     */
    getState() {
        return {
            state: this.state,
            selectedPiece: this.selectedPiece,
            hoveredSquare: this.hoveredSquare,
            validMoves: [...this.validMoves],
            dragPreview: this.dragPreview
        };
    }
    
    /**
     * Reset interaction manager
     */
    reset() {
        this.setState('IDLE');
        this.clearHover();
        this.clearSelection();
        this.positionHistory = [];
        this.lastPosition = null;
        
        // Clear any pending timeouts
        if (this.markerLostTimeout) {
            clearTimeout(this.markerLostTimeout);
            this.markerLostTimeout = null;
        }
        
        this.log('Interaction manager reset');
    }
    
    /**
     * Enable/disable debug mode
     */
    setDebugMode(enabled) {
        this.debugMode = enabled;
    }
    
    /**
     * Debug logging
     */
    log(message) {
        if (this.debugMode) {
            console.log(`[InteractionManager] ${message}`);
        }
    }
}

// Export for both Node.js and browser environments
if (typeof module !== 'undefined' && module.exports) {
    module.exports = InteractionManager;
} else if (typeof window !== 'undefined') {
    window.InteractionManager = InteractionManager;
}