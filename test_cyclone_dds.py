#!/usr/bin/env python3
"""
Test script for Cyclone DDS implementation.

This script demonstrates basic DDS operations without requiring the full gateway.
"""
import asyncio
import logging
import sys
import time

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

try:
    from cyclonedds.domain import DomainParticipant
    from cyclonedds.topic import Topic
    from cyclonedds.pub import DataWriter, Publisher
    from cyclonedds.sub import DataReader, Subscriber
    from cyclonedds.core import Qos, Policy
    from cyclonedds.util import duration
    from dataclasses import dataclass
    from cyclonedds.idl import IdlStruct
    CYCLONE_AVAILABLE = True
except ImportError:
    CYCLONE_AVAILABLE = False
    logger.error("Cyclone DDS not available. Install with: pip install cyclonedds")
    sys.exit(1)


# Define a simple data type
@dataclass
class TestMessage(IdlStruct):
    """Simple test message."""
    message_id: str
    text: str
    timestamp: int
    value: float


async def test_publisher():
    """Test publishing messages."""
    logger.info("Starting publisher test...")

    # Create participant
    participant = DomainParticipant(0)
    logger.info("Created participant on domain 0")

    # Create topic
    topic = Topic(participant, "TestTopic", TestMessage)
    logger.info("Created topic: TestTopic")

    # Create publisher and writer
    publisher = Publisher(participant)
    writer = DataWriter(publisher, topic)
    logger.info("Created data writer")

    # Publish some messages
    for i in range(5):
        msg = TestMessage(
            message_id=f"msg_{i}",
            text=f"Hello from Cyclone DDS! Message #{i}",
            timestamp=int(time.time() * 1000),
            value=i * 10.5
        )

        writer.write(msg)
        logger.info(f"Published: {msg.text}")
        await asyncio.sleep(1)

    logger.info("Publisher test complete")


async def test_subscriber():
    """Test subscribing to messages."""
    logger.info("Starting subscriber test...")

    # Create participant
    participant = DomainParticipant(0)
    logger.info("Created participant on domain 0")

    # Create topic
    topic = Topic(participant, "TestTopic", TestMessage)
    logger.info("Created topic: TestTopic")

    # Create subscriber and reader
    subscriber = Subscriber(participant)
    qos = Qos(Policy.Reliability.Reliable(duration(seconds=10)))
    reader = DataReader(subscriber, topic, qos)
    logger.info("Created data reader")

    # Read messages for 10 seconds
    logger.info("Listening for messages (10 seconds)...")
    start_time = time.time()
    message_count = 0

    while time.time() - start_time < 10:
        # Take samples
        samples = reader.take(10)

        for sample in samples:
            if sample is not None:
                message_count += 1
                logger.info(f"Received #{message_count}: {sample.text} (value={sample.value})")

        await asyncio.sleep(0.1)

    logger.info(f"Subscriber test complete. Received {message_count} messages")


async def test_pub_sub():
    """Test publisher and subscriber together."""
    logger.info("="*70)
    logger.info("Cyclone DDS Pub/Sub Test")
    logger.info("="*70)

    # Run subscriber and publisher concurrently
    subscriber_task = asyncio.create_task(test_subscriber())
    await asyncio.sleep(2)  # Give subscriber time to set up
    publisher_task = asyncio.create_task(test_publisher())

    # Wait for both to complete
    await asyncio.gather(subscriber_task, publisher_task)

    logger.info("="*70)
    logger.info("Test Complete!")
    logger.info("="*70)


async def test_gateway_integration():
    """Test the DDS manager integration."""
    logger.info("="*70)
    logger.info("Testing Gateway Integration with Cyclone DDS")
    logger.info("="*70)

    try:
        from config_manager import load_configuration
        from dds_manager import DDSManager

        # Load configuration
        gateway_config, types_config = load_configuration()
        logger.info("✓ Configuration loaded")

        # Create DDS manager
        dds_manager = DDSManager(gateway_config, types_config)
        logger.info("✓ DDS Manager created")

        # Start DDS manager
        dds_manager.start()
        logger.info("✓ DDS Manager started")

        # Get participant info
        info = dds_manager.get_participant_info()
        logger.info(f"✓ Participant info: {info}")

        # Test creating a topic
        topic = dds_manager.create_topic("SensorData")
        logger.info(f"✓ Topic created: SensorData")

        # Test writing a sample
        sample_data = {
            "sensor_id": "test_sensor_1",
            "sensor_type": "temperature",
            "temperature": 25.5,
            "humidity": 60.0,
            "pressure": 1013.25,
            "location": "test_location",
            "timestamp": int(time.time() * 1000),
            "status": 1
        }

        await dds_manager.write_sample("SensorData", sample_data)
        logger.info("✓ Sample written to SensorData")

        # Test reading samples
        samples = await dds_manager.read_samples("SensorData", max_samples=10)
        logger.info(f"✓ Read {len(samples)} samples from SensorData")

        if samples:
            logger.info(f"  Sample: {samples[0]}")

        # Stop DDS manager
        dds_manager.stop()
        logger.info("✓ DDS Manager stopped")

        logger.info("="*70)
        logger.info("Gateway Integration Test PASSED!")
        logger.info("="*70)

    except Exception as e:
        logger.error(f"Gateway integration test failed: {e}", exc_info=True)
        raise


async def main():
    """Main entry point."""
    if len(sys.argv) > 1:
        test_type = sys.argv[1]
    else:
        print("\nCyclone DDS Test Suite")
        print("=" * 50)
        print("1. Pub/Sub Test (basic)")
        print("2. Gateway Integration Test")
        print("=" * 50)
        choice = input("Select test (1-2): ").strip()

        test_type = "pubsub" if choice == "1" else "gateway"

    try:
        if test_type == "pubsub":
            await test_pub_sub()
        elif test_type == "gateway":
            await test_gateway_integration()
        else:
            print(f"Unknown test type: {test_type}")
            sys.exit(1)

    except KeyboardInterrupt:
        logger.info("\nTest interrupted by user")
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
