#!/usr/bin/env python
#
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

#
# This example provides both a running script (invoke from command line)
# and an importable module one can play with in Interactive Mode.
#
# See docstrings for usage examples.
#

try:
    import secrets
except:
    pass
import sys; sys.path.append('..')

from libcloud.types import Provider
from libcloud.providers import get_driver

from pprint import pprint

def main(argv):
    """Main EC2 Demo

    When invoked from the command line, it will connect using secrets.py
    (see secrets.py.dist for setup instructions), and perform the following
    tasks:

    - List current nodes
    - List available images (up to 10)
    - List available sizes (up to 10)
    """
    # Load EC2 driver
    EC2Driver = get_driver(Provider.EC2_US_EAST)

    # Instantiate with Access ID and Secret Key
    # (see secrets.py.dist)
    try:
        ec2 = EC2Driver(secrets.EC2_ACCESS_ID, secrets.EC2_SECRET_KEY)
        print ">> Loading nodes..."
        nodes = ec2.list_nodes()
        pprint(nodes)
    except NameError, e:
        print ">> Fatal Error: %s" % e
        print "   (Hint: modify secrets.py.dist)"
        return 1
    except Exception, e:
        print ">> Fatal error: %s" % e
        return 1
    
    print ">> Loading images... (showing up to 10)"
    images = ec2.list_images()
    pprint(images[:10])

    print ">> Loading sizes... (showing up to 10)"
    sizes = ec2.list_sizes()
    pprint(sizes[:10])

    return 0

def get_ec2(**kwargs):
    """An easy way to play with the EC2 Driver in Interactive Mode

    # Load credentials from secrets.py
    >>> from ec2demo import get_ec2
    >>> ec2 = get_ec2()

    # Or, provide credentials
    >>> from ec2demo import get_ec2
    >>> ec2 = get_ec2(access_id='xxx', secret_key='yyy')

    # Do things
    >>> ec2.load_nodes()
    >>> images = ec2.load_images()
    >>> sizes = ec2.load_sizes()
    """
    access_id = kwargs.get('access_id', secrets.EC2_ACCESS_ID)
    secret_key = kwargs.get('secret_key', secrets.EC2_SECRET_KEY)
    
    EC2Driver = get_driver(Provider.EC2_US_EAST)
    return EC2Driver(access_id, secret_key)

def create_demo(ec2):
    """Create EC2 Node Demo

    >>> from ec2demo import get_ec2, create_demo
    >>> ec2 = get_ec2()
    >>> node = create_demo(ec2)
    >>> node
    <Node: uuid=9d1..., name=i-7b1fa910, state=3, public_ip=[''], ...>

    And to destroy the node:

    >>> node.destroy()

    If you've accidentally quit and need to destroy the node:

    >>> from ec2demo import get_ec2
    >>> nodes = ec2.list_nodes()
    >>> nodes[0].destroy() # assuming it's the first node
    """
    images = ec2.list_images()
    image = [image for image in images if 'ami' in image.id][0]
    sizes = ec2.list_sizes()
    size = sizes[0]

    # Note, name is ignored by EC2
    node = ec2.create_node(name='create_image_demo',
                           image=image,
                           size=size)
    return node

if __name__ == '__main__':
    sys.exit(main(sys.argv))
