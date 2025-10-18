"""Configuration management for MCP-DDS Gateway."""
import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Set
import xmltodict


logger = logging.getLogger(__name__)


class ConfigurationError(Exception):
    """Raised when configuration is invalid."""
    pass


class GatewayConfig:
    """Gateway configuration manager."""

    def __init__(self, config_path: str = "config/gateway_config.json"):
        """
        Initialize gateway configuration.

        Args:
            config_path: Path to gateway configuration JSON file
        """
        self.config_path = Path(config_path)
        self.config: Dict = {}
        self._load_config()
        self._validate_config()

    def _load_config(self) -> None:
        """Load configuration from JSON file."""
        try:
            with open(self.config_path, 'r') as f:
                self.config = json.load(f)
            logger.info(f"Loaded configuration from {self.config_path}")
        except FileNotFoundError:
            raise ConfigurationError(f"Configuration file not found: {self.config_path}")
        except json.JSONDecodeError as e:
            raise ConfigurationError(f"Invalid JSON in configuration file: {e}")

    def _validate_config(self) -> None:
        """Validate configuration structure and required fields."""
        required_sections = ["domain_id", "gateway", "security", "topic_allowlist"]

        for section in required_sections:
            if section not in self.config:
                raise ConfigurationError(f"Missing required configuration section: {section}")

        # Validate domain_id
        if not isinstance(self.config["domain_id"], int):
            raise ConfigurationError("domain_id must be an integer")

        # Validate topic allowlist
        for agent_name, permissions in self.config["topic_allowlist"].items():
            if "read" not in permissions or "write" not in permissions:
                raise ConfigurationError(
                    f"Agent '{agent_name}' must have both 'read' and 'write' permissions lists"
                )
            if not isinstance(permissions["read"], list):
                raise ConfigurationError(f"Agent '{agent_name}' read permissions must be a list")
            if not isinstance(permissions["write"], list):
                raise ConfigurationError(f"Agent '{agent_name}' write permissions must be a list")

        logger.info("Configuration validation passed")

    @property
    def domain_id(self) -> int:
        """Get DDS domain ID."""
        return self.config["domain_id"]

    @property
    def gateway_name(self) -> str:
        """Get gateway name."""
        return self.config["gateway"]["name"]

    @property
    def bind_address(self) -> str:
        """Get gateway bind address."""
        return self.config["gateway"].get("bind_address", "0.0.0.0")

    @property
    def port(self) -> int:
        """Get gateway port."""
        return self.config["gateway"].get("port", 8080)

    @property
    def security_enabled(self) -> bool:
        """Check if security is enabled."""
        return self.config["security"].get("enabled", False)

    @property
    def certs_base_path(self) -> Path:
        """Get base path for certificates."""
        return Path(self.config["security"].get("certs_base_path", "./certs"))

    @property
    def max_samples_per_read(self) -> int:
        """Get maximum samples per read operation."""
        return self.config.get("performance", {}).get("max_samples_per_read", 100)

    @property
    def batch_timeout_ms(self) -> int:
        """Get batch timeout in milliseconds."""
        return self.config.get("performance", {}).get("batch_timeout_ms", 50)

    @property
    def rate_limiting_enabled(self) -> bool:
        """Check if rate limiting is enabled."""
        return self.config.get("rate_limiting", {}).get("enabled", True)

    @property
    def requests_per_minute(self) -> int:
        """Get global requests per minute limit."""
        return self.config.get("rate_limiting", {}).get("requests_per_minute", 1000)

    @property
    def per_agent_limit(self) -> int:
        """Get per-agent requests per minute limit."""
        return self.config.get("rate_limiting", {}).get("per_agent_limit", 500)

    @property
    def metrics_enabled(self) -> bool:
        """Check if metrics collection is enabled."""
        return self.config.get("monitoring", {}).get("metrics_enabled", True)

    @property
    def metrics_port(self) -> int:
        """Get metrics endpoint port."""
        return self.config.get("monitoring", {}).get("metrics_port", 9090)

    @property
    def log_level(self) -> str:
        """Get logging level."""
        return self.config.get("monitoring", {}).get("log_level", "INFO")

    def get_agent_read_topics(self, agent_name: str) -> List[str]:
        """
        Get list of topics an agent is allowed to read.

        Args:
            agent_name: Name of the agent

        Returns:
            List of topic names
        """
        allowlist = self.config.get("topic_allowlist", {})
        agent_perms = allowlist.get(agent_name, {})
        return agent_perms.get("read", [])

    def get_agent_write_topics(self, agent_name: str) -> List[str]:
        """
        Get list of topics an agent is allowed to write.

        Args:
            agent_name: Name of the agent

        Returns:
            List of topic names
        """
        allowlist = self.config.get("topic_allowlist", {})
        agent_perms = allowlist.get(agent_name, {})
        return agent_perms.get("write", [])

    def can_agent_read_topic(self, agent_name: str, topic_name: str) -> bool:
        """
        Check if agent has read permission for a topic.

        Args:
            agent_name: Name of the agent
            topic_name: Name of the topic

        Returns:
            True if agent can read the topic
        """
        return topic_name in self.get_agent_read_topics(agent_name)

    def can_agent_write_topic(self, agent_name: str, topic_name: str) -> bool:
        """
        Check if agent has write permission for a topic.

        Args:
            agent_name: Name of the agent
            topic_name: Name of the topic

        Returns:
            True if agent can write to the topic
        """
        return topic_name in self.get_agent_write_topics(agent_name)

    def get_all_agents(self) -> List[str]:
        """Get list of all configured agent names."""
        return list(self.config.get("topic_allowlist", {}).keys())

    def get_all_topics(self) -> Set[str]:
        """Get set of all topics mentioned in the configuration."""
        topics = set()
        for agent_perms in self.config.get("topic_allowlist", {}).values():
            topics.update(agent_perms.get("read", []))
            topics.update(agent_perms.get("write", []))
        return topics

    def get_dds_qos_profile(self) -> Dict:
        """Get DDS QoS profile settings."""
        return self.config.get("dds_qos", {})


