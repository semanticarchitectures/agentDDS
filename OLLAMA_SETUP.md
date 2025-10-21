# Using Ollama with DDS Chatbot Agent

This guide explains how to set up and use Ollama with the DDS Chatbot Agent for more interesting, LLM-powered responses.

## What is Ollama?

Ollama is a tool for running large language models locally on your machine. It's perfect for:
- Running LLMs without cloud dependencies
- Privacy (all data stays on your machine)
- No API keys required
- Fast inference on modern hardware

## Installation

### macOS

```bash
# Download and install Ollama
# Visit https://ollama.ai and download the macOS version
# Or use Homebrew:
brew install ollama
```

### Linux

```bash
# Download and run the installer
curl -fsSL https://ollama.ai/install.sh | sh
```

### Windows

```bash
# Download from https://ollama.ai/download/windows
# Or use Windows Package Manager:
winget install ollama
```

## Starting Ollama

### Option 1: Run as a Service (Recommended)

```bash
# macOS
brew services start ollama

# Linux
systemctl start ollama

# Windows
# Ollama runs automatically after installation
```

### Option 2: Run Manually

```bash
ollama serve
```

This will start the Ollama server on `http://localhost:11434`

## Downloading Models

Once Ollama is running, download a model:

```bash
# Download Mistral (recommended, ~4GB)
ollama pull mistral

# Or download other models:
ollama pull llama2          # Meta's LLaMA 2 (~4GB)
ollama pull neural-chat     # Intel's Neural Chat (~4GB)
ollama pull orca-mini       # Orca Mini (~2GB, faster)
ollama pull tinyllama       # Tiny LLaMA (~1GB, very fast)
```

## Using with DDS Chatbot Agent

### Default Configuration

The agent automatically detects Ollama and uses it if available:

```bash
# Run the demo with LLM support
python demo_chatbot.py
```

The agent will:
1. Try to connect to Ollama at `http://localhost:11434`
2. Use the `mistral` model by default
3. Fall back to rule-based responses if Ollama is unavailable

### Custom Configuration

Set environment variables to customize:

```bash
# Use a different Ollama server
export OLLAMA_URL="http://192.168.1.100:11434"

# Use a different model
export OLLAMA_MODEL="llama2"

# Run the agent
python demo_chatbot.py
```

### Supported Models

| Model | Size | Speed | Quality | Command |
|-------|------|-------|---------|---------|
| mistral | 4GB | Fast | Good | `ollama pull mistral` |
| llama2 | 4GB | Medium | Excellent | `ollama pull llama2` |
| neural-chat | 4GB | Fast | Good | `ollama pull neural-chat` |
| orca-mini | 2GB | Very Fast | Good | `ollama pull orca-mini` |
| tinyllama | 1GB | Fastest | Fair | `ollama pull tinyllama` |

## Example Chat Session with Ollama

```
👤 You: what is dds
🤖 Agent: DDS (Data Distribution Service) is a middleware for real-time data 
communication. It provides a publish-subscribe model for distributed systems to 
exchange data efficiently and reliably. DDS is commonly used in robotics, 
autonomous vehicles, and real-time control systems.
   (Processing time: 2500ms)

👤 You: how does it compare to kafka
🤖 Agent: DDS and Kafka are both messaging systems but serve different purposes:

DDS:
- Real-time, low-latency communication
- Peer-to-peer architecture
- Better for embedded systems and robotics
- Deterministic behavior

Kafka:
- High-throughput, distributed streaming
- Broker-based architecture
- Better for data pipelines and analytics
- Eventual consistency

DDS is better for real-time systems, while Kafka excels at data streaming.
   (Processing time: 3200ms)

👤 You: exit
```

## Troubleshooting

### Issue: "Ollama not available"

**Solution:** Make sure Ollama is running:

```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# If not running, start it:
ollama serve
```

### Issue: Slow Responses

**Solution:** Use a smaller model:

```bash
# Download a faster model
ollama pull orca-mini

# Set it as default
export OLLAMA_MODEL="orca-mini"
python demo_chatbot.py
```

### Issue: Out of Memory

**Solution:** Use a smaller model or increase swap:

```bash
# Use the smallest model
ollama pull tinyllama
export OLLAMA_MODEL="tinyllama"
```

### Issue: Connection Refused

**Solution:** Ollama might be running on a different port:

```bash
# Check what port Ollama is using
lsof -i :11434

# If using a different port, set it:
export OLLAMA_URL="http://localhost:8000"
```

## Performance Tips

### 1. Use GPU Acceleration

Ollama automatically uses GPU if available:
- NVIDIA: CUDA support (automatic)
- Apple Silicon: Metal support (automatic)
- AMD: ROCm support (requires setup)

### 2. Choose the Right Model

- **Fast responses:** Use `orca-mini` or `tinyllama`
- **Better quality:** Use `mistral` or `llama2`
- **Balanced:** Use `neural-chat`

### 3. Adjust Temperature

Lower temperature = more consistent responses:

```python
# In dds_chatbot_agent.py, modify the OllamaChatbot class:
response = requests.post(
    f"{self.base_url}/api/generate",
    json={
        "model": self.model,
        "prompt": prompt,
        "stream": False,
        "temperature": 0.3,  # Lower = more consistent
    },
    timeout=30
)
```

## Monitoring Ollama

### Check Running Models

```bash
curl http://localhost:11434/api/tags
```

### View Model Details

```bash
ollama show mistral
```

### Stop a Model

```bash
# Models are automatically unloaded after 5 minutes of inactivity
# To manually unload:
curl -X DELETE http://localhost:11434/api/generate
```

## Advanced Configuration

### Custom System Prompt

Modify the agent to use a custom system prompt:

```python
# In OllamaChatbot.generate_response():
response = requests.post(
    f"{self.base_url}/api/generate",
    json={
        "model": self.model,
        "prompt": f"You are a helpful DDS expert. {prompt}",
        "stream": False,
        "temperature": 0.7,
    },
    timeout=30
)
```

### Streaming Responses

For real-time streaming:

```python
response = requests.post(
    f"{self.base_url}/api/generate",
    json={
        "model": self.model,
        "prompt": prompt,
        "stream": True,  # Enable streaming
    },
    stream=True,
    timeout=30
)

for line in response.iter_lines():
    if line:
        data = json.loads(line)
        print(data.get("response", ""), end="", flush=True)
```

## Fallback Behavior

If Ollama is unavailable, the agent automatically falls back to rule-based responses:

```
Ollama not available → SimpleChatbot (rule-based)
```

This ensures the demo always works, even without Ollama installed.

## Next Steps

1. Install Ollama from https://ollama.ai
2. Start Ollama: `ollama serve`
3. Download a model: `ollama pull mistral`
4. Run the demo: `python demo_chatbot.py`
5. Chat with the LLM-powered agent!

## Resources

- [Ollama Official Website](https://ollama.ai)
- [Ollama GitHub](https://github.com/jmorganca/ollama)
- [Available Models](https://ollama.ai/library)
- [API Documentation](https://github.com/jmorganca/ollama/blob/main/docs/api.md)

## License

MIT License - See LICENSE file for details

