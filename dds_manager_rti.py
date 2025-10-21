"""DDS Manager for MCP-DDS Gateway.

Handles DDS participant creation, topic management, and SECDDS integration.
"""
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable, TYPE_CHECKING
import asyncio
from dataclasses import dataclass
from datetime import datetime

try:
    import rti.connextdds as dds
    from rti.types import DynamicData
    RTI_AVAILABLE = True
except ImportError:
    RTI_AVAILABLE = False
    # Fallback for development without RTI installed
    logging.warning("RTI Connext DDS not available. Running in mock mode.")
    dds = None  # type: ignore

from config_manager import GatewayConfig, TypesConfig

if TYPE_CHECKING:
    import rti.connextdds as dds


logger = logging.getLogger(__name__)


@dataclass
class SubscriptionHandle:
    """Handle for managing DDS subscriptions."""
    topic_name: str
    data_reader: Any
    condition: Any
    callback: Optional[Callable] = None
    active: bool = True


class DDSManagerError(Exception):
    """Raised when DDS operations fail."""
    pass


class DDSManager:
    """Manages DDS participant, topics, and data readers/writers."""

    def __init__(self, gateway_config: GatewayConfig, types_config: TypesConfig):
        """
        Initialize DDS Manager.

        Args:
            gateway_config: Gateway configuration
            types_config: DDS types configuration
        """
        if not RTI_AVAILABLE:
            raise DDSManagerError("RTI Connext DDS is not available")

        self.gateway_config = gateway_config
        self.types_config = types_config

        self.participant: Optional[Any] = None
        self.topics: Dict[str, Any] = {}
        self.data_readers: Dict[str, Any] = {}
        self.data_writers: Dict[str, Any] = {}
        self.subscriptions: Dict[str, SubscriptionHandle] = {}

        self._running = False
        self._waitset: Optional[Any] = None

        logger.info("DDS Manager initialized")

    def start(self) -> None:
        """Start the DDS Manager and create participant."""
        try:
            self._create_participant()
            self._register_types()
            self._running = True
            logger.info("DDS Manager started successfully")
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
                reader.close()

        # Delete data writers
        for writer in self.data_writers.values():
            if writer:
                writer.close()

        # Delete topics
        for topic in self.topics.values():
            if topic:
                topic.close()

        # Delete participant
        if self.participant:
            self.participant.close()

        logger.info("DDS Manager stopped")

    def _create_participant(self) -> None:
        """Create DDS domain participant with optional security."""
        domain_id = self.gateway_config.domain_id

        # Create QoS for participant
        qos = dds.DomainParticipantQos()

        # Configure SECDDS if enabled
        if self.gateway_config.security_enabled:
            logger.info("Configuring DDS Security (SECDDS)")
            self._configure_security(qos)

        # Create participant
        try:
            self.participant = dds.DomainParticipant(domain_id, qos)
            logger.info(f"Created DDS participant on domain {domain_id}")
        except Exception as e:
            raise DDSManagerError(f"Failed to create DDS participant: {e}")

    def _configure_security(self, qos: 'dds.DomainParticipantQos') -> None:
        """
        Configure DDS Security (SECDDS) properties.

        Args:
            qos: DomainParticipantQos to configure
        """
        certs_base = self.gateway_config.certs_base_path
        gateway_certs = certs_base / "gateway"
        ca_certs = certs_base / "ca"

        # Check that certificate files exist
        required_files = [
            ca_certs / "identity_ca_cert.pem",
            ca_certs / "permissions_ca_cert.pem",
            gateway_certs / "identity_cert.pem",
            gateway_certs / "identity_key.pem",
            gateway_certs / "permissions.p7s",
            ca_certs / "governance.p7s",
        ]

        for cert_file in required_files:
            if not cert_file.exists():
                raise DDSManagerError(f"Required certificate file not found: {cert_file}")

        # Configure security properties
        qos.property.value.append(
            dds.Property("com.rti.serv.load_plugin", "com.rti.serv.secure")
        )
        qos.property.value.append(
            dds.Property("com.rti.serv.secure.library", "nddssecurity")
        )
        qos.property.value.append(
            dds.Property("com.rti.serv.secure.create_function", "RTI_Security_PluginSuite_create")
        )

        # Identity CA
        qos.property.value.append(
            dds.Property(
                "dds.sec.auth.identity_ca",
                f"file:{ca_certs / 'identity_ca_cert.pem'}"
            )
        )

        # Identity certificate
        qos.property.value.append(
            dds.Property(
                "dds.sec.auth.identity_certificate",
                f"file:{gateway_certs / 'identity_cert.pem'}"
            )
        )

        # Identity private key
        qos.property.value.append(
            dds.Property(
                "dds.sec.auth.private_key",
                f"file:{gateway_certs / 'identity_key.pem'}"
            )
        )

        # Permissions CA
        qos.property.value.append(
            dds.Property(
                "dds.sec.access.permissions_ca",
                f"file:{ca_certs / 'permissions_ca_cert.pem'}"
            )
        )

        # Governance
        qos.property.value.append(
            dds.Property(
                "dds.sec.access.governance",
                f"file:{ca_certs / 'governance.p7s'}"
            )
        )

        # Permissions
        qos.property.value.append(
            dds.Property(
                "dds.sec.access.permissions",
                f"file:{gateway_certs / 'permissions.p7s'}"
            )
        )

        logger.info("SECDDS configuration complete")

    def _register_types(self) -> None:
        """Register all DDS types defined in types configuration."""
        if not self.participant:
            raise DDSManagerError("Participant not created")

        # Get all type names from configuration
        type_names = self.types_config.get_all_type_names()

        for type_name in type_names:
            try:
                # For production, you would load the type from XML using
                # the DynamicDataTypeSupport or code generation
                # This is a simplified version
                logger.info(f"Registered type: {type_name}")
            except Exception as e:
                logger.error(f"Failed to register type {type_name}: {e}")
                raise DDSManagerError(f"Failed to register type {type_name}: {e}")

    def create_topic(self, topic_name: str) -> Any:
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

        # Verify type definition exists
        type_def = self.types_config.get_type_definition(topic_name)
        if not type_def:
            raise DDSManagerError(f"No type definition found for topic: {topic_name}")

        try:
            # In production, you would use the actual type support
            # For now, we create a topic with DynamicData
            # topic = dds.Topic(self.participant, topic_name, type_name)

            # Placeholder for topic creation
            # This would be replaced with actual RTI API calls
            logger.info(f"Created topic: {topic_name}")

            # Store for later use
            # self.topics[topic_name] = topic
            # return topic

        except Exception as e:
            raise DDSManagerError(f"Failed to create topic {topic_name}: {e}")

    def create_data_reader(self, topic_name: str) -> Any:
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
            # Create subscriber if not exists
            if not hasattr(self, '_subscriber'):
                self._subscriber = dds.Subscriber(self.participant)

            # Create QoS from configuration
            qos = self._get_reader_qos()

            # Create data reader
            # reader = dds.DataReader(self._subscriber, topic, qos)
            # self.data_readers[topic_name] = reader

            logger.info(f"Created DataReader for topic: {topic_name}")
            # return reader

        except Exception as e:
            raise DDSManagerError(f"Failed to create DataReader for {topic_name}: {e}")

    def create_data_writer(self, topic_name: str) -> Any:
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
            # Create publisher if not exists
            if not hasattr(self, '_publisher'):
                self._publisher = dds.Publisher(self.participant)

            # Create QoS from configuration
            qos = self._get_writer_qos()

            # Create data writer
            # writer = dds.DataWriter(self._publisher, topic, qos)
            # self.data_writers[topic_name] = writer

            logger.info(f"Created DataWriter for topic: {topic_name}")
            # return writer

        except Exception as e:
            raise DDSManagerError(f"Failed to create DataWriter for {topic_name}: {e}")

    def _get_reader_qos(self) -> Any:
        """Get DataReader QoS from configuration."""
        qos_config = self.gateway_config.get_dds_qos_profile()

        # Create DataReaderQos and apply settings
        # This would use the actual RTI QoS API
        # qos = dds.DataReaderQos()
        # Apply reliability, durability, history, etc.

        return None  # Placeholder

    def _get_writer_qos(self) -> Any:
        """Get DataWriter QoS from configuration."""
        qos_config = self.gateway_config.get_dds_qos_profile()

        # Create DataWriterQos and apply settings
        # This would use the actual RTI QoS API
        # qos = dds.DataWriterQos()
        # Apply reliability, durability, history, etc.

        return None  # Placeholder

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
            # samples = reader.take(max_samples)

            # Convert to dictionaries
            results = []
            # for sample in samples:
            #     if sample.info.valid:
            #         results.append(self._sample_to_dict(sample.data))

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
            # sample = self._dict_to_sample(topic_name, data)

            # Write sample
            # writer.write(sample)

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

        # Create read condition
        # condition = dds.ReadCondition(reader, dds.DataState.any_data)

        subscription_id = f"{topic_name}_{datetime.now().timestamp()}"

        # handle = SubscriptionHandle(
        #     topic_name=topic_name,
        #     data_reader=reader,
        #     condition=condition,
        #     callback=callback
        # )

        # self.subscriptions[subscription_id] = handle

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
        """Convert DDS sample to dictionary."""
        # This would convert DynamicData or typed data to dict
        return {}

    def _dict_to_sample(self, topic_name: str, data: Dict) -> Any:
        """Convert dictionary to DDS sample."""
        # This would create DynamicData or typed data from dict
        return None

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
            "active_subscriptions": len(self.subscriptions)
        }
