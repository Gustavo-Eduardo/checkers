class CheckersEngine {
    constructor() {
        this.board = this.initializeBoard();
        this.currentPlayer = 'red';
        this.gameState = 'playing'; // 'playing', 'game_over'
        this.moveHistory = [];
        this.mandatoryJumps = [];
        this.winner = null;
        
        // Game statistics
        this.stats = {
            red: { pieces: 12, kings: 0 },
            black: { pieces: 12, kings: 0 }
        };
        
        this.updateMandatoryJumps();
    }
    
    initializeBoard() {
        const board = Array(8).fill().map(() => Array(8).fill(null));
        
        // Place initial pieces on dark squares only
        for (let row = 0; row < 8; row++) {
            for (let col = 0; col < 8; col++) {
                if ((row + col) % 2 === 1) { // Dark squares
                    if (row < 3) {
                        board[row][col] = 'black';
                    } else if (row > 4) {
                        board[row][col] = 'red';
                    }
                }
            }
        }
        return board;
    }
    
    isValidSquare(row, col) {
        return row >= 0 && row < 8 && col >= 0 && col < 8 && (row + col) % 2 === 1;
    }
    
    getPieceAt(row, col) {
        if (!this.isValidSquare(row, col)) return null;
        return this.board[row][col];
    }
    
    setPieceAt(row, col, piece) {
        if (this.isValidSquare(row, col)) {
            this.board[row][col] = piece;
        }
    }
    
    isPlayerPiece(row, col, player) {
        const piece = this.getPieceAt(row, col);
        return piece && piece.includes(player);
    }
    
    isOpponentPiece(row, col, player) {
        const piece = this.getPieceAt(row, col);
        if (!piece) return false;
        
        const opponent = player === 'red' ? 'black' : 'red';
        return piece.includes(opponent);
    }
    
    isKing(row, col) {
        const piece = this.getPieceAt(row, col);
        return piece && piece.includes('king');
    }
    
    getValidMoves(row, col) {
        const piece = this.getPieceAt(row, col);
        if (!piece || !piece.includes(this.currentPlayer)) return [];
        
        // If there are mandatory jumps, only allow jump moves
        if (this.mandatoryJumps.length > 0) {
            return this.mandatoryJumps.filter(jump => 
                jump.from.row === row && jump.from.col === col
            );
        }
        
        const moves = [];
        const isKing = this.isKing(row, col);
        
        // Define movement directions
        const directions = this.getMovementDirections(this.currentPlayer, isKing);
        
        // Check regular moves and jumps
        for (const [dRow, dCol] of directions) {
            // Regular move
            const newRow = row + dRow;
            const newCol = col + dCol;
            
            if (this.isValidSquare(newRow, newCol) && this.getPieceAt(newRow, newCol) === null) {
                moves.push({
                    from: {row, col},
                    to: {row: newRow, col: newCol},
                    type: 'move'
                });
            }
            
            // Jump move
            if (this.isValidSquare(newRow, newCol) && 
                this.isOpponentPiece(newRow, newCol, this.currentPlayer)) {
                
                const jumpRow = newRow + dRow;
                const jumpCol = newCol + dCol;
                
                if (this.isValidSquare(jumpRow, jumpCol) && 
                    this.getPieceAt(jumpRow, jumpCol) === null) {
                    moves.push({
                        from: {row, col},
                        to: {row: jumpRow, col: jumpCol},
                        type: 'jump',
                        captured: {row: newRow, col: newCol}
                    });
                }
            }
        }
        
        return moves;
    }
    
    getMovementDirections(player, isKing) {
        const directions = [];
        
        if (player === 'red' || isKing) {
            directions.push([-1, -1], [-1, 1]); // Up-left, up-right
        }
        if (player === 'black' || isKing) {
            directions.push([1, -1], [1, 1]); // Down-left, down-right
        }
        
        return directions;
    }
    
    getAllValidMoves(player) {
        const moves = [];
        for (let row = 0; row < 8; row++) {
            for (let col = 0; col < 8; col++) {
                if (this.isPlayerPiece(row, col, player)) {
                    moves.push(...this.getValidMoves(row, col));
                }
            }
        }
        return moves;
    }
    
    updateMandatoryJumps() {
        const jumps = [];
        for (let row = 0; row < 8; row++) {
            for (let col = 0; col < 8; col++) {
                if (this.isPlayerPiece(row, col, this.currentPlayer)) {
                    const moves = this.getValidMoves(row, col);
                    jumps.push(...moves.filter(m => m.type === 'jump'));
                }
            }
        }
        this.mandatoryJumps = jumps;
    }
    
    makeMove(move) {
        const {from, to, type, captured} = move;
        
        // Validate move
        const validMoves = this.getValidMoves(from.row, from.col);
        const isValidMove = validMoves.some(m => 
            m.to.row === to.row && m.to.col === to.col && m.type === type
        );
        
        if (!isValidMove) {
            return {success: false, error: 'Invalid move'};
        }
        
        // Execute move
        const piece = this.getPieceAt(from.row, from.col);
        this.setPieceAt(from.row, from.col, null);
        this.setPieceAt(to.row, to.col, piece);
        
        let capturedPiece = null;
        
        // Handle captures
        if (type === 'jump' && captured) {
            capturedPiece = this.getPieceAt(captured.row, captured.col);
            this.setPieceAt(captured.row, captured.col, null);
            this.updateStats(capturedPiece, 'captured');
        }
        
        // Check for king promotion
        let promoted = false;
        if ((this.currentPlayer === 'red' && to.row === 0) ||
            (this.currentPlayer === 'black' && to.row === 7)) {
            if (!piece.includes('king')) {
                this.setPieceAt(to.row, to.col, piece + '_king');
                this.updateStats(piece + '_king', 'promoted');
                promoted = true;
            }
        }
        
        // Record move in history
        this.moveHistory.push({
            ...move,
            piece: piece,
            capturedPiece: capturedPiece,
            promoted: promoted,
            timestamp: Date.now(),
            player: this.currentPlayer
        });
        
        // Check for additional jumps after a jump move
        if (type === 'jump') {
            // Temporarily switch to check for additional jumps from the new position
            const additionalJumps = this.getAdditionalJumps(to.row, to.col);
            
            if (additionalJumps.length > 0) {
                this.mandatoryJumps = additionalJumps;
                return {
                    success: true, 
                    additionalJumps: true,
                    continueTurn: true,
                    mustJump: additionalJumps
                };
            }
        }
        
        // Switch turns and update game state
        this.currentPlayer = this.currentPlayer === 'red' ? 'black' : 'red';
        this.updateMandatoryJumps();
        
        // Check for game end
        const gameEndResult = this.checkGameEnd();
        
        return {
            success: true,
            additionalJumps: false,
            continueTurn: false,
            gameEnd: gameEndResult.gameOver,
            winner: gameEndResult.winner
        };
    }
    
    getAdditionalJumps(row, col) {
        const piece = this.getPieceAt(row, col);
        if (!piece || !piece.includes(this.currentPlayer)) return [];
        
        const jumps = [];
        const isKing = this.isKing(row, col);
        const directions = this.getMovementDirections(this.currentPlayer, isKing);
        
        for (const [dRow, dCol] of directions) {
            const captureRow = row + dRow;
            const captureCol = col + dCol;
            
            if (this.isValidSquare(captureRow, captureCol) && 
                this.isOpponentPiece(captureRow, captureCol, this.currentPlayer)) {
                
                const jumpRow = captureRow + dRow;
                const jumpCol = captureCol + dCol;
                
                if (this.isValidSquare(jumpRow, jumpCol) && 
                    this.getPieceAt(jumpRow, jumpCol) === null) {
                    jumps.push({
                        from: {row, col},
                        to: {row: jumpRow, col: jumpCol},
                        type: 'jump',
                        captured: {row: captureRow, col: captureCol}
                    });
                }
            }
        }
        
        return jumps;
    }
    
    updateStats(piece, action) {
        if (!piece) return;
        
        const player = piece.includes('red') ? 'red' : 'black';
        
        switch (action) {
            case 'captured':
                this.stats[player].pieces--;
                if (piece.includes('king')) {
                    this.stats[player].kings--;
                }
                break;
            case 'promoted':
                this.stats[player].kings++;
                break;
        }
    }
    
    checkGameEnd() {
        // Count pieces and check for valid moves
        const playerPieces = [];
        const validMoves = this.getAllValidMoves(this.currentPlayer);
        
        for (let row = 0; row < 8; row++) {
            for (let col = 0; col < 8; col++) {
                if (this.isPlayerPiece(row, col, this.currentPlayer)) {
                    playerPieces.push({row, col});
                }
            }
        }
        
        // Game ends if no pieces or no valid moves
        if (playerPieces.length === 0 || validMoves.length === 0) {
            const winner = this.currentPlayer === 'red' ? 'black' : 'red';
            this.gameState = 'game_over';
            this.winner = winner;
            return {gameOver: true, winner: winner};
        }
        
        return {gameOver: false, winner: null};
    }
    
    isGameOver() {
        return this.gameState === 'game_over';
    }
    
    getGameState() {
        return {
            board: this.board.map(row => [...row]), // Deep copy
            currentPlayer: this.currentPlayer,
            gameState: this.gameState,
            winner: this.winner,
            stats: {...this.stats},
            mandatoryJumps: [...this.mandatoryJumps],
            moveCount: this.moveHistory.length
        };
    }
    
    canPlayerMove(player) {
        const moves = this.getAllValidMoves(player);
        return moves.length > 0;
    }
    
    getPieceCount(player) {
        let count = 0;
        for (let row = 0; row < 8; row++) {
            for (let col = 0; col < 8; col++) {
                if (this.isPlayerPiece(row, col, player)) {
                    count++;
                }
            }
        }
        return count;
    }
    
    getKingCount(player) {
        let count = 0;
        for (let row = 0; row < 8; row++) {
            for (let col = 0; col < 8; col++) {
                const piece = this.getPieceAt(row, col);
                if (piece && piece.includes(player) && piece.includes('king')) {
                    count++;
                }
            }
        }
        return count;
    }
    
    reset() {
        this.board = this.initializeBoard();
        this.currentPlayer = 'red';
        this.gameState = 'playing';
        this.winner = null;
        this.moveHistory = [];
        this.mandatoryJumps = [];
        this.stats = {
            red: { pieces: 12, kings: 0 },
            black: { pieces: 12, kings: 0 }
        };
        this.updateMandatoryJumps();
    }
    
    // Utility method for debugging
    printBoard() {
        console.log('  0 1 2 3 4 5 6 7');
        for (let row = 0; row < 8; row++) {
            let rowStr = row + ' ';
            for (let col = 0; col < 8; col++) {
                const piece = this.getPieceAt(row, col);
                if ((row + col) % 2 === 0) {
                    rowStr += '■ '; // Light square
                } else if (piece === null) {
                    rowStr += '□ '; // Empty dark square
                } else if (piece === 'red') {
                    rowStr += 'r ';
                } else if (piece === 'red_king') {
                    rowStr += 'R ';
                } else if (piece === 'black') {
                    rowStr += 'b ';
                } else if (piece === 'black_king') {
                    rowStr += 'B ';
                }
            }
            console.log(rowStr);
        }
        console.log(`Current player: ${this.currentPlayer}`);
        console.log(`Mandatory jumps: ${this.mandatoryJumps.length}`);
    }
}

// Export for both Node.js and browser environments
if (typeof module !== 'undefined' && module.exports) {
    module.exports = CheckersEngine;
} else if (typeof window !== 'undefined') {
    window.CheckersEngine = CheckersEngine;
}