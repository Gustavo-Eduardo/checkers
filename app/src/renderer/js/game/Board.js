class CheckersBoard {
  constructor(canvasId) {
    this.canvas = document.getElementById(canvasId);
    this.ctx = this.canvas.getContext('2d');
    this.boardSize = 8;
    this.squareSize = 70;
    this.pieces = [];
    this.selectedPiece = null;
    this.validMoves = [];
    this.hoveredSquare = null;
    this.currentGameState = null;
    this.mouseMode = false;
    
    this.setupCanvas();
    this.setupMouseEvents();
    this.loadAssets();
  }

  setupCanvas() {
    const size = this.boardSize * this.squareSize;
    this.canvas.width = size;
    this.canvas.height = size;
    
    // High DPI support
    const dpr = window.devicePixelRatio || 1;
    const rect = this.canvas.getBoundingClientRect();
    this.canvas.width = rect.width * dpr;
    this.canvas.height = rect.height * dpr;
    this.ctx.scale(dpr, dpr);
    this.canvas.style.width = `${rect.width}px`;
    this.canvas.style.height = `${rect.height}px`;
    
    // Store actual display size for coordinate calculations
    this.displaySize = Math.min(rect.width, rect.height);
    this.squareSize = this.displaySize / this.boardSize;
  }

  setupMouseEvents() {
    this.canvas.addEventListener('click', (e) => {
      if (!this.mouseMode) return;
      
      const rect = this.canvas.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      
      const boardPos = this.screenToBoardCoords(x, y);
      if (boardPos) {
        this.handleMouseClick(boardPos);
      }
    });

    this.canvas.addEventListener('mousemove', (e) => {
      if (!this.mouseMode) return;
      
      const rect = this.canvas.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      
      const boardPos = this.screenToBoardCoords(x, y);
      if (boardPos && (boardPos[0] !== this.hoveredSquare?.[0] || boardPos[1] !== this.hoveredSquare?.[1])) {
        this.updateHover(boardPos);
      }
    });

    this.canvas.addEventListener('mouseleave', () => {
      this.hoveredSquare = null;
      this.render(this.currentGameState);
    });

    this.canvas.addEventListener('contextmenu', (e) => {
      e.preventDefault();
      if (this.mouseMode) {
        this.selectedPiece = null;
        this.validMoves = [];
        this.render(this.currentGameState);
      }
    });
  }

  screenToBoardCoords(x, y) {
    const col = Math.floor(x / this.squareSize);
    const row = Math.floor(y / this.squareSize);
    
    if (row >= 0 && row < this.boardSize && col >= 0 && col < this.boardSize) {
      return [row, col];
    }
    return null;
  }

  handleMouseClick(boardPos) {
    const [row, col] = boardPos;
    const piece = this.currentGameState?.board[row]?.[col];
    
    if (!this.selectedPiece) {
      // Select piece if it belongs to current player
      if (piece && piece * this.currentGameState.current_player > 0) {
        this.selectedPiece = boardPos;
        window.gameManager?.requestValidMoves(boardPos);
      }
    } else {
      // Try to move piece
      if (this.validMoves.some(([r, c]) => r === row && c === col)) {
        window.gameManager?.makeMove(this.selectedPiece, boardPos);
        this.selectedPiece = null;
        this.validMoves = [];
      } else if (piece && piece * this.currentGameState.current_player > 0) {
        // Select different piece
        this.selectedPiece = boardPos;
        window.gameManager?.requestValidMoves(boardPos);
      } else {
        // Deselect
        this.selectedPiece = null;
        this.validMoves = [];
      }
    }
    
    this.render(this.currentGameState);
  }

  loadAssets() {
    // Assets loaded, ready to render
    this.assetsLoaded = true;
  }

  render(gameState) {
    if (!gameState) return;
    
    this.currentGameState = gameState;
    this.clearCanvas();
    this.drawBoard();
    this.drawValidMoves();
    this.drawHover();
    this.drawPieces(gameState.board);
    this.drawSelection();
  }

  clearCanvas() {
    this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
  }

  drawBoard() {
    for (let row = 0; row < this.boardSize; row++) {
      for (let col = 0; col < this.boardSize; col++) {
        const isDark = (row + col) % 2 === 1;
        
        // Board squares
        this.ctx.fillStyle = isDark ? '#8B4513' : '#DEB887';
        this.ctx.fillRect(
          col * this.squareSize,
          row * this.squareSize,
          this.squareSize,
          this.squareSize
        );
        
        // Grid lines
        this.ctx.strokeStyle = '#654321';
        this.ctx.lineWidth = 1;
        this.ctx.strokeRect(
          col * this.squareSize,
          row * this.squareSize,
          this.squareSize,
          this.squareSize
        );
      }
    }
  }

  drawPieces(board) {
    if (!board) return;
    
    for (let row = 0; row < this.boardSize; row++) {
      for (let col = 0; col < this.boardSize; col++) {
        const piece = board[row][col];
        if (piece !== 0) {
          this.drawPiece(row, col, piece);
        }
      }
    }
  }

  drawPiece(row, col, pieceType) {
    const x = col * this.squareSize + this.squareSize / 2;
    const y = row * this.squareSize + this.squareSize / 2;
    const radius = this.squareSize * 0.35;
    
    // Piece shadow
    this.ctx.fillStyle = 'rgba(0, 0, 0, 0.3)';
    this.ctx.beginPath();
    this.ctx.arc(x + 3, y + 3, radius, 0, Math.PI * 2);
    this.ctx.fill();
    
    // Piece body
    const isRed = pieceType > 0;
    const gradient = this.ctx.createRadialGradient(
      x - radius/3, y - radius/3, 0,
      x, y, radius
    );
    
    if (isRed) {
      gradient.addColorStop(0, '#FF6B6B');
      gradient.addColorStop(0.7, '#E53E3E');
      gradient.addColorStop(1, '#C53030');
    } else {
      gradient.addColorStop(0, '#4A5568');
      gradient.addColorStop(0.7, '#2D3748');
      gradient.addColorStop(1, '#1A202C');
    }
    
    this.ctx.fillStyle = gradient;
    this.ctx.beginPath();
    this.ctx.arc(x, y, radius, 0, Math.PI * 2);
    this.ctx.fill();
    
    // Piece border
    this.ctx.strokeStyle = isRed ? '#9B2C2C' : '#000000';
    this.ctx.lineWidth = 2;
    this.ctx.stroke();
    
    // King crown
    if (Math.abs(pieceType) === 2) {
      this.ctx.fillStyle = '#FFD700';
      this.ctx.strokeStyle = '#B7791F';
      this.ctx.lineWidth = 1;
      this.ctx.font = `bold ${radius}px Arial`;
      this.ctx.textAlign = 'center';
      this.ctx.textBaseline = 'middle';
      this.ctx.strokeText('♔', x, y);
      this.ctx.fillText('♔', x, y);
    }
  }

  drawValidMoves() {
    if (!this.validMoves.length) return;
    
    this.validMoves.forEach(([row, col]) => {
      const x = col * this.squareSize + this.squareSize / 2;
      const y = row * this.squareSize + this.squareSize / 2;
      
      // Pulsing animation
      const time = Date.now() * 0.003;
      const pulse = Math.sin(time) * 0.1 + 0.9;
      const alpha = Math.sin(time * 2) * 0.2 + 0.4;
      
      // Outer glow
      this.ctx.fillStyle = `rgba(34, 197, 94, ${alpha * 0.3})`;
      this.ctx.beginPath();
      this.ctx.arc(x, y, this.squareSize * 0.45 * pulse, 0, Math.PI * 2);
      this.ctx.fill();
      
      // Inner circle
      this.ctx.fillStyle = `rgba(34, 197, 94, ${alpha})`;
      this.ctx.beginPath();
      this.ctx.arc(x, y, this.squareSize * 0.25, 0, Math.PI * 2);
      this.ctx.fill();
      
      // Border
      this.ctx.strokeStyle = `rgba(22, 163, 74, ${alpha + 0.3})`;
      this.ctx.lineWidth = 2;
      this.ctx.setLineDash([5, 5]);
      this.ctx.stroke();
      this.ctx.setLineDash([]);
    });
  }

  drawHover() {
    if (this.hoveredSquare) {
      const [row, col] = this.hoveredSquare;
      this.ctx.fillStyle = 'rgba(59, 130, 246, 0.2)';
      this.ctx.strokeStyle = 'rgba(59, 130, 246, 0.6)';
      this.ctx.lineWidth = 2;
      this.ctx.fillRect(
        col * this.squareSize,
        row * this.squareSize,
        this.squareSize,
        this.squareSize
      );
      this.ctx.strokeRect(
        col * this.squareSize,
        row * this.squareSize,
        this.squareSize,
        this.squareSize
      );
    }
  }

  drawSelection() {
    if (this.selectedPiece) {
      const [row, col] = this.selectedPiece;
      const x = col * this.squareSize;
      const y = row * this.squareSize;
      
      // Animated selection border
      const time = Date.now() * 0.005;
      const intensity = Math.sin(time) * 0.3 + 0.7;
      
      this.ctx.strokeStyle = `rgba(251, 191, 36, ${intensity})`;
      this.ctx.lineWidth = 4;
      this.ctx.setLineDash([10, 5]);
      this.ctx.lineDashOffset = time * 20;
      this.ctx.strokeRect(x + 2, y + 2, this.squareSize - 4, this.squareSize - 4);
      this.ctx.setLineDash([]);
    }
  }

  updateHover(position) {
    this.hoveredSquare = position;
    this.render(this.currentGameState);
  }

  updateSelection(position, validMoves = []) {
    this.selectedPiece = position;
    this.validMoves = validMoves;
    this.render(this.currentGameState);
  }

  clearSelection() {
    this.selectedPiece = null;
    this.validMoves = [];
    this.render(this.currentGameState);
  }

  setMouseMode(enabled) {
    this.mouseMode = enabled;
    this.canvas.style.cursor = enabled ? 'pointer' : 'default';
    if (!enabled) {
      this.hoveredSquare = null;
      this.render(this.currentGameState);
    }
  }

  animateMove(from, to, callback) {
    // Simple move animation
    const [fromRow, fromCol] = from;
    const [toRow, toCol] = to;
    
    const startX = fromCol * this.squareSize + this.squareSize / 2;
    const startY = fromRow * this.squareSize + this.squareSize / 2;
    const endX = toCol * this.squareSize + this.squareSize / 2;
    const endY = toRow * this.squareSize + this.squareSize / 2;
    
    const piece = this.currentGameState.board[fromRow][fromCol];
    
    let progress = 0;
    const duration = 300; // ms
    const startTime = Date.now();
    
    const animate = () => {
      const elapsed = Date.now() - startTime;
      progress = Math.min(elapsed / duration, 1);
      
      // Easing function
      const eased = 1 - Math.pow(1 - progress, 3);
      
      const currentX = startX + (endX - startX) * eased;
      const currentY = startY + (endY - startY) * eased;
      
      // Redraw board without the moving piece
      this.render(this.currentGameState);
      
      // Draw moving piece at interpolated position
      const radius = this.squareSize * 0.35;
      this.drawPieceAt(currentX, currentY, piece, radius * (1 + Math.sin(progress * Math.PI) * 0.2));
      
      if (progress < 1) {
        requestAnimationFrame(animate);
      } else {
        if (callback) callback();
      }
    };
    
    animate();
  }

  drawPieceAt(x, y, pieceType, radius) {
    // Draw piece at specific coordinates (for animations)
    const isRed = pieceType > 0;
    
    // Shadow
    this.ctx.fillStyle = 'rgba(0, 0, 0, 0.3)';
    this.ctx.beginPath();
    this.ctx.arc(x + 3, y + 3, radius, 0, Math.PI * 2);
    this.ctx.fill();
    
    // Body
    const gradient = this.ctx.createRadialGradient(
      x - radius/3, y - radius/3, 0,
      x, y, radius
    );
    
    if (isRed) {
      gradient.addColorStop(0, '#FF6B6B');
      gradient.addColorStop(0.7, '#E53E3E');
      gradient.addColorStop(1, '#C53030');
    } else {
      gradient.addColorStop(0, '#4A5568');
      gradient.addColorStop(0.7, '#2D3748');
      gradient.addColorStop(1, '#1A202C');
    }
    
    this.ctx.fillStyle = gradient;
    this.ctx.beginPath();
    this.ctx.arc(x, y, radius, 0, Math.PI * 2);
    this.ctx.fill();
    
    // Border
    this.ctx.strokeStyle = isRed ? '#9B2C2C' : '#000000';
    this.ctx.lineWidth = 2;
    this.ctx.stroke();
    
    // King crown
    if (Math.abs(pieceType) === 2) {
      this.ctx.fillStyle = '#FFD700';
      this.ctx.font = `bold ${radius * 0.8}px Arial`;
      this.ctx.textAlign = 'center';
      this.ctx.textBaseline = 'middle';
      this.ctx.fillText('♔', x, y);
    }
  }
}