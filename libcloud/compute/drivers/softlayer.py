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
Softlayer driver
"""

import time

import libcloud

from libcloud.utils.py3 import xmlrpclib

from libcloud.common.types import InvalidCredsError, LibcloudError
from libcloud.compute.types import Provider, NodeState
from libcloud.compute.base import NodeDriver, Node, NodeLocation, NodeSize, NodeImage

DATACENTERS = {
    'sea01': {'country': 'US'},
    'wdc01': {'country': 'US'},
    'dal01': {'country': 'US'}
}

NODE_STATE_MAP = {
    'RUNNING': NodeState.RUNNING,
    'HALTED': NodeState.TERMINATED,
    'PAUSED': NodeState.TERMINATED,
}

DEFAULT_PACKAGE = 46

SL_IMAGES = [
    {'id': 1684, 'name': 'CentOS 5 - Minimal Install (32 bit)'},
    {'id': 1685, 'name': 'CentOS 5 - Minimal Install (64 bit)'},
    {'id': 1686, 'name': 'CentOS 5 - LAMP Install (32 bit)'},
    {'id': 1687, 'name': 'CentOS 5 - LAMP Install (64 bit)'},
    {'id': 1688, 'name': 'Red Hat Enterprise Linux 5 - Minimal Install (32 bit)'},
    {'id': 1689, 'name': 'Red Hat Enterprise Linux 5 - Minimal Install (64 bit)'},
    {'id': 1690, 'name': 'Red Hat Enterprise Linux 5 - LAMP Install (32 bit)'},
    {'id': 1691, 'name': 'Red Hat Enterprise Linux 5 - LAMP Install (64 bit)'},
    {'id': 1692, 'name': 'Ubuntu Linux 8 LTS Hardy Heron - Minimal Install (32 bit)'},
    {'id': 1693, 'name': 'Ubuntu Linux 8 LTS Hardy Heron - Minimal Install (64 bit)'},
    {'id': 1694, 'name': 'Ubuntu Linux 8 LTS Hardy Heron - LAMP Install (32 bit)'},
    {'id': 1695, 'name': 'Ubuntu Linux 8 LTS Hardy Heron - LAMP Install (64 bit)'},
    {'id': 1696, 'name': 'Debian GNU/Linux 5.0 Lenny/Stable - Minimal Install (32 bit)'},
    {'id': 1697, 'name': 'Debian GNU/Linux 5.0 Lenny/Stable - Minimal Install (64 bit)'},
    {'id': 1698, 'name': 'Debian GNU/Linux 5.0 Lenny/Stable - LAMP Install (32 bit)'},
    {'id': 1699, 'name': 'Debian GNU/Linux 5.0 Lenny/Stable - LAMP Install (64 bit)'},
    {'id': 1700, 'name': 'Windows Server 2003 Standard SP2 with R2 (32 bit)'},
    {'id': 1701, 'name': 'Windows Server 2003 Standard SP2 with R2 (64 bit)'},
    {'id': 1703, 'name': 'Windows Server 2003 Enterprise SP2 with R2 (64 bit)'},
    {'id': 1705, 'name': 'Windows Server 2008 Standard Edition (64bit)'},
    {'id': 1715, 'name': 'Windows Server 2003 Datacenter SP2 (64 bit)'},
    {'id': 1716, 'name': 'Windows Server 2003 Datacenter SP2 (32 bit)'},
    {'id': 1742, 'name': 'Windows Server 2008 Standard Edition SP2 (32bit)'},
    {'id': 1752, 'name': 'Windows Server 2008 Standard Edition SP2 (64bit)'},
    {'id': 1756, 'name': 'Windows Server 2008 Enterprise Edition SP2 (32bit)'},
    {'id': 1761, 'name': 'Windows Server 2008 Enterprise Edition SP2 (64bit)'},
    {'id': 1766, 'name': 'Windows Server 2008 Datacenter Edition SP2 (32bit)'},
    {'id': 1770, 'name': 'Windows Server 2008 Datacenter Edition SP2 (64bit)'},
    {'id': 1857, 'name': 'Windows Server 2008 R2 Standard Edition (64bit)'},
    {'id': 1860, 'name': 'Windows Server 2008 R2 Enterprise Edition (64bit)'},
    {'id': 1863, 'name': 'Windows Server 2008 R2 Datacenter Edition (64bit)'},
]

"""
The following code snippet will print out all available "prices"
    mask = { 'items': '' }
    res = self.connection.request(
        "SoftLayer_Product_Package",
        "getObject",
        res,
        id=46,
        object_mask=mask
    )

    from pprint import pprint; pprint(res)
