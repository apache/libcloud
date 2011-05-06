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

from pprint import pprint
import traceback

from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

def main():
    """Main OpenStack Demo

    When invoked from the command line, it will connect using NOVA_API_KEY
    NOVA_USERNAME NOVA_URL environment variables, and perform the following
    tasks:

    - List current nodes
    - List available images (up to 10)
    - List available sizes (up to 10)
    - Create a single instance
    - Destroy it
    """

    OpenStackDriver = get_driver(Provider.OPENSTACK1_1)

    import os
    try:
        nova_user_name = os.environ['NOVA_USERNAME']
        nova_api_key = os.environ['NOVA_API_KEY']
        nova_url=os.environ['NOVA_URL']
    except KeyError:
        print 'cloud access point definition is not provided!'
        print 'Hint define N0VA_API_KEY NOVA_USERNAME NOVA_URL'
        return 1

    try:
        open_stack = OpenStackDriver(user_name=nova_user_name, api_key= nova_api_key , url=nova_url)
        print ">> Loading nodes..."
        nodes = open_stack.list_nodes()
        pprint(nodes)
    except Exception:
        print traceback.print_exc()
        return 1

    print ">> Loading images... (showing up to 10)"
    images = open_stack.list_images()
    pprint(images[:10])

    print ">> Loading sizes... (showing up to 10)"
    sizes = open_stack.list_sizes()
    pprint(sizes[:10])

    instance = open_stack.create_node(name='create_image_demo',
                           image=images[0],
                           size=sizes[0])
    #TODO: add check status of instance
    instance.destroy()
    return 0

if __name__ == '__main__':
    main()

  