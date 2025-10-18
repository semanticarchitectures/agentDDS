#!/usr/bin/env python3
"""
MCP-DDS Gateway
Main gateway implementation for bridging AI agents to DDS via Model Context Protocol.
"""
import asyncio
import logging
import sys
from typing import Any, Dict, List, Optional
from pathlib import Path

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types

from config_manager import load_configuration, ConfigurationError
from dds_manager import DDSManager, DDSManagerError


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('mcp_gateway.log')
    ]
)
logger = logging.getLogger(__name__)


class MCPDDSGateway:
    """MCP-DDS Gateway server implementation."""

    def __init__(self):
        """Initialize the MCP-DDS Gateway."""
        self.server = Server("mcp-dds-gateway")
        self.dds_manager: Optional[DDSManager] = None
        self.gateway_config = None
        self.types_config = None

        # Track active agent sessions
        self.active_agents: Dict[str, Dict] = {}

        # Setup MCP tool handlers
        self._setup_tools()

        logger.info("MCP-DDS Gateway initialized")

    def _setup_tools(self) -> None:
        """Register MCP tools with the server."""

        @self.server.list_tools()
        async def list_tools() -> List[types.Tool]:
            """List available MCP tools."""
            return [
                types.Tool(
                    name="subscribe",
                    description="Subscribe to a DDS topic and receive real-time updates",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "agent_name": {
                                "type": "string",
                                "description": "Name of the agent requesting subscription"
                            },
                            "topic_name": {
                                "type": "string",
                                "description": "DDS topic name to subscribe to"
                            }
                        },
                        "required": ["agent_name", "topic_name"]
                    }
                ),
                types.Tool(
                    name="read",
                    description="Read samples from a DDS topic (one-time read)",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "agent_name": {
                                "type": "string",
                                "description": "Name of the agent requesting data"
                            },
                            "topic_name": {
                                "type": "string",
                                "description": "DDS topic name to read from"
                            },
                            "max_samples": {
                                "type": "integer",
                                "description": "Maximum number of samples to read",
                                "default": 10
                            }
                        },
                        "required": ["agent_name", "topic_name"]
                    }
                ),
                types.Tool(
                    name="write",
                    description="Write a sample to a DDS topic",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "agent_name": {
                                "type": "string",
                                "description": "Name of the agent writing data"
                            },
                            "topic_name": {
                                "type": "string",
                                "description": "DDS topic name to write to"
                            },
                            "data": {
                                "type": "object",
                                "description": "Sample data to write"
                            }
                        },
                        "required": ["agent_name", "topic_name", "data"]
                    }
                ),
                types.Tool(
                    name="unsubscribe",
                    description="Unsubscribe from a DDS topic",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "subscription_id": {
                                "type": "string",
                                "description": "Subscription ID to cancel"
                            }
                        },
                        "required": ["subscription_id"]
                    }
                ),
                types.Tool(
                    name="list_topics",
                    description="List all available DDS topics",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "agent_name": {
                                "type": "string",
                                "description": "Name of the agent"
                            }
                        },
                        "required": ["agent_name"]
                    }
                ),
                types.Tool(
                    name="get_topic_info",
                    description="Get detailed information about a DDS topic",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "topic_name": {
                                "type": "string",
                                "description": "DDS topic name"
                            }
                        },
                        "required": ["topic_name"]
                    }
                )
            ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: Any) -> List[types.TextContent]:
            """Handle MCP tool calls."""
            try:
                if name == "subscribe":
                    result = await self._handle_subscribe(arguments)
                elif name == "read":
                    result = await self._handle_read(arguments)
                elif name == "write":
                    result = await self._handle_write(arguments)
                elif name == "unsubscribe":
                    result = await self._handle_unsubscribe(arguments)
                elif name == "list_topics":
                    result = await self._handle_list_topics(arguments)
                elif name == "get_topic_info":
                    result = await self._handle_get_topic_info(arguments)
                else:
                    result = {"error": f"Unknown tool: {name}"}

                return [types.TextContent(type="text", text=str(result))]

            except Exception as e:
                logger.error(f"Error handling tool '{name}': {e}", exc_info=True)
                return [types.TextContent(
                    type="text",
                    text=f"Error: {str(e)}"
                )]

    async def _handle_subscribe(self, args: Dict) -> Dict:
        """Handle subscribe tool call."""
        agent_name = args["agent_name"]
        topic_name = args["topic_name"]

        # Check permissions
        if not self.gateway_config.can_agent_read_topic(agent_name, topic_name):
            logger.warning(f"Agent '{agent_name}' denied read access to '{topic_name}'")
            return {
                "success": False,
                "error": f"Agent '{agent_name}' does not have read permission for topic '{topic_name}'"
            }

        try:
            subscription_id = self.dds_manager.subscribe(topic_name)

            # Track subscription for this agent
            if agent_name not in self.active_agents:
                self.active_agents[agent_name] = {"subscriptions": []}
            self.active_agents[agent_name]["subscriptions"].append(subscription_id)

            logger.info(f"Agent '{agent_name}' subscribed to '{topic_name}' (ID: {subscription_id})")

            return {
                "success": True,
                "subscription_id": subscription_id,
                "topic_name": topic_name
            }

        except Exception as e:
            logger.error(f"Subscribe failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def _handle_read(self, args: Dict) -> Dict:
        """Handle read tool call."""
        agent_name = args["agent_name"]
        topic_name = args["topic_name"]
        max_samples = args.get("max_samples", 10)

        # Check permissions
        if not self.gateway_config.can_agent_read_topic(agent_name, topic_name):
            logger.warning(f"Agent '{agent_name}' denied read access to '{topic_name}'")
            return {
                "success": False,
                "error": f"Agent '{agent_name}' does not have read permission for topic '{topic_name}'"
            }

        # Apply configuration limits
        max_allowed = self.gateway_config.max_samples_per_read
        if max_samples > max_allowed:
            max_samples = max_allowed
            logger.info(f"Limiting read to {max_allowed} samples (config limit)")

        try:
            samples = await self.dds_manager.read_samples(topic_name, max_samples)

            logger.info(f"Agent '{agent_name}' read {len(samples)} samples from '{topic_name}'")

            return {
                "success": True,
                "topic_name": topic_name,
                "samples": samples,
                "count": len(samples)
            }

        except Exception as e:
            logger.error(f"Read failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def _handle_write(self, args: Dict) -> Dict:
        """Handle write tool call."""
        agent_name = args["agent_name"]
        topic_name = args["topic_name"]
        data = args["data"]

        # Check permissions
        if not self.gateway_config.can_agent_write_topic(agent_name, topic_name):
            logger.warning(f"Agent '{agent_name}' denied write access to '{topic_name}'")
            return {
                "success": False,
                "error": f"Agent '{agent_name}' does not have write permission for topic '{topic_name}'"
            }

        try:
            await self.dds_manager.write_sample(topic_name, data)

            logger.info(f"Agent '{agent_name}' wrote to '{topic_name}'")

            return {
                "success": True,
                "topic_name": topic_name,
                "message": "Sample written successfully"
            }

        except Exception as e:
            logger.error(f"Write failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def _handle_unsubscribe(self, args: Dict) -> Dict:
        """Handle unsubscribe tool call."""
        subscription_id = args["subscription_id"]

        try:
            self.dds_manager.unsubscribe(subscription_id)

            logger.info(f"Unsubscribed: {subscription_id}")

            return {
                "success": True,
                "subscription_id": subscription_id,
                "message": "Unsubscribed successfully"
            }

        except Exception as e:
            logger.error(f"Unsubscribe failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def _handle_list_topics(self, args: Dict) -> Dict:
        """Handle list_topics tool call."""
        agent_name = args["agent_name"]

        try:
            # Get topics the agent can access
            read_topics = self.gateway_config.get_agent_read_topics(agent_name)
            write_topics = self.gateway_config.get_agent_write_topics(agent_name)

            return {
                "success": True,
                "agent_name": agent_name,
                "topics": {
                    "readable": read_topics,
                    "writable": write_topics
                }
            }

        except Exception as e:
            logger.error(f"List topics failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def _handle_get_topic_info(self, args: Dict) -> Dict:
        """Handle get_topic_info tool call."""
        topic_name = args["topic_name"]

        try:
            # Get type definition for the topic
            type_def = self.types_config.get_type_definition(topic_name)

            if not type_def:
                return {
                    "success": False,
                    "error": f"Topic '{topic_name}' not found"
                }

            return {
                "success": True,
                "topic_name": topic_name,
                "type_definition": type_def
            }

        except Exception as e:
            logger.error(f"Get topic info failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def start(self) -> None:
        """Start the gateway."""
        try:
            # Load configuration
            logger.info("Loading configuration...")
            self.gateway_config, self.types_config = load_configuration()

            # Set log level from config
            log_level = getattr(logging, self.gateway_config.log_level, logging.INFO)
            logging.getLogger().setLevel(log_level)

            # Initialize DDS Manager
            logger.info("Initializing DDS Manager...")
            self.dds_manager = DDSManager(self.gateway_config, self.types_config)
            self.dds_manager.start()

            logger.info(f"Gateway started on domain {self.gateway_config.domain_id}")
            logger.info(f"Security: {'Enabled' if self.gateway_config.security_enabled else 'Disabled'}")
            logger.info(f"Configured agents: {', '.join(self.gateway_config.get_all_agents())}")

        except ConfigurationError as e:
            logger.error(f"Configuration error: {e}")
            raise
        except DDSManagerError as e:
            logger.error(f"DDS Manager error: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to start gateway: {e}", exc_info=True)
            raise

    async def stop(self) -> None:
        """Stop the gateway."""
        logger.info("Stopping gateway...")

        if self.dds_manager:
            self.dds_manager.stop()

        logger.info("Gateway stopped")

    async def run(self) -> None:
        """Run the gateway server."""
        await self.start()

        try:
            # Run MCP server using stdio transport
            async with stdio_server() as (read_stream, write_stream):
                await self.server.run(
                    read_stream,
                    write_stream,
                    self.server.create_initialization_options()
                )
        finally:
            await self.stop()


async def main():
    """Main entry point."""
    logger.info("="* 50)
    logger.info("MCP-DDS Gateway Starting...")
    logger.info("="* 50)

    gateway = MCPDDSGateway()

    try:
        await gateway.run()
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
