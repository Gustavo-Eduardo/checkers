# Vision Checkers

A fully digital checkers game that uses computer vision to detect user input through hand gestures, pointing, or visual markers. The game renders a virtual checkers board on screen while a camera captures user interactions to control piece movements.

## Features

- 🎯 **Computer Vision Input**: Use hand gestures to control the game
- 🖱️ **Mouse Control**: Fallback to traditional mouse input
- 🎮 **Complete Checkers Game**: Full implementation of American checkers rules
- 🌐 **Real-time Communication**: WebSocket-based frontend-backend communication
- 🎨 **Modern UI**: Beautiful Electron-based desktop application
- 📱 **Cross-platform**: Works on Windows, macOS, and Linux

## Architecture

- **Frontend**: Electron + JavaScript with Canvas rendering
- **Backend**: Python with OpenCV for computer vision
- **Communication**: WebSocket for real-time game updates
- **Game Engine**: Complete checkers logic with move validation
- **Vision System**: Hand tracking and gesture recognition

## Prerequisites

- Node.js (v16 or higher)
- Python 3.7 or higher
- A webcam (for computer vision input)

## Installation

1. **Navigate to the app directory**:
   ```bash
   cd app
   ```

2. **Install Node.js dependencies**:
   ```bash
   npm install
   ```

3. **Install Python dependencies**:
   ```bash
   pip install -r backend/requirements.txt
   ```

## Running the Application

### Development Mode

To run the application in development mode:

```bash
npm run dev
```

This will:
- Start the Python backend server on `ws://localhost:8765`
- Launch the Electron frontend application
- Enable developer tools

### Production Mode

To run the application in production mode:

```bash
npm start
```

### Manual Backend Start

If you want to run the backend separately:

```bash
cd backend
python3 main.py --host localhost --port 8765
```

## How to Play

### Vision Controls (Computer Vision Mode)

1. **Start the Camera**: Click the "Start Camera" button in the left panel
2. **Point to Select**: 👉 Point your finger at a piece to select it
3. **Point to Move**: 👉 Point to a valid square to move the selected piece
4. **Grab Gesture**: ✊ Make a fist to grab/confirm selection
5. **Release Gesture**: ✋ Open your hand to cancel selection
6. **Hover**: 👋 Move your hand over squares to see hover effects

### Mouse Controls (Fallback Mode)

1. **Switch to Mouse Mode**: Select "Mouse Control" in the left panel
2. **Click to Select**: Left-click on a piece to select it
3. **Click to Move**: Left-click on a valid square to move
4. **Right-click**: Cancel current selection

### Game Rules

- Move pieces diagonally forward
- Jump over opponent pieces to capture them
- Reach the opposite end to promote to King
- Kings can move in any diagonal direction
- Capture all opponent pieces or block all their moves to win

## Controls & Shortcuts

- **N** or **Ctrl+N**: New Game
- **R** or **Ctrl+R**: Reset Board
- **C** or **Ctrl+C**: Toggle Camera
- **H** or **F1**: Show Help
- **1**: Switch to Vision Mode
- **2**: Switch to Mouse Mode
- **ESC**: Close modals

## Troubleshooting

### Camera Issues

- Ensure your webcam is connected and not being used by other applications
- Grant camera permissions when prompted
- Try restarting the application if camera fails to initialize

### Backend Connection Issues

- Make sure no other application is using port 8765
- Check that Python dependencies are installed correctly
- Try restarting the backend manually

### Performance Issues

- Close other applications that might be using the camera
- Lower the camera resolution in settings (if available)
- Use mouse mode if vision tracking is too slow

## Development

### Project Structure

```
app/
├── src/
│   ├── main/              # Electron main process
│   ├── renderer/          # Frontend application
│   └── preload/           # Preload scripts
├── backend/               # Python backend
│   ├── core/              # Game engine and camera
│   ├── vision/            # Computer vision modules  
│   ├── processing/        # Input processing
│   └── api/               # WebSocket server
├── assets/                # Game assets
└── package.json
```

### Building

To build the application for distribution:

```bash
npm run build
```

For all platforms:

```bash
npm run dist
```

## Technical Details

### Computer Vision Pipeline

1. **Camera Capture**: Optimized frame capture at 60 FPS
2. **Hand Detection**: Color-based hand detection and tracking
3. **Gesture Recognition**: Classification of hand gestures
4. **Input Mapping**: Convert gestures to game actions
5. **Validation**: Game rule validation and move processing

### Game Engine

- Complete American checkers rules implementation
- Move validation and game state management
- AI opponent support (extensible)
- Undo/redo functionality
- Game history tracking

### Communication Protocol

WebSocket messages for real-time updates:
- `game_state`: Current board state
- `move_result`: Move execution results
- `hand_position`: Real-time gesture data
- `camera_frame`: Camera preview
- Various control messages

## License

This project is licensed under the MIT License.

## Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues for bugs and feature requests.

## Acknowledgments

- OpenCV for computer vision capabilities
- Electron for cross-platform desktop development
- WebSockets for real-time communication
- Canvas API for game rendering