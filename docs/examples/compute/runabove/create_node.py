from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

RunAbove = get_driver(Provider.RUNABOVE)
driver = RunAbove('yourAppKey', 'yourAppSecret', 'YourConsumerKey')

image = [i for i in driver.list_images() if 'Debian 8' == i.name][0]
size = [s for s in driver.list_sizes() if s.name == 'ra.s'][0]
location = [l for l in driver.list_locations() if l.id == 'SBG-1'][0]

node = driver.create_node(name='yournode', size=size, image=image,
                          location=location)
