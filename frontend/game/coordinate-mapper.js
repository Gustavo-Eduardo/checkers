class CoordinateMapper {
    constructor(config = {}) {
        // Default configuration
        this.config = {
            boardSize: config.boardSize || 640,
            cellSize: config.cellSize || 80,
            boardOffset: config.boardOffset || {x: 80, y: 80},
            windowSize: config.windowSize || {width: 800, height: 800},
            ...config
        };
        
        // Calibration data
        this.calibration = {
            isCalibrated: false,
            topLeft: null,
            topRight: null,
            bottomLeft: null,
            bottomRight: null,
            transform: null
        };
        
        // Smoothing for jitter reduction
        this.smoothingBuffer = [];
        this.smoothingSize = 5;
    }
    
    /**
     * Convert camera coordinates to board pixel coordinates
     */
    cameraToBoard(cameraX, cameraY, cameraWidth, cameraHeight) {
        // Normalize camera coordinates (0-1)
        const normalizedX = cameraX / cameraWidth;
        const normalizedY = cameraY / cameraHeight;
        
        let boardX, boardY;
        
        if (this.calibration.isCalibrated) {
            // Use calibrated transformation
            const transformed = this.applyCalibration(normalizedX, normalizedY);
            boardX = transformed.x;
            boardY = transformed.y;
        } else {
            // Use simple linear mapping
            boardX = normalizedX * this.config.boardSize + this.config.boardOffset.x;
            boardY = normalizedY * this.config.boardSize + this.config.boardOffset.y;
        }
        
        // Apply smoothing
        const smoothed = this.applySmoothingFilter(boardX, boardY);
        
        // Convert to grid position
        const gridX = Math.floor((smoothed.x - this.config.boardOffset.x) / this.config.cellSize);
        const gridY = Math.floor((smoothed.y - this.config.boardOffset.y) / this.config.cellSize);
        
        // Clamp to board bounds
        const clampedGridX = Math.max(0, Math.min(7, gridX));
        const clampedGridY = Math.max(0, Math.min(7, gridY));
        
        return {
            pixel: {
                x: smoothed.x,
                y: smoothed.y
            },
            grid: {
                x: clampedGridX,
                y: clampedGridY
            },
            normalized: {
                x: normalizedX,
                y: normalizedY
            },
            isOnBoard: this.isOnBoard(smoothed.x, smoothed.y),
            gridCenter: this.getGridCenter(clampedGridX, clampedGridY)
        };
    }
    
    /**
     * Convert grid coordinates to board pixel coordinates
     */
    gridToBoard(gridX, gridY) {
        const pixelX = gridX * this.config.cellSize + this.config.boardOffset.x + this.config.cellSize / 2;
        const pixelY = gridY * this.config.cellSize + this.config.boardOffset.y + this.config.cellSize / 2;
        
        return {
            x: pixelX,
            y: pixelY
        };
    }
    
    /**
     * Get the center pixel coordinates of a grid cell
     */
    getGridCenter(gridX, gridY) {
        return this.gridToBoard(gridX, gridY);
    }
    
    /**
     * Check if pixel coordinates are on the game board
     */
    isOnBoard(pixelX, pixelY) {
        return pixelX >= this.config.boardOffset.x &&
               pixelX <= this.config.boardOffset.x + this.config.boardSize &&
               pixelY >= this.config.boardOffset.y &&
               pixelY <= this.config.boardOffset.y + this.config.boardSize;
    }
    
    /**
     * Check if grid coordinates are valid
     */
    isValidGrid(gridX, gridY) {
        return gridX >= 0 && gridX < 8 && gridY >= 0 && gridY < 8;
    }
    
    /**
     * Check if grid coordinates represent a dark square (playable)
     */
    isDarkSquare(gridX, gridY) {
        return (gridX + gridY) % 2 === 1;
    }
    
    /**
     * Apply smoothing filter to reduce jitter
     */
    applySmoothingFilter(x, y) {
        // Add current position to buffer
        this.smoothingBuffer.push({x, y});
        
        // Keep buffer size limited
        if (this.smoothingBuffer.length > this.smoothingSize) {
            this.smoothingBuffer.shift();
        }
        
        // Calculate weighted average (more recent positions have higher weight)
        let totalWeight = 0;
        let weightedX = 0;
        let weightedY = 0;
        
        for (let i = 0; i < this.smoothingBuffer.length; i++) {
            const weight = (i + 1) / this.smoothingBuffer.length; // Linear weighting
            totalWeight += weight;
            weightedX += this.smoothingBuffer[i].x * weight;
            weightedY += this.smoothingBuffer[i].y * weight;
        }
        
        return {
            x: weightedX / totalWeight,
            y: weightedY / totalWeight
        };
    }
    
    /**
     * Calculate distance between two grid positions
     */
    getGridDistance(gridX1, gridY1, gridX2, gridY2) {
        return Math.sqrt(Math.pow(gridX2 - gridX1, 2) + Math.pow(gridY2 - gridY1, 2));
    }
    
    /**
     * Calculate distance between two pixel positions
     */
    getPixelDistance(x1, y1, x2, y2) {
        return Math.sqrt(Math.pow(x2 - x1, 2) + Math.pow(y2 - y1, 2));
    }
    
    /**
     * Start calibration process
     */
    startCalibration() {
        this.calibration = {
            isCalibrated: false,
            topLeft: null,
            topRight: null,
            bottomLeft: null,
            bottomRight: null,
            transform: null
        };
        console.log('Calibration started. Please point to board corners in order: top-left, top-right, bottom-left, bottom-right');
    }
    
    /**
     * Set calibration point
     */
    setCalibrationPoint(corner, cameraX, cameraY, cameraWidth, cameraHeight) {
        const normalizedX = cameraX / cameraWidth;
        const normalizedY = cameraY / cameraHeight;
        
        this.calibration[corner] = {x: normalizedX, y: normalizedY};
        
        console.log(`Calibration point set for ${corner}: (${normalizedX.toFixed(3)}, ${normalizedY.toFixed(3)})`);
        
        // Check if all corners are set
        if (this.calibration.topLeft && this.calibration.topRight && 
            this.calibration.bottomLeft && this.calibration.bottomRight) {
            this.finalizeCalibration();
        }
    }
    
    /**
     * Finalize calibration by computing transformation matrix
     */
    finalizeCalibration() {
        try {
            // Create perspective transformation matrix
            const sourcePoints = [
                [this.calibration.topLeft.x, this.calibration.topLeft.y],
                [this.calibration.topRight.x, this.calibration.topRight.y],
                [this.calibration.bottomLeft.x, this.calibration.bottomLeft.y],
                [this.calibration.bottomRight.x, this.calibration.bottomRight.y]
            ];
            
            const destPoints = [
                [0, 0],  // top-left board corner
                [1, 0],  // top-right board corner
                [0, 1],  // bottom-left board corner
                [1, 1]   // bottom-right board corner
            ];
            
            this.calibration.transform = this.computePerspectiveTransform(sourcePoints, destPoints);
            this.calibration.isCalibrated = true;
            
            console.log('Calibration completed successfully!');
            return true;
        } catch (error) {
            console.error('Calibration failed:', error);
            return false;
        }
    }
    
    /**
     * Apply calibrated transformation
     */
    applyCalibration(normalizedX, normalizedY) {
        if (!this.calibration.isCalibrated) {
            return {x: normalizedX, y: normalizedY};
        }
        
        // Apply perspective transformation
        const transformed = this.applyPerspectiveTransform(
            normalizedX, normalizedY, this.calibration.transform
        );
        
        // Map to board coordinates
        const boardX = transformed.x * this.config.boardSize + this.config.boardOffset.x;
        const boardY = transformed.y * this.config.boardSize + this.config.boardOffset.y;
        
        return {x: boardX, y: boardY};
    }
    
    /**
     * Compute perspective transformation matrix (simplified)
     */
    computePerspectiveTransform(srcPoints, dstPoints) {
        // This is a simplified bilinear transformation
        // For a full perspective transform, you'd need a more complex matrix calculation
        return {
            srcPoints: srcPoints,
            dstPoints: dstPoints
        };
    }
    
    /**
     * Apply perspective transformation (simplified bilinear interpolation)
     */
    applyPerspectiveTransform(x, y, transform) {
        const src = transform.srcPoints;
        const dst = transform.dstPoints;
        
        // Bilinear interpolation
        const x1 = this.lerp(src[0][0], src[1][0], x);
        const x2 = this.lerp(src[2][0], src[3][0], x);
        const y1 = this.lerp(src[0][1], src[2][1], y);
        const y2 = this.lerp(src[1][1], src[3][1], y);
        
        const finalX = this.lerp(x1, x2, y);
        const finalY = this.lerp(y1, y2, x);
        
        return {x: finalX, y: finalY};
    }
    
    /**
     * Linear interpolation helper
     */
    lerp(a, b, t) {
        return a + (b - a) * t;
    }
    
    /**
     * Reset smoothing buffer
     */
    resetSmoothing() {
        this.smoothingBuffer = [];
    }
    
    /**
     * Update configuration
     */
    updateConfig(newConfig) {
        this.config = {...this.config, ...newConfig};
        this.resetSmoothing();
    }
    
    /**
     * Get current configuration
     */
    getConfig() {
        return {...this.config};
    }
    
    /**
     * Get calibration status
     */
    getCalibrationStatus() {
        return {
            isCalibrated: this.calibration.isCalibrated,
            hasTopLeft: !!this.calibration.topLeft,
            hasTopRight: !!this.calibration.topRight,
            hasBottomLeft: !!this.calibration.bottomLeft,
            hasBottomRight: !!this.calibration.bottomRight
        };
    }
    
    /**
     * Save calibration data
     */
    saveCalibration() {
        if (this.calibration.isCalibrated) {
            const data = JSON.stringify(this.calibration);
            localStorage.setItem('checkers_calibration', data);
            return true;
        }
        return false;
    }
    
    /**
     * Load calibration data
     */
    loadCalibration() {
        try {
            const data = localStorage.getItem('checkers_calibration');
            if (data) {
                this.calibration = JSON.parse(data);
                return this.calibration.isCalibrated;
            }
        } catch (error) {
            console.error('Failed to load calibration:', error);
        }
        return false;
    }
}

// Export for both Node.js and browser environments
if (typeof module !== 'undefined' && module.exports) {
    module.exports = CoordinateMapper;
} else if (typeof window !== 'undefined') {
    window.CoordinateMapper = CoordinateMapper;
}