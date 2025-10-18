# Production Architecture Guide

This guide covers deploying and operating MCP-DDS Gateway in production environments.

## Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│                   Load Balancer                      │
└──────────────┬──────────────────────────────────────┘
               │
       ┌───────┴────────┐
       │                │
┌──────▼─────┐   ┌─────▼──────┐
│  Gateway   │   │  Gateway   │  (Multiple Replicas)
│  Instance  │   │  Instance  │
└──────┬─────┘   └─────┬──────┘
       │                │
       └───────┬────────┘
               │
       ┌───────▼────────┐
       │   DDS Domain   │
       │  Data Mesh     │
       └────────────────┘
```

## High Availability Setup

### Kubernetes Deployment (Recommended)

#### 1. Create Namespace

```bash
kubectl create namespace ai-agents
```

#### 2. Create ConfigMap

```bash
kubectl create configmap gateway-config \
  --from-file=config/gateway_config.json \
  -n ai-agents
```

#### 3. Create Secrets for Certificates

```bash
kubectl create secret generic gateway-certs \
  --from-file=certs/ \
  -n ai-agents
```

#### 4. Deploy

```bash
kubectl apply -f k8s/deployment.yaml
```

#### 5. Scale

```bash
kubectl scale deployment mcp-dds-gateway --replicas=5 -n ai-agents
```

### Horizontal Pod Autoscaling

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: mcp-dds-gateway-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: mcp-dds-gateway
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

## Performance Tuning

### System-Level Optimizations

#### Linux Kernel Parameters

Add to `/etc/sysctl.conf`:

```bash
# Increase network buffer sizes
net.core.rmem_max = 134217728
net.core.wmem_max = 134217728
net.ipv4.tcp_rmem = 4096 87380 67108864
net.ipv4.tcp_wmem = 4096 65536 67108864

# Increase connection tracking
net.netfilter.nf_conntrack_max = 1000000

# Optimize for low latency
net.ipv4.tcp_low_latency = 1
```

Apply changes:

```bash
sudo sysctl -p
```

### DDS QoS Tuning

For high-throughput scenarios, update `config/gateway_config.json`:

```json
{
  "dds_qos": {
    "reliability": "RELIABLE",
    "durability": "TRANSIENT_LOCAL",
    "history_kind": "KEEP_ALL",
    "resource_limits": {
      "max_samples": 1000,
      "max_instances": 100
    }
  }
}
```

For low-latency scenarios:

```json
{
  "dds_qos": {
    "reliability": "BEST_EFFORT",
    "durability": "VOLATILE",
    "history_kind": "KEEP_LAST",
    "history_depth": 1
  }
}
```

## Monitoring and Observability

### Prometheus Metrics

Key metrics to monitor:

- `mcp_request_duration_seconds` (P95, P99) - Should be < 100ms
- `rate_limit_exceeded_total` - Should be minimal
- `errors_total` - Should be near zero
- `active_subscriptions` - Track subscription growth

### Alerting Rules

Create `monitoring/alerts.yml`:

```yaml
groups:
  - name: gateway_alerts
    rules:
      - alert: HighErrorRate
        expr: rate(errors_total[5m]) > 0.05
        annotations:
          summary: "High error rate detected"

      - alert: HighLatency
        expr: histogram_quantile(0.95, rate(mcp_request_duration_seconds_bucket[5m])) > 1.0
        annotations:
          summary: "P95 latency exceeds 1 second"
```

## Security Best Practices

### Certificate Rotation

Rotate certificates every 90 days:

```bash
./scripts/rotate_certs.sh --agent monitoring_agent
```

### Network Security

- Use TLS for all external connections
- Implement firewall rules to restrict DDS discovery
- Use network segmentation for sensitive topics

### Access Control

- Review and update topic allowlists regularly
- Monitor `permission_denied_total` metrics
- Enable audit logging

## Backup and Disaster Recovery

### Configuration Backup

```bash
# Backup certificates
tar -czf certs-backup-$(date +%Y%m%d).tar.gz certs/

# Backup configuration
cp config/gateway_config.json config/gateway_config.json.bak
```

### Recovery Procedure

1. Restore certificates from backup
2. Restore configuration
3. Restart gateway instances
4. Verify health checks pass

## Capacity Planning

### Resource Requirements per Gateway Instance

| Concurrent Agents | CPU | Memory | Network |
|-------------------|-----|--------|---------|
| 50 | 500m | 1GB | 100Mbps |
| 100 | 1000m | 2GB | 200Mbps |
| 200 | 2000m | 4GB | 500Mbps |

### Scaling Guidelines

- Horizontal scaling preferred over vertical
- Add replicas when average CPU > 70%
- Monitor memory for leak detection
- Use connection pooling for database access

## Troubleshooting

### High Latency

1. Check DDS QoS settings
2. Review network configuration
3. Check for CPU throttling
4. Examine rate limiter settings

### Memory Leaks

1. Enable memory profiling
2. Check subscription cleanup
3. Review DDS sample retention policies

### Connection Issues

1. Verify DDS discovery configuration
2. Check firewall rules
3. Validate certificates haven't expired

## References

- [RTI Connext DDS Performance](https://community.rti.com/static/documentation/connext-dds/current/doc/manuals/connext_dds/html_files/RTI_ConnextDDS_CoreLibraries_UsersManual/index.htm#UsersManual/Performance.htm)
- [DDS Security Specification](https://www.omg.org/spec/DDS-SECURITY/)
- [Kubernetes Best Practices](https://kubernetes.io/docs/concepts/configuration/overview/)
