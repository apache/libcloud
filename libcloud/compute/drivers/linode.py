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

"""libcloud driver for the Linode(R) API

This driver implements all libcloud functionality for the Linode API.

Linode home page                    http://www.linode.com/
Linode API documentation            https://www.linode.com/docs/api/

Linode(R) is a registered trademark of Linode, LLC.

"""

import re
import binascii
from datetime import datetime

from libcloud.utils.py3 import httplib
from libcloud.compute.base import (
    Node,
    KeyPair,
    NodeSize,
    NodeImage,
    NodeDriver,
    NodeLocation,
    StorageVolume,
)
from libcloud.common.linode import (
    DEFAULT_API_VERSION,
    LINODE_DISK_FILESYSTEMS_V4,
    LinodeDisk,
    LinodeIPAddress,
    LinodeExceptionV4,
    LinodeConnectionV4,
)
from libcloud.compute.types import Provider, NodeState, StorageVolumeState
from libcloud.utils.networking import is_private_subnet

try:
    import simplejson as json
except ImportError:
    import json


class LinodeNodeDriver(NodeDriver):
    name = "Linode"
    website = "http://www.linode.com/"
    type = Provider.LINODE

    def __new__(
        cls,
        key,
        secret=None,
        secure=True,
        host=None,
        port=None,
        api_version=DEFAULT_API_VERSION,
        region=None,
        **kwargs,
    ):
        if cls is LinodeNodeDriver:
            if api_version == "4.0":
                cls = LinodeNodeDriverV4
            else:
                raise NotImplementedError(
                    "No Linode driver found for API version: %s" % (api_version)
                )
        return super().__new__(cls)


