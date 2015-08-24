from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

RunAbove = get_driver(Provider.RUNABOVE)
driver = RunAbove('yourAppKey', 'yourAppSecret', 'YourConsumerKey')

location = [l for l in driver.list_locations() if l.id == 'SBG-1'][0]
node = driver.list_nodes()[0]

volume = driver.create_volume(size=10, location=location)
driver.attach_volume(node=node, volume=volume)
