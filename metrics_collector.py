"""Prometheus metrics collector for MCP-DDS Gateway."""
import logging
import time
from typing import Dict, Optional
from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    Info,
    generate_latest,
    REGISTRY,
    CollectorRegistry
)
from prometheus_client.exposition import choose_encoder


logger = logging.getLogger(__name__)


class MetricsCollector:
    """Collects and exports Prometheus metrics for the gateway."""

    def __init__(self, registry: Optional[CollectorRegistry] = None):
        """
        Initialize metrics collector.

        Args:
            registry: Optional Prometheus registry (uses default if None)
        """
        self.registry = registry or REGISTRY

        # Request metrics
        self.requests_total = Counter(
            'mcp_requests_total',
            'Total number of MCP requests',
            ['operation', 'agent', 'status'],
            registry=self.registry
        )

        self.request_duration = Histogram(
            'mcp_request_duration_seconds',
            'MCP request duration in seconds',
            ['operation', 'agent'],
            buckets=(0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0),
            registry=self.registry
        )

        # DDS metrics
        self.dds_samples_total = Counter(
            'dds_samples_total',
            'Total number of DDS samples processed',
            ['topic', 'direction'],  # direction: read or write
            registry=self.registry
        )

        self.dds_operation_duration = Histogram(
            'dds_operation_duration_seconds',
            'DDS operation duration in seconds',
            ['operation', 'topic'],
            buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0),
            registry=self.registry
        )

        # Subscription metrics
        self.active_subscriptions = Gauge(
            'active_subscriptions',
            'Number of active topic subscriptions',
            ['topic'],
            registry=self.registry
        )

        self.subscriptions_total = Counter(
            'subscriptions_total',
            'Total number of subscriptions created',
            ['topic', 'agent'],
            registry=self.registry
        )

        # Participant metrics
        self.active_participants = Gauge(
            'active_participants',
            'Number of active DDS participants',
            registry=self.registry
        )

        self.active_agents = Gauge(
            'active_agents',
            'Number of active MCP agents',
            registry=self.registry
        )

        # Rate limiting metrics
        self.rate_limit_exceeded = Counter(
            'rate_limit_exceeded_total',
            'Total number of rate limit violations',
            ['agent', 'limit_type'],  # limit_type: global or agent
            registry=self.registry
        )

        # Error metrics
        self.errors_total = Counter(
            'errors_total',
            'Total number of errors',
            ['operation', 'error_type'],
            registry=self.registry
        )

        # Permission denied metrics
        self.permission_denied = Counter(
            'permission_denied_total',
            'Total number of permission denied events',
            ['agent', 'topic', 'operation'],
            registry=self.registry
        )

        # Gateway info
        self.gateway_info = Info(
            'gateway',
            'Gateway information',
            registry=self.registry
        )

        # Gateway uptime
        self.gateway_start_time = Gauge(
            'gateway_start_time_seconds',
            'Unix timestamp when gateway started',
            registry=self.registry
        )
        self.gateway_start_time.set(time.time())

        logger.info("Metrics collector initialized")

    def record_request(self, operation: str, agent: str, duration: float, status: str) -> None:
        """
        Record an MCP request.

        Args:
            operation: Operation name (subscribe, read, write, etc.)
            agent: Agent name
            duration: Request duration in seconds
            status: Request status (success, error, denied)
        """
        self.requests_total.labels(
            operation=operation,
            agent=agent,
            status=status
        ).inc()

        self.request_duration.labels(
            operation=operation,
            agent=agent
        ).observe(duration)

    def record_dds_sample(self, topic: str, direction: str, count: int = 1) -> None:
        """
        Record DDS samples processed.

        Args:
            topic: Topic name
            direction: 'read' or 'write'
            count: Number of samples
        """
        self.dds_samples_total.labels(
            topic=topic,
            direction=direction
        ).inc(count)

    def record_dds_operation(self, operation: str, topic: str, duration: float) -> None:
        """
        Record a DDS operation.

        Args:
            operation: Operation name (read, write, subscribe)
            topic: Topic name
            duration: Operation duration in seconds
        """
        self.dds_operation_duration.labels(
            operation=operation,
            topic=topic
        ).observe(duration)

    def record_subscription(self, topic: str, agent: str) -> None:
        """
        Record a new subscription.

        Args:
            topic: Topic name
            agent: Agent name
        """
        self.subscriptions_total.labels(
            topic=topic,
            agent=agent
        ).inc()

        # Update active subscriptions gauge
        # This would need to be called with proper increment/decrement
        self.active_subscriptions.labels(topic=topic).inc()

    def record_unsubscription(self, topic: str) -> None:
        """
        Record an unsubscription.

        Args:
            topic: Topic name
        """
        self.active_subscriptions.labels(topic=topic).dec()

    def record_error(self, operation: str, error_type: str) -> None:
        """
        Record an error.

        Args:
            operation: Operation where error occurred
            error_type: Type/class of error
        """
        self.errors_total.labels(
            operation=operation,
            error_type=error_type
        ).inc()

    def record_permission_denied(self, agent: str, topic: str, operation: str) -> None:
        """
        Record a permission denied event.

        Args:
            agent: Agent name
            topic: Topic name
            operation: Operation attempted (read/write)
        """
        self.permission_denied.labels(
            agent=agent,
            topic=topic,
            operation=operation
        ).inc()

    def record_rate_limit_exceeded(self, agent: str, limit_type: str) -> None:
        """
        Record a rate limit violation.

        Args:
            agent: Agent name
            limit_type: 'global' or 'agent'
        """
        self.rate_limit_exceeded.labels(
            agent=agent,
            limit_type=limit_type
        ).inc()

    def set_active_agents(self, count: int) -> None:
        """
        Set number of active agents.

        Args:
            count: Number of active agents
        """
        self.active_agents.set(count)

    def set_active_participants(self, count: int) -> None:
        """
        Set number of active DDS participants.

        Args:
            count: Number of active participants
        """
        self.active_participants.set(count)

    def set_gateway_info(self, info: Dict[str, str]) -> None:
        """
        Set gateway information.

        Args:
            info: Dictionary of gateway information
        """
        self.gateway_info.info(info)

    def get_metrics(self) -> bytes:
        """
        Get metrics in Prometheus exposition format.

        Returns:
            Metrics as bytes
        """
        return generate_latest(self.registry)

    def get_metrics_text(self) -> str:
        """
        Get metrics in Prometheus text format.

        Returns:
            Metrics as string
        """
        return self.get_metrics().decode('utf-8')


