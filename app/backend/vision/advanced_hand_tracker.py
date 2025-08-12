import cv2
import numpy as np
from dataclasses import dataclass
from typing import List, Optional, Dict, Tuple
from sklearn.cluster import DBSCAN
import time

@dataclass
class HandGesture:
    gesture_type: str  # 'point', 'grab', 'release', 'hover'
    confidence: float
    position: Tuple[float, float]  # Normalized coordinates
    hand_landmarks: Optional[np.ndarray]

class AdvancedHandTracker:
    """Advanced hand tracking using multiple techniques for improved accuracy"""
    
    def __init__(self):
        self.background_subtractor = cv2.createBackgroundSubtractorMOG2(detectShadows=False)
        self.last_position = None
        self.movement_threshold = 30
        self.calibration_frames = []
        self.calibrated = False
        self.skin_model = None
        self.hand_cascade = None
        
        # Try to load hand cascade classifier
        try:
            self.hand_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_hand.xml')
        except:
            # If not available, we'll use other methods
            pass
            
    def detect_hands(self, frame: np.ndarray) -> Optional[Dict]:
        """Detect hand using multiple advanced techniques"""
        
        # Technique 1: Motion-based detection with background subtraction
        motion_contours = self._detect_motion_based(frame)
        
        # Technique 2: Improved skin detection with calibration
        skin_contours = self._detect_skin_advanced(frame)
        
        # Technique 3: Edge-based hand detection
        edge_contours = self._detect_edge_based(frame)
        
        # Combine and filter results
        all_candidates = []
        
        # Process motion contours
        for contour in motion_contours:
            candidate = self._analyze_contour(contour, frame, "motion")
            if candidate:
                all_candidates.append(candidate)
                
        # Process skin contours  
        for contour in skin_contours:
            candidate = self._analyze_contour(contour, frame, "skin")
            if candidate:
                all_candidates.append(candidate)
                
        # Process edge contours
        for contour in edge_contours:
            candidate = self._analyze_contour(contour, frame, "edge")
            if candidate:
                all_candidates.append(candidate)
        
        # Find best candidate using multiple criteria
        best_candidate = self._select_best_candidate(all_candidates, frame)
        
        return best_candidate
        
    def _detect_motion_based(self, frame: np.ndarray) -> List[np.ndarray]:
        """Detect moving objects (likely hands)"""
        # Apply background subtraction
        fg_mask = self.background_subtractor.apply(frame)
        
        # Clean up the mask
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, kernel)
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_CLOSE, kernel)
        
        # Find contours
        contours, _ = cv2.findContours(fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Filter by size and shape
        filtered_contours = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if 1000 < area < 15000:  # Hand-sized objects
                # Check if shape is roughly hand-like
                hull = cv2.convexHull(contour)
                hull_area = cv2.contourArea(hull)
                solidity = area / hull_area if hull_area > 0 else 0
                
                if 0.5 < solidity < 0.95:  # Hands have moderate solidity
                    filtered_contours.append(contour)
                    
        return filtered_contours
        
    def _detect_skin_advanced(self, frame: np.ndarray) -> List[np.ndarray]:
        """Advanced skin detection with multiple color spaces"""
        
        # Convert to multiple color spaces
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        ycrcb = cv2.cvtColor(frame, cv2.COLOR_BGR2YCrCb)
        
        # HSV skin detection (improved ranges)
        lower_hsv = np.array([0, 20, 70], dtype=np.uint8)
        upper_hsv = np.array([20, 255, 255], dtype=np.uint8)
        mask_hsv = cv2.inRange(hsv, lower_hsv, upper_hsv)
        
        # YCrCb skin detection (more robust)
        lower_ycrcb = np.array([0, 133, 77], dtype=np.uint8)
        upper_ycrcb = np.array([255, 173, 127], dtype=np.uint8)
        mask_ycrcb = cv2.inRange(ycrcb, lower_ycrcb, upper_ycrcb)
        
        # Combine masks
        skin_mask = cv2.bitwise_and(mask_hsv, mask_ycrcb)
        
        # Advanced filtering
        kernel = np.ones((3, 3), np.uint8)
        skin_mask = cv2.morphologyEx(skin_mask, cv2.MORPH_OPEN, kernel, iterations=2)
        skin_mask = cv2.morphologyEx(skin_mask, cv2.MORPH_CLOSE, kernel, iterations=2)
        
        # Remove small noise
        kernel = np.ones((5, 5), np.uint8)
        skin_mask = cv2.morphologyEx(skin_mask, cv2.MORPH_OPEN, kernel)
        
        # Find contours
        contours, _ = cv2.findContours(skin_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        return contours
        
    def _detect_edge_based(self, frame: np.ndarray) -> List[np.ndarray]:
        """Detect hands using edge detection and shape analysis"""
        
        # Convert to grayscale
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Apply Gaussian blur
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        
        # Edge detection
        edges = cv2.Canny(blurred, 50, 150)
        
        # Dilate edges to connect broken lines
        kernel = np.ones((3, 3), np.uint8)
        edges = cv2.dilate(edges, kernel, iterations=1)
        
        # Find contours
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Filter by size and complexity
        filtered_contours = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if 2000 < area < 20000:
                # Check contour complexity (hands have moderate complexity)
                perimeter = cv2.arcLength(contour, True)
                if perimeter > 0:
                    circularity = 4 * np.pi * area / (perimeter * perimeter)
                    if 0.1 < circularity < 0.7:  # Not too circular, not too complex
                        filtered_contours.append(contour)
                        
        return filtered_contours
        
    def _analyze_contour(self, contour: np.ndarray, frame: np.ndarray, detection_type: str) -> Optional[Dict]:
        """Analyze a contour to determine if it's a hand"""
        
        area = cv2.contourArea(contour)
        if area < 1500:  # Too small
            return None
            
        # Get bounding rectangle
        x, y, w, h = cv2.boundingRect(contour)
        
        # Check aspect ratio (hands are roughly rectangular but not too extreme)
        aspect_ratio = w / h if h > 0 else 0
        if aspect_ratio < 0.3 or aspect_ratio > 3.0:
            return None
            
        # Get center point
        center_x = x + w // 2
        center_y = y + h // 2
        
        # Get convex hull and defects for finger detection
        hull = cv2.convexHull(contour, returnPoints=False)
        if len(hull) > 3:
            try:
                defects = cv2.convexityDefects(contour, hull)
                finger_count = self._count_fingers(contour, defects) if defects is not None else 0
            except:
                finger_count = 0
        else:
            finger_count = 0
            
        # Calculate confidence based on multiple factors
        confidence = self._calculate_confidence(contour, detection_type, finger_count, aspect_ratio)
        
        if confidence < 0.3:
            return None
            
        # Find topmost point for pointing
        topmost = tuple(contour[contour[:, :, 1].argmin()][0])
        
        # Calculate hand orientation and palm center
        palm_center = self._find_palm_center(contour)
        
        return {
            'center': (int(center_x), int(center_y)),
            'topmost': (int(topmost[0]), int(topmost[1])),
            'palm_center': palm_center,
            'bbox': (int(x), int(y), int(w), int(h)),
            'area': float(area),
            'confidence': float(confidence),
            'finger_count': finger_count,
            'detection_type': detection_type,
            'aspect_ratio': float(aspect_ratio),
            'debug': {
                'contour_count': 1,
                'all_areas': [float(area)],
                'detection_method': detection_type,
                'finger_count': finger_count
            }
        }
        
    def _count_fingers(self, contour: np.ndarray, defects: np.ndarray) -> int:
        """Count extended fingers using convexity defects"""
        if defects is None:
            return 0
            
        finger_count = 0
        for i in range(defects.shape[0]):
            s, e, f, d = defects[i, 0]
            start = tuple(contour[s][0])
            end = tuple(contour[e][0])
            far = tuple(contour[f][0])
            
            # Calculate distances
            a = np.sqrt((end[0] - start[0])**2 + (end[1] - start[1])**2)
            b = np.sqrt((far[0] - start[0])**2 + (far[1] - start[1])**2)
            c = np.sqrt((end[0] - far[0])**2 + (end[1] - far[1])**2)
            
            # Calculate angle using cosine rule
            if b > 0 and c > 0:
                angle = np.arccos((b**2 + c**2 - a**2) / (2 * b * c))
                
                # If angle is less than 90 degrees and defect depth is significant
                if angle <= np.pi/2 and d > 2000:
                    finger_count += 1
                    
        return min(finger_count, 5)  # Maximum 5 fingers
        
    def _find_palm_center(self, contour: np.ndarray) -> Tuple[int, int]:
        """Find the center of the palm (more stable than centroid)"""
        # Find the largest inscribed circle center
        dist_transform = cv2.distanceTransform(
            np.zeros((480, 640), dtype=np.uint8), 
            cv2.DIST_L2, 5
        )
        
        # For now, use centroid as approximation
        M = cv2.moments(contour)
        if M["m00"] != 0:
            center_x = int(M["m10"] / M["m00"])
            center_y = int(M["m01"] / M["m00"])
            return (center_x, center_y)
        else:
            x, y, w, h = cv2.boundingRect(contour)
            return (x + w//2, y + h//2)
            
    def _calculate_confidence(self, contour: np.ndarray, detection_type: str, finger_count: int, aspect_ratio: float) -> float:
        """Calculate confidence score based on multiple factors"""
        confidence = 0.5  # Base confidence
        
        # Area factor
        area = cv2.contourArea(contour)
        if 3000 < area < 12000:  # Ideal hand size
            confidence += 0.2
        elif 1500 < area < 20000:  # Acceptable range
            confidence += 0.1
        else:
            confidence -= 0.1
            
        # Aspect ratio factor
        if 0.5 < aspect_ratio < 2.0:  # Good hand proportions
            confidence += 0.15
        elif 0.3 < aspect_ratio < 3.0:  # Acceptable
            confidence += 0.05
            
        # Detection type factor
        if detection_type == "motion":
            confidence += 0.1  # Motion is good indicator
        elif detection_type == "skin":
            confidence += 0.05
            
        # Finger count factor
        if 3 <= finger_count <= 5:
            confidence += 0.1
        elif 1 <= finger_count <= 2:
            confidence += 0.05
            
        # Convexity factor
        hull = cv2.convexHull(contour)
        hull_area = cv2.contourArea(hull)
        if hull_area > 0:
            solidity = area / hull_area
            if 0.7 < solidity < 0.95:  # Good hand solidity
                confidence += 0.1
                
        return min(confidence, 1.0)
        
    def _select_best_candidate(self, candidates: List[Dict], frame: np.ndarray) -> Optional[Dict]:
        """Select the best hand candidate from multiple detections"""
        if not candidates:
            return None
            
        if len(candidates) == 1:
            return candidates[0]
            
        # Score candidates based on multiple criteria
        scored_candidates = []
        for candidate in candidates:
            score = candidate['confidence']
            
            # Prefer candidates closer to previous position
            if self.last_position:
                distance = np.sqrt(
                    (candidate['center'][0] - self.last_position[0])**2 + 
                    (candidate['center'][1] - self.last_position[1])**2
                )
                # Bonus for continuity (closer to last position)
                if distance < 100:
                    score += 0.2
                elif distance < 200:
                    score += 0.1
                    
            # Prefer candidates in upper part of frame (hands are usually raised)
            frame_height = frame.shape[0]
            y_position = candidate['center'][1]
            if y_position < frame_height * 0.7:  # Upper 70% of frame
                score += 0.1
                
            # Prefer moderate sizes
            area = candidate['area']
            if 3000 < area < 10000:
                score += 0.1
                
            scored_candidates.append((score, candidate))
            
        # Return the highest scoring candidate
        scored_candidates.sort(key=lambda x: x[0], reverse=True)
        best_candidate = scored_candidates[0][1]
        
        # Update last position
        self.last_position = best_candidate['center']
        
        return best_candidate

class GestureRecognizer:
    """Enhanced gesture recognition with better stability"""
    
    def __init__(self):
        self.gesture_history = []
        self.history_size = 10
        self.click_threshold = 40
        self.last_position = None
        self.stationary_frames = 0
        self.pointing_threshold = 30  # Increased for more stable pointing
        
    def recognize_gesture(self, hand_data: Dict) -> HandGesture:
        """Enhanced gesture classification"""
        if not hand_data or not hand_data.get('center'):
            return HandGesture(
                gesture_type='none',
                confidence=0.0,
                position=(0, 0),
                hand_landmarks=None
            )
        
        center = hand_data['center']
        area = hand_data['area']
        finger_count = hand_data.get('finger_count', 0)
        
        # Track movement stability
        if self.last_position:
            movement = np.sqrt((center[0] - self.last_position[0])**2 + 
                             (center[1] - self.last_position[1])**2)
            
            if movement < self.click_threshold:
                self.stationary_frames += 1
            else:
                self.stationary_frames = 0
        else:
            movement = 0
            self.stationary_frames = 0
            
        self.last_position = center
        
        # Enhanced gesture determination
        gesture_type = 'hover'
        confidence = hand_data.get('confidence', 0.5)
        
        # Pointing gesture - requires stability AND finger detection
        if self.stationary_frames > self.pointing_threshold:
            if finger_count == 1:  # Index finger pointing
                gesture_type = 'point'
                confidence = min(confidence + 0.3, 1.0)
            elif finger_count >= 2:  # Multiple fingers - less confident pointing
                gesture_type = 'point'
                confidence = min(confidence + 0.1, 1.0)
            else:
                gesture_type = 'point'  # Fallback to position-based
                
        # Grab gesture - closed fist (low finger count, compact shape)
        elif finger_count == 0 and area < 5000:
            gesture_type = 'grab'
            confidence = min(confidence + 0.2, 1.0)
            
        # Release gesture - open hand (many fingers, larger area)
        elif finger_count >= 4 and area > 8000:
            gesture_type = 'release'
            confidence = min(confidence + 0.2, 1.0)
            
        # Update history for smoothing
        self.gesture_history.append({
            'area': area, 
            'center': center, 
            'gesture': gesture_type,
            'fingers': finger_count
        })
        if len(self.gesture_history) > self.history_size:
            self.gesture_history.pop(0)
            
        # Use palm center for more accurate pointing
        position = hand_data.get('palm_center', hand_data.get('topmost', center))
        
        return HandGesture(
            gesture_type=gesture_type,
            confidence=confidence,
            position=position,
            hand_landmarks=None
        )