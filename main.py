"""Robot Control Agent - Control a robot via REST API using natural language."""

import os
import asyncio
import argparse
import base64
import time
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Annotated, Literal

import requests
from pydantic import BaseModel
from agents import (
    Agent,
    Runner,
    function_tool,
    ToolOutputImage,
    OpenAIResponsesModel,
    set_tracing_disabled,
    RunHooks,
)
from openai.types.responses import (
    ResponseTextDeltaEvent,
    ResponseReasoningTextDeltaEvent,
    ResponseReasoningSummaryTextDeltaEvent,
)
from dotenv import load_dotenv
from PIL import Image
from openai import AsyncAzureOpenAI
from loguru import logger

load_dotenv()
set_tracing_disabled(True)
logger.remove()
logger.add(
    lambda msg: print(msg, end=""),
    format="<level>{message}</level>",
    colorize=True,
    level="INFO",  # DEBUG to see all events, INFO for normal operation
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
        time.sleep(0.2)  # Wait for robot to settle
        return api.capture_photo()

    @function_tool
    def move_backward(
        duration: Annotated[int, "Duration in ms (50-5000)"] = 500,
    ) -> ToolOutputImage:
        """Move robot backward and return photo of new location."""
        api.call("motor/backward", duration=duration)
        time.sleep(0.2)  # Wait for robot to settle
        return api.capture_photo()

    @function_tool
    def turn_left(
        duration: Annotated[int, "Duration in ms (50-5000)"] = 250,
    ) -> ToolOutputImage:
        """Turn robot left and return photo of new orientation."""
        api.call("motor/left", duration=duration)
        time.sleep(0.2)  # Wait for robot to settle
        return api.capture_photo()

    @function_tool
    def turn_right(
        duration: Annotated[int, "Duration in ms (50-5000)"] = 250,
    ) -> ToolOutputImage:
        """Turn robot right and return photo of new orientation."""
        api.call("motor/right", duration=duration)
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

    class Move(BaseModel):
        """A single robot movement."""
        action: Literal["forward", "backward", "left", "right"]
        duration: int

    @function_tool
    def execute_moves(
        moves: Annotated[
            list[Move],
            "List of moves to execute. Example: [{'action': 'forward', 'duration': 500}, {'action': 'right', 'duration': 250}]"
        ]
    ) -> ToolOutputImage:
        """Execute a sequence of movements and return photo of final position. Use this for efficient multi-step navigation."""
        for i, move in enumerate(moves):
            action = move.action.lower()
            duration = move.duration

            # Map action to motor endpoint
            endpoint_map = {
                "forward": "motor/forward",
                "backward": "motor/backward",
                "left": "motor/left",
                "right": "motor/right",
            }

            if action not in endpoint_map:
                logger.warning(f"Unknown action '{action}' in move {i+1}, skipping")
                continue

            # Execute the move
            api.call(endpoint_map[action], duration=duration)

            # Small delay between moves for robot stability
            if i < len(moves) - 1:  # Don't wait after the last move
                time.sleep(0.1)

        # Wait for robot to settle after final move
        time.sleep(0.2)

        # Capture and return final photo
        return api.capture_photo()

    return [move_forward, move_backward, turn_left, turn_right, stop_motors, get_status, execute_moves]


class ContextPruningHooks(RunHooks):
    """Prune context to keep only recent moves and a summary of older ones."""

    def __init__(self, keep_recent_turns: int = 5):
        self.keep_recent_turns = keep_recent_turns
        self.move_history = []

    async def on_run_turn_done(self, context, result):
        """After each turn, prune the context window."""
        # Track movements
        for item in result.new_items:
            if hasattr(item, "type") and item.type == "tool_call_item":
                tool_name = item.name if hasattr(item, "name") else "unknown"
                if tool_name in [
                    "move_forward",
                    "move_backward",
                    "turn_left",
                    "turn_right",
                ]:
                    self.move_history.append(tool_name)

        # If we have more than keep_recent_turns worth of context, prune
        if (
            len(result.all_items) > self.keep_recent_turns * 4
        ):  # ~4 items per turn (tool call + output + message)
            # Keep initial message, recent items, and inject a summary
            total_items = len(result.all_items)
            keep_recent = self.keep_recent_turns * 4

            # Create summary of pruned moves
            pruned_count = total_items - keep_recent - 1
            if pruned_count > 0:
                summary = f"[Context pruned: {pruned_count} items removed. Recent moves: {', '.join(self.move_history[-10:])}]"
                logger.info(f"🔄 {summary}")

            # Prune: keep first item (initial photo+task) and recent items
            result.all_items = [result.all_items[0]] + result.all_items[-keep_recent:]

        return result


async def run_robot_agent(robot_ip: str, task: str):
    """Run the robot control agent."""
    api = RobotAPI(robot_ip)

    agent = Agent(
        name="Robot Controller",
        instructions="""You are an Intelligent robot control agent for physical robot operations.

        Capabilities: Move (forward/backward/left/right, 50-5000ms), stop motors, check status, execute multiple moves in sequence.

        IMPORTANT BEHAVIOR:
        - Robot is in a safe environment. Execute commands IMMEDIATELY without asking permission.
        - ALL movement commands automatically return a photo of the new location/orientation.
        - You will receive an initial photo at the start showing the current view.
        - Use the photos returned from movements to understand what the robot sees and plan next actions.
        - Older context may be pruned to maintain performance - rely on recent photos for current state.

        EFFICIENCY TIP:
        - Use execute_moves() to batch 2-4 movements together when you have a clear plan
        - Example: execute_moves([{'action': 'forward', 'duration': 800}, {'action': 'right', 'duration': 250}])
        - This is MUCH faster than individual moves but less adaptive
        - Use single moves when you need to check the environment frequently

        Task approach:
        1. Analyze the current/most recent photo to understand position
        2. Plan 2-3 moves ahead based on what you see
        3. If confident, use execute_moves() to batch them
        4. If uncertain, use single moves and observe photos between
        5. Adjust strategy based on latest visual feedback

        Duration guidelines:
        - Short: 200-500ms | Medium: 500-1500ms | Long: 1500-3000ms
        - Turns: 250ms (~45-60°) | 90° turns: 400-500ms
        - Robot has momentum - for precise short turns use as low as 50ms""",
        tools=create_tools(api),
        model=OpenAIResponsesModel(model="gpt-5", openai_client=client),
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

    # Use context pruning to prevent slowdowns
    hooks = ContextPruningHooks(keep_recent_turns=5)
    result_stream = Runner.run_streamed(
        agent, [message_input], max_turns=100, hooks=hooks
    )

    print("\n💭 Agent Thinking:\n" + "-" * 60)

    # Track if we've seen any text output
    seen_text = False

    async for event in result_stream.stream_events():
        if event.type == "raw_response_event":
            # Stream reasoning tokens (internal thinking)
            if isinstance(event.data, ResponseReasoningTextDeltaEvent):
                print(
                    f"\033[2m{event.data.delta}\033[0m", end="", flush=True
                )  # Dim text for reasoning
                seen_text = True

            # Stream reasoning summary
            elif isinstance(event.data, ResponseReasoningSummaryTextDeltaEvent):
                print(
                    f"\033[36m{event.data.delta}\033[0m", end="", flush=True
                )  # Cyan for summary
                seen_text = True

            # Stream agent output token-by-token
            elif isinstance(event.data, ResponseTextDeltaEvent):
                print(event.data.delta, end="", flush=True)
                seen_text = True

        # Show tool calls as they happen
        elif event.type == "run_item_stream_event":
            if event.item.type == "reasoning_item":
                # Extract reasoning content from the item
                reasoning_text = None
                if hasattr(event.item, "content"):
                    content = event.item.content
                    # Content might be a list of content parts
                    if isinstance(content, list):
                        reasoning_text = "".join([
                            part.get("text", "") if isinstance(part, dict) else str(part)
                            for part in content
                        ])
                    elif isinstance(content, str):
                        reasoning_text = content
                    else:
                        reasoning_text = str(content)

                if reasoning_text and reasoning_text.strip():
                    print(f"\n\033[2m💭 {reasoning_text}\033[0m\n", flush=True)
                    seen_text = True
                else:
                    # Debug: show what we got
                    logger.debug(f"reasoning_item content: {event.item.content if hasattr(event.item, 'content') else 'NO CONTENT'}")

            elif event.item.type == "tool_call_item":
                tool_name = (
                    event.item.name if hasattr(event.item, "name") else "unknown"
                )
                # Add newline only if we've printed text before
                if seen_text:
                    print()
                print(f"🔧 [{tool_name}] ", end="", flush=True)
                seen_text = False
            elif event.item.type == "tool_call_output_item":
                print("✓", flush=True)
            elif event.item.type == "message_output_item":
                # Extract and show any text content from the message
                if hasattr(event.item, "content") and event.item.content:
                    message_text = (
                        event.item.content
                        if isinstance(event.item.content, str)
                        else str(event.item.content)
                    )
                    if message_text and message_text.strip():
                        print(f"\n💬 {message_text}", flush=True)
                        seen_text = True
                # Agent's message completed - add separator
                elif seen_text:
                    print("\n", end="", flush=True)
                    seen_text = False

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
