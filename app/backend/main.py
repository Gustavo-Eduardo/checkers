#!/usr/bin/env python3
"""
Main entry point for the checkers game backend
"""

import sys
import os
import logging

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from api.websocket_server import GameWebSocketServer

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def main():
    """Main function to start the backend server"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Checkers Game Backend Server')
    parser.add_argument('--host', default='localhost', help='Host to bind to')
    parser.add_argument('--port', type=int, default=8765, help='Port to bind to')
    
    args = parser.parse_args()
    
    print("Starting Checkers Game Backend...")
    print(f"WebSocket Server running on ws://{args.host}:{args.port}")
    print("Press Ctrl+C to stop")
    
    server = GameWebSocketServer(host=args.host, port=args.port)
    
    try:
        server.start()
    except KeyboardInterrupt:
        print("\nShutting down server...")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()