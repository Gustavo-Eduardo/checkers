import cv2
import numpy as np
import json
import math
from dataclasses import dataclass, asdict
from typing import List, Tuple, Optional

@dataclass
class CalibrationPoint:
    distance_cm: float
    marker_pixel_area: float
    marker_pixel_radius: float
    confidence: float
    timestamp: float

class MarkerSizeCalibrator:
    """
    Calibration system for marker size at different distances.
    Allows automatic adjustment of detection parameters based on camera setup.
    """
    
    def __init__(self):
        self.calibration_points: List[CalibrationPoint] = []
        self.is_calibrating = False
        self.target_marker_size_cm = 1.5  # 1-2cm marker tip
        
        # Default size ranges (will be updated by calibration)
        self.min_area_default = 50
        self.max_area_default = 800
        
        # Calibrated parameters
        self.area_distance_relationship = None  # Function: distance -> expected_area
        self.adaptive_thresholds = False
        
    def start_calibration(self):
        """Start interactive calibration process"""
        self.calibration_points.clear()
        self.is_calibrating = True
        print("=== Marker Size Calibration Started ===")
        print("Instructions:")
        print("1. Hold your red marker at different distances from camera")
        print("2. Call add_calibration_measurement() at each distance")
        print("3. Recommended distances: 30cm, 50cm, 70cm, 100cm")
        print("4. Call finalize_calibration() when done")
        
    def add_calibration_measurement(self, frame, distance_cm: float, 
                                   contour: np.ndarray, confidence: float) -> bool:
        """Add a calibration measurement for a specific distance"""
        if not self.is_calibrating:
            return False
            
        area = cv2.contourArea(contour)
        
        # Calculate equivalent radius
        radius = math.sqrt(area / math.pi)
        
        point = CalibrationPoint(
            distance_cm=distance_cm,
            marker_pixel_area=area,
            marker_pixel_radius=radius,
            confidence=confidence,
            timestamp=cv2.getTickCount() / cv2.getTickFrequency()
        )
        
        self.calibration_points.append(point)
        
        print(f"Calibration point added: {distance_cm}cm -> {area:.1f}px area ({radius:.1f}px radius)")
        return True
        
    def finalize_calibration(self) -> bool:
        """Process calibration data and create size relationship model"""
        if len(self.calibration_points) < 3:
            print("Error: Need at least 3 calibration points")
            return False
            
        # Sort by distance
        self.calibration_points.sort(key=lambda p: p.distance_cm)
        
        # Create distance->area relationship using polynomial fit
        distances = np.array([p.distance_cm for p in self.calibration_points])
        areas = np.array([p.marker_pixel_area for p in self.calibration_points])
        
        # Fit inverse relationship: area = a / distance^2 + b
        # This models how marker appears smaller with distance
        try:
            # Transform to linear relationship
            inv_dist_sq = 1.0 / (distances ** 2)
            coeffs = np.polyfit(inv_dist_sq, areas, 1)  # Linear fit
            
            self.area_distance_relationship = {
                'type': 'inverse_square',
                'a': coeffs[0],
                'b': coeffs[1]
            }
            
            # Calculate updated size ranges based on expected usage distances
            min_distance = 25  # cm - very close
            max_distance = 120  # cm - far away
            
            self.min_area_calibrated = max(30, self.predict_area_at_distance(max_distance))
            self.max_area_calibrated = min(1000, self.predict_area_at_distance(min_distance))
            
            self.adaptive_thresholds = True
            self.is_calibrating = False
            
            print("=== Calibration Complete ===")
            print(f"Model: area = {coeffs[0]:.1f} / distance² + {coeffs[1]:.1f}")
            print(f"Adaptive area range: {self.min_area_calibrated:.0f} - {self.max_area_calibrated:.0f} pixels")
            
            return True
            
        except Exception as e:
            print(f"Calibration failed: {e}")
            return False
    
    def predict_area_at_distance(self, distance_cm: float) -> float:
        """Predict expected marker area at given distance"""
        if not self.area_distance_relationship:
            # Use default estimate: assume area inversely proportional to distance²
            reference_area = 200  # pixels at 50cm
            reference_distance = 50  # cm
            return reference_area * (reference_distance / distance_cm) ** 2
            
        rel = self.area_distance_relationship
        if rel['type'] == 'inverse_square':
            return rel['a'] / (distance_cm ** 2) + rel['b']
        
        return 200  # fallback
    
    def get_adaptive_size_range(self, estimated_distance: Optional[float] = None) -> Tuple[float, float]:
        """Get adaptive size range for detection"""
        if not self.adaptive_thresholds:
            return self.min_area_default, self.max_area_default
            
        if estimated_distance:
            # Predict for specific distance with tolerance
            predicted_area = self.predict_area_at_distance(estimated_distance)
            tolerance = 0.4  # ±40% tolerance
            min_area = predicted_area * (1 - tolerance)
            max_area = predicted_area * (1 + tolerance)
            return max(20, min_area), min(1200, max_area)
        else:
            # Use calibrated global range
            return self.min_area_calibrated, self.max_area_calibrated
    
    def estimate_distance_from_area(self, area: float) -> float:
        """Estimate marker distance based on detected area"""
        if not self.area_distance_relationship:
            # Default estimate
            reference_area = 200  # pixels at 50cm
            reference_distance = 50  # cm
            return reference_distance * math.sqrt(reference_area / area)
            
        rel = self.area_distance_relationship
        if rel['type'] == 'inverse_square':
            # Solve: area = a / distance² + b for distance
            # distance = sqrt(a / (area - b))
            if area <= rel['b']:
                return 200  # Very far - fallback
            return math.sqrt(rel['a'] / (area - rel['b']))
        
        return 50  # fallback
    
    def save_calibration(self, filename: str = 'marker_calibration.json') -> bool:
        """Save calibration data to file"""
        try:
            data = {
                'calibration_points': [asdict(p) for p in self.calibration_points],
                'area_distance_relationship': self.area_distance_relationship,
                'adaptive_thresholds': self.adaptive_thresholds,
                'target_marker_size_cm': self.target_marker_size_cm,
                'min_area_calibrated': getattr(self, 'min_area_calibrated', self.min_area_default),
                'max_area_calibrated': getattr(self, 'max_area_calibrated', self.max_area_default)
            }
            
            with open(filename, 'w') as f:
                json.dump(data, f, indent=2)
            
            print(f"Calibration saved to {filename}")
            return True
            
        except Exception as e:
            print(f"Failed to save calibration: {e}")
            return False
    
    def load_calibration(self, filename: str = 'marker_calibration.json') -> bool:
        """Load calibration data from file"""
        try:
            with open(filename, 'r') as f:
                data = json.load(f)
            
            # Restore calibration points
            self.calibration_points = [
                CalibrationPoint(**point) for point in data['calibration_points']
            ]
            
            # Restore parameters
            self.area_distance_relationship = data.get('area_distance_relationship')
            self.adaptive_thresholds = data.get('adaptive_thresholds', False)
            self.target_marker_size_cm = data.get('target_marker_size_cm', 1.5)
            self.min_area_calibrated = data.get('min_area_calibrated', self.min_area_default)
            self.max_area_calibrated = data.get('max_area_calibrated', self.max_area_default)
            
            print(f"Calibration loaded from {filename}")
            print(f"Loaded {len(self.calibration_points)} calibration points")
            if self.adaptive_thresholds:
                print(f"Adaptive area range: {self.min_area_calibrated:.0f} - {self.max_area_calibrated:.0f} pixels")
            
            return True
            
        except Exception as e:
            print(f"Failed to load calibration: {e}")
            return False
    
    def get_calibration_status(self) -> dict:
        """Get current calibration status"""
        return {
            'is_calibrating': self.is_calibrating,
            'points_collected': len(self.calibration_points),
            'adaptive_thresholds_enabled': self.adaptive_thresholds,
            'calibrated_size_range': (
                getattr(self, 'min_area_calibrated', self.min_area_default),
                getattr(self, 'max_area_calibrated', self.max_area_default)
            ) if self.adaptive_thresholds else None
        }

