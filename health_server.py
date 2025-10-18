"""Health check and metrics HTTP server for MCP-DDS Gateway."""
import asyncio
import logging
from typing import Optional, Callable
from aiohttp import web
from metrics_collector import MetricsCollector


logger = logging.getLogger(__name__)


class HealthServer:
    """HTTP server for health checks and metrics endpoints."""

    def __init__(self, port: int = 9090, metrics_collector: Optional[MetricsCollector] = None):
        """
        Initialize health server.

        Args:
            port: Port to listen on
            metrics_collector: Metrics collector instance
        """
        self.port = port
        self.metrics_collector = metrics_collector
        self.app = web.Application()
        self.runner: Optional[web.AppRunner] = None
        self.site: Optional[web.TCPSite] = None

        # Health check callbacks
        self.liveness_check: Optional[Callable] = None
        self.readiness_check: Optional[Callable] = None

        # Setup routes
        self._setup_routes()

        logger.info(f"Health server configured on port {port}")

    def _setup_routes(self) -> None:
        """Setup HTTP routes."""
        self.app.router.add_get('/health', self._handle_health)
        self.app.router.add_get('/ready', self._handle_ready)
        self.app.router.add_get('/metrics', self._handle_metrics)
        self.app.router.add_get('/info', self._handle_info)

    async def _handle_health(self, request: web.Request) -> web.Response:
        """
        Handle /health endpoint (liveness probe).

        Returns:
            200 if server is alive, 503 if not
        """
        try:
            # Check liveness
            if self.liveness_check:
                is_alive = await self.liveness_check() if asyncio.iscoroutinefunction(
                    self.liveness_check
                ) else self.liveness_check()

                if not is_alive:
                    return web.json_response(
                        {"status": "unhealthy", "message": "Liveness check failed"},
                        status=503
                    )

            return web.json_response({
                "status": "healthy",
                "message": "Gateway is alive"
            })

        except Exception as e:
            logger.error(f"Health check error: {e}")
            return web.json_response(
                {"status": "unhealthy", "error": str(e)},
                status=503
            )

    async def _handle_ready(self, request: web.Request) -> web.Response:
        """
        Handle /ready endpoint (readiness probe).

        Returns:
            200 if server is ready, 503 if not
        """
        try:
            # Check readiness
            if self.readiness_check:
                is_ready = await self.readiness_check() if asyncio.iscoroutinefunction(
                    self.readiness_check
                ) else self.readiness_check()

                if not is_ready:
                    return web.json_response(
                        {"status": "not_ready", "message": "Readiness check failed"},
                        status=503
                    )

            return web.json_response({
                "status": "ready",
                "message": "Gateway is ready to serve requests"
            })

        except Exception as e:
            logger.error(f"Readiness check error: {e}")
            return web.json_response(
                {"status": "not_ready", "error": str(e)},
                status=503
            )

    async def _handle_metrics(self, request: web.Request) -> web.Response:
        """
        Handle /metrics endpoint (Prometheus metrics).

        Returns:
            Prometheus-formatted metrics
        """
        try:
            if not self.metrics_collector:
                return web.Response(
                    text="# Metrics collector not configured\n",
                    content_type="text/plain"
                )

            metrics_text = self.metrics_collector.get_metrics_text()

            return web.Response(
                text=metrics_text,
                content_type="text/plain; version=0.0.4"
            )

        except Exception as e:
            logger.error(f"Metrics endpoint error: {e}")
            return web.Response(
                text=f"# Error: {e}\n",
                content_type="text/plain",
                status=500
            )

    async def _handle_info(self, request: web.Request) -> web.Response:
        """
        Handle /info endpoint (gateway information).

        Returns:
            Gateway information as JSON
        """
        try:
            info = {
                "service": "mcp-dds-gateway",
                "version": "1.0.0",
                "endpoints": {
                    "health": "/health",
                    "ready": "/ready",
                    "metrics": "/metrics",
                    "info": "/info"
                }
            }

            return web.json_response(info)

        except Exception as e:
            logger.error(f"Info endpoint error: {e}")
            return web.json_response(
                {"error": str(e)},
                status=500
            )

    async def start(self) -> None:
        """Start the health server."""
        try:
            self.runner = web.AppRunner(self.app)
            await self.runner.setup()

            self.site = web.TCPSite(
                self.runner,
                '0.0.0.0',
                self.port
            )
            await self.site.start()

            logger.info(f"Health server started on http://0.0.0.0:{self.port}")

        except Exception as e:
            logger.error(f"Failed to start health server: {e}")
            raise

    async def stop(self) -> None:
        """Stop the health server."""
        try:
            if self.site:
                await self.site.stop()

            if self.runner:
                await self.runner.cleanup()

            logger.info("Health server stopped")

        except Exception as e:
            logger.error(f"Error stopping health server: {e}")

    def set_liveness_check(self, callback: Callable) -> None:
        """
        Set liveness check callback.

        Args:
            callback: Function that returns True if alive, False otherwise
        """
        self.liveness_check = callback

    def set_readiness_check(self, callback: Callable) -> None:
        """
        Set readiness check callback.

        Args:
            callback: Function that returns True if ready, False otherwise
        """
        self.readiness_check = callback


async def example_usage():
    """Example of using the health server."""
    from metrics_collector import MetricsCollector

    # Create metrics collector
    metrics = MetricsCollector()

    # Create health server
    server = HealthServer(port=9090, metrics_collector=metrics)

    # Set health check callbacks
    server.set_liveness_check(lambda: True)
    server.set_readiness_check(lambda: True)

    # Start server
    await server.start()

    # Simulate some metrics
    metrics.record_request("subscribe", "test_agent", 0.05, "success")
    metrics.record_request("read", "test_agent", 0.02, "success")
    metrics.record_dds_sample("SensorData", "read", 10)

    print("Health server running on http://localhost:9090")
    print("Try:")
    print("  curl http://localhost:9090/health")
    print("  curl http://localhost:9090/ready")
    print("  curl http://localhost:9090/metrics")
    print("  curl http://localhost:9090/info")

    # Keep running
    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        pass

    # Stop server
    await server.stop()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(example_usage())
