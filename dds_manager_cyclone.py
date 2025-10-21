"""DDS Manager for MCP-DDS Gateway using Eclipse Cyclone DDS.

Handles DDS participant creation, topic management, and security integration.
"""
import logging
import json
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
import asyncio
from dataclasses import dataclass, field
from datetime import datetime
import time

try:
    from cyclonedds.domain import DomainParticipant
    from cyclonedds.topic import Topic
    from cyclonedds.pub import DataWriter, Publisher
    from cyclonedds.sub import DataReader, Subscriber
    from cyclonedds.core import Qos, Policy
    from cyclonedds.idl import IdlStruct
    from cyclonedds.util import duration
    from dataclasses import dataclass as idl_dataclass
    CYCLONE_AVAILABLE = True
except ImportError:
    CYCLONE_AVAILABLE = False
    logging.warning("Cyclone DDS not available. Running in mock mode.")

from config_manager import GatewayConfig, TypesConfig


logger = logging.getLogger(__name__)


# ============================================
# IDL Data Type Definitions
# ============================================

if CYCLONE_AVAILABLE:
    @idl_dataclass
    class SensorData(IdlStruct):
        """Sensor data structure."""
        sensor_id: str
        sensor_type: str
        temperature: float
        humidity: float
        pressure: float
        location: str
        timestamp: int
        status: int

    @idl_dataclass
    class SystemHealth(IdlStruct):
        """System health structure."""
        system_id: str
        cpu_usage: float
        memory_usage: float
        disk_usage: float
        network_rx_bytes: int
        network_tx_bytes: int
        uptime_seconds: int
        timestamp: int
        health_status: str

    @idl_dataclass
    class CommandTopic(IdlStruct):
        """Command structure."""
        command_id: str
        command_type: str
        target: str
        priority: int
        parameters: str
        issued_by: str
        timestamp: int
        expiry_timestamp: int

    @idl_dataclass
    class StatusTopic(IdlStruct):
        """Status structure."""
        entity_id: str
        status_code: int
        status_message: str
        timestamp: int
        severity: str

    @idl_dataclass
    class AlertTopic(IdlStruct):
        """Alert structure."""
        alert_id: str
        alert_type: str
        source: str
        severity: int
        message: str
        timestamp: int
        acknowledged: bool

    @idl_dataclass
    class ChatPrompt(IdlStruct):
        """Chat prompt structure."""
        prompt_id: str
        user_id: str
        prompt_text: str
        timestamp: int
        session_id: str

    @idl_dataclass
    class ChatResponse(IdlStruct):
        """Chat response structure."""
        response_id: str
        prompt_id: str
        user_id: str
        response_text: str
        timestamp: int
        session_id: str
        processing_time_ms: int


# Map topic names to IDL types
TYPE_MAP = {
    "SensorData": SensorData if CYCLONE_AVAILABLE else None,
    "SystemHealth": SystemHealth if CYCLONE_AVAILABLE else None,
    "CommandTopic": CommandTopic if CYCLONE_AVAILABLE else None,
    "StatusTopic": StatusTopic if CYCLONE_AVAILABLE else None,
    "AlertTopic": AlertTopic if CYCLONE_AVAILABLE else None,
    "ChatPrompt": ChatPrompt if CYCLONE_AVAILABLE else None,
    "ChatResponse": ChatResponse if CYCLONE_AVAILABLE else None,
}


@dataclass
class SubscriptionHandle:
    """Handle for managing DDS subscriptions."""
    topic_name: str
    data_reader: Any
    callback: Optional[Callable] = None
    active: bool = True


class DDSManagerError(Exception):
    """Raised when DDS operations fail."""
    pass


