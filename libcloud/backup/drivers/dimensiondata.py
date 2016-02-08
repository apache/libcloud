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
from libcloud.common.dimensiondata import API_ENDPOINTS
from libcloud.common.dimensiondata import DEFAULT_REGION
from libcloud.common.dimensiondata import TYPES_URN
from libcloud.common.dimensiondata import GENERAL_NS
from libcloud.utils.xml import fixxpath, findtext, findall

BACKUP_NS = 'http://oec.api.opsource.net/schemas/backup'


class DimensionDataBackupClientType(object):
    def __init__(self, type, is_file_system, description):
        self.type = type
        self.is_file_system = is_file_system
        self.description = description


class DimensionDataBackupDetails(object):
    def __init__(self, asset_id, service_plan, state, clients=[]):
        self.asset_id = asset_id
        self.service_plan = service_plan
        self.state = state
        self.clients = clients


class DimensionDataBackupClient(object):
    def __init__(self, type, is_file_system, status, description,
                 schedule_pol, storage_pol, trigger=None, email=None,
                 last_backup_time=None, next_backup=None, download_url=None,
                 total_backup_size=None, running_job=None):
        self.type = type
        self.is_file_system = is_file_system
        self.status = status
        self.description = description
        self.schedule_policy = schedule_pol
        self.storage_policy = storage_pol
        self.trigger = trigger
        self.email = email
        self.last_backup_time = last_backup_time
        self.next_backup = next_backup
        self.total_backup_size = total_backup_size
        self.download_url = download_url
        self.running_job = running_job


class DimensionDataBackupRunningJob(object):
    def __init__(self, id, status, percentage=0):
        self.id = id
        self.percentage = percentage
        self.status = status


class DimensionDataBackupStoragePolicy(object):
    def __init__(self, name, retention_period, secondary_location):
        self.name = name
        self.retention_period = retention_period
        self.secondary_location = secondary_location


