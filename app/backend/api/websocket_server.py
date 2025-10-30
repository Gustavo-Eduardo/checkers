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
from processing.input_mapper import InputMapper

# Try to import MediaPipe-based tracker, fall back to simple tracker if not available
try:
    from vision.simple_hand_tracker import SimpleHandTracker
    HAND_TRACKER_TYPE = "MediaPipe"
except ImportError:
    from vision.fallback_hand_tracker import FallbackHandTracker as SimpleHandTracker
    HAND_TRACKER_TYPE = "Fallback (Testing)"
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
        self.hand_tracker = SimpleHandTracker()
        self.input_mapper = InputMapper()
        self.camera_active = False
        self.processing_task = None
        self.frame_skip_counter = 0
        self.frame_skip_rate = 1  # Process every frame for better responsiveness
        self.board_dimensions = (640, 480)  # Default fallback dimensions
        
        logger.info(f"Using hand tracker: {HAND_TRACKER_TYPE}")
        
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
        logger.debug(f"Received message type: {msg_type}")
        
        if msg_type == 'start_camera':
            # Store board dimensions for coordinate alignment
            board_dimensions = data.get('board_dimensions')
            if board_dimensions:
                self.board_dimensions = (
                    int(board_dimensions['width']),
                    int(board_dimensions['height'])
                )
                logger.debug(f"Received board dimensions: {self.board_dimensions}")
            else:
                # Fallback to default dimensions
                self.board_dimensions = (640, 480)
                logger.debug("No board dimensions provided, using fallback")
            
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
            # Direct move command (used by mouse mode)
            result = self.game_engine.make_move(
                tuple(data['from']),
                tuple(data['to'])
            )
            if result['valid']:
                # Move successful - clear InputMapper selection
                self.input_mapper.update_game_state(None)
                # Transform result to match frontend expectations
                transformed_result = {
                    'valid': result['valid'],
                    'move': result['move'],
                    'board': result['board_state'],  # board_state -> board
                    'current_player': result['current_player'],
                    'game_over': result['game_over'],
                    'all_valid_moves': {str(k): v for k, v in result['all_valid_moves'].items()},
                    'piece_counts': {k: int(v) for k, v in self.game_engine.get_piece_counts().items()}  # Add missing piece counts
                }
                return {
                    'broadcast': True,
                    'data': {
                        'type': 'move_result',
                        'data': transformed_result
                    }
                }
            else:
                return {
                    'type': 'move_error',
                    'data': result
                }
            
        elif msg_type == 'reset':
            self.game_engine.initialize_board()
            self.input_mapper.update_game_state(None)  # Clear selection on reset
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
            # Update InputMapper state when mouse mode selects a piece
            if pos and moves:
                self.input_mapper.update_game_state(pos)
            else:
                self.input_mapper.update_game_state(None)
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
            logger.debug(f"WEBSOCKET: Broadcasting to {len(self.clients)} clients: {message.get('type', 'unknown_type')}")
            await asyncio.gather(
                *[client.send(message_str) for client in self.clients],
                return_exceptions=True
            )
        else:
            logger.debug(f"WEBSOCKET: No clients connected, cannot broadcast: {message.get('type', 'unknown_type')}")
            
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
            await self.processing_task
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
                    
                    # Detect hand using simple binary tracker
                    gesture = self.hand_tracker.detect_hand_state(frame)
                    
                    if gesture:
                        # Map to game action using board dimensions for coordinate alignment
                        action = self.input_mapper.map_gesture_to_action(
                            gesture,
                            self.board_dimensions
                        )
                        
                        if action:
                            logger.info(f"WEBSOCKET: CV action generated: {action['type']} at {action.get('position', 'N/A')}")
                            await self.handle_cv_action(action)
                        else:
                            logger.debug(f"WEBSOCKET: No action generated from gesture")
                        
                        # Send hand position for visualization (ensure serializable)
                        await self.broadcast({
                            'type': 'hand_position',
                            'data': {
                                'position': (float(gesture.position[0]), float(gesture.position[1])) if gesture.position else None,
                                'gesture': 'open' if gesture.is_open else 'grabbing',
                                'confidence': float(gesture.confidence),
                                'is_open': gesture.is_open  # Add binary state for cursor color
                            }
                        })
                    
                    # Send frame preview with debug overlays (less frequently)
                    if len(self.clients) > 0 and self.frame_skip_counter % 3 == 0:  # Every 3rd processed frame
                        # Use simple hand tracker's debug visualization with cursor colors
                        debug_frame = self.hand_tracker.create_debug_frame(frame, gesture)
                        
                        # Resize debug frame for preview
                        preview = cv2.resize(debug_frame, (320, 240))
                        _, buffer = cv2.imencode('.jpg', preview, [cv2.IMWRITE_JPEG_QUALITY, 60])  # Lower quality
                        frame_base64 = base64.b64encode(buffer).decode('utf-8')
                        
                        # Extract debug info for simple tracker
                        debug_info = {}
                        if gesture:
                            debug_info = {
                                'is_open': gesture.is_open,
                                'confidence': gesture.confidence,
                                'raw_area_ratio': gesture.raw_area_ratio,
                                'detection_method': 'simple_binary'
                            }
                        
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
        
        logger.info(f"WEBSOCKET: Handling CV action - Type: {action_type}, Position: {action.get('position', action.get('from', 'N/A'))}")
        
        if action_type == 'select_piece':
            pos = action['position']
            if pos:
                # Check if position has current player's piece (replicates mouse logic)
                piece = self.game_engine.board[pos[0]][pos[1]]
                logger.debug(f"WEBSOCKET: SELECT_PIECE at {pos} - Piece value: {piece}, Current player: {self.game_engine.current_player}")
                
                if piece != 0 and piece * self.game_engine.current_player > 0:
                    # Valid piece for current player - select it
                    self.input_mapper.update_game_state(pos)  # Sync InputMapper state
                    valid_moves = self.game_engine.get_valid_moves(pos)
                    
                    broadcast_msg = {
                        'type': 'piece_selected',
                        'data': {
                            'position': pos,
                            'valid_moves': valid_moves
                        }
                    }
                    logger.info(f"WEBSOCKET: Piece selected at {pos} with {len(valid_moves)} valid moves")
                    await self.broadcast(broadcast_msg)
                else:
                    # Invalid piece/empty square - clear selection
                    logger.debug(f"WEBSOCKET: Invalid piece/empty square at {pos}, clearing selection")
                    self.input_mapper.update_game_state(None)
                    
                    # Notify frontend to clear selection
                    await self.broadcast({
                        'type': 'selection_cleared',
                        'data': {}
                    })
                
        elif action_type == 'move_piece':
            from_pos = action['from']
            to_pos = action['to']
            if from_pos and to_pos:
                result = self.game_engine.make_move(from_pos, to_pos)
                if result['valid']:
                    # Move successful - clear selection
                    self.input_mapper.update_game_state(None)
                    # Transform result to match frontend expectations
                    transformed_result = {
                        'valid': result['valid'],
                        'move': result['move'],
                        'board': result['board_state'],  # board_state -> board
                        'current_player': result['current_player'],
                        'game_over': result['game_over'],
                        'all_valid_moves': {str(k): v for k, v in result['all_valid_moves'].items()},
                        'piece_counts': {k: int(v) for k, v in self.game_engine.get_piece_counts().items()}  # Add missing piece counts
                    }
                    await self.broadcast({
                        'type': 'move_result',
                        'data': transformed_result
                    })
                else:
                    # Invalid move - check if target square has current player's piece
                    target_piece = self.game_engine.board[to_pos[0]][to_pos[1]]
                    if target_piece != 0 and target_piece * self.game_engine.current_player > 0:
                        # Target square has valid piece - reselect it (replicates mouse behavior)
                        self.input_mapper.update_game_state(to_pos)
                        await self.broadcast({
                            'type': 'piece_selected',
                            'data': {
                                'position': to_pos,
                                'valid_moves': self.game_engine.get_valid_moves(to_pos)
                            }
                        })
                    else:
                        # Invalid move to empty/enemy square - clear selection
                        self.input_mapper.update_game_state(None)
                        await self.broadcast({
                            'type': 'selection_cleared',
                            'data': {}
                        })
                    
        elif action_type == 'cancel':
            # Clear selection (replicates right-click or clicking empty space)
            self.input_mapper.update_game_state(None)
            await self.broadcast({
                'type': 'selection_cleared',
                'data': {}
            })
                    
        elif action_type == 'hover':
            pos = action['position']
            await self.broadcast({
                'type': 'hover_position',
                'data': {
                    'position': pos
                }
            })
    
    # REMOVED: Old complex debug visualization replaced with simple binary tracker's built-in visualization
    # The SimpleHandTracker.create_debug_frame() method now handles all debug visualization
    # including blue cursor for open hand and orange cursor for closed hand
            
    def start(self):
        """Start WebSocket server"""
        logger.info(f"Starting WebSocket server on {self.host}:{self.port}")
        
        async def server():
            # Force IPv4 to avoid IPv6 binding issues
            async with websockets.serve(self.handle_client, self.host, self.port, family=socket.AF_INET):
                await asyncio.Future()  # Run forever
                
        asyncio.run(server())