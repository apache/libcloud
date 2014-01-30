from __future__ import with_statement

import os

from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

EC2_ACCESS_ID = 'your access id'
EC2_SECRET_KEY = 'your secret key'

Driver = get_driver(Provider.EC2)
conn = Driver(EC2_ACCESS_ID, EC2_SECRET_KEY)

key_file_path = os.path.expanduser('~/.ssh/id_rsa_my_key_pair_1.pub')

with open(key_file_path, 'r') as fp:
    key_material = fp.read()

key_pair = conn.import_key_pair_from_string(name='my_key',
                                            key_material=key_material)
