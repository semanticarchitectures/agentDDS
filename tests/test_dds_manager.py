"""Tests for DDS Manager."""
import pytest
from unittest.mock import Mock, patch, MagicMock
from config_manager import GatewayConfig, TypesConfig
from dds_manager import DDSManager, DDSManagerError


@pytest.fixture
def mock_dds():
    """Mock RTI DDS module."""
    with patch('dds_manager.RTI_AVAILABLE', True):
        with patch('dds_manager.dds') as mock:
            yield mock


@pytest.fixture
def dds_manager(gateway_config, mock_dds):
    """Create DDS manager for testing."""
    types_config = TypesConfig("config/types.xml")
    manager = DDSManager(gateway_config, types_config)
    return manager


def test_dds_manager_initialization(gateway_config, mock_dds):
    """Test DDS manager initialization."""
    types_config = TypesConfig("config/types.xml")
    manager = DDSManager(gateway_config, types_config)

    assert manager.gateway_config == gateway_config
    assert manager.types_config == types_config
    assert not manager.is_running


def test_dds_manager_get_participant_info(dds_manager):
    """Test getting participant information."""
    info = dds_manager.get_participant_info()

    assert isinstance(info, dict)
    assert "domain_id" in info
    assert "security_enabled" in info
