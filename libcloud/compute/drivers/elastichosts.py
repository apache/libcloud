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

"""
ElasticHosts Driver
"""

from libcloud.compute.types import Provider
from libcloud.compute.drivers.elasticstack import ElasticStackBaseNodeDriver
from libcloud.compute.drivers.elasticstack import ElasticStackBaseConnection


# API end-points
API_ENDPOINTS = {
    'uk-1': {
        'name': 'London Peer 1',
        'country': 'United Kingdom',
        'host': 'api-lon-p.elastichosts.com'
    },
    'uk-2': {
        'name': 'London BlueSquare',
        'country': 'United Kingdom',
        'host': 'api-lon-b.elastichosts.com'
    },
    'us-1': {
        'name': 'San Antonio Peer 1',
        'country': 'United States',
        'host': 'api-sat-p.elastichosts.com'
    },
    'us-2': {
        'name': 'Los Angeles Peer 1',
        'country': 'United States',
        'host': 'api-lax-p.elastichosts.com'
    },
    'us-3': {
        'name': 'San Jose (Silicon Valley)',
        'country': 'United States',
        'host': 'api-sjc-c.elastichosts.com'
    },
    'ca-1': {
        'name': 'Toronto Peer 1',
        'country': 'Canada',
        'host': 'api-tor-p.elastichosts.com'
    },
    'au-1': {
        'name': 'Sydney',
        'country': 'Australia',
        'host': 'api-syd-v.elastichosts.com'
    },
    'cn-1': {
        'name': 'Hong Kong',
        'country': 'China',
        'host': 'api-hkg-e.elastichosts.com'
    }
}

# Default API end-point for the base connection class.
DEFAULT_ENDPOINT = 'us-1'

# Retrieved from http://www.elastichosts.com/cloud-hosting/api
STANDARD_DRIVES = {
    '38df0986-4d85-4b76-b502-3878ffc80161': {
        'uuid': '38df0986-4d85-4b76-b502-3878ffc80161',
        'description': 'CentOS Linux 5.5',
        'size_gunzipped': '3GB',
        'supports_deployment': True,
    },
    '980cf63c-f21e-4382-997b-6541d5809629': {
        'uuid': '980cf63c-f21e-4382-997b-6541d5809629',
        'description': 'Debian Linux 5.0',
        'size_gunzipped': '1GB',
        'supports_deployment': True,
    },
    'aee5589a-88c3-43ef-bb0a-9cab6e64192d': {
        'uuid': 'aee5589a-88c3-43ef-bb0a-9cab6e64192d',
        'description': 'Ubuntu Linux 10.04',
        'size_gunzipped': '1GB',
        'supports_deployment': True,
    },
    '62f512cd-82c7-498e-88d8-a09ac2ef20e7': {
        'uuid': '62f512cd-82c7-498e-88d8-a09ac2ef20e7',
        'description': 'Ubuntu Linux 12.04',
        'size_gunzipped': '1GB',
        'supports_deployment': True,
    },
    'b9d0eb72-d273-43f1-98e3-0d4b87d372c0': {
        'uuid': 'b9d0eb72-d273-43f1-98e3-0d4b87d372c0',
        'description': 'Windows Web Server 2008',
        'size_gunzipped': '13GB',
        'supports_deployment': False,
    },
    '30824e97-05a4-410c-946e-2ba5a92b07cb': {
        'uuid': '30824e97-05a4-410c-946e-2ba5a92b07cb',
        'description': 'Windows Web Server 2008 R2',
        'size_gunzipped': '13GB',
        'supports_deployment': False,
    },
    '9ecf810e-6ad1-40ef-b360-d606f0444671': {
        'uuid': '9ecf810e-6ad1-40ef-b360-d606f0444671',
        'description': 'Windows Web Server 2008 R2 + SQL Server',
        'size_gunzipped': '13GB',
        'supports_deployment': False,
    },
    '10a88d1c-6575-46e3-8d2c-7744065ea530': {
        'uuid': '10a88d1c-6575-46e3-8d2c-7744065ea530',
        'description': 'Windows Server 2008 Standard R2',
        'size_gunzipped': '13GB',
        'supports_deployment': False,
    },
    '2567f25c-8fb8-45c7-95fc-bfe3c3d84c47': {
        'uuid': '2567f25c-8fb8-45c7-95fc-bfe3c3d84c47',
        'description': 'Windows Server 2008 Standard R2 + SQL Server',
        'size_gunzipped': '13GB',
        'supports_deployment': False,
    },
}


class ElasticHostsBaseConnection(ElasticStackBaseConnection):
    host = API_ENDPOINTS[DEFAULT_ENDPOINT]['host']


class ElasticHostsBaseNodeDriver(ElasticStackBaseNodeDriver):
    type = Provider.ELASTICHOSTS
    api_name = 'elastichosts'
    name = 'ElasticHosts'
    website = 'http://www.elastichosts.com/'
    connectionCls = ElasticHostsBaseConnection
    features = {"create_node": ["generates_password"]}
    _standard_drives = STANDARD_DRIVES


class ElasticHostsUK1Connection(ElasticStackBaseConnection):
    """
    Connection class for the ElasticHosts driver for
    the London Peer 1 end-point
    """

    host = API_ENDPOINTS['uk-1']['host']


class ElasticHostsUK1NodeDriver(ElasticHostsBaseNodeDriver):
    """
    ElasticHosts node driver for the London Peer 1 end-point
    """
    connectionCls = ElasticHostsUK1Connection


class ElasticHostsUK2Connection(ElasticStackBaseConnection):
    """
    Connection class for the ElasticHosts driver for
    the London Bluesquare end-point
    """
    host = API_ENDPOINTS['uk-2']['host']


class ElasticHostsUK2NodeDriver(ElasticHostsBaseNodeDriver):
    """
    ElasticHosts node driver for the London Bluesquare end-point
    """
    connectionCls = ElasticHostsUK2Connection


class ElasticHostsUS1Connection(ElasticStackBaseConnection):
    """
    Connection class for the ElasticHosts driver for
    the San Antonio Peer 1 end-point
    """
    host = API_ENDPOINTS['us-1']['host']


class ElasticHostsUS1NodeDriver(ElasticHostsBaseNodeDriver):
    """
    ElasticHosts node driver for the San Antonio Peer 1 end-point
    """
    connectionCls = ElasticHostsUS1Connection


class ElasticHostsUS2Connection(ElasticStackBaseConnection):
    """
    Connection class for the ElasticHosts driver for
    the Los Angeles Peer 1 end-point
    """
    host = API_ENDPOINTS['us-2']['host']


class ElasticHostsUS2NodeDriver(ElasticHostsBaseNodeDriver):
    """
    ElasticHosts node driver for the Los Angeles Peer 1 end-point
    """
    connectionCls = ElasticHostsUS2Connection


class ElasticHostsCA1Connection(ElasticStackBaseConnection):
    """
    Connection class for the ElasticHosts driver for
    the Toronto Peer 1 end-point
    """
    host = API_ENDPOINTS['ca-1']['host']


class ElasticHostsCA1NodeDriver(ElasticHostsBaseNodeDriver):
    """
    ElasticHosts node driver for the Toronto Peer 1 end-point
    """
    connectionCls = ElasticHostsCA1Connection
