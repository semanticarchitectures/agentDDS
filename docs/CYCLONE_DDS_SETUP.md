# Cyclone DDS Setup Guide

This guide covers setting up the MCP-DDS Gateway with **Eclipse Cyclone DDS** - a free, open-source DDS implementation.

## Why Cyclone DDS?

- ✅ **Free & Open Source** - Apache 2.0 / Eclipse Public License
- ✅ **Production Ready** - Used by ROS 2 (Robot Operating System)
- ✅ **High Performance** - Optimized for low latency
- ✅ **Python Support** - Native Python bindings
- ✅ **DDS Security** - Full DDS Security specification support
- ✅ **No License Required** - Unlike commercial DDS implementations

## Installation

### 1. Install Cyclone DDS Python Package

```bash
# Install Cyclone DDS with Python bindings
pip install cyclonedds

# Optional: Install DDS Security plugin
pip install cyclonedds-security
```

That's it! No additional downloads or license files needed.

### 2. Verify Installation

```bash
python -c "import cyclonedds; print('Cyclone DDS version:', cyclonedds.__version__)"
```

You should see output like: `Cyclone DDS version: 0.10.x`

## Quick Start

### 1. Install Project Dependencies

```bash
cd agentDDS
pip install -r requirements.txt
```

### 2. Test Cyclone DDS

Run the basic test to verify Cyclone DDS is working:

```bash
python test_cyclone_dds.py
```

Select option 1 for a basic pub/sub test or option 2 for gateway integration test.

### 3. Configure Cyclone DDS (Optional)

Set the Cyclone DDS configuration file:

```bash
export CYCLONEDDS_URI=file://$PWD/config/cyclonedds.xml
```

Add this to your `~/.bashrc` or `~/.zshrc` to make it permanent.

### 4. Start the Gateway

```bash
python mcp_gateway.py
```

### 5. Test with Agent Client

```bash
python agent_client.py
```

## Configuration

### Basic Configuration

Cyclone DDS can be configured via XML file (`config/cyclonedds.xml`):

```xml
<CycloneDDS>
  <Domain>
    <Id>0</Id>
    <General>
      <NetworkInterfaceAddress>auto</NetworkInterfaceAddress>
    </General>
  </Domain>
</CycloneDDS>
```

### Environment Variables

```bash
# Set configuration file
export CYCLONEDDS_URI=file:///path/to/cyclonedds.xml

# Or configure inline
export CYCLONEDDS_URI='<CycloneDDS><Domain><Id>0</Id></Domain></CycloneDDS>'

# Enable verbose logging
export CYCLONEDDS_URI='<CycloneDDS><Domain><Tracing><Verbosity>finest</Verbosity></Tracing></Domain></CycloneDDS>'
```

## DDS Security (Optional)

To enable DDS Security with Cyclone DDS:

### 1. Install Security Plugin

```bash
pip install cyclonedds-security
```

### 2. Generate Certificates

The existing SECDDS setup script can be reused:

```bash
./scripts/secdds_setup.sh
```

### 3. Configure Security in cyclonedds.xml

Uncomment the Security section in `config/cyclonedds.xml`:

```xml
<Security>
  <Authentication>
    <Library>dds_security_auth</Library>
    <IdentityCertificate>file:certs/gateway/identity_cert.pem</IdentityCertificate>
    <IdentityCA>file:certs/ca/identity_ca_cert.pem</IdentityCA>
    <PrivateKey>file:certs/gateway/identity_key.pem</PrivateKey>
  </Authentication>

  <AccessControl>
    <Library>dds_security_ac</Library>
    <Governance>file:certs/ca/governance.p7s</Governance>
    <Permissions>file:certs/gateway/permissions.p7s</Permissions>
    <PermissionsCA>file:certs/ca/permissions_ca_cert.pem</PermissionsCA>
  </AccessControl>

  <Cryptographic>
    <Library>dds_security_crypto</Library>
  </Cryptographic>
</Security>
```

### 4. Restart Gateway

```bash
export CYCLONEDDS_URI=file://$PWD/config/cyclonedds.xml
python mcp_gateway.py
```

## Performance Tuning

### For Low Latency

```xml
<Domain>
  <Internal>
    <Watermarks>
      <WhcHigh>100kB</WhcHigh>
    </Watermarks>
  </Internal>
</Domain>
```

### For High Throughput

