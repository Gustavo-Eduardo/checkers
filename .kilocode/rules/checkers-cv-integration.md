## Brief overview
- This rule file provides guidelines specific to the development of the checkers game integrated with computer vision for red marker detection and move tracking.
- It covers coding conventions, integration strategies, communication style, and architectural choices to ensure smooth collaboration and maintainability.

## Communication style
- Responses should be clear, concise, and technical, avoiding unnecessary verbosity.
- Provide direct, actionable instructions or code implementations.
- Avoid conversational fillers; focus on task completion and clarity.

## Development workflow
- Follow an iterative approach: design, implement, integrate, test, and refine.
- Use modular design to separate computer vision logic (backend) from game logic (frontend).
- Ensure real-time communication between backend and frontend using IPC or WebSocket.
- Prioritize robust error handling and validation in move detection and game state updates.

## Coding best practices
- Use descriptive, consistent naming conventions for functions, variables, and modules.
- Document key functions and modules with concise docstrings explaining purpose and usage.
- Maintain separation of concerns: vision processing, move detection, game logic, and UI updates should be distinct.
- Optimize image processing for performance without sacrificing accuracy.
- Use JSON for structured communication between backend and frontend.

## Project context
- The project uses Electron for the frontend with a Python backend for computer vision.
- The detection.py module handles camera input, red marker detection, and move identification.
- The frontend listens to backend events and updates the game state accordingly.
- Camera calibration and board mapping are critical for accurate move detection.

## Other guidelines
- Test thoroughly with real camera input to ensure marker detection accuracy and move validation.
- Keep UI feedback responsive to detected moves for a smooth user experience.
- When extending or refactoring, maintain compatibility with existing IPC communication protocols.
- Document any calibration or setup procedures clearly for ease of use.