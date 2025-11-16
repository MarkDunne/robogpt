"""Robot Control Agent - Control a robot via REST API using natural language."""

import os
import asyncio
import argparse
import base64
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
)
from openai.types.responses import ResponseTextDeltaEvent
from dotenv import load_dotenv
from PIL import Image
from openai import AsyncAzureOpenAI
from loguru import logger

load_dotenv()
set_tracing_disabled(True)
logger.remove()
logger.add(
    lambda msg: print(msg, end=""), format="<level>{message}</level>", colorize=True
)

client = AsyncAzureOpenAI(
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_version="2025-03-01-preview",
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
)


class RobotAPI:
    """Robot API wrapper."""

    def __init__(self, robot_ip: str):
        self.robot_ip = robot_ip

    def call(self, endpoint: str, **params) -> str:
        """Generic API call handler."""
        try:
            response = requests.get(
                f"http://{self.robot_ip}/api/{endpoint}", params=params, timeout=10
            )
            response.raise_for_status()
            logger.info(f"✓ {endpoint} {params if params else ''}")
            return f"✓ {endpoint}: {response.json()}"
        except Exception as e:
            logger.error(f"✗ {endpoint} failed: {e}")
            return f"✗ {endpoint} failed: {e}"

    def capture_photo(self) -> ToolOutputImage:
        """Capture and return photo from robot camera."""
        image = Image.open(
            BytesIO(
                requests.get(
                    f"http://{self.robot_ip}/api/camera/photo", timeout=10
                ).content
            )
        )
        image = image.rotate(-90, expand=True)

        # Save locally
        photo_path = Path("photos") / f"robot_photo_{datetime.now():%Y%m%d_%H%M%S}.jpg"
        photo_path.parent.mkdir(exist_ok=True)
        image.save(photo_path, "JPEG", quality=95)
        logger.info(f"📸 {photo_path}")

        # Convert to base64 for agent
        buffered = BytesIO()
        image.save(buffered, format="JPEG", quality=95)
        data_url = (
            f"data:image/jpeg;base64,{base64.b64encode(buffered.getvalue()).decode()}"
        )

        return ToolOutputImage(image_url=data_url, detail="auto")

    def get_status(self) -> str:
        """Get robot status."""
        try:
            status = requests.get(
                f"http://{self.robot_ip}/api/status", timeout=5
            ).json()
            camera = "✓" if status.get("camera") else "✗"
            return f"Camera: {camera} | WiFi: {status.get('wifi', 'Unknown')}"
        except Exception as e:
            return f"✗ Failed: {e}"


def create_tools(api: RobotAPI):
    """Create function tools from RobotAPI instance."""

    @function_tool
    def move_forward(
        duration: Annotated[int, "Duration in ms (50-5000)"] = 500,
    ) -> ToolOutputImage:
        """Move robot forward and return photo of new location."""
        api.call("motor/forward", duration=duration)
        import time

        time.sleep(0.2)  # Wait for robot to settle
        return api.capture_photo()

    @function_tool
    def move_backward(
        duration: Annotated[int, "Duration in ms (50-5000)"] = 500,
    ) -> ToolOutputImage:
        """Move robot backward and return photo of new location."""
        api.call("motor/backward", duration=duration)
        import time

        time.sleep(0.2)  # Wait for robot to settle
        return api.capture_photo()

    @function_tool
    def turn_left(
        duration: Annotated[int, "Duration in ms (50-5000)"] = 250,
    ) -> ToolOutputImage:
        """Turn robot left and return photo of new orientation."""
        api.call("motor/left", duration=duration)
        import time

        time.sleep(0.2)  # Wait for robot to settle
        return api.capture_photo()

    @function_tool
    def turn_right(
        duration: Annotated[int, "Duration in ms (50-5000)"] = 250,
    ) -> ToolOutputImage:
        """Turn robot right and return photo of new orientation."""
        api.call("motor/right", duration=duration)
        import time

        time.sleep(0.2)  # Wait for robot to settle
        return api.capture_photo()

    @function_tool
    def stop_motors() -> str:
        """Stop all motors immediately."""
        return api.call("motor/stop")

    @function_tool
    def get_status() -> str:
        """Get robot system status (camera and WiFi)."""
        return api.get_status()

    return [move_forward, move_backward, turn_left, turn_right, stop_motors, get_status]


async def run_robot_agent(robot_ip: str, task: str):
    """Run the robot control agent."""
    api = RobotAPI(robot_ip)

    agent = Agent(
        name="Robot Controller",
        instructions="""You are an Intelligent robot control agent for physical robot operations.

        Capabilities: Move (forward/backward/left/right, 50-5000ms), stop motors, check status.

        IMPORTANT BEHAVIOR:
        - Robot is in a safe environment. Execute commands IMMEDIATELY without asking permission.
        - ALL movement commands automatically return a photo of the new location/orientation.
        - You will receive an initial photo at the start showing the current view.
        - Use the photos returned from movements to understand what the robot sees and plan next actions.
        - DO NOT request additional photos - every movement gives you visual feedback automatically.

        Task approach:
        1. Analyze the initial photo to understand starting position
        2. Break task into logical movement steps
        3. Execute movements and observe returned photos
        4. Adjust strategy based on visual feedback

        Duration guidelines:
        - Short: 200-500ms | Medium: 500-1500ms | Long: 1500-3000ms
        - Turns: 250ms (~45-60°) | 90° turns: 400-500ms
        - Robot has momentum - for precise short turns use as low as 50ms""",
        tools=create_tools(api),
        model=OpenAIResponsesModel(model="gpt-5-nano", openai_client=client),
    )

    print(
        f"\n{'=' * 60}\n🤖 Robot Control Agent\n{'=' * 60}\nRobot IP: {robot_ip}\nTask: {task}\n{'=' * 60}\n"
    )

    # Capture initial photo and send with task
    logger.info("📸 Capturing initial robot view...")
    initial_photo = api.capture_photo()

    # Create a message with image and text content
    message_input = {
        "type": "message",
        "role": "user",
        "content": [
            {
                "type": "input_image",
                "image_url": initial_photo.image_url,
                "detail": initial_photo.detail,
            },
            {"type": "input_text", "text": f"Here is your current view. Task: {task}"},
        ],
    }

    result_stream = Runner.run_streamed(agent, [message_input], max_turns=100)

    print("\n💭 Agent Thinking:\n" + "-" * 60)
    async for event in result_stream.stream_events():
        # Stream agent thinking token-by-token
        if event.type == "raw_response_event" and isinstance(
            event.data, ResponseTextDeltaEvent
        ):
            print(event.data.delta, end="", flush=True)

        # Show tool calls as they happen
        elif event.type == "run_item_stream_event":
            if event.item.type == "tool_call_item":
                tool_name = (
                    event.item.name if hasattr(event.item, "name") else "unknown"
                )
                print(f"\n[Calling: {tool_name}]", flush=True)
            elif event.item.type == "tool_call_output_item":
                print(" ✓", flush=True)

    print(
        f"\n{'-' * 60}\n\n{'=' * 60}\n📋 Final Response:\n{'=' * 60}\n{result_stream.final_output}\n{'=' * 60}\n"
    )


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Control a robot using AI with natural language"
    )
    parser.add_argument("--robot-ip", required=True, help="Robot IP address")
    parser.add_argument("--task", required=True, help="Task description")
    args = parser.parse_args()
    asyncio.run(run_robot_agent(args.robot_ip, args.task))


if __name__ == "__main__":
    main()
