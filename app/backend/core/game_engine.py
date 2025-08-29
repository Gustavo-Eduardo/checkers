from typing import List, Optional, Tuple, Dict
import numpy as np
import logging

logger = logging.getLogger(__name__)

class CheckersEngine:
    """Core checkers game logic"""
    
    def __init__(self):
        self.board = np.zeros((8, 8), dtype=int)
        self.current_player = 1  # 1: red, -1: black
        self.move_history = []
        self.initialize_board()
        
    def initialize_board(self):
        """Set up initial board state"""
        logger.info("GAME_ENGINE: Initializing new game board")
        self.board = np.zeros((8, 8), dtype=int)
        
        # Red pieces (player 1) - top of board
        for row in range(3):
            for col in range(8):
                if (row + col) % 2 == 1:
                    self.board[row][col] = 1
                    
        # Black pieces (player -1) - bottom of board
        for row in range(5, 8):
            for col in range(8):
                if (row + col) % 2 == 1:
                    self.board[row][col] = -1
                    
        self.current_player = 1
        self.move_history = []
    
    def get_valid_moves(self, position: Tuple[int, int]) -> List[Tuple[int, int]]:
        """Get all valid moves for a piece at given position"""
        row, col = position
        piece = self.board[row][col]
        
        if piece == 0 or piece * self.current_player <= 0:
            return []
            
        moves = []
        is_king = abs(piece) == 2
        
        # Determine movement directions based on piece type
        if is_king:
            directions = [(-1, -1), (-1, 1), (1, -1), (1, 1)]
        elif piece == 1:  # Red moves down
            directions = [(1, -1), (1, 1)]
        else:  # Black moves up
            directions = [(-1, -1), (-1, 1)]
            
        # Check regular moves and captures
        for dr, dc in directions:
            # Regular move
            new_row, new_col = row + dr, col + dc
            if self._is_valid_position(new_row, new_col) and self.board[new_row][new_col] == 0:
                moves.append((new_row, new_col))
                
            # Capture move
            mid_row, mid_col = row + dr, col + dc
            jump_row, jump_col = row + 2*dr, col + 2*dc
            
            if (self._is_valid_position(jump_row, jump_col) and 
                self._is_valid_position(mid_row, mid_col) and
                self.board[jump_row][jump_col] == 0 and
                self.board[mid_row][mid_col] != 0 and
                self.board[mid_row][mid_col] * piece < 0):  # Enemy piece
                moves.append((jump_row, jump_col))
                
        return moves
    
    def get_all_valid_moves(self) -> Dict[Tuple[int, int], List[Tuple[int, int]]]:
        """Get all valid moves for current player"""
        all_moves = {}
        for row in range(8):
            for col in range(8):
                if self.board[row][col] * self.current_player > 0:
                    moves = self.get_valid_moves((row, col))
                    if moves:
                        all_moves[(row, col)] = moves
        return all_moves
    
    def make_move(self, from_pos: Tuple[int, int], to_pos: Tuple[int, int]) -> Dict:
        """Execute a move and return game state update"""
        valid_moves = self.get_valid_moves(from_pos)
        if to_pos not in valid_moves:
            logger.info(f"GAME_ENGINE: Invalid move attempted - from {from_pos} to {to_pos} (valid moves: {valid_moves})")
            return {'valid': False, 'error': 'Invalid move'}
            
        from_row, from_col = from_pos
        to_row, to_col = to_pos
        piece = self.board[from_row][from_col]
        
        # Move piece
        self.board[to_row][to_col] = piece
        self.board[from_row][from_col] = 0
        
        # Check for capture
        captured = None
        if abs(to_row - from_row) == 2:
            mid_row = (from_row + to_row) // 2
            mid_col = (from_col + to_col) // 2
            captured = (mid_row, mid_col)
            self.board[mid_row][mid_col] = 0
            logger.info(f"GAME_ENGINE: Piece captured at {captured}")
            
        # Check for king promotion
        promoted = False
        if piece == 1 and to_row == 7:  # Red reaches bottom
            self.board[to_row][to_col] = 2
            promoted = True
            logger.info(f"GAME_ENGINE: Red piece promoted to king at {to_pos}")
        elif piece == -1 and to_row == 0:  # Black reaches top
            self.board[to_row][to_col] = -2
            promoted = True
            logger.info(f"GAME_ENGINE: Black piece promoted to king at {to_pos}")
            
        # Switch players
        self.current_player *= -1
        player_name = "Red" if self.current_player == 1 else "Black"
        logger.info(f"GAME_ENGINE: Valid move executed - {from_pos} to {to_pos}. Turn passed to {player_name}")
        
        # Record move
        move_record = {
            'from': from_pos,
            'to': to_pos,
            'captured': captured,
            'promoted': promoted,
            'player': -self.current_player  # Previous player
        }
        self.move_history.append(move_record)
        
        return {
            'valid': True,
            'move': move_record,
            'board_state': self.board.tolist(),
            'current_player': self.current_player,
            'game_over': self.check_game_over(),
            'all_valid_moves': self.get_all_valid_moves()
        }
    
    def _is_valid_position(self, row: int, col: int) -> bool:
        """Check if position is within board bounds"""
        return 0 <= row < 8 and 0 <= col < 8
    
    def check_game_over(self) -> Optional[int]:
        """Check if game is over and return winner"""
        red_pieces = np.sum(self.board > 0)
        black_pieces = np.sum(self.board < 0)
        
        if red_pieces == 0:
            logger.info("GAME_ENGINE: Game Over - Black wins (no red pieces remaining)")
            return -1  # Black wins
        elif black_pieces == 0:
            logger.info("GAME_ENGINE: Game Over - Red wins (no black pieces remaining)")
            return 1  # Red wins
            
        # Check if current player has any valid moves
        has_moves = False
        for row in range(8):
            for col in range(8):
                if self.board[row][col] * self.current_player > 0:
                    if self.get_valid_moves((row, col)):
                        has_moves = True
                        break
            if has_moves:
                break
                
        if not has_moves:
            winner_name = "Red" if -self.current_player == 1 else "Black"
            current_name = "Red" if self.current_player == 1 else "Black"
            logger.info(f"GAME_ENGINE: Game Over - {winner_name} wins ({current_name} has no valid moves)")
            return -self.current_player  # Other player wins
            
        return None
        
    def get_piece_counts(self) -> Dict[str, int]:
        """Get count of pieces for each player"""
        return {
            'red': np.sum(self.board > 0),
            'black': np.sum(self.board < 0),
            'red_kings': np.sum(self.board == 2),
            'black_kings': np.sum(self.board == -2)
        }