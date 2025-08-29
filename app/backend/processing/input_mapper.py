from enum import Enum
from typing import Optional, Tuple, Dict
import time
import logging

logger = logging.getLogger(__name__)

class GameAction(Enum):
    SELECT_PIECE = "select_piece"
    MOVE_PIECE = "move_piece"
    HOVER = "hover"
    CANCEL = "cancel"
    CONFIRM = "confirm"

class InputMapper:
    """Maps computer vision input to game actions"""
    
    def __init__(self, board_size: int = 8):
        self.board_size = board_size
        self.selected_piece = None
        self.hover_position = None
        self.click_position = None  # Track where hand was closed for release handling
        self.last_valid_position = None  # Track last valid board position during drag
        self.drag_start_position = None  # Track start position of drag for moves
        self.last_action_time = 0
        self.action_cooldown = 0.2  # Faster response for binary gestures
        self.hover_history = []  # Store recent hover positions for stability
        self.hover_stability_threshold = 2  # Reduced for faster hover response
        
        # Binary gesture state tracking
        self.is_hand_closed = False  # Track if hand is currently closed (grabbing)
        self.was_grabbing = False    # Track previous grabbing state
        self.gesture_stability_count = 0  # Count frames for gesture stability
        self.gesture_stability_threshold = 8  # Require more stability for state changes
        self.gesture_history = []  # Track recent gesture states
        self.gesture_history_size = 15  # Look at more frames for stability
        
    def update_game_state(self, selected_piece_position: Optional[Tuple[int, int]]):
        """Update internal state to match game state - critical for gesture flow"""
        if self.selected_piece != selected_piece_position:
            logger.info(f"InputMapper state sync: selected_piece {self.selected_piece} -> {selected_piece_position}")
            self.selected_piece = selected_piece_position
        
    def map_gesture_to_action(self, gesture, screen_dimensions: Tuple[int, int]) -> Optional[Dict]:
        """Convert gesture to game action replicating exact mouse behavior"""
        
        logger.debug(f"INPUT_MAPPER: Processing gesture - Type: {type(gesture).__name__}")
        
        try:
            # Check if using new SimpleHandGesture
            if hasattr(gesture, 'is_open'):
                # New simple binary detection
                hand_closed = not gesture.is_open  # is_open=False means hand is closed (grabbing)
                logger.debug(f"INPUT_MAPPER: Simple binary gesture - "
                          f"is_open={gesture.is_open}, hand_closed={hand_closed}")
            elif hasattr(gesture, 'finger_count') and gesture.finger_count is not None:
                # Legacy finger count detection
                finger_count = gesture.finger_count
                if hasattr(finger_count, 'item'):  # numpy scalar
                    finger_count = finger_count.item()
                hand_closed = int(finger_count) == 0  # Only fully closed fist = closed, any fingers = open
                logger.debug(f"INPUT_MAPPER: Legacy finger count - {finger_count} fingers -> {'closed' if hand_closed else 'open'}")
            else:
                # Fallback to gesture type analysis
                hand_closed = gesture.gesture_type == 'grab'
                logger.debug(f"INPUT_MAPPER: Fallback gesture type - {gesture.gesture_type} -> {'closed' if hand_closed else 'open'}")
        except Exception as e:
            logger.error(f"INPUT_MAPPER: Error determining hand state: {e}")
            # Safe fallback - assume open hand
            hand_closed = False
        
        # Update hand state with stability checking
        hand_state_changed = self._update_hand_state(hand_closed)
        
        # Map hand position to board coordinates
        logger.debug(f"INPUT_MAPPER: Gesture position: {gesture.position}, Screen dimensions: {screen_dimensions}")
        board_pos = self._screen_to_board_coords(gesture.position, screen_dimensions)
        
        logger.debug(f"INPUT_MAPPER: State tracking - "
                   f"current_closed={self.is_hand_closed}, "
                   f"was_grabbing={self.was_grabbing}, "
                   f"state_changed={hand_state_changed}, "
                   f"board_pos={board_pos}, "
                   f"selected_piece={self.selected_piece}")
        
        # EXACT MOUSE BEHAVIOR REPLICATION:
        # 1. OPEN hand = mouse movement (hover)
        # 2. OPEN→GRABBED = mouse click down (select piece) 
        # 3. GRABBED hand = mouse drag (piece stays selected)
        # 4. GRABBED→OPEN = mouse release (move piece or deselect)
        
        # Debounce major actions (selection/movement)
        current_time = time.time()
        if current_time - self.last_action_time < self.action_cooldown and hand_state_changed:
            return None
        
        # Handle state transitions (replicating mouse click behavior)
        if hand_state_changed:
            if self.is_hand_closed and not self.was_grabbing:
                # OPEN→GRABBED: Equivalent to mouse click down
                # This replicates handleMouseClick() logic exactly:
                # If no piece selected, select piece at position
                # If piece selected, this starts a potential move (handled on release)
                if board_pos:
                    logger.info(f"INPUT_MAPPER: GRAB GESTURE - Hand closed at {board_pos}")
                    self.last_action_time = current_time
                    
                    # Store positions for proper move handling
                    self.click_position = board_pos
                    self.drag_start_position = board_pos
                    self.last_valid_position = board_pos
                    
                    # If no piece currently selected, select piece immediately 
                    if not self.selected_piece:
                        action = {
                            'type': GameAction.SELECT_PIECE.value,
                            'position': board_pos,
                            'confidence': gesture.confidence
                        }
                        logger.info(f"INPUT_MAPPER: SELECT_PIECE action generated: {action}")
                        return action
                    # If piece is already selected, we're starting a move - handle on release
                    else:
                        logger.debug(f"INPUT_MAPPER: Piece already selected {self.selected_piece}, waiting for release")
                    
            elif not self.is_hand_closed and self.was_grabbing:
                # GRABBED→OPEN: Equivalent to mouse release
                # Use current position if valid, otherwise use last valid position during drag
                if board_pos:
                    release_pos = board_pos
                    self.last_valid_position = board_pos
                else:
                    # Hand moved outside board - use last valid position during drag
                    release_pos = self.last_valid_position or self.click_position
                
                if not self.selected_piece:
                    # No piece was selected - just select piece at release position
                    if release_pos:
                        logger.info(f"INPUT_MAPPER: Selecting piece at {release_pos}")
                        self.last_action_time = current_time
                        return {
                            'type': GameAction.SELECT_PIECE.value, 
                            'position': release_pos,
                            'confidence': gesture.confidence
                        }
                else:
                    # Piece was already selected - handle move/reselect/deselect
                    if release_pos:
                        if release_pos == self.selected_piece:
                            # Released on same piece - keep selected (like mouse)
                            logger.debug(f"INPUT_MAPPER: Maintaining selection of {self.selected_piece}")
                            return None
                        else:
                            # Released on different square - attempt move or reselect
                            logger.info(f"INPUT_MAPPER: Move attempt from {self.selected_piece} to {release_pos}")
                            action = {
                                'type': GameAction.MOVE_PIECE.value,
                                'from': self.selected_piece,
                                'to': release_pos,
                                'confidence': gesture.confidence
                            }
                            # Clear selection - backend will reselect if move is invalid but clicks valid piece
                            self.selected_piece = None
                            self.last_action_time = current_time
                            return action
                    else:
                        # Released outside board - cancel selection
                        logger.info(f"INPUT_MAPPER: Released outside board, cancelled selection of {self.selected_piece}")
                        self.selected_piece = None
                        self.last_action_time = current_time
                        return {
                            'type': GameAction.CANCEL.value,
                            'confidence': gesture.confidence
                        }
        
        # Continuous position tracking for drag support
        if board_pos:
            self.last_valid_position = board_pos
        
        # Continuous hover feedback (replicating mouse movement)
        # Only send hover events when hand is open (not dragging) - just like mouse hover
        if not self.is_hand_closed:
            stable_pos = self._get_stable_hover_position(board_pos)
            if stable_pos and stable_pos != self.hover_position:
                self.hover_position = stable_pos
                return {
                    'type': GameAction.HOVER.value,
                    'position': stable_pos,
                    'confidence': gesture.confidence
                }
        
        return None
    
    def _update_hand_state(self, hand_closed: bool) -> bool:
        """Update hand state with enhanced stability checking"""
        
        # Add current detection to history
        self.gesture_history.append(hand_closed)
        
        # Keep history at manageable size
        if len(self.gesture_history) > self.gesture_history_size:
            self.gesture_history.pop(0)
        
        # Need enough history to make a decision
        if len(self.gesture_history) < self.gesture_stability_threshold:
            logger.debug(f"INPUT_MAPPER: Building gesture history {len(self.gesture_history)}/{self.gesture_stability_threshold}")
            return False
        
        # Count recent detections
        recent_detections = self.gesture_history[-self.gesture_stability_threshold:]
        closed_count = sum(recent_detections)
        open_count = len(recent_detections) - closed_count
        
        # Determine stable state based on majority vote
        stable_closed = closed_count >= (self.gesture_stability_threshold * 0.75)  # 75% threshold
        stable_open = open_count >= (self.gesture_stability_threshold * 0.75)
        
        # Only change state if we have a strong majority
        if stable_closed and not self.is_hand_closed:
            logger.info(f"INPUT_MAPPER: Hand state change: open -> closed (confirmed: {closed_count}/{self.gesture_stability_threshold} frames)")
            self.was_grabbing = self.is_hand_closed
            self.is_hand_closed = True
            return True
        elif stable_open and self.is_hand_closed:
            logger.info(f"INPUT_MAPPER: Hand state change: closed -> open (confirmed: {open_count}/{self.gesture_stability_threshold} frames)")
            self.was_grabbing = self.is_hand_closed
            self.is_hand_closed = False
            return True
        
        # No stable state change
        logger.debug(f"INPUT_MAPPER: No state change - closed_votes:{closed_count}, open_votes:{open_count}, current_closed:{self.is_hand_closed}")
        return False
    
    def _get_stable_hover_position(self, board_pos: Optional[Tuple[int, int]]) -> Optional[Tuple[int, int]]:
        """Get stable hover position to reduce flickering"""
        # Add current position to history
        self.hover_history.append(board_pos)
        
        # Keep only recent positions
        if len(self.hover_history) > 10:
            self.hover_history.pop(0)
        
        if not board_pos:
            return None
        
        # Count occurrences of the current position
        count = sum(1 for pos in self.hover_history if pos == board_pos)
        
        # Return position only if it's stable enough
        if count >= min(self.hover_stability_threshold, len(self.hover_history)):
            return board_pos
        
        return None
    
    def _screen_to_board_coords(self, screen_pos: Tuple[float, float],
                                screen_dims: Tuple[int, int]) -> Optional[Tuple[int, int]]:
        """Convert screen coordinates to board grid position
        
        NOTE: screen_pos is in normalized coordinates (0-1), not pixel coordinates!
        """
        if not screen_pos:
            logger.debug(f"INPUT_MAPPER: _screen_to_board_coords - screen_pos is None")
            return None
            
        norm_x, norm_y = screen_pos  # These are 0-1 normalized coordinates
        width, height = screen_dims
        
        # Convert normalized coordinates to pixel coordinates
        x = norm_x * width
        y = norm_y * height
        
        logger.debug(f"INPUT_MAPPER: _screen_to_board_coords - Normalized: ({norm_x:.3f}, {norm_y:.3f}) -> Pixels: ({x:.1f}, {y:.1f}), Screen: ({width}, {height})")
        
        # Define board area - matches Board.js logic exactly (lines 34-35)
        # The board uses the full canvas size, not 80% of it
        board_size_pixels = min(width, height)
        board_x_offset = (width - board_size_pixels) / 2
        board_y_offset = (height - board_size_pixels) / 2
        
        logger.debug(f"INPUT_MAPPER: Board area - size:{board_size_pixels:.1f}px, x_offset:{board_x_offset:.1f}, y_offset:{board_y_offset:.1f}")
        
        # Check if position is within board area
        if (x < board_x_offset or x > board_x_offset + board_size_pixels or
            y < board_y_offset or y > board_y_offset + board_size_pixels):
            logger.debug(f"INPUT_MAPPER: Position outside board area - "
                       f"x:{x:.1f} not in [{board_x_offset:.1f}, {board_x_offset + board_size_pixels:.1f}], "
                       f"y:{y:.1f} not in [{board_y_offset:.1f}, {board_y_offset + board_size_pixels:.1f}]")
            return None
        
        # Normalize to board coordinates
        board_x = int((x - board_x_offset) / board_size_pixels * self.board_size)
        board_y = int((y - board_y_offset) / board_size_pixels * self.board_size)
        
        logger.debug(f"INPUT_MAPPER: Calculated board coords - board_x:{board_x}, board_y:{board_y}")
        
        # Validate bounds
        if 0 <= board_x < self.board_size and 0 <= board_y < self.board_size:
            result = (board_y, board_x)  # Return as (row, col)
            logger.debug(f"INPUT_MAPPER: Valid board position: {result}")
            return result
        
        logger.debug(f"INPUT_MAPPER: Board coords out of bounds - board_x:{board_x}, board_y:{board_y}")
        return None