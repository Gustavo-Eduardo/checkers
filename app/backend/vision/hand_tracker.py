import cv2
import numpy as np
from dataclasses import dataclass
from typing import List, Optional, Dict, Tuple

@dataclass
class HandGesture:
    gesture_type: str  # 'point', 'grab', 'release', 'hover'
    confidence: float
    position: Tuple[float, float]  # Normalized coordinates
    hand_landmarks: Optional[np.ndarray]

class HandTracker:
    """Simplified hand tracking for game input using color detection"""
    
    def __init__(self):
        self.last_position = None
        self.movement_threshold = 30  # pixels
        
    def detect_hands(self, frame: np.ndarray) -> Optional[Dict]:
        """Detect hand/object in frame using color detection"""
        # Convert to HSV for better color detection
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        
        # Define range for skin color detection (broader range for better detection)
        lower_skin = np.array([0, 30, 60], dtype=np.uint8)
        upper_skin = np.array([25, 255, 255], dtype=np.uint8)
        
        # Create mask for skin color
        mask = cv2.inRange(hsv, lower_skin, upper_skin)
        
        # Apply morphological operations to remove noise
        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        
        # Find contours
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Store debug information (JSON serializable only)
        debug_info = {
            'contour_count': len(contours),
            'all_areas': [float(cv2.contourArea(c)) for c in contours] if contours else [],
            'hsv_sample': None
        }
        
        if contours:
            # Find largest contour (assuming it's the hand)
            largest_contour = max(contours, key=cv2.contourArea)
            area = cv2.contourArea(largest_contour)
            
            # Filter out small contours (lowered threshold)
            if area > 1500:
                # Get bounding box
                x, y, w, h = cv2.boundingRect(largest_contour)
                
                # Get center point
                center_x = x + w // 2
                center_y = y + h // 2
                
                # Get topmost point (for pointing gesture)
                topmost = tuple(largest_contour[largest_contour[:, :, 1].argmin()][0])
                
                # Sample HSV values at center for debugging
                if 0 <= center_y < hsv.shape[0] and 0 <= center_x < hsv.shape[1]:
                    debug_info['hsv_sample'] = [int(hsv[center_y, center_x][i]) for i in range(3)]
                
                return {
                    'center': (int(center_x), int(center_y)),
                    'topmost': (int(topmost[0]), int(topmost[1])),
                    'bbox': (int(x), int(y), int(w), int(h)),
                    'area': float(area),
                    'debug': debug_info
                }
        
        return {
            'center': None,
            'debug': debug_info
        }

# DISABLED: Complex gesture recognition replaced with simple binary detection
# Use simple_hand_tracker.py for binary open/closed hand detection instead

# class GestureRecognizer:
#     """Recognize gestures based on hand detection"""
#     
#     def __init__(self):
#         self.gesture_history = []
#         self.history_size = 5
#         self.click_threshold = 50  # Movement threshold for click detection
#         self.last_position = None
#         self.stationary_frames = 0
#         
#     def recognize_gesture(self, hand_data: Dict) -> HandGesture:
#         """Classify hand gesture for game input"""
#         if not hand_data:
#             return HandGesture(
#                 gesture_type='none',
#                 confidence=0.0,
#                 position=(0, 0),
#                 hand_landmarks=None
#             )
#         
#         center = hand_data['center']
#         area = hand_data['area']
#         
#         # Track movement
#         if self.last_position:
#             movement = np.sqrt((center[0] - self.last_position[0])**2 + 
#                              (center[1] - self.last_position[1])**2)
#             
#             if movement < self.click_threshold:
#                 self.stationary_frames += 1
#             else:
#                 self.stationary_frames = 0
#         else:
#             movement = 0
#             self.stationary_frames = 0
#         
#         self.last_position = center
#         
#         # Determine gesture based on area changes and movement
#         gesture_type = 'hover'
#         confidence = 0.7
#         
#         # If hand is stationary for several frames, consider it a selection
#         if self.stationary_frames > 20:  # Increased threshold for more stable detection
#             gesture_type = 'point'
#             confidence = 0.9
#         
#         # Large area changes might indicate grab/release
#         if len(self.gesture_history) > 0:
#             avg_area = np.mean([h['area'] for h in self.gesture_history[-3:] if 'area' in h])
#             area_change = abs(area - avg_area) / avg_area if avg_area > 0 else 0
#             
#             if area_change > 0.3:
#                 if area > avg_area:
#                     gesture_type = 'release'
#                 else:
#                     gesture_type = 'grab'
#                 confidence = 0.8
#         
#         # Update history
#         self.gesture_history.append({'area': area, 'center': center})
#         if len(self.gesture_history) > self.history_size:
#             self.gesture_history.pop(0)
#         
#         # Use topmost point for more precise pointing
#         position = hand_data.get('topmost', center)
#         
#         return HandGesture(
#             gesture_type=gesture_type,
#             confidence=confidence,
#             position=position,
#             hand_landmarks=None
#         )