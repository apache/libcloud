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
Outscale SDK
"""

import json

import requests

from libcloud.compute.base import NodeDriver
from libcloud.compute.types import Provider
from libcloud.common.osc import OSCRequestSignerAlgorithmV4
from libcloud.common.base import ConnectionUserAndKey
from libcloud.compute.base import Node, NodeImage, KeyPair
from libcloud.compute.types import NodeState


class OutscaleNodeDriver(NodeDriver):
    """
    Outscale SDK node driver
    """

    type = Provider.OUTSCALE
    name = 'Outscale API'
    website = 'http://www.outscale.com'

    def __init__(self,
                 key: str = None,
                 secret: str = None,
                 region: str = 'eu-west-2',
                 service: str = 'api',
                 version: str = 'latest'
                 ):
        self.key = key
        self.secret = secret
        self.region = region
        self.connection = ConnectionUserAndKey(self.key, self.secret)
        self.connection.region_name = region
        self.connection.service_name = service
        self.service_name = service
        self.version = version
        self.signer = OSCRequestSignerAlgorithmV4(access_key=self.key,
                                             access_secret=self.secret,
                                             version=self.version,
                                             connection=self.connection)

        self.NODE_STATE = {
            'pending': NodeState.PENDING,
            'running': NodeState.RUNNING,
            'shutting-down': NodeState.UNKNOWN,
            'terminated': NodeState.TERMINATED,
            'stopped': NodeState.STOPPED
        }

    def list_locations(self, ex_dry_run: bool = False):
        """
        Lists available regions details.
        :param      ex_dry_run: If true, checks whether you have the required
        permissions to perform the action.
        :type       ex_dry_run: ``bool``
        :return: regions details
        :rtype: ``dict``
        """
        action = "ReadRegions"
        data = json.dumps({"DryRun": ex_dry_run})
        signer = OSCRequestSignerAlgorithmV4(access_key=self.key,
                                             access_secret=self.secret,
                                             version=self.version,
                                             connection=self.connection)
        headers = signer.get_request_headers(action=action,
                                             data=data,
                                             service_name=self.service_name,
                                             region=self.region)
        endpoint = self._get_outscale_endpoint(self.region,
                                               self.version,
                                               action)
        return requests.post(endpoint, data=data, headers=headers)

    def ex_create_public_ip(self, dry_run: bool = False):
        """
        Create a new public ip.

        :param      dry_run: If true, checks whether you have the required
        permissions to perform the action.
        :type       dry_run: ``bool``

        :return: the created public ip
        :rtype: ``dict``
            """
        action = "CreatePublicIp"
        data = json.dumps({"DryRun": dry_run})
        headers = self._ex_generate_headers(action, data)
        endpoint = self._get_outscale_endpoint(self.region,
                                               self.version,
                                               action)
        return requests.post(endpoint, data=data, headers=headers)

    def ex_delete_public_ip(self,
                            dry_run: bool = False,
                            public_ip: str = None,
                            public_ip_id: str = None):
        """
        Delete instances.

        :param      dry_run: If true, checks whether you have the required
        permissions to perform the action.
        :type       dry_run: ``bool``

        :param      public_ip: The EIP. In the public Cloud, this parameter is
        required.
        :type       public_ip: ``str``

        :param      public_ip_id: The ID representing the association of the
        EIP with the VM or the NIC. In a Net,
        this parameter is required.
        :type       public_ip_id: ``str``

        :return: request
        :rtype: ``dict``
        """
        action = "DeletePublicIp"
        data = {"DryRun": dry_run}
        if public_ip is not None:
            data.update({"PublicIp": public_ip})
        if public_ip_id is not None:
            data.update({"PublicIpId": public_ip_id})
        data = json.dumps(data)
        headers = self._ex_generate_headers(action, data)
        endpoint = self._get_outscale_endpoint(self.region,
                                               self.version,
                                               action)
        return requests.post(endpoint, data=data, headers=headers)

    def ex_list_public_ips(self, data: str = "{}"):
        """
        List all nodes.

        :param      data: json stringify following the outscale api
        documentation for filter
        :type       data: ``string``

        :return: nodes
        :rtype: ``dict``
        """
        action = "ReadPublicIps"
        headers = self._ex_generate_headers(action, data)
        endpoint = self._get_outscale_endpoint(self.region,
                                               self.version,
                                               action)
        return requests.post(endpoint, data=data, headers=headers)

    def ex_list_public_ip_ranges(self, dry_run: bool = False):
        """
        Lists available regions details.

        :param      dry_run: If true, checks whether you have the
        required permissions to perform the action.
        :type       dry_run: ``bool``

        :return: regions details
        :rtype: ``dict``
        """
        action = "ReadPublicIpRanges"
        data = json.dumps({"DryRun": dry_run})
        headers = self._ex_generate_headers(action, data)
        endpoint = self._get_outscale_endpoint(self.region,
                                               self.version,
                                               action)
        return requests.post(endpoint, data=data, headers=headers)

    def ex_attach_public_ip(self,
                            allow_relink: bool = None,
                            dry_run: bool = False,
                            nic_id: str = None,
                            vm_id: str = None,
                            public_ip: str = None,
                            public_ip_id: str = None,
                            ):
        """
        Attach a volume.

        :param      allow_relink: If true, allows the EIP to be associated
        with the VM or NIC that you specify even if
        it is already associated with another VM or NIC.
        :type       allow_relink: ``bool``

        :param      dry_run: If true, checks whether you have the required
        permissions to perform the action.
        :type       dry_run: ``bool``

        :param      nic_id:(Net only) The ID of the NIC. This parameter is
        required if the VM has more than one NIC attached. Otherwise,
        you need to specify the VmId parameter instead.
        You cannot specify both parameters
        at the same time.
        :type       nic_id: ``str``

        :param      vm_id: the ID of the VM
        :type       nic_id: ``str``

        :param      public_ip: The EIP. In the public Cloud, this parameter
        is required.
        :type       public_ip: ``str``

        :param      public_ip_id: The allocation ID of the EIP. In a Net,
        this parameter is required.
        :type       public_ip_id: ``str``

        :return: the attached volume
        :rtype: ``dict``
        """
        action = "LinkPublicIp"
        data = {"DryRun": dry_run}
        if public_ip is not None:
            data.update({"PublicIp": public_ip})
        if public_ip_id is not None:
            data.update({"PublicIpId": public_ip_id})
        if nic_id is not None:
            data.update({"NicId": nic_id})
        if vm_id is not None:
            data.update({"VmId": vm_id})
        if allow_relink is not None:
            data.update({"AllowRelink": allow_relink})
        data = json.dumps(data)
        headers = self._ex_generate_headers(action, data)
        endpoint = self._get_outscale_endpoint(self.region,
                                               self.version,
                                               action)
        return requests.post(endpoint, data=data, headers=headers)

    def ex_detach_public_ip(self,
                            public_ip: str = None,
                            link_public_ip_id: str = None,
                            dry_run: bool = False):
        """
        Detach a volume.

        :param      public_ip: (Required in a Net) The ID representing the
        association of the EIP with the VM or the NIC
        :type       public_ip: ``str``

        :param      link_public_ip_id: (Required in a Net) The ID
        representing the association of the EIP with the
        VM or the NIC.
        :type       link_public_ip_id: ``str``

        :param      dry_run: If true, checks whether you have the required
        permissions to perform the action.
        :type       dry_run: ``bool``

        :return: the attached volume
        :rtype: ``dict``
        """
        action = "UnlinkPublicIp"
        data = {"DryRun": dry_run}
        if public_ip is not None:
            data.update({"PublicIp": public_ip})
        if link_public_ip_id is not None:
            data.update({"LinkPublicIpId": link_public_ip_id})
        data = json.dumps(data)
        headers = self._ex_generate_headers(action, data)
        endpoint = self._get_outscale_endpoint(self.region,
                                               self.version,
                                               action)
        return requests.post(endpoint, data=data, headers=headers)

    def create_node(self,
                    ex_image_id: str,
                    ex_dry_run: bool = False,
                    ex_block_device_mapping: dict = None,
                    ex_boot_on_creation: bool = True,
                    ex_bsu_optimized: bool = True,
                    ex_client_token: str = None,
                    ex_deletion_protection: bool = False,
                    ex_keypair_name: str = None,
                    ex_max_vms_count: int = None,
                    ex_min_vms_count: int = None,
                    ex_nics: dict = None,
                    ex_performance: str = None,
                    ex_placement: dict = None,
                    ex_private_ips: [str] = None,
                    ex_security_group_ids: [str] = None,
                    ex_security_groups: [str] = None,
                    ex_subnet_id: str = None,
                    ex_user_data: str = None,
                    ex_vm_initiated_shutdown_behavior: str = None,
                    ex_vm_type: str = None
                    ):
        """
        Create a new instance.

        :param      ex_image_id: The ID of the OMI used to create the VM.
        :type       ex_image_id: ``str``

        :param      ex_dry_run: If true, checks whether you have the required
        permissions to perform the action.
        :type       ex_dry_run: ``bool``

        :param      ex_block_device_mapping: One or more block device mappings.
        :type       ex_block_device_mapping: ``dict``

        :param      ex_boot_on_creation: By default or if true, the VM is
        started on creation. If false, the VM is
        stopped on creation.
        :type       ex_boot_on_creation: ``bool``

        :param      ex_bsu_optimized: If true, the VM is created with optimized
        BSU I/O.
        :type       ex_bsu_optimized: ``bool``

        :param      ex_client_token: A unique identifier which enables you to
        manage the idempotency.
        :type       ex_client_token: ``bool``

        :param      ex_deletion_protection: If true, you cannot terminate the
        VM using Cockpit, the CLI or the API.
        If false, you can.
        :type       ex_deletion_protection: ``bool``

        :param      ex_keypair_name: The name of the keypair.
        :type       ex_keypair_name: ``str``

        :param      ex_max_vms_count: The maximum number of VMs you want to
        create. If all the VMs cannot be created, the
        largest possible number of VMs above MinVmsCount is created.
        :type       ex_max_vms_count: ``integer``

        :param      ex_min_vms_count: The minimum number of VMs you want to
        create. If this number of VMs cannot be
        created, no VMs are created.
        :type       ex_min_vms_count: ``integer``

        :param      ex_nics: One or more NICs. If you specify this parameter,
        you must define one NIC as the primary
        network interface of the VM with 0 as its device number.
        :type       ex_nics: ``dict``

        :param      ex_performance: The performance of the VM (standard | high
        | highest).
        :type       ex_performance: ``str``

        :param      ex_placement: Information about the placement of the VM.
        :type       ex_placement: ``dict``

        :param      ex_private_ips: One or more private IP addresses of the VM.
        :type       ex_private_ips: ``list``

        :param      ex_security_group_ids: One or more IDs of security group
        for the VMs.
        :type       ex_security_group_ids: ``list``

        :param      ex_security_groups: One or more names of security groups
        for the VMs.
        :type       ex_security_groups: ``list``

        :param      ex_subnet_id: The ID of the Subnet in which you want to
        create the VM.
        :type       ex_subnet_id: ``str``

        :param      ex_user_data: Data or script used to add a specific configuration to the VM. It must be base64-encoded.
        :type       ex_user_data: ``str``

        :param      ex_vm_initiated_shutdown_behavior: The VM behavior when you stop it. By default or if set to stop, the
        VM stops. If set to restart, the VM stops then automatically restarts. If set to terminate, the VM stops and is terminated.
        create the VM.
        :type       ex_vm_initiated_shutdown_behavior: ``str``

        :param      ex_vm_type: The type of VM (t2.small by default).
        :type       ex_vm_type: ``str``

        :return: the created instance
        :rtype: ``dict``
        """
        data = {
            "DryRun": ex_dry_run,
            "BootOnCreation": ex_boot_on_creation,
            "BsuOptimized": ex_bsu_optimized,
            "ImageId": ex_image_id
        }
        if ex_block_device_mapping is not None:
            data.update({"BlockDeviceMappings": ex_block_device_mapping})
        if ex_client_token is not None:
            data.update({"ClientToken": ex_client_token})
        if ex_deletion_protection is not None:
            data.update({"DeletionProtection": ex_deletion_protection})
        if ex_keypair_name is not None:
            data.update({"KeypairName": ex_keypair_name})
        if ex_max_vms_count is not None:
            data.update({"MaxVmsCount": ex_max_vms_count})
        if ex_min_vms_count is not None:
            data.update({"MinVmsCount": ex_min_vms_count})
        if ex_nics is not None:
            data.update({"Nics": ex_nics})
        if ex_performance is not None:
            data.update({"Performance": ex_performance})
        if ex_placement is not None:
            data.update({"Placement": ex_placement})
        if ex_private_ips is not None:
            data.update({"PrivateIps": ex_private_ips})
        if ex_security_group_ids is not None:
            data.update({"SecurityGroupIds": ex_security_group_ids})
        if ex_security_groups is not None:
            data.update({"SecurityGroups": ex_security_groups})
        if ex_user_data is not None:
            data.update({"UserData": ex_user_data})
        if ex_vm_initiated_shutdown_behavior is not None:
            data.update({"VmInstantiatedShutdownBehavior": ex_vm_initiated_shutdown_behavior})
        if ex_vm_type is not None:
            data.update({"VmType": ex_vm_type})
        if ex_subnet_id is not None:
            data.update({"SubnetId": ex_subnet_id})
        action = "CreateVms"
        data = json.dumps(data)
        headers = self._ex_generate_headers(action, data)
        endpoint = self._get_outscale_endpoint(self.region,
                                               self.version,
                                               action)
        return requests.post(endpoint, data=data, headers=headers)

    def reboot_node(self, node: Node):
        """
        Reboot instances.

        :param      node: the ID(s) of the VM(s)
                    you want to reboot (required)
        :type       node: ``list``

        :return: the rebooted instances
        :rtype: ``dict``
        """
        action = "RebootVms"
        data = json.dumps({"VmIds": node.id})
        headers = self._ex_generate_headers(action, data)
        endpoint = self._get_outscale_endpoint(self.region,
                                               self.version,
                                               action)
        return requests.post(endpoint, data=data, headers=headers)

    def _to_nodes(self, vms: list):
        nodes_list = []
        for vm in vms:
            name = ""
            private_ips = []
            for tag in vm["Tags"]:
                if tag["Key"] == "Name":
                    name = tag["Value"]
            if "PrivateIps" in vm["Nics"]:
                private_ips = vm["Nics"]["PrivateIps"]

            node = Node(id=vm["VmId"],
                        name=name,
                        state=self.NODE_STATE[vm["State"]],
                        public_ips=[],
                        private_ips=private_ips,
                        driver=self,
                        extra=vm)
            nodes_list.append(node)
        return nodes_list

    def _to_node_images(self, node_images: list):
        node_image_list = []
        for image in node_images:
            name = ""
            private_ips = []
            for tag in image["Tags"]:
                if tag["Key"] == "Name":
                    name = tag["Value"]
            if "PrivateIps" in image["Nics"]:
                private_ips = image["Nics"]["PrivateIps"]

            node = NodeImage(id=image["NodeId"],
                             name=name,
                             driver=self,
                             extra=image)
            node_image_list.append(node)
        return node_image_list

    def list_nodes(self, ex_data: str = "{}"):
        """
        List all nodes.

        :return: nodes
        :rtype: ``dict``
        """
        action = "ReadVms"
        headers = self._ex_generate_headers(action, ex_data)
        endpoint = self._get_outscale_endpoint(self.region,
                                               self.version,
                                               action)
        vms = requests.post(endpoint, data=ex_data, headers=headers).json()["Vms"]
        return self._to_nodes(vms)

    def destroy_node(self, node: Node):
        """
        Delete instances.

        :param      node: one or more IDs of VMs (required)
        :type       node: ``Node``

        :return: request
        :rtype: ``dict``
        """
        action = "DeleteVms"
        data = json.dumps({"VmIds": node.id})
        headers = self._ex_generate_headers(action, data)
        endpoint = self._get_outscale_endpoint(self.region,
                                               self.version,
                                               action)
        return requests.post(endpoint, data=data, headers=headers)

    def create_image(
        self,
        ex_architecture: str = None,
        node: Node = None,
        name: str = None,
        description: str = None,
        ex_block_device_mapping: dict = None,
        ex_no_reboot: bool = False,
        ex_root_device_name: str = None,
        ex_dry_run: bool = False,
        ex_source_region_name: str = None,
        ex_file_location: str = None
    ):
        """
        Create a new image.

        :param      node: a valid Node object
        :type       node: ``str``

        :param      ex_architecture: The architecture of the OMI (by default,
        i386).
        :type       ex_architecture: ``str``

        :param      description: a description for the new OMI
        :type       description: ``str``

        :param      name: A unique name for the new OMI.
        :type       name: ``str``

        :param      ex_block_device_mapping: One or more block device mappings.
        :type       ex_block_device_mapping: ``dict``

        :param      ex_no_reboot: If false, the VM shuts down before creating
        the OMI and then reboots.
        If true, the VM does not.
        :type       ex_no_reboot: ``bool``

        :param      ex_root_device_name: The name of the root device.
        :type       ex_root_device_name: ``str``

        :param      ex_source_region_name: The name of the source Region,
        which must be the same
        as the Region of your account.
        :type       ex_source_region_name: ``str``

        :param      ex_file_location: The pre-signed URL of the OMI manifest
        file, or the full path to the OMI stored in
        an OSU bucket. If you specify this parameter, a copy of the OMI is
        created in your account.
        :type       ex_file_location: ``str``

        :param      ex_dry_run: If true, checks whether you have the required
        permissions to perform the action.
        :type       ex_dry_run: ``bool``

        :return: the created image
        :rtype: ``dict``
        """
        data = {
            "DryRun": ex_dry_run,
            "NoReboot": ex_no_reboot,
        }
        if ex_block_device_mapping is not None:
            data.update({"BlockDeviceMappings": ex_block_device_mapping})
        if name is not None:
            data.update({"ImageName": name})
        if description is not None:
            data.update({"Description": description})
        if node.id is not None:
            data.update({"VmId": node.id})
        if ex_root_device_name is not None:
            data.update({"RootDeviceName": ex_root_device_name})
        if ex_source_region_name is not None:
            data.update({"SourceRegionName": ex_source_region_name})
        if ex_file_location is not None:
            data.update({"FileLocation": ex_file_location})
        data = json.dumps(data)
        action = "CreateImage"
        headers = self._ex_generate_headers(action, data)
        endpoint = self._get_outscale_endpoint(self.region,
                                               self.version,
                                               action)
        return requests.post(endpoint, data=data, headers=headers)

    def list_images(self, ex_data: str = "{}"):
        """
        List all images.

        :return: images
        :rtype: ``dict``
        """
        action = "ReadImages"
        headers = self._ex_generate_headers(action, ex_data)
        endpoint = self._get_outscale_endpoint(self.region,
                                               self.version,
                                               action)
        images = requests.post(endpoint, data=ex_data, headers=headers).json()["Images"]
        return self._to_node_images(images)

    def get_image(self, image_id: str):
        """
        Get a specific image.

        :param      image_id: the ID of the image you want to select (required)
        :type       image_id: ``str``

        :return: the selected image
        :rtype: ``dict``
        """
        action = "ReadImages"
        data = '{"Filters": {"ImageIds": ["' + image_id + '"]}}'
        headers = self._ex_generate_headers(action, data)
        endpoint = self._get_outscale_endpoint(self.region,
                                               self.version,
                                               action)
        images = requests.post(endpoint, data=data, headers=headers).json()["Images"]
        return self._to_node_images(images)[0]

    def delete_image(self, node_image: NodeImage):
        """
        Delete an image.

        :param      node_image: the ID of the OMI you want to delete (required)
        :type       node_image: ``str``

        :return: request
        :rtype: ``dict``
        """
        action = "DeleteImage"
        data = '{"ImageId": "' + node_image.id + '"}'
        headers = self._ex_generate_headers(action, data)
        endpoint = self._get_outscale_endpoint(self.region,
                                               self.version,
                                               action)
        response = requests.post(endpoint, data=data, headers=headers)
        if response.status_code == 200:
            return True
        return False

    def _to_key_pairs(self, key_pairs):
        return [self._to_key_pair(key_pair) for key_pair in key_pairs]

    def _to_key_pair(self, key_pair):
        private_key = key_pair["PrivateKey"] if "PrivateKey" in key_pair else ""
        return KeyPair(
            name=key_pair["KeypairName"],
            public_key=None,
            private_key=private_key,
            fingerprint=key_pair["KeypairFingerprint"],
            driver=self)

    def create_key_pair(self,
                        name: str,
                        ex_dry_run: bool = False,
                        ex_public_key: str = None):
        """
        Create a new key pair.

        :param      name: A unique name for the keypair, with a maximum
        length of 255 ASCII printable characters.
        :type       name: ``str``

        :param      ex_dry_run: If true, checks whether you have the required
        permissions to perform the action.
        :type       ex_dry_run: ``bool``

        :param      ex_public_key: The public key. It must be base64-encoded.
        :type       ex_public_key: ``str``

        :return: the created key pair
        :rtype: ``dict``
        """
        data = {
            "KeypairName": name,
            "DryRun": ex_dry_run,
        }
        if ex_public_key is not None:
            data.update({"PublicKey": ex_public_key})
        data = json.dumps(data)
        action = "CreateKeypair"
        headers = self._ex_generate_headers(action, data)
        endpoint = self._get_outscale_endpoint(self.region,
                                               self.version,
                                               action)
        key_pair = requests.post(endpoint, data=data, headers=headers).json()
        return self._to_key_pair(key_pair["Keypair"])

    def list_key_pairs(self, ex_data: str = "{}"):
        """
        List all key pairs.

        :return: key pairs
        :rtype: ``dict``
        """
        action = "ReadKeypairs"
        headers = self._ex_generate_headers(action, ex_data)
        endpoint = self._get_outscale_endpoint(self.region,
                                               self.version,
                                               action)
        key_pairs = requests.post(endpoint, data=ex_data, headers=headers).json()
        return self._to_key_pairs(key_pairs["Keypairs"])

    def get_key_pair(self, name: str):
        """
        Get a specific key pair.

        :param      name: the name of the key pair
                    you want to select (required)
        :type       name: ``str``

        :return: the selected key pair
        :rtype: ``dict``
        """
        action = "ReadKeypairs"
        data = '{"Filters": {"KeypairNames" : ["' + name + '"]}}'
        headers = self._ex_generate_headers(action, data)
        endpoint = self._get_outscale_endpoint(self.region,
                                               self.version,
                                               action)
        key_pair = requests.post(endpoint, data=data, headers=headers).json()["Keypairs"][0]
        return self._to_key_pair(key_pair)

    def delete_key_pair(self, name: str):
        """
        Delete an image.

        :param      name: the name of the keypair you want to delete (required)
        :type       name: ``str``

        :return: request
        :rtype: ``dict``
        """
        action = "DeleteKeypair"
        data = '{"KeypairName": "' + name + '"}'
        headers = self._ex_generate_headers(action, data)
        endpoint = self._get_outscale_endpoint(self.region,
                                               self.version,
                                               action)
        return requests.post(endpoint, data=data, headers=headers)

    def create_snapshot(self,
                        description: str = None,
                        dry_run: bool = False,
                        file_location: str = None,
                        snapshot_size: int = None,
                        source_region_name: str = None,
                        source_snapshot_id: str = None,
                        volume_id: str = None,
                        ):
        """
        Create a new snapshot.

        :param      description: a description for the new OMI
        :type       description: ``str``

        :param      snapshot_size: The size of the snapshot created in your
        account, in bytes. This size must be
        exactly the same as the source snapshot one.
        :type       snapshot_size: ``integer``

        :param      source_snapshot_id: The ID of the snapshot you want to
        copy.
        :type       source_snapshot_id: ``str``

        :param      volume_id: The ID of the volume you want to create a
        snapshot of.
        :type       volume_id: ``str``

        :param      source_region_name: The name of the source Region,
        which must be the same
        as the Region of your account.
        :type       source_region_name: ``str``

        :param      file_location: The pre-signed URL of the OMI manifest
        file, or the full path to the OMI stored in
        an OSU bucket. If you specify this parameter, a copy of the OMI is
        created in your account.
        :type       file_location: ``str``

        :param      dry_run: If true, checks whether you have the required
        permissions to perform the action.
        :type       dry_run: ``bool``

        :return: the created snapshot
        :rtype: ``dict``
        """
        data = {
            "DryRun": dry_run,
        }
        if description is not None:
            data.update({"Description": description})
        if file_location is not None:
            data.update({"FileLocation": file_location})
        if snapshot_size is not None:
            data.update({"SnapshotSize": snapshot_size})
        if source_region_name is not None:
            data.update({"SourceRegionName": source_region_name})
        if source_snapshot_id is not None:
            data.update({"SourceSnapshotId": source_snapshot_id})
        if volume_id is not None:
            data.update({"VolumeId": volume_id})
        data = json.dumps(data)
        action = "CreateSnapshot"
        headers = self._ex_generate_headers(action, data)
        endpoint = self._get_outscale_endpoint(self.region,
                                               self.version,
                                               action)
        return requests.post(endpoint, data=data, headers=headers)

    def list_snapshots(self, data: str = "{}"):
        """
        List all snapshots.

        :return: snapshots
        :rtype: ``dict``
        """
        action = "ReadSnapshots"
        headers = self._ex_generate_headers(action, data)
        endpoint = self._get_outscale_endpoint(self.region,
                                               self.version,
                                               action)
        return requests.post(endpoint, data=data, headers=headers)

    def delete_snapshot(self, snapshot_id: str):
        """
        Delete a snapshot.

        :param      snapshot_id: the ID of the snapshot
                    you want to delete (required)
        :type       snapshot_id: ``str``

        :return: request
        :rtype: ``dict``
        """
        action = "DeleteSnapshot"
        data = '{"SnapshotId": "' + snapshot_id + '"}'
        headers = self._ex_generate_headers(action, data)
        endpoint = self._get_outscale_endpoint(self.region,
                                               self.version,
                                               action)
        return requests.post(endpoint, data=data, headers=headers)

    def create_volume(
        self,
        subregion_name: str,
        dry_run: bool = False,
        iops: int = None,
        size: int = None,
        snapshot_id: str = None,
        volume_type: str = None,
    ):
        """
        Create a new volume.

        :param      snapshot_id: the ID of the snapshot from which
                    you want to create the volume (required)
        :type       snapshot_id: ``str``

        :param      dry_run: If true, checks whether you have the required
        permissions to perform the action.
        :type       dry_run: ``bool``

        :param      size: the size of the volume, in gibibytes (GiB),
                    the maximum allowed size for a volume is 14,901 GiB
        :type       size: ``int``

        :param      subregion_name: The Subregion in which you want to
        create the volume.
        :type       subregion_name: ``str``

        :param      volume_type: the type of volume you want to create (io1
        | gp2 | standard)
        :type       volume_type: ``str``

        :param      iops: The number of I/O operations per second (IOPS).
        This parameter must be specified only if
        you create an io1 volume. The maximum number of IOPS allowed for io1
        volumes is 13000.
        :type       iops: ``integer``

        :return: the created volume
        :rtype: ``dict``
        """
        data = {
            "DryRun": dry_run,
            "SubregionName": subregion_name
        }
        if iops is not None:
            data.update({"Iops": iops})
        if size is not None:
            data.update({"Size": size})
        if snapshot_id is not None:
            data.update({"SnapshotId": snapshot_id})
        if volume_type is not None:
            data.update({"VolumeType": volume_type})
        data = json.dumps(data)
        action = "CreateVolume"
        headers = self._ex_generate_headers(action, data)

        endpoint = self._get_outscale_endpoint(self.region,
                                               self.version,
                                               action)
        return requests.post(endpoint, data=data, headers=headers)

    def list_volumes(self, data: str = "{}"):
        """
        List all volumes.

        :return: volumes
        :rtype: ``dict``
        """
        action = "ReadVolumes"
        headers = self._ex_generate_headers(action, data)
        endpoint = self._get_outscale_endpoint(self.region,
                                               self.version,
                                               action)
        return requests.post(endpoint, data=data, headers=headers)

    def delete_volume(self, volume_id: str):
        """
        Delete a volume.

        :param      volume_id: the ID of the volume
                    you want to delete (required)
        :type       volume_id: ``str``

        :return: request
        :rtype: ``dict``
        """
        action = "DeleteVolume"
        data = '{"VolumeId": "' + volume_id + '"}'
        headers = self._ex_generate_headers(action, data)
        endpoint = self._get_outscale_endpoint(self.region,
                                               self.version,
                                               action)
        return requests.post(endpoint, data=data, headers=headers)

    def attach_volume(self, node_id: str, volume_id: str, device_name: str):
        """
        Attach a volume.

        :param      node_id: the ID of the VM you want
                    to attach the volume to (required)
        :type       node_id: ``str``

        :param      volume_id: the ID of the volume
                    you want to attach (required)
        :type       volume_id: ``str``

        :param      device_name: the name of the device (required)
        :type       device_name: ``str``

        :return: the attached volume
        :rtype: ``dict``
        """
        action = "LinkVolume"
        data = json.dumps({
            "VmId": node_id,
            "VolumeId": volume_id,
            "DeviceName": device_name
        })
        headers = self._ex_generate_headers(action, data)
        endpoint = self._get_outscale_endpoint(self.region,
                                               self.version,
                                               action)
        return requests.post(endpoint, data=data, headers=headers)

    def detach_volume(self,
                      volume_id: str,
                      dry_run: bool = False,
                      force_unlink: bool = False):
        """
        Detach a volume.

        :param      volume_id: the ID of the volume you want to detach
        (required)
        :type       volume_id: ``str``

        :param      force_unlink: Forces the detachment of the volume in
        case of previous failure.
        Important: This action may damage your data or file systems.
        :type       force_unlink: ``bool``

        :param      dry_run: If true, checks whether you have the required
        permissions to perform the action.
        :type       dry_run: ``bool``

        :return: the attached volume
        :rtype: ``dict``
        """
        action = "UnlinkVolume"
        data = {"DryRun": dry_run, "VolumeId": volume_id}
        if force_unlink is not None:
            data.update({"ForceUnlink": force_unlink})
        data = json.dumps(data)
        headers = self._ex_generate_headers(action, data)
        endpoint = self._get_outscale_endpoint(self.region,
                                               self.version,
                                               action)
        return requests.post(endpoint, data=data, headers=headers)

    @staticmethod
    def _get_outscale_endpoint(region: str, version: str, action: str):
        return "https://api.{}.outscale.com/api/{}/{}".format(
            region,
            version,
            action
        )

    def _ex_generate_headers(self, action: str, data: dict):
        return self.signer.get_request_headers(action=action,
                                             data=data,
                                             service_name=self.service_name,
                                             region=self.region)

