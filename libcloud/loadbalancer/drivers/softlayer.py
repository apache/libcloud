# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance withv
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
    'SoftlayerLBDriver'
]

from libcloud.common.types import LibcloudError
from libcloud.common.softlayer import SoftLayerConnection
from libcloud.utils.misc import find, reverse_dict
from libcloud.loadbalancer.types import State
from libcloud.loadbalancer.base import Algorithm, Driver, LoadBalancer
from libcloud.loadbalancer.base import DEFAULT_ALGORITHM, Member

lb_service = 'SoftLayer_Network_Application_Delivery_Controller_LoadBalancer_'\
    'VirtualIpAddress'


class LBPackage(object):

    """
    Defines a single Softlayer package to be used when placing orders (
    e.g. via ex_place_balancer_order method).

    :param id: Package id.
    :type id: ``int``

    :param name: Package name.
    :type name: ``str``

    :param description: Package short description.
    :type description: ``str``

    :param price_id: Id of the price for this package.
    :type price_id: ``int``

    :param capacity: Provides a numerical representation of the capacity given
                     in the description of this package.
    :type capacity: ``int``

    """

    def __init__(self, id, name, description, price_id, capacity):
        self.id = id
        self.name = name
        self.description = description
        self.price_id = price_id
        self.capacity = capacity

    def __repr__(self):
        return (
            '<LBPackage: id=%s, name=%s, description=%s, price_id=%s, '
            'capacity=%s>' % (self.id, self.name, self.description,
                              self.price_id, self.capacity))


