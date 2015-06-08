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
from libcloud.common.base import ConnectionKey, BaseDriver, LibcloudError


class AutoScaleGroup(object):
    """Base class for auto scale group
    """
    def __init__(self, id, name, min_size, max_size, cooldown,
                 termination_policies, driver, extra=None):
        """
        :param name: name.
        :type name: ``str``

        :param min_size: Minimum membership size of group.
        :type min_size: ``int``

        :param max_size: Maximum membership size of group.
        :type max_size: ``int``

        :param cooldown: Group cooldown (in seconds).
        :type cooldown: ``int``

        :param termination_policies: Termination policies for this group.
        :type termination_policies: array of values within
                                  :class:`AutoScaleTerminationPolicy`
        """
        self.id = str(id) if id else None
        self.name = name
        self.min_size = min_size
        self.max_size = max_size
        self.cooldown = cooldown
        self.termination_policies = termination_policies
        self.driver = driver

        self.extra = extra or {}

    def __repr__(self):
        return (('<AutoScaleGroup: id=%s, name=%s, min_size=%s, max_size=%s, '
                 'cooldown=%s, termination_policies=%s, provider=%s>')
                % (self.id, self.name, self.min_size, self.max_size,
                   self.cooldown, self.termination_policies, self.driver.name))


class AutoScalePolicy(object):
    """Base class for scaling policy
    """
    def __init__(self, id, name, scaling_adjustment, adjustment_type,
                 driver, extra=None):
        """
        :param name: Policy name
        :type name: str

        :param scaling_adjustment: Adjustment amount.
        :type scaling_adjustment: int

        :param adjustment_type: The adjustment type.
        :type adjustment_type: value within :class:`AutoScaleAdjustmentType`
        """
        self.id = str(id) if id else None
        self.name = name
        self.adjustment_type = adjustment_type
        self.scaling_adjustment = scaling_adjustment

        self.driver = driver
        self.extra = extra or {}

    def __repr__(self):
        return (
            ('<AutoScalePolicy: id=%s, name=%s, adjustment_type=%s, '
             'scaling_adjustment=%s, provider=%s>') % (
                 self.id, self.name, self.adjustment_type,
                 self.scaling_adjustment, self.driver.name))


class AutoScaleAlarm(object):
    """Base class for alarm triggering
    """

    def __init__(self, id, name, metric_name, period, operator, threshold,
                 driver, extra=None):
        """
        :param name: Descriptive name of the alarm.
        :type name: ``str``

        :param metric_name: The metric to watch.
        :type metric_name: ``str``

        :param period: The number of seconds the values are aggregated for when
                       compared to value.
        :type period: ``int``

        :param operator: The operator to use for comparison.
        :type operator: value within :class:`AutoScaleOperator`

        :param threshold: The value against which the specified statistic is
                          compared
        :type threshold: ``int``
        """
        self.id = str(id) if id else None
        self.name = name
        self.metric_name = metric_name
        self.period = period
        self.operator = operator
        self.threshold = threshold
        self.statistic = 'AVG'

        self.driver = driver
        self.extra = extra or {}

    def __repr__(self):
        return (
            ('<AutoScaleAlarm: id=%s, metric_name=%s, period=%s, '
             'operator=%s, threshold=%s, statistic=%s, '
             'provider=%s>') % (self.id, self.metric_name, self.period,
                                self.operator, self.threshold,
                                self.statistic, self.driver.name))


