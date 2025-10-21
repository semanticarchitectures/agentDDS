#!/usr/bin/env python3
"""
DDS Chatbot Demo - Complete End-to-End Demo

This script demonstrates a complete chatbot system using DDS for data transport:
1. Starts the MCP-DDS Gateway
2. Starts the Chatbot Agent
3. Provides an interactive chat interface for users

Usage:
    python demo_chatbot.py [--user-id USER_ID] [--mode MODE]
    
    Modes:
        interactive - Run interactive chat (default)
        agent - Run only the chatbot agent
        gateway - Run only the gateway
"""
import asyncio
import logging
import sys
import argparse
from typing import Optional
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ChatbotDemo:
    """Complete chatbot demo orchestrator."""
    
    def __init__(self, user_id: str = "demo_user", mode: str = "interactive"):
        """
        Initialize the demo.
        
        Args:
            user_id: User ID for the chat session
            mode: Demo mode (interactive, agent, gateway)
        """
        self.user_id = user_id
        self.mode = mode
        self.gateway_process = None
        self.agent_process = None
        
        logger.info(f"Initializing Chatbot Demo - Mode: {mode}, User: {user_id}")
    
    async def run_interactive_demo(self) -> None:
        """Run the interactive chat demo."""
        print("\n" + "="*70)
        print("🤖 DDS CHATBOT DEMO - INTERACTIVE MODE")
        print("="*70)
        print("\nThis demo shows how to use DDS for agent communication.")
        print("The chatbot agent listens on the ChatPrompt topic and responds")
        print("on the ChatResponse topic.\n")
        
        # Import and run the chat client
        from chat_client import ChatClient
        
        client = ChatClient(user_id=self.user_id)
        await client.interactive_chat()
    
    async def run_agent_demo(self) -> None:
        """Run the chatbot agent demo."""
        print("\n" + "="*70)
        print("🤖 DDS CHATBOT DEMO - AGENT MODE")
        print("="*70)
        print("\nStarting the chatbot agent...")
        print("The agent will listen for prompts on the ChatPrompt topic.\n")
        
        # Import and run the agent
        from dds_chatbot_agent import DDSChatbotAgent
        
        agent = DDSChatbotAgent()
        
        try:
            await agent.run()
        except KeyboardInterrupt:
            logger.info("Agent interrupted")
            agent.stop()
    
    async def run_gateway_demo(self) -> None:
        """Run the gateway demo."""
        print("\n" + "="*70)
        print("🤖 DDS CHATBOT DEMO - GATEWAY MODE")
        print("="*70)
        print("\nStarting the MCP-DDS Gateway...")
        print("The gateway bridges AI agents to the DDS data mesh.\n")
        
        # Import and run the gateway
        from mcp_gateway import MCPDDSGateway
        
        gateway = MCPDDSGateway()
        
        try:
            await gateway.run()
        except KeyboardInterrupt:
            logger.info("Gateway interrupted")
            await gateway.stop()
    
    async def run_full_demo(self) -> None:
        """Run the full demo with gateway, agent, and client."""
        print("\n" + "="*70)
        print("🤖 DDS CHATBOT DEMO - FULL MODE")
        print("="*70)
        print("\nStarting full demo with gateway, agent, and client...")
        print("This requires RTI Connext DDS to be installed.\n")
        
        # Create tasks for gateway, agent, and client
        gateway_task = asyncio.create_task(self._run_gateway())
        agent_task = asyncio.create_task(self._run_agent())
        
        # Give gateway and agent time to start
        await asyncio.sleep(2)
        
        # Run the interactive client
        try:
            await self.run_interactive_demo()
        finally:
            # Cancel background tasks
            gateway_task.cancel()
            agent_task.cancel()
            
            try:
                await gateway_task
            except asyncio.CancelledError:
                pass
            
            try:
                await agent_task
            except asyncio.CancelledError:
                pass
    
    async def _run_gateway(self) -> None:
        """Run the gateway in the background."""
        try:
            from mcp_gateway import MCPDDSGateway
            gateway = MCPDDSGateway()
            await gateway.run()
        except Exception as e:
            logger.error(f"Gateway error: {e}")
    
    async def _run_agent(self) -> None:
        """Run the agent in the background."""
        try:
            from dds_chatbot_agent import DDSChatbotAgent
            agent = DDSChatbotAgent()
            await agent.run()
        except Exception as e:
            logger.error(f"Agent error: {e}")
    
    async def run(self) -> None:
        """Run the demo based on the selected mode."""
        try:
            if self.mode == "interactive":
                await self.run_interactive_demo()
            elif self.mode == "agent":
                await self.run_agent_demo()
            elif self.mode == "gateway":
                await self.run_gateway_demo()
            elif self.mode == "full":
                await self.run_full_demo()
            else:
                logger.error(f"Unknown mode: {self.mode}")
                sys.exit(1)
        except Exception as e:
            logger.error(f"Demo error: {e}", exc_info=True)
            sys.exit(1)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="DDS Chatbot Demo",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python demo_chatbot.py                    # Run interactive chat
  python demo_chatbot.py --user-id alice    # Chat as alice
  python demo_chatbot.py --mode agent       # Run agent only
  python demo_chatbot.py --mode full        # Run full demo
        """
    )
    
    parser.add_argument(
        "--user-id",
        default="demo_user",
        help="User ID for the chat session (default: demo_user)"
    )
    
    parser.add_argument(
        "--mode",
        choices=["interactive", "agent", "gateway", "full"],
        default="interactive",
        help="Demo mode (default: interactive)"
    )
    
    args = parser.parse_args()
    
    demo = ChatbotDemo(user_id=args.user_id, mode=args.mode)
    asyncio.run(demo.run())


if __name__ == "__main__":
    main()

