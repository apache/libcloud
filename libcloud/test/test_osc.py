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
try:
    from libcloud.common.osc import
except ImportError as ie:
    has_gateway = False
else:
    has_gateway = True

from libcloud.common.base import ConnectionUserAndKey
from libcloud.compute.base import NodeDriver
from libcloud.compute.types import Provider
from libcloud.compute.drivers.ec2 import OUTSCALE_INC_REGION_DETAILS

SERVICE_TYPE = 'compute'


class OutscaleSDKConnection(ConnectionUserAndKey):
    """
    Outscale SDK connection
    """

    @staticmethod
    def gtw_connection(self, access_key, secret_key, region='eu-west-2'):
        """
        Set the gateway connection.

        :param      access_key: personnal access key (required)
        :type       access_key: ``str``

        :param      secret_key: personnal secret key (required)
        :type       secret_key: ``str``

        :param      region: region
        :type       region: ``str``

        :return: request
        :rtype: ``dict``
        """
        return Gateway(**{
            'access_key': access_key,
            'secret_key': secret_key,
            'region': region
        })


class OutscaleSDKNodeDriver(NodeDriver):
    """
    Outscale SDK node driver
    """

    type = Provider.OUTSCALE_SDK
    connectionCls = OutscaleSDKConnection
    name = 'Outscale SDK'
    website = 'http://www.outscale.com'

    def __init__(self, key, secret, region='eu-west-2'):
        global gtw
        if has_gateway:
            gtw = OutscaleSDKConnection.gtw_connection(key, secret, region)

    def list_locations(self):
        """
        Lists available regions details.

        :return: regions details
        :rtype: ``dict``
        """
        return OUTSCALE_INC_REGION_DETAILS

    def create_public_ip(self):
        """
        Create a new public ip.

        :return: the created public ip
        :rtype: ``dict``
        """
        return gtw.CreatePublicIp()

    def create_node(self, image_id):
        """
        Create a new instance.

        :param      image_id: the ID of the OMI
                    used to create the VM (required)
        :type       image_id: ``str``

        :return: the created instance
        :rtype: ``dict``
        """
        return gtw.CreateVms(ImageId=image_id)

    def reboot_node(self, node_ids):
        """
        Reboot instances.

        :param      node_ids: the ID(s) of the VM(s)
                    you want to reboot (required)
        :type       node_ids: ``list``

        :return: the rebooted instances
        :rtype: ``dict``
        """
        return gtw.RebootVms(VmIds=node_ids)

    def list_nodes(self):
        """
        List all nodes.

        :return: nodes
        :rtype: ``dict``
        """
        return gtw.ReadVms()

    def delete_node(self, node_ids):
        """
        Delete instances.

        :param      node_ids: one or more IDs of VMs (required)
        :type       node_ids: ``list``

        :return: request
        :rtype: ``dict``
        """
        return gtw.DeleteVms(VmIds=node_ids)

    def create_image(self, node_id, name, description=''):
        """
        Create a new image.

        :param      node_id: the ID of the VM from which
                    you want to create the OMI (required)
        :type       node_id: ``str``

        :param      name: a unique name for the new OMI (required)
        :type       name: ``str``

        :param      description: a description for the new OMI
        :type       description: ``str``

        :return: the created image
        :rtype: ``dict``
        """
        return gtw.CreateImage(
            VmId=node_id,
            ImageName=name,
            Description=description
        )

    def list_images(self):
        """
        List all images.

        :return: images
        :rtype: ``dict``
        """
        return gtw.ReadImages()

    def get_image(self, image_id):
        """
        Get a specific image.

        :param      image_id: the ID of the image you want to select (required)
        :type       image_id: ``str``

        :return: the selected image
        :rtype: ``dict``
        """
        img = None
        images = gtw.ReadImages()
        for image in images.get('Images'):
            if image.get('ImageId') == image_id:
                img = image
        return img

    def delete_image(self, image_id):
        """
        Delete an image.

        :param      image_id: the ID of the OMI you want to delete (required)
        :type       image_id: ``str``

        :return: request
        :rtype: ``dict``
        """
        return gtw.DeleteImage(ImageId=image_id)

    def create_key_pair(self, name):
        """
        Create a new key pair.

        :param      node_id: a unique name for the keypair, with a maximum
                    length of 255 ASCII printable characters (required)
        :type       node_id: ``str``

        :return: the created key pair
        :rtype: ``dict``
        """
        return gtw.CreateKeypair(KeypairName=name)

    def list_key_pairs(self):
        """
        List all key pairs.

        :return: key pairs
        :rtype: ``dict``
        """
        return gtw.ReadKeypairs()

    def get_key_pair(self, name):
        """
        Get a specific key pair.

        :param      name: the name of the key pair
                    you want to select (required)
        :type       name: ``str``

        :return: the selected key pair
        :rtype: ``dict``
        """
        kp = None
        key_pairs = gtw.ReadKeypairs()
        for key_pair in key_pairs.get('Keypairs'):
            if key_pair.get('KeypairName') == name:
                kp = key_pair
        return kp

    def delete_key_pair(self, name):
        """
        Delete an image.

        :param      name: the name of the keypair you want to delete (required)
        :type       name: ``str``

        :return: request
        :rtype: ``dict``
        """
        return gtw.DeleteKeypair(KeypairName=name)

    def create_snapshot(self):
        """
        Create a new snapshot.

        :return: the created snapshot
        :rtype: ``dict``
        """
        return gtw.CreateSnapshot()

    def list_snapshots(self):
        """
        List all snapshots.

        :return: snapshots
        :rtype: ``dict``
        """
        return gtw.ReadSnapshots()

    def delete_snapshot(self, snapshot_id):
        """
        Delete a snapshot.

        :param      snapshot_id: the ID of the snapshot
                    you want to delete (required)
        :type       snapshot_id: ``str``

        :return: request
        :rtype: ``dict``
        """
        return gtw.DeleteSnapshot(SnapshotId=snapshot_id)

    def create_volume(
        self, snapshot_id,
        size=1,
        location='eu-west-2a',
        volume_type='standard'
    ):
        """
        Create a new volume.

        :param      snapshot_id: the ID of the snapshot from which
                    you want to create the volume (required)
        :type       snapshot_id: ``str``

        :param      size: the size of the volume, in gibibytes (GiB),
                    the maximum allowed size for a volume is 14,901 GiB
        :type       size: ``int``

        :param      location: the Subregion in which
                    you want to create the volume
        :type       location: ``str``

        :param      volume_type: the type of volume
                    you want to create (io1 | gp2 | standard)
        :type       volume_type: ``str``

        :return: the created volume
        :rtype: ``dict``
        """
        return gtw.CreateVolume(
            SnapshotId=snapshot_id,
            Size=size,
            SubregionName=location,
            VolumeType=volume_type
        )

    def list_volumes(self):
        """
        List all volumes.

        :return: volumes
        :rtype: ``dict``
        """
        return gtw.ReadVolumes()

    def delete_volume(self, volume_id):
        """
        Delete a volume.

        :param      volume_id: the ID of the volume
                    you want to delete (required)
        :type       volume_id: ``str``

        :return: request
        :rtype: ``dict``
        """
        return gtw.DeleteVolume(VolumeId=volume_id)

    def attach_volume(self, node_id, volume_id, device):
        """
        Attach a volume.

        :param      node_id: the ID of the VM you want
                    to attach the volume to (required)
        :type       node_id: ``str``

        :param      volume_id: the ID of the volume
                    you want to attach (required)
        :type       volume_id: ``str``

        :param      device: the name of the device (required)
        :type       device: ``str``

        :return: the attached volume
        :rtype: ``dict``
        """
        return gtw.LinkVolume(
            VmId=node_id,
            VolumeId=volume_id,
            DeviceName=device
        )

    def detach_volume(self, volume_id, force=False):
        """
        Detach a volume.

        :param      volume_id: the ID of the volume
                    you want to detach (required)
        :type       volume_id: ``str``

        :param      force: forces the detachment of
                    the volume in case of previous failure
        :type       force: ``str``

        :return: the attached volume
        :rtype: ``dict``
        """
        return gtw.UnlinkVolume(VolumeId=volume_id, ForceUnlink=force)
