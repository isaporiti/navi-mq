"""NaviBase implementation module."""

import logging

from pika import BaseConnection, ConnectionParameters, PlainCredentials

from navi import config
from navi.exceptions import NaviInitException


class NaviBase:
    """A base class that implements the base methods to be used by NaviListener.

    Attributes:
        _routing_key: The routing key to be used to either publish a message to an exchange, or bind
            a listening queue to an exchange.
        _connection_parameters: The ConnectionParameters instance to be used to establish
            connections.
        logger: A logger instance.
    """

    def __init__(self, routing_key: str = None):
        """Base initialization logic for NaviBase subclasses.

        It sets up the `_routing_key`, and `logger` attributes.

        Args:
            routing_key: The routing key to be used to either publish a message to an exchange, or
                bind a listening queue to an exchange.

        Raises:
            NaviInitException: When routing_key is None.
        """
        if routing_key is None:
            raise NaviInitException("Need routing_key to be not None.")

        self._routing_key = routing_key

        self._connection_parameters = self._init_connection_params()
        self.logger = logging.getLogger("navi")

    def _init_credentials(self) -> PlainCredentials:  # pylint:disable = R0201
        """Initializes a PlainCredentials object.

        To do so, it uses the NAVI_AMQP_USERNAME and NAVI_AMQP_PASSWORD environment variables.

        Returns:
            The created PlainCredentials instance.
        """
        credentials = PlainCredentials(config.NAVI_AMQP_USERNAME, config.NAVI_AMQP_PASSWORD)

        return credentials

    def _init_connection_params(self) -> ConnectionParameters:
        """Initializes a ConnectionParameters object.

        To do so, it first calls `_init_credentials` to create the required PlainCredentials object.

        Returns:
            The created ConnectionParameters instance.
        """
        credentials = self._init_credentials()
        connection_parameters = ConnectionParameters(
            host=config.NAVI_AMQP_HOST, port=config.NAVI_AMQP_PORT, credentials=credentials
        )

        return connection_parameters

    def _init_connection(self, connection_parameters: ConnectionParameters) -> BaseConnection:
        """Abstract method to be implemented by the NaviListener and NaviPublisher subclasses, as
        each of them should use different connection types.

        Args:
            connection_parameters: The ConnectionParameters instance to be used to connect to the
                broker.

        Raises:
            NotImplementedError: raised if this abstract method is called.

        Returns:
            BaseConnection: A BaseConnection subclass instance, representing and open connection to
                an AMQP broker.
        """
        raise NotImplementedError()
