#!/usr/bin/env python3
"""
MCP-DDS Agent Client Library

Provides a simple Python API for AI agents to interact with DDS topics
through the MCP-DDS Gateway.
"""
import asyncio
import json
import logging
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass


try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    logging.warning("MCP client not available. Install with: pip install mcp")


logger = logging.getLogger(__name__)


@dataclass
class DDSClientConfig:
    """Configuration for DDS client."""
    agent_name: str
    gateway_command: str = "python"
    gateway_script: str = "mcp_gateway.py"
    gateway_args: List[str] = None


class DDSClientError(Exception):
    """Raised when DDS client operations fail."""
    pass


class DDSAgentClient:
    """Client library for AI agents to access DDS topics via MCP gateway."""

    def __init__(self, agent_name: str, gateway_command: str = "python",
                 gateway_script: str = "mcp_gateway.py"):
        """
        Initialize DDS agent client.

        Args:
            agent_name: Name of this agent (must match gateway configuration)
            gateway_command: Command to run gateway (default: python)
            gateway_script: Path to gateway script (default: mcp_gateway.py)
        """
        if not MCP_AVAILABLE:
            raise DDSClientError("MCP client library not available")

        self.agent_name = agent_name
        self.gateway_command = gateway_command
        self.gateway_script = gateway_script

        self.session: Optional[ClientSession] = None
        self._subscriptions: Dict[str, str] = {}  # topic -> subscription_id
        self._connected = False

        logger.info(f"DDS Agent Client initialized for agent '{agent_name}'")

    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()

    async def connect(self) -> None:
        """Connect to the MCP-DDS gateway."""
        if self._connected:
            return

        try:
            # Create server parameters
            server_params = StdioServerParameters(
                command=self.gateway_command,
                args=[self.gateway_script],
                env=None
            )

            # Create stdio client
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    self.session = session
                    await session.initialize()
                    self._connected = True

                    logger.info(f"Connected to MCP-DDS gateway as '{self.agent_name}'")

        except Exception as e:
            logger.error(f"Failed to connect to gateway: {e}")
            raise DDSClientError(f"Connection failed: {e}")

    async def disconnect(self) -> None:
        """Disconnect from the MCP-DDS gateway."""
        if not self._connected:
            return

        # Unsubscribe from all active subscriptions
        for subscription_id in list(self._subscriptions.values()):
            try:
                await self.unsubscribe_by_id(subscription_id)
            except Exception as e:
                logger.warning(f"Error unsubscribing {subscription_id}: {e}")

        self._connected = False
        logger.info(f"Disconnected from MCP-DDS gateway")

    async def subscribe(self, topic_name: str, callback: Optional[Callable] = None) -> str:
        """
        Subscribe to a DDS topic.

        Args:
            topic_name: Name of the topic to subscribe to
            callback: Optional async callback function(topic, samples)

        Returns:
            Subscription ID

        Raises:
            DDSClientError: If subscription fails
        """
        if not self._connected:
            raise DDSClientError("Not connected to gateway")

        try:
            # Call subscribe tool via MCP
            result = await self.session.call_tool(
                "subscribe",
                arguments={
                    "agent_name": self.agent_name,
                    "topic_name": topic_name
                }
            )

            response = self._parse_result(result)

            if not response.get("success"):
                error = response.get("error", "Unknown error")
                raise DDSClientError(f"Subscription failed: {error}")

            subscription_id = response["subscription_id"]
            self._subscriptions[topic_name] = subscription_id

            logger.info(f"Subscribed to '{topic_name}' (ID: {subscription_id})")

            # If callback provided, start listener task
            if callback:
                asyncio.create_task(
                    self._subscription_listener(topic_name, subscription_id, callback)
                )

            return subscription_id

        except Exception as e:
            logger.error(f"Subscribe failed: {e}")
            raise DDSClientError(f"Subscribe failed: {e}")

    async def read(self, topic_name: str, max_samples: int = 10) -> List[Dict]:
        """
        Read samples from a DDS topic (one-time read).

        Args:
            topic_name: Name of the topic to read from
            max_samples: Maximum number of samples to read

        Returns:
            List of samples as dictionaries

        Raises:
            DDSClientError: If read fails
        """
        if not self._connected:
            raise DDSClientError("Not connected to gateway")

        try:
            # Call read tool via MCP
            result = await self.session.call_tool(
                "read",
                arguments={
                    "agent_name": self.agent_name,
                    "topic_name": topic_name,
                    "max_samples": max_samples
                }
            )

            response = self._parse_result(result)

            if not response.get("success"):
                error = response.get("error", "Unknown error")
                raise DDSClientError(f"Read failed: {error}")

            samples = response.get("samples", [])
            logger.info(f"Read {len(samples)} samples from '{topic_name}'")

            return samples

        except Exception as e:
            logger.error(f"Read failed: {e}")
            raise DDSClientError(f"Read failed: {e}")

    async def write(self, topic_name: str, data: Dict) -> None:
        """
        Write a sample to a DDS topic.

        Args:
            topic_name: Name of the topic to write to
            data: Sample data as dictionary

        Raises:
            DDSClientError: If write fails
        """
        if not self._connected:
            raise DDSClientError("Not connected to gateway")

        try:
            # Call write tool via MCP
            result = await self.session.call_tool(
                "write",
                arguments={
                    "agent_name": self.agent_name,
                    "topic_name": topic_name,
                    "data": data
                }
            )

            response = self._parse_result(result)

            if not response.get("success"):
                error = response.get("error", "Unknown error")
                raise DDSClientError(f"Write failed: {error}")

            logger.info(f"Wrote sample to '{topic_name}'")

        except Exception as e:
            logger.error(f"Write failed: {e}")
            raise DDSClientError(f"Write failed: {e}")

    async def unsubscribe(self, topic_name: str) -> None:
        """
        Unsubscribe from a DDS topic.

        Args:
            topic_name: Name of the topic to unsubscribe from

        Raises:
            DDSClientError: If unsubscribe fails
        """
        if topic_name not in self._subscriptions:
            logger.warning(f"Not subscribed to '{topic_name}'")
            return

        subscription_id = self._subscriptions[topic_name]
        await self.unsubscribe_by_id(subscription_id)
        del self._subscriptions[topic_name]

    async def unsubscribe_by_id(self, subscription_id: str) -> None:
        """
        Unsubscribe using subscription ID.

        Args:
            subscription_id: Subscription ID to cancel

        Raises:
            DDSClientError: If unsubscribe fails
        """
        if not self._connected:
            raise DDSClientError("Not connected to gateway")

        try:
            # Call unsubscribe tool via MCP
            result = await self.session.call_tool(
                "unsubscribe",
                arguments={
                    "subscription_id": subscription_id
                }
            )

            response = self._parse_result(result)

            if not response.get("success"):
                error = response.get("error", "Unknown error")
                raise DDSClientError(f"Unsubscribe failed: {error}")

            logger.info(f"Unsubscribed: {subscription_id}")

        except Exception as e:
            logger.error(f"Unsubscribe failed: {e}")
            raise DDSClientError(f"Unsubscribe failed: {e}")

    async def list_topics(self) -> Dict[str, List[str]]:
        """
        List all topics accessible to this agent.

        Returns:
            Dictionary with 'readable' and 'writable' topic lists

        Raises:
            DDSClientError: If listing fails
        """
        if not self._connected:
            raise DDSClientError("Not connected to gateway")

        try:
            # Call list_topics tool via MCP
            result = await self.session.call_tool(
                "list_topics",
                arguments={
                    "agent_name": self.agent_name
                }
            )

            response = self._parse_result(result)

            if not response.get("success"):
                error = response.get("error", "Unknown error")
                raise DDSClientError(f"List topics failed: {error}")

            topics = response.get("topics", {})
            return topics

        except Exception as e:
            logger.error(f"List topics failed: {e}")
            raise DDSClientError(f"List topics failed: {e}")

    async def get_topic_info(self, topic_name: str) -> Dict:
        """
        Get detailed information about a topic.

        Args:
            topic_name: Name of the topic

        Returns:
            Topic information including type definition

        Raises:
            DDSClientError: If request fails
        """
        if not self._connected:
            raise DDSClientError("Not connected to gateway")

        try:
            # Call get_topic_info tool via MCP
            result = await self.session.call_tool(
                "get_topic_info",
                arguments={
                    "topic_name": topic_name
                }
            )

            response = self._parse_result(result)

            if not response.get("success"):
                error = response.get("error", "Unknown error")
                raise DDSClientError(f"Get topic info failed: {error}")

            return response

        except Exception as e:
            logger.error(f"Get topic info failed: {e}")
            raise DDSClientError(f"Get topic info failed: {e}")

    async def _subscription_listener(self, topic_name: str, subscription_id: str,
                                    callback: Callable) -> None:
        """
        Background task to listen for subscription updates.

        Args:
            topic_name: Topic name
            subscription_id: Subscription ID
            callback: Callback function to invoke with samples
        """
        try:
            while topic_name in self._subscriptions:
                # Poll for new samples
                samples = await self.read(topic_name, max_samples=100)

                if samples:
                    # Invoke callback
                    if asyncio.iscoroutinefunction(callback):
                        await callback(topic_name, samples)
                    else:
                        callback(topic_name, samples)

                # Wait before next poll
                await asyncio.sleep(0.1)

        except Exception as e:
            logger.error(f"Subscription listener error for '{topic_name}': {e}")

    def _parse_result(self, result: Any) -> Dict:
        """Parse MCP tool result."""
        # Extract text content from result
        if hasattr(result, 'content'):
            for content in result.content:
                if hasattr(content, 'text'):
                    try:
                        # Try to parse as JSON
                        return json.loads(content.text)
                    except json.JSONDecodeError:
                        # If not JSON, try to evaluate as Python dict
                        import ast
                        return ast.literal_eval(content.text)

        return {}

    @property
    def is_connected(self) -> bool:
        """Check if connected to gateway."""
        return self._connected

    @property
    def active_subscriptions(self) -> List[str]:
        """Get list of active subscription topics."""
        return list(self._subscriptions.keys())


