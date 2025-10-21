#!/usr/bin/env python3
"""
DDS Chatbot Agent

A simple AI agent that listens for chat prompts on the ChatPrompt DDS topic
and responds with generated responses on the ChatResponse topic.

This agent demonstrates how to build an interactive chatbot using DDS for
data transport and the MCP-DDS Gateway for agent communication.

The agent uses Ollama for LLM-based responses with fallback to rule-based responses.
"""
import asyncio
import json
import logging
import sys
import uuid
import os
import requests
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('dds_chatbot_agent.log')
    ]
)
logger = logging.getLogger(__name__)


class SimpleChatbot:
    """Simple rule-based chatbot for demo purposes."""

    def __init__(self):
        """Initialize the chatbot with basic responses."""
        self.responses = {
            "hello": "Hello! I'm a DDS-powered chatbot. How can I help you?",
            "hi": "Hi there! What can I do for you?",
            "how are you": "I'm doing great! Thanks for asking. How are you?",
            "what is dds": "DDS (Data Distribution Service) is a middleware for real-time data communication.",
            "what is mcp": "MCP (Model Context Protocol) enables AI agents to interact with external systems.",
            "help": "I can answer questions about DDS, MCP, and this chatbot demo. Try asking me something!",
            "bye": "Goodbye! Thanks for chatting with me.",
            "exit": "Goodbye! Thanks for chatting with me.",
        }

    def generate_response(self, prompt: str) -> str:
        """
        Generate a response to a user prompt.

        Args:
            prompt: User's input text

        Returns:
            Generated response text
        """
        prompt_lower = prompt.lower().strip()

        # Check for exact matches
        if prompt_lower in self.responses:
            return self.responses[prompt_lower]

        # Check for partial matches
        for key, response in self.responses.items():
            if key in prompt_lower:
                return response

        # Default response
        return (
            f"That's an interesting question: '{prompt}'. "
            "I'm a simple demo chatbot, so I have limited knowledge. "
            "Try asking me about DDS, MCP, or say 'help' for more options!"
        )


class OllamaChatbot:
    """LLM-based chatbot using Ollama for local inference."""

    def __init__(self, base_url: str = "http://localhost:11434", model: str = "mistral"):
        """
        Initialize Ollama chatbot.

        Args:
            base_url: Ollama server URL
            model: Model to use (mistral, llama2, neural-chat, etc.)
        """
        self.base_url = base_url
        self.model = model
        self.fallback_chatbot = SimpleChatbot()
        self.available = False

        # Check if Ollama is available
        self._check_availability()

    def _check_availability(self) -> bool:
        """Check if Ollama server is available."""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=2)
            if response.status_code == 200:
                self.available = True
                logger.info(f"Ollama server available at {self.base_url}")
                return True
        except Exception as e:
            logger.warning(f"Ollama not available: {e}. Using fallback chatbot.")
            self.available = False
            return False

    def generate_response(self, prompt: str) -> str:
        """
        Generate a response using Ollama or fallback to SimpleChatbot.

        Args:
            prompt: User's input text

        Returns:
            Generated response text
        """
        if not self.available:
            return self.fallback_chatbot.generate_response(prompt)

        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "temperature": 0.7,
                },
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                return result.get("response", "").strip()
            else:
                logger.warning(f"Ollama error: {response.status_code}")
                return self.fallback_chatbot.generate_response(prompt)

        except requests.exceptions.Timeout:
            logger.warning("Ollama request timeout, using fallback")
            return self.fallback_chatbot.generate_response(prompt)
        except Exception as e:
            logger.warning(f"Ollama error: {e}, using fallback")
            return self.fallback_chatbot.generate_response(prompt)


class DDSChatbotAgent:
    """DDS-based chatbot agent using MCP-DDS Gateway."""

    def __init__(self, agent_name: str = "chatbot_agent", use_llm: bool = True):
        """
        Initialize the chatbot agent.

        Args:
            agent_name: Name of the agent in the DDS system
            use_llm: Whether to use LLM (Ollama) or fallback to simple chatbot
        """
        self.agent_name = agent_name
        self.session_id = str(uuid.uuid4())
        self.running = False

        # Initialize chatbot
        if use_llm:
            ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
            ollama_model = os.getenv("OLLAMA_MODEL", "mistral")
            self.chatbot = OllamaChatbot(base_url=ollama_url, model=ollama_model)
            logger.info(f"Using Ollama LLM (model: {ollama_model})")
        else:
            self.chatbot = SimpleChatbot()
            logger.info("Using SimpleChatbot (rule-based)")

        logger.info(f"Initialized DDS Chatbot Agent: {agent_name}")
        logger.info(f"Session ID: {self.session_id}")
    
    async def process_prompt(self, prompt_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a chat prompt and generate a response.
        
        Args:
            prompt_data: Dictionary containing prompt information
            
        Returns:
            Dictionary containing response information
        """
        prompt_id = prompt_data.get("prompt_id", str(uuid.uuid4()))
        user_id = prompt_data.get("user_id", "unknown_user")
        prompt_text = prompt_data.get("prompt_text", "")
        timestamp = prompt_data.get("timestamp", int(datetime.now().timestamp() * 1000))
        
        logger.info(f"Processing prompt from {user_id}: {prompt_text[:50]}...")
        
        # Generate response
        start_time = datetime.now()
        response_text = self.chatbot.generate_response(prompt_text)
        processing_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
        
        # Create response
        response_data = {
            "response_id": str(uuid.uuid4()),
            "prompt_id": prompt_id,
            "user_id": user_id,
            "response_text": response_text,
            "timestamp": int(datetime.now().timestamp() * 1000),
            "session_id": self.session_id,
            "processing_time_ms": processing_time_ms
        }
        
        logger.info(f"Generated response for {user_id} in {processing_time_ms}ms")
        
        return response_data
    
    async def run(self):
        """Run the chatbot agent (placeholder for DDS integration)."""
        self.running = True
        logger.info("Chatbot agent started")
        
        try:
            while self.running:
                # In a real implementation, this would:
                # 1. Listen for ChatPrompt messages on DDS
                # 2. Process each prompt
                # 3. Write ChatResponse messages to DDS
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("Chatbot agent interrupted")
        finally:
            self.running = False
            logger.info("Chatbot agent stopped")
    
    def stop(self):
        """Stop the chatbot agent."""
        self.running = False


async def main():
    """Main entry point for the chatbot agent."""
    agent = DDSChatbotAgent()
    
    try:
        await agent.run()
    except Exception as e:
        logger.error(f"Error running chatbot agent: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

