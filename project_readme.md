# MCP-DDS Gateway: Secure AI Agent Integration with RTI Connext DDS

[![Build Status](https://github.com/your-org/mcp-dds-gateway/workflows/CI/badge.svg)](https://github.com/your-org/mcp-dds-gateway/actions)
[![codecov](https://codecov.io/gh/your-org/mcp-dds-gateway/branch/main/graph/badge.svg)](https://codecov.io/gh/your-org/mcp-dds-gateway)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Production-ready gateway enabling AI agents to securely access DDS data meshes through the Model Context Protocol (MCP), with enterprise-grade security via DDS Security (SECDDS).

## 🎯 Overview

This project bridges the gap between AI agents and real-time operational systems by providing:

- **🔒 Secure Access**: SECDDS (DDS Security) with certificate-based authentication and fine-grained permissions
- **⚡ High Performance**: Low-latency pub-sub with real-time data streaming
- **🎛️ Topic Control**: Configurable per-agent access to specific DDS topics
- **📊 Production Ready**: Complete monitoring, benchmarking, and deployment infrastructure
- **🔄 Bidirectional**: Agents can both read and write to DDS topics
- **🌐 Standard Protocol**: Built on Model Context Protocol for interoperability

## 📋 Table of Contents

- [Quick Start](#quick-start)
- [Architecture](#architecture)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage Examples](#usage-examples)
- [Security](#security)
- [Performance](#performance)
- [Deployment](#deployment)
- [Monitoring](#monitoring)
- [Development](#development)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)

## 🚀 Quick Start

### Prerequisites

- RTI Connext DDS 7.x+ ([Download here](https://www.rti.com/downloads))
- Python 3.8+
- OpenSSL
- Valid RTI license

### 5-Minute Setup

```bash
# 1. Clone repository
git clone https://github.com/your-org/mcp-dds-gateway.git
cd mcp-dds-gateway

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set RTI environment
export NDDSHOME=/path/to/rti_connext_dds-7.x.x
export RTI_LICENSE_FILE=/path/to/rti_license.dat

# 4. Generate security certificates
chmod +x secdds_setup.sh
./secdds_setup.sh

# 5. Start gateway
python mcp_gateway.py
```

**Test it works:**
```bash
# In another terminal
python agent_client.py
# Select option 3 (Query Agent Example)
```

## 🏗️ Architecture

### System Overview

```
┌─────────────────┐
│   AI Agents     │  Claude, GPT, Custom Agents
└────────┬────────┘
         │ MCP Protocol (JSON-RPC)
         ▼
┌─────────────────┐
│  MCP Gateway    │  Authentication, Rate Limiting, Metrics
│  - Security     │
│  - Validation   │
│  - Monitoring   │
└────────┬────────┘
         │ DDS + SECDDS
         ▼
┌─────────────────┐
│  DDS Data Mesh  │  Real-time Operational Systems
│  - Topics       │  Sensors, Controls, Telemetry
│  - QoS Policies │
│  - Discovery    │
└─────────────────┘
```

### Key Components

| Component | Purpose | Technology |
|-----------|---------|------------|
| **MCP Gateway** | Protocol translation & security | Python, MCP SDK |
| **SECDDS Integration** | Authentication & authorization | RTI Connext Security |
| **Topic Manager** | Subscription lifecycle | RTI Python API |
| **Metrics Collector** | Performance monitoring | Prometheus |
| **Rate Limiter** | Throttling & fairness | In-memory |

## 📦 Installation

### Method 1: Docker (Recommended for Production)

```bash
# Build image
docker build -t mcp-dds-gateway:latest .

# Run with docker-compose
docker-compose up -d
```

### Method 2: Kubernetes

```bash
# Deploy to cluster
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml

# Verify deployment
kubectl get pods -n ai-agents
```

### Method 3: Manual Installation

```bash
# Install system dependencies (Ubuntu/Debian)
sudo apt-get update
sudo apt-get install -y python3.10 python3-pip openssl

# Install Python packages
pip install -r requirements.txt

# Install RTI Connext DDS
# Follow RTI installation guide: https://community.rti.com/
```

## ⚙️ Configuration

### Gateway Configuration (`config/gateway_config.json`)

```json
{
  "domain_id": 0,
  "security": {
    "enabled": true,
    "certs_base_path": "./certs"
  },
  "topic_allowlist": {
    "monitoring_agent": {
      "read": ["SensorData", "SystemHealth"],
      "write": []
    },
    "control_agent": {
      "read": ["SensorData", "StatusTopic"],
      "write": ["CommandTopic"]
    }
  },
  "performance": {
    "max_samples_per_read": 100,
    "batch_timeout_ms": 50
  }
}
```

### DDS Types (`config/types.xml`)

Define your data structures:

```xml
<struct name="SensorData">
  <member name="sensor_id" type="string" key="true"/>
  <member name="temperature" type="float32"/>
  <member name="timestamp" type="int64"/>
</struct>
```

## 💡 Usage Examples

### Example 1: Monitoring Agent (Read-Only)

```python
from agent_client import DDSAgentClient

async def monitor_sensors():
    async with DDSAgentClient("monitoring_agent") as client:
        # Subscribe with callback
        async def on_data(topic, samples):
            for sample in samples:
                print(f"Sensor {sample['sensor_id']}: {sample['temperature']}°C")
        
        await client.subscribe("SensorData", callback=on_data)
        
        # Keep running
        while True:
            await asyncio.sleep(1)
```

### Example 2: Control Agent (Read + Write)

```python
async def control_system():
    async with DDSAgentClient("control_agent") as client:
        # Read sensor data
        samples = await client.read("SensorData", max_samples=10)
        
        # Make decision
        if any(s['temperature'] > 30 for s in samples):
            # Send command
            await client.write("CommandTopic", {
                "command_id": "cmd_001",
                "command_type": "cool",
                "target": "hvac_system",
                "priority": 1
            })
```

### Example 3: Query Agent (One-Time)

```python
async def query_status():
    async with DDSAgentClient("monitoring_agent") as client:
        # Get latest system health
        health = await client.read("SystemHealth", max_samples=5)
        
        # Analyze
        avg_cpu = sum(h['cpu_usage'] for h in health) / len(health)
        print(f"Average CPU: {avg_cpu}%")
```

## 🔐 Security

### Multi-Layer Security Architecture

1. **SECDDS (DDS Security)**
   - X.509 certificate authentication
   - Per-participant permissions
   - Encryption of discovery and data
   - Governance policies

2. **Application Layer**
   - Topic access control lists
   - Rate limiting per agent
   - Input validation
   - Audit logging

3. **Network Layer**
   - TLS for external connections
   - Firewall rules
   - Network segmentation

### Security Best Practices

✅ **DO:**
- Rotate certificates every 90 days
- Use separate certificates per agent
- Enable all SECDDS protections for sensitive topics
- Monitor authentication failures
- Implement rate limiting
- Review audit logs regularly

❌ **DON'T:**
- Share private keys between agents
- Commit certificates to version control
- Disable SECDDS in production
- Grant write access unnecessarily
- Use default/example certificates

### Certificate Management

```bash
# Generate new agent credentials
./secdds_setup.sh  # Edit to add new agent

# Rotate certificates (before expiry)
./scripts/rotate_certs.sh --agent monitoring_agent

# Revoke compromised certificate
./scripts/revoke_cert.sh --agent compromised_agent
```

## 📊 Performance

### Benchmarks (Typical Hardware)

| Metric | Value |
|--------|-------|
| Subscription Latency (P95) | < 50ms |
| Read Latency (P95) | < 30ms |
| Write Throughput | 10,000+ samples/sec |
| Concurrent Agents | 200+ per gateway |
| Memory per Gateway | 1-2 GB |

### Running Benchmarks

```bash
# Quick benchmark (2 minutes)
python benchmark.py --quick

# Full suite (10 minutes)
python benchmark.py

# Specific test
python benchmark.py --test write
```

### Performance Tuning

See [Production Architecture Guide](production_architecture.md) for:
- QoS optimization
- System tuning (Linux)
- Horizontal scaling
- Load balancing

## 🚀 Deployment

### Development

```bash
python mcp_gateway.py
```

### Docker Compose (Small Scale)

```bash
docker-compose up -d
```

### Kubernetes (Production)

```bash
# Deploy
kubectl apply -f k8s/

# Scale
kubectl scale deployment mcp-dds-gateway --replicas=5 -n ai-agents

# Rolling update
kubectl set image deployment/mcp-dds-gateway gateway=mcp-dds-gateway:v1.1
```

### Health Checks

```bash
# Liveness
curl http://gateway:9090/health

# Readiness
curl http://gateway:9090/ready

# Metrics
curl http://gateway:9090/metrics
```

## 📈 Monitoring

### Prometheus Metrics

Key metrics exposed:
- `mcp_requests_total` - Request count by operation/status
- `mcp_request_duration_seconds` - Request latency histogram
- `dds_samples_total` - DDS throughput
- `active_subscriptions` - Current subscriptions
- `active_participants` - DDS participants

### Grafana Dashboard

Import `monitoring/grafana_dashboard.json` for:
- Real-time request rates
- Latency percentiles (P50, P95, P99)
- Error rates
- Active agents
- Topic throughput

### Alerting

Prometheus alerts configured for:
- Gateway down (1 minute)
- High error rate (> 5%)
- High latency (P95 > 1s)
- Authentication failures
- Memory exhaustion

## 🛠️ Development

### Project Structure

```
mcp-dds-gateway/
├── mcp_gateway.py          # Main gateway implementation
├── agent_client.py         # Example client for agents
├── benchmark.py            # Performance testing
├── tests/                  # Test suite
│   ├── test_security.py
│   ├── test_functionality.py
│   └── test_performance.py
├── config/                 # Configuration files
│   ├── gateway_config.json
│   └── types.xml
├── certs/                  # Security certificates
│   ├── ca/
│   ├── monitoring_agent/
│   └── control_agent/
├── scripts/                # Utility scripts
│   ├── secdds_setup.sh
│   ├── rotate_certs.sh
│   └── health_check.sh
├── k8s/                    # Kubernetes manifests
├── monitoring/             # Prometheus/Grafana
└── docs/                   # Documentation
    ├── production_architecture.md
    └── quickstart.md
```

### Running Tests

```bash
# All tests
pytest tests/ -v

# Unit tests only (skip integration)
pytest tests/ -v -m "not integration"

# With coverage
pytest tests/ --cov=. --cov-report=html
```

### Code Quality

```bash
# Format code
black .

# Lint
flake8 .

# Type checking
mypy mcp_gateway.py
```

### Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 🐛 Troubleshooting

### Common Issues

**Issue: "RTI_LICENSE_FILE not found"**
```bash
export RTI_LICENSE_FILE=/path/to/rti_license.dat
```

**Issue: "Authentication failed"**
```bash
# Check certificate validity
openssl x509 -in certs/agent/identity_cert.pem -noout -dates

# Verify CA chain
openssl verify -CAfile certs/ca/identity_ca_cert.pem certs/agent/identity_cert.pem
```

**Issue: "Permission denied for topic"**
```bash
# Verify permissions document
cat certs/agent/permissions.xml

# Check allowlist in config
cat config/gateway_config.json
```

**Issue: "High latency"**
```bash
# Check network
ping gateway-host

# Check DDS discovery
rtiddsping -domainId 0

# Review QoS settings
cat config/types.xml
```

### Debug Mode

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
python mcp_gateway.py
```

### Getting Help

- 📖 [Documentation](./docs/)
- 💬 [GitHub Issues](https://github.com/your-org/mcp-dds-gateway/issues)
- 🌐 [RTI Community](https://community.rti.com)
- 📧 Email: support@your-org.com

## 📄 License

This project is licensed under the MIT License - see [LICENSE](LICENSE) file.

## 🙏 Acknowledgments

- [RTI Connext DDS](https://www.rti.com) - High-performance DDS implementation
- [Anthropic MCP](https://www.anthropic.com) - Model Context Protocol
- [OMG DDS](https://www.omg.org/spec/DDS/) - DDS specification
- [OMG DDS Security](https://www.omg.org/spec/DDS-SECURITY/) - Security specification

## 📮 Contact

- **Project Lead**: Your Name (your.email@example.com)
- **Organization**: Your Organization
- **Website**: https://your-org.com

---

**Ready to connect your AI agents to real-time systems?** Start with our [Quick Start Guide](docs/quickstart.md)!
