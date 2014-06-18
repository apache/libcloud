from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

cls = get_driver(Provider.EC2, region='us-east-i1')
driver = cls('access key', 'secret key')

volume = driver.create_volume(size=100, name='Test GP volume',
                              ex_volume_type='g2')
