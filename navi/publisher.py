"""NaviPublisher implementation module"""
import json
import socket
from datetime import datetime
from uuid import uuid4

from pika import BaseConnection, BasicProperties, BlockingConnection, ConnectionParameters
from pika.exceptions import AMQPError

from navi import config
from navi.base import NaviBase


class NaviPublisher(NaviBase):
    """A class that sets up a connection with a AMQP broker and is capable of publishing messages to
    a broker's exchange.

    It opens a new connection for each message to be published. After the message is sent, or if an
    exception is raised, the connections is closed.
    """

    def _init_connection(self, connection_parameters: ConnectionParameters) -> BaseConnection:
        """Initializes a BlockingConnection to be used by the listener.

        Args:
            connection_parameters: A set up ConnectionParameters instance.

        Returns:
            The set up BaseConnection instance.
        """
        connection = BlockingConnection(connection_parameters)

        return connection

    def publish(self, message: dict):
        """Publishes `message` to the exchange with name and type defined by the `NAVI_EXCHANGE` and
        `NAVI_EXCHANGE_TYPE` environment variables.

        To do so, it dumps/serializes the message and opens a connection to the broker. After having
        published the message, or if an Exception is raised, the connection is closed, if set.

        Args:
            message: A dict containing data to be sent as a JSON string through the broker.
        """
        try:
            body = json.dumps(message)

        except (TypeError, ValueError) as error:
            self.logger.error("Message with invalid body: %s", str(error))

        else:
            self._publish_message(body)

    def _publish_message(self, body: str):
        connection = None
        message_properties = self._build_message_properties()

        try:
            connection = self._init_connection(self._connection_parameters)
            channel = connection.channel()
            channel.exchange_declare(
                exchange=config.NAVI_EXCHANGE,
                exchange_type=config.NAVI_EXCHANGE_TYPE,
                durable=True,
            )
            channel.basic_publish(
                exchange=config.NAVI_EXCHANGE,
                routing_key=self._routing_key,
                properties=message_properties,
                body=body,
            )
            self.logger.info("Exchange %s: Message sent.", config.NAVI_EXCHANGE)

        except AMQPError as error:
            self.logger.error(
                "Error while publishing. Exchange: %s; error: %s.", config.NAVI_EXCHANGE, error
            )

        finally:

            if connection:
                connection.close()

    @staticmethod
    def _build_message_properties() -> BasicProperties:  # pylint:disable = R0201
        """Builds a headers dict with metadata about the message, adds it to a BasicProperties,
        and returns the properties object.

        Returns:
            A BasicProperties instance with a headers dict containing message metadata.
        """
        headers = {
            "message_id": str(uuid4()),
            "published_at": str(datetime.utcnow()),
            "from_host": socket.getfqdn(),
        }
        message_properties = BasicProperties(headers=headers)

        return message_properties


def publish(routing_key: str = None, message: dict = None):
    """
    Instantiates a NaviPublisher that will publish the `message` to the exchange defined by the
    `NAVI_EXCHANGE` environment variable.

    Args:
        routing_key: The routing key to be used by the broker to find the queues to send the message
            to. Queues that have been declared as bound to the exact routing_key will receive this
            message.
        message: A dict containing data to be sent as a JSON string through the broker.
    """
    publisher = NaviPublisher(routing_key=routing_key)
    publisher.publish(message)
