const p = document.getElementById("python-data");

// Simple game state representation
let gameState = {
    board: initializeBoard(),
    currentPlayer: 'red'
};

// Initialize the board with pieces in starting positions
function initializeBoard() {
    // 8x8 board, null = empty, 'r' = red piece, 'b' = black piece
    let board = Array(8).fill(null).map(() => Array(8).fill(null));
    for (let row = 0; row < 3; row++) {
        for (let col = 0; col < 8; col++) {
            if ((row + col) % 2 === 1) {
                board[row][col] = 'b';
            }
        }
    }
    for (let row = 5; row < 8; row++) {
        for (let col = 0; col < 8; col++) {
            if ((row + col) % 2 === 1) {
                board[row][col] = 'r';
            }
        }
    }
    return board;
}

// Validate a move according to basic checkers rules
// moveData expected format: {from: [r1,c1], to: [r2,c2]}
function validateMove(moveData) {
    const { from, to } = moveData;
    if (!Array.isArray(from) || !Array.isArray(to) || from.length !== 2 || to.length !== 2) {
        return false;
    }
    const [r1, c1] = from;
    const [r2, c2] = to;
    if (r1 < 0 || r1 >= 8 || c1 < 0 || c1 >= 8 || r2 < 0 || r2 >= 8 || c2 < 0 || c2 >= 8) {
        return false;
    }
    const piece = gameState.board[r1][c1];
    if (piece === null) return false;
    if ((gameState.currentPlayer === 'red' && piece !== 'r') || (gameState.currentPlayer === 'black' && piece !== 'b')) {
        return false;
    }
    if (gameState.board[r2][c2] !== null) return false; // destination must be empty

    const dr = r2 - r1;
    const dc = c2 - c1;

    // Basic move: move diagonally forward by 1
    if (gameState.currentPlayer === 'red' && dr === -1 && Math.abs(dc) === 1) {
        return true;
    }
    if (gameState.currentPlayer === 'black' && dr === 1 && Math.abs(dc) === 1) {
        return true;
    }

    // Capture move: move diagonally forward by 2, jumping over opponent piece
    if (gameState.currentPlayer === 'red' && dr === -2 && Math.abs(dc) === 2) {
        const jumpedPiece = gameState.board[r1 - 1][c1 + (dc / 2)];
        if (jumpedPiece === 'b') return true;
    }
    if (gameState.currentPlayer === 'black' && dr === 2 && Math.abs(dc) === 2) {
        const jumpedPiece = gameState.board[r1 + 1][c1 + (dc / 2)];
        if (jumpedPiece === 'r') return true;
    }

    return false;
}

// Update the game state and UI after a valid move
function applyMove(moveData) {
    const { from, to } = moveData;
    const [r1, c1] = from;
    const [r2, c2] = to;
    const piece = gameState.board[r1][c1];
    gameState.board[r1][c1] = null;
    gameState.board[r2][c2] = piece;

    // Check if move was a capture
    if (Math.abs(r2 - r1) === 2) {
        const jumpedRow = (r1 + r2) / 2;
        const jumpedCol = (c1 + c2) / 2;
        gameState.board[jumpedRow][jumpedCol] = null;
    }

    // Switch player
    gameState.currentPlayer = gameState.currentPlayer === 'red' ? 'black' : 'red';

    updateUI();
}

// Update the UI to reflect the current game state
function updateUI() {
    // For simplicity, just display the board as text in the element
    let display = '';
    for (let row = 0; row < 8; row++) {
        for (let col = 0; col < 8; col++) {
            display += gameState.board[row][col] ? gameState.board[row][col] : '.';
            display += ' ';
        }
        display += '\n';
    }
    p.textContent = `Current player: ${gameState.currentPlayer}\n` + display;
}

const { ipcRenderer } = require('electron');

const p = document.getElementById("python-data");

// Simple game state representation
let gameState = {
    board: initializeBoard(),
    currentPlayer: 'red'
};

