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
Azure Compute driver
"""
import uuid
import re
import time
import collections
import random
import sys
import os
import copy

#import azure
#import azure.servicemanagement
#from azure.servicemanagement import ServiceManagementService
#from azure.servicemanagement import WindowsConfigurationSet, ConfigurationSet, LinuxConfigurationSet
#from azure.servicemanagement import ConfigurationSetInputEndpoint

from azure import *
from azure.servicemanagement import *

from libcloud.compute.providers import Provider
from libcloud.compute.base import Node, NodeDriver, NodeLocation, NodeSize
from libcloud.compute.base import NodeImage, StorageVolume, VolumeSnapshot
from libcloud.compute.base import KeyPair, NodeAuthPassword
from libcloud.compute.types import NodeState, KeyPairDoesNotExistError
from libcloud.common.base import ConnectionUserAndKey

"""
Sizes must be hardcoded because Microsoft doesn't provide an API to fetch them.
From http://msdn.microsoft.com/en-us/library/windowsazure/dn197896.aspx
"""
AZURE_COMPUTE_INSTANCE_TYPES = {
    'A0': {
        'id': 'A0',
        'name': 'ExtraSmall Instance',
        'ram': 768,
        'disk': 127,
        'bandwidth': None,
        'price': '0.02',
        'max_data_disks': 1,
        'cores': 'Shared'
    },
    'A1': {
        'id': 'A1',
        'name': 'Small Instance',
        'ram': 1792,
        'disk': 127,
        'bandwidth': None,
        'price': '0.09',
        'max_data_disks': 2,
        'cores': 1
    },
    'A2': {
        'id': 'A2',
        'name': 'Medium Instance',
        'ram': 3584,
        'disk': 127,
        'bandwidth': None,
        'price': '0.18',
        'max_data_disks': 4,
        'cores': 2
    },
    'A3': {
        'id': 'A3',
        'name': 'Large Instance',
        'ram': 7168,
        'disk': 127,
        'bandwidth': None,
        'price': '0.36',
        'max_data_disks': 8,
        'cores': 4
    },
    'A4': {
        'id': 'A4',
        'name': 'ExtraLarge Instance',
        'ram': 14336,
        'disk': 127,
        'bandwidth': None,
        'price': '0.72',
        'max_data_disks': 16,
        'cores': 8
    },
    'A5': {
        'id': 'A5',
        'name': 'Memory Intensive Instance',
        'ram': 14336,
        'disk': 127,
        'bandwidth': None,
        'price': '0.40',
        'max_data_disks': 4,
        'cores': 2
    },
    'A6': {
        'id': 'A6',
        'name': 'A6 Instance',
        'ram': 28672,
        'disk': 127,
        'bandwidth': None,
        'price': '0.80',
        'max_data_disks': 8,
        'cores': 4
    },
    'A7': {
        'id': 'A7',
        'name': 'A7 Instance',
        'ram': 57344,
        'disk': 127,
        'bandwidth': None,
        'price': '1.60',
        'max_data_disks': 16,
        'cores': 8
    }    
}

subscription_id = "aff4792f-fc2c-4fa8-88f4-bab437747469"
certificate_path = "/Users/baldwin/.azure/managementCertificate.pem"

class AzureConnection(ConnectionUserAndKey):
	"""AzureConnection

	Connection class for Azure Compute Driver.
	"""


	#def __init__(self, user_id, key, secure):
	#	super(AzureConnection, self).__init__(user_id, key, secure=secure, **kwargs)

class AzureNodeDriver(NodeDriver):
    
    _instance_types = AZURE_COMPUTE_INSTANCE_TYPES
    _blob_url = ".blob.core.windows.net"
    features = {'create_node': ['password']}
    service_location = collections.namedtuple('service_location',['is_affinity_group', 'service_location'])
    sms = ServiceManagementService(subscription_id, certificate_path)

    def list_sizes(self):
        """
        Lists all sizes

        :rtype: ``list`` of :class:`NodeSize`
        """
        sizes = []

        for key, values in self._instance_types.items():
            node_size = self._to_node_size(copy.deepcopy(values))
            sizes.append(node_size)

        return sizes

    def list_images(self):
        """
        Lists all images

        :rtype: ``list`` of :class:`NodeImage`
        """
        sms = ServiceManagementService(subscription_id, certificate_path)
        
        data = sms.list_os_images()

        return [self._to_image(i) for i in data]

    def list_locations(self):
        """
        Lists all locations

        :rtype: ``list`` of :class:`NodeLocation`
        """
        sms = ServiceManagementService(subscription_id, certificate_path)

        data = sms.list_locations()

        return [self._to_location(l) for l in data]

    def list_nodes(self, ex_cloud_service_name=None):
        """
        List all nodes

        ex_cloud_service_name parameter is used to scope the request 
        to a specific Cloud Service. This is a required parameter as
        nodes cannot exist outside of a Cloud Service nor be shared
        between a Cloud Service within Azure. 

        :param      ex_cloud_service_name: Cloud Service name
        :type       ex_cloud_service_name: ``str``

        :rtype: ``list`` of :class:`Node`
        """
        if not ex_cloud_service_name:
            raise ValueError("ex_cloud_service_name is required.")

        sms = ServiceManagementService(subscription_id, certificate_path)

        data = sms.get_hosted_service_properties(service_name=ex_cloud_service_name,embed_detail=True)

        try:
            return [self._to_node(n) for n in data.deployments[0].role_instance_list]
        except IndexError:
            return None

    def reboot_node(self, node, ex_cloud_service_name=None, ex_deployment_slot=None):
        """
        Reboots a node.

        ex_cloud_service_name parameter is used to scope the request 
        to a specific Cloud Service. This is a required parameter as
        nodes cannot exist outside of a Cloud Service nor be shared
        between a Cloud Service within Azure. 

        :param      ex_cloud_service_name: Cloud Service name
        :type       ex_cloud_service_name: ``str``

        :param      ex_deployment_name: Options are "production" (default)
                                         or "Staging". (Optional)
        :type       ex_deployment_name: ``str``

        :rtype: ``list`` of :class:`Node`
        """
        sms = ServiceManagementService(subscription_id, certificate_path)

        if not ex_cloud_service_name:
            raise ValueError("ex_cloud_service_name is required.")

        if not ex_deployment_slot:
            ex_deployment_slot = "production"

        _deployment_name = self._get_deployment(service_name=ex_cloud_service_name,deployment_slot=ex_deployment_slot).name

        try:
            result = sms.reboot_role_instance(
                service_name=ex_cloud_service_name,
                deployment_name=_deployment_name,
                role_instance_name=node.id
                )
            if result.request_id:
                return True
            else:
                return False
        except Exception:
            return False

    def list_volumes(self, node=None):
        """
        Lists volumes of the disks in the image repository that are
        associated with the specificed subscription.

        Pass Node object to scope the list of volumes to a single
        instance.

        :rtype: ``list`` of :class:`StorageVolume`
        """

        sms = ServiceManagementService(subscription_id, certificate_path)

        data = sms.list_disks()

        volumes = [self._to_volume(volume=v,node=node) for v in data]

        return volumes

    def create_node(self, ex_cloud_service_name=None, **kwargs):
        """Create Azure Virtual Machine

           Reference: http://bit.ly/1fIsCb7 [www.windowsazure.com/en-us/documentation/]

           We default to: 

           + 3389/TCP - RDP - 1st Microsoft instance.
           + RANDOM/TCP - RDP - All succeeding Microsoft instances. 

           + 22/TCP - SSH - 1st Linux instance 
           + RANDOM/TCP - SSH - All succeeding Linux instances.

          The above replicates the standard behavior of the Azure UI. 
          You can retrieve the assigned ports to each instance by 
          using the following private function:

          _get_endpoint_ports(service_name)
            Returns public,private port key pair.

           @inherits: :class:`NodeDriver.create_node`

           :keyword     ex_cloud_service_name: Required. Name of the Azure Cloud Service.
           :type        ex_cloud_service_name:  ``str``

           :keyword     ex_storage_service_name: Optional: Name of the Azure Storage Service.
           :type        ex_cloud_service_name:  ``str``

           :keyword     ex_deployment_name: Optional. The name of the deployment. 
                                            If this is not passed in we default to
                                            using the Cloud Service name.
            :type       ex_deployment_name: ``str``

           :keyword     ex_deployment_slot: Optional: Valid values: production|staging. 
                                            Defaults to production.
           :type        ex_cloud_service_name:  ``str``

           :keyword     ex_linux_user_id: Optional. Defaults to 'azureuser'.
           :type        ex_cloud_service_name:  ``str``

        """
        name = kwargs['name']
        size = kwargs['size']
        image = kwargs['image']

        password = None
        auth = self._get_and_check_auth(kwargs["auth"])        
        password = auth.password

        sms = ServiceManagementService(subscription_id, certificate_path)

        if not ex_cloud_service_name:
            raise ValueError("ex_cloud_service_name is required.")

        if "ex_deployment_slot" in kwargs:
            ex_deployment_slot = kwargs['ex_deployment_slot']
        else:
            ex_deployment_slot = "production" # We assume production if this is not provided. 

        if "ex_linux_user_id" in kwargs:
            ex_linux_user_id = kwargs['ex_linux_user_id']
        else:
            # This mimics the Azure UI behavior.
            ex_linux_user_id = "azureuser"

        node_list = self.list_nodes(ex_cloud_service_name=ex_cloud_service_name)
        network_config = ConfigurationSet()
        network_config.configuration_set_type = 'NetworkConfiguration'

        # We do this because we need to pass a Configuration to the 
        # method. This will be either Linux or Windows. 
        if re.search("Win|SQL|SharePoint|Visual|Dynamics|DynGP|BizTalk", image, re.I): 
            machine_config = WindowsConfigurationSet(name, password)
            machine_config.domain_join = None

            if node_list is None:
                port = "3389"
            else:
                port = random.randint(41952,65535)
                endpoints = self._get_deployment(service_name=ex_cloud_service_name,deployment_slot=ex_deployment_slot)

                for instances in endpoints.role_instance_list:
                    ports = []
                    for ep in instances.instance_endpoints:
                        ports += [ep.public_port]

                    while port in ports:
                        port = random.randint(41952,65535)

            endpoint = ConfigurationSetInputEndpoint(
                name='Remote Desktop',
                protocol='tcp',
                port=port,
                local_port='3389',
                load_balanced_endpoint_set_name=None,
                enable_direct_server_return=False
            )
        else:
            if node_list is None:
                port = "22"
            else:
                port = random.randint(41952,65535)
                endpoints = self._get_deployment(service_name=ex_cloud_service_name,deployment_slot=ex_deployment_slot)

                for instances in endpoints.role_instance_list:
                    ports = []
                    for ep in instances.instance_endpoints:
                        ports += [ep.public_port]

                    while port in ports:
                        port = random.randint(41952,65535)

            endpoint = ConfigurationSetInputEndpoint(
                name='SSH',
                protocol='tcp',
                port=port,
                local_port='22',
                load_balanced_endpoint_set_name=None,
                enable_direct_server_return=False
            )
            machine_config = LinuxConfigurationSet(name, ex_linux_user_id, password, False)

        network_config.input_endpoints.input_endpoints.append(endpoint)

        _storage_location = self._get_cloud_service_location(service_name=ex_cloud_service_name)
        
        # OK, bit annoying here. You must create a deployment before
        # you can create an instance; however, the deployment function
        # creates the first instance, but all subsequent instances
        # must be created using the add_role function. 
        #
        # So, yeah, annoying.
        if node_list is None:
            # This is the first node in this cloud service.
            if "ex_storage_service_name" in kwargs:
                ex_storage_service_name = kwargs['ex_storage_service_name'] 
            else:
                ex_storage_service_name = ex_cloud_service_name
                ex_storage_service_name = re.sub(ur'[\W_]+', u'', ex_storage_service_name.lower(), flags=re.UNICODE)
                if self._is_storage_service_unique(service_name=ex_storage_service_name):
                    self._create_storage_account(
                        service_name=ex_storage_service_name,
                        location=_storage_location.service_location,
                        is_affinity_group=_storage_location.is_affinity_group
                        )

            if "ex_deployment_name" in kwargs:
                ex_deployment_name = kwargs['ex_deployment_name']
            else:
                ex_deployment_name = ex_cloud_service_name

            blob_url = "http://" + ex_storage_service_name + ".blob.core.windows.net"
            disk_name = "{0}-{1}-{2}.vhd".format(ex_cloud_service_name,name,time.strftime("%Y-%m-%d")) # Azure's pattern in the UI.
            media_link = blob_url + "/vhds/" + disk_name
            disk_config = OSVirtualHardDisk(image, media_link)
            
            result = sms.create_virtual_machine_deployment(
                service_name=ex_cloud_service_name,
                deployment_name=ex_deployment_name,
                deployment_slot=ex_deployment_slot,
                label=name,
                role_name=name,
                system_config=machine_config,
                os_virtual_hard_disk=disk_config,
                network_config=network_config,
                role_size=size
                )
        else:
            _deployment_name = self._get_deployment(service_name=ex_cloud_service_name,deployment_slot=ex_deployment_slot).name

            if "ex_storage_service_name" in kwargs:
                ex_storage_service_name = kwargs['ex_storage_service_name']
            else:
                ex_storage_service_name = ex_cloud_service_name
                ex_storage_service_name = re.sub(ur'[\W_]+', u'', ex_storage_service_name.lower(), flags=re.UNICODE)
                
                if self._is_storage_service_unique(service_name=ex_storage_service_name):
                    self._create_storage_account(
                        service_name=ex_storage_service_name,
                        location=_storage_location.service_location,
                        is_affinity_group=_storage_location.is_affinity_group
                        )

            blob_url = "http://" + ex_storage_service_name + ".blob.core.windows.net"
            disk_name = "{0}-{1}-{2}.vhd".format(ex_cloud_service_name,name,time.strftime("%Y-%m-%d"))
            media_link = blob_url + "/vhds/" + disk_name
            disk_config = OSVirtualHardDisk(image, media_link)

            result = self.sms.add_role(
                service_name=ex_cloud_service_name,
                deployment_name=_deployment_name,
                role_name=name,
                system_config=machine_config,
                os_virtual_hard_disk=disk_config,
                network_config=network_config,
                role_size=size
            )

        return Node(
            id=name,
            name=name,
            state=NodeState.PENDING,
            public_ips=[],
            private_ips=[],
            driver=self.connection.driver
        )

        #operation_status = self.sms.get_operation_status(result.request_id)

        #timeout = 60 * 5
        #waittime = 0
        #interval = 5  

        #while operation_status.status == "InProgress" and waittime < timeout:
        #    operation_status = self.sms.get_operation_status(result.request_id)            
        #    if operation_status.status == "Succeeded":
        #        break

        #    waittime += interval
        #    time.sleep(interval)

        #if operation_status.status == "Failed":
        #    raise Exception(operation_status.error.message)
        #return

    def destroy_node(self, node, ex_cloud_service_name=None, ex_deployment_slot=None):
        """Remove Azure Virtual Machine

        This removes the instance, but does not 
        remove the disk. You will need to use destroy_volume. 
        Azure sometimes has an issue where it will hold onto
        a blob lease for an extended amount of time. 

        :keyword     ex_cloud_service_name: Required. Name of the Azure Cloud Service.
        :type        ex_cloud_service_name:  ``str``

        :keyword     ex_deployment_slot: Optional: The name of the deployment
                                         slot. If this is not passed in we 
                                         default to production. 
        :type        ex_deployment_slot:  ``str``
        """

        if not ex_cloud_service_name:
            raise ValueError("ex_cloud_service_name is required.")

        if not ex_deployment_slot:
            ex_deployment_slot = "production"

        _deployment = self._get_deployment(service_name=ex_cloud_service_name,deployment_slot=ex_deployment_slot)
        _deployment_name = _deployment.name

        _server_deployment_count = len(_deployment.role_instance_list)

        sms = ServiceManagementService(subscription_id, certificate_path)

        try:
            if _server_deployment_count > 1:
                data = sms.delete_role(service_name=ex_cloud_service_name,
                    deployment_name=_deployment_name,
                    role_name=node.id,
                    delete_attached_disks=True)
                return True
            else:
                data = sms.delete_deployment(service_name=ex_cloud_service_name,deployment_name=_deployment_name,delete_attached_disks=True)
                return True
        except Exception:
            return False

    """ Functions not implemented
    """
    def create_volume_snapshot(self):
        raise NotImplementedError(
            'You cannot create snapshots of '
            'Azure VMs at this time.')

    def attach_volume(self):
        raise NotImplementedError(
            'attach_volume is not supported '
            'at this time.')

    def create_volume(self):
        raise NotImplementedError(
            'create_volume is not supported '
            'at this time.')

    def detach_volume(self):
        raise NotImplementedError(
            'detach_volume is not supported '
            'at this time.')

    def destroy_volume(self):
        raise NotImplementedError(
            'destroy_volume is not supported '
            'at this time.')

    """Private Functions
    """

    def _to_node(self, data):
        """
        Convert the data from a Azure response object into a Node
        """

        if len(data.instance_endpoints) >= 1:
            public_ip = data.instance_endpoints[0].vip
        else:
            public_ip = []

        for port in data.instance_endpoints:
            if port.name == 'Remote Desktop':
                remote_desktop_port = port.public_port

        return Node(
            id=data.instance_name,
            name=data.instance_name,
            state=data.instance_status,
            public_ips=[public_ip],
            private_ips=[data.ip_address],
            driver=self.connection.driver,
            extra={
                'remote_desktop_port': remote_desktop_port,
                'power_state': data.power_state,
                'instance_size': data.instance_size})

    def _to_location(self, data):
        """
        Convert the data from a Azure resonse object into a location
        """
        country = data.display_name

        if "Asia" in data.display_name:
            country = "Asia"

        if "Europe" in data.display_name:
            country = "Europe"

        if "US" in data.display_name:
            country = "US"

        if "Japan" in data.display_name:
            country = "Japan"

        if "Brazil" in data.display_name:
            country = "Brazil"

        return NodeLocation(
            id=data.name,
            name=data.display_name,
            country=country,
            driver=self.connection.driver)

    def _to_node_size(self, data):
        """
        Convert the AZURE_COMPUTE_INSTANCE_TYPES into NodeSize
        """
        
        return NodeSize(
            id=data["id"],
            name=data["name"],
            ram=data["ram"],
            disk=data["disk"],
            bandwidth=data["bandwidth"],
            price=data["price"],
            driver=self.connection.driver,
            extra={
                'max_data_disks' : data["max_data_disks"],
                'cores' : data["cores"]
            })

    def _to_image(self, data):

        return NodeImage(
            id=data.name,
            name=data.label


            ,
            driver=self.connection.driver,
            extra={
                'os' : data.os,
                'category' : data.category,
                'description' : data.description,
                'location' : data.location,
                'affinity_group' : data.affinity_group,
                'media_link' : data.media_link
            })

    def _to_volume(self, volume, node):

        if node: 
            if hasattr(volume.attached_to, 'role_name'):
                if volume.attached_to.role_name == node.id:
                    extra = {}
                    extra['affinity_group'] = volume.affinity_group
                    if hasattr(volume.attached_to, 'hosted_service_name'):
                        extra['hosted_service_name'] = volume.attached_to.hosted_service_name
                    if hasattr(volume.attached_to, 'role_name'):
                        extra['role_name'] = volume.attached_to.role_name
                    if hasattr(volume.attached_to, 'deployment_name'):
                        extra['deployment_name'] = volume.attached_to.deployment_name
                    extra['os'] = volume.os
                    extra['location'] = volume.location
                    extra['media_link'] = volume.media_link
                    extra['source_image_name'] = volume.source_image_name

                    return StorageVolume(id=volume.name,
                        name=volume.name,
                        size=int(volume.logical_disk_size_in_gb),
                        driver=self.connection.driver,
                        extra=extra)
        else:
            extra = {}
            extra['affinity_group'] = volume.affinity_group
            if hasattr(volume.attached_to, 'hosted_service_name'):
                extra['hosted_service_name'] = volume.attached_to.hosted_service_name
            if hasattr(volume.attached_to, 'role_name'):
                extra['role_name'] = volume.attached_to.role_name
            if hasattr(volume.attached_to, 'deployment_name'):
                extra['deployment_name'] = volume.attached_to.deployment_name
            extra['os'] = volume.os
            extra['location'] = volume.location
            extra['media_link'] = volume.media_link
            extra['source_image_name'] = volume.source_image_name

            return StorageVolume(id=volume.name,
                name=volume.name,
                size=int(volume.logical_disk_size_in_gb),
                driver=self.connection.driver,
                extra=extra)

    def _get_deployment(self, **kwargs):
        _service_name = kwargs['service_name']
        _deployment_slot = kwargs['deployment_slot'] 

        sms = ServiceManagementService(subscription_id, certificate_path)

        return sms.get_deployment_by_slot(service_name=_service_name,deployment_slot=_deployment_slot)

    def _get_cloud_service_location(self, service_name=None):

        if not service_name:
            raise ValueError("service_name is required.")

        sms = ServiceManagementService(subscription_id, certificate_path)

        res = sms.get_hosted_service_properties(service_name=service_name,embed_detail=False)

        _affinity_group = res.hosted_service_properties.affinity_group
        _cloud_service_location = res.hosted_service_properties.location

        if _affinity_group is not None:
            return self.service_location(True, _affinity_group)
        elif _cloud_service_location is not None:
            return self.service_location(False, _cloud_service_location)
        else:
            return None

    def _is_storage_service_unique(self, service_name=None):
        if not service_name:
            raise ValueError("service_name is required.")

        sms = ServiceManagementService(subscription_id, certificate_path)
        
        _check_availability = sms.check_storage_account_name_availability(service_name=service_name)
        
        return _check_availability.result

    def _create_storage_account(self, **kwargs):
        sms = ServiceManagementService(subscription_id, certificate_path)

        if kwargs['is_affinity_group'] is True:
            result = sms.create_storage_account(
                service_name=kwargs['service_name'],
                description=kwargs['service_name'],
                label=kwargs['service_name'],
                affinity_group=kwargs['location'])
        else:
            result = sms.create_storage_account(
                service_name=kwargs['service_name'],
                description=kwargs['service_name'],
                label=kwargs['service_name'],
                location=kwargs['location'])

        # We need to wait for this to be created before we can 
        # create the storage container and the instance. 

        operation_status = sms.get_operation_status(result.request_id)

        timeout = 60 * 5
        waittime = 0
        interval = 5  

        while operation_status.status == "InProgress" and waittime < timeout:
            operation_status = sms.get_operation_status(result.request_id)
            if operation_status.status == "Succeeded":
                break

            waittime += interval
            time.sleep(interval)
        return