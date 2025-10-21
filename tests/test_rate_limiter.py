"""Tests for rate limiter."""
import pytest
import asyncio
from rate_limiter import RateLimiter, RateLimitConfig, RateLimitExceeded, TokenBucket


@pytest.fixture
def rate_limiter():
    """Create rate limiter for testing."""
    config = RateLimitConfig(
        requests_per_minute=60,  # 1 per second
        burst_size=10,
        per_agent_limit=30  # 0.5 per second
    )
    return RateLimiter(config)


@pytest.mark.asyncio
async def test_rate_limiter_allows_requests(rate_limiter):
    """Test that rate limiter allows requests under limit."""
    # Should allow first request
    await rate_limiter.check_rate_limit("test_agent")

    # Check metrics
    metrics = rate_limiter.get_metrics()
    assert metrics["total_requests"] == 1
    assert metrics["total_rejected"] == 0


@pytest.mark.asyncio
async def test_rate_limiter_rejects_over_limit(rate_limiter):
    """Test that rate limiter rejects requests over limit."""
    # Per-agent capacity is burst_size / 2 = 10 / 2 = 5
    # Consume all tokens from per-agent limiter
    for _ in range(5):  # per-agent capacity
        await rate_limiter.check_rate_limit("test_agent")

    # Next request should be rejected
    with pytest.raises(RateLimitExceeded):
        await rate_limiter.check_rate_limit("test_agent")


@pytest.mark.asyncio
async def test_rate_limiter_per_agent_limits(rate_limiter):
    """Test per-agent rate limiting."""
    # Agent 1 consumes their tokens
    for _ in range(5):
        await rate_limiter.check_rate_limit("agent1")

    # Agent 2 should still be able to make requests
    await rate_limiter.check_rate_limit("agent2")


@pytest.mark.asyncio
async def test_rate_limiter_can_be_disabled(rate_limiter):
    """Test disabling rate limiter."""
    rate_limiter.disable()

    # Should allow unlimited requests
    for _ in range(100):
        await rate_limiter.check_rate_limit("test_agent")

    metrics = rate_limiter.get_metrics()
    assert metrics["total_rejected"] == 0


def test_token_bucket_consume():
    """Test token bucket consumption."""
    bucket = TokenBucket(rate=1.0, capacity=10)

    # Should have initial capacity
    assert bucket.tokens == 10

    # Consume some tokens
    assert asyncio.run(bucket.consume(5))
    assert bucket.tokens == 5

    # Try to consume more than available
    assert not asyncio.run(bucket.consume(10))
