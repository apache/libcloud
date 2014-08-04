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

__all__ = [
    'Provider'
]


class Provider(object):
    """
    Defines for each of the supported providers

    :cvar DUMMY: Example provider
    :cvar OPENSTACK_NOVA: Nova based networking
    :cvar OPENSTACK_QUANTUM: OpenStack Quantum Networking
    :cvar OPENSTACK_NEUTRON: OpenStack Quantum Networking
    :cvar HPCLOUD: HP Cloud driver based on the OpenStack Neutron.
    """
    DUMMY = 'dummy'

    # OpenStack based providers
    OPENSTACK_NOVA = 'openstack_nova'
    OPENSTACK_QUANTUM = 'openstack_quantum'
    OPENSTACK_NEUTRON = 'openstack_neutron'
    HPCLOUD = 'hpcloud'
