# MCP-DDS Gateway

Production-ready gateway enabling AI agents to securely access DDS data meshes through the Model Context Protocol (MCP).

**Now using Eclipse Cyclone DDS** - Free, open-source DDS implementation! 🚀

## Quick Start (1 Minute!)

```bash
# Install dependencies (includes Cyclone DDS)
pip install -r requirements.txt

# Optional: Set Cyclone DDS config
export CYCLONEDDS_URI=file://$PWD/config/cyclonedds.xml

# Optional: Generate security certificates
./scripts/secdds_setup.sh

# Start gateway
python mcp_gateway.py
```

**That's it!** No license files, no external downloads, no complex setup.

### Alternative: Using RTI Connext DDS

If you prefer RTI Connext DDS (commercial):

```bash
# Switch to RTI version
cp dds_manager_rti.py dds_manager.py

# Set RTI environment
export NDDSHOME=/path/to/rti_connext_dds-7.x.x
export RTI_LICENSE_FILE=/path/to/rti_license.dat

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