class AutoScaleDriver(BaseDriver):
    """
    A base AutoScaleDriver class to derive from.

    This class is always subclassed by a specific driver.

    """
    connectionCls = ConnectionKey

    name = None
    type = None
    port = None

    _SCALE_OPERATOR_TYPE_TO_VALUE_MAP = {}
    _VALUE_TO_SCALE_OPERATOR_TYPE_MAP = {}

    _METRIC_TO_VALUE_MAP = {}
    _VALUE_TO_METRIC_MAP = {}

    _SCALE_ADJUSTMENT_TYPE_TO_VALUE_MAP = {}
    _VALUE_TO_SCALE_ADJUSTMENT_TYPE_MAP = {}

    _TERMINATION_POLICY_TO_VALUE_MAP = {}
    _VALUE_TO_TERMINATION_POLICY_MAP = {}

    def __init__(self, key, secret=None, secure=True, host=None,
                 port=None, api_version=None, **kwargs):
        super(AutoScaleDriver, self).__init__(
            key=key, secret=secret, secure=secure, host=host,
            port=port, api_version=api_version, **kwargs)

    def create_auto_scale_group(
            self, group_name, min_size, max_size, cooldown,
            termination_policies, **kwargs):
        """
        Create a new auto scale group. Group's instances will be started
        automatically. Some of the keyward arguments are driver specific
        implementation.

        :param group_name: Group name.
        :type group_name: ``str``

        :param min_size: Minimum membership size of group.
        :type min_size: ``int``

        :param max_size: Maximum membership size of group.
        :type max_size: ``int``

        :param cooldown: Group cooldown (in seconds).
        :type cooldown: ``int``

        :param termination_policies: Termination policies for this group.
        :type termination_policy: list of values within
                                  :class:`AutoScaleTerminationPolicy`

        :keyword    name: The name to assign the group members with.
                          (required)
        :type       name: ``str``

        :keyword    size: Size definition for group members instances.
                          (required)
        :type       size: :class:`.NodeSize`

        :keyword    image: The image to create the member with. (required)
        :type       image: :class:`.NodeImage`

        :keyword    location: Which location to create the members in.
        :type       location: :class:`.NodeLocation`

        :return: The newly created scale group.
        :rtype: :class:`.AutoScaleGroup`
        """

        raise NotImplementedError(
            'create_auto_scale_group not implemented for this driver')

    def list_auto_scale_groups(self):
        """
        :rtype: ``list`` of ``AutoScaleGroup``
        """
        raise NotImplementedError(
            'list_auto_scale_groups not implemented for this driver')

    def list_auto_scale_group_members(self, group):
        """
        List members for given auto scale group.

        :param group: Group object.
        :type group: :class:`.AutoScaleGroup`

        :return: Group members.
        :rtype: ``list`` of ``Node``
        """
        raise NotImplementedError(
            'list_auto_scale_group_members not implemented for this driver')

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

        :return: The created policy.
        :rtype: :class:`.AutoScalePolicy`
        """

        raise NotImplementedError(
            'create_auto_scale_policy not implemented for this driver')

    def list_auto_scale_policies(self, group):
        """
        List policies assiciated with the given auto scale group

        :param policy: Group object.
        :type policy: :class:`.AutoScaleGroup`

        :rtype: ``list`` of ``AutoScalePolicy``
        """
        raise NotImplementedError(
            'list_auto_scale_policies not implemented for this driver')

    def delete_auto_scale_policy(self, policy):
        """
        Delete auto scale policy.

        :param policy: Policy object.
        :type policy: :class:`.AutoScalePolicy`

        :return: ``True`` if delete_auto_scale_policy was successful,
        ``False`` otherwise.
        :rtype: ``bool``

        """
        raise NotImplementedError(
            'delete_auto_scale_policy not implemented for this driver')

    def create_auto_scale_alarm(self, name, policy, metric_name, operator,
                                threshold, period, **kwargs):
        """
        Create an auto scale alarm for the given policy.

        :param name: Descriptive name of the alarm.
        :type name: ``str``

        :param policy: Policy object.
        :type policy: :class:`.AutoScalePolicy`

        :param metric_name: The metric to watch.
        :type metric_name: value within :class:`AutoScaleMetric`

        :param operator: The operator to use for comparison.
        :type operator: value within :class:`AutoScaleOperator`

        :param threshold: The value against which the specified statistic is
                          compared
        :type threshold: ``int``

        :param name: The descriptive name for the alarm.
        :type name: ``str``

        :param period: The number of seconds the values are aggregated for when
                       compared to threshold.
        :type period: ``int``

        :return: The created alarm.
        :rtype: :class:`.AutoScaleAlarm`
        """

        raise NotImplementedError(
            'create_auto_scale_alarm not implemented for this driver')

    def list_auto_scale_alarms(self, policy):
        """
        List alarms assiciated with the given auto scale policy

        :param policy: Policy object.
        :type policy: :class:`.AutoScalePolicy`

        :rtype: ``list`` of ``AutoScaleAlarm``
        """
        raise NotImplementedError(
            'list_auto_scale_alarms not implemented for this driver')

    def delete_auto_scale_alarm(self, alarm):
        """
        Delete auto scale alarm.

        :param alarm: Alarm object.
        :type alarm: :class:`.AutoScaleAlarm`

        :return: ``True`` if delete_auto_scale_alarm was successful,
        ``False`` otherwise.
        :rtype: ``bool``

        """
        raise NotImplementedError(
            'delete_auto_scale_alarm not implemented for this driver')

    def delete_auto_scale_group(self, group):
        """
        Delete auto scale group.

        :param group: Group object.
        :type group: :class:`.AutoScaleGroup`

        :return: ``True`` if delete_auto_scale_group was successful,
        ``False`` otherwise.
        :rtype: ``bool``

        """
        raise NotImplementedError(
            'delete_auto_scale_group not implemented for this driver')

    def list_supported_scale_adjustment_types(self):
        """
        Return scale adjustment types supported by this driver.

        :rtype: ``list`` of ``str``
        """
        return list(self._SCALE_ADJUSTMENT_TYPE_TO_VALUE_MAP.keys())

    def list_termination_policies(self):
        """
        Return termination policies supported by this driver.

        :rtype: ``list`` of ``str``
        """
        return list(self._TERMINATION_POLICY_TO_VALUE_MAP.keys())

    def list_supported_operator_types(self):
        """
        Return operator types supported by this driver.

        :rtype: ``list`` of ``str``
        """
        return list(self._SCALE_OPERATOR_TYPE_TO_VALUE_MAP.keys())

    def _value_to_scale_adjustment(self, value):
        try:
            return self._VALUE_TO_SCALE_ADJUSTMENT_TYPE_MAP[value]
        except KeyError:
            raise LibcloudError(value='Invalid value: %s' % (value),
                                driver=self)

    def _scale_adjustment_to_value(self, scale_adjustment):
        """
        Return string value for the provided algorithm.

        :param value: Algorithm enum.
        :type  value: :class:`Algorithm`

        :rtype: ``str``
        """
        try:
            return self._SCALE_ADJUSTMENT_TYPE_TO_VALUE_MAP[scale_adjustment]
        except KeyError:
            raise LibcloudError(value='Invalid scale adjustment: %s'
                                % (scale_adjustment), driver=self)

    def _value_to_termination_policy(self, value):
        try:
            return self._VALUE_TO_TERMINATION_POLICY_MAP[value]
        except KeyError:
            raise LibcloudError(value='Invalid value: %s' % (value),
                                driver=self)

    def _termination_policy_to_value(self, termination_policy):
        """
        Return string value for the provided termination policy.

        :param value: AutoScaleTerminationPolicy enum.
        :type  value: :class:`AutoScaleTerminationPolicy`

        :rtype: ``str``
        """
        try:
            return self._TERMINATION_POLICY_TO_VALUE_MAP[termination_policy]
        except KeyError:
            raise LibcloudError(value='Invalid termination policy: %s'
                                % (termination_policy), driver=self)

    def _value_to_operator_type(self, value):

        try:
            return self._VALUE_TO_SCALE_OPERATOR_TYPE_MAP[value]
        except KeyError:
            raise LibcloudError(value='Invalid value: %s' % (value),
                                driver=self)

    def _operator_type_to_value(self, operator_type):
        """
        Return string value for the provided operator.

        :param value: AutoScaleOperator enum.
        :type  value: :class:`AutoScaleOperator`

        :rtype: ``str``
        """
        try:
            return self._SCALE_OPERATOR_TYPE_TO_VALUE_MAP[operator_type]
        except KeyError:
            raise LibcloudError(value='Invalid operator type: %s'
                                % (operator_type), driver=self)

    def _value_to_metric(self, value):

        try:
            return self._VALUE_TO_METRIC_MAP[value]
        except KeyError:
            raise LibcloudError(value='Invalid value: %s' % (value),
                                driver=self)

    def _metric_to_value(self, metric):
        """
        Return string value for the provided metric.

        :param value: AutoScaleMetric enum.
        :type  value: :class:`AutoScaleMetric`

        :rtype: ``str``
        """
        try:
            return self._METRIC_TO_VALUE_MAP[metric]
        except KeyError:
            raise LibcloudError(value='Invalid metric: %s'
                                % (metric), driver=self)
