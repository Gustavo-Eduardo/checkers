import cv2
import numpy as np
import sys
import json

"""
Design for Computer Vision System for Red Marker Detection and Move Tracking:

1. Camera Calibration and Board Mapping:
   - Calibrate the camera to get a perspective transform matrix that maps camera pixel coordinates to board squares.
   - Define the 8x8 grid of the checkers board in the camera frame.
   - Use this mapping to convert detected marker positions to board coordinates (row, col).

2. Marker Detection:
   - Use existing red color detection in HSV color space.
   - Apply noise reduction and contour detection.
   - Find the largest red contour and calculate its centroid.

3. Move Tracking:
   - Track the marker's position frame-to-frame.
   - Detect when the marker moves from one square to another.
   - Use a state machine to detect move start and end:
     * Marker placed on a piece (start square).
     * Marker moved to a new square (end square).
   - Debounce detection to avoid false positives.

4. Move Validation:
   - Send detected moves (start and end squares) to the frontend.
   - Frontend validates moves according to checkers rules.

5. Communication:
   - Output detected moves as JSON to stdout or via a WebSocket/HTTP API.
   - Include camera dimensions and board mapping info for frontend synchronization.

6. Real-time Processing:
   - Process frames asynchronously.
   - Limit frame rate for performance.

This design will be implemented incrementally in detection.py and integrated with the frontend game logic.
"""

def main():
    cap = cv2.VideoCapture(0)  # Use 0 or your specific camera ID
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Flip if needed for mirror effect
        frame = cv2.flip(frame, 1)

        # Convert to HSV (better for color filtering)
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        # Define red color range (2 ranges for red in HSV)
        lower_red1 = np.array([0, 100, 100])
        upper_red1 = np.array([10, 255, 255])

        lower_red2 = np.array([160, 100, 100])
        upper_red2 = np.array([179, 255, 255])

        # Create masks and combine
        mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
        mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
        mask = cv2.bitwise_or(mask1, mask2)

        # Noise reduction
        mask = cv2.erode(mask, None, iterations=2)
        mask = cv2.dilate(mask, None, iterations=2)

        # Find contours
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if contours:
            # Find the largest red object
            largest_contour = max(contours, key=cv2.contourArea)
            if cv2.contourArea(largest_contour) > 500:  # Ignore small noise
                # Get bounding box and center
                (x, y, w, h) = cv2.boundingRect(largest_contour)
                center_x = x + w // 2
                center_y = y + h // 2
                print(json.dumps({"camera_dimension": {"x": frame.shape[1], "y": frame.shape[0]}, "pointer": {"x": center_x, "y": center_y}}))
                sys.stdout.flush()
        # Exit on 'q' key
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

import time

BOARD_SIZE = 8

def calibrate_board_corners():
    """
    Hardcoded or interactive calibration of board corners in camera frame.
    Returns the four corners of the board in pixel coordinates in order:
    top-left, top-right, bottom-right, bottom-left.
    For simplicity, hardcode example values here.
    """
    # TODO: Replace with actual calibration or interactive method
    return [(100, 100), (500, 100), (500, 500), (100, 500)]

def get_perspective_transform(corners):
    """
    Compute perspective transform matrix from camera frame to board coordinates.
    """
    dst = np.array([
        [0, 0],
        [BOARD_SIZE, 0],
        [BOARD_SIZE, BOARD_SIZE],
        [0, BOARD_SIZE]
    ], dtype=np.float32)
    src = np.array(corners, dtype=np.float32)
    matrix = cv2.getPerspectiveTransform(src, dst)
    return matrix

def pixel_to_board_square(matrix, point):
    """
    Map pixel coordinates to board square (row, col).
    """
    pts = np.array([[point]], dtype=np.float32)
    dst = cv2.perspectiveTransform(pts, matrix)[0][0]
    col = int(dst[0])
    row = int(dst[1])
    if 0 <= row < BOARD_SIZE and 0 <= col < BOARD_SIZE:
        return (row, col)
    else:
        return None

def main():
    cap = cv2.VideoCapture(0)  # Use 0 or your specific camera ID
    corners = calibrate_board_corners()
    matrix = get_perspective_transform(corners)

    last_position = None
    move_start = None
    move_end = None
    move_detected = False
    move_cooldown = 1.0  # seconds to wait before detecting next move
    last_move_time = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        lower_red1 = np.array([0, 100, 100])
        upper_red1 = np.array([10, 255, 255])
        lower_red2 = np.array([160, 100, 100])
        upper_red2 = np.array([179, 255, 255])

        mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
        mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
        mask = cv2.bitwise_or(mask1, mask2)

        mask = cv2.erode(mask, None, iterations=2)
        mask = cv2.dilate(mask, None, iterations=2)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if contours:
            largest_contour = max(contours, key=cv2.contourArea)
            if cv2.contourArea(largest_contour) > 500:
                (x, y, w, h) = cv2.boundingRect(largest_contour)
                center_x = x + w // 2
                center_y = y + h // 2

                board_pos = pixel_to_board_square(matrix, (center_x, center_y))

                if board_pos is not None:
                    current_time = time.time()
                    if last_position != board_pos:
                        if move_start is None:
                            move_start = board_pos
                        else:
                            move_end = board_pos
                            if not move_detected and (current_time - last_move_time) > move_cooldown:
                                move_detected = True
                                last_move_time = current_time
                                move = {"start": move_start, "end": move_end}
                                print(json.dumps({"move": move}))
                                sys.stdout.flush()
                                move_start = None
                                move_end = None
                    last_position = board_pos
        else:
            last_position = None
            move_start = None
            move_end = None
            move_detected = False

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()

