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
        
    def map_gesture_to_action(self, gesture, screen_dimensions: Tuple[int, int]) -> Optional[Dict]:
        """Convert gesture to game action using binary closed/open hand detection"""
        
        try:
            # Determine if hand is closed based on finger count
            if hasattr(gesture, 'finger_count') and gesture.finger_count is not None:
                # Ensure finger_count is a scalar value
                finger_count = gesture.finger_count
                if hasattr(finger_count, 'item'):  # numpy scalar
                    finger_count = finger_count.item()
                hand_closed = int(finger_count) == 0  # Only fully closed fist = closed, any fingers = open
                logger.debug(f"Binary gesture: {finger_count} fingers -> {'closed' if hand_closed else 'open'}")
            else:
                # Fallback to gesture type analysis
                hand_closed = gesture.gesture_type == 'grab'
                logger.debug(f"Fallback gesture: {gesture.gesture_type} -> {'closed' if hand_closed else 'open'}")
        except Exception as e:
            logger.error(f"Error determining hand state: {e}, gesture type: {getattr(gesture, 'gesture_type', 'unknown')}")
            # Safe fallback
            hand_closed = gesture.gesture_type == 'grab'
        
        # Update hand state with stability checking
        hand_state_changed = self._update_hand_state(hand_closed)
        
        # Map hand position to board coordinates
        board_pos = self._screen_to_board_coords(gesture.position, screen_dimensions)
        
        # Debounce actions (except for hover)
        current_time = time.time()
        if current_time - self.last_action_time < self.action_cooldown and hand_state_changed:
            return None
        
        # Handle state transitions
        if hand_state_changed:
            if self.is_hand_closed and not self.was_grabbing:
                # Just closed hand - select piece
                if board_pos:
                    self.selected_piece = board_pos
                    self.last_action_time = current_time
                    logger.info(f"GRAB START: Selected piece at {board_pos}")
                    return {
                        'type': GameAction.SELECT_PIECE.value,
                        'position': board_pos,
                        'confidence': gesture.confidence
                    }
                    
            elif not self.is_hand_closed and self.was_grabbing:
                # Just opened hand - complete move or cancel
                if self.selected_piece and board_pos:
                    logger.info(f"GRAB END: Moving piece from {self.selected_piece} to {board_pos}")
                    action = {
                        'type': GameAction.MOVE_PIECE.value,
                        'from': self.selected_piece,
                        'to': board_pos,
                        'confidence': gesture.confidence
                    }
                    self.selected_piece = None
                    self.last_action_time = current_time
                    return action
                elif self.selected_piece:
                    # No valid target - cancel
                    logger.info(f"GRAB END: Canceling selection (no valid target at {board_pos})")
                    self.selected_piece = None
                    self.last_action_time = current_time
                    return {
                        'type': GameAction.CANCEL.value,
                        'confidence': gesture.confidence
                    }
        
        # Continuous hover feedback when hand is open
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
            logger.info(f"HAND STATE CHANGE: open -> closed (confirmed: {closed_count}/{self.gesture_stability_threshold} frames)")
            self.was_grabbing = self.is_hand_closed
            self.is_hand_closed = True
            return True
        elif stable_open and self.is_hand_closed:
            logger.info(f"HAND STATE CHANGE: closed -> open (confirmed: {open_count}/{self.gesture_stability_threshold} frames)")
            self.was_grabbing = self.is_hand_closed
            self.is_hand_closed = False
            return True
        
        # No stable state change
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
        """Convert screen coordinates to board grid position"""
        if not screen_pos:
            return None
            
        x, y = screen_pos
        width, height = screen_dims
        
        # Define board area (centered square in the screen)
        board_size_pixels = min(width, height) * 0.8
        board_x_offset = (width - board_size_pixels) / 2
        board_y_offset = (height - board_size_pixels) / 2
        
        # Check if position is within board area
        if (x < board_x_offset or x > board_x_offset + board_size_pixels or
            y < board_y_offset or y > board_y_offset + board_size_pixels):
            return None
        
        # Normalize to board coordinates
        board_x = int((x - board_x_offset) / board_size_pixels * self.board_size)
        board_y = int((y - board_y_offset) / board_size_pixels * self.board_size)
        
        # Validate bounds
        if 0 <= board_x < self.board_size and 0 <= board_y < self.board_size:
            return (board_y, board_x)  # Return as (row, col)
        return None