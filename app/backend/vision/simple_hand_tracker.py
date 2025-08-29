import cv2
import numpy as np
import mediapipe as mp
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

class SimpleHandTracker:
    """Simple binary hand tracker using MediaPipe and convex hull area detection"""
    
    def __init__(self):
        # Initialize MediaPipe Hands
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.7,
            model_complexity=0
        )
        
        # Drawing utilities for debugging
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_drawing_styles = mp.solutions.drawing_styles
        
        # State tracking for hysteresis and stability
        self.current_state = True  # Start with open hand
        self.state_history = []
        self.stability_frames = 4  # Require only 4 consecutive frames for faster response
        
        # Hysteresis thresholds for area ratio
        # Lower ratio = more closed (fingers inside hull)
        # Higher ratio = more open (fingers spread out)
        self.open_to_closed_threshold = 0.6   # Below this = transition to closed
        self.closed_to_open_threshold = 0.75  # Above this = transition to open
        
        # Position smoothing
        self.last_position = None
        self.position_smoothing = 0.7  # Smooth factor for cursor movement
        
    def detect_hand_state(self, frame: np.ndarray) -> Optional[SimpleHandGesture]:
        """Detect hand and determine binary open/closed state"""
        
        # Mirror frame for natural interaction
        frame = cv2.flip(frame, 1)
        
        # Convert BGR to RGB for MediaPipe
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Set writable flag to False to improve performance
        rgb_frame.flags.writeable = False
        
        # Process frame
        results = self.hands.process(rgb_frame)
        
        if not results.multi_hand_landmarks:
            # No hand detected - return None
            logger.debug("HAND_DETECTION: No hand landmarks detected")
            return None
            
        # Get the first (and only) hand
        hand_landmarks = results.multi_hand_landmarks[0]
        
        # Convert landmarks to pixel coordinates
        height, width = frame.shape[:2]
        landmarks = []
        for landmark in hand_landmarks.landmark:
            x = int(landmark.x * width)
            y = int(landmark.y * height)
            landmarks.append((x, y))
        
        # Calculate hand center (average of all landmarks)
        center_x = int(np.mean([p[0] for p in landmarks]))
        center_y = int(np.mean([p[1] for p in landmarks]))
        hand_center = (center_x, center_y)
        
        # Smooth position
        if self.last_position:
            smooth_x = int(self.last_position[0] * self.position_smoothing + 
                          hand_center[0] * (1 - self.position_smoothing))
            smooth_y = int(self.last_position[1] * self.position_smoothing + 
                          hand_center[1] * (1 - self.position_smoothing))
            hand_center = (smooth_x, smooth_y)
        
        self.last_position = hand_center
        
        # Use multiple detection methods for reliability
        finger_detection = self._detect_finger_extensions(landmarks)
        extended_fingers = finger_detection['extended_count']
        finger_distances = finger_detection['distances']
        
        # Primary method: finger extension count
        # 0-1 extended fingers = closed fist (GRABBED)
        # 2+ extended fingers = open hand (OPEN)
        finger_based_open = extended_fingers >= 2
        
        # Secondary method (fallback): convex hull ratio
        area_ratio = self._calculate_convex_hull_ratio(landmarks, frame.shape)
        area_based_open = area_ratio > 0.65  # Simple threshold without hysteresis for fallback
        
        # Combine both methods - finger extension takes priority
        if extended_fingers >= 0:  # Valid finger detection
            detection_confidence = 0.9
            primary_open = finger_based_open
        else:  # Fallback to area method
            detection_confidence = 0.6
            primary_open = area_based_open
        
        # Determine binary state with hysteresis using primary method
        is_open = self._update_hand_state_v2(primary_open, extended_fingers)
        
        # Calculate confidence based on how clear the state is
        if is_open:
            # For open hands, confidence is higher when area ratio is well above threshold
            confidence = min(0.9, 0.5 + (area_ratio - 0.8) * 2.0) if area_ratio > 0.8 else 0.5
        else:
            # For closed hands, confidence is higher when area ratio is well below threshold
            confidence = min(0.9, 0.5 + (0.8 - area_ratio) * 2.0) if area_ratio < 0.8 else 0.5
        
        # Normalize position to 0-1 range
        normalized_position = (hand_center[0] / width, hand_center[1] / height)
        
        # Create gesture object
        gesture = SimpleHandGesture(
            is_open=is_open,
            confidence=max(0.1, detection_confidence),
            position=normalized_position,
            raw_area_ratio=area_ratio,
            extended_fingers=extended_fingers,
            finger_distances=finger_distances
        )
        
        # LOG: Report detected gesture with state
        logger.debug(f"HAND_DETECTION: Gesture detected - "
                   f"State: {'OPEN' if is_open else 'CLOSED'}, "
                   f"Extended fingers: {extended_fingers}, "
                   f"Position: ({normalized_position[0]:.2f}, {normalized_position[1]:.2f}), "
                   f"Confidence: {gesture.confidence:.2f}")
        
        return gesture
    
    def _calculate_convex_hull_ratio(self, landmarks: list, frame_shape: tuple = (480, 640)) -> float:
        """Calculate ratio of actual hand area to convex hull area - simplified approach"""
        
        if len(landmarks) < 21:  # Need all MediaPipe hand landmarks
            return 1.0
            
        # Convert landmarks to numpy array for cv2
        points = np.array(landmarks, dtype=np.int32)
        
        # Calculate convex hull
        hull = cv2.convexHull(points)
        hull_area = cv2.contourArea(hull)
        
        if hull_area == 0:
            return 1.0
        
        # Simplified approach: use the actual landmarks as the hand contour
        # This gives a more direct measure of hand openness vs the convex hull
        hand_area = cv2.contourArea(points)
        
        # If hand contour area is invalid, use a distance-based approach
        if hand_area <= 0:
            # Calculate average distance from landmarks to hull
            # Closed hand = fingers close to hull, Open hand = fingers far from hull
            total_distance = 0
            for point in landmarks:
                dist = cv2.pointPolygonTest(hull, point, True)
                total_distance += abs(dist)
            
            # Normalize by number of points and hull perimeter
            hull_perimeter = cv2.arcLength(hull, True)
            if hull_perimeter > 0:
                normalized_distance = total_distance / (len(landmarks) * hull_perimeter * 0.1)
                # Higher normalized distance = more open hand
                return min(1.0, max(0.3, normalized_distance))
            else:
                return 0.8  # Default to somewhat open
        
        # Calculate ratio - when hand is open, area approaches hull area
        ratio = hand_area / hull_area if hull_area > 0 else 1.0
        
        # Ensure ratio is in reasonable range and invert if needed
        # For MediaPipe landmarks, closed fist typically has lower ratio
        ratio = max(0.3, min(1.0, ratio))
        
        return ratio
    
    def _create_hand_outline(self, landmarks: list) -> Optional[np.ndarray]:
        """Create a simple hand outline from key landmarks"""
        
        if len(landmarks) < 21:
            return None
        
        try:
            # Key landmarks for hand outline (MediaPipe hand landmark indices)
            # Wrist and finger bases to create outer boundary
            outline_indices = [
                0,   # Wrist
                1, 2, 5, 9, 13, 17,  # Palm base points
                4,   # Thumb tip
                8,   # Index tip
                12,  # Middle tip
                16,  # Ring tip
                20,  # Pinky tip
                17, 13, 9, 5, 1  # Back to palm base
            ]
            
            outline_points = []
            for idx in outline_indices:
                if idx < len(landmarks):
                    outline_points.append(landmarks[idx])
            
            return np.array(outline_points, dtype=np.int32)
        except:
            return None
    
    def _detect_finger_extensions(self, landmarks: list) -> dict:
        """Detect which fingers are extended using MediaPipe hand landmarks
        
        MediaPipe Hand Landmarks (21 points):
        Thumb: 1=CMC, 2=MCP, 3=IP, 4=TIP
        Index: 5=MCP, 6=PIP, 7=DIP, 8=TIP  
        Middle: 9=MCP, 10=PIP, 11=DIP, 12=TIP
        Ring: 13=MCP, 14=PIP, 15=DIP, 16=TIP
        Pinky: 17=MCP, 18=PIP, 19=DIP, 20=TIP
        Wrist: 0=WRIST
        """
        
        if len(landmarks) < 21:
            return {'extended_count': -1, 'distances': {}, 'extended_fingers': []}
            
        try:
            # Get key landmark positions
            wrist = np.array(landmarks[0])
            palm_center = np.array(landmarks[9])  # Middle finger MCP as palm reference
            
            extended_fingers = []
            distances = {}
            
            # Check each finger for extension
            finger_checks = {
                'thumb': self._is_thumb_extended(landmarks, wrist),
                'index': self._is_finger_extended(landmarks, [5, 6, 7, 8], palm_center, 'index'),
                'middle': self._is_finger_extended(landmarks, [9, 10, 11, 12], palm_center, 'middle'),
                'ring': self._is_finger_extended(landmarks, [13, 14, 15, 16], palm_center, 'ring'),
                'pinky': self._is_finger_extended(landmarks, [17, 18, 19, 20], palm_center, 'pinky')
            }
            
            # Count extended fingers and collect debug info
            extended_count = 0
            for finger_name, (is_extended, distance) in finger_checks.items():
                if is_extended:
                    extended_fingers.append(finger_name)
                    extended_count += 1
                distances[finger_name] = distance
                
            logger.debug(f"Finger extension: {extended_fingers} (count: {extended_count})")
            
            return {
                'extended_count': extended_count,
                'distances': distances,
                'extended_fingers': extended_fingers
            }
            
        except Exception as e:
            logger.debug(f"Finger extension detection failed: {e}")
            return {'extended_count': -1, 'distances': {}, 'extended_fingers': []}
    
    def _is_thumb_extended(self, landmarks: list, wrist: np.ndarray) -> tuple:
        """Check if thumb is extended - special case due to different orientation"""
        try:
            thumb_tip = np.array(landmarks[4])
            thumb_ip = np.array(landmarks[3])
            thumb_mcp = np.array(landmarks[2])
            thumb_cmc = np.array(landmarks[1])
            palm_center = np.array(landmarks[9])  # Use same reference as other fingers
            
            # Method 1: Thumb tip should be farther from palm than MCP
            tip_to_palm = np.linalg.norm(thumb_tip - palm_center)
            mcp_to_palm = np.linalg.norm(thumb_mcp - palm_center)
            
            # Method 2: Check progression from base to tip
            cmc_to_palm = np.linalg.norm(thumb_cmc - palm_center)
            progression_check = tip_to_palm > max(mcp_to_palm * 1.1, cmc_to_palm * 1.2)
            
            # Method 3: Check if thumb is not curled back toward palm
            # Vector from MCP to IP
            v1 = thumb_ip - thumb_mcp
            # Vector from IP to TIP
            v2 = thumb_tip - thumb_ip
            
            angle_check = True
            if np.linalg.norm(v1) > 0 and np.linalg.norm(v2) > 0:
                cos_angle = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
                angle_check = cos_angle > -0.1  # Thumb should not be curled back too much
            
            is_extended = progression_check and angle_check
            
            logger.debug(f"Thumb: tip_dist={tip_to_palm:.1f}, mcp_dist={mcp_to_palm:.1f}, progression={progression_check}, angle={angle_check} -> {is_extended}")
            
            return (is_extended, tip_to_palm)
        except Exception as e:
            logger.debug(f"Thumb extension detection error: {e}")
            return (False, 0.0)
    
    def _is_finger_extended(self, landmarks: list, indices: list, palm_center: np.ndarray, finger_name: str) -> tuple:
        """Check if a finger (index, middle, ring, pinky) is extended"""
        try:
            mcp_idx, pip_idx, dip_idx, tip_idx = indices
            
            tip = np.array(landmarks[tip_idx])
            pip = np.array(landmarks[pip_idx])
            dip = np.array(landmarks[dip_idx])
            mcp = np.array(landmarks[mcp_idx])
            
            # Method 1: Tip should be farther from palm center than PIP joint
            tip_to_palm = np.linalg.norm(tip - palm_center)
            pip_to_palm = np.linalg.norm(pip - palm_center)
            mcp_to_palm = np.linalg.norm(mcp - palm_center)
            
            # Method 2: Check if finger is generally pointing away from palm
            # Extended finger should have tip farther from palm than both PIP and MCP
            distance_check = tip_to_palm > max(pip_to_palm * 1.2, mcp_to_palm * 1.1)
            
            # Method 3: Check joint progression - in extended finger, distance from palm increases
            # MCP -> PIP -> TIP should be increasing distances (with some tolerance)
            progression_check = (pip_to_palm > mcp_to_palm * 0.9) and (tip_to_palm > pip_to_palm * 1.05)
            
            # Method 4: Check finger straightness using joint angles  
            # Vector from MCP to PIP
            v1 = pip - mcp
            # Vector from PIP to DIP
            v2 = dip - pip
            
            angle_check = True
            if np.linalg.norm(v1) > 0 and np.linalg.norm(v2) > 0:
                # Angle between MCP-PIP and PIP-DIP segments
                cos_angle1 = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
                angle_check = cos_angle1 > -0.2  # Allow some curl, but not too much
            
            # Combine all checks - need at least distance check AND progression check
            is_extended = distance_check and progression_check and angle_check
            
            logger.debug(f"{finger_name}: tip={tip_to_palm:.1f}, pip={pip_to_palm:.1f}, mcp={mcp_to_palm:.1f}, "
                        f"dist={distance_check}, prog={progression_check}, angle={angle_check} -> {is_extended}")
            
            return (is_extended, tip_to_palm)
        except Exception as e:
            logger.debug(f"{finger_name} extension detection error: {e}")
            return (False, 0.0)
    
    def _update_hand_state_v2(self, is_open_detected: bool, extended_fingers: int) -> bool:
        """Update hand state with improved logic and stability checking"""
        
        # Add detected state to history
        self.state_history.append(is_open_detected)
        
        # Keep only recent history
        if len(self.state_history) > self.stability_frames * 2:
            self.state_history = self.state_history[-self.stability_frames:]
        
        # For stability, require fewer consecutive frames for reliable detections
        stability_threshold = max(3, self.stability_frames // 2) if extended_fingers >= 0 else self.stability_frames
        
        # Check for stable state change
        if len(self.state_history) >= stability_threshold:
            recent_states = self.state_history[-stability_threshold:]
            
            # Majority vote for state change (more forgiving than requiring all frames)
            open_votes = sum(recent_states)
            closed_votes = stability_threshold - open_votes
            
            if open_votes > closed_votes:  # Majority says open
                desired_state = True
            else:  # Majority says closed
                desired_state = False
            
            # Apply hysteresis - require stronger evidence to change state
            confidence_ratio = max(open_votes, closed_votes) / stability_threshold
            
            if desired_state != self.current_state and confidence_ratio >= 0.6:  # 60% instead of 70% for faster response
                logger.info(f"HAND_TRACKER: Hand state transition: {'OPEN' if self.current_state else 'CLOSED'} -> "
                             f"{'OPEN' if desired_state else 'CLOSED'} "
                             f"(fingers: {extended_fingers}, confidence: {confidence_ratio:.2f})")
                self.current_state = desired_state
                # Clear history after state change
                self.state_history = []
        
        return self.current_state
    
    def _update_hand_state(self, area_ratio: float) -> bool:
        """Legacy method - kept for compatibility"""
        # This method is now deprecated in favor of _update_hand_state_v2
        return self._update_hand_state_v2(area_ratio > 0.65, -1)
    
    def create_debug_frame(self, frame: np.ndarray, gesture: Optional[SimpleHandGesture]) -> np.ndarray:
        """Create debug visualization frame with cursor"""
        
        # Frame is already mirrored from detect_hand_state
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
            cv2.putText(debug_frame, f'Confidence: {gesture.confidence:.2f}', 
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
            cv2.putText(debug_frame, f'Extended Fingers: {gesture.extended_fingers}', 
                       (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
            cv2.putText(debug_frame, f'Area Ratio: {gesture.raw_area_ratio:.3f}', 
                       (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
            
            # Show finger extension details
            if hasattr(gesture, 'finger_distances') and gesture.finger_distances:
                y_offset = 90
                for finger, distance in gesture.finger_distances.items():
                    cv2.putText(debug_frame, f'{finger}: {distance:.1f}', 
                               (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
                    y_offset += 15
            
            # Show detection method info
            cv2.putText(debug_frame, f'Detection: 0-1=CLOSED, 2+=OPEN', 
                       (10, debug_frame.shape[0] - 60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 255, 100), 1)
            cv2.putText(debug_frame, f'Stability: {len(self.state_history)} frames', 
                       (10, debug_frame.shape[0] - 40), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 255, 100), 1)
            cv2.putText(debug_frame, 'Simple Binary Hand Tracker', 
                       (10, debug_frame.shape[0] - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
        else:
            # No hand detected
            cv2.putText(debug_frame, 'No hand detected', 
                       (debug_frame.shape[1]//2 - 100, debug_frame.shape[0]//2), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        
        return debug_frame