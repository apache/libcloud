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

# NOTE: Re-enable once we add mypy annotations for the base container API
# type: ignore
"""
kubevirt driver with support for nodes (vms)
"""
import json
import time
import hashlib

from datetime import datetime

from libcloud.common.types import LibcloudError
from libcloud.common.kubernetes import KubernetesBasicAuthConnection
from libcloud.common.kubernetes import KubernetesDriverMixin
from libcloud.common.kubernetes import VALID_RESPONSE_CODES

from libcloud.compute.types import Provider, NodeState
from libcloud.compute.base import NodeDriver, NodeSize, Node
from libcloud.compute.base import NodeImage, NodeLocation, StorageVolume

__all__ = [
    "KubeVirtNodeDriver"
]
ROOT_URL = '/api/v1/'
KUBEVIRT_URL = '/apis/kubevirt.io/v1alpha3/'


class KubeVirtNodeDriver(KubernetesDriverMixin, NodeDriver):
    type = Provider.KUBEVIRT
    name = "kubevirt"
    website = 'https://www.kubevirt.io'
    connectionCls = KubernetesBasicAuthConnection

    NODE_STATE_MAP = {
        'pending': NodeState.PENDING,
        'running': NodeState.RUNNING,
        'stopped': NodeState.STOPPED
    }

    def list_nodes(self, location=None):
        namespaces = []
        if location is not None:
            namespaces.append(location.name)
        else:
            for ns in self.list_locations():
                namespaces.append(ns.name)

        dormant = []
        live = []
        for ns in namespaces:
            req = KUBEVIRT_URL + 'namespaces/' + ns + \
                "/virtualmachines"
            result = self.connection.request(req)
            if result.status != 200:
                continue
            result = result.object
            for item in result['items']:
                if not item['spec']['running']:
                    dormant.append(item)
                else:
                    live.append(item)
        vms = []
        for vm in dormant:
            vms.append(self._to_node(vm, is_stopped=True))

        for vm in live:
            vms.append(self._to_node(vm, is_stopped=False))

        return vms

    def get_node(self, id=None, name=None):
        "get a vm by name or id"
        if not id and not name:
            raise ValueError("This method needs id or name to be specified")
        nodes = self.list_nodes()
        if id:
            node_gen = filter(lambda x: x.id == id,
                              nodes)
        if name:
            node_gen = filter(lambda x: x.name == name,
                              nodes)

        try:
            return next(node_gen)
        except StopIteration:
            raise ValueError("Node does not exist")

    def start_node(self, node):
        # make sure it is stopped
        if node.state is NodeState.RUNNING:
            return True
        name = node.name
        namespace = node.extra['namespace']
        req = KUBEVIRT_URL + 'namespaces/' + namespace +\
            '/virtualmachines/' + name
        data = {"spec": {"running": True}}
        headers = {"Content-Type": "application/merge-patch+json"}
        try:
            result = self.connection.request(req, method="PATCH",
                                             data=json.dumps(data),
                                             headers=headers)

            return result.status in VALID_RESPONSE_CODES

        except Exception:
            raise

    def stop_node(self, node):
        # check if running
        if node.state is NodeState.STOPPED:
            return True
        name = node.name
        namespace = node.extra['namespace']
        req = KUBEVIRT_URL + 'namespaces/' + namespace + \
            '/virtualmachines/' + name
        headers = {"Content-Type": "application/merge-patch+json"}
        data = {"spec": {"running": False}}
        try:
            result = self.connection.request(req, method="PATCH",
                                             data=json.dumps(data),
                                             headers=headers)

            return result.status in VALID_RESPONSE_CODES

        except Exception:
            raise

    def reboot_node(self, node):
        """
        Rebooting a node.
        """
        namespace = node.extra['namespace']
        name = node.name
        method = 'DELETE'
        try:
            result = self.connection.request(KUBEVIRT_URL + 'namespaces/' +
                                             namespace +
                                             '/virtualmachineinstances/' +
                                             name,
                                             method=method)

            return result.status in VALID_RESPONSE_CODES
        except Exception:
            raise
        return

    def destroy_node(self, node):
        """
        Terminating a VMI and deleting the VM resource backing it
        """
        namespace = node.extra['namespace']
        name = node.name
        # find and delete services for this VM only
        services = self.ex_list_services(namespace=namespace, node_name=name)
        for service in services:
            service_name = service['metadata']['name']
            self.ex_delete_service(namespace=namespace,
                                   service_name=service_name)
        # stop the vmi
        self.stop_node(node)
        try:
            result = self.connection.request(KUBEVIRT_URL +
                                             'namespaces/' +
                                             namespace +
                                             '/virtualmachines/' + name,
                                             method='DELETE')
            return result.status in VALID_RESPONSE_CODES
        except Exception:
            raise

    # only has container disk support atm with no persistency
    def create_node(self, name, image, location=None, ex_memory=128, ex_cpu=1,
                    ex_disks=None, ex_network=None,
                    ex_termination_grace_period=0,
                    ports=None):
        """
        Creating a VM with a containerDisk.
        :param name: A name to give the VM. The VM will be identified by
                     this name and atm it cannot be changed after it is set.
        :type name: ``str``

        :param image: Either a libcloud NodeImage or a string.
                      In both cases it must point to a Docker image with an
                      embedded disk.
                      May be a URI like `kubevirt/cirros-registry-disk-demo`,
                      kubevirt will automatically pull it from
                      https://hub.docker.com/u/URI.
                      For more info visit:
                      https://kubevirt.io/user-guide/docs/latest/creating-virtual-machines/disks-and-volumes.html#containerdisk
        :type image: `str`

        :param location: The namespace where the VM will live.
                          (default is 'default')
        :type location: ``str``

        :param ex_memory: The RAM in MB to be allocated to the VM
        :type ex_memory: ``int``

        :param ex_cpu: The ammount of cpu to be allocated in miliCPUs
                    ie: 400 will mean 0.4 of a core, 1000 will mean 1 core
                    and 3000 will mean 3 cores.
        :type ex_cpu: ``int``

        :param ex_disks: A list containing disk dictionaries.
                             Each dictionaries should have the
                             following optional keys:
                             -bus: can be "virtio", "sata", or "scsi"
                             -device: can be "lun" or "disk"
                             The following are required keys:
                             -disk_type: atm only "persistentVolumeClaim"
                                         is supported
                             -name: The name of the disk configuration
                             -claim_name: the name of the
                                         Persistent Volume Claim

                            If you wish a new Persistent Volume Claim can be
                            created by providing the following:
                            required:
                            -size: the desired size (implied in GB)
                            -storage_class_name: the name of the storage class to # NOQA
                                               be used for the creation of the
                                               Persistent Volume Claim.
                                               Make sure it allows for
                                               dymamic provisioning.
                             optional:
                            -access_mode: default is ReadWriteOnce
                            -volume_mode: default is `Filesystem`,
                                         it can also be `Block`

        :type ex_disks: `list` of `dict`. For each `dict` the types
                            for its keys are:
                            -bus: `str`
                            -device: `str`
                            -disk_type: `str`
                            -name: `str`
                            -claim_name: `str`
                            (for creating a claim:)
                            -size: `int`
                            -storage_class_name: `str`
                            -volume_mode: `str`
                            -access_mode: `str`

        :param ex_network: Only the pod type is supported, and in the
                               configuration masquerade or bridge are the
                               accepted values.
                               The parameter must be a tupple or list with
                               (network_type, interface, name)
        :type ex_network: `iterable` (tupple or list) [network_type, inteface, name]
                      network_type: `str` | only "pod" is accepted atm
                      interface: `str` | "masquerade" or "bridge"
                      name: `str`

        :param ports: A dictionary with keys: 'ports_tcp' and 'ports_udp'
                      'ports_tcp' value is a list of ints that indicate
                      the ports to be exposed with TCP protocol,
                      and 'ports_udp' is a list of ints that indicate
                      the ports to be exposed with UDP protocol.
        :type  ports: `dict` with keys
                      'ports_tcp`: `list` of `int`
                      'ports_udp`: `list` of `int`
        """
        # all valid disk types for which support will be added in the future
        DISK_TYPES = {'containerDisk', 'ephemeral', 'configMap', 'dataVolume',
                      'cloudInitNoCloud', 'persistentVolumeClaim', 'emptyDisk',
                      'cloudInitConfigDrive', 'hostDisk'}

        if location is not None:
            namespace = location.name
        else:
            namespace = 'default'

        # vm template to be populated
        vm = {
            "apiVersion": "kubevirt.io/v1alpha3",
            "kind": "VirtualMachine",
            "metadata": {
                "labels": {
                    "kubevirt.io/vm": name
                },
                "name": name
            },
            "spec": {
                "running": False,
                "template": {
                    "metadata": {
                        "labels": {
                            "kubevirt.io/vm": name
                        }
                    },
                    "spec": {
                        "domain": {
                            "devices": {
                                "disks": [],
                                "interfaces": [],
                                "networkInterfaceMultiqueue": False,
                            },
                            "machine": {
                                "type": ""
                            },
                            "resources": {
                                "requests": {},
                                "limits": {}
                            },
                        },
                        "networks": [],
                        "terminationGracePeriodSeconds": ex_termination_grace_period, # NOQA
                        "volumes": []
                    }
                }
            }
        }
        memory = str(ex_memory) + "Mi"
        vm['spec']['template']['spec']['domain']['resources'][
            'requests']['memory'] = memory
        vm['spec']['template']['spec']['domain']['resources'][
            'limits']['memory'] = memory
        if ex_cpu < 10:
            cpu = int(ex_cpu)
            vm['spec']['template']['spec']['domain'][
                'resources']['requests']['cpu'] = cpu
            vm['spec']['template']['spec']['domain'][
                'resources']['limits']['cpu'] = cpu
        else:
            cpu = str(ex_cpu) + "m"
            vm['spec']['template']['spec']['domain']['resources'][
                'requests']['cpu'] = cpu
            vm['spec']['template']['spec']['domain']['resources'][
                'limits']['cpu'] = cpu
        i = 0
        for disk in ex_disks:
            disk_type = disk.get('disk_type')
            bus = disk.get('bus', 'virtio')
            disk_name = disk.get('name', 'disk{}'.format(i))
            i += 1
            device = disk.get('device', 'disk')
            if disk_type not in DISK_TYPES:
                raise ValueError("The possible values for this "
                                 "parameter are: ", DISK_TYPES)
            # depending on disk_type, in the future,
            # when more will be supported,
            # additional elif should be added
            if disk_type == "containerDisk":
                try:
                    image = disk['image']
                except KeyError:
                    raise KeyError('A container disk needs a '
                                   'containerized image')

                volumes_dict = {'containerDisk': {'image': image},
                                'name': disk_name}

            if disk_type == "persistentVolumeClaim":
                if 'claim_name' in disk:
                    claimName = disk['claim_name']
                    if claimName not in self.ex_list_persistent_volume_claims(
                        namespace=namespace
                    ):
                        if ('size' not in disk or "storage_class_name"
                                not in disk):
                            msg = ("disk['size'] and "
                                   "disk['storage_class_name'] "
                                   "are both required to create "
                                   "a new claim.")
                            raise KeyError(msg)
                        size = disk['size']
                        storage_class = disk['storage_class_name']
                        volume_mode = disk.get('volume_mode', 'Filesystem')
                        access_mode = disk.get('access_mode', 'ReadWriteOnce')
                        self.create_volume(size=size, name=claimName,
                                           location=location,
                                           ex_storage_class_name=storage_class,
                                           ex_volume_mode=volume_mode,
                                           ex_access_mode=access_mode)

                else:
                    msg = ("You must provide either a claim_name of an "
                           "existing claim or if you want one to be "
                           "created you must additionally provide size "
                           "and the storage_class_name of the "
                           "cluster, which allows dynamic provisioning, "
                           "so a Persistent Volume Claim can be created. "
                           "In the latter case please provide the desired "
                           "size as well.")
                    raise KeyError(msg)

                volumes_dict = {'persistentVolumeClaim': {
                                'claimName': claimName},
                                'name': disk_name}
            disk_dict = {device: {'bus': bus}, 'name': disk_name}
            vm['spec']['template']['spec']['domain'][
                'devices']['disks'].append(disk_dict)
            vm['spec']['template']['spec']['volumes'].append(volumes_dict)

        # adding image in a container Disk
        if isinstance(image, NodeImage):
            image = image.name

        volumes_dict = {'containerDisk': {'image': image},
                        'name': 'boot-disk'}
        disk_dict = {'disk': {'bus': 'virtio'}, 'name': 'boot-disk'}
        vm['spec']['template']['spec']['domain'][
            'devices']['disks'].append(disk_dict)
        vm['spec']['template']['spec']['volumes'].append(volumes_dict)

        # network
        if ex_network:
            interface = ex_network[1]
            network_name = ex_network[2]
            network_type = ex_network[0]
        # add a default network
        else:
            interface = 'masquerade'
            network_name = "netw1"
            network_type = "pod"
        network_dict = {network_type: {}, 'name': network_name}
        interface_dict = {interface: {}, 'name': network_name}
        ports = ports or {}
        if ports.get('ports_tcp'):
            ports_to_expose = []
            for port in ports['ports_tcp']:
                ports_to_expose.append(
                    {
                        'port': port,
                        'protocol': 'TCP'
                    }
                )
            interface_dict[interface]['ports'] = ports_to_expose
        if ports.get('ports_udp'):
            ports_to_expose = interface_dict[interface].get('ports', [])
            for port in ports.get('ports_udp'):
                ports_to_expose.append(
                    {
                        'port': port,
                        'protocol': 'UDP'
                    }
                )
            interface_dict[interface]['ports'] = ports_to_expose
        vm['spec']['template']['spec'][
            'networks'].append(network_dict)
        vm['spec']['template']['spec']['domain']['devices'][
            'interfaces'].append(interface_dict)

        method = "POST"
        data = json.dumps(vm)
        req = KUBEVIRT_URL + "namespaces/" + namespace + "/virtualmachines/"
        try:

            self.connection.request(req, method=method, data=data)

        except Exception:
            raise
        # check if new node is present
        nodes = self.list_nodes()
        for node in nodes:
            if node.name == name:
                self.start_node(node)
                return node

    def list_images(self, location=None):
        """
        If location (namespace) is provided only the images
        in that location will be provided. Otherwise all of them.
        """
        nodes = self.list_nodes()
        if location:
            namespace = location.name
            nodes = list(filter(lambda x: x['extra'][
                                'namespace'] == namespace, nodes))
        name_set = set()
        images = []
        for node in nodes:
            if node.image.name in name_set:
                continue
            name_set.add(node.image.name)
            images.append(node.image)

        return images

    def list_locations(self):
        """
        By locations here it is meant namespaces.
        """
        req = ROOT_URL + "namespaces"

        namespaces = []
        result = self.connection.request(req).object
        for item in result['items']:
            name = item['metadata']['name']
            ID = item['metadata']['uid']
            namespaces.append(NodeLocation(id=ID, name=name,
                                           country='',
                                           driver=self.connection.driver))
        return namespaces

    def list_sizes(self, location=None):

        namespace = ''
        if location:
            namespace = location.name
        nodes = self.list_nodes()
        sizes = []
        for node in nodes:
            if not namespace:
                sizes.append(node.size)
            elif namespace == node.extra['namespace']:
                sizes.append(node.size)

        return sizes

    def create_volume(self, size, name,
                      location=None,
                      ex_storage_class_name='',
                      ex_volume_mode='Filesystem',
                      ex_access_mode='ReadWriteOnce',
                      ex_dynamic=True,
                      ex_reclaim_policy='Recycle',
                      ex_volume_type=None,
                      ex_volume_params=None,
                      ):
        """
        :param size: The size in Gigabytes
        :type size: `int`

        :param volume_type: This is the type of volume to be created that is
                            dependent on the underlying cloud where Kubernetes
                            is deployed. K8s is supporting the following types:
                            -gcePersistentDisk
                            -awsElasticBlockStore
                            -azureFile
                            -azureDisk
                            -csi
                            -fc (Fibre Channel)
                            -flexVolume
                            -flocker
                            -nfs
                            -iSCSI
                            -rbd (Ceph Block Device)
                            -cephFS
                            -cinder (OpenStack block storage)
                            -glusterfs
                            -vsphereVolume
                            -quobyte Volumes
                            -hostPath (Single node testing only – local storage is not supported in any way and WILL NOT WORK in a multi-node cluster) # NOQA
                            -portworx Volumes
                            -scaleIO Volumes
                            -storageOS
                            This parameter is a dict in the form {type: {key1:value1, key2:value2,...}},
                            where type is one of the above and key1, key2... are type specific keys and
                            their corresponding values. eg: {nsf: {server: "172.0.0.0", path: "/tmp"}}
                                            {awsElasticBlockStore: {fsType: 'ext4', volumeID: "1234"}}
        :type volume_type: `str`

        :param volume_params: A dict with the key:value that the
                              volume_type needs.
                              This parameter is a dict in the form
                              {key1:value1, key2:value2,...},
                              where type is one of the above and key1, key2...
                              are type specific keys and
                              their corresponding values.
                              eg: for nsf volume_type
                              {server: "172.0.0.0", path: "/tmp"}
                              for awsElasticBlockStore volume_type
                              {fsType: 'ext4', volumeID: "1234"}
        """
        if ex_dynamic:
            if location is None:
                msg = "Please provide a namespace for the PVC."
                raise ValueError(msg)
            vol = self._create_volume_dynamic(
                size=size,
                name=name,
                storage_class_name=ex_storage_class_name,
                namespace=location.name,
                volume_mode=ex_volume_mode,
                access_mode=ex_access_mode)
            return vol
        else:
            if ex_volume_type is None or ex_volume_params is None:
                msg = ("An ex_volume_type must be provided from the list "
                       "of supported clouds, as well as the ex_volume_params "
                       "necessesary for your volume type choice.")
                raise ValueError(msg)

        pv = {
            'apiVersion': 'v1',
            'kind': 'PersistentVolume',
            'metadata': {
                'name': name,
            },
            'spec': {
                'capacity': {
                    'storage': str(size) + 'Gi'
                },
                'volumeMode': ex_volume_mode,
                'accessModes': [ex_access_mode],
                'persistentVolumeReclaimPolicy': ex_reclaim_policy,
                'storageClassName': ex_storage_class_name,
                'mountOptions': [],  # beta, to add in the future
                ex_volume_type: ex_volume_params,
            }
        }

        req = ROOT_URL + "persistentvolumes/"
        method = 'POST'
        data = json.dumps(pv)
        try:
            self.connection.request(req, method=method, data=data)

        except Exception:
            raise
        # make sure that the volume was created
        volumes = self.list_volumes()
        for volume in volumes:
            if volume.name == name:
                return volume

    def _create_volume_dynamic(self, size, name, storage_class_name,
                               volume_mode='Filesystem', namespace='default',
                               access_mode='ReadWriteOnce'):
        """
        Method to create a Persistent Volume Claim for storage,
        thus storage is required in the arguments.
        This method assumes dynamic provisioning of the
        Persistent Volume so the storage_class given should
        allow for it (by default it usually is), or already
        have unbounded Persistent Volumes created by an admin.

        :param name: The name of the pvc an arbitrary string of lower letters
        :type name: `str`

        :param size: An int of the ammount of gigabytes desired
        :type size: `int`

        :param namespace: The namespace where the claim will live
        :type namespace: `str`

        :param storage_class_name: If you want the pvc to be bound to
                                 a particular class of PVs specified here.
        :type storage_class_name: `str`

        :param access_mode: The desired access mode, ie "ReadOnlyMany"
        :type access_mode: `str`

        :param matchLabels: A dictionary with the labels, ie:
                            {'release': 'stable,}
        :type matchLabels: `dict` with keys `str` and values `str`
        """
        pvc = {
            'apiVersion': 'v1',
            'kind': 'PersistentVolumeClaim',
            'metadata': {
                'name': name
            },
            'spec': {
                'accessModes': [],
                'volumeMode': volume_mode,
                'resources': {
                    'requests': {
                        'storage': ''
                    }
                },
            }
        }

        pvc['spec']['accessModes'].append(access_mode)

        if storage_class_name is not None:
            pvc['spec']['storageClassName'] = storage_class_name
        else:
            raise ValueError("The storage class name must be provided of a"
                             "storage class which allows for dynamic "
                             "provisioning")
        pvc['spec']['resources']['requests']['storage'] = str(size) + 'Gi'

        method = "POST"
        req = ROOT_URL + "namespaces/" + namespace + "/persistentvolumeclaims"
        data = json.dumps(pvc)
        try:
            result = self.connection.request(req, method=method, data=data)
        except Exception:
            raise
        if result.object['status']['phase'] != "Bound":
            for _ in range(3):

                req = ROOT_URL + "namespaces/" + namespace + \
                    "/persistentvolumeclaims/" + name
                try:
                    result = self.connection.request(req).object
                except Exception:
                    raise
                if result['status']['phase'] == "Bound":
                    break
                time.sleep(3)

        # check that the pv was created and bound
        volumes = self.list_volumes()
        for volume in volumes:
            if volume.extra['pvc']['name'] == name:
                return volume

    def _bind_volume(self, volume, namespace='default'):
        """
        This method is for unbound volumes that were statically made.
        It will bind them to a pvc so they can be used by
        a kubernetes resource.
        """
        if volume.extra['is_bound']:
            return  # volume already bound

        storage_class = volume.extra['storage_class_name']
        size = volume.size
        name = volume.name + "-pvc"
        volume_mode = volume.extra['volume_mode']
        access_mode = volume.extra['access_modes'][0]

        vol = self._create_volume_dynamic(size=size, name=name,
                                          storage_class_name=storage_class,
                                          volume_mode=volume_mode,
                                          namespace=namespace,
                                          access_mode=access_mode)
        return vol

    def destroy_volume(self, volume):
        # first delete the pvc
        method = 'DELETE'
        if volume.extra['is_bound']:
            pvc = volume.extra['pvc']['name']
            namespace = volume.extra['pvc']['namespace']
            req = ROOT_URL + "namespaces/" + namespace + \
                "/persistentvolumeclaims/" + pvc
            try:
                result = self.connection.request(req, method=method)

            except Exception:
                raise

        pv = volume.name
        req = ROOT_URL + "persistentvolumes/" + pv

        try:
            result = self.connection.request(req, method=method)
            return result.status
        except Exception:
            raise

    def attach_volume(self, node, volume, device='disk',
                      ex_bus='virtio', ex_name=None):
        """
        params: bus, name , device (disk or lun)
        """
        # volume must be bound to a claim
        if not volume.extra['is_bound']:
            volume = self._bind_volume(volume, node.extra['namespace'])
            if volume is None:
                raise LibcloudError("Selected Volume (PV) could not be bound "
                                    "(to a PVC), please select another volume",
                                    driver=self)

        claimName = volume.extra['pvc']['name']
        if ex_name is None:
            name = claimName
        else:
            name = ex_name
        namespace = volume.extra['pvc']['namespace']
        # check if vm is stopped
        self.stop_node(node)
        # check if it is the same namespace
        if node.extra['namespace'] != namespace:
            msg = "The PVC and the VM must be in the same namespace"
            raise ValueError(msg)
        vm = node.name
        req = KUBEVIRT_URL + 'namespaces/' + namespace + '/virtualmachines/'\
            + vm
        disk_dict = {device: {'bus': ex_bus}, 'name': name}
        volumes_dict = {'persistentVolumeClaim': {'claimName': claimName},
                        'name': name}
        # Get all the volumes of the vm
        try:
            result = self.connection.request(req).object
        except Exception:
            raise
        disks = result['spec']['template']['spec']['domain'][
            'devices']['disks']
        volumes = result['spec']['template']['spec']['volumes']
        disks.append(disk_dict)
        volumes.append(volumes_dict)
        # now patch the new volumes and disks lists into the resource
        headers = {"Content-Type": "application/merge-patch+json"}
        data = {'spec': {
            'template': {
                'spec': {
                    'volumes': volumes,
                    'domain': {
                        'devices':
                        {'disks': disks}
                    }
                }
            }
        }
        }
        try:
            result = self.connection.request(req, method="PATCH",
                                             data=json.dumps(data),
                                             headers=headers)
            if 'pvcs' in node.extra:
                node.extra['pvcs'].append(claimName)
            else:
                node.extra['pvcs'] = [claimName]
            return result in VALID_RESPONSE_CODES
        except Exception:
            raise

    def detach_volume(self, volume, ex_node):
        """
        Detaches a volume from a node but the node must be given since a PVC
        can have more than one VMI's pointing to it
        """
        # vmi must be stopped
        self.stop_node(ex_node)

        claimName = volume.extra['pvc']['name']
        name = ex_node.name
        namespace = ex_node.extra['namespace']
        req = KUBEVIRT_URL + 'namespaces/' + namespace + '/virtualmachines/'\
            + name
        headers = {"Content-Type": "application/merge-patch+json"}
        # Get all the volumes of the vm

        try:
            result = self.connection.request(req).object
        except Exception:
            raise
        disks = result['spec']['template']['spec']['domain'][
            'devices']['disks']
        volumes = result['spec']['template']['spec']['volumes']
        to_delete = None
        for volume in volumes:
            if 'persistentVolumeClaim' in volume:
                if volume['persistentVolumeClaim']['claimName'] == claimName:
                    to_delete = volume['name']
                    volumes.remove(volume)
                    break
        if not to_delete:
            msg = "The given volume is not attached to the given VM"
            raise ValueError(msg)

        for disk in disks:
            if disk['name'] == to_delete:
                disks.remove(disk)
                break
        # now patch the new volumes and disks lists into the resource
        data = {'spec': {
            'template': {
                'spec': {
                    'volumes': volumes,
                    'domain': {
                        'devices':
                        {'disks': disks}
                    }
                }
            }
        }
        }
        try:
            result = self.connection.request(req, method="PATCH",
                                             data=json.dumps(data),
                                             headers=headers)
            ex_node.extra['pvcs'].remove(claimName)
            return result in VALID_RESPONSE_CODES
        except Exception:
            raise

    def ex_list_persistent_volume_claims(self, namespace="default"):

        pvc_req = ROOT_URL + "namespaces/" + namespace + \
            "/persistentvolumeclaims"
        try:
            result = self.connection.request(pvc_req).object
        except Exception:
            raise
        pvcs = [item['metadata']['name'] for item in result['items']]
        return pvcs

    def ex_list_storage_classes(self):

        # sc = storage class
        sc_req = "/apis/storage.k8s.io/v1/storageclasses"
        try:
            result = self.connection.request(sc_req).object
        except Exception:
            raise
        scs = [item['metadata']['name'] for item in result['items']]

        return scs

    def list_volumes(self):
        """
        Location is a namespace of the cluster.
        """
        volumes = []

        pv_rec = ROOT_URL + "/persistentvolumes/"

        try:
            result = self.connection.request(pv_rec).object
        except Exception:
            raise

        for item in result['items']:
            if item['status']['phase'] not in {'Available', 'Bound'}:
                continue
            ID = item['metadata']['uid']
            size = item['spec']['capacity']['storage']
            size = int(size.rstrip('Gi'))
            extra = {'pvc': {}}
            extra['storage_class_name'] = item['spec']['storageClassName']
            extra['is_bound'] = item['status']['phase'] == "Bound"
            extra['access_modes'] = item['spec']['accessModes']
            extra['volume_mode'] = item['spec']['volumeMode']
            if extra['is_bound']:
                extra['pvc']['name'] = item['spec']['claimRef']['name']
                extra['pvc']['namespace'] = item['spec']['claimRef'][
                    'namespace']
                extra['pvc']['uid'] = item['spec']['claimRef']['uid']
                name = extra['pvc']['name']
            else:
                name = item['metadata']['name']
            volume = StorageVolume(id=ID, name=name, size=size,
                                   driver=self.connection.driver,
                                   extra=extra)
            volumes.append(volume)

        return volumes

    def _ex_connection_class_kwargs(self):
        kwargs = {}
        if hasattr(self, 'key_file'):
            kwargs['key_file'] = self.key_file
        if hasattr(self, 'cert_file'):
            kwargs['cert_file'] = self.cert_file
        return kwargs

    def _to_node(self, vm, is_stopped=False):
        """
        """
        ID = vm['metadata']['uid']
        name = vm['metadata']['name']
        driver = self.connection.driver
        extra = {'namespace': vm['metadata']['namespace']}
        extra['pvcs'] = []
        memory = 0
        if 'limits' in vm['spec']['template']['spec'][
                'domain']['resources']:
            if 'memory' in vm['spec']['template']['spec'][
                    'domain']['resources']['limits']:
                memory = vm['spec']['template']['spec'][
                    'domain']['resources']['limits']['memory']
        elif vm['spec']['template']['spec']['domain']['resources'].get(
                'requests', None):

            if vm['spec']['template']['spec'][
               'domain']['resources']['requests'].get('memory', None):
                memory = vm['spec']['template']['spec'][
                    'domain']['resources']['requests']['memory']
        if not isinstance(memory, int):
            if 'M' in memory or 'Mi' in memory:
                memory = memory.rstrip('M')
                memory = memory.rstrip('Mi')
                memory = int(memory)
            elif 'G' in memory:
                memory = memory.rstrip('G')
                memory = int(memory) // 1000
            elif 'Gi' in memory:
                memory = memory.rstrip('Gi')
                memory = int(memory) // 1024
        cpu = 1
        if vm['spec']['template']['spec'][
                'domain']['resources'].get('limits', None):
            if vm['spec']['template']['spec']['domain']['resources'][
               'limits'].get('cpu', None):
                cpu = vm['spec']['template']['spec'][
                    'domain']['resources']['limits']['cpu']
        elif vm['spec']['template']['spec'][
            'domain']['resources'].get('requests', None) and vm[
                'spec']['template']['spec'][
                'domain']['resources']['requests'].get('cpu', None):
            cpu = vm['spec']['template']['spec'][
                'domain']['resources']['requests']['cpu']
        elif vm['spec']['template']['spec']['domain'].get('cpu', None):
            cpu = vm['spec']['template']['spec']['domain'][
                'cpu'].get('cores', 1)
        if not isinstance(cpu, int):
            cpu = int(cpu.rstrip('m'))
        extra_size = {'cpus': cpu}
        size_name = "{} vCPUs, {}MB Ram".format(str(cpu), str(memory))
        size_id = hashlib.md5(size_name.encode("utf-8")).hexdigest()
        size = NodeSize(id=size_id, name=size_name, ram=memory,
                        disk=0, bandwidth=0, price=0,
                        driver=driver, extra=extra_size)
        extra['memory'] = memory
        extra['cpu'] = cpu
        image_name = "undefined"
        for volume in vm['spec']['template'][
                'spec']['volumes']:
            for k, v in volume.items():
                if type(v) is dict:
                    if 'image' in v:
                        image_name = v['image']
        image = NodeImage(image_name, image_name, driver)
        if 'volumes' in vm['spec']['template']['spec']:
            for volume in vm['spec']['template']['spec']['volumes']:
                if 'persistentVolumeClaim' in volume:
                    extra['pvcs'].append(volume[
                        'persistentVolumeClaim']['claimName'])
        port_forwards = []
        services = self.ex_list_services(namespace=extra['namespace'],
                                         node_name=name)
        for service in services:
            service_type = service['spec'].get('type')
            for port_pair in service['spec']['ports']:
                protocol = port_pair.get('protocol')
                public_port = port_pair.get('port')
                local_port = port_pair.get('targetPort')
                try:
                    int(local_port)
                except ValueError:
                    local_port = public_port
                port_forwards.append({
                    'local_port': local_port,
                    'public_port': public_port,
                    'protocol': protocol,
                    'service_type': service_type
                })
        extra['port_forwards'] = port_forwards
        if is_stopped:
            state = NodeState.STOPPED
            public_ips = None
            private_ips = None
            return Node(id=ID, name=name, state=state,
                        public_ips=public_ips,
                        private_ips=private_ips,
                        driver=driver, size=size,
                        image=image, extra=extra)

        # getting image and image_ID from the container
        req = ROOT_URL + "namespaces/" + extra['namespace'] + "/pods"
        result = self.connection.request(req).object
        pod = None
        for pd in result['items']:
            if 'metadata' in pd and 'ownerReferences' in pd['metadata']:
                if pd['metadata']['ownerReferences'][0]['name'] == name:
                    pod = pd
        if pod is None or 'containerStatuses' not in pod['status']:
            state = NodeState.PENDING
            public_ips = None
            private_ips = None
            return Node(id=ID, name=name, state=state,
                        public_ips=public_ips,
                        private_ips=private_ips,
                        driver=driver, size=size,
                        image=image, extra=extra)
        extra['pod'] = {'name': pod['metadata']['name']}
        for cont_status in pod['status']['containerStatuses']:
            # only 2 containers are present the launcher and the vmi
            if cont_status['name'] != 'compute':
                image = NodeImage(ID, cont_status['image'],
                                  driver)
                state = NodeState.RUNNING if "running" in cont_status[
                    'state'] else NodeState.PENDING
        public_ips = None
        created_at = datetime.strptime(vm['metadata']['creationTimestamp'],
                                       '%Y-%m-%dT%H:%M:%SZ')

        if 'podIPs' in pod['status']:
            private_ips = [ip['ip'] for ip in pod['status']['podIPs']]
        else:
            private_ips = []

        return Node(id=ID, name=name, state=state,
                    public_ips=public_ips,
                    private_ips=private_ips,
                    driver=driver, size=size,
                    image=image, extra=extra,
                    created_at=created_at)

    def ex_list_services(self, namespace='default', node_name=None,
                         service_name=None):
        '''
        If node_name is given then the services returned will be those that
        concern the node
        '''
        params = None
        if service_name is not None:
            params = {'fieldSelector': 'metadata.name={}'.format(service_name)}
        req = ROOT_URL + '/namespaces/{}/services'.format(namespace)
        result = self.connection.request(req, params=params).object['items']
        if node_name:
            res = []
            for service in result:
                if node_name in service['metadata'].get('name', ""):
                    res.append(service)
            return res
        return result

    def ex_create_service(self, node, ports, service_type="NodePort",
                          cluster_ip=None, load_balancer_ip=None,
                          override_existing_ports=False):
        '''
        Each node has a single service of one type on which the exposed ports
        are described. If a service exists then the port declared will be
        exposed alongside the existing ones, set override_existing_ports=True
        to delete existing exposed ports and expose just the ones in the port
        variable.

        param node: the libcloud node for which the ports will be exposed
        type  node: libcloud `Node` class

        param ports: a list of dictionaries with keys --> values:
                     'port' --> port to be exposed on the service
                     'target_port' --> port on the pod/node, optional
                                       if empty then it gets the same
                                       value as 'port' value
                     'protocol' ---> either 'UDP' or 'TCP', defaults to TCP
                     'name' --> A name for the service
                     If ports is an empty `list` and a service exists of this
                     type then the service will be deleted.
        type  ports: `list` of `dict` where each `dict` has keys --> values:
                     'port' --> `int`
                     'target_port' --> `int`
                     'protocol' --> `str`
                     'name' --> `str`

        param service_type: Valid types are ClusterIP, NodePort, LoadBalancer
        type  service_type: `str`

        param cluster_ip: This can be set with an IP string value if you want
                          manually set the service's internal IP. If the value
                          is not correct the method will fail, this value can't
                          be updated.
        type  cluster_ip: `str`

        param override_existing_ports: Set to True if you want to delete the
                                       existing ports exposed by the service
                                       and keep just the ones declared in the
                                       present ports argument.
                                       By default it is false and if the
                                       service already exists the ports will be
                                       added to the existing ones.
        type  override_existing_ports: `boolean`
        '''
        # check if service exists first
        namespace = node.extra.get('namespace', 'default')
        service_name = 'service-{}-{}'.format(service_type.lower(), node.name)
        service_list = self.ex_list_services(namespace=namespace,
                                             service_name=service_name)

        ports_to_expose = []
        # if ports has a falsey value like None or 0
        if not ports:
            ports = []
        for port_group in ports:
            if not port_group.get('target_port', None):
                port_group['target_port'] = port_group['port']
            if not port_group.get('name', ""):
                port_group['name'] = 'port-{}'.format(port_group['port'])
            ports_to_expose.append(
                {'protocol': port_group.get('protocol', 'TCP'),
                 'port': int(port_group['port']),
                 'targetPort': int(port_group['target_port']),
                 'name': port_group['name']})
        headers = None
        data = None
        if len(service_list) > 0:
            if not ports:
                result = True
                for service in service_list:
                    service_name = service['metadata']['name']
                    result = result and self.ex_delete_service(
                        namespace=namespace,
                        service_name=service_name)
                return result
            else:
                method = 'PATCH'
                spec = {'ports': ports_to_expose}
                if not override_existing_ports:
                    existing_ports = service_list[0]['spec']['ports']
                    spec = {'ports': existing_ports.extend(ports_to_expose)}
                data = json.dumps({'spec': spec})
                headers = {"Content-Type": "application/merge-patch+json"}
            req = "{}/namespaces/{}/services/{}".format(
                ROOT_URL, namespace, service_name
            )
        else:
            if not ports:
                raise ValueError("Argument ports is empty but there is no "
                                 "service of {} type to be deleted".format(
                                     service_type
                                 ))
            method = 'POST'
            service = {
                'kind': 'Service',
                'apiVersion': 'v1',
                'metadata': {
                    'name': service_name,
                    'labels': {
                        'service': 'kubevirt.io'
                    }
                },
                'spec': {
                    'type': "",
                    'selector': {
                        "kubevirt.io/vm": node.name
                    },
                    'ports': []
                },
            }
            service['spec']['ports'] = ports_to_expose
            service['spec']['type'] = service_type
            if cluster_ip is not None:
                service['spec']['clusterIP'] = cluster_ip
            if service_type == "LoadBalancer" and load_balancer_ip is not None:
                service['spec']['loadBalancerIP'] = load_balancer_ip
            data = json.dumps(service)
            req = "{}/namespaces/{}/services".format(ROOT_URL, namespace)
        try:
            result = self.connection.request(req, method=method, data=data,
                                             headers=headers)
        except Exception:
            raise
        return result.status in VALID_RESPONSE_CODES

    def ex_delete_service(self, namespace, service_name):
        req = "{}/namespaces/{}/services/{}".format(ROOT_URL, namespace,
                                                    service_name)
        headers = {"Content-Type": "application/yaml"}
        try:
            result = self.connection.request(req, method="DELETE",
                                             headers=headers)
        except Exception:
            raise
        return result.status in VALID_RESPONSE_CODES
