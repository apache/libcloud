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
import time

from libcloud.common.types import LibcloudError
from libcloud.common.softlayer import SoftLayerException, \
    SoftLayerObjectDoesntExist, SoftLayerConnection

from libcloud.autoscale.base import AutoScaleDriver, AutoScalePolicy, \
    AutoScaleGroup, AutoScaleAlarm
from libcloud.autoscale.types import AutoScaleOperator, \
    AutoScaleTerminationPolicy, AutoScaleAdjustmentType, AutoScaleMetric
from libcloud.autoscale.types import Provider
from libcloud.utils.misc import find, reverse_dict
from libcloud.compute.drivers.softlayer import SoftLayerNodeDriver


class SoftLayerAutoScaleDriver(AutoScaleDriver):

    _VALUE_TO_SCALE_OPERATOR_TYPE_MAP = {
        '>': AutoScaleOperator.GT,
        '<': AutoScaleOperator.LT
    }

    _SCALE_OPERATOR_TYPE_TO_VALUE_MAP = reverse_dict(
        _VALUE_TO_SCALE_OPERATOR_TYPE_MAP)

    _VALUE_TO_SCALE_ADJUSTMENT_TYPE_MAP = {
        'RELATIVE': AutoScaleAdjustmentType.CHANGE_IN_CAPACITY,
        'ABSOLUTE': AutoScaleAdjustmentType.EXACT_CAPACITY,
        'PERCENT': AutoScaleAdjustmentType.PERCENT_CHANGE_IN_CAPACITY
    }

    _SCALE_ADJUSTMENT_TYPE_TO_VALUE_MAP = reverse_dict(
        _VALUE_TO_SCALE_ADJUSTMENT_TYPE_MAP)

    _VALUE_TO_TERMINATION_POLICY_MAP = {
        'OLDEST': AutoScaleTerminationPolicy.OLDEST_INSTANCE,
        'NEWEST': AutoScaleTerminationPolicy.NEWEST_INSTANCE,
        'CLOSEST_TO_NEXT_CHARGE': AutoScaleTerminationPolicy.
        CLOSEST_TO_NEXT_CHARGE
    }

    _TERMINATION_POLICY_TO_VALUE_MAP = reverse_dict(
        _VALUE_TO_TERMINATION_POLICY_MAP)

    _VALUE_TO_METRIC_MAP = {
        'host.cpu.percent': AutoScaleMetric.CPU_UTIL
    }

    _METRIC_TO_VALUE_MAP = reverse_dict(
        _VALUE_TO_METRIC_MAP)

    connectionCls = SoftLayerConnection
    name = 'SoftLayer'
    website = 'http://www.softlayer.com/'
    type = Provider.SOFTLAYER

    def __init__(self, *args, **kwargs):

        if kwargs.get('softlayer'):
            self.softlayer = kwargs['softlayer']
        else:
            self.softlayer = SoftLayerNodeDriver(*args, **kwargs)

    def list_auto_scale_groups(self):

        mask = {
            'scaleGroups': {
                'terminationPolicy': ''
            }
        }

        res = self.connection.request('SoftLayer_Account',
                                      'getScaleGroups', object_mask=mask).\
            object
        return self._to_autoscale_groups(res)

    def create_auto_scale_group(
            self, group_name, min_size, max_size, cooldown,
            termination_policies, ex_region='na-usa-east-1',
            **kwargs):
        """
        Create a new auto scale group.

        @inherits: :class:`AutoScaleDriver.create_auto_scale_group`

        :param ex_region: The region the group will be created
        in. e.g. 'na-usa-east-1' (required)
        :type  ex_region: ``str``

        Note: keyword arguments identical to ones passed into create_node()

        :return: The newly created scale group.
        :rtype: :class:`.AutoScaleGroup`
        """
        DEFAULT_TIMEOUT = 12000
        template = self.softlayer._to_virtual_guest_template(kwargs)

        # Customize template per property 'virtualGuestMemberTemplate' at:
        # http://sldn.softlayer.com/reference/datatypes/SoftLayer_Scale_Group
        if 'datacenter' not in template:
            template['datacenter'] = {'name': 'FIRST_AVAILABLE'}
        template['hourlyBillingFlag'] = 'true'

        def _wait_for_creation(group_id):
            # 5 seconds
            POLL_INTERVAL = 5

            end = time.time() + DEFAULT_TIMEOUT
            completed = False
            while time.time() < end and not completed:
                status_name = self._get_group_status(group_id)
                if status_name != 'ACTIVE':
                    time.sleep(POLL_INTERVAL)
                else:
                    completed = True

            if not completed:
                raise LibcloudError('Group creation did not complete in %s'
                                    ' seconds' % (DEFAULT_TIMEOUT))

        # retrieve internal region id
        res = self.connection.request(
            'SoftLayer_Location_Group_Regional',
            'getAllObjects').object
        r = find(res, lambda r: r['name'] == ex_region)
        if not r:
            raise SoftLayerException('Unable to find region id for region: %s'
                                     % ex_region)
        rgn_grp_id = r['id']

        data = {}
        data['name'] = group_name
        data['minimumMemberCount'] = min_size
        data['maximumMemberCount'] = max_size
        data['cooldown'] = cooldown

        data['regionalGroupId'] = rgn_grp_id
        data['suspendedFlag'] = False

        if termination_policies:
            termination_policy = termination_policies[0] if \
                isinstance(termination_policies, list) else \
                termination_policies
            data['terminationPolicy'] = {
                'keyName':
                    self._termination_policy_to_value(termination_policy)
            }

        data['virtualGuestMemberTemplate'] = template

        res = self.connection.request('SoftLayer_Scale_Group',
                                      'createObject', data).object

        _wait_for_creation(res['id'])
        mask = {
            'terminationPolicy': ''
        }

        res = self.connection.request('SoftLayer_Scale_Group', 'getObject',
                                      object_mask=mask, id=res['id']).object
        group = self._to_autoscale_group(res)

        return group

    def list_auto_scale_group_members(self, group):
        mask = {
            'virtualGuest': {
                'billingItem': '',
                'powerState': '',
                'operatingSystem': {'passwords': ''},
                'provisionDate': ''
            }
        }

        res = self.connection.request('SoftLayer_Scale_Group',
                                      'getVirtualGuestMembers',
                                      id=group.id).object

        nodes = []
        for r in res:
            # NOTE: r[id]  is ID of virtual guest member
            # (not instance itself)
            res_node = self.connection.request('SoftLayer_Scale_Member_'
                                               'Virtual_Guest',
                                               'getVirtualGuest', id=r['id'],
                                               object_mask=mask).object

            nodes.append(self._to_node(res_node))

        return nodes

    def create_auto_scale_policy(self, group, name, adjustment_type,
                                 scaling_adjustment):
        """
        Create an auto scale policy for the given group.

        @inherits: :class:`NodeDriver.create_auto_scale_policy`

        :param group: Group object.
        :type group: :class:`.AutoScaleGroup`

        :param name: Policy name.
        :type name: ``str``

        :param adjustment_type: The adjustment type.
        :type adjustment_type: value within :class:`AutoScaleAdjustmentType`

        :param scaling_adjustment: The number of instances by which to scale.
        :type scaling_adjustment: ``int``

        :return: The newly created policy.
        :rtype: :class:`.AutoScalePolicy`
        """
        data = {}
        data['name'] = name
        data['scaleGroupId'] = int(group.id)

        policy_action = {}
        # 'SCALE'
        policy_action['typeId'] = 1
        policy_action['scaleType'] = \
            self._scale_adjustment_to_value(adjustment_type)
        policy_action['amount'] = scaling_adjustment

        data['scaleActions'] = [policy_action]

        res = self.connection.request('SoftLayer_Scale_Policy',
                                      'createObject', data).object
        mask = {
            'scaleActions': ''
        }

        res = self.connection.request('SoftLayer_Scale_Policy',
                                      'getObject', id=res['id'],
                                      object_mask=mask).object
        policy = self._to_autoscale_policy(res)

        return policy

    def list_auto_scale_policies(self, group):
        mask = {
            'policies': {
                'scaleActions': ''
            }
        }

        res = self.connection.request('SoftLayer_Scale_Group', 'getPolicies',
                                      id=group.id, object_mask=mask).object
        return [self._to_autoscale_policy(r) for r in res]

    def delete_auto_scale_policy(self, policy):
        self.connection.request('SoftLayer_Scale_Policy',
                                'deleteObject', id=policy.id).object
        return True

    def create_auto_scale_alarm(self, name, policy, metric_name, operator,
                                threshold, period, **kwargs):
        """
        Create an auto scale alarm for the given policy.

        @inherits: :class:`NodeDriver.create_auto_scale_alarm`

        :param name: Descriptive name of the alarm.
        :type name: ``str``

        :param policy: Policy object.
        :type policy: :class:`.AutoScalePolicy`

        :param metric_name: The metric to watch.
        :type metric_name: value within :class:`AutoScaleMetric`

        :param operator: The operator to use for comparison.
        :type operator: value within :class:`AutoScaleOperator`

        :param threshold: The value against which the specified statistic is
                          compared.
        :type threshold: ``int``

        :param name: The descriptive name for the alarm.
        :type name: ``str``

        :param period: The number of seconds the values are aggregated for when
                       compared to threshold.
        :type period: ``int``

        :return: The newly created alarm.
        :rtype: :class:`.AutoScaleAlarm`
        """

        data = {}
        # 'RESOURCE_USE'
        data['typeId'] = 3
        data['scalePolicyId'] = policy.id

        trigger_watch = {}
        trigger_watch['algorithm'] = 'EWMA'
        trigger_watch['metric'] = self._metric_to_value(metric_name)

        trigger_watch['operator'] = \
            self._operator_type_to_value(operator)

        trigger_watch['value'] = threshold
        trigger_watch['period'] = period

        data['watches'] = [trigger_watch]

        res = self.connection.\
            request('SoftLayer_Scale_Policy_Trigger_ResourceUse',
                    'createObject', data).object

        mask = {
            'watches': ''
        }

        res = self.connection.\
            request('SoftLayer_Scale_Policy_Trigger_ResourceUse',
                    'getObject', id=res['id'], object_mask=mask).object
        alarm = self._to_autoscale_alarm(res)

        return alarm

    def list_auto_scale_alarms(self, policy):
        mask = {
            'resourceUseTriggers': {
                'watches': ''
            }
        }

        res = self.connection.request('SoftLayer_Scale_Policy',
                                      'getResourceUseTriggers',
                                      object_mask=mask, id=policy.id).object
        return [self._to_autoscale_alarm(r) for r in res]

    def delete_auto_scale_alarm(self, alarm):
        self.connection.request('SoftLayer_Scale_Policy_Trigger_ResourceUse',
                                'deleteObject', id=alarm.id).object
        return True

    def delete_auto_scale_group(self, group):
        DEFAULT_TIMEOUT = 12000

        def _wait_for_deletion(group_name):
            # 5 seconds
            POLL_INTERVAL = 5

            end = time.time() + DEFAULT_TIMEOUT
            completed = False
            while time.time() < end and not completed:
                try:
                    self._get_auto_scale_group(group_name)
                    time.sleep(POLL_INTERVAL)
                except SoftLayerObjectDoesntExist:
                    # for now treat this as not found
                    completed = True
            if not completed:
                raise LibcloudError('Operation did not complete in %s seconds'
                                    % (DEFAULT_TIMEOUT))

        self.connection.request(
            'SoftLayer_Scale_Group', 'forceDeleteObject', id=group.id).object

        _wait_for_deletion(group.name)

        return True

    def _get_auto_scale_group(self, group_name):

        groups = self.list_auto_scale_groups()
        group = find(groups, lambda g: g.name == group_name)
        if not group:
            raise SoftLayerObjectDoesntExist('Group name: %s does not exist'
                                             % group_name)
        return group

    def _get_group_status(self, group_id):
        res = self.connection.request('SoftLayer_Scale_Group',
                                      'getStatus', id=group_id).object
        return res['keyName']

    def _to_autoscale_policy(self, plc):

        plc_id = plc['id']
        name = plc['name']

        adj_type = None
        adjustment_type = None
        scaling_adjustment = None

        if plc.get('scaleActions', []):

            adj_type = plc['scaleActions'][0]['scaleType']
            adjustment_type = self._value_to_scale_adjustment(adj_type)
            scaling_adjustment = plc['scaleActions'][0]['amount']

        return AutoScalePolicy(id=plc_id, name=name,
                               adjustment_type=adjustment_type,
                               scaling_adjustment=scaling_adjustment,
                               driver=self.connection.driver)

    def _to_autoscale_groups(self, res):
        groups = [self._to_autoscale_group(grp) for grp in res]
        return groups

    def _to_autoscale_group(self, grp):

        grp_id = grp['id']
        name = grp['name']
        cooldown = grp['cooldown']
        min_size = grp['minimumMemberCount']
        max_size = grp['maximumMemberCount']

        sl_tp = self._value_to_termination_policy(
            grp['terminationPolicy']['keyName'])
        termination_policies = [sl_tp]

        extra = {}
        extra['id'] = grp_id
        extra['state'] = grp['status']['keyName']
        # TODO: set with region name
        extra['region'] = 'softlayer'
        extra['regionalGroupId'] = grp['regionalGroupId']
        extra['suspendedFlag'] = grp['suspendedFlag']
        extra['terminationPolicyId'] = grp['terminationPolicyId']

        return AutoScaleGroup(id=grp_id, name=name, cooldown=cooldown,
                              min_size=min_size, max_size=max_size,
                              termination_policies=termination_policies,
                              driver=self.connection.driver,
                              extra=extra)

    def _to_autoscale_alarm(self, alrm):

        alrm_id = alrm['id']

        metric = None
        operator = None
        period = None
        threshold = None

        if alrm.get('watches', []):

            metric = self._value_to_metric(alrm['watches'][0]['metric'])
            op = alrm['watches'][0]['operator']
            operator = self._value_to_operator_type(op)
            period = alrm['watches'][0]['period']
            threshold = alrm['watches'][0]['value']

        return AutoScaleAlarm(id=alrm_id, name='N/A', metric_name=metric,
                              operator=operator, period=period,
                              threshold=int(threshold),
                              driver=self.connection.driver)
