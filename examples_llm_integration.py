#!/usr/bin/env python3
"""
LLM Integration Examples for DDS Chatbot

This file shows how to integrate various LLMs with the DDS chatbot agent.
Choose the integration that works best for your use case.
"""
import logging
from typing import Optional
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class LLMChatbot(ABC):
    """Abstract base class for LLM-based chatbots."""
    
    @abstractmethod
    def generate_response(self, prompt: str) -> str:
        """Generate a response to a prompt."""
        pass


# ============================================================================
# OpenAI Integration (GPT-4, GPT-3.5)
# ============================================================================

class OpenAIChatbot(LLMChatbot):
    """OpenAI-based chatbot using GPT-4 or GPT-3.5."""
    
    def __init__(self, api_key: str, model: str = "gpt-4"):
        """
        Initialize OpenAI chatbot.
        
        Args:
            api_key: OpenAI API key
            model: Model to use (gpt-4, gpt-3.5-turbo)
        """
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError("Install openai: pip install openai")
        
        self.client = OpenAI(api_key=api_key)
        self.model = model
        logger.info(f"Initialized OpenAI chatbot with model: {model}")
    
    def generate_response(self, prompt: str) -> str:
        """Generate response using OpenAI API."""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful assistant integrated with a DDS data mesh system."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=500
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            return f"Error generating response: {e}"


# ============================================================================
# Anthropic Claude Integration
# ============================================================================

class ClaudeChatbot(LLMChatbot):
    """Anthropic Claude-based chatbot."""
    
    def __init__(self, api_key: str, model: str = "claude-3-sonnet-20240229"):
        """
        Initialize Claude chatbot.
        
        Args:
            api_key: Anthropic API key
            model: Model to use
        """
        try:
            import anthropic
        except ImportError:
            raise ImportError("Install anthropic: pip install anthropic")
        
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        logger.info(f"Initialized Claude chatbot with model: {model}")
    
    def generate_response(self, prompt: str) -> str:
        """Generate response using Claude API."""
        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            return message.content[0].text
        except Exception as e:
            logger.error(f"Claude API error: {e}")
            return f"Error generating response: {e}"


# ============================================================================
# Ollama Integration (Local LLMs)
# ============================================================================

class OllamaChatbot(LLMChatbot):
    """Ollama-based chatbot for running local LLMs."""
    
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama2"):
        """
        Initialize Ollama chatbot.
        
        Args:
            base_url: Ollama server URL
            model: Model to use (llama2, mistral, neural-chat, etc.)
        """
        try:
            import requests
        except ImportError:
            raise ImportError("Install requests: pip install requests")
        
        self.base_url = base_url
        self.model = model
        self.requests = requests
        logger.info(f"Initialized Ollama chatbot with model: {model}")
    
    def generate_response(self, prompt: str) -> str:
        """Generate response using Ollama."""
        try:
            response = self.requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False
                }
            )
            response.raise_for_status()
            return response.json()["response"]
        except Exception as e:
            logger.error(f"Ollama error: {e}")
            return f"Error generating response: {e}"


# ============================================================================
# Hugging Face Integration
# ============================================================================

class HuggingFaceChatbot(LLMChatbot):
    """Hugging Face-based chatbot."""
    
    def __init__(self, api_key: str, model: str = "meta-llama/Llama-2-7b-chat-hf"):
        """
        Initialize Hugging Face chatbot.
        
        Args:
            api_key: Hugging Face API key
            model: Model ID from Hugging Face Hub
        """
        try:
            from huggingface_hub import InferenceClient
        except ImportError:
            raise ImportError("Install huggingface-hub: pip install huggingface-hub")
        
        self.client = InferenceClient(api_key=api_key)
        self.model = model
        logger.info(f"Initialized Hugging Face chatbot with model: {model}")
    
    def generate_response(self, prompt: str) -> str:
        """Generate response using Hugging Face."""
        try:
            response = self.client.text_generation(
                prompt,
                model=self.model,
                max_new_tokens=500
            )
            return response
        except Exception as e:
            logger.error(f"Hugging Face error: {e}")
            return f"Error generating response: {e}"


# ============================================================================
# LLaMA 2 Integration (via Replicate)
# ============================================================================

