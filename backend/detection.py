import cv2
import numpy as np
import sys
import json
import time
import math
from collections import deque
from dataclasses import dataclass, asdict
from typing import Optional, Tuple, List, Dict, Any

@dataclass
class MarkerPosition:
    x: int
    y: int
    confidence: float
    timestamp: float
    area: float = 0.0
    circularity: float = 0.0
    convexity: float = 0.0
    
@dataclass
class QualityMetrics:
    geometric_score: float
    color_score: float
    uniformity_score: float
    temporal_score: float
    area: float
    circularity: float
    convexity: float

@dataclass
class DetectionDebugInfo:
    candidates_found: int
    passed_geometry: int
    passed_uniformity: int
    final_confidence_factors: List[float]

@dataclass
class GestureState:
    state: str  # 'NONE', 'HOVER', 'SELECT', 'DRAG'
    position: Optional[MarkerPosition]
    duration: float
    stability_score: float

class AdaptiveColorDetector:
    def __init__(self):
        # Much more restrictive HSV ranges for markers vs clothing
        self.marker_red_ranges = [
            ([0, 120, 120], [10, 255, 255]),    # Primary red - higher saturation
            ([160, 120, 120], [179, 255, 255])  # Wrap-around red
        ]
        # Clothing typically has saturation 50-100, markers 120+
        
    def find_red_candidates(self, frame) -> List[np.ndarray]:
        """Find potential red marker candidates with strict color filtering"""
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        
        # Create mask for both red ranges
        mask1 = cv2.inRange(hsv, np.array(self.marker_red_ranges[0][0]), 
                           np.array(self.marker_red_ranges[0][1]))
        mask2 = cv2.inRange(hsv, np.array(self.marker_red_ranges[1][0]), 
                           np.array(self.marker_red_ranges[1][1]))
        mask = cv2.bitwise_or(mask1, mask2)
        
        # Enhanced morphological operations for small circular objects
        kernel = np.ones((3, 3), np.uint8)  # Smaller kernel for small markers
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
        
        # Find contours
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        return contours
    
    def calculate_color_score(self, frame, contour) -> float:
        """Calculate color quality score for the contour region"""
        # Create mask for the contour
        mask = np.zeros(frame.shape[:2], np.uint8)
        cv2.fillPoly(mask, [contour], 255)
        
        # Get HSV values in the region
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        region_pixels = hsv[mask > 0]
        
        if len(region_pixels) < 5:
            return 0.0
        
        # Check hue distribution - should be in red ranges
        hue_values = region_pixels[:, 0]
        red_pixels = np.sum((hue_values <= 10) | (hue_values >= 160))
        hue_score = red_pixels / len(hue_values)
        
        # Check saturation - should be high for markers
        saturation_mean = np.mean(region_pixels[:, 1])
        saturation_score = min(1.0, saturation_mean / 200.0)  # Normalize to 0-1
        
        # Check value (brightness) consistency
        value_std = np.std(region_pixels[:, 2])
        brightness_score = max(0.0, 1.0 - value_std / 50.0)
        
        # Combined color score
        return (hue_score * 0.4 + saturation_score * 0.4 + brightness_score * 0.2)