"""
SL_TEMPLATES = {
    'sl1': {
        'imagedata': {
            'name': '2 x 2.0 GHz, 1GB ram, 100GB',
            'ram': 1024,
            'disk': 100,
            'bandwidth': None
        },
        'prices':[
            {'id': 1644},  # 1 GB
            {'id': 1639},  # 100 GB (SAN)
            {'id': 1963},  # Private 2 x 2.0 GHz Cores
            {'id': 21},  # 1 IP Address
            {'id': 55},  # Host Ping
            {'id': 58},  # Automated Notification
            {'id': 1800},  # 0 GB Bandwidth
            {'id': 57},  # Email and Ticket
            {'id': 274},  # 1000 Mbps Public & Private Networks
            {'id': 905},  # Reboot / Remote Console
            {'id': 418},  # Nessus Vulnerability Assessment & Reporting
            {'id': 420},  # Unlimited SSL VPN Users & 1 PPTP VPN User per account
        ],
    },
    'sl2': {
        'imagedata': {
            'name': '2 x 2.0 GHz, 4GB ram, 350GB',
            'ram': 4096,
            'disk': 350,
            'bandwidth': None
        },
        'prices': [
            {'id': 1646},  # 4 GB
            {'id': 1639},  # 100 GB (SAN) - This is the only available "First Disk"
            {'id': 1638},  # 250 GB (SAN)
            {'id': 1963},  # Private 2 x 2.0 GHz Cores
            {'id': 21},  # 1 IP Address
            {'id': 55},  # Host Ping
            {'id': 58},  # Automated Notification
            {'id': 1800},  # 0 GB Bandwidth
            {'id': 57},  # Email and Ticket
            {'id': 274},  # 1000 Mbps Public & Private Networks
            {'id': 905},  # Reboot / Remote Console
            {'id': 418},  # Nessus Vulnerability Assessment & Reporting
            {'id': 420},  # Unlimited SSL VPN Users & 1 PPTP VPN User per account
        ],
    }
}

class SoftLayerException(LibcloudError):
    """
    Exception class for SoftLayer driver
    """
    pass

class SoftLayerSafeTransport(xmlrpclib.SafeTransport):
    pass

class SoftLayerTransport(xmlrpclib.Transport):
    pass

class SoftLayerProxy(xmlrpclib.ServerProxy):
    transportCls = (SoftLayerTransport, SoftLayerSafeTransport)
    API_PREFIX = 'https://api.softlayer.com/xmlrpc/v3/'

    def __init__(self, service, user_agent, verbose=0):
        cls = self.transportCls[0]
        if SoftLayerProxy.API_PREFIX[:8] == "https://":
            cls = self.transportCls[1]
        t = cls(use_datetime=0)
        t.user_agent = user_agent
        xmlrpclib.ServerProxy.__init__(
            self,
            uri="%s/%s" % (SoftLayerProxy.API_PREFIX, service),
            transport=t,
            verbose=verbose
        )

class SoftLayerConnection(object):
    """
    Connection class for the SoftLayer driver
    """

    proxyCls = SoftLayerProxy
    driver = None

    def __init__(self, user, key):
        self.user = user
        self.key = key
        self.ua = []

    def request(self, service, method, *args, **kwargs):
        sl = self.proxyCls(service, self._user_agent())

        headers = {}
        headers.update(self._get_auth_headers())
        headers.update(self._get_init_params(service, kwargs.get('id')))
        headers.update(self._get_object_mask(service, kwargs.get('object_mask')))
        params = [{'headers': headers}] + list(args)

        try:
            return getattr(sl, method)(*params)
        except xmlrpclib.Fault:
            e = sys.exc_info()[1]
            if e.faultCode == "SoftLayer_Account":
                raise InvalidCredsError(e.faultString)
            raise SoftLayerException(e)

    def _user_agent(self):
        return 'libcloud/%s (%s)%s' % (
                libcloud.__version__,
                self.driver.name,
                "".join([" (%s)" % x for x in self.ua]))

    def user_agent_append(self, s):
        self.ua.append(s)

    def _get_auth_headers(self):
        return {
            'authenticate': {
                'username': self.user,
                'apiKey': self.key
            }
        }

    def _get_init_params(self, service, id):
        if id is not None:
            return {
                '%sInitParameters' % service: {'id': id}
            }
        else:
            return {}

    def _get_object_mask(self, service, mask):
        if mask is not None:
            return {
                '%sObjectMask' % service: {'mask': mask}
            }
        else:
            return {}

class SoftLayerNodeDriver(NodeDriver):
    """
    SoftLayer node driver

    Extra node attributes:
        - password: root password
        - hourlyRecurringFee: hourly price (if applicable)
        - recurringFee      : flat rate    (if applicable)
        - recurringMonths   : The number of months in which the recurringFee will be incurred.
    """
    connectionCls = SoftLayerConnection
    name = 'SoftLayer'
    type = Provider.SOFTLAYER

    features = {"create_node": ["generates_password"]}

    def __init__(self, key, secret=None, secure=False):
        self.key = key
        self.secret = secret
        self.connection = self.connectionCls(key, secret)
        self.connection.driver = self

    def _to_node(self, host):
        try:
            password = host['softwareComponents'][0]['passwords'][0]['password']
        except (IndexError, KeyError):
            password = None

        hourlyRecurringFee = host.get('billingItem', {}).get('hourlyRecurringFee', 0)
        recurringFee = host.get('billingItem', {}).get('recurringFee', 0)
        recurringMonths = host.get('billingItem', {}).get('recurringMonths', 0)

        return Node(
            id=host['id'],
            name=host['hostname'],
            state=NODE_STATE_MAP.get(
                host['powerState']['keyName'],
                NodeState.UNKNOWN
            ),
            public_ips=[host['primaryIpAddress']],
            private_ips=[host['primaryBackendIpAddress']],
            driver=self,
            extra={
                'password': password,
                'hourlyRecurringFee': hourlyRecurringFee,
                'recurringFee': recurringFee,
                'recurringMonths': recurringMonths,
            }
        )

    def _to_nodes(self, hosts):
        return [self._to_node(h) for h in hosts]

    def destroy_node(self, node):
        billing_item = self.connection.request(
            "SoftLayer_Virtual_Guest",
            "getBillingItem",
            id=node.id
        )

        if billing_item:
            res = self.connection.request(
                "SoftLayer_Billing_Item",
                "cancelService",
                id=billing_item['id']
            )
            return res
        else:
            return False

    def _get_order_information(self, order_id, timeout=1200, check_interval=5):
        mask = {
            'orderTopLevelItems': {
                'billingItem':  {
                    'resource': {
                        'softwareComponents': {
                            'passwords': ''
                        },
                        'powerState': '',
                    }
                },
            }
         }

        for i in range(0, timeout, check_interval):
            try:
                res = self.connection.request(
                    "SoftLayer_Billing_Order",
                    "getObject",
                    id=order_id,
                    object_mask=mask
                )
                item = res['orderTopLevelItems'][0]['billingItem']['resource']
                if item['softwareComponents'][0]['passwords']:
                    return item

            except (KeyError, IndexError):
                pass

            time.sleep(check_interval)

        return None

    def create_node(self, **kwargs):
        """Create a new SoftLayer node

        See L{NodeDriver.create_node} for more keyword args.
        @keyword    ex_domain: e.g. libcloud.org
        @type       ex_domain: C{string}
        """
        name = kwargs['name']
        image = kwargs['image']
        size = kwargs['size']
        domain = kwargs.get('ex_domain')
        location = kwargs['location']
        if domain == None:
            if name.find(".") != -1:
                domain = name[name.find('.')+1:]

        if domain == None:
            # TODO: domain is a required argument for the Sofylayer API, but it
            # it shouldn't be.
            domain = "exmaple.com"

        res = {'prices': SL_TEMPLATES[size.id]['prices']}
        res['packageId'] = DEFAULT_PACKAGE
        res['prices'].append({'id': image.id})  # Add OS to order
        res['location'] = location.id
        res['complexType'] = 'SoftLayer_Container_Product_Order_Virtual_Guest'
        res['quantity'] = 1
        res['useHourlyPricing'] = True
        res['virtualGuests'] = [
            {
                'hostname': name,
                'domain': domain
            }
        ]

        res = self.connection.request(
            "SoftLayer_Product_Order",
            "placeOrder",
            res
        )

        order_id = res['orderId']
        raw_node = self._get_order_information(order_id)

        return self._to_node(raw_node)

    def _to_image(self, img):
        return NodeImage(
            id=img['id'],
            name=img['name'],
            driver=self.connection.driver
        )

    def list_images(self, location=None):
        return [self._to_image(i) for i in SL_IMAGES]

    def _to_size(self, id, size):
        return NodeSize(
            id=id,
            name=size['name'],
            ram=size['ram'],
            disk=size['disk'],
            bandwidth=size['bandwidth'],
            price=None,
            driver=self.connection.driver,
        )

    def list_sizes(self, location=None):
        return [self._to_size(id, s['imagedata']) for id, s in
                list(SL_TEMPLATES.items())]

    def _to_loc(self, loc):
        return NodeLocation(
            id=loc['id'],
            name=loc['name'],
            country=DATACENTERS[loc['name']]['country'],
            driver=self
        )

    def list_locations(self):
        res = self.connection.request(
            "SoftLayer_Location_Datacenter",
            "getDatacenters"
        )

        # checking "in DATACENTERS", because some of the locations returned by getDatacenters are not useable.
        return [self._to_loc(l) for l in res if l['name'] in DATACENTERS]

    def list_nodes(self):
        mask = {
            'virtualGuests': {
                'powerState': '',
                'softwareComponents': {
                    'passwords': ''
                },
                'billingItem': '',
            },
        }
        res = self.connection.request(
            "SoftLayer_Account",
            "getVirtualGuests",
            object_mask=mask
        )
        nodes = self._to_nodes(res)
        return nodes

    def reboot_node(self, node):
        res = self.connection.request(
            "SoftLayer_Virtual_Guest",
            "rebootHard",
            id=node.id
        )
        return res
