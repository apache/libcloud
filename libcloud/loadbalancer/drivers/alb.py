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
    'ApplicationLBDriver'
]

from libcloud.utils.xml import findtext, findall
from libcloud.loadbalancer.types import State
from libcloud.loadbalancer.base import Driver, LoadBalancer, Member
from libcloud.common.aws import AWSGenericResponse, SignedAWSConnection


VERSION = '2015-12-01'
HOST = 'elasticloadbalancing.%s.amazonaws.com'
ROOT = '/%s/' % (VERSION)
NS = 'http://elasticloadbalancing.amazonaws.com/doc/%s/' % (VERSION, )


class ALBResponse(AWSGenericResponse):
    """
    Amazon ALB response class.
    """
    namespace = NS
    exceptions = {}
    xpath = 'Error'


class ALBConnection(SignedAWSConnection):
    version = VERSION
    host = HOST
    responseCls = ALBResponse
    service_name = 'elasticloadbalancing'


class ApplicationLBDriver(Driver):
    name = 'Amazon Application Load Balancing'
    website = 'http://aws.amazon.com/elasticloadbalancing/'
    connectionCls = ALBConnection
    signature_version = '4'

    def __init__(self, access_id, secret, region, token=None):
        self.token = token
        super(ApplicationLBDriver, self).__init__(
            access_id, secret, token=token
        )
        self.region = region
        self.region_name = region
        self.connection.host = HOST % (region)

    def list_protocols(self):
        return ['http', 'https']

    def list_balancers(self):
        params = {'Action': 'DescribeLoadBalancers'}
        data = self.connection.request(ROOT, params=params).object
        return self._to_balancers(data)

    def balancer_list_members(self, balancer):
        return balancer._members

    def get_balancer(self, balancer_id):
        params = {
            'Action': 'DescribeLoadBalancers',
            'LoadBalancerNames.member.1': balancer_id
        }
        data = self.connection.request(ROOT, params=params).object
        return self._to_balancers(data)[0]

    def ex_balancer_list_listeners(self, balancer):
        return balancer.extra.get('listeners', [])

    def _to_listeners(self, data):
        xpath = 'DescribeListenersResult/Listeners/member'
        return [self._to_listener(el) for el in findall(
            element=data, xpath=xpath, namespace=NS
        )]

    def _to_listener(self, el):
        listener_arn = findtext(element=el, xpath='ListenerArn', namespace=NS)
        listener = {
            'id': listener_arn,
            'protocol': findtext(element=el, xpath='Protocol', namespace=NS),
            'port': findtext(element=el, xpath='Port', namespace=NS),
            'rules': self._ex_get_rules_for_listener(listener_arn)
        }
        return listener

    def _to_targets(self, data):
        xpath = 'DefaultActions/member'
        return [self._to_target(el) for el in findall(
            element=data, xpath=xpath, namespace=NS
        )]

    def _to_target(self, el):
        return findtext(
            element=el,
            xpath='DefaultActions/member/TargetGroupArn',
            namespace=NS
        )

    def _to_balancer(self, el):
        name = findtext(element=el, xpath='LoadBalancerName', namespace=NS)
        id = findtext(element=el, xpath='LoadBalancerArn', namespace=NS)
        dns_name = findtext(el, xpath='DNSName', namespace=NS)

        balancer = LoadBalancer(
            id=id,
            name=name,
            state=State.UNKNOWN,
            ip=dns_name,
            port=None,
            driver=self.connection.driver
        )

        extra = {
            'listeners': self._ex_get_balancer_listeners(balancer),
            'target_groups': self._ex_get_balancer_target_groups(balancer),
            'tags': self._ex_get_balancer_tags(balancer)
        }
        balancer.extra = extra
        if len(extra['listeners']) > 0:
            balancer.port = extra['listeners'][0]['port']
        else:
            balancer.port = None
        balancer._members = self._ex_get_balancer_memebers(balancer)

        return balancer

    def _to_balancers(self, data):
        xpath = 'DescribeLoadBalancersResult/LoadBalancers/member'
        return [self._to_balancer(el)
                for el in findall(element=data, xpath=xpath, namespace=NS)]

    def _to_tags(self, data):
        """
        return tags dict
        """
        tags = {}
        xpath = 'DescribeTagsResult/TagDescriptions/member/Tags/member'

        for el in findall(element=data, xpath=xpath, namespace=NS):
            key = findtext(element=el, xpath='Key', namespace=NS)
            value = findtext(element=el, xpath='Value', namespace=NS)
            if key:
                tags[key] = value

        return tags

    def _to_rule(self, el):
        def __to_bool__(val):
            return val.lower() in ("yes", "true", "t", "1")

        id = findtext(element=el, xpath='RuleArn', namespace=NS)
        is_default = findtext(element=el, xpath='IsDefault', namespace=NS)
        priority = findtext(element=el, xpath='Priority', namespace=NS)
        target_group = findtext(
            element=el,
            xpath='Actions/member/TargetGroupArn',
            namespace=NS
        )
        conditions = {}
        cond_members = findall(
            element=el, xpath='Conditions/member', namespace=NS
        )
        for cond_member in cond_members:
            field = findtext(element=cond_member, xpath='Field', namespace=NS)
            conditions[field] = []
            value_members = findall(
                element=cond_member, xpath='Values/member', namespace=NS
            )
            for value_member in value_members:
                conditions[field].append(value_member.text)

        rule = {
            'id': id,
            'is_default': __to_bool__(is_default),
            'priority': priority,
            'target_group': target_group,
            'conditions': conditions
        }

        return rule

    def _to_rules(self, data):
        xpath = 'DescribeRulesResult/Rules/member'
        return [self._to_rule(el)
                for el in findall(element=data, xpath=xpath, namespace=NS)]

    def _to_target_groups(self, data):
        xpath = 'DescribeTargetGroupsResult/TargetGroups/member'
        return [self._to_target_group(el)
                for el in findall(element=data, xpath=xpath, namespace=NS)]

    def _to_target_group(self, el):
        target_group_arn = findtext(
            element=el, xpath='TargetGroupArn', namespace=NS
        )
        name = findtext(element=el, xpath='TargetGroupName', namespace=NS)
        members = self._ex_get_target_group_members(target_group_arn)

        return {'id': target_group_arn, 'name': name, 'members': members}

    def _to_target_group_members(self, data):
        xpath = 'DescribeTargetHealthResult/TargetHealthDescriptions/member'
        return [self._to_target_group_member(el)
                for el in findall(element=data, xpath=xpath, namespace=NS)]

    def _to_target_group_member(self, el):
        id = findtext(element=el, xpath='Target/Id', namespace=NS)
        port = findtext(element=el, xpath='Target/Port', namespace=NS)
        health = findtext(
            element=el, xpath='TargetHealth/State', namespace=NS
        )

        return {'id': id, 'port': port, 'health': health}

    def _ex_get_balancer_memebers(self, balancer):
        balancer_members = []
        for tg in balancer.extra['target_groups']:
            for tg_member in tg['members']:
                new_member = Member(
                    tg_member['id'],
                    None,
                    tg_member['port'],
                    balancer=balancer,
                    extra={
                        'health': tg_member['health'],
                        'target_group': tg['name']
                    }
                )
                balancer_members.append(new_member)

        return balancer_members

    def _ex_get_target_group_members(self, target_group_arn):
        """
        Return a list of target group member dicts.

        :rtype: ``list`` of ``dict``
        """
        params = {
            'Action': 'DescribeTargetHealth',
            'TargetGroupArn': target_group_arn
        }

        data = self.connection.request(ROOT, params=params).object
        return self._to_target_group_members(data)

    def _ex_get_balancer_target_groups(self, balancer):
        """
        Return a list of load balancer target groups with members.

        :rtype: ``list`` of ``dict``
        """
        params = {
            'Action': 'DescribeTargetGroups',
            'LoadBalancerArn': balancer.id
        }

        data = self.connection.request(ROOT, params=params).object
        return self._to_target_groups(data)

    def _ex_get_balancer_listeners(self, balancer):
        """
        Return a list of load balancer listeners dicts.

        :rtype: ``list`` of ``dict``
        """
        params = {
            'Action': 'DescribeListeners',
            'LoadBalancerArn': balancer.id
        }

        data = self.connection.request(ROOT, params=params).object
        return self._to_listeners(data)

    def _ex_get_rules_for_listener(self, listener_arn):
        """
        Return a list of listeners rule dicts.

        :rtype: ``list`` of ``dict``
        """
        params = {
            'Action': 'DescribeRules',
            'ListenerArn': listener_arn
        }

        data = self.connection.request(ROOT, params=params).object
        return self._to_rules(data)

    def _ex_connection_class_kwargs(self):
        pdriver = super(ApplicationLBDriver, self)
        kwargs = pdriver._ex_connection_class_kwargs()
        if hasattr(self, 'token') and self.token is not None:
            kwargs['token'] = self.token
            kwargs['signature_version'] = '4'
        else:
            kwargs['signature_version'] = self.signature_version

        return kwargs

    def _ex_get_balancer_tags(self, balancer):
        params = {
            'Action': 'DescribeTags',
            'ResourceArns.member.1': balancer.id
        }
        data = self.connection.request(ROOT, params=params).object
        return self._to_tags(data)
