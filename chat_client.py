#!/usr/bin/env python3
"""
Interactive Chat Client for DDS Chatbot Demo

Allows users to send prompts to the chatbot agent via DDS and receive responses.
This client demonstrates how to interact with a DDS-based agent through the
MCP-DDS Gateway.
"""
import asyncio
import json
import logging
import sys
import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('chat_client.log')
    ]
)
logger = logging.getLogger(__name__)


class ChatClient:
    """Interactive chat client for DDS chatbot."""
    
    def __init__(self, user_id: str = "demo_user"):
        """
        Initialize the chat client.
        
        Args:
            user_id: Unique identifier for the user
        """
        self.user_id = user_id
        self.session_id = str(uuid.uuid4())
        self.prompt_count = 0
        self.response_count = 0
        
        logger.info(f"Chat client initialized for user: {user_id}")
        logger.info(f"Session ID: {self.session_id}")
    
    def create_prompt(self, text: str) -> Dict[str, Any]:
        """
        Create a chat prompt message.
        
        Args:
            text: User's prompt text
            
        Returns:
            Dictionary containing prompt data
        """
        self.prompt_count += 1
        
        prompt_data = {
            "prompt_id": str(uuid.uuid4()),
            "user_id": self.user_id,
            "prompt_text": text,
            "timestamp": int(datetime.now().timestamp() * 1000),
            "session_id": self.session_id
        }
        
        logger.debug(f"Created prompt: {prompt_data['prompt_id']}")
        return prompt_data
    
    def display_response(self, response_data: Dict[str, Any]) -> None:
        """
        Display a response from the chatbot.
        
        Args:
            response_data: Dictionary containing response data
        """
        self.response_count += 1
        
        response_text = response_data.get("response_text", "No response")
        processing_time = response_data.get("processing_time_ms", 0)
        
        print(f"\n🤖 Agent: {response_text}")
        print(f"   (Processing time: {processing_time}ms)\n")
    
    async def send_prompt(self, prompt_text: str) -> Dict[str, Any]:
        """
        Send a prompt to the chatbot and get a response.
        
        In a real implementation, this would:
        1. Write the prompt to the ChatPrompt DDS topic
        2. Wait for a response on the ChatResponse DDS topic
        3. Return the response
        
        Args:
            prompt_text: User's input text
            
        Returns:
            Response data from the chatbot
        """
        prompt_data = self.create_prompt(prompt_text)
        
        logger.info(f"Sending prompt: {prompt_text[:50]}...")
        
        # Simulate sending to DDS and receiving response
        # In real implementation, this would use the DDS manager
        await asyncio.sleep(0.1)  # Simulate network latency
        
        # For demo purposes, we'll simulate a response
        response_data = {
            "response_id": str(uuid.uuid4()),
            "prompt_id": prompt_data["prompt_id"],
            "user_id": self.user_id,
            "response_text": f"Echo: {prompt_text}",
            "timestamp": int(datetime.now().timestamp() * 1000),
            "session_id": self.session_id,
            "processing_time_ms": 50
        }
        
        return response_data
    
    async def interactive_chat(self) -> None:
        """Run interactive chat session."""
        print("\n" + "="*60)
        print("🤖 DDS Chatbot Demo - Interactive Chat")
        print("="*60)
        print(f"User ID: {self.user_id}")
        print(f"Session ID: {self.session_id}")
        print("\nType your messages below. Type 'exit' or 'quit' to end the chat.")
        print("-"*60 + "\n")
        
        while True:
            try:
                # Get user input
                user_input = input("👤 You: ").strip()
                
                if not user_input:
                    continue
                
                # Check for exit commands
                if user_input.lower() in ["exit", "quit", "bye"]:
                    print("\n👋 Goodbye! Thanks for chatting.")
                    break
                
                # Send prompt and get response
                response = await self.send_prompt(user_input)
                self.display_response(response)
                
            except KeyboardInterrupt:
                print("\n\n👋 Chat interrupted. Goodbye!")
                break
            except Exception as e:
                logger.error(f"Error in chat: {e}")
                print(f"❌ Error: {e}")
        
        # Print session summary
        self._print_session_summary()
    
    def _print_session_summary(self) -> None:
        """Print a summary of the chat session."""
        print("\n" + "="*60)
        print("📊 Session Summary")
        print("="*60)
        print(f"User ID: {self.user_id}")
        print(f"Session ID: {self.session_id}")
        print(f"Prompts sent: {self.prompt_count}")
        print(f"Responses received: {self.response_count}")
        print("="*60 + "\n")


async def main():
    """Main entry point for the chat client."""
    # Get user ID from command line or use default
    user_id = sys.argv[1] if len(sys.argv) > 1 else "demo_user"
    
    client = ChatClient(user_id=user_id)
    
    try:
        await client.interactive_chat()
    except Exception as e:
        logger.error(f"Error running chat client: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

