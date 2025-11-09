# Robot Control Agent

An AI-powered robot controller using the OpenAI Agents SDK. This agent can control your ESP32-S3-CAM robot through natural language commands.

## Features

- **Motor Control**: Move forward, backward, turn left/right, stop
- **Camera Operations**: Capture and save photos from the robot's camera
- **Status Monitoring**: Check system status and camera availability
- **Natural Language Interface**: Give commands in plain English
- **Sequential Execution**: Agent breaks down complex tasks into steps
- **Photo Storage**: Automatically saves captured photos with timestamps

## Setup

1. Install dependencies (already configured in `pyproject.toml`):
   ```bash
   uv sync
   ```

2. Create a `.env` file with your OpenAI API key:
   ```bash
   cp .env.example .env
   # Edit .env and add your OPENAI_API_KEY
   ```

3. Make sure your robot is connected to the network and note its IP address

## Usage

Run the agent with a natural language task:

```bash
python main.py --robot-ip 192.168.1.100 --task "Move forward for 2 seconds, take a photo, then turn right"
```

### Example Tasks

**Simple movement:**
```bash
python main.py --robot-ip 192.168.1.100 --task "Move forward for 1 second"
```

**Photo capture:**
```bash
python main.py --robot-ip 192.168.1.100 --task "Take a photo of what's in front of you"
```

**Complex sequence:**
```bash
python main.py --robot-ip 192.168.1.100 --task "Check the robot status, move forward, take a photo, turn left, take another photo, then stop"
```

**Exploration:**
```bash
python main.py --robot-ip 192.168.1.100 --task "Explore the room by moving forward, taking photos, and turning periodically"
```

## How It Works

The agent uses the OpenAI Agents SDK with function tools that map to your robot's API endpoints:

1. **Function Tools**: Each robot API endpoint is wrapped as a `@function_tool`
2. **Agent Instructions**: The agent has built-in knowledge about movement durations and safety
3. **Sequential Execution**: The agent uses `Runner.run()` to execute tasks step-by-step
4. **Photo Storage**: Photos are saved to the `photos/` directory with timestamps

## Agent Capabilities

The agent has access to these function tools:

- `move_forward(duration)` - Move forward (50-5000ms)
- `move_backward(duration)` - Move backward (50-5000ms)
- `turn_left(duration)` - Turn left (50-5000ms)
- `turn_right(duration)` - Turn right (50-5000ms)
- `stop_motors()` - Stop all motors
- `capture_photo()` - Take a photo and save it
- `get_status()` - Check robot status

## Architecture

```
┌─────────────────┐
│  Natural Lang.  │  "Move forward and take a photo"
│     Command     │
└────────┬────────┘
         │
         v
┌─────────────────┐
│   OpenAI Agent  │  Breaks down task into steps
│      (GPT)      │
└────────┬────────┘
         │
         v
┌─────────────────┐
│ Function Tools  │  Python functions calling robot API
└────────┬────────┘
         │
         v
┌─────────────────┐
│   Robot API     │  ESP32-S3-CAM endpoints
│  (HTTP/REST)    │
└─────────────────┘
```

## Photos

Captured photos are automatically saved to the `photos/` directory with timestamps:
```
photos/
├── robot_photo_20250109_143022.jpg
├── robot_photo_20250109_143145.jpg
└── robot_photo_20250109_143301.jpg
```

## Troubleshooting

**Connection errors:**
- Verify the robot IP address is correct
- Check that the robot is on the same network
- Ensure the robot's API server is running

**API Key errors:**
- Make sure your `.env` file contains a valid `OPENAI_API_KEY`
- Check that the key has sufficient credits

**Robot not responding:**
- Use the status check: `--task "Check the robot status"`
- Verify the robot's WiFi connection via serial console

## API Reference

See [API.md](API.md) for complete robot API documentation.
