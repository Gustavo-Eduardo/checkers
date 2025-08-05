class CanvasRenderer {
    constructor(canvasId, config = {}) {
        this.canvas = document.getElementById(canvasId);
        this.ctx = this.canvas.getContext('2d');
        
        // Configuration
        this.config = {
            boardSize: config.boardSize || 640,
            cellSize: config.cellSize || 80,
            boardOffset: config.boardOffset || {x: 80, y: 80},
            pieceRadius: config.pieceRadius || 30,
            kingRadius: config.kingRadius || 25,
            borderWidth: config.borderWidth || 2,
            ...config
        };
        
        // Colors
        this.colors = {
            lightSquare: '#F0D9B5',
            darkSquare: '#B58863',
            redPiece: '#DC143C',
            blackPiece: '#2F4F4F',
            redKing: '#FF6347',
            blackKing: '#708090',
            boardBorder: '#8B4513',
            hoverGlow: 'rgba(255, 255, 0, 0.3)',
            selectedGlow: 'rgba(0, 255, 0, 0.5)',
            validMoveHighlight: 'rgba(0, 200, 0, 0.4)',
            invalidSelection: 'rgba(255, 0, 0, 0.4)',
            dragPreview: 'rgba(255, 255, 255, 0.7)',
            visionMarker: 'rgba(255, 0, 0, 0.8)',
            ...config.colors
        };
        
        // Animation system
        this.animations = [];
        this.animationFrame = null;
        
        // Current visual state
        this.gameState = null;
        this.hoveredSquare = null;
        this.selectedSquare = null;
        this.validMoves = [];
        this.dragState = null;
        this.visionMarker = null;
        
        // Performance tracking
        this.lastRender = 0;
        this.frameCount = 0;
        this.fps = 0;
        
        // Initialize canvas
        this.initializeCanvas();
        this.startRenderLoop();
    }
    
    /**
     * Initialize canvas and set up basic properties
     */
    initializeCanvas() {
        // Set canvas size
        this.canvas.width = this.config.boardSize + this.config.boardOffset.x * 2;
        this.canvas.height = this.config.boardSize + this.config.boardOffset.y * 2;
        
        // Enable high DPI rendering
        const dpr = window.devicePixelRatio || 1;
        const rect = this.canvas.getBoundingClientRect();
        
        this.canvas.width = rect.width * dpr;
        this.canvas.height = rect.height * dpr;
        this.ctx.scale(dpr, dpr);
        
        // Set canvas display size
        this.canvas.style.width = rect.width + 'px';
        this.canvas.style.height = rect.height + 'px';
        
        // Configure rendering context
        this.ctx.imageSmoothingEnabled = true;
        this.ctx.imageSmoothingQuality = 'high';
    }
    
    /**
     * Start the main render loop
     */
    startRenderLoop() {
        const render = (timestamp) => {
            this.updateAnimations(timestamp);
            this.draw();
            this.updateFPS(timestamp);
            this.animationFrame = requestAnimationFrame(render);
        };
        
        this.animationFrame = requestAnimationFrame(render);
    }
    
    /**
     * Stop the render loop
     */
    stopRenderLoop() {
        if (this.animationFrame) {
            cancelAnimationFrame(this.animationFrame);
            this.animationFrame = null;
        }
    }
    
    /**
     * Main drawing function
     */
    draw() {
        // Clear canvas
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
        
        // Draw background
        this.drawBackground();
        
        // Draw board
        this.drawBoard();
        
        // Draw valid move highlights
        this.drawValidMoveHighlights();
        
        // Draw hover effect
        this.drawHover();
        
        // Draw selection highlight
        this.drawSelection();
        
        // Draw pieces
        this.drawPieces();
        
        // Draw drag preview
        this.drawDragPreview();
        
        // Draw vision marker
        this.drawVisionMarker();
        
        // Draw UI elements
        this.drawUI();
        
        // Draw debug info if enabled
        if (this.debugMode) {
            this.drawDebugInfo();
        }
    }
    
    /**
     * Draw background
     */
    drawBackground() {
        this.ctx.fillStyle = '#2C2C2C';
        this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
    }
    
    /**
     * Draw the checkerboard
     */
    drawBoard() {
        const {boardOffset, cellSize, boardSize} = this.config;
        
        // Draw board border
        this.ctx.strokeStyle = this.colors.boardBorder;
        this.ctx.lineWidth = this.config.borderWidth;
        this.ctx.strokeRect(
            boardOffset.x - this.config.borderWidth,
            boardOffset.y - this.config.borderWidth,
            boardSize + this.config.borderWidth * 2,
            boardSize + this.config.borderWidth * 2
        );
        
        // Draw squares
        for (let row = 0; row < 8; row++) {
            for (let col = 0; col < 8; col++) {
                const x = boardOffset.x + col * cellSize;
                const y = boardOffset.y + row * cellSize;
                
                // Determine square color
                const isLight = (row + col) % 2 === 0;
                this.ctx.fillStyle = isLight ? this.colors.lightSquare : this.colors.darkSquare;
                
                this.ctx.fillRect(x, y, cellSize, cellSize);
                
                // Add square coordinates for debugging
                if (this.debugMode) {
                    this.ctx.fillStyle = 'rgba(255, 255, 255, 0.3)';
                    this.ctx.font = '12px Arial';
                    this.ctx.textAlign = 'center';
                    this.ctx.fillText(`${col},${row}`, x + cellSize/2, y + cellSize/2);
                }
            }
        }
    }
    
    /**
     * Draw valid move highlights
     */
    drawValidMoveHighlights() {
        if (!this.validMoves.length) return;
        
        this.ctx.fillStyle = this.colors.validMoveHighlight;
        
        for (const move of this.validMoves) {
            const {col, row} = move.to;
            const x = this.config.boardOffset.x + col * this.config.cellSize;
            const y = this.config.boardOffset.y + row * this.config.cellSize;
            
            // Draw highlight circle
            this.ctx.beginPath();
            this.ctx.arc(
                x + this.config.cellSize / 2,
                y + this.config.cellSize / 2,
                this.config.cellSize / 4,
                0,
                2 * Math.PI
            );
            this.ctx.fill();
            
            // Add move type indicator
            if (move.type === 'jump') {
                this.ctx.strokeStyle = 'rgba(255, 0, 0, 0.6)';
                this.ctx.lineWidth = 3;
                this.ctx.stroke();
            }
        }
    }
    
    /**
     * Draw hover effect
     */
    drawHover() {
        if (!this.hoveredSquare) return;
        
        const {x: col, y: row} = this.hoveredSquare;
        const x = this.config.boardOffset.x + col * this.config.cellSize;
        const y = this.config.boardOffset.y + row * this.config.cellSize;
        
        // Draw glow effect
        this.ctx.fillStyle = this.colors.hoverGlow;
        this.ctx.fillRect(x, y, this.config.cellSize, this.config.cellSize);
        
        // Draw border
        this.ctx.strokeStyle = 'rgba(255, 255, 0, 0.7)';
        this.ctx.lineWidth = 2;
        this.ctx.strokeRect(x, y, this.config.cellSize, this.config.cellSize);
    }
    
    /**
     * Draw selection highlight
     */
    drawSelection() {
        if (!this.selectedSquare) return;
        
        const {x: col, y: row} = this.selectedSquare;
        const x = this.config.boardOffset.x + col * this.config.cellSize;
        const y = this.config.boardOffset.y + row * this.config.cellSize;
        
        // Draw selection glow
        this.ctx.fillStyle = this.colors.selectedGlow;
        this.ctx.fillRect(x, y, this.config.cellSize, this.config.cellSize);
        
        // Draw animated border
        const time = Date.now() / 1000;
        const alpha = 0.5 + 0.3 * Math.sin(time * 4);
        this.ctx.strokeStyle = `rgba(0, 255, 0, ${alpha})`;
        this.ctx.lineWidth = 4;
        this.ctx.strokeRect(x, y, this.config.cellSize, this.config.cellSize);
    }
    
    /**
     * Draw game pieces
     */
    drawPieces() {
        if (!this.gameState?.board) return;
        
        for (let row = 0; row < 8; row++) {
            for (let col = 0; col < 8; col++) {
                const piece = this.gameState.board[row][col];
                if (!piece) continue;
                
                // Skip piece being dragged
                if (this.dragState?.piece && 
                    this.dragState.piece.x === col && this.dragState.piece.y === row) {
                    continue;
                }
                
                this.drawPiece(col, row, piece);
            }
        }
    }
    
    /**
     * Draw a single piece
     */
    drawPiece(col, row, piece, alpha = 1.0, offsetX = 0, offsetY = 0) {
        const centerX = this.config.boardOffset.x + col * this.config.cellSize + this.config.cellSize / 2 + offsetX;
        const centerY = this.config.boardOffset.y + row * this.config.cellSize + this.config.cellSize / 2 + offsetY;
        
        const isRed = piece.includes('red');
        const isKing = piece.includes('king');
        
        // Set colors with alpha
        const baseColor = isRed ? this.colors.redPiece : this.colors.blackPiece;
        const kingColor = isRed ? this.colors.redKing : this.colors.blackKing;
        
        this.ctx.globalAlpha = alpha;
        
        // Draw piece shadow
        this.ctx.fillStyle = 'rgba(0, 0, 0, 0.3)';
        this.ctx.beginPath();
        this.ctx.arc(centerX + 2, centerY + 2, this.config.pieceRadius, 0, 2 * Math.PI);
        this.ctx.fill();
        
        // Draw main piece
        this.ctx.fillStyle = baseColor;
        this.ctx.beginPath();
        this.ctx.arc(centerX, centerY, this.config.pieceRadius, 0, 2 * Math.PI);
        this.ctx.fill();
        
        // Draw piece border
        this.ctx.strokeStyle = 'rgba(0, 0, 0, 0.5)';
        this.ctx.lineWidth = 2;
        this.ctx.stroke();
        
        // Draw king indicator
        if (isKing) {
            this.ctx.fillStyle = kingColor;
            this.ctx.beginPath();
            this.ctx.arc(centerX, centerY, this.config.kingRadius, 0, 2 * Math.PI);
            this.ctx.fill();
            
            // Draw crown symbol
            this.drawCrown(centerX, centerY, this.config.kingRadius * 0.6);
        }
        
        this.ctx.globalAlpha = 1.0;
    }
    
    /**
     * Draw crown symbol for kings
     */
    drawCrown(centerX, centerY, size) {
        this.ctx.fillStyle = 'rgba(255, 215, 0, 0.8)'; // Gold color
        this.ctx.strokeStyle = 'rgba(0, 0, 0, 0.6)';
        this.ctx.lineWidth = 1;
        
        // Simple crown shape
        this.ctx.beginPath();
        this.ctx.moveTo(centerX - size, centerY + size/3);
        this.ctx.lineTo(centerX - size/2, centerY - size/3);
        this.ctx.lineTo(centerX, centerY);
        this.ctx.lineTo(centerX + size/2, centerY - size/3);
        this.ctx.lineTo(centerX + size, centerY + size/3);
        this.ctx.lineTo(centerX + size/2, centerY + size/2);
        this.ctx.lineTo(centerX - size/2, centerY + size/2);
        this.ctx.closePath();
        this.ctx.fill();
        this.ctx.stroke();
    }
    
    /**
     * Draw drag preview
     */
    drawDragPreview() {
        if (!this.dragState) return;
        
        const {piece, position, originalPiece} = this.dragState;
        
        // Draw semi-transparent piece at drag position
        const gridCol = Math.floor((position.x - this.config.boardOffset.x) / this.config.cellSize);
        const gridRow = Math.floor((position.y - this.config.boardOffset.y) / this.config.cellSize);
        
        this.drawPiece(
            gridCol, gridRow, originalPiece, 0.7,
            position.x - (this.config.boardOffset.x + gridCol * this.config.cellSize + this.config.cellSize / 2),
            position.y - (this.config.boardOffset.y + gridRow * this.config.cellSize + this.config.cellSize / 2)
        );
    }
    
    /**
     * Draw computer vision marker
     */
    drawVisionMarker() {
        if (!this.visionMarker) return;
        
        const {x, y, confidence} = this.visionMarker;
        const radius = 8 + confidence * 12; // Size based on confidence
        
        // Draw marker with pulsing effect
        const time = Date.now() / 1000;
        const pulse = 0.7 + 0.3 * Math.sin(time * 6);
        
        this.ctx.fillStyle = this.colors.visionMarker;
        this.ctx.globalAlpha = pulse * confidence;
        
        this.ctx.beginPath();
        this.ctx.arc(x, y, radius, 0, 2 * Math.PI);
        this.ctx.fill();
        
        // Draw crosshair
        this.ctx.strokeStyle = this.colors.visionMarker;
        this.ctx.lineWidth = 2;
        this.ctx.beginPath();
        this.ctx.moveTo(x - radius - 5, y);
        this.ctx.lineTo(x + radius + 5, y);
        this.ctx.moveTo(x, y - radius - 5);
        this.ctx.lineTo(x, y + radius + 5);
        this.ctx.stroke();
        
        this.ctx.globalAlpha = 1.0;
    }
    
    /**
     * Draw UI elements
     */
    drawUI() {
        if (!this.gameState) return;
        
        // Draw current player indicator
        this.drawCurrentPlayerIndicator();
        
        // Draw game status
        this.drawGameStatus();
        
        // Draw piece counts
        this.drawPieceCounts();
    }
    
    /**
     * Draw current player indicator
     */
    drawCurrentPlayerIndicator() {
        const x = this.config.boardOffset.x;
        const y = 20;
        
        this.ctx.font = '24px Arial';
        this.ctx.textAlign = 'left';
        this.ctx.fillStyle = this.gameState.currentPlayer === 'red' ? this.colors.redPiece : this.colors.blackPiece;
        this.ctx.fillText(`Current Player: ${this.gameState.currentPlayer.toUpperCase()}`, x, y);
    }
    
    /**
     * Draw game status
     */
    drawGameStatus() {
        if (this.gameState.gameState === 'game_over') {
            const x = this.canvas.width / 2;
            const y = this.canvas.height - 30;
            
            this.ctx.font = '32px Arial';
            this.ctx.textAlign = 'center';
            this.ctx.fillStyle = 'rgba(255, 255, 255, 0.9)';
            this.ctx.strokeStyle = 'rgba(0, 0, 0, 0.7)';
            this.ctx.lineWidth = 2;
            
            const text = `${this.gameState.winner?.toUpperCase()} WINS!`;
            this.ctx.strokeText(text, x, y);
            this.ctx.fillText(text, x, y);
        }
    }
    
    /**
     * Draw piece counts
     */
    drawPieceCounts() {
        const rightX = this.config.boardOffset.x + this.config.boardSize;
        const y = 20;
        
        this.ctx.font = '16px Arial';
        this.ctx.textAlign = 'right';
        
        // Red pieces
        this.ctx.fillStyle = this.colors.redPiece;
        this.ctx.fillText(`Red: ${this.gameState.stats?.red?.pieces || 0}`, rightX, y);
        
        // Black pieces
        this.ctx.fillStyle = this.colors.blackPiece;
        this.ctx.fillText(`Black: ${this.gameState.stats?.black?.pieces || 0}`, rightX, y + 25);
    }
    
    /**
     * Draw debug information
     */
    drawDebugInfo() {
        const x = 10;
        let y = this.canvas.height - 80;
        
        this.ctx.font = '12px monospace';
        this.ctx.textAlign = 'left';
        this.ctx.fillStyle = 'rgba(255, 255, 255, 0.8)';
        
        this.ctx.fillText(`FPS: ${this.fps.toFixed(1)}`, x, y);
        y += 15;
        this.ctx.fillText(`Animations: ${this.animations.length}`, x, y);
        y += 15;
        
        if (this.visionMarker) {
            this.ctx.fillText(`Vision: (${this.visionMarker.x.toFixed(0)}, ${this.visionMarker.y.toFixed(0)})`, x, y);
            y += 15;
            this.ctx.fillText(`Confidence: ${(this.visionMarker.confidence * 100).toFixed(1)}%`, x, y);
        }
    }
    
    /**
     * Update animations
     */
    updateAnimations(timestamp) {
        this.animations = this.animations.filter(animation => {
            const progress = Math.min(1, (timestamp - animation.startTime) / animation.duration);
            
            animation.update(progress);
            
            if (progress >= 1) {
                if (animation.onComplete) {
                    animation.onComplete();
                }
                return false; // Remove completed animation
            }
            
            return true; // Keep animation
        });
    }
    
    /**
     * Update FPS counter
     */
    updateFPS(timestamp) {
        if (timestamp - this.lastRender >= 1000) {
            this.fps = this.frameCount;
            this.frameCount = 0;
            this.lastRender = timestamp;
        }
        this.frameCount++;
    }
    
    // Public API methods for updating visual state
    
    updateGameState(gameState) {
        this.gameState = gameState;
    }
    
    updateHover(square) {
        this.hoveredSquare = square;
    }
    
    clearHover() {
        this.hoveredSquare = null;
    }
    
    updateSelection(square, validMoves) {
        this.selectedSquare = square;
        this.validMoves = validMoves || [];
    }
    
    clearSelection() {
        this.selectedSquare = null;
        this.validMoves = [];
    }
    
    startDrag(piece, position) {
        this.dragState = {
            piece: piece,
            position: position,
            originalPiece: this.gameState?.board[piece.y][piece.x]
        };
    }
    
    updateDrag(position) {
        if (this.dragState) {
            this.dragState.position = position;
        }
    }
    
    cancelDrag() {
        this.dragState = null;
    }
    
    updateDropTarget(square, isValid) {
        // Visual feedback for drop target could be added here
    }
    
    updateVisionMarker(marker) {
        this.visionMarker = marker;
    }
    
    clearVisionMarker() {
        this.visionMarker = null;
    }
    
    showInvalidSelection(square) {
        // Flash effect for invalid selection
        const x = this.config.boardOffset.x + square.x * this.config.cellSize;
        const y = this.config.boardOffset.y + square.y * this.config.cellSize;
        
        this.addAnimation({
            duration: 500,
            update: (progress) => {
                const alpha = Math.sin(progress * Math.PI * 4) * 0.5;
                this.ctx.fillStyle = `rgba(255, 0, 0, ${Math.abs(alpha)})`;
                this.ctx.fillRect(x, y, this.config.cellSize, this.config.cellSize);
            }
        });
    }
    
    animateMove(move, onComplete) {
        const fromX = this.config.boardOffset.x + move.from.col * this.config.cellSize + this.config.cellSize / 2;
        const fromY = this.config.boardOffset.y + move.from.row * this.config.cellSize + this.config.cellSize / 2;
        const toX = this.config.boardOffset.x + move.to.col * this.config.cellSize + this.config.cellSize / 2;
        const toY = this.config.boardOffset.y + move.to.row * this.config.cellSize + this.config.cellSize / 2;
        
        const piece = this.gameState.board[move.from.row][move.from.col];
        
        this.addAnimation({
            duration: 400,
            update: (progress) => {
                const easeProgress = this.easeInOutCubic(progress);
                const currentX = fromX + (toX - fromX) * easeProgress;
                const currentY = fromY + (toY - fromY) * easeProgress;
                
                // Hide original piece during animation
                this.gameState.board[move.from.row][move.from.col] = null;
                
                // Draw animated piece
                this.drawPiece(0, 0, piece, 1.0, currentX - this.config.cellSize / 2, currentY - this.config.cellSize / 2);
            },
            onComplete: () => {
                this.dragState = null;
                if (onComplete) onComplete();
            }
        });
    }
    
    showGameEnd(winner) {
        // Add celebration animation
        this.addAnimation({
            duration: 2000,
            update: (progress) => {
                // Pulsing winner text could be enhanced here
            }
        });
    }
    
    addAnimation(animation) {
        animation.startTime = performance.now();
        this.animations.push(animation);
    }
    
    easeInOutCubic(t) {
        return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
    }
    
    setDebugMode(enabled) {
        this.debugMode = enabled;
    }
    
    destroy() {
        this.stopRenderLoop();
    }
}

// Export for both Node.js and browser environments
if (typeof module !== 'undefined' && module.exports) {
    module.exports = CanvasRenderer;
} else if (typeof window !== 'undefined') {
    window.CanvasRenderer = CanvasRenderer;
}