class MarkerGeometryValidator:
    def __init__(self):
        # Expected marker properties for 1-2cm diameter at various distances
        self.min_area = 50      # Very close camera (30cm distance)
        self.max_area = 800     # Far camera (100cm distance)
        self.min_circularity = 0.75  # Much stricter than before
        self.min_convexity = 0.9     # Markers are convex, clothing folds aren't
        self.aspect_ratio_range = (0.8, 1.2)  # Nearly circular
        self.min_compactness = 0.7   # Area vs bounding box ratio
        
    def is_valid_marker(self, contour) -> Tuple[bool, Dict[str, float]]:
        """Validate contour geometry and return metrics"""
        area = cv2.contourArea(contour)
        metrics = {'area': area}
        
        # Size constraint check
        if not (self.min_area <= area <= self.max_area):
            return False, metrics
        
        # Perimeter check for circularity calculation
        perimeter = cv2.arcLength(contour, True)
        if perimeter == 0:
            return False, metrics
            
        # Circularity check - 4*pi*area/perimeter^2
        circularity = 4 * math.pi * area / (perimeter * perimeter)
        metrics['circularity'] = circularity
        if circularity < self.min_circularity:
            return False, metrics
            
        # Convexity check - markers are convex, clothing folds aren't
        hull = cv2.convexHull(contour)
        hull_area = cv2.contourArea(hull)
        convexity = area / hull_area if hull_area > 0 else 0
        metrics['convexity'] = convexity
        if convexity < self.min_convexity:
            return False, metrics
            
        # Aspect ratio check
        (x, y, w, h) = cv2.boundingRect(contour)
        aspect_ratio = w / h if h > 0 else 0
        metrics['aspect_ratio'] = aspect_ratio
        if not (self.aspect_ratio_range[0] <= aspect_ratio <= self.aspect_ratio_range[1]):
            return False, metrics
            
        # Compactness check - area vs bounding box
        compactness = area / (w * h) if (w * h) > 0 else 0
        metrics['compactness'] = compactness
        if compactness < self.min_compactness:
            return False, metrics
        
        return True, metrics
    
    def calculate_geometric_score(self, metrics: Dict[str, float]) -> float:
        """Calculate normalized geometric quality score"""
        # Normalize each metric to 0-1 scale
        circularity_score = min(1.0, metrics['circularity'] / 1.0)
        convexity_score = metrics['convexity']
        
        # Size score - prefer medium sizes (optimal detection distance)
        area = metrics['area']
        optimal_area = 300  # Sweet spot for detection
        size_diff = abs(area - optimal_area) / optimal_area
        size_score = max(0.0, 1.0 - size_diff)
        
        # Aspect ratio score - closer to 1.0 is better
        aspect_score = 1.0 - abs(1.0 - metrics['aspect_ratio'])
        
        # Compactness score
        compactness_score = metrics['compactness']
        
        # Weighted combination
        return (circularity_score * 0.3 + convexity_score * 0.25 + 
                size_score * 0.2 + aspect_score * 0.15 + compactness_score * 0.1)

class ColorUniformityAnalyzer:
    def __init__(self):
        self.max_color_variance = 400    # Low variance for uniform markers
        self.max_brightness_range = 40   # Consistent brightness
        self.min_saturation_consistency = 0.85  # Consistent saturation
        
    def has_uniform_color(self, frame, contour) -> Tuple[bool, float]:
        """Check if contour region has uniform color like a marker"""
        # Create mask for the contour
        mask = np.zeros(frame.shape[:2], np.uint8)
        cv2.fillPoly(mask, [contour], 255)
        
        # Get pixels inside the contour
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        region_pixels = hsv[mask > 0]
        
        if len(region_pixels) < 10:
            return False, 0.0
            
        # Color variance check - markers are uniform, clothing isn't
        h_var = np.var(region_pixels[:, 0])
        s_var = np.var(region_pixels[:, 1])  
        v_var = np.var(region_pixels[:, 2])
        total_variance = h_var + s_var + v_var
        
        variance_score = max(0.0, 1.0 - total_variance / self.max_color_variance)
        
        # Brightness consistency check
        v_range = np.max(region_pixels[:, 2]) - np.min(region_pixels[:, 2])
        brightness_score = max(0.0, 1.0 - v_range / self.max_brightness_range)
        
        # Saturation consistency - markers have consistent high saturation
        s_mean = np.mean(region_pixels[:, 1])
        s_std = np.std(region_pixels[:, 1])
        saturation_consistency = 1.0 - (s_std / s_mean) if s_mean > 0 else 0.0
        
        # Combined uniformity score
        uniformity_score = (variance_score * 0.4 + brightness_score * 0.3 + 
                          saturation_consistency * 0.3)
        
        is_uniform = (total_variance <= self.max_color_variance and 
                     v_range <= self.max_brightness_range and
                     saturation_consistency >= self.min_saturation_consistency)
                     
        return is_uniform, uniformity_score

class TemporalConsistencyValidator:
    def __init__(self):
        self.position_history = deque(maxlen=10)
        self.property_history = deque(maxlen=5)
        self.max_position_jump = 30  # pixels - reasonable hand movement
        self.max_size_change = 0.3   # 30% size change allowed
        self.stability_threshold = 15  # pixels for stable position
        
    def validate_and_score(self, position: MarkerPosition) -> Tuple[MarkerPosition, float]:
        """Validate temporal consistency and return updated position with score"""
        temporal_score = 1.0
        
        # Position stability check
        if len(self.position_history) >= 2:
            last_pos = self.position_history[-1]
            distance = math.sqrt((position.x - last_pos.x)**2 + 
                               (position.y - last_pos.y)**2)
                               
            # Penalize sudden jumps
            if distance > self.max_position_jump:
                temporal_score *= 0.5
                
            # Reward stability
            if distance < self.stability_threshold:
                temporal_score *= 1.1
                
        # Property consistency check over recent history
        if len(self.property_history) >= 3:
            recent_areas = [p.area for p in list(self.property_history)[-3:]]
            area_variance = np.var(recent_areas)
            mean_area = np.mean(recent_areas)
            
            # Penalize inconsistent size
            if area_variance > (mean_area * self.max_size_change)**2:
                temporal_score *= 0.7
                
        # Store current position and properties
        self.position_history.append(position)
        self.property_history.append(position)
        
        # Calculate position stability for the position
        position_stable = self.is_position_stable()
        
        return position, min(1.0, temporal_score), position_stable
        
    def is_position_stable(self) -> bool:
        """Check if recent positions are stable"""
        if len(self.position_history) < 5:
            return False
            
        recent_positions = list(self.position_history)[-5:]
        avg_x = sum(p.x for p in recent_positions) / 5
        avg_y = sum(p.y for p in recent_positions) / 5
        
        # Check if all recent positions are within stability threshold
        for pos in recent_positions:
            distance = math.sqrt((pos.x - avg_x)**2 + (pos.y - avg_y)**2)
            if distance > self.stability_threshold:
                return False
                
        return True
        
    def reset(self):
        """Reset temporal validation state"""
        self.position_history.clear()
        self.property_history.clear()