class LLaMA2Chatbot(LLMChatbot):
    """LLaMA 2 chatbot via Replicate API."""
    
    def __init__(self, api_token: str):
        """
        Initialize LLaMA 2 chatbot.
        
        Args:
            api_token: Replicate API token
        """
        try:
            import replicate
        except ImportError:
            raise ImportError("Install replicate: pip install replicate")
        
        self.replicate = replicate
        self.replicate.api.token = api_token
        logger.info("Initialized LLaMA 2 chatbot via Replicate")
    
    def generate_response(self, prompt: str) -> str:
        """Generate response using LLaMA 2."""
        try:
            output = self.replicate.run(
                "meta/llama-2-7b-chat:13c3cdee13ee059ab779f0291d29f6338d3b66fb1124200cd5beb9d2a20eeb41",
                input={
                    "prompt": prompt,
                    "max_tokens": 500
                }
            )
            return "".join(output)
        except Exception as e:
            logger.error(f"LLaMA 2 error: {e}")
            return f"Error generating response: {e}"


# ============================================================================
# Usage Examples
# ============================================================================

def example_openai():
    """Example: Using OpenAI GPT-4."""
    import os
    
    api_key = os.getenv("OPENAI_API_KEY")
    chatbot = OpenAIChatbot(api_key=api_key, model="gpt-4")
    
    response = chatbot.generate_response("What is DDS?")
    print(f"Response: {response}")


def example_claude():
    """Example: Using Anthropic Claude."""
    import os
    
    api_key = os.getenv("ANTHROPIC_API_KEY")
    chatbot = ClaudeChatbot(api_key=api_key)
    
    response = chatbot.generate_response("What is DDS?")
    print(f"Response: {response}")


def example_ollama():
    """Example: Using local Ollama."""
    chatbot = OllamaChatbot(model="llama2")
    
    response = chatbot.generate_response("What is DDS?")
    print(f"Response: {response}")


def example_huggingface():
    """Example: Using Hugging Face."""
    import os
    
    api_key = os.getenv("HUGGINGFACE_API_KEY")
    chatbot = HuggingFaceChatbot(api_key=api_key)
    
    response = chatbot.generate_response("What is DDS?")
    print(f"Response: {response}")


# ============================================================================
# Integration with DDS Chatbot Agent
# ============================================================================

def integrate_with_agent(llm_chatbot: LLMChatbot):
    """
    Example: Integrate LLM with DDS chatbot agent.
    
    Usage in dds_chatbot_agent.py:
    
    ```python
    from examples_llm_integration import OpenAIChatbot
    
    class DDSChatbotAgent:
        def __init__(self, agent_name: str = "chatbot_agent"):
            self.agent_name = agent_name
            self.chatbot = OpenAIChatbot(api_key=os.getenv("OPENAI_API_KEY"))
            # ... rest of initialization
    ```
    """
    pass


# ============================================================================
# Configuration Examples
# ============================================================================

INTEGRATION_CONFIGS = {
    "openai": {
        "class": "OpenAIChatbot",
        "env_vars": ["OPENAI_API_KEY"],
        "models": ["gpt-4", "gpt-3.5-turbo"],
        "cost": "Pay per token",
        "latency": "~1-2 seconds"
    },
    "claude": {
        "class": "ClaudeChatbot",
        "env_vars": ["ANTHROPIC_API_KEY"],
        "models": ["claude-3-sonnet-20240229", "claude-3-opus-20240229"],
        "cost": "Pay per token",
        "latency": "~1-2 seconds"
    },
    "ollama": {
        "class": "OllamaChatbot",
        "env_vars": [],
        "models": ["llama2", "mistral", "neural-chat"],
        "cost": "Free (local)",
        "latency": "~100-500ms"
    },
    "huggingface": {
        "class": "HuggingFaceChatbot",
        "env_vars": ["HUGGINGFACE_API_KEY"],
        "models": ["meta-llama/Llama-2-7b-chat-hf"],
        "cost": "Pay per token",
        "latency": "~1-2 seconds"
    },
    "llama2": {
        "class": "LLaMA2Chatbot",
        "env_vars": ["REPLICATE_API_TOKEN"],
        "models": ["llama-2-7b-chat", "llama-2-13b-chat"],
        "cost": "Pay per token",
        "latency": "~2-5 seconds"
    }
}


if __name__ == "__main__":
    print("LLM Integration Examples for DDS Chatbot")
    print("=" * 60)
    print("\nAvailable integrations:")
    for name, config in INTEGRATION_CONFIGS.items():
        print(f"\n{name.upper()}")
        print(f"  Class: {config['class']}")
        print(f"  Models: {', '.join(config['models'])}")
        print(f"  Cost: {config['cost']}")
        print(f"  Latency: {config['latency']}")
    
    print("\n" + "=" * 60)
    print("See examples_llm_integration.py for usage examples")

