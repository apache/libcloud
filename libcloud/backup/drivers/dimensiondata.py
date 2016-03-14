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

try:
    from lxml import etree as ET
except ImportError:
    from xml.etree import ElementTree as ET

from libcloud.backup.base import BackupDriver, BackupTarget
from libcloud.backup.types import BackupTargetType
from libcloud.backup.types import Provider
from libcloud.common.dimensiondata import DimensionDataConnection
from libcloud.common.dimensiondata import DimensionDataBackupClient
from libcloud.common.dimensiondata import DimensionDataBackupClientAlert
from libcloud.common.dimensiondata import DimensionDataBackupClientRunningJob
from libcloud.common.dimensiondata import DimensionDataBackupClientType
from libcloud.common.dimensiondata import DimensionDataBackupDetails
from libcloud.common.dimensiondata import DimensionDataBackupSchedulePolicy
from libcloud.common.dimensiondata import DimensionDataBackupStoragePolicy
from libcloud.common.dimensiondata import API_ENDPOINTS, DEFAULT_REGION
from libcloud.common.dimensiondata import TYPES_URN
from libcloud.common.dimensiondata import GENERAL_NS, BACKUP_NS
from libcloud.utils.py3 import basestring
from libcloud.utils.xml import fixxpath, findtext, findall

DEFAULT_BACKUP_PLAN = 'Advanced'