class MarkerConfidenceScorer:
    def __init__(self):
        self.weights = {
            'geometric': 0.30,    # Shape, size, circularity
            'color': 0.25,        # Hue accuracy, saturation
            'uniformity': 0.25,   # Color consistency, no texture  
            'temporal': 0.20      # Position stability, consistency
        }
        self.min_component_threshold = 0.6  # All components must be reasonable
        
    def calculate_confidence(self, geometric_score: float, color_score: float, 
                           uniformity_score: float, temporal_score: float) -> Tuple[float, List[float]]:
        """Calculate overall confidence score with component validation"""
        
        components = [geometric_score, color_score, uniformity_score, temporal_score]
        
        # Ensure all components meet minimum threshold
        if any(score < self.min_component_threshold for score in components):
            return 0.0, components  # Fail if any component is too weak
            
        # Weighted final confidence
        final_confidence = (
            geometric_score * self.weights['geometric'] +
            color_score * self.weights['color'] +  
            uniformity_score * self.weights['uniformity'] +
            temporal_score * self.weights['temporal']
        )
        
        return min(1.0, final_confidence), components

class GestureRecognizer:
    def __init__(self):
        self.current_state = 'NONE'
        self.dwell_start = None
        self.dwell_threshold = 1.0  # seconds to trigger selection
        self.last_position = None
        self.movement_threshold = 20  # pixels
        self.state_history = deque(maxlen=5)
        
    def update(self, position: Optional[MarkerPosition]) -> GestureState:
        """Update gesture recognition state with enhanced validation"""
        current_time = time.time()
        
        if position is None or position.confidence < 0.75:  # Require high confidence
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
        
        # Enhanced detection components
        self.color_detector = AdaptiveColorDetector()
        self.geometry_validator = MarkerGeometryValidator()  
        self.uniformity_analyzer = ColorUniformityAnalyzer()
        self.temporal_validator = TemporalConsistencyValidator()
        self.confidence_scorer = MarkerConfidenceScorer()
        self.gesture_recognizer = GestureRecognizer()
        
        # Kalman filter for position smoothing
        self.kalman_filter = self.init_kalman_filter()
        self.kalman_initialized = False
        
        # Detection parameters
        self.min_confidence_threshold = 0.75  # Much higher threshold
        self.detection_state = "SEARCHING"  # SEARCHING, CONFIRMED, TRACKING
        
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
        
    def detect_marker(self, frame) -> Tuple[Optional[MarkerPosition], DetectionDebugInfo]:
        """Enhanced multi-stage marker detection pipeline"""
        debug_info = DetectionDebugInfo(0, 0, 0, [])
        
        # Stage 1: Adaptive color detection
        candidates = self.color_detector.find_red_candidates(frame)
        debug_info.candidates_found = len(candidates)
        
        if not candidates:
            return None, debug_info
            
        # Stage 2: Geometric validation  
        valid_contours = []
        geometric_metrics_list = []
        
        for contour in candidates:
            is_valid, metrics = self.geometry_validator.is_valid_marker(contour)
            if is_valid:
                valid_contours.append(contour)
                geometric_metrics_list.append(metrics)
                
        debug_info.passed_geometry = len(valid_contours)
        
        if not valid_contours:
            return None, debug_info
                
        # Stage 3: Color uniformity analysis
        uniform_candidates = []
        uniformity_scores = []
        
        for i, contour in enumerate(valid_contours):
            is_uniform, uniformity_score = self.uniformity_analyzer.has_uniform_color(frame, contour)
            if is_uniform:
                uniform_candidates.append((contour, geometric_metrics_list[i], uniformity_score))
                uniformity_scores.append(uniformity_score)
                
        debug_info.passed_uniformity = len(uniform_candidates)
        
        if not uniform_candidates:
            return None, debug_info
            
        # Stage 4: Select best candidate and calculate initial scores
        best_candidate = max(uniform_candidates, key=lambda x: x[2])  # Best uniformity score
        best_contour, best_metrics, best_uniformity = best_candidate
        
        # Extract position
        (x, y, w, h) = cv2.boundingRect(best_contour)
        center_x = x + w // 2
        center_y = y + h // 2
        
        # Calculate component scores
        geometric_score = self.geometry_validator.calculate_geometric_score(best_metrics)
        color_score = self.color_detector.calculate_color_score(frame, best_contour)
        uniformity_score = best_uniformity
        
        # Create initial position
        position = MarkerPosition(
            x=center_x, y=center_y, 
            confidence=0.0, timestamp=time.time(),
            area=best_metrics['area'],
            circularity=best_metrics['circularity'],
            convexity=best_metrics['convexity']
        )
        
        # Stage 5: Temporal validation and confidence scoring
        position, temporal_score, is_stable = self.temporal_validator.validate_and_score(position)
        
        # Final confidence calculation
        final_confidence, confidence_factors = self.confidence_scorer.calculate_confidence(
            geometric_score, color_score, uniformity_score, temporal_score
        )
        
        debug_info.final_confidence_factors = confidence_factors
        position.confidence = final_confidence
        
        # Update detection state
        if final_confidence >= self.min_confidence_threshold:
            self.detection_state = "CONFIRMED" if self.detection_state == "SEARCHING" else "TRACKING"
        else:
            self.detection_state = "SEARCHING"
            return None, debug_info
            
        return position, debug_info
        
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
        
        # Create smoothed position
        smoothed_position = MarkerPosition(
            x=int(prediction[0]),
            y=int(prediction[1]),
            confidence=position.confidence,
            timestamp=position.timestamp,
            area=position.area,
            circularity=position.circularity,
            convexity=position.convexity
        )
        
        return smoothed_position
        
    def run(self):
        """Main detection loop with enhanced output"""
        while True:
            ret, frame = self.cap.read()
            if not ret:
                break
                
            frame = cv2.flip(frame, 1)  # Mirror effect
            
            # Enhanced marker detection
            marker_pos, debug_info = self.detect_marker(frame)
            
            # Smooth position if detected
            if marker_pos:
                smoothed_pos = self.smooth_position(marker_pos)
                is_stable = self.temporal_validator.is_position_stable()
                
                # Update gesture recognition
                gesture_state = self.gesture_recognizer.update(smoothed_pos)
                
                # Enhanced output with quality metrics
                output_data = {
                    "camera_dimension": {"x": frame.shape[1], "y": frame.shape[0]},
                    "marker": {
                        "x": smoothed_pos.x,
                        "y": smoothed_pos.y,
                        "confidence": smoothed_pos.confidence,
                        "stable": is_stable,
                        "detection_state": self.detection_state
                    },
                    "gesture": {
                        "state": gesture_state.state,
                        "duration": gesture_state.duration,
                        "stability": gesture_state.stability_score
                    },
                    "quality_metrics": {
                        "geometric_score": debug_info.final_confidence_factors[0] if debug_info.final_confidence_factors else 0,
                        "color_score": debug_info.final_confidence_factors[1] if debug_info.final_confidence_factors else 0,
                        "uniformity_score": debug_info.final_confidence_factors[2] if debug_info.final_confidence_factors else 0,
                        "temporal_score": debug_info.final_confidence_factors[3] if debug_info.final_confidence_factors else 0,
                        "area": smoothed_pos.area,
                        "circularity": smoothed_pos.circularity,
                        "convexity": smoothed_pos.convexity
                    },
                    "debug_info": {
                        "candidates_found": debug_info.candidates_found,
                        "passed_geometry": debug_info.passed_geometry,
                        "passed_uniformity": debug_info.passed_uniformity
                    },
                    "timestamp": time.time()
                }
                
                print(json.dumps(output_data))
                sys.stdout.flush()
                
            else:
                # Reset state when no detection
                self.detection_state = "SEARCHING"
                self.gesture_recognizer.update(None)
                
                # No detection output
                no_detection = {
                    "camera_dimension": {"x": frame.shape[1], "y": frame.shape[0]},
                    "marker": None,
                    "gesture": {"state": "NONE", "duration": 0, "stability": 0},
                    "quality_metrics": None,
                    "debug_info": {
                        "candidates_found": debug_info.candidates_found,
                        "passed_geometry": debug_info.passed_geometry,
                        "passed_uniformity": debug_info.passed_uniformity
                    },
                    "timestamp": time.time()
                }
                
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
