from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

cls = get_driver(Provider.CLOUDSIGMA)
driver = cls("username", "password", region="zrh", api_version="2.0")

node = driver.list_nodes()[0]

vnc_url = driver.ex_open_vnc_tunnel(node=node)
vnc_password = node.extra["vnc_password"]

values = {"url": vnc_url, "password": vnc_password}
print("URL: %(url)s, Password: %(password)s" % values)

# When you are done
driver.ex_close_vnc_tunnel(node=node)