class DimensionDataBackupSchedulePolicy(object):
    def __init__(self, name, description):
        self.name = name
        self.description = description


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
        service_plan = extra.get('service_plan', 'Advanced')
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
        :type  target: Instance of :class:`BackupTarget`

        :param name: Name of the target
        :type name: ``str``

        :param address: Hostname, FQDN, IP, file path etc.
        :type address: ``str``

        :param extra: (optional) Extra attributes (driver specific).
        :type extra: ``dict``

        :rtype: Instance of :class:`BackupTarget`
        """
        service_plan = extra.get('servicePlan', 'Advanced')
        request = ET.Element('ModifyBackup',
                             {'xmlns': BACKUP_NS})
        request.set('servicePlan', service_plan)

        self.connection.request_with_orgId_api_1(
            'server/%s/backup/modify' % (target.address),
            method='POST',
            data=ET.tostring(request)).object
        target.extra = extra
        return target

    def delete_target(self, target):
        """
        Delete a backup target

        :param target: Backup target to delete
        :type  target: Instance of :class:`BackupTarget`

        :rtype: ``bool``
        """
        response = self.connection.request_with_orgId_api_1(
            'server/%s/backup?disable' % (target.address),
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

    def ex_add_client_to_target(self, target, client, storage_policy,
                                schedule_policy, trigger, email):
        """
        Add a client to a target

        :param target: Backup target with the backup data
        :type  target: Instance of :class:`BackupTarget` or ``str``

        :param client: Client to add to the target
        :type  client: ``str``

        :param storage_policy: The storage policy for the client
        :type  storage_policy: ``str``

        :param schedule_policy: The storage policy for the client
        :type  schedule_policy: ``str``

        :param trigger: The notify trigger for the client
        :type  trigger: ``str``

        :param email: The notify email for the client
        :type  email: ``str``

        :rtype: ``bool``
        """

        if isinstance(target, BackupTarget):
            server_id = target.address
        else:
            server_id = target

        backup_elm = ET.Element('NewBackupClient',
                                {'xmlns': BACKUP_NS})
        ET.SubElement(backup_elm, "type").text = client
        ET.SubElement(backup_elm, "storagePolicyName").text = storage_policy
        ET.SubElement(backup_elm, "schedulePolicyName").text = schedule_policy
        alerting_elm = ET.SubElement(backup_elm, "alerting")
        ET.SubElement(alerting_elm, "trigger").text = trigger
        ET.SubElement(alerting_elm, "emailAddress").text = email

        response = self.connection.request_with_orgId_api_1(
            'server/%s/backup/client' % (server_id),
            method='POST',
            data=ET.tostring(backup_elm)).object

        response_code = findtext(response, 'result', GENERAL_NS)
        return response_code in ['IN_PROGRESS', 'SUCCESS']

    def ex_get_backup_details_for_target(self, target):
        """
        Returns a list of available backup client types

        :param  target: The backup target to list available types for
        :type   target: :class:`BackupTarget` or ``str``

        :rtype: ``list`` of :class:`DimensionDataBackupDetails`
        """

        if isinstance(target, BackupTarget):
            server_id = target.address
        else:
            server_id = target
        response = self.connection.request_with_orgId_api_1(
            'server/%s/backup' % (server_id),
            method='GET').object
        return self._to_backup_details(response)

    def ex_list_available_client_types(self, target):
        """
        Returns a list of available backup client types

        :param  target: The backup target to list available types for
        :type   target: :class:`BackupTarget`

        :rtype: ``list`` of :class:`DimensionDataBackupClientType`
        """
        response = self.connection.request_with_orgId_api_1(
            'server/%s/backup/client/type' % (target.address),
            method='GET').object
        return self._to_client_types(response)

    def ex_list_available_storage_policies(self, target):
        """
        Returns a list of available backup storage policies

        :param  target: The backup target to list available policies for
        :type   target: :class:`BackupTarget`

        :rtype: ``list`` of :class:`DimensionDataBackupStoragePolicy`
        """
        response = self.connection.request_with_orgId_api_1(
            'server/%s/backup/client/storagePolicy' % (target.address),
            method='GET').object
        return self._to_storage_policies(response)

    def ex_list_available_schedule_policies(self, target):
        """
        Returns a list of available backup schedule policies

        :param  target: The backup target to list available policies for
        :type   target: :class:`BackupTarget`

        :rtype: ``list`` of :class:`DimensionDataBackupSchedulePolicy`
        """
        response = self.connection.request_with_orgId_api_1(
            'server/%s/backup/client/schedulePolicy' % (target.address),
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
        return DimensionDataBackupClientType(
            type=element.get('type'),
            description=element.get('description'),
            is_file_system=bool(element.get('isFileSystem') == 'true')
        )

    def _to_backup_details(self, object):
        return DimensionDataBackupDetails(
            asset_id=object.get('asset_id'),
            service_plan=object.get('servicePlan'),
            state=object.get('state'),
            clients=self._to_clients(object)
        )

    def _to_clients(self, object):
        elements = object.findall(fixxpath('backupClient', BACKUP_NS))

        return [self._to_client(el) for el in elements]

    def _to_client(self, element):
        job = element.find(fixxpath('runningJob', BACKUP_NS))
        running_job = None
        if job is not None:
            running_job = DimensionDataBackupRunningJob(
                id=job.get('id'),
                status=job.get('status'),
                percentage=int(job.get('percentageComplete'))
            )

        return DimensionDataBackupClient(
            type=element.get('type'),
            is_file_system=bool(element.get('isFileSystem') == 'true'),
            status=element.get('status'),
            description=findtext(element, 'description', BACKUP_NS),
            schedule_pol=findtext(element, 'schedulePolicyName', BACKUP_NS),
            storage_pol=findtext(element, 'storagePolicyName', BACKUP_NS),
            download_url=findtext(element, 'downloadUrl', BACKUP_NS),
            running_job=running_job
        )

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
