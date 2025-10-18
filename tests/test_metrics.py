"""Tests for metrics collector."""
import pytest
from metrics_collector import MetricsCollector


@pytest.fixture
def metrics():
    """Create metrics collector for testing."""
    return MetricsCollector()


def test_metrics_collector_initialization(metrics):
    """Test metrics collector initialization."""
    assert metrics is not None
    assert metrics.registry is not None


def test_record_request(metrics):
    """Test recording a request."""
    metrics.record_request("subscribe", "test_agent", 0.05, "success")

    # Get metrics text
    metrics_text = metrics.get_metrics_text()
    assert "mcp_requests_total" in metrics_text
    assert "test_agent" in metrics_text


def test_record_dds_sample(metrics):
    """Test recording DDS samples."""
    metrics.record_dds_sample("SensorData", "read", 10)

    metrics_text = metrics.get_metrics_text()
    assert "dds_samples_total" in metrics_text
    assert "SensorData" in metrics_text


def test_record_error(metrics):
    """Test recording errors."""
    metrics.record_error("subscribe", "TimeoutError")

    metrics_text = metrics.get_metrics_text()
    assert "errors_total" in metrics_text


def test_record_permission_denied(metrics):
    """Test recording permission denied."""
    metrics.record_permission_denied("test_agent", "SensorData", "read")

    metrics_text = metrics.get_metrics_text()
    assert "permission_denied_total" in metrics_text


def test_set_active_agents(metrics):
    """Test setting active agents gauge."""
    metrics.set_active_agents(5)

    metrics_text = metrics.get_metrics_text()
    assert "active_agents" in metrics_text