class TypesConfig:
    """DDS types configuration manager."""

    def __init__(self, types_path: str = "config/types.xml"):
        """
        Initialize types configuration.

        Args:
            types_path: Path to DDS types XML file
        """
        self.types_path = Path(types_path)
        self.types: Dict = {}
        self._load_types()

    def _load_types(self) -> None:
        """Load DDS type definitions from XML file."""
        try:
            with open(self.types_path, 'r') as f:
                xml_content = f.read()
                self.types = xmltodict.parse(xml_content)
            logger.info(f"Loaded DDS types from {self.types_path}")
        except FileNotFoundError:
            raise ConfigurationError(f"Types file not found: {self.types_path}")
        except Exception as e:
            raise ConfigurationError(f"Error parsing types XML: {e}")

    def get_type_definition(self, type_name: str) -> Optional[Dict]:
        """
        Get type definition by name.

        Args:
            type_name: Name of the DDS type

        Returns:
            Type definition dictionary or None if not found
        """
        types_list = self.types.get("types", {}).get("struct", [])

        # Handle single struct vs list of structs
        if isinstance(types_list, dict):
            types_list = [types_list]

        for type_def in types_list:
            if type_def.get("@name") == type_name:
                return type_def

        return None

    def get_all_type_names(self) -> List[str]:
        """Get list of all defined type names."""
        types_list = self.types.get("types", {}).get("struct", [])

        # Handle single struct vs list of structs
        if isinstance(types_list, dict):
            types_list = [types_list]

        return [t.get("@name") for t in types_list if "@name" in t]

    def validate_topic_types(self, topics: Set[str]) -> bool:
        """
        Validate that all topics have corresponding type definitions.

        Args:
            topics: Set of topic names to validate

        Returns:
            True if all topics have type definitions

        Raises:
            ConfigurationError: If any topic lacks a type definition
        """
        defined_types = set(self.get_all_type_names())
        missing_types = topics - defined_types

        if missing_types:
            raise ConfigurationError(
                f"Topics without type definitions: {', '.join(missing_types)}"
            )

        logger.info(f"All {len(topics)} topics have valid type definitions")
        return True


def load_configuration(config_path: str = "config/gateway_config.json",
                      types_path: str = "config/types.xml") -> tuple[GatewayConfig, TypesConfig]:
    """
    Load and validate all configuration files.

    Args:
        config_path: Path to gateway configuration
        types_path: Path to types configuration

    Returns:
        Tuple of (GatewayConfig, TypesConfig)

    Raises:
        ConfigurationError: If configuration is invalid
    """
    gateway_config = GatewayConfig(config_path)
    types_config = TypesConfig(types_path)

    # Cross-validate: ensure all topics have type definitions
    all_topics = gateway_config.get_all_topics()
    types_config.validate_topic_types(all_topics)

    logger.info("All configurations loaded and validated successfully")
    return gateway_config, types_config
