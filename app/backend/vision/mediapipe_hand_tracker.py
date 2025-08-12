import cv2
import numpy as np
import mediapipe as mp
from dataclasses import dataclass
from typing import List, Optional, Dict, Tuple
import math

@dataclass
class HandGesture:
    gesture_type: str  # 'point', 'grab', 'release', 'hover'
    confidence: float
    position: Tuple[float, float]  # Normalized coordinates
    hand_landmarks: Optional[np.ndarray]
    finger_count: int = 0  # Number of fingers up

class MediaPipeHandTracker:
    """High-accuracy hand tracking using Google's MediaPipe"""
    
    def __init__(self):
        # Initialize MediaPipe Hands with optimized settings for speed and reduced warnings
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,        # Process video stream
            max_num_hands=1,                # Only track one hand for better performance
            min_detection_confidence=0.7,   # Slightly higher for stability
            min_tracking_confidence=0.7,    # Better tracking consistency
            model_complexity=0              # Faster, lighter model (reduces inference warnings)
        )
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_drawing_styles = mp.solutions.drawing_styles
        
        # Hand landmark indices for finger detection
        self.FINGER_TIPS = [4, 8, 12, 16, 20]  # Thumb, Index, Middle, Ring, Pinky tips
        self.FINGER_PIPS = [3, 6, 10, 14, 18]  # Finger PIP joints (for direction checking)
        self.FINGER_MIPS = [2, 5, 9, 13, 17]   # Finger MCP joints
        
        # Hand center and palm landmarks
        self.PALM_LANDMARKS = [0, 1, 2, 5, 9, 13, 17]  # Wrist and palm base points
        
        self.last_position = None
        self.last_gesture = None
        
    def detect_hands(self, frame: np.ndarray) -> Optional[Dict]:
        """Detect hands using MediaPipe"""
        # Mirror the frame horizontally for more natural interaction
        frame = cv2.flip(frame, 1)
        
        # Convert BGR to RGB (MediaPipe expects RGB)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Process frame
        results = self.hands.process(rgb_frame)
        
        if results.multi_hand_landmarks and results.multi_handedness:
            # Get the most confident hand (primary hand)
            best_hand_idx = 0
            best_confidence = 0
            
            for idx, handedness in enumerate(results.multi_handedness):
                confidence = handedness.classification[0].score
                if confidence > best_confidence:
                    best_confidence = confidence
                    best_hand_idx = idx
                    
            if best_confidence < 0.7:  # Minimum confidence threshold
                return None
                
            hand_landmarks = results.multi_hand_landmarks[best_hand_idx]
            handedness = results.multi_handedness[best_hand_idx]
            
            # Convert normalized coordinates to pixel coordinates
            height, width = frame.shape[:2]
            landmarks_px = []
            landmarks_norm = []
            
            for landmark in hand_landmarks.landmark:
                x_px = int(landmark.x * width)
                y_px = int(landmark.y * height)
                landmarks_px.append((x_px, y_px))
                landmarks_norm.append((landmark.x, landmark.y))
            
            # Calculate hand properties
            hand_info = self._analyze_hand(landmarks_px, landmarks_norm, handedness, frame.shape)
            
            if hand_info:
                return {
                    'center': hand_info['center'],
                    'palm_center': hand_info['palm_center'],
                    'index_tip': hand_info['index_tip'],
                    'topmost': hand_info['topmost'],
                    'bbox': hand_info['bbox'],
                    'area': hand_info['area'],
                    'landmarks': landmarks_px,
                    'landmarks_norm': landmarks_norm,
                    'finger_states': hand_info['finger_states'],
                    'fingers_up': hand_info['fingers_up'],
                    'confidence': float(best_confidence),
                    'handedness': handedness.classification[0].label,
                    'debug': {
                        'finger_count': hand_info['fingers_up'],
                        'detection_method': 'mediapipe',
                        'handedness': handedness.classification[0].label,
                        'confidence': float(best_confidence),
                        'all_areas': [hand_info['area']]
                    }
                }
        
        return None
        
    def _analyze_hand(self, landmarks_px: List[Tuple[int, int]], 
                     landmarks_norm: List[Tuple[float, float]], 
                     handedness, frame_shape: Tuple[int, int]) -> Optional[Dict]:
        """Analyze hand landmarks to extract useful information"""
        
        if len(landmarks_px) != 21:  # MediaPipe provides 21 landmarks per hand
            return None
            
        height, width = frame_shape[:2]
        
        # Calculate palm center (average of palm landmarks)
        palm_points = [landmarks_px[i] for i in self.PALM_LANDMARKS]
        palm_center = (
            int(np.mean([p[0] for p in palm_points])),
            int(np.mean([p[1] for p in palm_points]))
        )
        
        # Calculate hand center (centroid of all landmarks)
        center = (
            int(np.mean([p[0] for p in landmarks_px])),
            int(np.mean([p[1] for p in landmarks_px]))
        )
        
        # Get bounding box
        x_coords = [p[0] for p in landmarks_px]
        y_coords = [p[1] for p in landmarks_px]
        bbox = (min(x_coords), min(y_coords), 
                max(x_coords) - min(x_coords), 
                max(y_coords) - min(y_coords))
        
        # Calculate hand area (approximate)
        area = bbox[2] * bbox[3]
        
        # Detect which fingers are extended
        finger_states = self._detect_finger_states(landmarks_px, handedness)
        fingers_up = sum(finger_states)
        
        # Get index finger tip for pointing
        index_tip = landmarks_px[8]  # Index finger tip landmark
        
        # Find topmost point (highest y-coordinate, lowest value)
        topmost_idx = min(range(len(landmarks_px)), key=lambda i: landmarks_px[i][1])
        topmost = landmarks_px[topmost_idx]
        
        return {
            'center': center,
            'palm_center': palm_center,
            'index_tip': index_tip,
            'topmost': topmost,
            'bbox': bbox,
            'area': area,
            'finger_states': finger_states,
            'fingers_up': fingers_up
        }
        
    def _detect_finger_states(self, landmarks: List[Tuple[int, int]], handedness) -> List[bool]:
        """Detect which fingers are extended (up)"""
        fingers = []
        is_right_hand = handedness.classification[0].label == "Right"
        
        # Thumb (special case - check x-coordinate relative to hand orientation)
        if is_right_hand:
            # Right hand: thumb up if tip is to the right of MCP
            fingers.append(landmarks[self.FINGER_TIPS[0]][0] > landmarks[self.FINGER_MIPS[0]][0])
        else:
            # Left hand: thumb up if tip is to the left of MCP
            fingers.append(landmarks[self.FINGER_TIPS[0]][0] < landmarks[self.FINGER_MIPS[0]][0])
        
        # Other fingers: check if tip is above PIP joint
        for i in range(1, 5):
            tip_y = landmarks[self.FINGER_TIPS[i]][1]
            pip_y = landmarks[self.FINGER_PIPS[i]][1]
            fingers.append(tip_y < pip_y)  # Lower y value means higher on screen
            
        return fingers
        
    def create_debug_frame(self, frame: np.ndarray, hand_data: Optional[Dict]) -> np.ndarray:
        """Create optimized debug visualization frame"""
        # Frame is already mirrored from detect_hands, so we use it as-is
        debug_frame = frame.copy()
        
        if hand_data and 'landmarks' in hand_data:
            landmarks = hand_data['landmarks']
            
            # Simple, fast landmark drawing instead of full MediaPipe visualization
            # Draw key landmarks only for performance
            key_points = [0, 4, 8, 12, 16, 20]  # Wrist + fingertips
            for i in key_points:
                if i < len(landmarks):
                    x, y = landmarks[i]
                    cv2.circle(debug_frame, (x, y), 4, (0, 255, 0), -1)
            
            # Draw simple hand outline instead of full skeleton
            if len(landmarks) >= 21:
                # Connect key points with lines
                connections = [(0, 5), (5, 9), (9, 13), (13, 17), (17, 0)]  # Palm outline
                for start_idx, end_idx in connections:
                    start_point = landmarks[start_idx]
                    end_point = landmarks[end_idx]
                    cv2.line(debug_frame, start_point, end_point, (255, 255, 0), 2)
            
            # Draw additional debug info
            center = hand_data['center']
            palm_center = hand_data['palm_center']
            index_tip = hand_data['index_tip']
            bbox = hand_data['bbox']
            
            # Draw bounding box
            x, y, w, h = bbox
            cv2.rectangle(debug_frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            
            # Draw center points
            cv2.circle(debug_frame, center, 8, (255, 0, 0), -1)  # Blue center
            cv2.circle(debug_frame, palm_center, 6, (0, 0, 255), -1)  # Red palm
            cv2.circle(debug_frame, index_tip, 6, (255, 255, 0), -1)  # Cyan index tip
            
            # Draw finger states
            finger_states = hand_data.get('finger_states', [])
            finger_names = ['Thumb', 'Index', 'Middle', 'Ring', 'Pinky']
            y_offset = 30
            
            for i, (name, is_up) in enumerate(zip(finger_names, finger_states)):
                color = (0, 255, 0) if is_up else (0, 0, 255)
                status = "UP" if is_up else "DOWN"
                cv2.putText(debug_frame, f'{name}: {status}', 
                           (10, y_offset + i * 25), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
            
            # Draw hand info
            confidence = hand_data.get('confidence', 0)
            handedness = hand_data.get('handedness', 'Unknown')
            fingers_up = hand_data.get('fingers_up', 0)
            
            cv2.putText(debug_frame, f'Hand: {handedness} ({confidence:.2f})', 
                       (10, debug_frame.shape[0] - 80), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            cv2.putText(debug_frame, f'Fingers Up: {fingers_up}', 
                       (10, debug_frame.shape[0] - 60), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            cv2.putText(debug_frame, f'Area: {int(hand_data.get("area", 0))}px', 
                       (10, debug_frame.shape[0] - 40), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            cv2.putText(debug_frame, 'MediaPipe Hand Detection - High Accuracy', 
                       (10, debug_frame.shape[0] - 20), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
        
        return debug_frame

class GestureRecognizer:
    """Enhanced gesture recognition using MediaPipe hand landmarks"""
    
    def __init__(self):
        self.gesture_history = []
        self.history_size = 10
        self.pointing_threshold = 8   # Reduced frames for faster pointing recognition
        self.last_position = None
        self.stationary_frames = 0
        self.movement_threshold = 15  # Reduced threshold for more sensitive movement detection
        
    def recognize_gesture(self, hand_data: Dict) -> HandGesture:
        """Classify gesture based on MediaPipe hand data"""
        
        if not hand_data or 'landmarks' not in hand_data:
            return HandGesture(
                gesture_type='none',
                confidence=0.0,
                position=(0, 0),
                hand_landmarks=None,
                finger_count=0
            )
        
        finger_states = hand_data.get('finger_states', [False] * 5)
        fingers_up = hand_data.get('fingers_up', 0)
        confidence = hand_data.get('confidence', 0.5)
        index_tip = hand_data.get('index_tip', hand_data['center'])
        
        # Track movement for stability
        if self.last_position:
            distance = math.sqrt(
                (index_tip[0] - self.last_position[0])**2 + 
                (index_tip[1] - self.last_position[1])**2
            )
            if distance < self.movement_threshold:
                self.stationary_frames += 1
            else:
                self.stationary_frames = 0
        else:
            self.stationary_frames = 0
            
        self.last_position = index_tip
        
        # Simplified binary gesture classification
        gesture_type = 'hover'  # Default to hover
        gesture_confidence = confidence
        
        if fingers_up <= 1:  # Closed fist (0-1 fingers)
            gesture_type = 'grab'
            gesture_confidence = min(confidence + 0.2, 1.0)
        else:  # Open hand (2+ fingers)
            gesture_type = 'hover'
            gesture_confidence = confidence
        
        # Make gestures more responsive by checking recent gesture history
        if len(self.gesture_history) >= 3:
            recent_gestures = [g['gesture'] for g in self.gesture_history[-3:]]
            if recent_gestures.count(gesture_type) >= 2:
                # Boost confidence if gesture is consistent
                gesture_confidence = min(gesture_confidence + 0.1, 1.0)
            
        # Use palm center for more stable positioning, index tip for pointing
        position = hand_data.get('palm_center', index_tip)
        if gesture_type == 'point':
            position = index_tip  # Use precise finger tip for pointing
            
        # Update history
        self.gesture_history.append({
            'gesture': gesture_type,
            'fingers': fingers_up,
            'position': position,
            'confidence': gesture_confidence
        })
        
        if len(self.gesture_history) > self.history_size:
            self.gesture_history.pop(0)
            
        return HandGesture(
            gesture_type=gesture_type,
            confidence=gesture_confidence,
            position=position,
            hand_landmarks=np.array(hand_data['landmarks']),
            finger_count=fingers_up
        )