import cv2
import numpy as np
import sys
import json

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

if __name__ == "__main__":
    main()

