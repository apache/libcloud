from pprint import pprint

# pylint: disable=import-error
from twisted.internet import defer, reactor, threads

from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver


@defer.inlineCallbacks
def create_node(name):
    node = yield threads.deferToThread(_thread_create_node, name=name)
    pprint(node)
    reactor.stop()


def _thread_create_node(name):
    Driver = get_driver(Provider.RACKSPACE)
    conn = Driver("username", "api key")
    image = conn.list_images()[0]
    size = conn.list_sizes()[0]
    node = conn.create_node(name=name, image=image, size=size)
    return node


def stop(*args, **kwargs):
    reactor.stop()


d = create_node(name="my-lc-node")
d.addCallback(stop)  # pylint: disable=no-member
d.addErrback(stop)  # pylint: disable=no-member

reactor.run()
