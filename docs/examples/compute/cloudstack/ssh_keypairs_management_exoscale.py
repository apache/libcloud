import os
from pprint import pprint

from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

cls = get_driver(Provider.EXOSCALE)
driver = cls('api key', 'api secret key')

# Create a new key pair. Most providers will return generated private key in
# the response which can be accessed at key_pair.private_key
key_pair = driver.create_key_pair(name='test-key-pair-1')
pprint(key_pair)

# Import an existing public key from a file. If you have public key as a
# string, you can use import_key_pair_from_string method instead.
key_file_path = os.path.expanduser('~/.ssh/id_rsa_test.pub')
key_pair = driver.import_key_pair_from_file(name='test-key-pair-2',
                                            key_file_path=key_file_path)
pprint(key_pair)

# Retrieve information about previously created key pair
key_pair = driver.get_key_pair(name='test-key-pair-1')
pprint(key_pair)

# Delete a key pair we have previously created
status = driver.delete_key_pair(key_pair=key_pair)
pprint(status)
