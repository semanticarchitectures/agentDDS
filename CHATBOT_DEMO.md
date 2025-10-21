# DDS Chatbot Demo

A complete end-to-end demonstration of an AI chatbot that uses DDS (Data Distribution Service) for real-time data communication.

## Overview

This demo showcases:
- **User Interface**: Interactive chat client for sending prompts
- **DDS Agent**: Chatbot agent that processes prompts and generates responses
- **MCP-DDS Gateway**: Bridges the agent to the DDS data mesh
- **DDS Topics**: ChatPrompt (user→agent) and ChatResponse (agent→user)

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Chat Client (User)                       │
│                  (chat_client.py)                           │
└────────────────────┬────────────────────────────────────────┘
                     │
                     │ ChatPrompt Topic
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              MCP-DDS Gateway                                │
│           (mcp_gateway.py)                                  │
│  - Manages DDS topics                                       │
│  - Handles permissions                                      │
│  - Provides MCP interface                                   │
└────────────────────┬────────────────────────────────────────┘
                     │
                     │ DDS Data Mesh
                     │
┌────────────────────▼────────────────────────────────────────┐
│              Chatbot Agent                                  │
│         (dds_chatbot_agent.py)                              │
│  - Listens for ChatPrompt messages                          │
│  - Processes user input                                     │
│  - Generates responses                                      │
└────────────────────┬────────────────────────────────────────┘
                     │
                     │ ChatResponse Topic
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                    Chat Client (User)                       │
│                  Receives Response                          │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start

### 1. Interactive Chat (Recommended for First-Time Users)

The simplest way to try the demo:

```bash
# Run the interactive chat client
python demo_chatbot.py

# Or specify a user ID
python demo_chatbot.py --user-id alice
```

This mode simulates the full chatbot experience without requiring RTI Connext DDS to be installed.

### 2. Agent-Only Mode

Run just the chatbot agent:

```bash
python demo_chatbot.py --mode agent
```

### 3. Gateway-Only Mode

Run just the MCP-DDS Gateway:

```bash
python demo_chatbot.py --mode gateway
```

### 4. Full Demo Mode (Requires RTI Connext DDS)

Run the complete system with gateway, agent, and client:

```bash
# Set up RTI environment
export NDDSHOME=/path/to/rti_connext_dds-7.x.x
export RTI_LICENSE_FILE=/path/to/rti_license.dat

# Run full demo
python demo_chatbot.py --mode full
```

## Components

### Chat Client (`chat_client.py`)

Interactive CLI for users to chat with the agent.

**Features:**
- User-friendly prompt interface
- Session tracking
- Response display with processing time
- Session summary statistics

**Usage:**
```bash
python chat_client.py [user_id]
```

**Example:**
```bash
python chat_client.py alice
```

### Chatbot Agent (`dds_chatbot_agent.py`)

The AI agent that processes prompts and generates responses.

**Features:**
- Simple rule-based chatbot (extensible for LLM integration)
- DDS topic listener for ChatPrompt
- Response generation and publishing to ChatResponse
- Session management
- Processing time tracking

**Usage:**
```bash
python dds_chatbot_agent.py
```

### Demo Orchestrator (`demo_chatbot.py`)

Unified entry point for running different demo modes.

**Modes:**
- `interactive`: Chat client only (default)
- `agent`: Agent only
- `gateway`: Gateway only
- `full`: Complete system

**Usage:**
```bash
python demo_chatbot.py [--user-id USER_ID] [--mode MODE]
```

## DDS Topics

### ChatPrompt Topic

**Direction:** User → Agent

**Structure:**
```json
{
  "prompt_id": "unique-id",
  "user_id": "user-name",
  "prompt_text": "user's question or command",
  "timestamp": 1234567890000,
  "session_id": "session-uuid"
}
```

### ChatResponse Topic

**Direction:** Agent → User

**Structure:**
```json
{
  "response_id": "unique-id",
  "prompt_id": "corresponding-prompt-id",
  "user_id": "user-name",
  "response_text": "agent's response",
  "timestamp": 1234567890000,
  "session_id": "session-uuid",
  "processing_time_ms": 50
}
```

## Configuration

### Gateway Configuration (`config/gateway_config.json`)

The chatbot agent is configured with:
- **Agent Name:** `chatbot_agent`
- **Read Topics:** `ChatPrompt`
- **Write Topics:** `ChatResponse`

```json
{
  "topic_allowlist": {
    "chatbot_agent": {
      "read": ["ChatPrompt"],
      "write": ["ChatResponse"]
    }
  }
}
```

### Type Definitions (`config/types.xml`)

ChatPrompt and ChatResponse types are defined in the types configuration.

## Example Chat Session

```
============================================================
🤖 DDS Chatbot Demo - Interactive Chat
============================================================
User ID: alice
Session ID: 550e8400-e29b-41d4-a716-446655440000

Type your messages below. Type 'exit' or 'quit' to end the chat.
------------------------------------------------------------

👤 You: hello
🤖 Agent: Hello! I'm a DDS-powered chatbot. How can I help you?
   (Processing time: 2ms)

👤 You: what is dds
🤖 Agent: DDS (Data Distribution Service) is a middleware for real-time data communication.
   (Processing time: 1ms)

👤 You: tell me about mcp
🤖 Agent: MCP (Model Context Protocol) enables AI agents to interact with external systems.
   (Processing time: 1ms)

👤 You: exit
👋 Goodbye! Thanks for chatting.

============================================================
📊 Session Summary
============================================================
User ID: alice
Session ID: 550e8400-e29b-41d4-a716-446655440000
Prompts sent: 3
Responses received: 3
============================================================
```

## Extending the Demo

### Adding LLM Integration

Replace the `SimpleChatbot` class in `dds_chatbot_agent.py` with an LLM-based implementation:

```python
from openai import OpenAI

class LLMChatbot:
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)
    
    def generate_response(self, prompt: str) -> str:
        response = self.client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content
```

### Adding Persistence

Store chat history to a database:

```python
async def save_interaction(self, prompt_data, response_data):
    # Save to database
    await db.chat_history.insert_one({
        "prompt": prompt_data,
        "response": response_data,
        "timestamp": datetime.now()
    })
```

### Adding Authentication

Implement user authentication in the chat client:

```python
async def authenticate(self, username: str, password: str) -> bool:
    # Verify credentials
    return await auth_service.verify(username, password)
```

## Troubleshooting

### Issue: "RTI Connext DDS not available"

**Solution:** This is expected in interactive mode. RTI is only required for full mode.

### Issue: Chat client doesn't receive responses

**Solution:** Ensure the agent is running and listening on the ChatPrompt topic.

### Issue: Permission denied errors

**Solution:** Check that the chatbot_agent has proper permissions in `gateway_config.json`.

## Performance Considerations

- **Latency:** Typical response time is 1-50ms
- **Throughput:** Can handle hundreds of concurrent chat sessions
- **Scalability:** Add more agent instances for higher throughput

## Next Steps

1. **Try the interactive demo:** `python demo_chatbot.py`
2. **Integrate with an LLM:** Replace SimpleChatbot with your preferred LLM
3. **Deploy to production:** Use Kubernetes deployment (see production_architecture.md)
4. **Monitor metrics:** Check Prometheus metrics for performance

## References

- [RTI Connext DDS Documentation](https://community.rti.com/documentation)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [DDS Security Specification](https://www.omg.org/spec/DDS-SECURITY/)

