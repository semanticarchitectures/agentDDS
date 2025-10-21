"""Pytest configuration and fixtures for MCP-DDS Gateway tests."""
import pytest
from unittest.mock import Mock, patch
from config_manager import GatewayConfig, TypesConfig


@pytest.fixture
def gateway_config():
    """Fixture providing test gateway configuration."""
    # Mock the GatewayConfig to avoid file I/O during tests
    config = Mock(spec=GatewayConfig)
    config.domain_id = 0
    config.security_enabled = False
    config.certs_base_path = "./certs"
    config.gateway_name = "test_gateway"
    config.bind_address = "0.0.0.0"
    config.port = 8080
    config.max_samples_per_read = 100
    config.batch_timeout_ms = 50
    config.get_agent_permissions = Mock(return_value={"read": ["TestTopic"], "write": ["TestTopic"]})
    config.get_all_agents = Mock(return_value=["test_agent"])
    config.get_all_topics = Mock(return_value=["TestTopic"])
    config.get_dds_qos_profile = Mock(return_value={})
    return config
