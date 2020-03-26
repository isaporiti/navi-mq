"""Navi's configuration file."""
from dataclasses import dataclass
from navi.exceptions import NaviConfigException

NAVI_AMQP_USERNAME = None
NAVI_AMQP_PASSWORD = None
NAVI_AMQP_HOST = None
NAVI_AMQP_PORT = None
NAVI_EXCHANGE = None
NAVI_EXCHANGE_TYPE = None


@dataclass
class NaviConfigEntry:
    """A class representing a Navi configuration entry.

    Used for validation and data representation. Can be subclassified to implement custom
    validations.
    """

    key: str
    value: str

    @property
    def is_valid(self):
        """Checks if the NaviConfigEntry is valid.

        Returns:
            A boolean value indicating if the NaviConfigEntry instance is valid.
        """
        return bool(self.key and self.value is not None)


def init_config(
        broker_host: str,
        broker_port: str,
        username: str,
        password: str,
        default_exchange: str = "amq.topic",
        default_exchange_type: str = "topic",
):  # pylint:disable = R0913
    """Sets Navi's configuration.

    This should be called when initializing your application to set the variables needed to
    establish connections to an AMQP broker.

    Consider that this should only be called once per application run, to avoid communicating with
    different brokers in a single execution.

    Args:
        broker_host: The host's domain where the broker we want to connect to is running. Required.
        broker_port: The host's port where the broker we want to connect to is running. Required.
        username: The username to connect to the broker. Required.
        password: The password to connect to the broker. Required.

        **kwargs:
            default_exchange: The default exchange name to use. Optional. Defaults to "amq.topic".
                Possible values are: "amq.direct", "amq.fanout", "amq.topic".
            default_exchange_type: The default exchange type to use. Optional. Defaults to "topic".
                Possible values are: "direct", "fanout", "topic".

    """
    configs = [
        NaviConfigEntry(key="NAVI_AMQP_USERNAME", value=username),
        NaviConfigEntry(key="NAVI_AMQP_PASSWORD", value=password),
        NaviConfigEntry(key="NAVI_AMQP_HOST", value=broker_host),
        NaviConfigEntry(key="NAVI_AMQP_PORT", value=broker_port),
        NaviConfigEntry(key="NAVI_EXCHANGE", value=default_exchange),
        NaviConfigEntry(key="NAVI_EXCHANGE_TYPE", value=default_exchange_type),
    ]
    invalid_configs = [config for config in configs if not config.is_valid]

    if any(invalid_configs):
        raise NaviConfigException(invalid_configs)

    globals().update({config.key: config.value for config in configs})
