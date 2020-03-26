"""Test cases for navi.publisher"""
from unittest import TestCase, mock

from pika import BasicProperties, BlockingConnection, ConnectionParameters
from pika.exceptions import AMQPError

from navi import config
from navi.publisher import NaviPublisher, publish


class TestNaviPublisher(TestCase):
    """Test cases for NaviPublisher"""

    def setUp(self):
        """Initializes a NaviPublisher"""
        config.init_config(
            broker_host="test", broker_port="1234", username="guest", password="guest"
        )
        self.publisher = NaviPublisher(routing_key="test_routing_key")
        self.publisher.logger = mock.MagicMock()

    @mock.patch("navi.publisher.socket")
    @mock.patch("navi.publisher.datetime")
    @mock.patch("navi.publisher.uuid4")
    def test__build_message_properties(self, uuid4_mock, datetime_mock, socket_mock):
        """
        When `NaviPublisher._build_message_properties` is called, a BasicProperties object should be
        created, containing a headers dict.
        """
        properties = self.publisher._build_message_properties()

        uuid4_mock.assert_called_once()
        datetime_mock.utcnow.assert_called_once()
        socket_mock.getfqdn.assert_called_once()
        self.assertTrue(
            isinstance(properties, BasicProperties),
            msg=f"Expected: {BasicProperties}, obtained: {type(properties)}",
        )
        self.assertTrue(any(properties.headers), msg="Missing headers!")

    @mock.patch.object(NaviPublisher, "_publish_message")
    @mock.patch("navi.publisher.json")
    def test_publish_json_dumps_error(self, json_mock, publish_message_mock):
        json_mock.dumps.side_effect = TypeError()
        message = {"hello": "world"}

        self.publisher.publish(message)

        self.publisher.logger.error.assert_called_once()
        publish_message_mock.assert_not_called()

    @mock.patch.object(NaviPublisher, "_init_connection")
    @mock.patch.object(NaviPublisher, "_build_message_properties")
    def test_publish_message(self, build_message_properties_mock, init_connection_mock):
        message_properties = build_message_properties_mock.return_value
        connection = init_connection_mock.return_value
        channel = connection.channel.return_value
        body = "{'hello': 'world'}"

        self.publisher._publish_message(body)

        channel.exchange_declare.assert_called_once_with(
            exchange=config.NAVI_EXCHANGE, exchange_type=config.NAVI_EXCHANGE_TYPE, durable=True,
        )
        channel.basic_publish.assert_called_once_with(
            exchange=config.NAVI_EXCHANGE,
            routing_key=self.publisher._routing_key,
            properties=message_properties,
            body=body,
        )
        connection.close.assert_called_once()
        self.publisher.logger.error.assert_not_called()

    @mock.patch.object(NaviPublisher, "_init_connection")
    @mock.patch.object(NaviPublisher, "_build_message_properties")
    def test_publish_message_amqp_error_connection_set(
        self, build_message_properties_mock, init_connection_mock
    ):
        """If an AMQPError is raised when `_publish_message` is called, and the connection is set,
        then it should be closed and logger.error should be called.
        
        Args:
            build_message_properties_mock ([type]): [description]
            init_connection_mock ([type]): [description]
        """
        message_properties = build_message_properties_mock.return_value
        connection = init_connection_mock.return_value
        channel = connection.channel.return_value
        body = "{'hello': 'world'}"
        channel.basic_publish.side_effect = AMQPError()

        self.publisher._publish_message(body)

        channel.exchange_declare.assert_called_once_with(
            exchange=config.NAVI_EXCHANGE, exchange_type=config.NAVI_EXCHANGE_TYPE, durable=True,
        )
        channel.basic_publish.assert_called_once_with(
            exchange=config.NAVI_EXCHANGE,
            routing_key=self.publisher._routing_key,
            properties=message_properties,
            body=body,
        )
        connection.close.assert_called_once()
        self.publisher.logger.error.assert_called_once()

    @mock.patch.object(NaviPublisher, "_init_connection")
    @mock.patch.object(NaviPublisher, "_build_message_properties")
    def test_publish_message_connection_error(
        self, build_message_properties_mock, init_connection_mock
    ):
        """If an AMQPError is raised when `_publish_message` is called, and the connection is not
        set, then it shouldn't be closed and logger.error should be called.
        
        Args:
            build_message_properties_mock ([type]): [description]
            init_connection_mock ([type]): [description]
        """
        message_properties = build_message_properties_mock.return_value
        init_connection_mock.side_effect = AMQPError()
        body = "{'hello': 'world'}"

        self.publisher._publish_message(body)

        self.publisher.logger.error.assert_called_once()


class TestPublish(TestCase):
    """Test cases for the publisher.publish function."""

    @mock.patch.object(NaviPublisher, "publish")
    @mock.patch.object(NaviPublisher, "_init_connection_params")
    def test_publish(self, init_connection_params_mock, publish_mock):
        """When `publisher.publish` is called with a `message` argument, a NaviPublisher should be
        initialized, and its `publish` instance method should be called with `message`.
        """
        message = {"hello": "world"}
        routing_key = "some.routing.key"
        publish(routing_key=routing_key, message=message)

        init_connection_params_mock.assert_called_once()
        publish_mock.assert_called_once()
