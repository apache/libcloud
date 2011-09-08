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
except ImportError:
    secrets = None

import sys; sys.path.append('..')

from libcloud.compute.types import Provider
from libcloud.providers import get_driver

from pprint import pprint

def main(argv):
    """Main Compute Demo

    When invoked from the command line, it will connect using secrets.py
    (see secrets.py.dist for setup instructions), and perform the following
    tasks:

    - List current nodes
    - List available images (up to 10)
    - List available sizes (up to 10)
    """
    driver = get_demo_driver()

    try:
        print ">> Loading nodes..."
        nodes = driver.list_nodes()
        pprint(nodes)
    except NameError, e:
        print ">> Fatal Error: %s" % e
        print "   (Hint: modify secrets.py.dist)"
        return 1
    except Exception, e:
        print ">> Fatal error: %s" % e
        return 1

    print ">> Loading images... (showing up to 10)"
    images = driver.list_images()
    pprint(images[:10])

    print ">> Loading sizes... (showing up to 10)"
    sizes = driver.list_sizes()
    pprint(sizes[:10])

    return 0

def get_demo_driver(provider_name='RACKSPACE', *args, **kwargs):
    """An easy way to play with a driver interactively.

    # Load credentials from secrets.py:
    >>> from compute_demo import get_demo_driver
    >>> driver = get_demo_driver('RACKSPACE')

    # Or, provide credentials:
    >>> from compute_demo import get_demo_driver
    >>> driver = get_demo_driver('RACKSPACE', 'username', 'api_key')
    # Note that these parameters vary by driver ^^^

    # Do things like the demo:
    >>> driver.load_nodes()
    >>> images = driver.load_images()
    >>> sizes = driver.load_sizes()
    
    # And maybe do more than that:
    >>> node = driver.create_node(
            name='my_first_node',
            image=images[0],
            size=sizes[0],
        )
    >>> node.destroy()
    """
    provider_name = provider_name.upper()

    DriverClass = get_driver(getattr(Provider, provider_name))

    if not args:
        args = getattr(secrets, provider_name + '_PARAMS', ())
    if not kwargs:
        kwargs = getattr(secrets, provider_name + '_KEYWORD_PARAMS', {})

    return DriverClass(*args, **kwargs)

if __name__ == '__main__':
    sys.exit(main(sys.argv))
