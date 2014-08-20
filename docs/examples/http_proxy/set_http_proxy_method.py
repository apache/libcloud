from pprint import pprint

from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

PROXY_URL = 'http://<proxy hostname>:<proxy port>'

cls = get_driver(Provider.RACKSPACE)
driver = cls('username', 'api key', region='ord')
driver.connection.set_http_proxy(proxy_url=PROXY_URL)

pprint(driver.list_nodes())
