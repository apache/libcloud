from pprint import pprint

from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

HTTP_PROXY_URL_NO_AUTH_1 = "http://<proxy hostname 1>:<proxy port 2>"
HTTP_PROXY_URL_NO_AUTH_2 = "http://<proxy hostname 1>:<proxy port 2>"
HTTP_PROXY_URL_BASIC_AUTH = "http://<user>:<pass>@<proxy hostname>:<port>"

cls = get_driver(Provider.RACKSPACE)
driver = cls("username", "api key", region="ord")

# Use proxy 1 for this request
driver.connection.connection.set_http_proxy(proxy_url=HTTP_PROXY_URL_NO_AUTH_1)
pprint(driver.list_nodes())

# Use proxy 2 for this request
driver.connection.connection.set_http_proxy(proxy_url=HTTP_PROXY_URL_NO_AUTH_2)
pprint(driver.list_nodes())
