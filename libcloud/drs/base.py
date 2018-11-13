
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

from libcloud.common.base import ConnectionKey
from libcloud.common.base import BaseDriver

__all__ = [
    'DRSConsistencyGroup',
    'DRSDriver',
]


class DRSConsistencyGroup(object):
    """
    Provide a common interface for handling DRS.
    """

    def __init__(self, id, name, description, journalSizeGB,
                 serverPairSourceServerId, serverPairtargetServerId,
                 driver, extra=None):
        """
        :param id: Load balancer ID.
        :type id: ``str``

        :param name: Load balancer name.
        :type name: ``str``

        :param state: State this loadbalancer is in.
        :type state: :class:`libcloud.loadbalancer.types.State`

        :param ip: IP address of this loadbalancer.
        :type ip: ``str``

        :param port: Port of this loadbalancer.
        :type port: ``int``

        :param driver: Driver this loadbalancer belongs to.
        :type driver: :class:`.Driver`

        :param extra: Provider specific attributes. (optional)
        :type extra: ``dict``
        """
        self.id = str(id) if id else None
        self.name = name
        self.description = description
        self.journalSizeGB = journalSizeGB

        self.serverPairSourceServerId = serverPairSourceServerId
        self.serverPairtargetServerId = serverPairtargetServerId
        self.driver = driver
        self.extra = extra or {}


class DRSDriver(BaseDriver):
    """
    A base Driver class to derive from

    This class is always subclassed by a specific driver.
    """

    connectionCls = ConnectionKey
    name = None
    type = None
    port = None

    def __init__(self, key, secret=None, secure=True, host=None,
                 port=None, **kwargs):
        super(DRSDriver, self).__init__(key=key, secret=secret, secure=secure,
                                        host=host, port=port, **kwargs)

    def create_consistency_group(self, name, journal_sz_gb,
                                 source_server_id, target_server_id):
        """
        :param name: Name of the consistency group to create
        :type name: ``str``
        :param journal_sz_gb: Size in 10 Gb increments of the consistency
                              group's journal
        :type journal_sz_gb: ``str``
        :param source_server_id: The id of the server to copy from
        :type source_server_id: ``str``
        :param target_server_id: The id of the server to copy to
        :type target_server_id: ``str``
        :return: :class: `ConsistencyGroup`
        """
        raise NotImplementedError(
            'create_consistency_group not implemented for this driver')

    def list_consistency_groups(self):
        """
        List all consistency groups

        :rtype: ``list`` of :class:`ConsistencyGroup`
        """
        raise NotImplementedError(
            'list_consistency_groups not implemented for this driver')

    def get_consistency_group(self, consistency_group_id):
        """
        Return a :class:`ConsistencyGroup` object.

        :param consistency_group_id: id of a consistency group you want
         to fetch
        :type  consistency_group_id: ``str``

        :rtype: :class:`ConsistencyGroup`
        """

        raise NotImplementedError(
            'get_consistency_group not implemented for this driver')

    def delete_consistency_group(self, consistency_group_id):
        """
        Delete a consistency group

        :param consistency_group_id: Id of consistency group to delete
        :type  consistency_group_id: ``str``

        :return: ``True`` For successful deletion, otherwise ``False``.
        :rtype: ``bool``
        """

        raise NotImplementedError(
            'delete_consistency_group not implemented for this driver')

    def list_consistency_group_snapshots(self, consistency_group_id):
        """
        Return a list of consistency group snapshots.

        :param consistency_group_id: id of a consistency group to fetch
                                     snapshots from.
        :type  consistency_group_id: ``str``
        :rtype: ``list``
        """

        raise NotImplementedError(
            'list_consistency_group_snapshots not implemented for this driver')

    def expand_journal(self, consistency_group_id, size_gb):
        """
        :param consistency_group_id: consistency group's id with journal
                                     to expand
        :type consistency_group_id: ``str``
        :param size_gb: Size in increments of 10 Gb to expand journal.
        :return: ``True`` For successful deletion, otherwise ``False``.
        :rtype: ``bool``
        """

        raise NotImplementedError(
            'expand_journal not implemented for this driver')

    def start_failover_preview(self, consistency_group_id, snapshot_id):
        """
        :param consistency_group_id: consistency group's id with journal
                                     to expand
        :type consistency_group_id: ``str ``
        :param snapshot_id: Snapshot Id to bring into preview mode.
        :type snapshot_id: ``str``
        :return: ``True`` For successful deletion, otherwise ``False``.
        :rtype: ``bool``
        """

        raise NotImplementedError(
            'start_failover_preview not implemented for this driver')

    def stop_failover_preview(self, consistency_group_id):
        """
        :param consistency_group_id: Consistency group id of consistency
                                     group to brought out of
                                     PREVIEWING_SNAHSHOT and into DRS_MODE.
        :type consistency_group_id: ``str``
        :return: ``True`` For successful deletion, otherwise ``False``.
        :rtype: ``bool``
        """

        raise NotImplementedError(
            'stop_failover_preview not implemented for this driver')

    def initiate_failover(self, consistency_group_id):
        """
        :param consistency_group_id: Consistency group id of consistency
                                     group on which to initiate failover.
        :type consistency_group_id: ``str``
        :return: ``True`` For successful deletion, otherwise ``False``.
        :rtype: ``bool``
        """

        raise NotImplementedError(
            'initiate_failover not implemented for this driver')
