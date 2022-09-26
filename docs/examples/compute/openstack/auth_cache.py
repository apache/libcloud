from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver
from libcloud.common.openstack_identity import OpenStackAuthenticationCache


class MyAuthenticationCache(OpenStackAuthenticationCache):
    pass  # implement...


auth_cache = MyAuthenticationCache(...)

OpenStack = get_driver(Provider.OPENSTACK)
driver = OpenStack(
    "your_auth_username",
    "your_auth_password",
    ex_force_auth_url="http://192.168.1.101:5000",
    ex_force_auth_version="3.x_password",
    ex_auth_cache=auth_cache,
)

driver.list_sizes()