class LinodeNodeDriverV4(LinodeNodeDriver):
    connectionCls = LinodeConnectionV4
    _linode_disk_filesystems = LINODE_DISK_FILESYSTEMS_V4

    LINODE_STATES = {
        "running": NodeState.RUNNING,
        "stopped": NodeState.STOPPED,
        "provisioning": NodeState.STARTING,
        "offline": NodeState.STOPPED,
        "booting": NodeState.STARTING,
        "rebooting": NodeState.REBOOTING,
        "shutting_down": NodeState.STOPPING,
        "deleting": NodeState.PENDING,
        "migrating": NodeState.MIGRATING,
        "rebuilding": NodeState.UPDATING,
        "cloning": NodeState.MIGRATING,
        "restoring": NodeState.PENDING,
        "resizing": NodeState.RECONFIGURING,
    }

    LINODE_DISK_STATES = {
        "ready": StorageVolumeState.AVAILABLE,
        "not ready": StorageVolumeState.CREATING,
        "deleting": StorageVolumeState.DELETING,
    }

    LINODE_VOLUME_STATES = {
        "creating": StorageVolumeState.CREATING,
        "active": StorageVolumeState.AVAILABLE,
        "resizing": StorageVolumeState.UPDATING,
        "contact_support": StorageVolumeState.UNKNOWN,
    }

    def list_nodes(self):
        """
        Returns a list of Linodes the API key in use has access
        to view.

        :return: List of node objects
        :rtype: ``list`` of :class:`Node`
        """

        data = self._paginated_request("/v4/linode/instances", "data")
        return [self._to_node(obj) for obj in data]

    def list_sizes(
        self,
        location=None,
    ):
        """
        Returns a list of Linode Types

        : rtype: ``list`` of :class: `NodeSize`
        """
        data = self._paginated_request("/v4/linode/types", "data")
        return [self._to_size(obj) for obj in data]

    def list_images(
        self,
        location=None,
    ):
        """
        Returns a list of images

        :rtype: ``list`` of :class:`NodeImage`
        """
        data = self._paginated_request("/v4/images", "data")
        return [self._to_image(obj) for obj in data]

    def create_key_pair(self, name, public_key=""):
        """
        Creates an SSH keypair

        :param name: The name to be given to the keypair (required).\
        :type name: `str`

        :keyword public_key: Contents of the public key the the SSH key pair
        :type public_key: `str`

        :rtype: :class: `KeyPair`
        """
        attr = {"label": name, "ssh_key": public_key}
        response = self.connection.request(
            "/v4/profile/sshkeys", data=json.dumps(attr), method="POST"
        ).object
        return self._to_key_pair(response)

    def list_key_pairs(self):
        """
        Provide a list of all the SSH keypairs in your account.

        :rtype: ``list`` of :class: `KeyPair`
        """
        data = self._paginated_request("/v4/profile/sshkeys", "data")
        return [self._to_key_pair(obj) for obj in data]

    def list_locations(self):
        """
        Lists the Regions available for Linode services

        :rtype: ``list`` of :class:`NodeLocation`
        """
        data = self._paginated_request("/v4/regions", "data")
        return [self._to_location(obj) for obj in data]

    def start_node(self, node):
        """Boots a node the API Key has permission to modify

        :param       node: the node to start
        :type        node: :class:`Node`

        :rtype: ``bool``
        """
        if not isinstance(node, Node):
            raise LinodeExceptionV4("Invalid node instance")

        response = self.connection.request("/v4/linode/instances/%s/boot" % node.id, method="POST")
        return response.status == httplib.OK

    def ex_start_node(self, node):
        # NOTE: This method is here for backward compatibility reasons after
        # this method was promoted to be part of the standard compute API in
        # Libcloud v2.7.0
        return self.start_node(node=node)

    def stop_node(self, node):
        """Shuts down a a node the API Key has permission to modify.

        :param       node: the Linode to destroy
        :type        node: :class:`Node`

        :rtype: ``bool``
        """
        if not isinstance(node, Node):
            raise LinodeExceptionV4("Invalid node instance")

        response = self.connection.request(
            "/v4/linode/instances/%s/shutdown" % node.id, method="POST"
        )
        return response.status == httplib.OK

    def ex_stop_node(self, node):
        # NOTE: This method is here for backward compatibility reasons after
        # this method was promoted to be part of the standard compute API in
        # Libcloud v2.7.0
        return self.stop_node(node=node)

    def destroy_node(self, node):
        """Deletes a node the API Key has permission to `read_write`

        :param       node: the Linode to destroy
        :type        node: :class:`Node`

        :rtype: ``bool``
        """
        if not isinstance(node, Node):
            raise LinodeExceptionV4("Invalid node instance")

        response = self.connection.request("/v4/linode/instances/%s" % node.id, method="DELETE")
        return response.status == httplib.OK

    def reboot_node(self, node):
        """Reboots a node the API Key has permission to modify.

        :param       node: the Linode to destroy
        :type        node: :class:`Node`

        :rtype: ``bool``
        """
        if not isinstance(node, Node):
            raise LinodeExceptionV4("Invalid node instance")

        response = self.connection.request(
            "/v4/linode/instances/%s/reboot" % node.id, method="POST"
        )
        return response.status == httplib.OK

    def create_node(
        self,
        # Previously, the following 3 parameters did not match the rest of the libcloud
        # codebase drivers. They should be in the same order as other compute drivers.
        # Previously, it looked like this:
        #         size,
        #         image=None,
        #         name=None,
        #
        # Comments welcome on how backwards compatibility (if any) should work here.
        # Since it was not compatible with other drivers, it is not clear to me if this
        # would break anyone's codebase if they were not using any other libcloud drivers
        # to other cloud providers in the first place. If they were not, that seems to
        # kind of defeat the purpose of using libcloud.
        name,  # Can be None
        size,  # Can be None
        image,  # Can be None
        location=None,
        auth=None,
        root_pass=None,
        ex_authorized_keys=None,
        ex_authorized_users=None,
        ex_tags=None,
        ex_backups_enabled=False,
        ex_private_ip=False,
        ex_userdata=None,
    ):
        """Creates a Linode Instance.
        In order for this request to complete successfully,
        the user must have the `add_linodes` grant as this call
        will incur a charge.

        :param location: which region to create the node in
        :type    location: :class:`NodeLocation`

        :param size: the plan size to create
        :type    size: :class:`NodeSize`

        :keyword image: which distribution to deploy on the node
        :type    image: :class:`NodeImage`

        :keyword name: the name to assign to node.\
        Must start with an alpha character.\
        May only consist of alphanumeric characters,\
         dashes (-), underscores (_) or periods (.).\
        Cannot have two dashes (--), underscores (__) or periods (..) in a row.
        :type    name: ``str``

        :keyword root_pass: the root password (required if image is provided)
        :type    root_pass: ``str``

        :keyword ex_authorized_keys: a list of public SSH keys
        :type    ex_authorized_keys: ``list`` of ``str``

        :keyword ex_authorized_users:  a list of usernames.\
        If the usernames have associated SSH keys,\
        the keys will be appended to the root users `authorized_keys`
        :type    ex_authorized_users: ``list`` of ``str``

        :keyword ex_tags: list of tags for the node
        :type    ex_tags: ``list`` of ``str``

        :keyword ex_backups_enabled: whether to be enrolled \
        in the Linode Backup service (False)
        :type    ex_backups_enabled: ``bool``

        :keyword ex_private_ip: whether or not to request a private IP
        :type    ex_private_ip: ``bool``

        :keyword ex_userdata: add cloud-config compatible userdata to be
        processed by cloud-init inside the Linode instance. NOTE: the
        contents of this string must be base64 encoded before passing
        it to this function.
        :type    ex_userdata: ``str``

        :return: Node representing the newly-created node
        :rtype: :class:`Node`
        """

        if not isinstance(location, NodeLocation):
            raise LinodeExceptionV4("Invalid location instance")

        if not isinstance(size, NodeSize):
            raise LinodeExceptionV4("Invalid size instance")

        attr = {
            "region": location.id,
            "type": size.id,
            "private_ip": ex_private_ip,
            "backups_enabled": ex_backups_enabled,
        }

        if ex_userdata:
            attr["metadata"] = {
                "user_data": binascii.b2a_base64(bytes(ex_userdata.encode("utf-8")))
                .decode("ascii")
                .strip()
            }

        if image is not None:
            if root_pass is None:
                raise LinodeExceptionV4("root password required " "when providing an image")
            attr["image"] = image.id
            attr["root_pass"] = root_pass

        if name is not None:
            valid_name = r"^[a-zA-Z]((?!--|__|\.\.)[a-zA-Z0-9-_.])+$"
            if not re.match(valid_name, name):
                raise LinodeExceptionV4("Invalid name")
            attr["label"] = name
        if ex_authorized_keys is not None:
            attr["authorized_keys"] = list(ex_authorized_keys)
        if ex_authorized_users is not None:
            attr["authorized_users"] = list(ex_authorized_users)
        if ex_tags is not None:
            attr["tags"] = list(ex_tags)

        response = self.connection.request(
            "/v4/linode/instances", data=json.dumps(attr), method="POST"
        ).object
        return self._to_node(response)

    def ex_get_node(self, node_id):
        """
        Return a Node object based on a node ID.

        :keyword node_id: Node's ID
        :type    node_id: ``str``

        :return: Created node
        :rtype  : :class:`Node`
        """
        response = self.connection.request("/v4/linode/instances/%s" % node_id).object
        return self._to_node(response)

    def ex_list_disks(self, node):
        """
        List disks associated with the node.

        :param    node: Node to list disks. (required)
        :type       node: :class:`Node`

        :rtype: ``list`` of :class:`LinodeDisk`
        """
        if not isinstance(node, Node):
            raise LinodeExceptionV4("Invalid node instance")

        data = self._paginated_request("/v4/linode/instances/%s/disks" % node.id, "data")

        return [self._to_disk(obj) for obj in data]

    def ex_create_disk(
        self,
        size,
        name,
        node,
        fs_type,
        image=None,
        ex_root_pass=None,
        ex_authorized_keys=None,
        ex_authorized_users=None,
        ex_read_only=False,
    ):
        """
        Adds a new disk to node

        :param    size: Size of disk in megabytes (required)
        :type       size: ``int``

        :param    name: Name of the disk to be created (required)
        :type       name: ``str``

        :param    node: Node to attach disk to (required)
        :type       node: :class:`Node`

        :param    fs_type: The formatted type of this disk. Valid types are:
                             ext3, ext4, swap, raw, initrd
        :type       fs_type: ``str``

        :keyword    image: Image  to deploy the volume from
        :type       image: :class:`NodeImage`

        :keyword    ex_root_pass: root password,required \
                    if an image is provided
        :type       ex_root_pass: ``str``

        :keyword ex_authorized_keys:  a list of SSH keys
        :type    ex_authorized_keys: ``list`` of ``str``

        :keyword ex_authorized_users:  a list of usernames \
                 that will have their SSH keys,\
                 if any, automatically appended \
                 to the root user's ~/.ssh/authorized_keys file.
        :type    ex_authorized_users: ``list`` of ``str``

        :keyword ex_read_only: if true, this disk is read-only
        :type ex_read_only: ``bool``

        :return: LinodeDisk representing the newly-created disk
        :rtype: :class:`LinodeDisk`
        """

        attr = {
            "label": str(name),
            "size": int(size),
            "filesystem": fs_type,
            "read_only": ex_read_only,
        }

        if not isinstance(node, Node):
            raise LinodeExceptionV4("Invalid node instance")

        if fs_type not in self._linode_disk_filesystems:
            raise LinodeExceptionV4("Not valid filesystem type")

        if image is not None:
            if not isinstance(image, NodeImage):
                raise LinodeExceptionV4("Invalid image instance")
            # when an image is set, root pass must be set as well
            if ex_root_pass is None:
                raise LinodeExceptionV4("root_pass is required when " "deploying an image")
            attr["image"] = image.id
            attr["root_pass"] = ex_root_pass

        if ex_authorized_keys is not None:
            attr["authorized_keys"] = list(ex_authorized_keys)

        if ex_authorized_users is not None:
            attr["authorized_users"] = list(ex_authorized_users)

        response = self.connection.request(
            "/v4/linode/instances/%s/disks" % node.id,
            data=json.dumps(attr),
            method="POST",
        ).object
        return self._to_disk(response)

    def ex_destroy_disk(self, node, disk):
        """
        Destroys disk for the given node.

        :param node: The Node the disk is attached to. (required)
        :type    node: :class:`Node`

        :param disk: LinodeDisk to be destroyed (required)
        :type disk: :class:`LinodeDisk`

        :rtype: ``bool``
        """
        if not isinstance(node, Node):
            raise LinodeExceptionV4("Invalid node instance")

        if not isinstance(disk, LinodeDisk):
            raise LinodeExceptionV4("Invalid disk instance")

        if node.state != self.LINODE_STATES["stopped"]:
            raise LinodeExceptionV4("Node needs to be stopped" " before disk is destroyed")

        response = self.connection.request(
            "/v4/linode/instances/{}/disks/{}".format(node.id, disk.id), method="DELETE"
        )
        return response.status == httplib.OK

    def list_volumes(self):
        """Get all volumes of the account
        :rtype: `list` of :class: `StorageVolume`
        """
        data = self._paginated_request("/v4/volumes", "data")

        return [self._to_volume(obj) for obj in data]

    def create_volume(
        self,
        size,
        name,
        location=None,
        snapshot=None,
        node=None,
        tags=None,
    ):
        """Creates a volume and optionally attaches it to a node.

        :param name: The name to be given to volume (required).\
        Must start with an alpha character. \
        May only consist of alphanumeric characters,\
         dashes (-), underscores (_)\
        Cannot have two dashes (--), underscores (__) in a row.

        :type name: `str`

        :param size: Size in gigabytes (required)
        :type size: `int`

        :keyword location: Location to create the node.\
        Required if node is not given.
        :type location: :class:`NodeLocation`

        :keyword volume: Node to attach the volume to
        :type volume: :class:`Node`

        :keyword tags: tags to apply to volume
        :type tags: `list` of `str`

        :rtype: :class: `StorageVolume`
        """

        valid_name = "^[a-zA-Z]((?!--|__)[a-zA-Z0-9-_])+$"
        if not re.match(valid_name, name):
            raise LinodeExceptionV4("Invalid name")

        attr = {
            "label": name,
            "size": int(size),
        }

        if node is not None:
            if not isinstance(node, Node):
                raise LinodeExceptionV4("Invalid node instance")
            attr["linode_id"] = int(node.id)
        else:
            # location is only required if a node is not given
            if location:
                if not isinstance(location, NodeLocation):
                    raise LinodeExceptionV4("Invalid location instance")
                attr["region"] = location.id
            else:
                raise LinodeExceptionV4("Region must be provided " "when node is not")
        if tags is not None:
            attr["tags"] = list(tags)

        response = self.connection.request(
            "/v4/volumes", data=json.dumps(attr), method="POST"
        ).object
        return self._to_volume(response)

    def attach_volume(
        self,
        node,
        volume,
        device=None,
        persist_across_boots=True,
    ):
        """Attaches a volume to a node.
        Volume and node must be located in the same region

        :param node: Node to attach the volume to(required)
        :type node: :class:`Node`

        :param volume: Volume to be attached (required)
        :type volume: :class:`StorageVolume`

        :keyword persist_across_boots: Whether volume should be \
        attached to node across boots
        :type persist_across_boots: `bool`

        :rtype: :class: `StorageVolume`
        """
        if not isinstance(volume, StorageVolume):
            raise LinodeExceptionV4("Invalid volume instance")

        if not isinstance(node, Node):
            raise LinodeExceptionV4("Invalid node instance")

        if volume.extra["linode_id"] is not None:
            raise LinodeExceptionV4("Volume is already attached to a node")

        if node.extra["location"] != volume.extra["location"]:
            raise LinodeExceptionV4("Volume and node " "must be on the same region")

        attr = {"linode_id": int(node.id), "persist_across_boots": persist_across_boots}

        response = self.connection.request(
            "/v4/volumes/%s/attach" % volume.id, data=json.dumps(attr), method="POST"
        ).object
        return self._to_volume(response)

    def detach_volume(self, volume):
        """Detaches a volume from a node.

        :param volume: Volume to be detached (required)
        :type volume: :class:`StorageVolume`

        :rtype: ``bool``
        """
        if not isinstance(volume, StorageVolume):
            raise LinodeExceptionV4("Invalid volume instance")

        if volume.extra["linode_id"] is None:
            raise LinodeExceptionV4("Volume is already detached")

        response = self.connection.request("/v4/volumes/%s/detach" % volume.id, method="POST")
        return response.status == httplib.OK

    def destroy_volume(self, volume):
        """Destroys the volume given.

        :param volume: Volume to be deleted (required)
        :type volume: :class:`StorageVolume`

        :rtype: ``bool``
        """
        if not isinstance(volume, StorageVolume):
            raise LinodeExceptionV4("Invalid volume instance")

        if volume.extra["linode_id"] is not None:
            raise LinodeExceptionV4("Volume must be detached" " before it can be deleted.")
        response = self.connection.request("/v4/volumes/%s" % volume.id, method="DELETE")
        return response.status == httplib.OK

    def ex_resize_volume(self, volume, size):
        """Resizes the volume given.

        :param volume: Volume to be resized
        :type  volume: :class:`StorageVolume`

        :param size: new volume size in gigabytes, must be\
        greater than current size
        :type  size: `int`

        :rtype: ``bool``
        """
        if not isinstance(volume, StorageVolume):
            raise LinodeExceptionV4("Invalid volume instance")

        if volume.size >= size:
            raise LinodeExceptionV4("Volumes can only be resized up")
        attr = {"size": size}

        response = self.connection.request(
            "/v4/volumes/%s/resize" % volume.id, data=json.dumps(attr), method="POST"
        )
        return response.status == httplib.OK

    def ex_clone_volume(self, volume, name):
        """Clones the volume given

        :param volume: Volume to be cloned
        :type  volume: :class:`StorageVolume`

        :param name: new cloned volume name
        :type  name: `str`

        :rtype: :class:`StorageVolume`
        """

        if not isinstance(volume, StorageVolume):
            raise LinodeExceptionV4("Invalid volume instance")

        attr = {"label": name}
        response = self.connection.request(
            "/v4/volumes/%s/clone" % volume.id, data=json.dumps(attr), method="POST"
        ).object

        return self._to_volume(response)

    def ex_get_volume(self, volume_id):
        """
        Return a Volume object based on a volume ID.

        :param  volume_id: Volume's id
        :type   volume_id: ``str``

        :return:  A StorageVolume object for the volume
        :rtype:   :class:`StorageVolume`
        """
        response = self.connection.request("/v4/volumes/%s" % volume_id).object
        return self._to_volume(response)

    def get_image(
        self,
        image_id,
    ):
        """
        Lookup a Linode image

        :param image: The name to image to be looked up (required).\
        :type name: `str`

        :rtype: :class: `NodeImage`
        """
        image = image_id
        response = self.connection.request("/v4/images/%s" % image, method="GET")
        return self._to_image(response.object)

    def create_image(
        self,
        node,
        name,
        description=None,
    ):
        """Creates a private image from a LinodeDisk.
         Images are limited to three per account.

        :param disk: LinodeDisk to create the image from (required)
        :type disk: :class:`LinodeDisk`

        :keyword name: A name for the image.\
        Defaults to the name of the disk \
        it is being created from if not provided
        :type name: `str`

        :keyword description: A description of the image
        :type description: `str`

        :return: The newly created NodeImage
        :rtype: :class:`NodeImage`
        """

        disk = node
        if not isinstance(disk, LinodeDisk):
            raise LinodeExceptionV4("Invalid disk instance")

        attr = {"disk_id": int(disk.id), "label": name, "description": description}

        response = self.connection.request(
            "/v4/images", data=json.dumps(attr), method="POST"
        ).object
        return self._to_image(response)

    def delete_image(
        self,
        node_image,
    ):
        """Deletes a private image

        :param image: NodeImage to delete (required)
        :type image: :class:`NodeImage`

        :rtype: ``bool``
        """
        image = node_image
        if not isinstance(image, NodeImage):
            raise LinodeExceptionV4("Invalid image instance")

        response = self.connection.request("/v4/images/%s" % image.id, method="DELETE")
        return response.status == httplib.OK

    def ex_list_addresses(self):
        """List IP addresses

        :return: LinodeIPAddress list
        :rtype: `list` of :class:`LinodeIPAddress`
        """
        data = self._paginated_request("/v4/networking/ips", "data")

        return [self._to_address(obj) for obj in data]

    def ex_list_node_addresses(self, node):
        """List all IPv4 addresses attached to node

        :param node: Node to list IP addresses
        :type node: :class:`Node`

        :return: LinodeIPAddress list
        :rtype: `list` of :class:`LinodeIPAddress`
        """
        if not isinstance(node, Node):
            raise LinodeExceptionV4("Invalid node instance")

        response = self.connection.request("/v4/linode/instances/%s/ips" % node.id).object
        return self._to_addresses(response)

    def ex_allocate_private_address(self, node, address_type="ipv4"):
        """Allocates a private IPv4 address to node.Only ipv4 is currently supported

        :param node: Node to attach the IP address
        :type node: :class:`Node`

        :keyword address_type: Type of IP address
        :type address_type: `str`

        :return: The newly created LinodeIPAddress
        :rtype: :class:`LinodeIPAddress`
        """
        if not isinstance(node, Node):
            raise LinodeExceptionV4("Invalid node instance")

        # Only ipv4 is currently supported
        if address_type != "ipv4":
            raise LinodeExceptionV4("Address type not supported")
        # Only one private IP address can be allocated
        if len(node.private_ips) >= 1:
            raise LinodeExceptionV4("Nodes can have up to one private IP")

        attr = {"public": False, "type": address_type}

        response = self.connection.request(
            "/v4/linode/instances/%s/ips" % node.id,
            data=json.dumps(attr),
            method="POST",
        ).object
        return self._to_address(response)

    def ex_share_address(self, node, addresses):
        """Shares an IP with another node.This can be used to allow one Linode
         to begin serving requests should another become unresponsive.

        :param node: Node to share the IP addresses with
        :type node: :class:`Node`

        :keyword addresses: List of IP addresses to share
        :type address_type: `list` of :class: `LinodeIPAddress`

        :rtype: ``bool``
        """
        if not isinstance(node, Node):
            raise LinodeExceptionV4("Invalid node instance")

        if not all(isinstance(address, LinodeIPAddress) for address in addresses):
            raise LinodeExceptionV4("Invalid address instance")

        attr = {
            "ips": [address.inet for address in addresses],
            "linode_id": int(node.id),
        }
        response = self.connection.request(
            "/v4/networking/ipv4/share", data=json.dumps(attr), method="POST"
        )
        return response.status == httplib.OK

    def ex_resize_node(self, node, size, allow_auto_disk_resize=False):
        """
        Resizes a node the API Key has read_write permission
        to a different Type.
        The following requirements must be met:
        - The node must not have a pending migration
        - The account cannot have an outstanding balance
        - The node must not have more disk allocation than the new size allows

        :param node: the Linode to resize
        :type node: :class:`Node`

        :param size: the size of the new node
        :type size: :class:`NodeSize`

        :keyword allow_auto_disk_resize: Automatically resize disks \
        when resizing a node.
        :type allow_auto_disk_resize: ``bool``

        :rtype: ``bool``
        """
        if not isinstance(node, Node):
            raise LinodeExceptionV4("Invalid node instance")
        if not isinstance(size, NodeSize):
            raise LinodeExceptionV4("Invalid node size")

        attr = {"type": size.id, "allow_auto_disk_resize": allow_auto_disk_resize}

        response = self.connection.request(
            "/v4/linode/instances/%s/resize" % node.id,
            data=json.dumps(attr),
            method="POST",
        )

        return response.status == httplib.OK

    def ex_rename_node(self, node, name):
        """Renames a node

        :param node: the Linode to resize
        :type node: :class:`Node`

        :param name: the node's new name
        :type name: ``str``

        :return: Changed Node
        :rtype: :class:`Node`
        """
        if not isinstance(node, Node):
            raise LinodeExceptionV4("Invalid node instance")

        attr = {"label": name}

        response = self.connection.request(
            "/v4/linode/instances/%s" % node.id, data=json.dumps(attr), method="PUT"
        ).object

        return self._to_node(response)

    def _to_key_pair(self, data):
        extra = {"id": data["id"]}

        return KeyPair(
            name=data["label"],
            fingerprint=None,
            public_key=data["ssh_key"],
            private_key=None,
            driver=self,
            extra=extra,
        )

    def _to_node(self, data):
        extra = {
            "tags": data["tags"],
            "location": data["region"],
            "ipv6": data["ipv6"],
            "hypervisor": data["hypervisor"],
            "specs": data["specs"],
            "alerts": data["alerts"],
            "backups": data["backups"],
            "watchdog_enabled": data["watchdog_enabled"],
        }

        public_ips = [ip for ip in data["ipv4"] if not is_private_subnet(ip)]
        private_ips = [ip for ip in data["ipv4"] if is_private_subnet(ip)]
        return Node(
            id=data["id"],
            name=data["label"],
            state=self.LINODE_STATES[data["status"]],
            public_ips=public_ips,
            private_ips=private_ips,
            driver=self,
            size=data["type"],
            image=data["image"],
            created_at=self._to_datetime(data["created"]),
            extra=extra,
        )

    def _to_datetime(self, strtime):
        return datetime.strptime(strtime, "%Y-%m-%dT%H:%M:%S")

    def _to_size(self, data):
        extra = {
            "class": data["class"],
            "monthly_price": data["price"]["monthly"],
            "addons": data["addons"],
            "successor": data["successor"],
            "transfer": data["transfer"],
            "vcpus": data["vcpus"],
            "gpus": data["gpus"],
        }
        return NodeSize(
            id=data["id"],
            name=data["label"],
            ram=data["memory"],
            disk=data["disk"],
            bandwidth=data["network_out"],
            price=data["price"]["hourly"],
            driver=self,
            extra=extra,
        )

    def _to_image(self, data):
        extra = {
            "type": data["type"],
            "description": data["description"],
            "created": self._to_datetime(data["created"]),
            "created_by": data["created_by"],
            "is_public": data["is_public"],
            "size": data["size"],
            "eol": data["eol"],
            "vendor": data["vendor"],
        }
        return NodeImage(id=data["id"], name=data["label"], driver=self, extra=extra)

    def _to_location(self, data):
        extra = {
            "status": data["status"],
            "capabilities": data["capabilities"],
            "resolvers": data["resolvers"],
        }
        return NodeLocation(
            id=data["id"],
            name=data["id"],
            country=data["country"].upper(),
            driver=self,
            extra=extra,
        )

    def _to_volume(self, data):
        extra = {
            "created": self._to_datetime(data["created"]),
            "tags": data["tags"],
            "location": data["region"],
            "linode_id": data["linode_id"],
            "linode_label": data["linode_label"],
            "state": self.LINODE_VOLUME_STATES[data["status"]],
            "filesystem_path": data["filesystem_path"],
        }
        return StorageVolume(
            id=str(data["id"]),
            name=data["label"],
            size=data["size"],
            driver=self,
            extra=extra,
        )

    def _to_disk(self, data):
        return LinodeDisk(
            id=data["id"],
            state=self.LINODE_DISK_STATES[data["status"]],
            name=data["label"],
            filesystem=data["filesystem"],
            size=data["size"],
            driver=self,
        )

    def _to_address(self, data):
        extra = {
            "gateway": data["gateway"],
            "subnet_mask": data["subnet_mask"],
            "prefix": data["prefix"],
            "rdns": data["rdns"],
            "node_id": data["linode_id"],
            "region": data["region"],
        }
        return LinodeIPAddress(
            inet=data["address"],
            public=data["public"],
            version=data["type"],
            driver=self,
            extra=extra,
        )

    def _to_addresses(self, data):
        addresses = data["ipv4"]["public"] + data["ipv4"]["private"]
        return [self._to_address(address) for address in addresses]

    def _paginated_request(self, url, obj, params=None):
        """
        Perform multiple calls in order to have a full list of elements when
        the API responses are paginated.

        :param url: API endpoint
        :type url: ``str``

        :param obj: Result object key
        :type obj: ``str``

        :param params: Request parameters
        :type params: ``dict``

        :return: ``list`` of API response objects
        :rtype: ``list``
        """
        objects = []
        params = params if params is not None else {}

        ret = self.connection.request(url, params=params).object

        data = list(ret.get(obj, []))
        current_page = int(ret.get("page", 1))
        num_of_pages = int(ret.get("pages", 1))
        objects.extend(data)
        for page in range(current_page + 1, num_of_pages + 1):
            # add param to request next page
            params["page"] = page
            ret = self.connection.request(url, params=params).object
            data = list(ret.get(obj, []))
            objects.extend(data)
        return objects
