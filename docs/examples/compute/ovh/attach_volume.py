from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

Ovh = get_driver(Provider.OVH)
driver = Ovh("yourAppKey", "yourAppSecret", "youProjectId", "yourConsumerKey")

location = [loc for loc in driver.list_locations() if loc.id == "SBG1"][0]
node = driver.list_nodes()[0]

volume = driver.create_volume(size=10, location=location)
driver.attach_volume(node=node, volume=volume)