```xml
<Domain>
  <General>
    <MaxMessageSize>65500B</MaxMessageSize>
  </General>
  <Internal>
    <Watermarks>
      <WhcHigh>10MB</WhcHigh>
    </Watermarks>
  </Internal>
</Domain>
```

### Network Configuration

```xml
<Domain>
  <General>
    <!-- Use specific network interface -->
    <NetworkInterfaceAddress>192.168.1.100</NetworkInterfaceAddress>

    <!-- Or use auto-detection -->
    <NetworkInterfaceAddress>auto</NetworkInterfaceAddress>

    <!-- Enable multicast -->
    <AllowMulticast>true</AllowMulticast>
  </General>
</Domain>
```

## Troubleshooting

### Issue: "cyclonedds module not found"

```bash
pip install cyclonedds
```

### Issue: No data being received

1. Check firewall settings (UDP ports 7400-7500)
2. Verify network interface is correct in config
3. Enable verbose logging:

```bash
export CYCLONEDDS_URI='<CycloneDDS><Domain><Tracing><Verbosity>finest</Verbosity><OutputFile>dds.log</OutputFile></Tracing></Domain></CycloneDDS>'
python mcp_gateway.py
# Check dds.log for details
```

### Issue: High latency

1. Check QoS settings in `config/gateway_config.json`
2. Use `BEST_EFFORT` reliability for lower latency:

```json
{
  "dds_qos": {
    "reliability": "BEST_EFFORT",
    "history_kind": "KEEP_LAST",
    "history_depth": 1
  }
}
```

### Issue: Security not working

1. Verify security plugin is installed:

```bash
pip list | grep cyclonedds
# Should show: cyclonedds-security
```

2. Check certificate paths in cyclonedds.xml
3. Verify certificates are valid:

```bash
openssl x509 -in certs/gateway/identity_cert.pem -noout -text
```

## Switching Between RTI and Cyclone DDS

The gateway supports both implementations. To switch:

### Use Cyclone DDS (default):

```bash
# dds_manager.py already uses Cyclone
python mcp_gateway.py
```

### Use RTI Connext:

```bash
# Copy the RTI version
cp dds_manager_rti.py dds_manager.py

# Set RTI environment
export NDDSHOME=/path/to/rti_connext_dds
export RTI_LICENSE_FILE=/path/to/rti_license.dat

python mcp_gateway.py
```

## Performance Comparison

Based on typical hardware:

| Metric | Cyclone DDS | RTI Connext |
|--------|-------------|-------------|
| Latency (P95) | < 50ms | < 30ms |
| Throughput | 50k+ msg/s | 100k+ msg/s |
| Memory | ~50MB | ~100MB |
| Setup Time | 1 min | 30 min |
| Cost | FREE | License required |

**Verdict**: Cyclone DDS is excellent for most use cases. RTI Connext offers better performance for mission-critical, ultra-low-latency applications.

## Additional Resources

- [Cyclone DDS Documentation](https://cyclonedds.io/docs/cyclonedds/latest/)
- [Cyclone DDS Python API](https://cyclonedds.io/docs/cyclonedds-python/latest/)
- [DDS Security Specification](https://www.omg.org/spec/DDS-SECURITY/)
- [ROS 2 + Cyclone DDS](https://docs.ros.org/en/rolling/Installation/DDS-Implementations/Working-with-Eclipse-CycloneDDS.html)

## Example: Simple Publisher

```python
from cyclonedds.domain import DomainParticipant
from cyclonedds.topic import Topic
from cyclonedds.pub import DataWriter, Publisher
from dataclasses import dataclass
from cyclonedds.idl import IdlStruct

@dataclass
class SensorData(IdlStruct):
    sensor_id: str
    temperature: float
    timestamp: int

# Create participant
participant = DomainParticipant(0)

# Create topic
topic = Topic(participant, "SensorData", SensorData)

# Create writer
publisher = Publisher(participant)
writer = DataWriter(publisher, topic)

# Write data
data = SensorData(sensor_id="sensor_1", temperature=25.5, timestamp=1234567890)
writer.write(data)
```

## Support

- **Issues**: https://github.com/eclipse-cyclonedds/cyclonedds/issues
- **Discussions**: https://github.com/eclipse-cyclonedds/cyclonedds/discussions
- **Documentation**: https://cyclonedds.io/docs/

---

**Ready to use Cyclone DDS with the MCP-DDS Gateway!** 🚀