class RequestTimer:
    """Context manager for timing requests and recording metrics."""

    def __init__(self, metrics: MetricsCollector, operation: str, agent: str):
        """
        Initialize request timer.

        Args:
            metrics: MetricsCollector instance
            operation: Operation being timed
            agent: Agent name
        """
        self.metrics = metrics
        self.operation = operation
        self.agent = agent
        self.start_time: Optional[float] = None
        self.status = "success"

    def __enter__(self):
        """Start timing."""
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop timing and record metrics."""
        duration = time.time() - self.start_time

        # Set status based on exception
        if exc_type is not None:
            self.status = "error"
            self.metrics.record_error(
                self.operation,
                exc_type.__name__
            )

        # Record request
        self.metrics.record_request(
            self.operation,
            self.agent,
            duration,
            self.status
        )

        return False  # Don't suppress exceptions

    def set_status(self, status: str) -> None:
        """
        Set request status.

        Args:
            status: Status string (success, error, denied)
        """
        self.status = status


class AsyncRequestTimer:
    """Async context manager for timing requests and recording metrics."""

    def __init__(self, metrics: MetricsCollector, operation: str, agent: str):
        """
        Initialize async request timer.

        Args:
            metrics: MetricsCollector instance
            operation: Operation being timed
            agent: Agent name
        """
        self.metrics = metrics
        self.operation = operation
        self.agent = agent
        self.start_time: Optional[float] = None
        self.status = "success"

    async def __aenter__(self):
        """Start timing."""
        self.start_time = time.time()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Stop timing and record metrics."""
        duration = time.time() - self.start_time

        # Set status based on exception
        if exc_type is not None:
            self.status = "error"
            self.metrics.record_error(
                self.operation,
                exc_type.__name__
            )

        # Record request
        self.metrics.record_request(
            self.operation,
            self.agent,
            duration,
            self.status
        )

        return False  # Don't suppress exceptions

    def set_status(self, status: str) -> None:
        """
        Set request status.

        Args:
            status: Status string (success, error, denied)
        """
        self.status = status