# Interactive calibration utility
def run_interactive_calibration():
    """Run interactive calibration session"""
    calibrator = MarkerSizeCalibrator()
    cap = cv2.VideoCapture(0)
    
    print("=== Interactive Marker Calibration ===")
    print("Controls:")
    print("'s' - Start calibration")
    print("'c' - Capture measurement at current distance")
    print("'f' - Finalize calibration")
    print("'q' - Quit")
    print("\nHold red marker steady and press 'c' at different distances")
    
    # Simple detection for calibration
    calibrator.start_calibration()
    current_distance = 50  # Default distance
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
            
        frame = cv2.flip(frame, 1)
        
        # Simple red detection for calibration
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask1 = cv2.inRange(hsv, np.array([0, 120, 120]), np.array([10, 255, 255]))
        mask2 = cv2.inRange(hsv, np.array([160, 120, 120]), np.array([179, 255, 255]))
        mask = cv2.bitwise_or(mask1, mask2)
        
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Find best contour
        best_contour = None
        if contours:
            best_contour = max(contours, key=cv2.contourArea)
            area = cv2.contourArea(best_contour)
            
            if area > 30:  # Minimum size
                # Draw contour and info
                cv2.drawContours(frame, [best_contour], -1, (0, 255, 0), 2)
                
                (x, y, w, h) = cv2.boundingRect(best_contour)
                center = (x + w//2, y + h//2)
                
                cv2.putText(frame, f"Area: {area:.0f}px", (10, 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                cv2.putText(frame, f"Distance: {current_distance}cm", (10, 60), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                cv2.putText(frame, "Press 'c' to capture", (10, 90), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
        
        # Instructions
        cv2.putText(frame, "Calibration Mode - Hold marker steady", (10, frame.shape[0] - 60), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        cv2.putText(frame, f"Points: {len(calibrator.calibration_points)}/4", (10, frame.shape[0] - 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        cv2.imshow('Marker Calibration', frame)
        
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('c') and best_contour is not None:
            # Capture calibration point
            distance_str = input(f"Enter actual distance in cm (current: {current_distance}): ")
            if distance_str.strip():
                try:
                    current_distance = float(distance_str)
                except ValueError:
                    pass
            
            area = cv2.contourArea(best_contour)
            if calibrator.add_calibration_measurement(frame, current_distance, best_contour, 0.9):
                print(f"Captured point {len(calibrator.calibration_points)}")
                
        elif key == ord('f'):
            # Finalize calibration
            if calibrator.finalize_calibration():
                calibrator.save_calibration()
                print("Calibration complete and saved!")
                break
    
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    run_interactive_calibration()