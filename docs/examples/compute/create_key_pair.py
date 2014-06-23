from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

EC2_ACCESS_ID = 'your access id'
EC2_SECRET_KEY = 'your secret key'

Driver = get_driver(Provider.EC2)
conn = Driver(EC2_ACCESS_ID, EC2_SECRET_KEY)

key_pair = conn.create_key_pair(name='my-key-pair-1')

# Private key which provided generated on your behalf should be available
# through key_pair.private_key attribute.