class CycloneDDSManager:
    """Manages DDS participant, topics, and data readers/writers using Cyclone DDS."""

    def __init__(self, gateway_config: GatewayConfig, types_config: TypesConfig):
        """
        Initialize DDS Manager with Cyclone DDS.

        Args:
            gateway_config: Gateway configuration
            types_config: DDS types configuration
        """
        if not CYCLONE_AVAILABLE:
            raise DDSManagerError("Cyclone DDS is not available. Install with: pip install cyclonedds")

        self.gateway_config = gateway_config
        self.types_config = types_config

        self.participant: Optional[DomainParticipant] = None
        self.publisher: Optional[Publisher] = None
        self.subscriber: Optional[Subscriber] = None

        self.topics: Dict[str, Topic] = {}
        self.data_readers: Dict[str, DataReader] = {}
        self.data_writers: Dict[str, DataWriter] = {}
        self.subscriptions: Dict[str, SubscriptionHandle] = {}

        self._running = False

        logger.info("Cyclone DDS Manager initialized")

    def start(self) -> None:
        """Start the DDS Manager and create participant."""
        try:
            self._create_participant()
            self._create_publisher_subscriber()
            self._running = True
            logger.info("Cyclone DDS Manager started successfully")
        except Exception as e:
            logger.error(f"Failed to start DDS Manager: {e}")
            raise DDSManagerError(f"Failed to start DDS Manager: {e}")

    def stop(self) -> None:
        """Stop the DDS Manager and cleanup resources."""
        self._running = False

        # Close all subscriptions
        for sub_handle in self.subscriptions.values():
            sub_handle.active = False

        # Delete data readers
        for reader in self.data_readers.values():
            if reader:
                del reader

        # Delete data writers
        for writer in self.data_writers.values():
            if writer:
                del writer

        # Delete topics
        for topic in self.topics.values():
            if topic:
                del topic

        # Delete publisher and subscriber
        if self.publisher:
            del self.publisher
        if self.subscriber:
            del self.subscriber

        # Delete participant
        if self.participant:
            del self.participant

        logger.info("Cyclone DDS Manager stopped")

    def _create_participant(self) -> None:
        """Create DDS domain participant."""
        domain_id = self.gateway_config.domain_id

        try:
            # Create QoS for participant
            qos = Qos()

            # Note: Cyclone DDS security configuration is typically done via XML
            # or environment variables rather than programmatically
            if self.gateway_config.security_enabled:
                logger.info("DDS Security: Configure via cyclonedds.xml or environment variables")
                logger.info("See: https://cyclonedds.io/docs/cyclonedds/latest/config/config_file_reference.html")

            # Create participant
            self.participant = DomainParticipant(domain_id, qos)
            logger.info(f"Created DDS participant on domain {domain_id}")

        except Exception as e:
            raise DDSManagerError(f"Failed to create DDS participant: {e}")

    def _create_publisher_subscriber(self) -> None:
        """Create publisher and subscriber."""
        if not self.participant:
            raise DDSManagerError("Participant not created")

        try:
            # Create publisher with default QoS
            self.publisher = Publisher(self.participant)
            logger.info("Created publisher")

            # Create subscriber with default QoS
            self.subscriber = Subscriber(self.participant)
            logger.info("Created subscriber")

        except Exception as e:
            raise DDSManagerError(f"Failed to create publisher/subscriber: {e}")

    def _get_type_for_topic(self, topic_name: str) -> type:
        """
        Get the IDL type class for a topic.

        Args:
            topic_name: Name of the topic

        Returns:
            IDL type class

        Raises:
            DDSManagerError: If type not found
        """
        if topic_name not in TYPE_MAP:
            raise DDSManagerError(f"No type definition found for topic: {topic_name}")

        idl_type = TYPE_MAP[topic_name]
        if idl_type is None:
            raise DDSManagerError(f"Type for topic {topic_name} not available")

        return idl_type

    def create_topic(self, topic_name: str) -> Topic:
        """
        Create or get a DDS topic.

        Args:
            topic_name: Name of the topic

        Returns:
            DDS Topic

        Raises:
            DDSManagerError: If topic creation fails
        """
        if topic_name in self.topics:
            return self.topics[topic_name]

        if not self.participant:
            raise DDSManagerError("Participant not created")

        try:
            # Get the IDL type for this topic
            idl_type = self._get_type_for_topic(topic_name)

            # Create QoS for topic
            qos = self._get_topic_qos()

            # Create topic
            topic = Topic(self.participant, topic_name, idl_type, qos)

            self.topics[topic_name] = topic
            logger.info(f"Created topic: {topic_name}")

            return topic

        except Exception as e:
            raise DDSManagerError(f"Failed to create topic {topic_name}: {e}")

    def create_data_reader(self, topic_name: str) -> DataReader:
        """
        Create a DDS DataReader for a topic.

        Args:
            topic_name: Name of the topic

        Returns:
            DDS DataReader

        Raises:
            DDSManagerError: If reader creation fails
        """
        if topic_name in self.data_readers:
            return self.data_readers[topic_name]

        topic = self.create_topic(topic_name)

        try:
            # Create QoS from configuration
            qos = self._get_reader_qos()

            # Create data reader
            reader = DataReader(self.subscriber, topic, qos)
            self.data_readers[topic_name] = reader

            logger.info(f"Created DataReader for topic: {topic_name}")
            return reader

        except Exception as e:
            raise DDSManagerError(f"Failed to create DataReader for {topic_name}: {e}")

    def create_data_writer(self, topic_name: str) -> DataWriter:
        """
        Create a DDS DataWriter for a topic.

        Args:
            topic_name: Name of the topic

        Returns:
            DDS DataWriter

        Raises:
            DDSManagerError: If writer creation fails
        """
        if topic_name in self.data_writers:
            return self.data_writers[topic_name]

        topic = self.create_topic(topic_name)

        try:
            # Create QoS from configuration
            qos = self._get_writer_qos()

            # Create data writer
            writer = DataWriter(self.publisher, topic, qos)
            self.data_writers[topic_name] = writer

            logger.info(f"Created DataWriter for topic: {topic_name}")
            return writer

        except Exception as e:
            raise DDSManagerError(f"Failed to create DataWriter for {topic_name}: {e}")

    def _get_topic_qos(self) -> Qos:
        """Get Topic QoS from configuration."""
        qos_config = self.gateway_config.get_dds_qos_profile()
        qos = Qos()

        # Apply reliability policy
        reliability = qos_config.get("reliability", "RELIABLE")
        if reliability == "RELIABLE":
            qos += Policy.Reliability.Reliable(duration(seconds=10))
        else:
            qos += Policy.Reliability.BestEffort

        # Apply durability policy
        durability = qos_config.get("durability", "VOLATILE")
        if durability == "TRANSIENT_LOCAL":
            qos += Policy.Durability.TransientLocal
        elif durability == "TRANSIENT":
            qos += Policy.Durability.Transient
        elif durability == "PERSISTENT":
            qos += Policy.Durability.Persistent
        else:
            qos += Policy.Durability.Volatile

        return qos

    def _get_reader_qos(self) -> Qos:
        """Get DataReader QoS from configuration."""
        qos_config = self.gateway_config.get_dds_qos_profile()
        qos = Qos()

        # Reliability
        reliability = qos_config.get("reliability", "RELIABLE")
        if reliability == "RELIABLE":
            qos += Policy.Reliability.Reliable(duration(seconds=10))
        else:
            qos += Policy.Reliability.BestEffort

        # Durability
        durability = qos_config.get("durability", "VOLATILE")
        if durability == "TRANSIENT_LOCAL":
            qos += Policy.Durability.TransientLocal
        else:
            qos += Policy.Durability.Volatile

        # History
        history_kind = qos_config.get("history_kind", "KEEP_LAST")
        history_depth = qos_config.get("history_depth", 10)

        if history_kind == "KEEP_ALL":
            qos += Policy.History.KeepAll
        else:
            qos += Policy.History.KeepLast(history_depth)

        return qos

    def _get_writer_qos(self) -> Qos:
        """Get DataWriter QoS from configuration."""
        qos_config = self.gateway_config.get_dds_qos_profile()
        qos = Qos()

        # Reliability
        reliability = qos_config.get("reliability", "RELIABLE")
        if reliability == "RELIABLE":
            qos += Policy.Reliability.Reliable(duration(seconds=10))
        else:
            qos += Policy.Reliability.BestEffort

        # Durability
        durability = qos_config.get("durability", "VOLATILE")
        if durability == "TRANSIENT_LOCAL":
            qos += Policy.Durability.TransientLocal
        else:
            qos += Policy.Durability.Volatile

        # History
        history_kind = qos_config.get("history_kind", "KEEP_LAST")
        history_depth = qos_config.get("history_depth", 10)

        if history_kind == "KEEP_ALL":
            qos += Policy.History.KeepAll
        else:
            qos += Policy.History.KeepLast(history_depth)

        return qos

    async def read_samples(self, topic_name: str, max_samples: int = 100) -> List[Dict]:
        """
        Read samples from a topic.

        Args:
            topic_name: Name of the topic
            max_samples: Maximum number of samples to read

        Returns:
            List of sample dictionaries

        Raises:
            DDSManagerError: If read fails
        """
        reader = self.data_readers.get(topic_name)
        if not reader:
            reader = self.create_data_reader(topic_name)

        try:
            # Read samples from DDS
            samples = reader.take(max_samples)

            # Convert to dictionaries
            results = []
            for sample in samples:
                if sample is not None:  # Valid sample
                    results.append(self._sample_to_dict(sample))

            logger.debug(f"Read {len(results)} samples from {topic_name}")
            return results

        except Exception as e:
            raise DDSManagerError(f"Failed to read from {topic_name}: {e}")

    async def write_sample(self, topic_name: str, data: Dict) -> None:
        """
        Write a sample to a topic.

        Args:
            topic_name: Name of the topic
            data: Sample data as dictionary

        Raises:
            DDSManagerError: If write fails
        """
        writer = self.data_writers.get(topic_name)
        if not writer:
            writer = self.create_data_writer(topic_name)

        try:
            # Convert dict to DDS sample
            sample = self._dict_to_sample(topic_name, data)

            # Write sample
            writer.write(sample)

            logger.debug(f"Wrote sample to {topic_name}")

        except Exception as e:
            raise DDSManagerError(f"Failed to write to {topic_name}: {e}")

    def subscribe(self, topic_name: str, callback: Optional[Callable] = None) -> str:
        """
        Subscribe to a topic with optional callback.

        Args:
            topic_name: Name of the topic
            callback: Optional async callback function(topic_name, samples)

        Returns:
            Subscription ID

        Raises:
            DDSManagerError: If subscription fails
        """
        reader = self.data_readers.get(topic_name)
        if not reader:
            reader = self.create_data_reader(topic_name)

        subscription_id = f"{topic_name}_{int(time.time() * 1000)}"

        handle = SubscriptionHandle(
            topic_name=topic_name,
            data_reader=reader,
            callback=callback
        )

        self.subscriptions[subscription_id] = handle

        logger.info(f"Created subscription {subscription_id} for topic {topic_name}")
        return subscription_id

    def unsubscribe(self, subscription_id: str) -> None:
        """
        Unsubscribe from a topic.

        Args:
            subscription_id: Subscription ID to cancel
        """
        if subscription_id in self.subscriptions:
            handle = self.subscriptions[subscription_id]
            handle.active = False
            del self.subscriptions[subscription_id]
            logger.info(f"Unsubscribed: {subscription_id}")

    def _sample_to_dict(self, sample: Any) -> Dict:
        """
        Convert DDS sample (IdlStruct) to dictionary.

        Args:
            sample: DDS sample object

        Returns:
            Dictionary representation
        """
        if hasattr(sample, '__dict__'):
            # For IdlStruct objects, convert to dict
            result = {}
            for field_name in sample.__dataclass_fields__:
                result[field_name] = getattr(sample, field_name)
            return result
        else:
            # Fallback
            return {}

    def _dict_to_sample(self, topic_name: str, data: Dict) -> Any:
        """
        Convert dictionary to DDS sample (IdlStruct).

        Args:
            topic_name: Name of the topic
            data: Dictionary with sample data

        Returns:
            DDS sample object
        """
        idl_type = self._get_type_for_topic(topic_name)

        # Create instance of the IDL type
        # Handle missing fields by providing defaults
        sample_data = {}
        for field_name, field_def in idl_type.__dataclass_fields__.items():
            if field_name in data:
                sample_data[field_name] = data[field_name]
            else:
                # Provide default value based on type
                field_type = field_def.type
                if field_type == str:
                    sample_data[field_name] = ""
                elif field_type == int:
                    sample_data[field_name] = 0
                elif field_type == float:
                    sample_data[field_name] = 0.0
                elif field_type == bool:
                    sample_data[field_name] = False
                else:
                    sample_data[field_name] = None

        return idl_type(**sample_data)

    @property
    def is_running(self) -> bool:
        """Check if DDS Manager is running."""
        return self._running

    def get_participant_info(self) -> Dict:
        """Get information about the DDS participant."""
        if not self.participant:
            return {}

        return {
            "domain_id": self.gateway_config.domain_id,
            "security_enabled": self.gateway_config.security_enabled,
            "topics": list(self.topics.keys()),
            "active_readers": len(self.data_readers),
            "active_writers": len(self.data_writers),
            "active_subscriptions": len(self.subscriptions),
            "dds_implementation": "Eclipse Cyclone DDS"
        }


# Alias for backward compatibility
DDSManager = CycloneDDSManager
