from pprint import pprint

from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

PROXY_URL_NO_AUTH = 'http://<proxy hostname>:<proxy port>'
PROXY_URL_BASIC_AUTH = 'http://<user>:<pass>@<proxy hostname>:<proxy port>'

cls = get_driver(Provider.RACKSPACE)
driver = cls('username', 'api key', region='ord')
driver.connection.set_http_proxy(proxy_url=PROXY_URL_NO_AUTH)
pprint(driver.list_nodes())
