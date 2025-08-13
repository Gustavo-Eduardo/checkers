#!/usr/bin/env python3
"""
Test script to validate finger extension detection logic without MediaPipe
"""

import numpy as np
import sys
import os

# Add backend path to imports
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app', 'backend'))

# Mock MediaPipe landmarks for testing
def create_mock_open_hand_landmarks():
    """Create mock landmarks for a fully open hand (5 fingers extended)"""
    # MediaPipe hand landmarks (21 points) - simulating open hand
    # These are normalized coordinates, but we'll use pixel-like values for easier testing
    landmarks = [
        (100, 200),  # 0: WRIST
        (120, 180),  # 1: THUMB_CMC
        (140, 160),  # 2: THUMB_MCP
        (160, 140),  # 3: THUMB_IP
        (180, 120),  # 4: THUMB_TIP (extended)
        (130, 190),  # 5: INDEX_MCP
        (130, 160),  # 6: INDEX_PIP
        (130, 130),  # 7: INDEX_DIP
        (130, 100),  # 8: INDEX_TIP (extended)
        (150, 190),  # 9: MIDDLE_MCP (palm center reference)
        (150, 150),  # 10: MIDDLE_PIP
        (150, 120),  # 11: MIDDLE_DIP
        (150, 90),   # 12: MIDDLE_TIP (extended)
        (170, 190),  # 13: RING_MCP
        (170, 160),  # 14: RING_PIP
        (170, 130),  # 15: RING_DIP
        (170, 100),  # 16: RING_TIP (extended)
        (190, 190),  # 17: PINKY_MCP
        (190, 170),  # 18: PINKY_PIP
        (190, 150),  # 19: PINKY_DIP
        (190, 130),  # 20: PINKY_TIP (extended)
    ]
    return landmarks

def create_mock_closed_fist_landmarks():
    """Create mock landmarks for a closed fist (0 fingers extended)"""
    # All fingertips curled back toward palm - more realistic positions
    landmarks = [
        (100, 200),  # 0: WRIST
        (120, 180),  # 1: THUMB_CMC
        (140, 160),  # 2: THUMB_MCP
        (145, 170),  # 3: THUMB_IP (curled back)
        (140, 175),  # 4: THUMB_TIP (curled toward palm, closer to wrist than MCP)
        (130, 190),  # 5: INDEX_MCP
        (135, 185),  # 6: INDEX_PIP
        (138, 188),  # 7: INDEX_DIP (curled back toward palm)
        (135, 185),  # 8: INDEX_TIP (same level as PIP, curled)
        (150, 190),  # 9: MIDDLE_MCP (palm center reference)
        (155, 185),  # 10: MIDDLE_PIP
        (157, 187),  # 11: MIDDLE_DIP (curled back)
        (155, 185),  # 12: MIDDLE_TIP (same level as PIP, curled)
        (170, 190),  # 13: RING_MCP
        (165, 185),  # 14: RING_PIP
        (162, 187),  # 15: RING_DIP (curled back)
        (165, 185),  # 16: RING_TIP (same level as PIP, curled)
        (190, 190),  # 17: PINKY_MCP
        (185, 185),  # 18: PINKY_PIP
        (182, 187),  # 19: PINKY_DIP (curled back)
        (185, 185),  # 20: PINKY_TIP (same level as PIP, curled)
    ]
    return landmarks

def create_mock_two_fingers_landmarks():
    """Create mock landmarks for peace sign (2 fingers extended)"""
    landmarks = [
        (100, 200),  # 0: WRIST
        (120, 180),  # 1: THUMB_CMC
        (140, 160),  # 2: THUMB_MCP
        (160, 140),  # 3: THUMB_IP
        (150, 150),  # 4: THUMB_TIP (curled)
        (130, 190),  # 5: INDEX_MCP
        (130, 160),  # 6: INDEX_PIP
        (130, 130),  # 7: INDEX_DIP
        (130, 100),  # 8: INDEX_TIP (extended)
        (150, 190),  # 9: MIDDLE_MCP (palm center reference)
        (150, 150),  # 10: MIDDLE_PIP
        (150, 120),  # 11: MIDDLE_DIP
        (150, 90),   # 12: MIDDLE_TIP (extended)
        (170, 190),  # 13: RING_MCP
        (165, 180),  # 14: RING_PIP
        (162, 175),  # 15: RING_DIP
        (160, 170),  # 16: RING_TIP (curled)
        (190, 190),  # 17: PINKY_MCP
        (185, 180),  # 18: PINKY_PIP
        (182, 175),  # 19: PINKY_DIP
        (180, 170),  # 20: PINKY_TIP (curled)
    ]
    return landmarks