// Initialize the board with pieces in starting positions
function initializeBoard() {
    // 8x8 board, null = empty, 'r' = red piece, 'b' = black piece
    let board = Array(8).fill(null).map(() => Array(8).fill(null));
    for (let row = 0; row < 3; row++) {
        for (let col = 0; col < 8; col++) {
            if ((row + col) % 2 === 1) {
                board[row][col] = 'b';
            }
        }
    }
    for (let row = 5; row < 8; row++) {
        for (let col = 0; col < 8; col++) {
            if ((row + col) % 2 === 1) {
                board[row][col] = 'r';
            }
        }
    }
    return board;
}

// Validate a move according to basic checkers rules
// moveData expected format: {from: [r1,c1], to: [r2,c2]}
function validateMove(moveData) {
    const { from, to } = moveData;
    if (!Array.isArray(from) || !Array.isArray(to) || from.length !== 2 || to.length !== 2) {
        return false;
    }
    const [r1, c1] = from;
    const [r2, c2] = to;
    if (r1 < 0 || r1 >= 8 || c1 < 0 || c1 >= 8 || r2 < 0 || r2 >= 8 || c2 < 0 || c2 >= 8) {
        return false;
    }
    const piece = gameState.board[r1][c1];
    if (piece === null) return false;
    if ((gameState.currentPlayer === 'red' && piece !== 'r') || (gameState.currentPlayer === 'black' && piece !== 'b')) {
        return false;
    }
    if (gameState.board[r2][c2] !== null) return false; // destination must be empty

    const dr = r2 - r1;
    const dc = c2 - c1;

    // Basic move: move diagonally forward by 1
    if (gameState.currentPlayer === 'red' && dr === -1 && Math.abs(dc) === 1) {
        return true;
    }
    if (gameState.currentPlayer === 'black' && dr === 1 && Math.abs(dc) === 1) {
        return true;
    }

    // Capture move: move diagonally forward by 2, jumping over opponent piece
    if (gameState.currentPlayer === 'red' && dr === -2 && Math.abs(dc) === 2) {
        const jumpedPiece = gameState.board[r1 - 1][c1 + (dc / 2)];
        if (jumpedPiece === 'b') return true;
    }
    if (gameState.currentPlayer === 'black' && dr === 2 && Math.abs(dc) === 2) {
        const jumpedPiece = gameState.board[r1 + 1][c1 + (dc / 2)];
        if (jumpedPiece === 'r') return true;
    }

    return false;
}

// Update the game state and UI after a valid move
function applyMove(moveData) {
    const { from, to } = moveData;
    const [r1, c1] = from;
    const [r2, c2] = to;
    const piece = gameState.board[r1][c1];
    gameState.board[r1][c1] = null;
    gameState.board[r2][c2] = piece;

    // Check if move was a capture
    if (Math.abs(r2 - r1) === 2) {
        const jumpedRow = (r1 + r2) / 2;
        const jumpedCol = (c1 + c2) / 2;
        gameState.board[jumpedRow][jumpedCol] = null;
    }

    // Switch player
    gameState.currentPlayer = gameState.currentPlayer === 'red' ? 'black' : 'red';

    updateUI();
}

// Update the UI to reflect the current game state
function updateUI() {
    // For simplicity, just display the board as text in the element
    let display = '';
    for (let row = 0; row < 8; row++) {
        for (let col = 0; col < 8; col++) {
            display += gameState.board[row][col] ? gameState.board[row][col] : '.';
            display += ' ';
        }
        display += '\n';
    }
    p.textContent = `Current player: ${gameState.currentPlayer}\n` + display;
}

ipcRenderer.on('update-pointer', (event, data) => {
    try {
        const parsed = JSON.parse(data);
        if (parsed.move) {
            const { start, end } = parsed.move;
            const moveData = { from: start, to: end };
            if (validateMove(moveData)) {
                applyMove(moveData);
            } else {
                console.warn('Invalid move detected:', moveData);
            }
        }
    } catch (e) {
        console.error('Failed to parse move data:', e);
    }
});

updateUI();

updateUI();