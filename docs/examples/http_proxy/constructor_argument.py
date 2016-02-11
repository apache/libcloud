from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

PROXY_URL_NO_AUTH_1 = 'http://<proxy hostname 1>:<proxy port 2>'

cls = get_driver(Provider.RACKSPACE)
driver = cls('username', 'api key', region='ord',
             http_proxy=PROXY_URL_NO_AUTH_1)
