# MCP-DDS Gateway

Production-ready gateway enabling AI agents to securely access DDS data meshes through the Model Context Protocol (MCP).

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Set RTI environment
export NDDSHOME=/path/to/rti_connext_dds-7.x.x
export RTI_LICENSE_FILE=/path/to/rti_license.dat

# Generate security certificates
./scripts/secdds_setup.sh

# Start gateway
python mcp_gateway.py
```

## Documentation

See [project_readme.md](project_readme.md) for complete documentation.

## Project Structure

```
.
├── mcp_gateway.py          # Main gateway implementation
├── agent_client.py         # Client library for AI agents
├── benchmark.py            # Performance testing suite
├── config/                 # Configuration files
├── certs/                  # Security certificates (not in git)
├── scripts/                # Utility scripts
├── tests/                  # Test suite
├── k8s/                    # Kubernetes manifests
├── monitoring/             # Prometheus/Grafana configs
└── docs/                   # Additional documentation
```

## License

MIT License - see LICENSE file for details.
