from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

HTTP_PROXY_URL_NO_AUTH_1 = "http://<proxy hostname 1>:<proxy port 2>"
HTTPS_PROXY_URL_NO_AUTH_1 = "https://<proxy hostname 1>:<proxy port 2>"

cls = get_driver(Provider.RACKSPACE)

# 1. Use http proxy
driver = cls("username", "api key", region="ord", proxy_url=HTTP_PROXY_URL_NO_AUTH_1)

# 2. Use https proxy
driver = cls("username", "api key", region="ord", proxy_url=HTTPS_PROXY_URL_NO_AUTH_1)
