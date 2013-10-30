from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

CloudFrames = get_driver(Provider.CLOUDFRAMES)
driver = CloudFrames(key='admin', secret='admin', secure=False,
                     host='cloudframes', port=80)
