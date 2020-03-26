"""Test cases for navi.listener"""

from unittest import TestCase, mock

from pika import BaseConnection, ConnectionParameters, PlainCredentials
from pika.channel import Channel
from pika.exceptions import AMQPError

from navi import config
from navi.listener import NaviListener, listen


class TestNaviListener(TestCase):
    """Test cases for NaviListener"""

    def setUp(self):
        """Initializes a NaviListener"""
        config.init_config(
            broker_host="test", broker_port="1234", username="guest", password="guest"
        )
        self.listener = NaviListener(
            queue_name="test_queue", routing_key="test_routing_key", callback=mock.MagicMock()
        )
        self.listener.logger = mock.MagicMock()

    def test_on_connected(self):
        """
        When `on_connected` is called with a `connection` argument,
        `connection.channel(on_open_callback=self.on_channel_open)` should be called.
        """
        connection = mock.MagicMock()
        self.listener.on_connected(connection)
        connection.channel.assert_called_once_with(on_open_callback=self.listener.on_channel_open)

    def test_on_queue_declared(self):
        """
        When `on_queue_declared` is called with a `method` argument, the listener's `channel`'s 
        `basic_consume` method should be called.
        """
        method = mock.MagicMock()
        self.listener._channel = mock.MagicMock()

        self.listener.on_queue_declared(method)

        self.listener._channel.basic_consume.assert_called_once_with(
            self.listener._queue_name, self.listener.handle_delivery, auto_ack=True
        )

    def test_init_connection(self):
        """
        When the listener's `_init_connection` method is called, a `BaseConnection` object should
        be instantiated and returned.
        """
        connection_parameters = mock.MagicMock(spec=ConnectionParameters)

        obtained = self.listener._init_connection(connection_parameters)

        self.assertTrue(
            isinstance(obtained, BaseConnection),
            msg=f"Expected: BaseConnection; obtained: {type(obtained)}"
        )

    @mock.patch("navi.listener.Thread")
    def test_listen(self, thread_mock):
        """
        When the listener's `listen` method is called, a Thread should be instantiated and its
        `start` method should be called once.
        """
        self.listener.listen()
        thread_mock.return_value.start.assert_called_once()

    # TODO: move this to base test
    def test__init_credentials(self):
        """
        When the listener's `_init_credentials` method is called, a Thread should be instantiated
        and its `start` method should be called once.
        """
        credentials = self.listener._init_credentials()

        self.assertTrue(
            isinstance(credentials, PlainCredentials),
            msg="credentials obj is not of type PlainCredentials",
        )
        self.assertIsNotNone(credentials.username, msg="Missing username in credentials")
        self.assertIsNotNone(credentials.password, msg="Missing password in credentials")

    @mock.patch.object(NaviListener, "_init_connection")
    def test_listen(self, init_connection_mock):
        """
        When the listener's `listen` method is called, `_init_connection` should be called, and from
        the connection returned by it, `ioloop.start` should be called. As the execution is
        successful, `connection.close` shouldn't be called.
        """
        connection = mock.MagicMock(spec=BaseConnection)
        init_connection_mock.return_value = connection

        self.listener._listen()

        connection.ioloop.start.assert_called_once()
        connection.assert_not_called()

    @mock.patch.object(BaseConnection, "close")
    @mock.patch.object(NaviListener, "_init_connection")
    def test_listen_failure_connection_not_set(self, init_connection_mock, close_mock):
        """
        When the listener's `listen` method is called, `_init_connection` should be called, and from
        the connection returned by it, `ioloop.start` should be called. If the execution fails, if
        the connection is not set, then `connection.close` shouldn't be called.
        """
        init_connection_mock.side_effect = AMQPError()

        self.listener._listen()

        close_mock.assert_not_called()

    @mock.patch.object(NaviListener, "_init_connection")
    def test_listen_failure_connection_set(self, init_connection_mock):
        """
        When the listener's `listen` method is called, `_init_connection` should be called, and from
        the connection returned by it, `ioloop.start` should be called. As the execution fails, if
        the connection is set, then `connection.close` should be be called.
        """
        self.listener._connection_parameters = mock.MagicMock()
        connection = init_connection_mock.return_value
        connection.ioloop.start.side_effect = (AMQPError(), True)

        self.listener._listen()

        connection.ioloop.start.assert_any_call()
        connection.close.assert_called_once()

    def test_on_channel_open(self):
        """
        When the listener's `on_channel_open` method is called with a `channel` argument,
        `channel`'s `exchange_declare`, `queue_declare` and `queue_bind` methods should be called.
        """
        channel = mock.MagicMock(spec=Channel)

        self.listener.on_channel_open(channel)

        channel.exchange_declare.assert_called_once_with(
            exchange=config.NAVI_EXCHANGE, exchange_type=config.NAVI_EXCHANGE_TYPE, durable=True
        )
        channel.queue_declare.assert_called_once_with(
            queue=self.listener._queue_name,
            durable=True,
            exclusive=True,
            auto_delete=False,
            callback=self.listener.on_queue_declared,
        )
        channel.queue_bind.assert_called_once_with(
            exchange=config.NAVI_EXCHANGE,
            queue=self.listener._queue_name,
            routing_key=self.listener._routing_key,
        )

    @mock.patch("navi.listener.json.loads")
    def test_handle_delivery(self, json_loads_mock):
        """
        When the listener's `handle_delivery` is called, if no error raises on json dumping,
        `_callback` should be called.
        """
        channel = mock.MagicMock()
        method = mock.MagicMock()
        properties = mock.MagicMock()
        body = mock.MagicMock()
        json_loads_mock.return_value = {}

        self.listener.handle_delivery(channel, method, properties, body)

        self.listener._callback.assert_called_once()

    @mock.patch("navi.listener.json.loads")
    def test_handle_delivery_failure(self, json_loads_mock):
        """
        When the listener's `handle_delivery` is called, if an error raises on json dumping or
        calling `_callback`, then the error should be caught and `logger.error` be called.
        """
        channel = mock.MagicMock()
        method = mock.MagicMock()
        properties = mock.MagicMock()
        body = mock.MagicMock()
        json_loads_mock.return_value = {}
        self.listener._callback.side_effect = Exception()

        self.listener.handle_delivery(channel, method, properties, body)

        self.listener.logger.error.assert_called_once()


class TestListen(TestCase):
    """Test cases for the listener.listen function."""

    @mock.patch.object(NaviListener, "listen")
    @mock.patch.object(NaviListener, "_init_connection_params")
    def test_listen(self, init_connection_params_mock, listen_mock):
        """
        When `listener.listen` is called with queue_name, routing_key and callback arguments, a 
        NaviListener should be initialized, and its `listen` method should be called.
        """
        queue_name = "my_queue"
        routing_key = "some.routing.key"
        callback = mock.MagicMock()
        listen(queue_name=queue_name, routing_key=routing_key, callback=callback)

        init_connection_params_mock.assert_called_once()
        listen_mock.assert_called_once()
