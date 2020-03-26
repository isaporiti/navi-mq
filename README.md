# Navi MQ

Navi is a library intended to wrap ![Pika client](https://pika.readthedocs.io/en/stable/) to allow easier communication with AMQP brokers.

Its based on providing the user two basic functionalities: `publish` and `listen`. Navi handles AMQP connection management, exchange and queue declarations and bindings, message serialization and headers management so its user doesn't have to and therefore just focus on listeners definition and message publishing.

Navi can be configured through environment variables to customize its management. The following items are accepted:

- `NAVI_AMQP_USERNAME`: Username to establish the connection with AMQP broker.
- `NAVI_AMQP_PASSWORD`: Password to establish the connection with AMQP broker.
- `NAVI_AMQP_HOST`: AMQP host address.
- `NAVI_AMQP_PORT`: AMQP port to be used to connect.
- `NAVI_EXCHANGE`: The name of the exchange to be used. 
    - Defaults to: `"amq.topic"`.
    - Accepted values: `"amq.direct"`, `"amq.fanout"`, `"amq.topic"`, or a custom user name.
- `NAVI_EXCHANGE_TYPE`: The exchange type to be used.
    - Defaults to: `"topic"`
    - Accepted values: `"direct"`, `"fanout"`, `"topic"`.

The following example, extracted from `demo/publish_listen_demo.py`, shows how to both declare listeners and how to publish messages:

```python
def hello_world(headers: dict, message: dict):
    name = message.get("name", "world")
    listener_name = headers.get("listener_name")
    print(f"Hello {name}! Listening from {listener_name}\n")


if __name__ == "__main__":
    # a listener can be set up through the navi.listen function, like this:
    navi.listen(queue_name="from_listen_func", routing_key="demo.hello_world", callback=hello_world)

    # also, listeners can be initialized and told to listen:
    listener = NaviListener(
        queue_name="from_initialized_listener", routing_key="demo.hello_world", callback=hello_world
    )
    listener.listen()

    for name in ("Sonic", "Tails", "Knuckles"):
        message = {"name": name}
        navi.publish(routing_key="demo.hello_world", message=message)
```

## FAQs
- _Why does **NaviPublisher** connects to the broker with **BlockingConnection**, while **NaviListener** does with **SelectConnection**?_ [anchor])=

    Basically, because that's how it's suggested by [pika docs](https://pika.readthedocs.io/en/stable/examples/comparing_publishing_sync_async.html#comparing-message-publishing-with-blockingconnection-and-selectconnection). `BlockingConnection` is intended to be used for short living connections, as is the case with publishing. They're easier to set up, and don't need any callbacks to execute, when events like the channel being opened occur.
    `SelectConnection`, in turn, is better for the case of a long living connection, and when we need to set up callbacks for events like channel opening, queue declaration, etc.