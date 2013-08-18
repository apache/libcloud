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

import sys
import unittest

from libcloud.utils.py3 import httplib
from libcloud.loadbalancer.base import Member, Algorithm
from libcloud.loadbalancer.types import State

from libcloud.test import MockHttpTestCase

from xml.etree import ElementTree as ET
from libcloud.utils.py3 import urlparse
from cgi import parse_qs
from libcloud.loadbalancer.base import DEFAULT_ALGORITHM
from libcloud.loadbalancer.drivers.elb import NS


class AWSParamAdaptor(object):

    def __init__(self, container):
        self.container = container

    @classmethod
    def from_query_string(cls, query_string):
        return cls(parse_qs(query_string))

    @classmethod
    def from_url(cls, url):
        parsed = urlparse.urlparse(url)
        return cls.from_query_string(parsed.query)

    def get(self, key, default=None):
        val = self.container.get(key, [default])
        assert len(val) == 1
        return val[0]

    def __getitem__(self, key):
        val = self.container[key]
        assert len(val) == 1
        return val[0]

    def __contains__(self, key):
        return key in self.container

    def get_list_of_literals(self, key):
        """
        For AWS and similar, a list of literal values will be represented as follows:

            AvailabilityZones.member.1
            AvailabilityZones.member.2
        """
        params = self.container

        relevant_keys = [p for p in params.keys() if p.startswith(key)]
        relevant_keys.sort()

        if not len(relevant_keys):
            return []

        retval = []
        for key in relevant_keys:
            tup = key.split(".")
            assert len(tup) == 3
            val = params[key]
            assert len(val) == 1
            retval.append(val[0])

        return retval

    def get_list_of_structs(self, key):
        """
        For AWS and similar a list of structs will be represented as follows:

            Listeners.members.1.InstancePort
            Listeners.members.1.LoadBalancerPort
            Listeners.members.2.InstancePort
            Listeners.members.2.LoadBalancerPort

        It can also handle:

            realiplist.0.ip
            realiplist.1.ip
        """
        params = self.container

        relevant_keys = [p for p in params.keys() if p.startswith(key)]
        relevant_keys.sort()

        if not len(relevant_keys):
            return []

        retval = []
        idx = -1
        for key in relevant_keys:
            tup = key.split(".")
            assert len(tup) in (3,4)
            if idx != int(tup[-2]):
                s = {}
                retval.append(s)
                idx = int(tup[-2])
            val = params[key]
            assert len(val) == 1
            s[tup[-1]] = val[0]

        return retval


class ElasticLBMockHttp(MockHttpTestCase):

    type = None
    use_param = 'Action'

    def __init__(self, *args, **kwargs):
        MockHttpTestCase.__init__(self, *args, **kwargs)

    @property
    def driver(self):
        return self.test.mock

    def _verify_signature(self, params):
        self.assertIn("Timestamp", params)
        self.assertEqual(params["SignatureVersion"], "2")
        self.assertEqual(params["SignatureMethod"], "HmacSHA256")
        self.assertIn("Signature", params)
        self.assertIn("Version", params)

    def _2012_06_01_DescribeLoadBalancers(self, method, url, body, headers):
        params = AWSParamAdaptor.from_url(url)
        self._verify_signature(params)

        attrs = {'xmlns': NS}
        resp = ET.Element('DescribeLoadBalancersResponse', attrs)
        result = ET.SubElement(resp, 'DescribeLoadBalancersResult')
        descs = ET.SubElement(result, 'LoadBalancerDescriptions')

        for b in self.driver.list_balancers():
            m = ET.SubElement(descs, "member")
            ET.SubElement(m, "LoadBalancerName").text = b.name

            instances = ET.SubElement(m, "Instances")
            for i in b._members:
                inst = ET.SubElement(instances, "member")
                ET.SubElement(inst, "InstanceId").text = i.id

            listeners = ET.SubElement(m, "ListenerDescriptions")
            m2 = ET.SubElement(listeners, "member")
            listener = ET.SubElement(m2, "Listener")

            protocol = b.extra.get('protocol', '').lower()

            ET.SubElement(listener, "Protocol").text = protocol
            ET.SubElement(listener, "LoadBalancerPort").text = str(b.port)
            ET.SubElement(listener, "InstanceProtocol").text = protocol
            ET.SubElement(listener, "InstancePort").text = str(b.port)

            ET.SubElement(m, "DNSName").text = b.ip

        body = ET.tostring(resp)
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _2012_06_01_CreateLoadBalancer(self, method, url, body, headers):
        params = AWSParamAdaptor.from_url(url)
        self._verify_signature(params)

        lb_name = params['LoadBalancerName']

        # Amazon enforces that at least one availability zone be set
        zones = params.get_list_of_literals("AvailabilityZones")
        self.assertGreater(len(zones), 0)
        self.assertEqual(len(set(zones)), len(zones))

        listeners = params.get_list_of_structs("Listeners")
        for l in listeners:
            self.assertIn("Protocol", l)
            self.assertIn(l["Protocol"], ("HTTP", "HTTPS", "TCP", "SSL"))
            self.assertIn("InstancePort", l)
            self.assertIn("LoadBalancerPort", l)

        lb = self.driver.create_balancer(
            name=params['LoadBalancerName'],
            port=listeners[0]['LoadBalancerPort'],
            protocol=listeners[0]['Protocol'].lower(),
            algorithm=DEFAULT_ALGORITHM,
            members=[],
        )

        attrs = {'xmlns': NS}
        result = ET.Element('CreateLoadBalancerResult', attrs)
        ET.SubElement(result, "DNSName").text = lb.ip
        body = ET.tostring(result)
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _2012_06_01_DeregisterInstancesFromLoadBalancer(self, method, url, body, headers):
        params = AWSParamAdaptor.from_url(url)
        self._verify_signature(params)

        to_delete = params.get_list_of_structs('Instances')
        to_delete = [d["InstanceId"] for d in to_delete]

        balancers = [b for b in self.driver.list_balancers() if b.name == params['LoadBalancerName']]
        balancer = balancers[0]
        for member in balancer.list_members():
            if member.id in to_delete:
                balancer.detach_member(member)

        attrs = {'xmlns': NS}
        result = ET.Element('DeregisterInstancesFromLoadBalancerResult', attrs)
        instances = ET.SubElement(result, "Instances")
        for m in balancer.list_members():
            ET.SubElement(instances, "InstanceId").text = m.id
        body = ET.tostring(result)
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _2012_06_01_DeleteLoadBalancer(self, method, url, body, headers):
        params = AWSParamAdaptor.from_url(url)
        self._verify_signature(params)

        balancers = [b for b in self.driver.list_balancers() if b.name == params['LoadBalancerName']]
        balancer = balancers[0]
        balancer.destroy()

        attrs = {'xmlns': NS}
        result = ET.Element('DeleteLoadBalancerResult', attrs)
        body = ET.tostring(result)
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])


if __name__ == "__main__":
    sys.exit(unittest.main())
