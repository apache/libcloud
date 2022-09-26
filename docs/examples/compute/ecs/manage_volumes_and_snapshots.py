import time

from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

ECSDriver = get_driver(Provider.ALIYUN_ECS)

region = "cn-hangzhou"
access_key_id = "CHANGE IT"
access_key_secret = "CHANGE IT"

driver = ECSDriver(access_key_id, access_key_secret, region=region)

node = driver.list_nodes()[0]
zone = driver.ex_list_zones()[0]

new_volume = driver.create_volume(
    size=5,
    name="data_volume1",
    ex_zone_id=zone.id,
    ex_disk_category=driver.disk_categories.CLOUD,
)
driver.attach_volume(node, new_volume)
# Wait 10s for attaching finished
time.sleep(10)

snapshot = driver.create_volume_snapshot(new_volume, name="data_volume1_snapshot1")