class DimensionDataBackupDriver(BackupDriver):
    """
    DimensionData backup driver.
    """

    selected_region = None
    connectionCls = DimensionDataConnection
    name = 'Dimension Data Backup'
    website = 'https://cloud.dimensiondata.com/'
    type = Provider.DIMENSIONDATA
    api_version = 1.0

    network_domain_id = None

    def __init__(self, key, secret=None, secure=True, host=None, port=None,
                 api_version=None, region=DEFAULT_REGION, **kwargs):

        if region not in API_ENDPOINTS:
            raise ValueError('Invalid region: %s' % (region))

        self.selected_region = API_ENDPOINTS[region]

        super(DimensionDataBackupDriver, self).__init__(
            key=key, secret=secret,
            secure=secure, host=host,
            port=port,
            api_version=api_version,
            region=region,
            **kwargs)

    def _ex_connection_class_kwargs(self):
        """
            Add the region to the kwargs before the connection is instantiated
        """

        kwargs = super(DimensionDataBackupDriver,
                       self)._ex_connection_class_kwargs()
        kwargs['region'] = self.selected_region
        return kwargs

    def get_supported_target_types(self):
        """
        Get a list of backup target types this driver supports

        :return: ``list`` of :class:``BackupTargetType``
        """
        return [BackupTargetType.VIRTUAL]

    def list_targets(self):
        """
        List all backuptargets

        :rtype: ``list`` of :class:`BackupTarget`
        """
        targets = self._to_targets(
            self.connection.request_with_orgId_api_2('server/server').object)
        return targets

    def create_target(self, name, address,
                      type=BackupTargetType.VIRTUAL, extra=None):
        """
        Creates a new backup target

        :param name: Name of the target (not used)
        :type name: ``str``

        :param address: The ID of the node in Dimension Data Cloud
        :type address: ``str``

        :param type: Backup target type, only Virtual supported
        :type type: :class:`BackupTargetType`

        :param extra: (optional) Extra attributes (driver specific).
        :type extra: ``dict``

        :rtype: Instance of :class:`BackupTarget`
        """
        if extra is not None:
            service_plan = extra.get('servicePlan', DEFAULT_BACKUP_PLAN)
        else:
            service_plan = DEFAULT_BACKUP_PLAN

        create_node = ET.Element('NewBackup',
                                 {'xmlns': BACKUP_NS})
        create_node.set('servicePlan', service_plan)

        response = self.connection.request_with_orgId_api_1(
            'server/%s/backup' % (address),
            method='POST',
            data=ET.tostring(create_node)).object

        asset_id = None
        for info in findall(response,
                            'additionalInformation',
                            GENERAL_NS):
            if info.get('name') == 'assetId':
                asset_id = findtext(info, 'value', GENERAL_NS)

        return BackupTarget(
            id=asset_id,
            name=name,
            address=address,
            type=type,
            extra=extra,
            driver=self
        )

    def create_target_from_node(self, node, type=BackupTargetType.VIRTUAL,
                                extra=None):
        """
        Creates a new backup target from an existing node

        :param node: The Node to backup
        :type  node: ``Node``

        :param type: Backup target type (Physical, Virtual, ...).
        :type type: :class:`BackupTargetType`

        :param extra: (optional) Extra attributes (driver specific).
        :type extra: ``dict``

        :rtype: Instance of :class:`BackupTarget`
        """
        return self.create_target(name=node.name,
                                  address=node.id,
                                  type=BackupTargetType.VIRTUAL,
                                  extra=extra)

    def create_target_from_container(self, container,
                                     type=BackupTargetType.OBJECT,
                                     extra=None):
        """
        Creates a new backup target from an existing storage container

        :param node: The Container to backup
        :type  node: ``Container``

        :param type: Backup target type (Physical, Virtual, ...).
        :type type: :class:`BackupTargetType`

        :param extra: (optional) Extra attributes (driver specific).
        :type extra: ``dict``

        :rtype: Instance of :class:`BackupTarget`
        """
        return NotImplementedError(
            'create_target_from_container not supported for this driver')

    def update_target(self, target, name=None, address=None, extra=None):
        """
        Update the properties of a backup target, only changing the serviceplan
        is supported.

        :param target: Backup target to update
        :type  target: Instance of :class:`BackupTarget` or ``str``

        :param name: Name of the target
        :type name: ``str``

        :param address: Hostname, FQDN, IP, file path etc.
        :type address: ``str``

        :param extra: (optional) Extra attributes (driver specific).
        :type extra: ``dict``

        :rtype: Instance of :class:`BackupTarget`
        """
        if extra is not None:
            service_plan = extra.get('servicePlan', DEFAULT_BACKUP_PLAN)
        else:
            service_plan = DEFAULT_BACKUP_PLAN
        request = ET.Element('ModifyBackup',
                             {'xmlns': BACKUP_NS})
        request.set('servicePlan', service_plan)
        server_id = self._target_to_target_address(target)
        self.connection.request_with_orgId_api_1(
            'server/%s/backup/modify' % (server_id),
            method='POST',
            data=ET.tostring(request)).object
        if isinstance(target, BackupTarget):
            target.extra = extra
        else:
            target = self.ex_get_target_by_id(server_id)
        return target

    def delete_target(self, target):
        """
        Delete a backup target

        :param target: Backup target to delete
        :type  target: Instance of :class:`BackupTarget` or ``str``

        :rtype: ``bool``
        """
        server_id = self._target_to_target_address(target)
        response = self.connection.request_with_orgId_api_1(
            'server/%s/backup?disable' % (server_id),
            method='GET').object
        response_code = findtext(response, 'result', GENERAL_NS)
        return response_code in ['IN_PROGRESS', 'SUCCESS']

    def list_recovery_points(self, target, start_date=None, end_date=None):
        """
        List the recovery points available for a target

        :param target: Backup target to delete
        :type  target: Instance of :class:`BackupTarget`

        :param start_date: The start date to show jobs between (optional)
        :type  start_date: :class:`datetime.datetime`

        :param end_date: The end date to show jobs between (optional)
        :type  end_date: :class:`datetime.datetime``

        :rtype: ``list`` of :class:`BackupTargetRecoveryPoint`
        """
        raise NotImplementedError(
            'list_recovery_points not implemented for this driver')

    def recover_target(self, target, recovery_point, path=None):
        """
        Recover a backup target to a recovery point

        :param target: Backup target to delete
        :type  target: Instance of :class:`BackupTarget`

        :param recovery_point: Backup target with the backup data
        :type  recovery_point: Instance of :class:`BackupTarget`

        :param path: The part of the recovery point to recover (optional)
        :type  path: ``str``

        :rtype: Instance of :class:`BackupTargetJob`
        """
        raise NotImplementedError(
            'recover_target not implemented for this driver')

    def recover_target_out_of_place(self, target, recovery_point,
                                    recovery_target, path=None):
        """
        Recover a backup target to a recovery point out-of-place

        :param target: Backup target with the backup data
        :type  target: Instance of :class:`BackupTarget`

        :param recovery_point: Backup target with the backup data
        :type  recovery_point: Instance of :class:`BackupTarget`

        :param recovery_target: Backup target with to recover the data to
        :type  recovery_target: Instance of :class:`BackupTarget`

        :param path: The part of the recovery point to recover (optional)
        :type  path: ``str``

        :rtype: Instance of :class:`BackupTargetJob`
        """
        raise NotImplementedError(
            'recover_target_out_of_place not implemented for this driver')

    def get_target_job(self, target, id):
        """
        Get a specific backup job by ID

        :param target: Backup target with the backup data
        :type  target: Instance of :class:`BackupTarget`

        :param id: Backup target with the backup data
        :type  id: Instance of :class:`BackupTarget`

        :rtype: :class:`BackupTargetJob`
        """
        jobs = self.list_target_jobs(target)
        return list(filter(lambda x: x.id == id, jobs))[0]

    def list_target_jobs(self, target):
        """
        List the backup jobs on a target

        :param target: Backup target with the backup data
        :type  target: Instance of :class:`BackupTarget`

        :rtype: ``list`` of :class:`BackupTargetJob`
        """
        raise NotImplementedError(
            'list_target_jobs not implemented for this driver')

    def create_target_job(self, target, extra=None):
        """
        Create a new backup job on a target

        :param target: Backup target with the backup data
        :type  target: Instance of :class:`BackupTarget`

        :param extra: (optional) Extra attributes (driver specific).
        :type extra: ``dict``

        :rtype: Instance of :class:`BackupTargetJob`
        """
        raise NotImplementedError(
            'create_target_job not implemented for this driver')

    def resume_target_job(self, target, job):
        """
        Resume a suspended backup job on a target

        :param target: Backup target with the backup data
        :type  target: Instance of :class:`BackupTarget`

        :param job: Backup target job to resume
        :type  job: Instance of :class:`BackupTargetJob`

        :rtype: ``bool``
        """
        raise NotImplementedError(
            'resume_target_job not implemented for this driver')

    def suspend_target_job(self, target, job):
        """
        Suspend a running backup job on a target

        :param target: Backup target with the backup data
        :type  target: Instance of :class:`BackupTarget`

        :param job: Backup target job to suspend
        :type  job: Instance of :class:`BackupTargetJob`

        :rtype: ``bool``
        """
        raise NotImplementedError(
            'suspend_target_job not implemented for this driver')

    def cancel_target_job(self, target, job):
        """
        Cancel a backup job on a target

        :param target: Backup target with the backup data
        :type  target: Instance of :class:`BackupTarget`

        :param job: Backup target job to cancel
        :type  job: Instance of :class:`BackupTargetJob`

        :rtype: ``bool``
        """
        raise NotImplementedError(
            'cancel_target_job not implemented for this driver')

    def ex_get_target_by_id(self, id):
        """
        Get a target by server id

        :param id: The id of the target you want to get
        :type  id: ``str``

        :rtype: :class:`BackupTarget`
        """
        node = self.connection.request_with_orgId_api_2(
            'server/server/%s' % id).object
        return self._to_target(node)

    def ex_add_client_to_target(self, target, client_type, storage_policy,
                                schedule_policy, trigger, email):
        """
        Add a client to a target

        :param target: Backup target with the backup data
        :type  target: Instance of :class:`BackupTarget` or ``str``

        :param client: Client to add to the target
        :type  client: Instance of :class:`DimensionDataBackupClientType`
                       or ``str``

        :param storage_policy: The storage policy for the client
        :type  storage_policy: Instance of
                               :class:`DimensionDataBackupStoragePolicy`
                               or ``str``

        :param schedule_policy: The schedule policy for the client
        :type  schedule_policy: Instance of
                                :class:`DimensionDataBackupSchedulePolicy`
                                or ``str``

        :param trigger: The notify trigger for the client
        :type  trigger: ``str``

        :param email: The notify email for the client
        :type  email: ``str``

        :rtype: ``bool``
        """
        server_id = self._target_to_target_address(target)

        backup_elm = ET.Element('NewBackupClient',
                                {'xmlns': BACKUP_NS})
        if isinstance(client_type, DimensionDataBackupClientType):
            ET.SubElement(backup_elm, "type").text = client_type.type
        else:
            ET.SubElement(backup_elm, "type").text = client_type

        if isinstance(storage_policy, DimensionDataBackupStoragePolicy):
            ET.SubElement(backup_elm,
                          "storagePolicyName").text = storage_policy.name
        else:
            ET.SubElement(backup_elm,
                          "storagePolicyName").text = storage_policy

        if isinstance(schedule_policy, DimensionDataBackupSchedulePolicy):
            ET.SubElement(backup_elm,
                          "schedulePolicyName").text = schedule_policy.name
        else:
            ET.SubElement(backup_elm,
                          "schedulePolicyName").text = schedule_policy

        alerting_elm = ET.SubElement(backup_elm, "alerting")
        alerting_elm.set('trigger', trigger)
        ET.SubElement(alerting_elm, "emailAddress").text = email

        response = self.connection.request_with_orgId_api_1(
            'server/%s/backup/client' % (server_id),
            method='POST',
            data=ET.tostring(backup_elm)).object
        response_code = findtext(response, 'result', GENERAL_NS)
        return response_code in ['IN_PROGRESS', 'SUCCESS']

    def ex_remove_client_from_target(self, target, backup_client):
        """
        Removes a client from a backup target

        :param  target: The backup target to remove the client from
        :type   target: :class:`BackupTarget` or ``str``

        :param  backup_client: The backup client to remove
        :type   backup_client: :class:`DimensionDataBackupClient` or ``str``

        :rtype: ``bool``
        """
        server_id = self._target_to_target_address(target)
        client_id = self._client_to_client_id(backup_client)
        response = self.connection.request_with_orgId_api_1(
            'server/%s/backup/client/%s?disable' % (server_id, client_id),
            method='GET').object
        response_code = findtext(response, 'result', GENERAL_NS)
        return response_code in ['IN_PROGRESS', 'SUCCESS']

    def ex_get_backup_details_for_target(self, target):
        """
        Returns a backup details object for a target

        :param  target: The backup target to get details for
        :type   target: :class:`BackupTarget` or ``str``

        :rtype: :class:`DimensionDataBackupDetails`
        """
        server_id = self._target_to_target_address(target)
        response = self.connection.request_with_orgId_api_1(
            'server/%s/backup' % (server_id),
            method='GET').object
        return self._to_backup_details(response)

    def ex_list_available_client_types(self, target):
        """
        Returns a list of available backup client types

        :param  target: The backup target to list available types for
        :type   target: :class:`BackupTarget` or ``str``

        :rtype: ``list`` of :class:`DimensionDataBackupClientType`
        """
        server_id = self._target_to_target_address(target)
        response = self.connection.request_with_orgId_api_1(
            'server/%s/backup/client/type' % (server_id),
            method='GET').object
        return self._to_client_types(response)

    def ex_list_available_storage_policies(self, target):
        """
        Returns a list of available backup storage policies

        :param  target: The backup target to list available policies for
        :type   target: :class:`BackupTarget` or ``str``

        :rtype: ``list`` of :class:`DimensionDataBackupStoragePolicy`
        """
        server_id = self._target_to_target_address(target)
        response = self.connection.request_with_orgId_api_1(
            'server/%s/backup/client/storagePolicy' % (server_id),
            method='GET').object
        return self._to_storage_policies(response)

    def ex_list_available_schedule_policies(self, target):
        """
        Returns a list of available backup schedule policies

        :param  target: The backup target to list available policies for
        :type   target: :class:`BackupTarget` or ``str``

        :rtype: ``list`` of :class:`DimensionDataBackupSchedulePolicy`
        """
        server_id = self._target_to_target_address(target)
        response = self.connection.request_with_orgId_api_1(
            'server/%s/backup/client/schedulePolicy' % (server_id),
            method='GET').object
        return self._to_schedule_policies(response)

    def _to_storage_policies(self, object):
        elements = object.findall(fixxpath('storagePolicy', BACKUP_NS))

        return [self._to_storage_policy(el) for el in elements]

    def _to_storage_policy(self, element):
        return DimensionDataBackupStoragePolicy(
            retention_period=int(element.get('retentionPeriodInDays')),
            name=element.get('name'),
            secondary_location=element.get('secondaryLocation')
        )

    def _to_schedule_policies(self, object):
        elements = object.findall(fixxpath('schedulePolicy', BACKUP_NS))

        return [self._to_schedule_policy(el) for el in elements]

    def _to_schedule_policy(self, element):
        return DimensionDataBackupSchedulePolicy(
            name=element.get('name'),
            description=element.get('description')
        )

    def _to_client_types(self, object):
        elements = object.findall(fixxpath('backupClientType', BACKUP_NS))

        return [self._to_client_type(el) for el in elements]

    def _to_client_type(self, element):
        description = element.get('description')
        if description is None:
            description = findtext(element, 'description', BACKUP_NS)
        return DimensionDataBackupClientType(
            type=element.get('type'),
            description=description,
            is_file_system=bool(element.get('isFileSystem') == 'true')
        )

    def _to_backup_details(self, object):
        return DimensionDataBackupDetails(
            asset_id=object.get('asset_id'),
            service_plan=object.get('servicePlan'),
            status=object.get('state'),
            clients=self._to_clients(object)
        )

    def _to_clients(self, object):
        elements = object.findall(fixxpath('backupClient', BACKUP_NS))

        return [self._to_client(el) for el in elements]

    def _to_client(self, element):
        return DimensionDataBackupClient(
            id=element.get('id'),
            type=self._to_client_type(element, ),
            status=element.get('status'),
            schedule_policy=findtext(element, 'schedulePolicyName', BACKUP_NS),
            storage_policy=findtext(element, 'storagePolicyName', BACKUP_NS),
            download_url=findtext(element, 'downloadUrl', BACKUP_NS),
            running_job=self._to_running_job(element),
            alert=self._to_alert(element)
        )

    def _to_alert(self, element):
        alert = element.find(fixxpath('alerting', BACKUP_NS))
        if alert is not None:
            notify_list = [
                email_addr.text for email_addr
                in alert.findall(fixxpath('emailAddress', BACKUP_NS))
            ]
            return DimensionDataBackupClientAlert(
                trigger=element.get('trigger'),
                notify_list=notify_list
            )
        return None

    def _to_running_job(self, element):
        running_job = element.find(fixxpath('runningJob', BACKUP_NS))
        if running_job is not None:
            return DimensionDataBackupClientRunningJob(
                id=running_job.get('id'),
                status=running_job.get('status'),
                percentage=int(running_job.get('percentageComplete'))
            )
        return None

    def _to_targets(self, object):
        node_elements = object.findall(fixxpath('server', TYPES_URN))

        return [self._to_target(el) for el in node_elements]

    def _to_target(self, element):
        backup = findall(element, 'backup', TYPES_URN)
        if len(backup) == 0:
            return
        extra = {
            'description': findtext(element, 'description', TYPES_URN),
            'sourceImageId': findtext(element, 'sourceImageId', TYPES_URN),
            'datacenterId': element.get('datacenterId'),
            'deployedTime': findtext(element, 'createTime', TYPES_URN),
            'servicePlan': backup[0].get('servicePlan')
        }

        n = BackupTarget(id=backup[0].get('assetId'),
                         name=findtext(element, 'name', TYPES_URN),
                         address=element.get('id'),
                         driver=self.connection.driver,
                         type=BackupTargetType.VIRTUAL,
                         extra=extra)
        return n

    @staticmethod
    def _client_to_client_id(backup_client):
        if isinstance(backup_client, DimensionDataBackupClient):
            return backup_client.id
        elif isinstance(backup_client, basestring):
            return backup_client
        else:
            raise TypeError(
                "Invalid backup_client type for _client_to_client_id()"
            )

    @staticmethod
    def _target_to_target_address(target):
        if isinstance(target, BackupTarget):
            return target.address
        elif isinstance(target, basestring):
            return target
        else:
            raise TypeError(
                "Invalid target type for _target_to_target_address()"
            )