class SoftlayerLBDriver(Driver):
    name = 'Softlayer Load Balancing'
    website = 'http://www.softlayer.com/'
    connectionCls = SoftLayerConnection

    _VALUE_TO_ALGORITHM_MAP = {
        'ROUND_ROBIN': Algorithm.ROUND_ROBIN,
        'LEAST_CONNECTIONS': Algorithm.LEAST_CONNECTIONS,
        'SHORTEST_RESPONSE': Algorithm.SHORTEST_RESPONSE,
        'PERSISTENT_IP': Algorithm.PERSISTENT_IP
    }

    _ALGORITHM_TO_VALUE_MAP = reverse_dict(_VALUE_TO_ALGORITHM_MAP)

    def list_balancers(self):
        mask = {
            'adcLoadBalancers': {
                'ipAddress': '',
                'loadBalancerHardware': {
                    'datacenter': ''
                },
                'virtualServers': {
                    'serviceGroups': {
                        'routingMethod': '',
                        'routingType': '',
                        'services': {
                            'ipAddress': ''
                        }
                    }
                }
            }
        }

        res = self.connection.request(
            'SoftLayer_Account', 'getAdcLoadBalancers',
            object_mask=mask).object

        return [self._to_balancer(lb) for lb in res]

    def get_balancer(self, balancer_id):
        balancers = self.list_balancers()
        balancer = find(balancers, lambda b: b.id == balancer_id)
        if not balancer:
            raise LibcloudError(value='No balancer found for id: %s' %
                                balancer_id, driver=self)
        return balancer

    def list_protocols(self):
        """
        Return a list of supported protocols.

        :rtype: ``list`` of ``str``
        """
        return ['dns', 'ftp', 'http', 'https', 'tcp', 'udp']

    def balancer_list_members(self, balancer):
        lb = self._get_balancer_model(balancer.id)
        members = []
        vs = self._locate_service_group(lb, balancer.port)
        if vs:
            if vs['serviceGroups']:
                srvgrp = vs['serviceGroups'][0]
                members = [self._to_member(srv, balancer) for
                           srv in srvgrp['services']]

        return members

    def balancer_attach_member(self, balancer, member):
        lb = self._get_balancer_model(balancer.id)
        vs = self._locate_service_group(lb, balancer.port)
        if not vs:
            raise LibcloudError(value='No service_group found for balancer '
                                'port: %s' % balancer.port, driver=self)

        if vs['serviceGroups']:
            services = vs['serviceGroups'][0]['services']
            services.append(self._to_service_template(member.ip,
                                                      member.port))

        self.connection.request(lb_service, 'editObject', lb, id=balancer.id)

        return [m for m in balancer.list_members() if m.ip == member.ip][0]

    def balancer_detach_member(self, balancer, member):
        svc_lbsrv = 'SoftLayer_Network_Application_Delivery_Controller_'\
            'LoadBalancer_Service'

        self.connection.request(svc_lbsrv, 'deleteObject', id=member.id)
        return True

    def destroy_balancer(self, balancer):
        res_billing = self.connection.request(lb_service, 'getBillingItem',
                                              id=balancer.id).object

        self.connection.request('SoftLayer_Billing_Item', 'cancelService',
                                id=res_billing['id'])
        return True

    def ex_list_balancer_packages(self):
        """
        Retrieves the available local load balancer packages.

        :rtype: ``list`` of :class:`LBPackage`
        """
        mask = {
            'prices': ''
        }
        res = self.connection.request('SoftLayer_Product_Package', 'getItems',
                                      id=0, object_mask=mask).object

        res_lb_pkgs = [r for r in res if r['description'].find
                       ('Load Balancer') != -1]
        res_lb_pkgs = [r for r in res_lb_pkgs if not r['description'].
                       startswith('Global')]

        return [self._to_lb_package(r) for r in res_lb_pkgs]

    def ex_place_balancer_order(self, package, location):
        """
        Places an order for a local loadbalancer in the specified
        location.

        :param package: The package to create the loadbalancer from.
        :type package: :class:`LBPackage`

        :param string location: The location (datacenter) to create the
                                loadbalancer.
        :type location: :class:`NodeLocation`

        :return: ``True`` if ex_place_balancer_order was successful.
        :rtype: ``bool``
        """
        data = {
            'complexType': 'SoftLayer_Container_Product_Order_Network_'
                           'LoadBalancer',
            'quantity': 1,
            'packageId': 0,
            'location': self._get_location(location.id),
            'prices': [{'id': package.price_id}]
        }

        self.connection.request('SoftLayer_Product_Order', 'placeOrder',
                                data)
        return True

    def ex_configure_load_balancer(self, balancer, port=80,
                                   protocol='http',
                                   algorithm=DEFAULT_ALGORITHM,
                                   ex_allocation=100):
        """
        Configure the loadbalancer by adding it with a front-end port (aka
        a service group in the Softlayer loadbalancer model).

        Softlayer loadbalancer may be defined with multiple service
        groups (front-end ports) each defined with a unique port number.

        :param balancer: The loadbalancer.
        :type  balancer: :class:`LoadBalancer`

        :param port: Port of the service group, defaults to 80.
        :type  port: ``int``

        :param protocol: Loadbalancer protocol, defaults to http.
        :type  protocol: ``str``

        :param algorithm: Load balancing algorithm, defaults to
                            Algorithm.ROUND_ROBIN
        :type  algorithm: :class:`Algorithm`

        :param ex_allocation: The percentage of the total connection
                              allocations to allocate for this group.
        :type  ex_allocation: ``int``

        :return: ``True`` if ex_add_service_group was successful.
        :rtype: ``bool``
        """
        _types = self._get_routing_types()
        _methods = self._get_routing_methods()

        rt = find(_types, lambda t: t['keyname'] == protocol.upper())
        if not rt:
            raise LibcloudError(value='Invalid protocol %s' % protocol,
                                driver=self)

        value = self._algorithm_to_value(algorithm)
        meth = find(_methods, lambda m: m['keyname'] == value)
        if not meth:
            raise LibcloudError(value='Invalid algorithm %s' % algorithm,
                                driver=self)

        service_group_template = {
            'port': port,
            'allocation': ex_allocation,
            'serviceGroups': [{
                'routingTypeId': rt['id'],
                'routingMethodId': meth['id']
            }]
        }

        lb = self._get_balancer_model(balancer.id)
        if len(lb['virtualServers']) > 0:
            port = lb['virtualServers'][0]['port']
            raise LibcloudError(value='Loadbalancer already configured with '
                                'a service group (front-end port)' % port,
                                driver=self)

        lb['virtualServers'].append(service_group_template)
        self.connection.request(lb_service, 'editObject', lb, id=balancer.id)
        return True

    def _get_balancer_model(self, balancer_id):
        """
        Retrieve Softlayer loadbalancer model.
        """
        lb_mask = {
            'virtualServers': {
                'serviceGroups': {
                    'services': {
                        'ipAddress': '',
                        'groupReferences': '',
                    }
                }
            }
        }

        lb_res = self.connection.request(lb_service, 'getObject',
                                         object_mask=lb_mask, id=balancer_id).\
            object
        return lb_res

    def _locate_service_group(self, lb, port):
        """
        Locate service group with given port.

        Return virtualServers (vs) entry whose port matches the
        supplied parameter port. For a negative port, just return
        the first vs entry.
        None is returned if no match found.

        :param lb: Softlayer loadbalancer model.
        :type lb: ``dict``

        :param port: loadbalancer front-end port.
        :type port: ``int``

        :return: Matched entry in the virtualServers array of the supplied
        model.
        :rtype: ``dict``
        """
        vs = None
        if port < 0:
            vs = lb['virtualServers'][0] if lb['virtualServers']\
                else None
        else:
            vs = find(lb['virtualServers'], lambda v: v['port'] == port)

        return vs

    def _get_routing_types(self):
        svc_rtype = 'SoftLayer_Network_Application_Delivery_Controller_'\
            'LoadBalancer_Routing_Type'

        return self.connection.request(svc_rtype, 'getAllObjects').object

    def _get_routing_methods(self):
        svc_rmeth = 'SoftLayer_Network_Application_Delivery_Controller_'\
            'LoadBalancer_Routing_Method'

        return self.connection.request(svc_rmeth, 'getAllObjects').object

    def _get_location(self, location_id):
        res = self.connection.request('SoftLayer_Location_Datacenter',
                                      'getDatacenters').object

        dcenter = find(res, lambda d: d['name'] == location_id)
        if not dcenter:
            raise LibcloudError(value='Invalid value %s' % location_id,
                                driver=self)
        return dcenter['id']

    def _get_ipaddress(self, ip):
        svc_ipaddress = 'SoftLayer_Network_Subnet_IpAddress'

        return self.connection.request(svc_ipaddress, 'getByIpAddress',
                                       ip).object

    def _to_lb_package(self, pkg):
        try:
            price_id = pkg['prices'][0]['id']
        except:
            price_id = -1

        capacity = int(pkg.get('capacity', 0))
        return LBPackage(id=pkg['id'], name=pkg['keyName'],
                         description=pkg['description'],
                         price_id=price_id, capacity=capacity)

    def _to_service_template(self, ip, port):
        """
        Builds single member entry in Softlayer loadbalancer model
        """
        template = {
            'enabled': 1,  # enable the service
            'port': port,  # back-end port
            'ipAddressId': self._get_ipaddress(ip)['id'],
            'healthChecks': [{
                'healthCheckTypeId': 21  # default health check
            }],
            'groupReferences': [{
                'weight': 1
            }]
        }

        return template

    def _to_balancer(self, lb):
        ipaddress = lb['ipAddress']['ipAddress']

        extra = {}
        extra['connection_limit'] = lb['connectionLimit']
        extra['ssl_active'] = lb['sslActiveFlag']
        extra['ssl_enabled'] = lb['sslEnabledFlag']
        extra['ha'] = lb['highAvailabilityFlag']
        extra['datacenter'] = \
            lb['loadBalancerHardware'][0]['datacenter']['name']

        # In Softlayer, there could be multiple group of members (aka service
        # groups), so retrieve the first one
        vs = self._locate_service_group(lb, -1)
        if vs:
            port = vs['port']
            if vs['serviceGroups']:
                srvgrp = vs['serviceGroups'][0]
                routing_method = srvgrp['routingMethod']['keyname']
                routing_type = srvgrp['routingType']['keyname']
                try:
                    extra['algorithm'] = self.\
                        _value_to_algorithm(routing_method)
                except:
                    pass
                extra['protocol'] = routing_type.lower()

        if not vs:
            port = -1

        balancer = LoadBalancer(
            id=lb['id'],
            name='',
            state=State.UNKNOWN,
            ip=ipaddress,
            port=port,
            driver=self.connection.driver,
            extra=extra
        )

        return balancer

    def _to_member(self, srv, balancer=None):
        svc_id = srv['id']
        ip = srv['ipAddress']['ipAddress']
        port = srv['port']

        extra = {}
        extra['status'] = srv['status']
        extra['enabled'] = srv['enabled']
        return Member(id=svc_id, ip=ip, port=port, balancer=balancer,
                      extra=extra)
