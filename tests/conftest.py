"""Pytest configuration and fixtures for MCP-DDS Gateway tests."""
import pytest


@pytest.fixture
def gateway_config():
    """Fixture providing test gateway configuration."""
    return {
        "domain_id": 0,
        "security": {
            "enabled": False,  # Disabled for unit tests
            "certs_base_path": "./certs"
        },
        "topic_allowlist": {
            "test_agent": {
                "read": ["TestTopic"],
                "write": ["TestTopic"]
            }
        },
        "performance": {
            "max_samples_per_read": 100,
            "batch_timeout_ms": 50
        }
    }
