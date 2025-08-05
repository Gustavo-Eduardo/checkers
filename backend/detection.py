import cv2
import numpy as np
import sys
import json
import time
import math
from collections import deque
from dataclasses import dataclass
from typing import Optional, Tuple, List

@dataclass
class MarkerPosition:
    x: int
    y: int
    confidence: float
    timestamp: float
    
@dataclass
class GestureState:
    state: str  # 'NONE', 'HOVER', 'SELECT', 'DRAG'
    position: Optional[MarkerPosition]
    duration: float
    stability_score: float

class GestureRecognizer:
    def __init__(self):
        self.current_state = 'NONE'
        self.dwell_start = None
        self.dwell_threshold = 1.0  # seconds to trigger selection
        self.last_position = None
        self.movement_threshold = 20  # pixels
        self.state_history = deque(maxlen=5)
        
    def update(self, position: Optional[MarkerPosition]) -> GestureState:
        """Update gesture recognition state"""
        current_time = time.time()
        
        if position is None:
            self.current_state = 'NONE'
            self.dwell_start = None
            self.last_position = None
            return GestureState('NONE', None, 0, 0)
        
        # Calculate movement if we have a previous position
        movement = 0
        if self.last_position:
            movement = math.sqrt((position.x - self.last_position.x)**2 +
                               (position.y - self.last_position.y)**2)
        
        # State transitions
        if self.current_state == 'NONE':
            self.current_state = 'HOVER'
            self.dwell_start = current_time
            
        elif self.current_state == 'HOVER':
            if movement < self.movement_threshold:
                if self.dwell_start and current_time - self.dwell_start > self.dwell_threshold:
                    self.current_state = 'SELECT'
            else:
                self.dwell_start = current_time  # Reset dwell timer
                
        elif self.current_state == 'SELECT':
            if movement > self.movement_threshold:
                self.current_state = 'DRAG'
                
        elif self.current_state == 'DRAG':
            if movement < self.movement_threshold / 2:
                # Slow movement might indicate end of drag
                self.current_state = 'SELECT'
        
        duration = current_time - self.dwell_start if self.dwell_start else 0
        stability_score = max(0, 1 - (movement / self.movement_threshold))
        
        self.last_position = position
        self.state_history.append(self.current_state)
        
        return GestureState(
            state=self.current_state,
            position=position,
            duration=duration,
            stability_score=stability_score
        )

