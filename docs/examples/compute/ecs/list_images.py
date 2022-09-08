import pprint

from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

ECSDriver = get_driver(Provider.ALIYUN_ECS)

region = "cn-hangzhou"
access_key_id = "CHANGE IT"
access_key_secret = "CHANGE IT"

driver = ECSDriver(access_key_id, access_key_secret, region=region)

images = driver.list_images()
pprint.pprint(images)
