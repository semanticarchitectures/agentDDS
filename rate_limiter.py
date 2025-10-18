"""Rate limiting for MCP-DDS Gateway."""
import asyncio
import logging
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Dict, Optional
from datetime import datetime, timedelta


logger = logging.getLogger(__name__)


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""
    requests_per_minute: int = 1000
    burst_size: int = 100
    per_agent_limit: int = 500


class RateLimitExceeded(Exception):
    """Raised when rate limit is exceeded."""
    pass


class TokenBucket:
    """Token bucket rate limiter implementation."""

    def __init__(self, rate: float, capacity: int):
        """
        Initialize token bucket.

        Args:
            rate: Tokens added per second
            capacity: Maximum bucket capacity (burst size)
        """
        self.rate = rate  # tokens per second
        self.capacity = capacity
        self.tokens = capacity
        self.last_update = time.time()
        self._lock = asyncio.Lock()

    async def consume(self, tokens: int = 1) -> bool:
        """
        Try to consume tokens from the bucket.

        Args:
            tokens: Number of tokens to consume

        Returns:
            True if tokens were consumed, False if rate limit exceeded
        """
        async with self._lock:
            now = time.time()
            elapsed = now - self.last_update

            # Add tokens based on elapsed time
            self.tokens = min(
                self.capacity,
                self.tokens + elapsed * self.rate
            )
            self.last_update = now

            # Try to consume tokens
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            else:
                return False

    def get_wait_time(self, tokens: int = 1) -> float:
        """
        Get estimated wait time until tokens are available.

        Args:
            tokens: Number of tokens needed

        Returns:
            Wait time in seconds
        """
        if self.tokens >= tokens:
            return 0.0

        tokens_needed = tokens - self.tokens
        return tokens_needed / self.rate


class SlidingWindowCounter:
    """Sliding window rate limiter implementation."""

    def __init__(self, window_size: int, max_requests: int):
        """
        Initialize sliding window counter.

        Args:
            window_size: Window size in seconds
            max_requests: Maximum requests per window
        """
        self.window_size = window_size
        self.max_requests = max_requests
        self.requests: deque = deque()
        self._lock = asyncio.Lock()

    async def is_allowed(self) -> bool:
        """
        Check if a request is allowed.

        Returns:
            True if request is allowed, False otherwise
        """
        async with self._lock:
            now = time.time()
            cutoff = now - self.window_size

            # Remove old requests outside the window
            while self.requests and self.requests[0] < cutoff:
                self.requests.popleft()

            # Check if under limit
            if len(self.requests) < self.max_requests:
                self.requests.append(now)
                return True

            return False

    def get_request_count(self) -> int:
        """Get current request count in window."""
        now = time.time()
        cutoff = now - self.window_size

        # Count requests in current window
        count = 0
        for req_time in self.requests:
            if req_time >= cutoff:
                count += 1

        return count


