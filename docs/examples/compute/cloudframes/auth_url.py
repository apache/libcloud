from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

CloudFrames = get_driver(Provider.CLOUDFRAMES)
driver = CloudFrames(url="http://admin:admin@cloudframes:80/appserver/xmlrpc")
