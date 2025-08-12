import cv2
import numpy as np
from typing import Optional, Tuple
import threading
import queue
import platform

class CameraManager:
    """Manages camera capture with optimized settings for hand tracking"""
    
    def __init__(self, camera_id: int = 0):
        self.camera_id = camera_id
        self.cap = None
        self.frame_queue = queue.Queue(maxsize=2)
        self.is_running = False
        self.platform = platform.system()
        
    def initialize(self) -> bool:
        """Initialize camera with optimal settings for gesture detection"""
        # Platform-specific backend selection
        backend_map = {
            'Windows': cv2.CAP_DSHOW,
            'Darwin': cv2.CAP_AVFOUNDATION,
            'Linux': cv2.CAP_V4L2
        }
        backend = backend_map.get(self.platform, cv2.CAP_ANY)
        
        self.cap = cv2.VideoCapture(self.camera_id, backend)
        
        if not self.cap.isOpened():
            # Try fallback without specific backend
            self.cap = cv2.VideoCapture(self.camera_id)
            
        if self.cap.isOpened():
            # Optimize for low latency
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            self.cap.set(cv2.CAP_PROP_FPS, 60)
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            
            # Platform-specific optimizations
            if cv2.CAP_PROP_FOURCC:
                self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))
                
            return True
        return False
    
    def start_capture_thread(self):
        """Start background thread for continuous capture"""
        if self.cap and self.cap.isOpened():
            self.is_running = True
            self.capture_thread = threading.Thread(target=self._capture_loop)
            self.capture_thread.daemon = True
            self.capture_thread.start()
        
    def _capture_loop(self):
        """Background capture loop for consistent frame rate"""
        while self.is_running:
            if self.cap and self.cap.isOpened():
                ret, frame = self.cap.read()
                if ret:
                    # Drop old frames to maintain real-time performance
                    if self.frame_queue.full():
                        try:
                            self.frame_queue.get_nowait()
                        except queue.Empty:
                            pass
                    self.frame_queue.put(frame)
    
    def get_frame(self) -> Optional[np.ndarray]:
        """Get latest frame from queue"""
        try:
            return self.frame_queue.get(timeout=0.1)
        except queue.Empty:
            return None
            
    def stop(self):
        """Stop capture and release resources"""
        self.is_running = False
        if hasattr(self, 'capture_thread'):
            self.capture_thread.join(timeout=1.0)
        if self.cap:
            self.cap.release()
            
    def __del__(self):
        """Cleanup on deletion"""
        self.stop()