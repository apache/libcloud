import pytest
import libcloud
from libcloud import loadbalancer
from libcloud.common.nttcis import NttCisAPIException


def test_server_clone_to_image(compute_driver):
    node = compute_driver.ex_get_node_by_id('040fefdb-78be-4b17-8ef9-86820bad67d9 ')
    result = compute_driver.ex_clone_node_to_image(node, 'sdk_test_image', image_description='A test image for libcloud')
    assert result is True