class RateLimiter:
    """
    Rate limiter for MCP-DDS Gateway.

    Implements both global and per-agent rate limiting using token bucket algorithm.
    """

    def __init__(self, config: RateLimitConfig):
        """
        Initialize rate limiter.

        Args:
            config: Rate limit configuration
        """
        self.config = config
        self.enabled = True

        # Global rate limiter (requests per minute)
        global_rate = config.requests_per_minute / 60.0  # Convert to per-second
        self.global_limiter = TokenBucket(
            rate=global_rate,
            capacity=config.burst_size
        )

        # Per-agent rate limiters
        per_agent_rate = config.per_agent_limit / 60.0  # Convert to per-second
        self.agent_limiters: Dict[str, TokenBucket] = {}
        self.per_agent_rate = per_agent_rate
        self.per_agent_capacity = int(config.burst_size / 2)  # Smaller burst for agents

        # Metrics
        self.total_requests = 0
        self.total_rejected = 0
        self.agent_requests: Dict[str, int] = defaultdict(int)
        self.agent_rejected: Dict[str, int] = defaultdict(int)

        logger.info(
            f"Rate limiter initialized: {config.requests_per_minute} req/min global, "
            f"{config.per_agent_limit} req/min per agent"
        )

    def _get_agent_limiter(self, agent_name: str) -> TokenBucket:
        """Get or create rate limiter for an agent."""
        if agent_name not in self.agent_limiters:
            self.agent_limiters[agent_name] = TokenBucket(
                rate=self.per_agent_rate,
                capacity=self.per_agent_capacity
            )
        return self.agent_limiters[agent_name]

    async def check_rate_limit(self, agent_name: str, tokens: int = 1) -> None:
        """
        Check if request is allowed under rate limits.

        Args:
            agent_name: Name of the requesting agent
            tokens: Number of tokens to consume (default 1)

        Raises:
            RateLimitExceeded: If rate limit is exceeded
        """
        if not self.enabled:
            return

        self.total_requests += 1
        self.agent_requests[agent_name] += 1

        # Check global rate limit
        if not await self.global_limiter.consume(tokens):
            self.total_rejected += 1
            self.agent_rejected[agent_name] += 1

            wait_time = self.global_limiter.get_wait_time(tokens)
            logger.warning(
                f"Global rate limit exceeded for agent '{agent_name}'. "
                f"Retry in {wait_time:.2f}s"
            )
            raise RateLimitExceeded(
                f"Global rate limit exceeded. Retry in {wait_time:.2f} seconds"
            )

        # Check per-agent rate limit
        agent_limiter = self._get_agent_limiter(agent_name)
        if not await agent_limiter.consume(tokens):
            self.total_rejected += 1
            self.agent_rejected[agent_name] += 1

            wait_time = agent_limiter.get_wait_time(tokens)
            logger.warning(
                f"Per-agent rate limit exceeded for '{agent_name}'. "
                f"Retry in {wait_time:.2f}s"
            )
            raise RateLimitExceeded(
                f"Agent rate limit exceeded. Retry in {wait_time:.2f} seconds"
            )

        logger.debug(f"Rate limit check passed for agent '{agent_name}'")

    def disable(self) -> None:
        """Disable rate limiting."""
        self.enabled = False
        logger.info("Rate limiting disabled")

    def enable(self) -> None:
        """Enable rate limiting."""
        self.enabled = True
        logger.info("Rate limiting enabled")

    def get_metrics(self) -> Dict:
        """
        Get rate limiter metrics.

        Returns:
            Dictionary of metrics
        """
        return {
            "enabled": self.enabled,
            "total_requests": self.total_requests,
            "total_rejected": self.total_rejected,
            "rejection_rate": (
                self.total_rejected / self.total_requests
                if self.total_requests > 0 else 0
            ),
            "global_tokens_available": self.global_limiter.tokens,
            "global_capacity": self.global_limiter.capacity,
            "agent_stats": {
                agent: {
                    "requests": self.agent_requests[agent],
                    "rejected": self.agent_rejected[agent],
                    "rejection_rate": (
                        self.agent_rejected[agent] / self.agent_requests[agent]
                        if self.agent_requests[agent] > 0 else 0
                    ),
                    "tokens_available": (
                        self.agent_limiters[agent].tokens
                        if agent in self.agent_limiters else 0
                    )
                }
                for agent in set(list(self.agent_requests.keys()) + list(self.agent_limiters.keys()))
            }
        }

    def reset_metrics(self) -> None:
        """Reset all metrics counters."""
        self.total_requests = 0
        self.total_rejected = 0
        self.agent_requests.clear()
        self.agent_rejected.clear()
        logger.info("Rate limiter metrics reset")

    def get_agent_stats(self, agent_name: str) -> Dict:
        """
        Get statistics for a specific agent.

        Args:
            agent_name: Name of the agent

        Returns:
            Dictionary of agent statistics
        """
        limiter = self.agent_limiters.get(agent_name)

        return {
            "agent_name": agent_name,
            "total_requests": self.agent_requests[agent_name],
            "rejected_requests": self.agent_rejected[agent_name],
            "tokens_available": limiter.tokens if limiter else 0,
            "token_capacity": limiter.capacity if limiter else 0,
            "rate_per_second": self.per_agent_rate
        }


class AdaptiveRateLimiter(RateLimiter):
    """
    Adaptive rate limiter that adjusts limits based on system load.

    Inherits from RateLimiter and adds dynamic adjustment capabilities.
    """

    def __init__(self, config: RateLimitConfig):
        """Initialize adaptive rate limiter."""
        super().__init__(config)
        self.base_config = config
        self.load_threshold = 0.8  # 80% utilization threshold
        self.adjustment_factor = 0.9  # Reduce by 10% when over threshold

    async def adjust_limits(self, system_load: float) -> None:
        """
        Adjust rate limits based on system load.

        Args:
            system_load: Current system load (0.0 to 1.0)
        """
        if system_load > self.load_threshold:
            # Reduce limits
            new_rate = self.global_limiter.rate * self.adjustment_factor
            self.global_limiter.rate = max(1.0, new_rate)  # Minimum 1 req/sec

            logger.info(
                f"Rate limits adjusted down due to high load ({system_load:.2%}). "
                f"New rate: {self.global_limiter.rate * 60:.0f} req/min"
            )
        elif system_load < self.load_threshold * 0.5:
            # Restore original limits if load is low
            original_rate = self.base_config.requests_per_minute / 60.0
            if self.global_limiter.rate < original_rate:
                self.global_limiter.rate = min(original_rate, self.global_limiter.rate * 1.1)

                logger.info(
                    f"Rate limits adjusted up due to low load ({system_load:.2%}). "
                    f"New rate: {self.global_limiter.rate * 60:.0f} req/min"
                )
