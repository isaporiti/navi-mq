"""
This is a console script used as support for the development of this project.

The code stored in the demo folder must not be distributed and it is also not a real part of the
project itself so it should not be checked in neither violations evaluation nor unitary testing.

The documentation and conventions rules can be ommited here, nevertheless, we encourage to follow
them even in the testing/demo scripts.
"""
import navi
from navi.listener import NaviListener


def hello_world(headers: dict, message: dict):
    name = message.get("name")
    listener_name = headers.get("listener_name")
    print(f"Hey {name}! Listening from {listener_name}\n")


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
