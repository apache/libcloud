from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

Ovh = get_driver(Provider.OVH)
driver = Ovh('yourAppKey', 'yourAppSecret', 'yourProjectId', 'yourConsumerKey')

location = [l for l in driver.list_locations() if l.id == 'SBG1'][0]
image = [i for i in driver.list_images() if 'Debian 8' == i.name][0]
size = [s for s in driver.list_sizes() if s.name == 'vps-ssd-1'][0]

node = driver.create_node(name='yournode', size=size, image=image,
                          location=location)
