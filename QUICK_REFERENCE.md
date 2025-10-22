# MCP-DDS Gateway - Quick Reference Card

## Installation

### Cyclone DDS (Recommended - FREE)
```bash
pip install -r requirements.txt
python mcp_gateway.py
```

### RTI Connext DDS
```bash
cp dds_manager_rti.py dds_manager.py
export NDDSHOME=/path/to/rti
export RTI_LICENSE_FILE=/path/to/license.dat
python mcp_gateway.py
```

## Common Commands

### Start Gateway
```bash
python mcp_gateway.py
```

### Test Installation
```bash
# Test Cyclone DDS
python test_cyclone_dds.py

# Test gateway integration
python test_cyclone_dds.py gateway
```

### Run Example Agent
```bash
python agent_client.py
# Select: 1=Monitoring, 2=Control, 3=Query
```

### Run Benchmarks
```bash
# Quick test (2 min)
python benchmark.py --quick

# Full suite (10 min)
python benchmark.py
```

### Check Health
```bash
curl http://localhost:9090/health
curl http://localhost:9090/ready
curl http://localhost:9090/metrics
```

## Configuration

### Environment Variables
```bash
# Cyclone DDS config
export CYCLONEDDS_URI=file://$PWD/config/cyclonedds.xml

# RTI Connext config
export NDDSHOME=/path/to/rti_connext_dds
export RTI_LICENSE_FILE=/path/to/rti_license.dat
```

### Config Files
- `config/gateway_config.json` - Gateway settings
- `config/types.xml` - DDS data types
- `config/cyclonedds.xml` - Cyclone DDS settings

## Security

### Generate Certificates
```bash
./scripts/secdds_setup.sh
```

### Enable Security (Cyclone)
```bash
# 1. Install security plugin
pip install cyclonedds-security

# 2. Edit config/cyclonedds.xml
# Uncomment <Security> section

# 3. Set config
export CYCLONEDDS_URI=file://$PWD/config/cyclonedds.xml
```

## Agent Client API

### Basic Usage
```python
from agent_client import DDSAgentClient

async with DDSAgentClient("agent_name") as client:
    # Read data
    samples = await client.read("SensorData", max_samples=10)

    # Write data
    await client.write("CommandTopic", {
        "command_id": "cmd_1",
        "command_type": "action",
        ...
    })

    # Subscribe
    sub_id = await client.subscribe("StatusTopic")

    # List topics
    topics = await client.list_topics()
```

## Deployment

### Docker
```bash
docker-compose up -d

# Access Grafana
open http://localhost:3000  # admin/admin
```

### Kubernetes
```bash
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/deployment.yaml

# Scale
kubectl scale deployment mcp-dds-gateway --replicas=5
```

## Monitoring

### Endpoints
- Health: http://localhost:9090/health
- Ready: http://localhost:9090/ready
- Metrics: http://localhost:9090/metrics
- Info: http://localhost:9090/info

### Grafana Dashboards
```bash
# Start monitoring stack
docker-compose up -d grafana prometheus

# Access dashboards
open http://localhost:3000
```

## Testing

### Run Tests
```bash
# All tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=. --cov-report=html

# Specific tests
pytest tests/test_config.py -v
```

### Health Check
```bash
./scripts/health_check.sh
```

## Troubleshooting

### Check Logs
```bash
tail -f mcp_gateway.log
tail -f cyclonedds.log
```

### Enable Debug Logging
```bash
export LOG_LEVEL=DEBUG
python mcp_gateway.py
```

### Network Issues
```bash
# Check DDS discovery
# Cyclone: Set verbosity in cyclonedds.xml
<Tracing><Verbosity>finest</Verbosity></Tracing>

# RTI: Use rtiddsspy
rtiddsspy -domainId 0
```

### Permission Denied
Check agent permissions in `config/gateway_config.json`:
```json
{
  "topic_allowlist": {
    "your_agent": {
      "read": ["Topic1"],
      "write": ["Topic2"]
    }
  }
}
```

## Performance Tuning

### Low Latency
Edit `config/gateway_config.json`:
```json
{
  "dds_qos": {
    "reliability": "BEST_EFFORT",
    "history_kind": "KEEP_LAST",
    "history_depth": 1
  }
}
```

### High Throughput
```json
{
  "performance": {
    "max_samples_per_read": 1000,
    "batch_timeout_ms": 100
  }
}
```

## File Structure

```
agentDDS/
├── mcp_gateway.py          # Main gateway
├── agent_client.py         # Client library
├── dds_manager.py          # DDS manager (Cyclone)
├── dds_manager_rti.py      # RTI version (backup)
├── config/
│   ├── gateway_config.json # Gateway config
│   ├── types.xml           # DDS types
│   └── cyclonedds.xml      # Cyclone config
├── scripts/
│   ├── secdds_setup.sh     # Cert generation
│   └── health_check.sh     # Health check
└── docs/
    ├── CYCLONE_DDS_SETUP.md
    └── quickstart.md
```

## Key Metrics

### Expected Performance
- Subscribe Latency: < 50ms (P95)
- Read Latency: < 30ms (P95)
- Write Throughput: 10,000+ samples/sec
- Concurrent Agents: 200+ per gateway

### Resource Usage
- Memory: 0.5-2 GB per gateway
- CPU: 250m-1000m per gateway
- Network: 100-500 Mbps

## DDS Implementation Comparison

| Feature | Cyclone DDS | RTI Connext |
|---------|-------------|-------------|
| Cost | FREE | License required |
| Setup | 1 min | 30 min |
| Latency (P95) | ~50ms | ~30ms |
| Use When | General use | Ultra-low latency |

## URLs

- **Documentation**: [project_readme.md](project_readme.md)
- **Cyclone Setup**: [docs/CYCLONE_DDS_SETUP.md](docs/CYCLONE_DDS_SETUP.md)
- **Migration Guide**: [CYCLONE_DDS_MIGRATION.md](CYCLONE_DDS_MIGRATION.md)
- **Quick Start**: [docs/quickstart.md](docs/quickstart.md)

## Support

- **GitHub Issues**: https://github.com/your-org/mcp-dds-gateway/issues
- **Cyclone DDS**: https://github.com/eclipse-cyclonedds/cyclonedds
- **RTI Community**: https://community.rti.com

---

**Need help?** Check [docs/](docs/) or run `python mcp_gateway.py --help`
