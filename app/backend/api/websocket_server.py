import asyncio
import websockets
import json
from typing import Set, Dict, Optional
import logging
import sys
import os
import socket

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.game_engine import CheckersEngine
from core.camera_manager import CameraManager
from vision.mediapipe_hand_tracker import MediaPipeHandTracker, GestureRecognizer
from processing.input_mapper import InputMapper
import cv2
import numpy as np
import base64

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GameWebSocketServer:
    """WebSocket server for real-time game communication"""
    
    def __init__(self, host='localhost', port=8765):
        self.host = host
        self.port = port
        self.clients: Set[websockets.WebSocketServerProtocol] = set()
        self.game_engine = CheckersEngine()
        self.camera_manager = CameraManager()
        self.hand_tracker = MediaPipeHandTracker()
        self.gesture_recognizer = GestureRecognizer()
        self.input_mapper = InputMapper()
        self.camera_active = False
        self.processing_task = None
        self.frame_skip_counter = 0
        self.frame_skip_rate = 1  # Process every frame for better responsiveness
        
    async def register(self, websocket):
        """Register new client connection"""
        self.clients.add(websocket)
        logger.info(f"Client connected. Total clients: {len(self.clients)}")
        
        # Send initial game state
        await websocket.send(json.dumps({
            'type': 'game_state',
            'data': {
                'board': self.game_engine.board.tolist(),
                'current_player': int(self.game_engine.current_player),
                'piece_counts': {k: int(v) for k, v in self.game_engine.get_piece_counts().items()},
                'all_valid_moves': {str(k): v for k, v in self.game_engine.get_all_valid_moves().items()}
            }
        }))
        
    async def unregister(self, websocket):
        """Remove client connection"""
        self.clients.discard(websocket)
        logger.info(f"Client disconnected. Total clients: {len(self.clients)}")
        
    async def handle_client(self, websocket, path=None):
        """Handle client messages"""
        await self.register(websocket)
        try:
            async for message in websocket:
                data = json.loads(message)
                response = await self.process_message(data)
                
                # Send response to requesting client
                if response:
                    if response.get('broadcast'):
                        await self.broadcast(response['data'])
                    else:
                        await websocket.send(json.dumps(response))
        except websockets.exceptions.ConnectionClosed:
            pass
        except Exception as e:
            logger.error(f"Error handling client: {e}")
        finally:
            await self.unregister(websocket)
            
    async def process_message(self, data: Dict) -> Optional[Dict]:
        """Process incoming messages"""
        msg_type = data.get('type')
        logger.info(f"Received message type: {msg_type}")
        
        if msg_type == 'start_camera':
            # Start camera processing
            success = await self.start_camera_processing()
            return {
                'type': 'camera_status',
                'data': {'active': success}
            }
            
        elif msg_type == 'stop_camera':
            # Stop camera processing
            await self.stop_camera_processing()
            return {
                'type': 'camera_status',
                'data': {'active': False}
            }
            
        elif msg_type == 'move':
            # Direct move command (fallback/testing)
            result = self.game_engine.make_move(
                tuple(data['from']),
                tuple(data['to'])
            )
            if result['valid']:
                return {
                    'broadcast': True,
                    'data': {
                        'type': 'move_result',
                        'data': result
                    }
                }
            else:
                return {
                    'type': 'move_error',
                    'data': result
                }
            
        elif msg_type == 'reset':
            self.game_engine.initialize_board()
            return {
                'broadcast': True,
                'data': {
                    'type': 'game_reset',
                    'data': {
                        'board': self.game_engine.board.tolist(),
                        'current_player': int(self.game_engine.current_player),
                        'piece_counts': {k: int(v) for k, v in self.game_engine.get_piece_counts().items()},
                        'all_valid_moves': {str(k): v for k, v in self.game_engine.get_all_valid_moves().items()}
                    }
                }
            }
            
        elif msg_type == 'get_valid_moves':
            pos = tuple(data.get('position', []))
            moves = self.game_engine.get_valid_moves(pos) if pos else []
            return {
                'type': 'valid_moves',
                'data': {
                    'position': pos,
                    'moves': moves
                }
            }
            
        return None
        
    async def broadcast(self, message: Dict):
        """Send message to all connected clients"""
        if self.clients:
            message_str = json.dumps(message)
            await asyncio.gather(
                *[client.send(message_str) for client in self.clients],
                return_exceptions=True
            )
            
    async def start_camera_processing(self) -> bool:
        """Start processing camera frames for gesture input"""
        if self.camera_active:
            return True
            
        if not self.camera_manager.initialize():
            logger.error("Failed to initialize camera")
            return False
            
        self.camera_manager.start_capture_thread()
        self.camera_active = True
        
        # Start processing loop
        self.processing_task = asyncio.create_task(self.process_camera_frames())
        logger.info("Camera processing started")
        return True
        
    async def stop_camera_processing(self):
        """Stop camera processing"""
        self.camera_active = False
        if self.processing_task:
            self.processing_task.cancel()
            try:
                await self.processing_task
            except asyncio.CancelledError:
                pass
        self.camera_manager.stop()
        logger.info("Camera processing stopped")
        
    async def process_camera_frames(self):
        """Process camera frames for gesture detection"""
        while self.camera_active:
            try:
                frame = self.camera_manager.get_frame()
                if frame is not None:
                    # Skip frames for better performance
                    self.frame_skip_counter += 1
                    if self.frame_skip_counter % self.frame_skip_rate != 0:
                        continue
                    
                    # Resize frame for faster processing
                    height, width = frame.shape[:2]
                    if width > 640:  # Resize large frames
                        scale = 640 / width
                        new_width = int(width * scale)
                        new_height = int(height * scale)
                        frame = cv2.resize(frame, (new_width, new_height))
                    
                    # Detect hand
                    hand_data = self.hand_tracker.detect_hands(frame)
                    
                    if hand_data:
                        # Recognize gesture
                        gesture = self.gesture_recognizer.recognize_gesture(hand_data)
                        
                        # Map to game action
                        action = self.input_mapper.map_gesture_to_action(
                            gesture,
                            (frame.shape[1], frame.shape[0])
                        )
                        
                        if action:
                            await self.handle_cv_action(action)
                        
                        # Send hand position for visualization (ensure serializable)
                        await self.broadcast({
                            'type': 'hand_position',
                            'data': {
                                'position': (float(gesture.position[0]), float(gesture.position[1])) if gesture.position else None,
                                'gesture': str(gesture.gesture_type),
                                'confidence': float(gesture.confidence)
                            }
                        })
                    
                    # Send frame preview with debug overlays (less frequently)
                    if len(self.clients) > 0 and self.frame_skip_counter % 3 == 0:  # Every 3rd processed frame
                        # Use MediaPipe's debug visualization
                        debug_frame = self.hand_tracker.create_debug_frame(frame, hand_data)
                        
                        # Resize debug frame for preview
                        preview = cv2.resize(debug_frame, (320, 240))
                        _, buffer = cv2.imencode('.jpg', preview, [cv2.IMWRITE_JPEG_QUALITY, 60])  # Lower quality
                        frame_base64 = base64.b64encode(buffer).decode('utf-8')
                        
                        # Extract only serializable debug info
                        debug_info = {}
                        if hand_data and 'debug' in hand_data:
                            debug_info = hand_data['debug'].copy()
                        
                        await self.broadcast({
                            'type': 'camera_frame',
                            'data': {
                                'frame': frame_base64,
                                'debug_info': debug_info
                            }
                        })
                
                await asyncio.sleep(0.05)   # ~20 FPS for better responsiveness
                
            except Exception as e:
                logger.error(f"Error processing camera frame: {e}")
                await asyncio.sleep(0.1)
                
    async def handle_cv_action(self, action: Dict):
        """Handle action from computer vision input"""
        action_type = action['type']
        
        if action_type == 'select_piece':
            pos = action['position']
            if pos:
                # Send selection feedback
                await self.broadcast({
                    'type': 'piece_selected',
                    'data': {
                        'position': pos,
                        'valid_moves': self.game_engine.get_valid_moves(pos)
                    }
                })
                
        elif action_type == 'move_piece':
            from_pos = action['from']
            to_pos = action['to']
            if from_pos and to_pos:
                result = self.game_engine.make_move(from_pos, to_pos)
                if result['valid']:
                    await self.broadcast({
                        'type': 'move_result',
                        'data': result
                    })
                    
        elif action_type == 'hover':
            pos = action['position']
            await self.broadcast({
                'type': 'hover_position',
                'data': {
                    'position': pos
                }
            })
    
    def create_debug_frame(self, original_frame, hand_data):
        """Create frame with debug overlays"""
        debug_frame = original_frame.copy()
        
        # Always recreate mask for visual overlay
        hsv = cv2.cvtColor(original_frame, cv2.COLOR_BGR2HSV)
        lower_skin = np.array([0, 30, 60], dtype=np.uint8)
        upper_skin = np.array([25, 255, 255], dtype=np.uint8)
        mask = cv2.inRange(hsv, lower_skin, upper_skin)
        
        # Draw detection mask as blue overlay
        mask_colored = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)
        mask_colored[:, :, 0] = 0  # Remove blue channel
        mask_colored[:, :, 1] = 0  # Remove green channel
        # Blend with original frame
        debug_frame = cv2.addWeighted(debug_frame, 0.7, mask_colored, 0.3, 0)
        
        # Draw all contours in yellow
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if contours:
            # Draw all contours
            cv2.drawContours(debug_frame, contours, -1, (0, 255, 255), 2)
            
            # Draw area text for each contour
            for i, contour in enumerate(contours):
                area = cv2.contourArea(contour)
                if area > 100:  # Only show significant contours
                    x, y, w, h = cv2.boundingRect(contour)
                    cv2.putText(debug_frame, f'{int(area)}', (x, y-10), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
        
        # Draw hand detection results
        if hand_data and hand_data.get('center'):
            center = hand_data['center']
            bbox = hand_data.get('bbox')
            area = hand_data.get('area', 0)
            
            # Draw center point
            cv2.circle(debug_frame, center, 8, (0, 255, 0), -1)
            cv2.circle(debug_frame, center, 12, (255, 255, 255), 2)
            
            # Draw bounding box
            if bbox:
                x, y, w, h = bbox
                cv2.rectangle(debug_frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                
                # Draw area text
                cv2.putText(debug_frame, f'Area: {int(area)}', (x, y - 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            
            # Draw topmost point
            if 'topmost' in hand_data:
                topmost = hand_data['topmost']
                cv2.circle(debug_frame, topmost, 6, (255, 0, 0), -1)
                cv2.putText(debug_frame, 'TOP', (topmost[0] - 15, topmost[1] - 10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 0, 0), 1)
            
            # Draw palm center
            if 'palm_center' in hand_data:
                palm = hand_data['palm_center']
                cv2.circle(debug_frame, palm, 8, (0, 0, 255), -1)
                cv2.circle(debug_frame, palm, 12, (255, 255, 255), 2)
                cv2.putText(debug_frame, 'PALM', (palm[0] - 20, palm[1] + 25), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)
        
        # Draw detection info
        height, width = debug_frame.shape[:2]
        cv2.putText(debug_frame, 'Advanced Multi-Method Hand Detection', 
                   (10, height - 80), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        if hand_data and hand_data.get('debug'):
            debug_info = hand_data['debug']
            method = debug_info.get('detection_method', 'unknown')
            fingers = debug_info.get('finger_count', 0)
            cv2.putText(debug_frame, f'Method: {method.title()} | Fingers: {fingers}', 
                       (10, height - 60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # Draw areas
        cv2.putText(debug_frame, 'Ideal Area: 3000-12000px | Max: 20000px', 
                   (10, height - 40), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # Draw legend
        cv2.putText(debug_frame, 'Green: Hand Center | Red: Palm | Blue: Skin Areas | Yellow: Motion/Edges', 
                   (10, height - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
        
        return debug_frame
            
    def start(self):
        """Start WebSocket server"""
        logger.info(f"Starting WebSocket server on {self.host}:{self.port}")
        
        async def server():
            # Force IPv4 to avoid IPv6 binding issues
            async with websockets.serve(self.handle_client, self.host, self.port, family=socket.AF_INET):
                await asyncio.Future()  # Run forever
                
        asyncio.run(server())