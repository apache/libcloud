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
Vultr Driver
"""
import time
from functools import update_wrapper

from libcloud.common.base import ConnectionKey, JsonResponse
from libcloud.common.types import InvalidCredsError
from libcloud.common.types import LibcloudError
from libcloud.common.types import ServiceUnavailableError
from libcloud.compute.base import Node, NodeImage, NodeSize, NodeLocation
from libcloud.compute.base import NodeDriver
from libcloud.compute.types import Provider, NodeState
from libcloud.utils.iso8601 import parse_date
from libcloud.utils.py3 import httplib
from libcloud.utils.py3 import urlencode

# For matching region by id
VULTR_COMPUTE_INSTANCE_LOCATIONS = {
    "1": {
        "DCID": "1",
        "name": "New Jersey",
        "country": "US",
        "continent": "North America",
        "state": "NJ",
        "regioncode": "EWR"
    },
    "2": {
        "DCID": "2",
        "name": "Chicago",
        "country": "US",
        "continent": "North America",
        "state": "IL",
        "regioncode": "ORD"
    },
    "3": {
        "DCID": "3",
        "name": "Dallas",
        "country": "US",
        "continent": "North America",
        "state": "TX",
        "regioncode": "DFW"
    },
    "4": {
        "DCID": "4",
        "name": "Seattle",
        "country": "US",
        "continent": "North America",
        "state": "WA",
        "regioncode": "SEA"
    },
    "5": {
        "DCID": "5",
        "name": "Los Angeles",
        "country": "US",
        "continent": "North America",
        "state": "CA",
        "regioncode": "LAX"
    },
    "6": {
        "DCID": "6",
        "name": "Atlanta",
        "country": "US",
        "continent": "North America",
        "state": "GA",
        "regioncode": "ATL"
    },
    "7": {
        "DCID": "7",
        "name": "Amsterdam",
        "country": "NL",
        "continent": "Europe",
        "state": "",
        "regioncode": "AMS"
    },
    "8": {
        "DCID": "8",
        "name": "London",
        "country": "GB",
        "continent": "Europe",
        "state": "",
        "regioncode": "LHR"
    },
    "9": {
        "DCID": "9",
        "name": "Frankfurt",
        "country": "DE",
        "continent": "Europe",
        "state": "",
        "regioncode": "FRA"
    },
    "12": {
        "DCID": "12",
        "name": "Silicon Valley",
        "country": "US",
        "continent": "North America",
        "state": "CA",
        "regioncode": "SJC"
    },
    "19": {
        "DCID": "19",
        "name": "Sydney",
        "country": "AU",
        "continent": "Australia",
        "state": "",
        "regioncode": "SYD"
    },
    "22": {
        "DCID": "22",
        "name": "Toronto",
        "country": "CA",
        "continent": "North America",
        "state": "",
        "regioncode": "YTO"
    },
    "24": {
        "DCID": "24",
        "name": "Paris",
        "country": "FR",
        "continent": "Europe",
        "state": "",
        "regioncode": "CDG"
    },
    "25": {
        "DCID": "25",
        "name": "Tokyo",
        "country": "JP",
        "continent": "Asia",
        "state": "",
        "regioncode": "NRT"
    },
    "34": {
        "DCID": "34",
        "name": "Seoul",
        "country": "KR",
        "continent": "Asia",
        "state": "",
        "regioncode": "ICN"
    },
    "39": {
        "DCID": "39",
        "name": "Miami",
        "country": "US",
        "continent": "North America",
        "state": "FL",
        "regioncode": "MIA"
    },
    "40": {
        "DCID": "40",
        "name": "Singapore",
        "country": "SG",
        "continent": "Asia",
        "state": "",
        "regioncode": "SGP"
    }
}
# For matching image by id
VULTR_COMPUTE_INSTANCE_IMAGES = {
    "127": {
        "OSID": 127,
        "name": "CentOS 6 x64",
        "arch": "x64",
        "family": "centos",
        "windows": False
    },
    "147": {
        "OSID": 147,
        "name": "CentOS 6 i386",
        "arch": "i386",
        "family": "centos",
        "windows": False
    },
    "167": {
        "OSID": 167,
        "name": "CentOS 7 x64",
        "arch": "x64",
        "family": "centos",
        "windows": False
    },
    "381": {
        "OSID": 381,
        "name": "CentOS 7 SELinux x64",
        "arch": "x64",
        "family": "centos",
        "windows": False
    },
    "362": {
        "OSID": 362,
        "name": "CentOS 8 x64",
        "arch": "x64",
        "family": "centos",
        "windows": False
    },
    "401": {
        "OSID": 401,
        "name": "CentOS 8 Stream x64",
        "arch": "x64",
        "family": "centos",
        "windows": False
    },
    "215": {
        "OSID": 215,
        "name": "Ubuntu 16.04 x64",
        "arch": "x64",
        "family": "ubuntu",
        "windows": False
    },
    "216": {
        "OSID": 216,
        "name": "Ubuntu 16.04 i386",
        "arch": "i386",
        "family": "ubuntu",
        "windows": False
    },
    "270": {
        "OSID": 270,
        "name": "Ubuntu 18.04 x64",
        "arch": "x64",
        "family": "ubuntu",
        "windows": False
    },
    "387": {
        "OSID": 387,
        "name": "Ubuntu 20.04 x64",
        "arch": "x64",
        "family": "ubuntu",
        "windows": False
    },
    "194": {
        "OSID": 194,
        "name": "Debian 8 i386 (jessie)",
        "arch": "i386",
        "family": "debian",
        "windows": False
    },
    "244": {
        "OSID": 244,
        "name": "Debian 9 x64 (stretch)",
        "arch": "x64",
        "family": "debian",
        "windows": False
    },
    "352": {
        "OSID": 352,
        "name": "Debian 10 x64 (buster)",
        "arch": "x64",
        "family": "debian",
        "windows": False
    },
    "230": {
        "OSID": 230,
        "name": "FreeBSD 11 x64",
        "arch": "x64",
        "family": "freebsd",
        "windows": False
    },
    "327": {
        "OSID": 327,
        "name": "FreeBSD 12 x64",
        "arch": "x64",
        "family": "freebsd",
        "windows": False
    },
    "366": {
        "OSID": 366,
        "name": "OpenBSD 6.6 x64",
        "arch": "x64",
        "family": "openbsd",
        "windows": False
    },
    "394": {
        "OSID": 394,
        "name": "OpenBSD 6.7 x64",
        "arch": "x64",
        "family": "openbsd",
        "windows": False
    },
    "391": {
        "OSID": 391,
        "name": "Fedora CoreOS",
        "arch": "x64",
        "family": "fedora-coreos",
        "windows": False
    },
    "367": {
        "OSID": 367,
        "name": "Fedora 31 x64",
        "arch": "x64",
        "family": "fedora",
        "windows": False
    },
    "389": {
        "OSID": 389,
        "name": "Fedora 32 x64",
        "arch": "x64",
        "family": "fedora",
        "windows": False
    },
    "124": {
        "OSID": 124,
        "name": "Windows 2012 R2 x64",
        "arch": "x64",
        "family": "windows",
        "windows": False
    },
    "240": {
        "OSID": 240,
        "name": "Windows 2016 x64",
        "arch": "x64",
        "family": "windows",
        "windows": False
    },
    "159": {
        "OSID": 159,
        "name": "Custom",
        "arch": "x64",
        "family": "iso",
        "windows": False
    },
    "164": {
        "OSID": 164,
        "name": "Snapshot",
        "arch": "x64",
        "family": "snapshot",
        "windows": False
    },
    "180": {
        "OSID": 180,
        "name": "Backup",
        "arch": "x64",
        "family": "backup",
        "windows": False
    },
    "186": {
        "OSID": 186,
        "name": "Application",
        "arch": "x64",
        "family": "application",
        "windows": False
    }
}
VULTR_COMPUTE_INSTANCE_SIZES = {
    "201": {
        "VPSPLANID": "201",
        "name": "1024 MB RAM,25 GB SSD,1.00 TB BW",
        "vcpu_count": "1",
        "ram": "1024",
        "disk": "25",
        "bandwidth": "1.00",
        "bandwidth_gb": "1024",
        "price_per_month": "5.00",
        "plan_type": "SSD",
        "windows": False,
    },
    "202": {
        "VPSPLANID": "202",
        "name": "2048 MB RAM,55 GB SSD,2.00 TB BW",
        "vcpu_count": "1",
        "ram": "2048",
        "disk": "55",
        "bandwidth": "2.00",
        "bandwidth_gb": "2048",
        "price_per_month": "10.00",
        "plan_type": "SSD",
        "windows": False,
    },
    "203": {
        "VPSPLANID": "203",
        "name": "4096 MB RAM,80 GB SSD,3.00 TB BW",
        "vcpu_count": "2",
        "ram": "4096",
        "disk": "80",
        "bandwidth": "3.00",
        "bandwidth_gb": "3072",
        "price_per_month": "20.00",
        "plan_type": "SSD",
        "windows": False,
    },
    "204": {
        "VPSPLANID": "204",
        "name": "8192 MB RAM,160 GB SSD,4.00 TB BW",
        "vcpu_count": "4",
        "ram": "8192",
        "disk": "160",
        "bandwidth": "4.00",
        "bandwidth_gb": "4096",
        "price_per_month": "40.00",
        "plan_type": "SSD",
        "windows": False,
    },
    "205": {
        "VPSPLANID": "205",
        "name": "16384 MB RAM,320 GB SSD,5.00 TB BW",
        "vcpu_count": "6",
        "ram": "16384",
        "disk": "320",
        "bandwidth": "5.00",
        "bandwidth_gb": "5120",
        "price_per_month": "80.00",
        "plan_type": "SSD",
        "windows": False,
    },
    "206": {
        "VPSPLANID": "206",
        "name": "32768 MB RAM,640 GB SSD,6.00 TB BW",
        "vcpu_count": "8",
        "ram": "32768",
        "disk": "640",
        "bandwidth": "6.00",
        "bandwidth_gb": "6144",
        "price_per_month": "160.00",
        "plan_type": "SSD",
        "windows": False,
    },
    "207": {
        "VPSPLANID": "207",
        "name": "65536 MB RAM,1280 GB SSD,10.00 TB BW",
        "vcpu_count": "16",
        "ram": "65536",
        "disk": "1280",
        "bandwidth": "10.00",
        "bandwidth_gb": "10240",
        "price_per_month": "320.00",
        "plan_type": "SSD",
        "windows": False,
    },
    "208": {
        "VPSPLANID": "208",
        "name": "98304 MB RAM,1600 GB SSD,15.00 TB BW",
        "vcpu_count": "24",
        "ram": "98304",
        "disk": "1600",
        "bandwidth": "15.00",
        "bandwidth_gb": "15360",
        "price_per_month": "640.00",
        "plan_type": "SSD",
        "windows": False,
    },
    "115": {
        "VPSPLANID": "115",
        "name": "8192 MB RAM,110 GB SSD,10.00 TB BW",
        "vcpu_count": "2",
        "ram": "8192",
        "disk": "110",
        "bandwidth": "10.00",
        "bandwidth_gb": "10240",
        "price_per_month": "60.00",
        "plan_type": "DEDICATED",
        "windows": False,
    },
    "116": {
        "VPSPLANID": "116",
        "name": "16384 MB RAM,2x110 GB SSD,20.00 TB BW",
        "vcpu_count": "4",
        "ram": "16384",
        "disk": "110",
        "bandwidth": "20.00",
        "bandwidth_gb": "20480",
        "price_per_month": "120.00",
        "plan_type": "DEDICATED",
        "windows": False,
    },
    "117": {
        "VPSPLANID": "117",
        "name": "24576 MB RAM,3x110 GB SSD,30.00 TB BW",
        "vcpu_count": "6",
        "ram": "24576",
        "disk": "110",
        "bandwidth": "30.00",
        "bandwidth_gb": "30720",
        "price_per_month": "180.00",
        "plan_type": "DEDICATED",
        "windows": False,
    },
    "118": {
        "VPSPLANID": "118",
        "name": "32768 MB RAM,4x110 GB SSD,40.00 TB BW",
        "vcpu_count": "8",
        "ram": "32768",
        "disk": "110",
        "bandwidth": "40.00",
        "bandwidth_gb": "40960",
        "price_per_month": "240.00",
        "plan_type": "DEDICATED",
        "windows": False,
    },
    "400": {
        "VPSPLANID": "400",
        "name": "1024 MB RAM,32 GB SSD,1.00 TB BW",
        "vcpu_count": "1",
        "ram": "1024",
        "disk": "32",
        "bandwidth": "1.00",
        "bandwidth_gb": "1024",
        "price_per_month": "6.00",
        "plan_type": "HIGHFREQUENCY",
        "windows": False,
    },
    "401": {
        "VPSPLANID": "401",
        "name": "2048 MB RAM,64 GB SSD,2.00 TB BW",
        "vcpu_count": "1",
        "ram": "2048",
        "disk": "64",
        "bandwidth": "2.00",
        "bandwidth_gb": "2048",
        "price_per_month": "12.00",
        "plan_type": "HIGHFREQUENCY",
        "windows": False,
    },
    "402": {
        "VPSPLANID": "402",
        "name": "4096 MB RAM,128 GB SSD,3.00 TB BW",
        "vcpu_count": "2",
        "ram": "4096",
        "disk": "128",
        "bandwidth": "3.00",
        "bandwidth_gb": "3072",
        "price_per_month": "24.00",
        "plan_type": "HIGHFREQUENCY",
        "windows": False,
    },
    "403": {
        "VPSPLANID": "403",
        "name": "8192 MB RAM,256 GB SSD,4.00 TB BW",
        "vcpu_count": "3",
        "ram": "8192",
        "disk": "256",
        "bandwidth": "4.00",
        "bandwidth_gb": "4096",
        "price_per_month": "48.00",
        "plan_type": "HIGHFREQUENCY",
        "windows": False,
    },
    "404": {
        "VPSPLANID": "404",
        "name": "16384 MB RAM,384 GB SSD,5.00 TB BW",
        "vcpu_count": "4",
        "ram": "16384",
        "disk": "384",
        "bandwidth": "5.00",
        "bandwidth_gb": "5120",
        "price_per_month": "96.00",
        "plan_type": "HIGHFREQUENCY",
        "windows": False,
    },
    "405": {
        "VPSPLANID": "405",
        "name": "32768 MB RAM,512 GB SSD,6.00 TB BW",
        "vcpu_count": "8",
        "ram": "32768",
        "disk": "512",
        "bandwidth": "6.00",
        "bandwidth_gb": "6144",
        "price_per_month": "192.00",
        "plan_type": "HIGHFREQUENCY",
        "windows": False,
    },
    "406": {
        "VPSPLANID": "406",
        "name": "49152 MB RAM,768 GB SSD,8.00 TB BW",
        "vcpu_count": "12",
        "ram": "49152",
        "disk": "768",
        "bandwidth": "8.00",
        "bandwidth_gb": "8192",
        "price_per_month": "256.00",
        "plan_type": "HIGHFREQUENCY",
        "windows": False,
    }
}


class rate_limited:
    """
    Decorator for retrying Vultr calls that are rate-limited.

    :param int sleep: Seconds to sleep after being rate-limited.
    :param int retries: Number of retries.
    """

    def __init__(self, sleep=0.5, retries=1):
        self.sleep = sleep
        self.retries = retries

    def __call__(self, call):
        """
        Run ``call`` method until it's not rate-limited.

        The method is invoked while it returns 503 Service Unavailable or the
        allowed number of retries is reached.

        :param callable call: Method to be decorated.
        """

        def wrapper(*args, **kwargs):
            last_exception = None

            for _ in range(self.retries + 1):
                try:
                    return call(*args, **kwargs)
                except ServiceUnavailableError as e:
                    last_exception = e
                    time.sleep(self.sleep)  # hit by rate limit, let's sleep

            if last_exception:
                raise last_exception  # pylint: disable=raising-bad-type

        update_wrapper(wrapper, call)
        return wrapper


class VultrResponse(JsonResponse):
    def parse_error(self):
        if self.status == httplib.OK:
            body = self.parse_body()
            return body
        elif self.status == httplib.FORBIDDEN:
            raise InvalidCredsError(self.body)
        elif self.status == httplib.SERVICE_UNAVAILABLE:
            raise ServiceUnavailableError(self.body)
        else:
            raise LibcloudError(self.body)


class SSHKey(object):
    def __init__(self, id, name, pub_key):
        self.id = id
        self.name = name
        self.pub_key = pub_key

    def __repr__(self):
        return (('<SSHKey: id=%s, name=%s, pub_key=%s>') %
                (self.id, self.name, self.pub_key))


class VultrConnection(ConnectionKey):
    """
    Connection class for the Vultr driver.
    """

    host = 'api.vultr.com'
    responseCls = VultrResponse
    unauthenticated_endpoints = {  # {action: methods}
        '/v1/app/list': ['GET'],
        '/v1/os/list': ['GET'],
        '/v1/plans/list': ['GET'],
        '/v1/plans/list_vc2': ['GET'],
        '/v1/plans/list_vdc2': ['GET'],
        '/v1/regions/availability': ['GET'],
        '/v1/regions/list': ['GET']
    }

    def add_default_headers(self, headers):
        """
        Adds ``API-Key`` default header.

        :return: Updated headers.
        :rtype: dict
        """

        if self.require_api_key():
            headers.update({'API-Key': self.key})
        return headers

    def encode_data(self, data):
        return urlencode(data)

    @rate_limited()
    def get(self, url):
        return self.request(url)

    @rate_limited()
    def post(self, url, data):
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        return self.request(url, data=data, headers=headers, method='POST')

    def require_api_key(self):
        """
        Check whether this call (method + action) must be authenticated.

        :return: True if ``API-Key`` header required, False otherwise.
        :rtype: bool
        """

        try:
            return self.method \
                not in self.unauthenticated_endpoints[self.action]
        except KeyError:
            return True


class VultrNodeDriverHelper(object):
    """
        VultrNode helper class.
    """

    def handle_extra(self, extra_keys, data):
        extra = {}
        for key in extra_keys:
            if key in data:
                extra[key] = data[key]
        return extra


class VultrNodeDriver(NodeDriver):
    """
    VultrNode node driver.
    """

    connectionCls = VultrConnection

    type = Provider.VULTR
    name = 'Vultr'
    website = 'https://www.vultr.com'

    NODE_STATE_MAP = {'pending': NodeState.PENDING,
                      'active': NodeState.RUNNING}

    EX_CREATE_YES_NO_ATTRIBUTES = ['enable_ipv6',
                                   'enable_private_network',
                                   'auto_backups',
                                   'notify_activate',
                                   'ddos_protection']

    EX_CREATE_ID_ATTRIBUTES = {'iso_id': 'ISOID',
                               'script_id': 'SCRIPTID',
                               'snapshot_id': 'SNAPSHOTID',
                               'app_id': 'APPID'}

    EX_CREATE_ATTRIBUTES = ['ipxe_chain_url',
                            'label',
                            'userdata',
                            'reserved_ip_v4',
                            'hostname',
                            'tag']
    EX_CREATE_ATTRIBUTES.extend(EX_CREATE_YES_NO_ATTRIBUTES)
    EX_CREATE_ATTRIBUTES.extend(EX_CREATE_ID_ATTRIBUTES.keys())

    def __init__(self, *args, **kwargs):
        super(VultrNodeDriver, self).__init__(*args, **kwargs)
        self._helper = VultrNodeDriverHelper()

    def list_nodes(self):
        return self._list_resources('/v1/server/list', self._to_node)

    def list_key_pairs(self):
        """
        List all the available SSH keys.
        :return: Available SSH keys.
        :rtype: ``list`` of :class:`SSHKey`
        """
        return self._list_resources('/v1/sshkey/list', self._to_ssh_key)

    def create_key_pair(self, name, public_key=''):
        """
        Create a new SSH key.
        :param name: Name of the new SSH key
        :type name: ``str``

        :key public_key: Public part of the new SSH key
        :type name: ``str``

        :return: True on success
        :rtype: ``bool``
        """
        params = {'name': name, 'ssh_key': public_key}
        res = self.connection.post('/v1/sshkey/create', params)
        return res.status == httplib.OK

    def delete_key_pair(self, key_pair):
        """
        Delete an SSH key.
        :param key_pair: The SSH key to delete
        :type key_pair: :class:`SSHKey`

        :return: True on success
        :rtype: ``bool``
        """
        params = {'SSHKEYID': key_pair.id}
        res = self.connection.post('/v1/sshkey/destroy', params)
        return res.status == httplib.OK

    def list_locations(self):
        return self._list_resources('/v1/regions/list', self._to_location)

    def list_sizes(self):
        return self._list_resources('/v1/plans/list', self._to_size)

    def list_images(self):
        return self._list_resources('/v1/os/list', self._to_image)

    # pylint: disable=too-many-locals
    def create_node(self, name, size, image, location, ex_ssh_key_ids=None,
                    ex_create_attr=None):
        """
        Create a node

        :param name: Name for the new node
        :type name: ``str``

        :param size: Size of the new node
        :type size: :class:`NodeSize`

        :param image: Image for the new node
        :type image: :class:`NodeImage`

        :param location: Location of the new node
        :type location: :class:`NodeLocation`

        :param ex_ssh_key_ids: IDs of the SSH keys to initialize
        :type ex_sshkeyid: ``list`` of ``str``

        :param ex_create_attr: Extra attributes for node creation
        :type ex_create_attr: ``dict``

        The `ex_create_attr` parameter can include the following dictionary
        key and value pairs:

        * `ipxe_chain_url`: ``str`` for specifying URL to boot via IPXE
        * `iso_id`: ``str`` the ID of a specific ISO to mount,
          only meaningful with the `Custom` `NodeImage`
        * `script_id`: ``int`` ID of a startup script to execute on boot,
          only meaningful when the `NodeImage` is not `Custom`
        * 'snapshot_id`: ``str`` Snapshot ID to restore for the initial
          installation, only meaningful with the `Snapshot` `NodeImage`
        * `enable_ipv6`: ``bool`` Whether an IPv6 subnet should be assigned
        * `enable_private_network`: ``bool`` Whether private networking
          support should be added
        * `label`: ``str`` Text label to be shown in the control panel
        * `auto_backups`: ``bool`` Whether automatic backups should be enabled
        * `app_id`: ``int`` App ID to launch if launching an application,
          only meaningful when the `NodeImage` is `Application`
        * `userdata`: ``str`` Base64 encoded cloud-init user-data
        * `notify_activate`: ``bool`` Whether an activation email should be
          sent when the server is ready
        * `ddos_protection`: ``bool`` Whether DDOS protection should be enabled
        * `reserved_ip_v4`: ``str`` IP address of the floating IP to use as
          the main IP of this server
        * `hostname`: ``str`` The hostname to assign to this server
        * `tag`: ``str`` The tag to assign to this server

        :return: The newly created node.
        :rtype: :class:`Node`

        """
        params = {'DCID': location.id, 'VPSPLANID': size.id,
                  'OSID': image.id, 'label': name}

        if ex_ssh_key_ids is not None:
            params['SSHKEYID'] = ','.join(ex_ssh_key_ids)

        ex_create_attr = ex_create_attr or {}
        for key, value in ex_create_attr.items():
            if key in self.EX_CREATE_ATTRIBUTES:
                if key in self.EX_CREATE_YES_NO_ATTRIBUTES:
                    params[key] = 'yes' if value else 'no'
                else:
                    if key in self.EX_CREATE_ID_ATTRIBUTES:
                        key = self.EX_CREATE_ID_ATTRIBUTES[key]
                    params[key] = value

        result = self.connection.post('/v1/server/create', params)
        if result.status != httplib.OK:
            return False

        subid = result.object['SUBID']

        retry_count = 3
        created_node = None

        for _ in range(retry_count):
            try:
                nodes = self.list_nodes()
                created_node = [n for n in nodes if n.id == subid][0]
            except IndexError:
                time.sleep(1)
            else:
                break

        return created_node

    def reboot_node(self, node):
        params = {'SUBID': node.id}
        res = self.connection.post('/v1/server/reboot', params)

        return res.status == httplib.OK

    def destroy_node(self, node):
        params = {'SUBID': node.id}
        res = self.connection.post('/v1/server/destroy', params)

        return res.status == httplib.OK

    def _list_resources(self, url, tranform_func):
        data = self.connection.get(url).object
        sorted_key = sorted(data)
        return [tranform_func(data[key]) for key in sorted_key]

    def _to_node(self, data):
        if 'status' in data:
            state = self.NODE_STATE_MAP.get(data['status'], NodeState.UNKNOWN)
            if state == NodeState.RUNNING and \
                    data['power_status'] != 'running':
                state = NodeState.STOPPED
        else:
            state = NodeState.UNKNOWN

        if 'main_ip' in data and data['main_ip'] is not None:
            public_ips = [data['main_ip']]
        else:
            public_ips = []
        # simple check that we have ip address in value
        if len(data['internal_ip']) > 0:
            private_ips = [data['internal_ip']]
        else:
            private_ips = []
        created_at = parse_date(data['date_created'])

        # response ordering
        extra_keys = [
            "location",  # Location name
            "default_password", "pending_charges", "cost_per_month",
            "current_bandwidth_gb", "allowed_bandwidth_gb", "netmask_v4",
            "gateway_v4", "power_status", "server_state",
            "v6_networks",
            # TODO: Does we really need kvm_url?
            "kvm_url",
            "auto_backups", "tag",
            # "OSID",  # Operating system to use. See v1/os/list.
            "APPID", "FIREWALLGROUPID"
        ]
        extra = self._helper.handle_extra(extra_keys, data)

        resolve_data = VULTR_COMPUTE_INSTANCE_IMAGES.get(data["OSID"])
        if resolve_data:
            image = self._to_image(resolve_data)
        else:
            image = None

        resolve_data = VULTR_COMPUTE_INSTANCE_SIZES.get(data["VPSPLANID"])
        if resolve_data:
            size = self._to_size(resolve_data)
        else:
            size = None

        # resolve_data = VULTR_COMPUTE_INSTANCE_LOCATIONS.get(data['DCID'])
        # if resolve_data:
        #     location = self._to_location(resolve_data)
        # extra['location'] = location

        node = Node(
            id=data['SUBID'],
            name=data['label'],
            state=state,
            public_ips=public_ips,
            private_ips=private_ips,
            image=image,
            size=size,
            extra=extra,
            created_at=created_at,
            driver=self)

        return node

    def _to_location(self, data):
        extra_keys = ['continent', 'state', 'ddos_protection',
                      'block_storage', 'regioncode']
        extra = self._helper.handle_extra(extra_keys, data)

        return NodeLocation(id=data['DCID'], name=data['name'],
                            country=data['country'], extra=extra, driver=self)

    def _to_size(self, data):
        extra_keys = [
            'vcpu_count', 'plan_type', 'available_locations',
        ]
        extra = self._helper.handle_extra(extra_keys, data)

        # backward compatibility
        if extra.get('vcpu_count').isdigit():
            extra['vcpu_count'] = int(extra['vcpu_count'])

        ram = int(data['ram'])
        disk = int(data['disk'])
        # NodeSize accepted int instead float
        bandwidth = int(float(data['bandwidth']))
        price = float(data['price_per_month'])
        return NodeSize(id=data['VPSPLANID'], name=data['name'],
                        ram=ram, disk=disk,
                        bandwidth=bandwidth, price=price,
                        extra=extra, driver=self)

    def _to_image(self, data):
        extra_keys = ['arch', 'family']
        extra = self._helper.handle_extra(extra_keys, data)
        return NodeImage(id=data['OSID'], name=data['name'], extra=extra,
                         driver=self)

    def _to_ssh_key(self, data):
        return SSHKey(id=data['SSHKEYID'], name=data['name'],
                      pub_key=data['ssh_key'])
