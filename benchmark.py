#!/usr/bin/env python3
"""
Benchmark suite for MCP-DDS Gateway

Tests performance characteristics including:
- Request latency (P50, P95, P99)
- Throughput (requests/second)
- Concurrent agent handling
- DDS operations (read/write)
"""
import asyncio
import time
import statistics
import logging
from typing import List, Dict
from dataclasses import dataclass
from datetime import datetime

from agent_client import DDSAgentClient, DDSClientError


logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)


@dataclass
class BenchmarkResult:
    """Result of a benchmark test."""
    test_name: str
    duration: float
    operations: int
    throughput: float
    latencies: List[float]
    p50_latency: float
    p95_latency: float
    p99_latency: float
    errors: int


class Benchmark:
    """Benchmark suite for MCP-DDS Gateway."""

    def __init__(self, agent_name: str = "monitoring_agent"):
        """
        Initialize benchmark.

        Args:
            agent_name: Agent name to use for testing
        """
        self.agent_name = agent_name
        self.results: List[BenchmarkResult] = []

    async def run_all(self, quick: bool = False) -> None:
        """
        Run all benchmarks.

        Args:
            quick: If True, run shorter versions of tests
        """
        print("=" * 70)
        print("MCP-DDS Gateway Benchmark Suite")
        print("=" * 70)
        print(f"Agent: {self.agent_name}")
        print(f"Mode: {'Quick' if quick else 'Full'}")
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70)
        print()

        # Run benchmarks
        await self.benchmark_subscribe_latency(iterations=100 if quick else 1000)
        await self.benchmark_read_latency(iterations=100 if quick else 1000)
        await self.benchmark_write_latency(iterations=100 if quick else 1000)
        await self.benchmark_read_throughput(duration=5 if quick else 30)
        await self.benchmark_write_throughput(duration=5 if quick else 30)
        await self.benchmark_concurrent_agents(agents=5 if quick else 20)

        # Print summary
        self._print_summary()

    async def benchmark_subscribe_latency(self, iterations: int = 1000) -> BenchmarkResult:
        """
        Benchmark subscription operation latency.

        Args:
            iterations: Number of subscribe operations to perform

        Returns:
            BenchmarkResult
        """
        print(f"Running subscribe latency benchmark ({iterations} iterations)...")

        latencies = []
        errors = 0
        start_time = time.time()

        async with DDSAgentClient(self.agent_name) as client:
            for i in range(iterations):
                try:
                    op_start = time.time()
                    sub_id = await client.subscribe("SensorData")
                    op_end = time.time()

                    latencies.append(op_end - op_start)

                    # Unsubscribe to clean up
                    await client.unsubscribe_by_id(sub_id)

                except Exception as e:
                    errors += 1
                    logger.error(f"Subscribe error: {e}")

        end_time = time.time()
        duration = end_time - start_time

        result = self._create_result(
            "Subscribe Latency",
            duration,
            iterations,
            latencies,
            errors
        )

        self.results.append(result)
        self._print_result(result)
        return result

    async def benchmark_read_latency(self, iterations: int = 1000) -> BenchmarkResult:
        """
        Benchmark read operation latency.

        Args:
            iterations: Number of read operations to perform

        Returns:
            BenchmarkResult
        """
        print(f"Running read latency benchmark ({iterations} iterations)...")

        latencies = []
        errors = 0
        start_time = time.time()

        async with DDSAgentClient(self.agent_name) as client:
            for i in range(iterations):
                try:
                    op_start = time.time()
                    await client.read("SensorData", max_samples=10)
                    op_end = time.time()

                    latencies.append(op_end - op_start)

                except Exception as e:
                    errors += 1
                    logger.error(f"Read error: {e}")

        end_time = time.time()
        duration = end_time - start_time

        result = self._create_result(
            "Read Latency",
            duration,
            iterations,
            latencies,
            errors
        )

        self.results.append(result)
        self._print_result(result)
        return result

    async def benchmark_write_latency(self, iterations: int = 1000) -> BenchmarkResult:
        """
        Benchmark write operation latency.

        Args:
            iterations: Number of write operations to perform

        Returns:
            BenchmarkResult
        """
        print(f"Running write latency benchmark ({iterations} iterations)...")

        latencies = []
        errors = 0
        start_time = time.time()

        # Note: This requires an agent with write permissions
        agent_name = "control_agent"

        try:
            async with DDSAgentClient(agent_name) as client:
                for i in range(iterations):
                    try:
                        sample = {
                            "command_id": f"bench_{i}",
                            "command_type": "test",
                            "target": "benchmark",
                            "priority": 1,
                            "parameters": "{}",
                            "issued_by": agent_name,
                            "timestamp": int(time.time() * 1000),
                            "expiry_timestamp": int(time.time() * 1000) + 60000
                        }

                        op_start = time.time()
                        await client.write("CommandTopic", sample)
                        op_end = time.time()

                        latencies.append(op_end - op_start)

                    except Exception as e:
                        errors += 1
                        logger.error(f"Write error: {e}")

        except DDSClientError:
            print("  ⚠ Skipping write benchmark (requires control_agent permissions)")
            return BenchmarkResult(
                "Write Latency", 0, 0, 0, [], 0, 0, 0, 0
            )

        end_time = time.time()
        duration = end_time - start_time

        result = self._create_result(
            "Write Latency",
            duration,
            iterations,
            latencies,
            errors
        )

        self.results.append(result)
        self._print_result(result)
        return result

    async def benchmark_read_throughput(self, duration: int = 30) -> BenchmarkResult:
        """
        Benchmark read throughput (operations per second).

        Args:
            duration: Test duration in seconds

        Returns:
            BenchmarkResult
        """
        print(f"Running read throughput benchmark ({duration}s)...")

        latencies = []
        errors = 0
        operations = 0
        start_time = time.time()
        end_time = start_time + duration

        async with DDSAgentClient(self.agent_name) as client:
            while time.time() < end_time:
                try:
                    op_start = time.time()
                    await client.read("SensorData", max_samples=100)
                    op_end = time.time()

                    latencies.append(op_end - op_start)
                    operations += 1

                except Exception as e:
                    errors += 1
                    logger.error(f"Read error: {e}")

        actual_duration = time.time() - start_time

        result = self._create_result(
            "Read Throughput",
            actual_duration,
            operations,
            latencies,
            errors
        )

        self.results.append(result)
        self._print_result(result)
        return result

    async def benchmark_write_throughput(self, duration: int = 30) -> BenchmarkResult:
        """
        Benchmark write throughput (operations per second).

        Args:
            duration: Test duration in seconds

        Returns:
            BenchmarkResult
        """
        print(f"Running write throughput benchmark ({duration}s)...")

        latencies = []
        errors = 0
        operations = 0
        start_time = time.time()
        end_time = start_time + duration

        agent_name = "control_agent"

        try:
            async with DDSAgentClient(agent_name) as client:
                while time.time() < end_time:
                    try:
                        sample = {
                            "command_id": f"bench_{operations}",
                            "command_type": "test",
                            "target": "benchmark",
                            "priority": 1,
                            "parameters": "{}",
                            "issued_by": agent_name,
                            "timestamp": int(time.time() * 1000),
                            "expiry_timestamp": int(time.time() * 1000) + 60000
                        }

                        op_start = time.time()
                        await client.write("CommandTopic", sample)
                        op_end = time.time()

                        latencies.append(op_end - op_start)
                        operations += 1

                    except Exception as e:
                        errors += 1
                        logger.error(f"Write error: {e}")

        except DDSClientError:
            print("  ⚠ Skipping write throughput (requires control_agent permissions)")
            return BenchmarkResult(
                "Write Throughput", 0, 0, 0, [], 0, 0, 0, 0
            )

        actual_duration = time.time() - start_time

        result = self._create_result(
            "Write Throughput",
            actual_duration,
            operations,
            latencies,
            errors
        )

        self.results.append(result)
        self._print_result(result)
        return result

    async def benchmark_concurrent_agents(self, agents: int = 20) -> BenchmarkResult:
        """
        Benchmark concurrent agent handling.

        Args:
            agents: Number of concurrent agents to simulate

        Returns:
            BenchmarkResult
        """
        print(f"Running concurrent agents benchmark ({agents} agents)...")

        async def agent_workload(agent_id: int) -> tuple:
            """Workload for a single agent."""
            latencies = []
            errors = 0

            try:
                async with DDSAgentClient(f"{self.agent_name}_{agent_id}") as client:
                    for _ in range(10):
                        try:
                            op_start = time.time()
                            await client.read("SensorData", max_samples=10)
                            op_end = time.time()
                            latencies.append(op_end - op_start)
                        except Exception as e:
                            errors += 1

            except Exception:
                # Agent might not be configured
                errors += 1

            return latencies, errors

        start_time = time.time()

        # Run all agents concurrently
        tasks = [agent_workload(i) for i in range(agents)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        end_time = time.time()
        duration = end_time - start_time

        # Aggregate results
        all_latencies = []
        total_errors = 0

        for r in results:
            if isinstance(r, Exception):
                total_errors += 1
                continue
            latencies, errors = r
            all_latencies.extend(latencies)
            total_errors += errors

        result = self._create_result(
            "Concurrent Agents",
            duration,
            len(all_latencies),
            all_latencies,
            total_errors
        )

        self.results.append(result)
        self._print_result(result)
        return result

    def _create_result(self, test_name: str, duration: float, operations: int,
                      latencies: List[float], errors: int) -> BenchmarkResult:
        """Create a BenchmarkResult from raw data."""
        if not latencies:
            return BenchmarkResult(
                test_name, duration, operations, 0, [], 0, 0, 0, errors
            )

        throughput = operations / duration if duration > 0 else 0

        sorted_latencies = sorted(latencies)
        p50 = statistics.median(sorted_latencies)
        p95 = sorted_latencies[int(len(sorted_latencies) * 0.95)]
        p99 = sorted_latencies[int(len(sorted_latencies) * 0.99)]

        return BenchmarkResult(
            test_name=test_name,
            duration=duration,
            operations=operations,
            throughput=throughput,
            latencies=latencies,
            p50_latency=p50,
            p95_latency=p95,
            p99_latency=p99,
            errors=errors
        )

    def _print_result(self, result: BenchmarkResult) -> None:
        """Print a single benchmark result."""
        print(f"\n  Results:")
        print(f"    Duration:    {result.duration:.2f}s")
        print(f"    Operations:  {result.operations}")
        print(f"    Throughput:  {result.throughput:.2f} ops/sec")
        print(f"    P50 Latency: {result.p50_latency * 1000:.2f}ms")
        print(f"    P95 Latency: {result.p95_latency * 1000:.2f}ms")
        print(f"    P99 Latency: {result.p99_latency * 1000:.2f}ms")
        print(f"    Errors:      {result.errors}")
        print()

    def _print_summary(self) -> None:
        """Print benchmark summary."""
        print("=" * 70)
        print("BENCHMARK SUMMARY")
        print("=" * 70)
        print()

        for result in self.results:
            if result.operations == 0:
                continue

            print(f"{result.test_name}:")
            print(f"  Throughput:  {result.throughput:.2f} ops/sec")
            print(f"  P50 Latency: {result.p50_latency * 1000:.2f}ms")
            print(f"  P95 Latency: {result.p95_latency * 1000:.2f}ms")
            print(f"  P99 Latency: {result.p99_latency * 1000:.2f}ms")
            print()

        print("=" * 70)


async def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="MCP-DDS Gateway Benchmark")
    parser.add_argument("--quick", action="store_true", help="Run quick benchmarks")
    parser.add_argument("--test", choices=["subscribe", "read", "write", "all"],
                       default="all", help="Test to run")
    parser.add_argument("--agent", default="monitoring_agent", help="Agent name to use")

    args = parser.parse_args()

    benchmark = Benchmark(agent_name=args.agent)

    if args.test == "all":
        await benchmark.run_all(quick=args.quick)
    elif args.test == "subscribe":
        await benchmark.benchmark_subscribe_latency(100 if args.quick else 1000)
    elif args.test == "read":
        await benchmark.benchmark_read_latency(100 if args.quick else 1000)
    elif args.test == "write":
        await benchmark.benchmark_write_latency(100 if args.quick else 1000)


if __name__ == "__main__":
    asyncio.run(main())
