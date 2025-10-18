# MCP-DDS Gateway Quick Start Guide

This guide will get you up and running with the MCP-DDS Gateway in 5 minutes.

## Prerequisites

Before you begin, ensure you have:

- Python 3.8 or higher
- RTI Connext DDS 7.x+ ([Download here](https://www.rti.com/downloads))
- Valid RTI license
- OpenSSL

## Installation Steps

### 1. Clone the Repository

```bash
git clone https://github.com/your-org/mcp-dds-gateway.git
cd mcp-dds-gateway
```

### 2. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 3. Set RTI Environment Variables

```bash
export NDDSHOME=/path/to/rti_connext_dds-7.x.x
export RTI_LICENSE_FILE=/path/to/rti_license.dat
```

Add these to your `~/.bashrc` or `~/.zshrc` for persistence.

### 4. Generate Security Certificates

```bash
chmod +x scripts/secdds_setup.sh
./scripts/secdds_setup.sh
```

This will generate:
- Certificate Authority (CA) certificates
- Identity certificates for gateway and agents
- Permissions documents
- Governance policies

### 5. Start the Gateway

```bash
python mcp_gateway.py
```

You should see output indicating the gateway has started successfully:

```
2025-01-18 10:00:00 - INFO - Gateway started on domain 0
2025-01-18 10:00:00 - INFO - Security: Enabled
2025-01-18 10:00:00 - INFO - Configured agents: monitoring_agent, control_agent, query_agent
```

## Verify Installation

### Test Health Endpoints

In a new terminal:

```bash
# Check liveness
curl http://localhost:9090/health

# Check readiness
curl http://localhost:9090/ready

# Check metrics
curl http://localhost:9090/metrics
```

### Run Example Agent

```bash
python agent_client.py
```

Select option 3 (Query Agent Example) to test reading data.

## Next Steps

### Configure Your Own Agents

Edit `config/gateway_config.json` to add your agents:

```json
{
  "topic_allowlist": {
    "your_agent": {
      "read": ["YourTopic"],
      "write": []
    }
  }
}
```

### Define Your DDS Types

Edit `config/types.xml` to add your data structures:

```xml
<struct name="YourTopic">
  <member name="field1" type="string" key="true"/>
  <member name="field2" type="int32"/>
</struct>
```

### Run Benchmarks

```bash
python benchmark.py --quick
```

### Deploy with Docker

```bash
docker-compose up -d
```

Access Grafana dashboards at http://localhost:3000 (admin/admin)

## Troubleshooting

### RTI License Not Found

```bash
export RTI_LICENSE_FILE=/path/to/rti_license.dat
```

### Certificate Errors

Regenerate certificates:

```bash
./scripts/secdds_setup.sh
```

### Permission Denied

Check that your agent name matches the configuration and has appropriate permissions in `config/gateway_config.json`.

## Support

- Documentation: [project_readme.md](../project_readme.md)
- GitHub Issues: https://github.com/your-org/mcp-dds-gateway/issues
- RTI Community: https://community.rti.com
