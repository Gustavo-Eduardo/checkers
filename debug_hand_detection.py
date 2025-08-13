#!/usr/bin/env python3
"""
Debug script to analyze hand detection issues
"""

import sys
import os
import cv2
import numpy as np
import logging

# Add backend path to imports
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app', 'backend'))

from vision.simple_hand_tracker import SimpleHandTracker
from core.camera_manager import CameraManager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def main():
    """Debug the hand detection system"""
    
    print("=== Hand Detection Debug Tool ===")
    print("This tool will help analyze why hand detection is failing")
    print("Instructions:")
    print("- Hold your hand clearly in front of the camera")
    print("- Try both open hand and closed fist")
    print("- Watch the debug values in the console and on screen")
    print("- Press 'q' to quit, 'r' to reset state history")
    print()
    
    # Initialize camera
    camera = CameraManager()
    if not camera.initialize():
        print("ERROR: Could not initialize camera")
        return
        
    camera.start_capture_thread()
    
    # Initialize hand tracker
    tracker = SimpleHandTracker()
    
    # Debug data collection
    area_ratios = []
    states = []
    frame_count = 0
    
    try:
        while True:
            frame = camera.get_frame()
            if frame is None:
                continue
                
            frame_count += 1
            
            # Detect hand gesture
            gesture = tracker.detect_hand_state(frame)
            
            if gesture:
                area_ratios.append(gesture.raw_area_ratio)
                states.append(gesture.is_open)
                
                # Print debug info every 10 frames
                if frame_count % 10 == 0:
                    recent_ratios = area_ratios[-20:] if len(area_ratios) >= 20 else area_ratios
                    avg_ratio = np.mean(recent_ratios) if recent_ratios else 0
                    
                    print(f"\nFrame {frame_count}:")
                    print(f"  Current state: {'OPEN' if gesture.is_open else 'CLOSED/GRABBED'}")
                    print(f"  Extended fingers: {getattr(gesture, 'extended_fingers', 'N/A')}")
                    print(f"  Area ratio: {gesture.raw_area_ratio:.3f}")
                    print(f"  Avg ratio (last 20): {avg_ratio:.3f}")
                    print(f"  Confidence: {gesture.confidence:.2f}")
                    print(f"  State history length: {len(tracker.state_history)}")
                    
                    # Show finger distances if available
                    if hasattr(gesture, 'finger_distances') and gesture.finger_distances:
                        print(f"  Finger distances: {gesture.finger_distances}")
                    
                    # Analysis based on finger counting
                    if hasattr(gesture, 'extended_fingers'):
                        expected_state = gesture.extended_fingers >= 2
                        if expected_state != gesture.is_open:
                            print(f"  ⚠️  WARNING: {gesture.extended_fingers} fingers extended suggests {'OPEN' if expected_state else 'CLOSED'}, but detected as {'OPEN' if gesture.is_open else 'CLOSED'}!")
                    
                    # Legacy area ratio analysis
                    if gesture.is_open and gesture.raw_area_ratio < 0.65:
                        print(f"  ℹ️  Area ratio suggests closed ({gesture.raw_area_ratio:.3f} < 0.65) but finger detection overrides")
                    elif not gesture.is_open and gesture.raw_area_ratio > 0.65:
                        print(f"  ℹ️  Area ratio suggests open ({gesture.raw_area_ratio:.3f} > 0.65) but finger detection overrides")
            
            # Create and show debug frame
            debug_frame = tracker.create_debug_frame(frame, gesture)
            
            # Add additional debug text
            if gesture:
                # Show extended fingers count prominently
                finger_count = getattr(gesture, 'extended_fingers', -1)
                finger_color = (0, 255, 0) if finger_count >= 2 else (0, 0, 255) if finger_count >= 0 else (128, 128, 128)
                cv2.putText(debug_frame, f'Extended Fingers: {finger_count}', 
                           (debug_frame.shape[1] - 250, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, finger_color, 2)
                
                # Show detection logic
                if finger_count >= 0:
                    logic_text = "FINGER DETECTION: 0-1=CLOSED, 2+=OPEN"
                    cv2.putText(debug_frame, logic_text, 
                               (debug_frame.shape[1] - 350, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 0), 1)
                
                # Show frame counter
                cv2.putText(debug_frame, f'Frame: {frame_count}', 
                           (10, debug_frame.shape[0] - 100), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                
                # Show current vs detected state
                current_str = "OPEN" if tracker.current_state else "CLOSED"
                cv2.putText(debug_frame, f'State: {current_str}', 
                           (10, debug_frame.shape[0] - 80), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            
            cv2.imshow('Hand Detection Debug', debug_frame)
            
            # Handle key presses
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('r'):
                print("\n🔄 Resetting state history...")
                tracker.state_history = []
                tracker.current_state = True  # Reset to open
                
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    finally:
        camera.stop()
        cv2.destroyAllWindows()
        
        # Final analysis
        if area_ratios:
            print(f"\n=== ANALYSIS SUMMARY ===")
            print(f"Total frames with hand detected: {len(area_ratios)}")
            print(f"Area ratio statistics:")
            print(f"  Min: {np.min(area_ratios):.3f}")
            print(f"  Max: {np.max(area_ratios):.3f}")
            print(f"  Mean: {np.mean(area_ratios):.3f}")
            print(f"  Std: {np.std(area_ratios):.3f}")
            
            # Analyze threshold effectiveness
            open_ratios = [r for i, r in enumerate(area_ratios) if i < len(states) and states[i]]
            closed_ratios = [r for i, r in enumerate(area_ratios) if i < len(states) and not states[i]]
            
            if open_ratios:
                print(f"Open hand ratios - Mean: {np.mean(open_ratios):.3f}, Range: {np.min(open_ratios):.3f}-{np.max(open_ratios):.3f}")
            if closed_ratios:
                print(f"Closed hand ratios - Mean: {np.mean(closed_ratios):.3f}, Range: {np.min(closed_ratios):.3f}-{np.max(closed_ratios):.3f}")
                
            # Suggest better thresholds
            all_ratios = np.array(area_ratios)
            suggested_open_to_closed = np.percentile(all_ratios, 25)
            suggested_closed_to_open = np.percentile(all_ratios, 75)
            
            print(f"\n🔧 SUGGESTED THRESHOLDS:")
            print(f"  Current: open→closed = {tracker.open_to_closed_threshold:.3f}, closed→open = {tracker.closed_to_open_threshold:.3f}")
            print(f"  Suggested: open→closed = {suggested_open_to_closed:.3f}, closed→open = {suggested_closed_to_open:.3f}")

if __name__ == "__main__":
    main()