# Mock the SimpleHandTracker methods for testing
class MockHandTracker:
    def __init__(self):
        pass
        
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
            
            print(f"  thumb: tip_dist={tip_to_palm:.1f}, mcp_dist={mcp_to_palm:.1f}, cmc_dist={cmc_to_palm:.1f}")
            print(f"    progression_check={progression_check}, angle_check={angle_check} -> {is_extended}")
            
            return (is_extended, tip_to_palm)
        except Exception as e:
            print(f"    thumb: Error in detection: {e}")
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
            # Vector from DIP to TIP
            v3 = tip - dip
            
            angle_check = True
            if np.linalg.norm(v1) > 0 and np.linalg.norm(v2) > 0:
                # Angle between MCP-PIP and PIP-DIP segments
                cos_angle1 = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
                angle_check = cos_angle1 > -0.2  # Allow some curl, but not too much
            
            # Combine all checks - need at least distance check AND progression check
            is_extended = distance_check and progression_check and angle_check
            
            print(f"  {finger_name}: tip_dist={tip_to_palm:.1f}, pip_dist={pip_to_palm:.1f}, mcp_dist={mcp_to_palm:.1f}")
            print(f"    distance_check={distance_check}, progression_check={progression_check}, angle_check={angle_check} -> {is_extended}")
            
            return (is_extended, tip_to_palm)
        except Exception as e:
            print(f"    {finger_name}: Error in detection: {e}")
            return (False, 0.0)
            
    def _detect_finger_extensions(self, landmarks: list) -> dict:
        """Detect which fingers are extended using MediaPipe hand landmarks"""
        
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
                
            print(f"Finger extension: {extended_fingers} (count: {extended_count})")
            
            return {
                'extended_count': extended_count,
                'distances': distances,
                'extended_fingers': extended_fingers
            }
            
        except Exception as e:
            print(f"Finger extension detection failed: {e}")
            return {'extended_count': -1, 'distances': {}, 'extended_fingers': []}

def test_finger_detection():
    """Test the finger detection logic with mock data"""
    
    print("=== Testing Finger Extension Detection Logic ===\n")
    
    tracker = MockHandTracker()
    
    test_cases = [
        ("Fully Open Hand (5 fingers)", create_mock_open_hand_landmarks(), True),
        ("Closed Fist (0 fingers)", create_mock_closed_fist_landmarks(), False),
        ("Peace Sign (2 fingers)", create_mock_two_fingers_landmarks(), True),
    ]
    
    for test_name, landmarks, expected_open in test_cases:
        print(f"Testing: {test_name}")
        print(f"Expected state: {'OPEN' if expected_open else 'CLOSED'}")
        
        result = tracker._detect_finger_extensions(landmarks)
        extended_count = result['extended_count']
        extended_fingers = result['extended_fingers']
        distances = result['distances']
        
        # Apply our detection logic
        detected_open = extended_count >= 2
        
        print(f"Extended fingers: {extended_count} ({extended_fingers})")
        print(f"Detected state: {'OPEN' if detected_open else 'CLOSED'}")
        print(f"Finger distances: {distances}")
        
        # Check if detection matches expectation
        if detected_open == expected_open:
            print("✅ PASS - Detection matches expected result")
        else:
            print("❌ FAIL - Detection does not match expected result")
            
        print("-" * 50)

if __name__ == "__main__":
    test_finger_detection()