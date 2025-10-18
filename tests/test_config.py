"""Tests for configuration management."""
import pytest
from pathlib import Path
from config_manager import GatewayConfig, TypesConfig, ConfigurationError, load_configuration


def test_gateway_config_loads_successfully():
    """Test that gateway configuration loads without errors."""
    config = GatewayConfig("config/gateway_config.json")
    assert config.domain_id >= 0
    assert config.gateway_name == "mcp-dds-gateway"


def test_gateway_config_domain_id():
    """Test domain ID accessor."""
    config = GatewayConfig("config/gateway_config.json")
    assert isinstance(config.domain_id, int)
    assert config.domain_id == 0


def test_gateway_config_security_settings():
    """Test security configuration accessors."""
    config = GatewayConfig("config/gateway_config.json")
    assert isinstance(config.security_enabled, bool)
    assert isinstance(config.certs_base_path, Path)


def test_gateway_config_agent_permissions():
    """Test agent permission checks."""
    config = GatewayConfig("config/gateway_config.json")

    # Test monitoring_agent read permissions
    assert config.can_agent_read_topic("monitoring_agent", "SensorData")
    assert config.can_agent_read_topic("monitoring_agent", "SystemHealth")

    # Test monitoring_agent cannot write
    assert not config.can_agent_write_topic("monitoring_agent", "CommandTopic")

    # Test control_agent write permissions
    assert config.can_agent_write_topic("control_agent", "CommandTopic")
    assert config.can_agent_read_topic("control_agent", "SensorData")


def test_gateway_config_get_all_agents():
    """Test getting all configured agents."""
    config = GatewayConfig("config/gateway_config.json")
    agents = config.get_all_agents()

    assert "monitoring_agent" in agents
    assert "control_agent" in agents
    assert "query_agent" in agents


def test_gateway_config_get_all_topics():
    """Test getting all topics from configuration."""
    config = GatewayConfig("config/gateway_config.json")
    topics = config.get_all_topics()

    assert "SensorData" in topics
    assert "SystemHealth" in topics
    assert "CommandTopic" in topics
    assert "StatusTopic" in topics


def test_gateway_config_rate_limiting():
    """Test rate limiting configuration."""
    config = GatewayConfig("config/gateway_config.json")

    assert isinstance(config.rate_limiting_enabled, bool)
    assert config.requests_per_minute > 0
    assert config.per_agent_limit > 0


def test_gateway_config_metrics():
    """Test metrics configuration."""
    config = GatewayConfig("config/gateway_config.json")

    assert isinstance(config.metrics_enabled, bool)
    assert config.metrics_port > 0
    assert config.log_level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


def test_types_config_loads_successfully():
    """Test that types configuration loads without errors."""
    types = TypesConfig("config/types.xml")
    assert types.types is not None


def test_types_config_get_type_definition():
    """Test retrieving type definitions."""
    types = TypesConfig("config/types.xml")

    sensor_data = types.get_type_definition("SensorData")
    assert sensor_data is not None
    assert sensor_data["@name"] == "SensorData"

    system_health = types.get_type_definition("SystemHealth")
    assert system_health is not None
    assert system_health["@name"] == "SystemHealth"


def test_types_config_get_all_type_names():
    """Test getting all type names."""
    types = TypesConfig("config/types.xml")
    type_names = types.get_all_type_names()

    assert "SensorData" in type_names
    assert "SystemHealth" in type_names
    assert "CommandTopic" in type_names
    assert "StatusTopic" in type_names
    assert "AlertTopic" in type_names


def test_types_config_validate_topic_types():
    """Test topic type validation."""
    types = TypesConfig("config/types.xml")

    # Valid topics
    valid_topics = {"SensorData", "SystemHealth", "CommandTopic"}
    assert types.validate_topic_types(valid_topics)

    # Invalid topics should raise error
    invalid_topics = {"SensorData", "NonexistentTopic"}
    with pytest.raises(ConfigurationError):
        types.validate_topic_types(invalid_topics)


def test_load_configuration_integration():
    """Test loading and cross-validating all configurations."""
    gateway_config, types_config = load_configuration()

    # Verify configs are loaded
    assert gateway_config is not None
    assert types_config is not None

    # Verify cross-validation passed
    all_topics = gateway_config.get_all_topics()
    assert len(all_topics) > 0

    # All topics should have type definitions
    for topic in all_topics:
        type_def = types_config.get_type_definition(topic)
        assert type_def is not None, f"Topic '{topic}' missing type definition"


def test_gateway_config_invalid_file():
    """Test handling of invalid configuration file."""
    with pytest.raises(ConfigurationError):
        GatewayConfig("nonexistent.json")


def test_types_config_invalid_file():
    """Test handling of invalid types file."""
    with pytest.raises(ConfigurationError):
        TypesConfig("nonexistent.xml")


def test_gateway_config_qos_profile():
    """Test DDS QoS profile retrieval."""
    config = GatewayConfig("config/gateway_config.json")
    qos = config.get_dds_qos_profile()

    assert "reliability" in qos
    assert "durability" in qos
    assert "history_kind" in qos


def test_agent_read_write_topics():
    """Test getting agent-specific topic lists."""
    config = GatewayConfig("config/gateway_config.json")

    # Monitoring agent should have read topics but no write topics
    monitoring_read = config.get_agent_read_topics("monitoring_agent")
    monitoring_write = config.get_agent_write_topics("monitoring_agent")

    assert len(monitoring_read) > 0
    assert len(monitoring_write) == 0

    # Control agent should have both read and write topics
    control_read = config.get_agent_read_topics("control_agent")
    control_write = config.get_agent_write_topics("control_agent")

    assert len(control_read) > 0
    assert len(control_write) > 0