# Example usage functions
async def example_monitoring_agent():
    """Example: Monitoring agent that reads sensor data."""
    async with DDSAgentClient("monitoring_agent") as client:
        # List available topics
        topics = await client.list_topics()
        print(f"Available topics: {topics}")

        # Read latest sensor data
        samples = await client.read("SensorData", max_samples=5)
        print(f"Sensor data: {samples}")

        # Read system health
        health = await client.read("SystemHealth", max_samples=1)
        print(f"System health: {health}")


async def example_control_agent():
    """Example: Control agent that sends commands based on sensor data."""
    async with DDSAgentClient("control_agent") as client:
        # Read sensor data
        samples = await client.read("SensorData", max_samples=10)

        # Check temperature
        for sample in samples:
            if sample.get("temperature", 0) > 30:
                # Send cooling command
                command = {
                    "command_id": f"cmd_{sample['sensor_id']}",
                    "command_type": "cool",
                    "target": "hvac_system",
                    "priority": 1,
                    "parameters": json.dumps({"target_temp": 25}),
                    "issued_by": "control_agent",
                    "timestamp": int(time.time() * 1000),
                    "expiry_timestamp": int(time.time() * 1000) + 300000  # 5 min
                }

                await client.write("CommandTopic", command)
                print(f"Sent cooling command for sensor {sample['sensor_id']}")


async def example_query_agent():
    """Example: Query agent that performs one-time data analysis."""
    async with DDSAgentClient("query_agent") as client:
        # Get system health data
        health_data = await client.read("SystemHealth", max_samples=10)

        if health_data:
            # Calculate average CPU usage
            avg_cpu = sum(h.get("cpu_usage", 0) for h in health_data) / len(health_data)
            print(f"Average CPU usage: {avg_cpu:.2f}%")

            # Calculate average memory usage
            avg_mem = sum(h.get("memory_usage", 0) for h in health_data) / len(health_data)
            print(f"Average memory usage: {avg_mem:.2f}%")


if __name__ == "__main__":
    import sys
    import time

    # Configure logging
    logging.basicConfig(level=logging.INFO)

    print("MCP-DDS Agent Client Examples")
    print("=" * 50)
    print("1. Monitoring Agent Example")
    print("2. Control Agent Example")
    print("3. Query Agent Example")
    print("=" * 50)

    choice = input("Select example (1-3): ")

    if choice == "1":
        asyncio.run(example_monitoring_agent())
    elif choice == "2":
        asyncio.run(example_control_agent())
    elif choice == "3":
        asyncio.run(example_query_agent())
    else:
        print("Invalid choice")
