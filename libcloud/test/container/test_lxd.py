import sys

from libcloud.test import unittest

from libcloud.container.types import Provider
from libcloud.container.providers import get_driver

from libcloud.container.base import ContainerImage

from libcloud.container.drivers.lxd import LXDContainerDriver

from libcloud.utils.py3 import httplib
from libcloud.test.file_fixtures import ContainerFileFixtures
from libcloud.test import MockHttp


class LXDContainerDriverTestCase(unittest.TestCase):

    """
    Unit tests for LXDContainerDriver
    """

    @staticmethod
    def get_lxd_connection():

        # get the libcloud LXD driver
        lxd_driver = get_driver(Provider.LXD)

        # LXD host change accordingly
        host_lxd = 'https://192.168.2.4'

        # port that LXD server is listening at
        # change this according to your configuration
        port_id = 8443

        # acquire the connection.
        # certificates should  have been  added to the LXD server
        # here we assume they are on the same directory change
        # accordingly
        conn = lxd_driver(key='', secret='', secure=False,
                          host=host_lxd, port=port_id, key_file='lxd.key', cert_file='lxd.crt')

        return conn



    """
    Test Scenario: Application attempts to generate an action that is not in LXD_API_STATE_ACTIONS
    Expected Output: InvalidArgument exception should be thrown
    """
    def test_invalid_action_given(self):

        conn = LXDContainerDriverTestCase.get_lxd_connection()

        with ValueError as e:
            conn._do_container_action(container=None, action="INVALID",
                                  timeout=None, stateful=None, force=None)
            self.assertEqual(str(e), "Invalid action specified")


if __name__ == '__main__':
    sys.exit(unittest.main())