class EnhancedDetection:
    def __init__(self):
        self.cap = cv2.VideoCapture(0)
        self.position_history = deque(maxlen=10)
        self.gesture_recognizer = GestureRecognizer()
        self.kalman_filter = self.init_kalman_filter()
        self.kalman_initialized = False
        
        # Detection parameters
        self.min_contour_area = 500
        self.stability_threshold = 15  # pixels
        self.confidence_threshold = 0.3
        
    def init_kalman_filter(self):
        """Initialize Kalman filter for position smoothing"""
        kf = cv2.KalmanFilter(4, 2)
        kf.measurementMatrix = np.array([[1, 0, 0, 0],
                                        [0, 1, 0, 0]], np.float32)
        kf.transitionMatrix = np.array([[1, 0, 1, 0],
                                       [0, 1, 0, 1],
                                       [0, 0, 1, 0],
                                       [0, 0, 0, 1]], np.float32)
        kf.processNoiseCov = 0.03 * np.eye(4, dtype=np.float32)
        kf.measurementNoiseCov = 0.1 * np.eye(2, dtype=np.float32)
        return kf
        
    def detect_marker(self, frame) -> Optional[MarkerPosition]:
        """Enhanced red marker detection with confidence scoring"""
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        
        # Red color ranges (broader range for better detection)
        lower_red1 = np.array([0, 50, 50])
        upper_red1 = np.array([10, 255, 255])
        lower_red2 = np.array([160, 50, 50])
        upper_red2 = np.array([179, 255, 255])
        
        mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
        mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
        mask = cv2.bitwise_or(mask1, mask2)
        
        # Enhanced morphological operations
        kernel = np.ones((5,5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            return None
            
        # Find best contour
        largest_contour = max(contours, key=cv2.contourArea)
        area = cv2.contourArea(largest_contour)
        
        if area < self.min_contour_area:
            return None
            
        # Calculate position and confidence
        (x, y, w, h) = cv2.boundingRect(largest_contour)
        center_x = x + w // 2
        center_y = y + h // 2
        
        # Enhanced confidence calculation
        perimeter = cv2.arcLength(largest_contour, True)
        if perimeter > 0:
            circularity = 4 * math.pi * area / (perimeter * perimeter)
        else:
            circularity = 0
            
        # Aspect ratio confidence
        aspect_ratio = w / h if h > 0 else 0
        aspect_confidence = 1 - abs(1 - aspect_ratio) if aspect_ratio > 0 else 0
        
        # Size confidence (bigger is better, up to a point)
        size_confidence = min(1.0, area / 2000)
        
        # Combined confidence
        confidence = (circularity * 0.4 + aspect_confidence * 0.3 + size_confidence * 0.3)
        confidence = max(0, min(1, confidence))
        
        return MarkerPosition(
            x=center_x,
            y=center_y,
            confidence=confidence,
            timestamp=time.time()
        )
        
    def smooth_position(self, position: MarkerPosition) -> MarkerPosition:
        """Apply Kalman filtering for smooth tracking"""
        measurement = np.array([[position.x], [position.y]], dtype=np.float32)
        
        if not self.kalman_initialized:
            self.kalman_filter.statePre = np.array([position.x, position.y, 0, 0], dtype=np.float32)
            self.kalman_filter.statePost = np.array([position.x, position.y, 0, 0], dtype=np.float32)
            self.kalman_initialized = True
            return position
            
        self.kalman_filter.correct(measurement)
        prediction = self.kalman_filter.predict()
        
        return MarkerPosition(
            x=int(prediction[0]),
            y=int(prediction[1]),
            confidence=position.confidence,
            timestamp=position.timestamp
        )
        
    def is_position_stable(self, position: MarkerPosition) -> bool:
        """Check if position is stable based on recent history"""
        if len(self.position_history) < 5:
            return False
            
        recent_positions = list(self.position_history)[-5:]
        avg_x = sum(p.x for p in recent_positions) / 5
        avg_y = sum(p.y for p in recent_positions) / 5
        
        distance = math.sqrt((position.x - avg_x)**2 + (position.y - avg_y)**2)
        return distance < self.stability_threshold
        
    def run(self):
        """Main detection loop"""
        while True:
            ret, frame = self.cap.read()
            if not ret:
                break
                
            frame = cv2.flip(frame, 1)  # Mirror effect
            
            # Detect marker
            marker_pos = self.detect_marker(frame)
            
            if marker_pos and marker_pos.confidence > self.confidence_threshold:
                # Smooth position
                smoothed_pos = self.smooth_position(marker_pos)
                self.position_history.append(smoothed_pos)
                
                # Check stability
                is_stable = self.is_position_stable(smoothed_pos)
                
                # Update gesture recognition
                gesture_state = self.gesture_recognizer.update(smoothed_pos)
                
                # Send enhanced data to frontend
                output_data = {
                    "camera_dimension": {"x": frame.shape[1], "y": frame.shape[0]},
                    "marker": {
                        "x": smoothed_pos.x,
                        "y": smoothed_pos.y,
                        "confidence": smoothed_pos.confidence,
                        "stable": is_stable
                    },
                    "gesture": {
                        "state": gesture_state.state,
                        "duration": gesture_state.duration,
                        "stability": gesture_state.stability_score
                    },
                    "timestamp": time.time()
                }
                
                print(json.dumps(output_data))
                sys.stdout.flush()
            else:
                # Send no detection data
                no_detection = {
                    "camera_dimension": {"x": frame.shape[1], "y": frame.shape[0]},
                    "marker": None,
                    "gesture": {"state": "NONE", "duration": 0, "stability": 0},
                    "timestamp": time.time()
                }
                self.gesture_recognizer.update(None)
                print(json.dumps(no_detection))
                sys.stdout.flush()
                
            # Exit on 'q' key
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        
        self.cap.release()
        cv2.destroyAllWindows()

def main():
    detector = EnhancedDetection()
    detector.run()

if __name__ == "__main__":
    main()

