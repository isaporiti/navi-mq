"""NaviListener implementation module"""

import json
from threading import Thread
from typing import Callable

from pika import BaseConnection, BasicProperties, ConnectionParameters, SelectConnection
from pika.channel import Channel
from pika.exceptions import AMQPError
from pika.frame import Method

from navi import config
from navi.base import NaviBase
from navi.exceptions import NaviInitException


class NaviListener(NaviBase):
    """A class that sets up an AMQP connection, creates a queue, and binds a listener to it."""

    _callback: Callable
    _channel: Channel
    _queue_name: str
    _thread_name: str
    _thread: Thread

    def __init__(
            self, queue_name: str = None, routing_key: str = None, callback: Callable = None
    ):
        """Initializes a NaviListener.

        This class sets up a connection to an AMQP broker and binds a listener and a callback method
        to it.

        Args:
            queue_name: The name of the queue to listen at. Defaults to None.
            routing_key: The routing key to bind the listener's queue (defined by the `queue_name`
                argument) to the exchange (defined by the env variable`NAVI_EXCHANGE`). Defaults to
                None.
            callback: The callable to be executed whenever a message is received. Defaults to None.
        """
        super().__init__(routing_key=routing_key)

        if not queue_name:
            raise NaviInitException("Need queue to be not None.")

        self._queue_name = queue_name
        self._thread_name = f"navi-{self._queue_name}"

        if callback is None or not callable(callback):
            raise NaviInitException("Callable callback needed.")

        self._callback = callback

    def _init_connection(self, connection_parameters: ConnectionParameters) -> BaseConnection:
        """Initializes a BaseConnection to be used by the listener.

        Args:
            connection_parameters: A set up ConnectionParameters instance.

        Returns:
            The set up BaseConnection instance.
        """
        connection = SelectConnection(connection_parameters, on_open_callback=self.on_connected)

        return connection

    def listen(self):
        """Starts a thread that will spin the `_listen` method in background."""
        self._thread = Thread(target=self._listen, name=self._thread_name)
        self._thread.start()

    def _listen(self):
        """Starts listening in the NaviListener's queue.

            If any AMQPError is raised, the connection will be closed.
        """
        self.logger.info("Starting listener on %s...", self._queue_name)
        connection = None

        try:
            connection = self._init_connection(self._connection_parameters)
            connection.ioloop.start()

        except AMQPError as error:
            self.logger.error(
                "Error while listening on %s: %s. Closing connection.",
                self._queue_name,
                str(error),
            )
            self._close_connection(connection)

    def _close_connection(self, connection: SelectConnection):
        """Closes a given `SelectConnection` instance.

        It will call the connection's `close` method, and then `ioloop.start`, to try keep looping
        until it is fully closed, as suggested by pika's documentation:
            https://pika.readthedocs.io/en/stable/intro.html#io-and-event-looping

        Args:
            connection: The connection to close.
        """

        if not connection:
            return

        try:
            # Gracefully close the connection
            connection.close()
            # Loop until we're fully closed, will stop on its own
            connection.ioloop.start()

        except AMQPError as error:
            self.logger.error(
                "Error while closing connection on %s: %s.", self._queue_name, str(error),
            )

    def on_connected(self, connection: SelectConnection):
        """Called when the connection to the message broker is completed

        Args:
            connection: The SelectConnection instance, representing the achieved connection with the
            broker.
        """
        connection.channel(on_open_callback=self.on_channel_open)

    def on_channel_open(self, new_channel: Channel):
        """Called when a channel has opened.

        Through that channel, an exchange and a queue are declared. The exchange name and type will
        be set with config.NAVI_EXCHANGE and config.NAVI_EXCHANGE_TYPE, respectively. The queue name
        will be set with NaviListener._queue_name

        Args:
            new_channel: A pika's Channel instance, representing the opened communication channel.
        """
        self._channel = new_channel
        self._channel.exchange_declare(
            exchange=config.NAVI_EXCHANGE, exchange_type=config.NAVI_EXCHANGE_TYPE, durable=True
        )
        self._channel.queue_declare(
            queue=self._queue_name,
            durable=True,  # Survive reboots of the broker
            exclusive=True,  # Only allow access by the current connection
            auto_delete=False,  # Delete after consumer cancels or disconnects
            callback=self.on_queue_declared,
        )
        self._channel.queue_bind(
            exchange=config.NAVI_EXCHANGE, queue=self._queue_name, routing_key=self._routing_key
        )

    def on_queue_declared(self, method: Method):  # pylint:disable=unused-argument
        """Called when the message broker acknowledges queue declaration.

        Here the listener starts to consume from the previously declared queue. The callback
        assigned for each new message is NaviListener.handle_delivery, which wraps the user's
        callback and does message serialization and error handling.

        Args:
            method: The broker's response to a queue declaration request.
        """
        self._channel.basic_consume(self._queue_name, self.handle_delivery, auto_ack=True)

    def handle_delivery(
            self, channel: Channel, method: Method, properties: BasicProperties, body: bytes
    ):  # pylint:disable=unused-argument
        """Called whenever a message is dequeued from the declared queue.

        It loads/deserializes the message's body. If this executes without errors, the user's
        callback is executed. Any raised Exception during these actions is catched in order to
        ensure the listener is kept alive.
        """
        try:
            message = json.loads(body)

        except (TypeError, ValueError) as error:
            message_id = properties.headers.get("message_id")
            self.logger.error("Message %s with invalid body: %s", message_id, str(error))

        else:
            headers = {
                **{
                    "listener_name": self._thread_name,
                    "queue_name": self._queue_name
                },
                **properties.headers,
            }

            try:
                self._callback(headers, message)

            except Exception as error:  # pylint:disable = W0703
                message_id = properties.headers.get("message_id")
                self.logger.error("Error while handling message %s: %s", message_id, str(error))


def listen(
        queue_name: str = None, routing_key: str = None, callback: Callable = None,
):
    """Instantiates a threaded listener that keeps waiting for events on a queue.

    The queue will be named `queue_name`, bound to the exchange defined by `NAVI_EXCHANGE` env
    variable through routing key`routing_key`, and will execute `callback` whenever a message is
    dequeued.
    """
    listener = NaviListener(queue_name=queue_name, routing_key=routing_key, callback=callback,)
    listener.listen()
