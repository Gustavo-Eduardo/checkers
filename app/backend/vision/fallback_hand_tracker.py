import cv2
import numpy as np
from dataclasses import dataclass
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)

@dataclass
class SimpleHandGesture:
    """Simplified gesture with only binary open/closed state"""
    is_open: bool  # True = open hand (moving), False = closed hand (grabbing)
    confidence: float
    position: Tuple[float, float]  # Hand center position
    raw_area_ratio: float  # Raw convex hull area ratio for debugging
    extended_fingers: int  # Number of extended fingers (0-5)
    finger_distances: dict  # Debug info for finger tip distances

class FallbackHandTracker:
    """Simple fallback hand tracker for testing without MediaPipe"""
    
    def __init__(self):
        # State tracking for simulation
        self.current_state = True  # Start with open hand
        self.test_mode = True
        self.frame_counter = 0
        
        # For testing, we'll simulate hand gestures based on frame count
        # Much shorter sequence to see closed gestures quickly
        self.gesture_sequence = [
            # Pattern: open -> closed -> open -> closed (simulating grab gestures)
            *([True] * 8),    # Open for 8 frames  
            *([False] * 4),   # Closed for 4 frames
            *([True] * 8),    # Open for 8 frames
            *([False] * 4),   # Closed for 4 frames
        ]
        
    def detect_hand_state(self, frame: np.ndarray) -> Optional[SimpleHandGesture]:
        """Simulate hand detection for testing purposes"""
        
        # For demo purposes, simulate a hand in the center of the frame
        height, width = frame.shape[:2]
        center_x, center_y = width // 2, height // 2
        
        # Cycle through gesture sequence
        self.frame_counter += 1
        sequence_index = (self.frame_counter // 3) % len(self.gesture_sequence)  # Faster cycling
        is_open = self.gesture_sequence[sequence_index]
        
        # DEBUG: Log gesture cycling (reduced frequency)
        if self.frame_counter % 50 == 0:  # Log every 50 frames to reduce clutter
            logger.debug(f"FALLBACK_TRACKER: Frame {self.frame_counter}, Index {sequence_index}, is_open={is_open}, sequence_len={len(self.gesture_sequence)}")
        
        # Simulate movement towards actual piece positions for testing
        # Target board position (1, 0) which should have a red piece
        # Board area: centered square in screen, 80% of min(width, height)
        board_size_pixels = min(width, height) * 0.8
        board_x_offset = (width - board_size_pixels) / 2
        board_y_offset = (height - board_size_pixels) / 2
        
        # Convert board position (1, 0) to pixel position
        target_board_row, target_board_col = 1, 0  # This should have a red piece
        target_pixel_x = board_x_offset + (target_board_col + 0.5) * (board_size_pixels / 8)
        target_pixel_y = board_y_offset + (target_board_row + 0.5) * (board_size_pixels / 8)
        
        # Simulate gradual movement towards the target with some oscillation
        base_offset_x = int((target_pixel_x - center_x) * 0.8)
        base_offset_y = int((target_pixel_y - center_y) * 0.8)
        
        oscillation_x = int(20 * np.sin(self.frame_counter * 0.1))
        oscillation_y = int(15 * np.cos(self.frame_counter * 0.08))
        
        hand_x = center_x + base_offset_x + oscillation_x
        hand_y = center_y + base_offset_y + oscillation_y
        
        # Keep hand in bounds
        hand_x = max(50, min(width - 50, hand_x))
        hand_y = max(50, min(height - 50, hand_y))
        
        # Normalize position to 0-1 range
        normalized_position = (hand_x / width, hand_y / height)
        
        # Simulate confidence and other values
        confidence = 0.8 + 0.1 * np.sin(self.frame_counter * 0.1)
        extended_fingers = 3 if is_open else 0
        area_ratio = 0.8 if is_open else 0.4
        
        return SimpleHandGesture(
            is_open=is_open,
            confidence=confidence,
            position=normalized_position,
            raw_area_ratio=area_ratio,
            extended_fingers=extended_fingers,
            finger_distances={'simulated': 1.0}
        )
    
    def create_debug_frame(self, frame: np.ndarray, gesture: Optional[SimpleHandGesture]) -> np.ndarray:
        """Create debug visualization frame with cursor"""
        
        debug_frame = frame.copy()
        height, width = frame.shape[:2]
        
        if gesture:
            # Convert normalized position back to pixel coordinates for drawing
            x, y = int(gesture.position[0] * width), int(gesture.position[1] * height)
            
            # Draw cursor with color based on hand state
            if gesture.is_open:
                # Blue cursor for open hand (moving state)
                color = (255, 100, 0)  # Blue in BGR
                cursor_text = "OPEN (Moving)"
            else:
                # Orange cursor for closed hand (grabbing state)
                color = (0, 165, 255)  # Orange in BGR
                cursor_text = "GRABBING"
            
            # Draw cursor
            cv2.circle(debug_frame, (x, y), 15, color, -1)
            cv2.circle(debug_frame, (x, y), 18, (255, 255, 255), 2)
            
            # Add crosshair
            cv2.line(debug_frame, (x-10, y), (x+10, y), (255, 255, 255), 2)
            cv2.line(debug_frame, (x, y-10), (x, y+10), (255, 255, 255), 2)
            
            # Display state information
            cv2.putText(debug_frame, cursor_text, 
                       (x + 25, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
            
            # Display debug info
            cv2.putText(debug_frame, f'FALLBACK TRACKER (Testing)', 
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
            cv2.putText(debug_frame, f'Confidence: {gesture.confidence:.2f}', 
                       (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
            cv2.putText(debug_frame, f'Extended Fingers: {gesture.extended_fingers}', 
                       (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
            cv2.putText(debug_frame, f'Area Ratio: {gesture.raw_area_ratio:.3f}', 
                       (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
            
            # Show detection method info
            cv2.putText(debug_frame, f'SIMULATED: 0-1=CLOSED, 2+=OPEN', 
                       (10, debug_frame.shape[0] - 60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 255, 100), 1)
            cv2.putText(debug_frame, f'Frame: {self.frame_counter}', 
                       (10, debug_frame.shape[0] - 40), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 255, 100), 1)
            cv2.putText(debug_frame, 'Fallback Hand Tracker (No MediaPipe)', 
                       (10, debug_frame.shape[0] - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
        else:
            # No hand detected
            cv2.putText(debug_frame, 'No hand detected', 
                       (debug_frame.shape[1]//2 - 100, debug_frame.shape[0]//2), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        
        return debug_frame