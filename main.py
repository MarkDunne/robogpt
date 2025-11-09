"""
Robot Control Agent using OpenAI Agents SDK

This agent can control a robot via REST API endpoints, including:
- Motor control (forward, backward, left, right, stop)
- Camera operations (capture photos)
- Status checking

Usage:
    python main.py --robot-ip <ROBOT_IP> --task "<your task description>"

Example:
    python main.py --robot-ip 192.168.1.100 --task "Move forward, take a photo, then turn right"
"""

import os
import asyncio
import argparse
import base64
import logging
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Annotated

import requests
from agents import (
    Agent,
    Runner,
    function_tool,
    ToolOutputImage,
    OpenAIResponsesModel,
    set_tracing_disabled,
    ItemHelpers,
)
from openai.types.responses import ResponseTextDeltaEvent

from dotenv import load_dotenv
from PIL import Image

from openai import AsyncAzureOpenAI

load_dotenv()

set_tracing_disabled(True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

API_VERSION = "2025-03-01-preview"
MODEL = "gpt-5"

client = AsyncAzureOpenAI(
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_version=API_VERSION,
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
)

# Global variable for robot IP
ROBOT_IP = None

# Default durations for robot movements (in milliseconds)
DEFAULT_TURN_DURATION = 250


@function_tool
def move_forward(
    duration: Annotated[int, "Movement duration in milliseconds (50-5000)"] = 500,
) -> str:
    """Move the robot forward for a specified duration."""
    logger.info(f"🚀 Moving forward for {duration}ms")
    try:
        url = f"http://{ROBOT_IP}/api/motor/forward"
        logger.debug(f"Sending GET request to {url} with duration={duration}")
        response = requests.get(
            url,
            params={"duration": duration},
            timeout=10,
        )
        response.raise_for_status()
        result = response.json()
        logger.info(f"✓ Successfully moved forward. Response: {result}")
        return f"✓ Moved forward for {duration}ms. Response: {result}"
    except Exception as e:
        logger.error(f"✗ Failed to move forward: {str(e)}")
        return f"✗ Failed to move forward: {str(e)}"


@function_tool
def move_backward(
    duration: Annotated[int, "Movement duration in milliseconds (50-5000)"] = 500,
) -> str:
    """Move the robot backward for a specified duration."""
    logger.info(f"🔙 Moving backward for {duration}ms")
    try:
        url = f"http://{ROBOT_IP}/api/motor/backward"
        logger.debug(f"Sending GET request to {url} with duration={duration}")
        response = requests.get(
            url,
            params={"duration": duration},
            timeout=10,
        )
        response.raise_for_status()
        result = response.json()
        logger.info(f"✓ Successfully moved backward. Response: {result}")
        return f"✓ Moved backward for {duration}ms. Response: {result}"
    except Exception as e:
        logger.error(f"✗ Failed to move backward: {str(e)}")
        return f"✗ Failed to move backward: {str(e)}"


@function_tool
def turn_left(
    duration: Annotated[int, "Turn duration in milliseconds (50-5000)"] = DEFAULT_TURN_DURATION,
) -> str:
    """Turn the robot left for a specified duration (default: 250ms)."""
    logger.info(f"↩️  Turning left for {duration}ms")
    try:
        url = f"http://{ROBOT_IP}/api/motor/left"
        logger.debug(f"Sending GET request to {url} with duration={duration}")
        response = requests.get(
            url,
            params={"duration": duration},
            timeout=10,
        )
        response.raise_for_status()
        result = response.json()
        logger.info(f"✓ Successfully turned left. Response: {result}")
        return f"✓ Turned left for {duration}ms. Response: {result}"
    except Exception as e:
        logger.error(f"✗ Failed to turn left: {str(e)}")
        return f"✗ Failed to turn left: {str(e)}"


@function_tool
def turn_right(
    duration: Annotated[int, "Turn duration in milliseconds (50-5000)"] = DEFAULT_TURN_DURATION,
) -> str:
    """Turn the robot right for a specified duration (default: 250ms)."""
    logger.info(f"↪️  Turning right for {duration}ms")
    try:
        url = f"http://{ROBOT_IP}/api/motor/right"
        logger.debug(f"Sending GET request to {url} with duration={duration}")
        response = requests.get(
            url,
            params={"duration": duration},
            timeout=10,
        )
        response.raise_for_status()
        result = response.json()
        logger.info(f"✓ Successfully turned right. Response: {result}")
        return f"✓ Turned right for {duration}ms. Response: {result}"
    except Exception as e:
        logger.error(f"✗ Failed to turn right: {str(e)}")
        return f"✗ Failed to turn right: {str(e)}"


@function_tool
def stop_motors() -> str:
    """Stop all robot motors immediately."""
    logger.info("🛑 Stopping motors")
    try:
        url = f"http://{ROBOT_IP}/api/motor/stop"
        logger.debug(f"Sending GET request to {url}")
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        result = response.json()
        logger.info(f"✓ Motors stopped successfully. Response: {result}")
        return f"✓ Motors stopped. Response: {result}"
    except Exception as e:
        logger.error(f"✗ Failed to stop motors: {str(e)}")
        return f"✗ Failed to stop motors: {str(e)}"


@function_tool
def capture_photo() -> ToolOutputImage:
    """
    Capture a photo from the robot's camera, rotate it 90 degrees clockwise, and return it as an image.
    The image is also saved locally for reference.
    """
    logger.info("📸 Capturing photo from robot camera")
    try:
        url = f"http://{ROBOT_IP}/api/camera/photo"
        logger.debug(f"Sending GET request to {url}")
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        logger.info(f"✓ Photo received from camera ({len(response.content)} bytes)")

        # Load image and rotate 90 degrees clockwise
        logger.debug("Processing image: loading and rotating 90° clockwise")
        image = Image.open(BytesIO(response.content))
        logger.debug(f"Original image size: {image.size}")
        rotated_image = image.rotate(-90, expand=True)
        logger.debug(f"Rotated image size: {rotated_image.size}")

        # Save photo with timestamp for local reference
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        photos_dir = Path("photos")
        photos_dir.mkdir(exist_ok=True)

        photo_path = photos_dir / f"robot_photo_{timestamp}.jpg"
        rotated_image.save(photo_path, "JPEG", quality=95)
        logger.info(f"✓ Photo saved locally to {photo_path}")

        # Convert rotated image to base64 data URL for the agent
        logger.debug("Converting image to base64 data URL for agent")
        buffered = BytesIO()
        rotated_image.save(buffered, format="JPEG", quality=95)
        img_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
        data_url = f"data:image/jpeg;base64,{img_base64}"
        logger.info(f"✓ Image converted to data URL ({len(data_url)} chars)")

        # Return as ToolOutputImage so the agent can see the photo
        logger.info("✓ Returning ToolOutputImage to agent for vision analysis")
        return ToolOutputImage(image_url=data_url, detail="high")
    except Exception as e:
        logger.error(f"✗ Failed to capture photo: {str(e)}")
        raise Exception(f"Failed to capture photo: {str(e)}")


@function_tool
def get_status() -> str:
    """Check the robot's system status including camera and WiFi connectivity."""
    logger.info("ℹ️  Checking robot status")
    try:
        url = f"http://{ROBOT_IP}/api/status"
        logger.debug(f"Sending GET request to {url}")
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        status = response.json()
        logger.debug(f"Status response: {status}")

        camera_status = "✓ Working" if status.get("camera") else "✗ Not initialized"
        wifi_ip = status.get("wifi", "Unknown")

        result = f"Robot Status:\n  Camera: {camera_status}\n  WiFi IP: {wifi_ip}"
        logger.info(
            f"✓ Status check complete: Camera={status.get('camera')}, IP={wifi_ip}"
        )
        return result
    except Exception as e:
        logger.error(f"✗ Failed to get status: {str(e)}")
        return f"✗ Failed to get status: {str(e)}"


async def run_robot_agent(robot_ip: str, task: str):
    """
    Initialize and run the robot control agent with a given task.

    Args:
        robot_ip: IP address of the robot
        task: Natural language description of what the robot should do
    """
    global ROBOT_IP
    ROBOT_IP = robot_ip

    logger.info("=" * 60)
    logger.info("🤖 Initializing Robot Control Agent")
    logger.info("=" * 60)
    logger.info(f"Robot IP: {robot_ip}")
    logger.info(f"Task: {task}")
    logger.info(f"Model: {MODEL}")
    logger.info("=" * 60)

    # Create the robot control agent
    logger.debug("Creating Agent instance with tools and instructions")
    agent = Agent(
        name="Robot Controller",
        instructions="""You are an intelligent robot control agent. You can control a physical robot
        through various commands and observe its environment through photos.

        Your capabilities:
        - Move the robot (forward, backward, left, right) with controllable duration (50-5000ms)
        - Stop the motors
        - Capture photos from the robot's camera
        - Check system status

        IMPORTANT: The robot is in a safe, controlled environment. It is SAFE to move and execute commands.
        You should execute your plan IMMEDIATELY without hesitation. The environment has been prepared
        for robot operation, and there are no obstacles or safety concerns that would prevent movement.

        When given a task:
        1. Break it down into logical steps
        2. IMMEDIATELY execute commands sequentially - do not ask for permission or confirmation
        3. Use the camera to gather visual information when needed
        4. Provide clear feedback on what you're doing and why
        5. Be decisive and execute your plan with confidence

        Duration guidelines:
        - Short movements: 200-500ms
        - Medium movements: 500-1500ms
        - Long movements: 1500-3000ms
        - Turns: Default is 250ms. This typically makes a ~45-60 degree turn. For 90 degree turns, use 400-500ms (adjust based on feedback)

        Execute the task directly and explain what you're doing as you perform each action.""",
        tools=[
            move_forward,
            move_backward,
            turn_left,
            turn_right,
            stop_motors,
            capture_photo,
            get_status,
        ],
        model=OpenAIResponsesModel(
            model=MODEL,
            openai_client=client,
        ),
    )

    print(f"\n{'=' * 60}")
    print(f"🤖 Robot Control Agent Started")
    print(f"{'=' * 60}")
    print(f"Robot IP: {robot_ip}")
    print(f"Task: {task}")
    print(f"{'=' * 60}\n")

    # Run the agent with streaming enabled
    logger.info("🚀 Starting agent execution with streaming")
    logger.debug(f"Running agent with task: {task}")

    print("\n💭 Agent Thinking (streaming):\n")
    print("-" * 60)

    result_stream = Runner.run_streamed(agent, task, max_turns=100)

    # Stream events to show agent thinking in real-time
    async for event in result_stream.stream_events():
        # Show token-by-token text output (agent's thinking)
        if event.type == "raw_response_event" and isinstance(event.data, ResponseTextDeltaEvent):
            print(event.data.delta, end="", flush=True)

        # Show completed messages
        elif event.type == "run_item_stream_event":
            if event.item.type == "message_output_item":
                message_text = ItemHelpers.text_message_output(event.item)
                if message_text:
                    logger.debug(f"Message completed: {message_text[:100]}...")

        # Show agent handoffs if they occur
        elif event.type == "agent_updated_stream_event":
            logger.debug(f"Agent updated: {event.new_agent.name}")

    print("\n" + "-" * 60)
    logger.info("✓ Agent execution complete")

    # Get the final result from the stream object
    final_result = result_stream

    logger.debug(
        f"Final output length: {len(final_result.final_output) if final_result.final_output else 0} chars"
    )

    print(f"\n{'=' * 60}")
    print("📋 Agent Final Response:")
    print(f"{'=' * 60}")
    print(final_result.final_output)
    print(f"{'=' * 60}\n")

    logger.info("🏁 Robot control agent session finished")


def main():
    """Main entry point for the robot control agent."""
    parser = argparse.ArgumentParser(
        description="Control a robot using an AI agent with natural language commands"
    )
    parser.add_argument(
        "--robot-ip",
        type=str,
        required=True,
        help="IP address of the robot (e.g., 192.168.1.100)",
    )
    parser.add_argument(
        "--task",
        type=str,
        required=True,
        help="Natural language description of what the robot should do",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging (shows detailed HTTP requests and image processing)",
    )

    args = parser.parse_args()

    # Set debug level if requested
    if args.debug:
        logger.setLevel(logging.DEBUG)
        logger.info("🐛 Debug logging enabled")

    # Run the async agent
    logger.info("Starting robot control application")
    asyncio.run(run_robot_agent(args.robot_ip, args.task))


if __name__ == "__main__":
    main()
