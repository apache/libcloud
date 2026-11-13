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
Upcloud node driver
"""

import json
import base64

from libcloud.utils.py3 import b, httplib
from libcloud.common.base import JsonResponse, ConnectionUserAndKey
from libcloud.common.types import InvalidCredsError
from libcloud.compute.base import (
    Node,
    NodeSize,
    NodeImage,
    NodeState,
    NodeDriver,
    NodeLocation,
    StorageVolume,
)
from libcloud.compute.types import Provider, StorageVolumeState
from libcloud.common.upcloud import (
    PlanPrice,
    UpcloudNodeDestroyer,
    UpcloudNodeOperations,
    UpcloudCreateNodeRequestBody,
)


class UpcloudResponse(JsonResponse):
    """
    Response class for UpcloudDriver
    """

    def success(self):
        if self.status == httplib.NO_CONTENT:
            return True
        return super().success()

    def parse_error(self):
        data = self.parse_body()
        error = data.get("error", data)
        if self.status == httplib.UNAUTHORIZED:
            raise InvalidCredsError(value=error["error_message"])

        if isinstance(error, dict):
            message = error.get("error_message")
            code = error.get("error_code")
            if message and code:
                return "{}: {}".format(code, message)
            if message:
                return message

        return json.dumps(data)


class UpcloudConnection(ConnectionUserAndKey):
    """
    Connection class for UpcloudDriver
    """

    host = "api.upcloud.com"
    responseCls = UpcloudResponse

    def __init__(self, user_id, key, *args, **kwargs):
        self.token = kwargs.pop("token", None)
        super().__init__(user_id, key, *args, **kwargs)

    def add_default_headers(self, headers):
        """Adds headers that are needed for all requests"""
        if self.token:
            headers["Authorization"] = "Bearer {}".format(self.token)
        else:
            headers["Authorization"] = self._basic_auth()
        headers["Accept"] = "application/json"
        headers["Content-Type"] = "application/json"
        return headers

    def _basic_auth(self):
        """Constructs basic auth header content string"""
        credentials = b("{}:{}".format(self.user_id, self.key))
        credentials = base64.b64encode(credentials)
        return "Basic {}".format(credentials.decode("ascii"))


class UpcloudDriver(NodeDriver):
    """
    Upcloud node driver

    :keyword    username: Username required for basic authentication
    :type       username: ``str``

    :keyword    password: Password required for basic authentication
    :type       password: ``str``

    :keyword    token: Bearer API token used instead of username/password
    :type       token: ``str``
    """

    type = Provider.UPCLOUD
    name = "Upcloud"
    website = "https://www.upcloud.com"
    connectionCls = UpcloudConnection
    features = {"create_node": ["ssh_key", "generates_password"]}

    NODE_STATE_MAP = {
        "started": NodeState.RUNNING,
        "stopped": NodeState.STOPPED,
        "maintenance": NodeState.RECONFIGURING,
        "error": NodeState.ERROR,
    }

    STORAGE_VOLUME_STATE_MAP = {
        "online": StorageVolumeState.AVAILABLE,
        "maintenance": StorageVolumeState.UPDATING,
        "cloning": StorageVolumeState.UPDATING,
        "backuping": StorageVolumeState.BACKUP,
        "syncing": StorageVolumeState.MIGRATING,
        "error": StorageVolumeState.ERROR,
    }

    def __init__(self, username=None, password=None, token=None, **kwargs):
        if token is None and (username is None or password is None):
            raise ValueError("Must provide either username/password or token.")

        self.token = token
        super().__init__(key=username or "", secret=password or "", **kwargs)

    def _ex_connection_class_kwargs(self):
        kwargs = super()._ex_connection_class_kwargs()
        if self.token:
            kwargs["token"] = self.token
        return kwargs

    def list_locations(self):
        """
        List available locations for deployment

        :rtype: ``list`` of :class:`NodeLocation`
        """
        response = self.connection.request("1.3/zone")
        return self._to_node_locations(response.object["zones"]["zone"])

    def list_sizes(self, location=None):
        """
        List available plans

        :param location: Location of the deployment. Price depends on
        location. lf location is not given or price not found for
        location, price will be None (optional)
        :type location: :class:`.NodeLocation`

        :rtype: ``list`` of :class:`NodeSize`
        """
        prices_response = self.connection.request("1.3/price")
        response = self.connection.request("1.3/plan")
        return self._to_node_sizes(
            response.object["plans"]["plan"],
            prices_response.object["prices"]["zone"],
            location,
        )

    def list_images(
        self,
        location=None,
    ):
        """
        List available distributions.

        :rtype: ``list`` of :class:`NodeImage`
        """
        response = self.connection.request("1.3/storage/template")
        obj = response.object
        response = self.connection.request("1.3/storage/cdrom")
        storage = response.object["storages"]["storage"]
        obj["storages"]["storage"].extend(storage)
        return self._to_node_images(obj["storages"]["storage"])

    def create_node(
        self,
        name,
        size,
        image,
        location=None,
        auth=None,
        ex_hostname="localhost",
        ex_username="root",
        ex_storage_devices=None,
        ex_metadata=None,
    ):
        """
        Creates instance to upcloud.

        If auth is not given then password will be generated.

        :param name:   String with a name for this new node (required)
        :type name:   ``str``

        :param size:   The size of resources allocated to this node.
                            (required)
        :type size:   :class:`.NodeSize`

        :param image:  OS Image to boot on node. (required)
        :type image:  :class:`.NodeImage`

        :param location: Which data center to create a node in. If empty,
                              undefined behavior will be selected. (optional)
        :type location: :class:`.NodeLocation`

        :param auth:   Initial authentication information for the node
                            (optional)
        :type auth:   :class:`.NodeAuthSSHKey`

        :param ex_hostname: Hostname. Default is 'localhost'. (optional)
        :type ex_hostname: ``str``

        :param ex_username: User's username, which is created.
                            Default is 'root'. (optional)
        :type ex_username: ``str``

        :param ex_storage_devices: Additional UpCloud storage_device
                                   dictionaries to include in the server
                                   creation request. For example, an
                                   ``attach`` action can attach an existing
                                   storage and a ``create`` action can create
                                   an extra data disk. (optional)
        :type ex_storage_devices: ``list`` of ``dict``

        :param ex_metadata: Enable or disable the UpCloud metadata service,
                            ``"yes"`` or ``"no"``. Cloud-init templates
                            require this to be enabled. (optional)
        :type ex_metadata: ``str``

        :return: The newly created node.
        :rtype: :class:`.Node`
        """
        body = UpcloudCreateNodeRequestBody(
            name=name,
            size=size,
            image=image,
            location=location,
            auth=auth,
            ex_hostname=ex_hostname,
            ex_username=ex_username,
            ex_storage_devices=ex_storage_devices,
            ex_metadata=ex_metadata,
        )
        response = self.connection.request("1.3/server", method="POST", data=body.to_json())
        server = response.object["server"]
        # Upcloud server's are in maintenance state when going
        # from state to other, it is safe to assume STARTING state
        return self._to_node(server, state=NodeState.STARTING)

    def list_volumes(self):
        """
        List normal storage volumes.

        :rtype: ``list`` of :class:`StorageVolume`
        """
        response = self.connection.request("1.3/storage/normal")
        return self._to_volumes(response.object["storages"]["storage"])

    def create_volume(
        self,
        size,
        name,
        location=None,
        snapshot=None,
        ex_tier="maxiops",
        ex_backup_rule=None,
    ):
        """
        Create a new storage volume.

        :param size: Size of volume in gigabytes. (required)
        :type size: ``int``

        :param name: Name of the volume to be created. (required)
        :type name: ``str``

        :param location: Which data center to create a volume in. (required)
        :type location: :class:`.NodeLocation`

        :param ex_tier: UpCloud storage tier: ``maxiops`` or ``hdd``.
                        Default is ``maxiops``. (optional)
        :type ex_tier: ``str``

        :param ex_backup_rule: Backup rule block for automatic backups.
                               (optional)
        :type ex_backup_rule: ``dict``

        :rtype: :class:`StorageVolume`
        """
        if location is None:
            raise ValueError("Must provide `location` value.")

        if snapshot is not None:
            raise NotImplementedError("Creating a volume from snapshot is not supported.")

        storage = {
            "size": size,
            "title": name,
            "zone": location.id,
            "tier": ex_tier,
        }
        if ex_backup_rule is not None:
            storage["backup_rule"] = ex_backup_rule

        response = self.connection.request(
            "1.3/storage",
            method="POST",
            data=json.dumps({"storage": storage}),
        )
        return self._to_volume(response.object["storage"])

    def attach_volume(
        self,
        node,
        volume,
        device=None,
        ex_type="disk",
        ex_boot_disk=False,
    ):
        """
        Attach a storage volume to a node.

        :param node: Node to attach volume to.
        :type node: :class:`Node`

        :param volume: Volume to attach.
        :type volume: :class:`StorageVolume`

        :param device: UpCloud device address or bus, for example
                       ``virtio``, ``scsi`` or ``scsi:0:0``. (optional)
        :type device: ``str``

        :param ex_type: Attached device type, ``disk`` or ``cdrom``.
                        Default is ``disk``. (optional)
        :type ex_type: ``str``

        :param ex_boot_disk: Whether the storage should be a boot disk.
                             Default is False. (optional)
        :type ex_boot_disk: ``bool``

        :rtype: ``bool``
        """
        storage_device = {
            "type": ex_type,
            "storage": volume.id,
            "boot_disk": "1" if ex_boot_disk else "0",
        }
        if device is not None:
            storage_device["address"] = device

        self.connection.request(
            "1.3/server/{}/storage/attach".format(node.id),
            method="POST",
            data=json.dumps({"storage_device": storage_device}),
        )
        return True

    def detach_volume(self, volume, ex_node=None, ex_address=None):
        """
        Detach a storage volume from its server.

        :param volume: Volume to detach.
        :type volume: :class:`StorageVolume`

        :param ex_node: Node where the volume is attached. Required by the
                        UpCloud 1.3 detach endpoint.
        :type ex_node: :class:`Node`

        :param ex_address: Device address to detach, for example
                           ``scsi:0:0``. Required by the UpCloud 1.3 detach
                           endpoint.
        :type ex_address: ``str``

        :rtype: ``bool``
        """
        if ex_node is None or ex_address is None:
            raise ValueError(
                "UpCloud API 1.3 requires `ex_node` and `ex_address` " "when detaching a volume."
            )

        self.connection.request(
            "1.3/server/{}/storage/detach".format(ex_node.id),
            method="POST",
            data=json.dumps({"storage_device": {"address": ex_address}}),
        )
        return True

    def destroy_volume(self, volume):
        """
        Destroy a storage volume.

        :param volume: Volume to destroy.
        :type volume: :class:`StorageVolume`

        :rtype: ``bool``
        """
        self.connection.request("1.3/storage/{}".format(volume.id), method="DELETE")
        return True

    def ex_list_firewall_rules(self, node):
        """
        List firewall rules for a node.

        :param node: Node whose firewall rules are listed.
        :type node: :class:`Node`

        :rtype: ``list`` of ``dict``
        """
        response = self.connection.request("1.3/server/{}/firewall_rule".format(node.id))
        rules = response.object["firewall_rules"].get("firewall_rule", [])
        if isinstance(rules, dict):
            return [rules]
        return rules

    def ex_get_firewall_rule(self, node, position):
        """
        Get firewall rule details by rule position.

        :param node: Node whose firewall rule is fetched.
        :type node: :class:`Node`

        :param position: Firewall rule position.
        :type position: ``str`` or ``int``

        :rtype: ``dict``
        """
        response = self.connection.request(
            "1.3/server/{}/firewall_rule/{}".format(node.id, position)
        )
        return response.object["firewall_rule"]

    def ex_create_firewall_rule(self, node, rule):
        """
        Create a firewall rule for a node.

        :param node: Node where the firewall rule is created.
        :type node: :class:`Node`

        :param rule: UpCloud firewall rule dictionary.
        :type rule: ``dict``

        :rtype: ``dict``
        """
        response = self.connection.request(
            "1.3/server/{}/firewall_rule".format(node.id),
            method="POST",
            data=json.dumps({"firewall_rule": rule}),
        )
        return response.object["firewall_rule"]

    def ex_create_firewall_rules(self, node, rules):
        """
        Replace firewall rules for a node.

        :param node: Node whose firewall rules are replaced.
        :type node: :class:`Node`

        :param rules: UpCloud firewall rule dictionaries.
        :type rules: ``list`` of ``dict``

        :rtype: ``bool``
        """
        self.connection.request(
            "1.3/server/{}/firewall_rule".format(node.id),
            method="PUT",
            data=json.dumps({"firewall_rules": {"firewall_rule": rules}}),
        )
        return True

    def ex_delete_firewall_rule(self, node, position):
        """
        Delete a firewall rule by rule position.

        :param node: Node whose firewall rule is deleted.
        :type node: :class:`Node`

        :param position: Firewall rule position.
        :type position: ``str`` or ``int``

        :rtype: ``bool``
        """
        self.connection.request(
            "1.3/server/{}/firewall_rule/{}".format(node.id, position),
            method="DELETE",
        )
        return True

    def list_nodes(self):
        """
        List nodes

        :return: List of node objects
        :rtype: ``list`` of :class:`Node`
        """
        servers = []
        for nid in self._node_ids():
            response = self.connection.request("1.3/server/{}".format(nid))
            servers.append(response.object["server"])
        return self._to_nodes(servers)

    def reboot_node(self, node):
        """
        Reboot the given node

        :param      node: the node to reboot
        :type       node: :class:`Node`

        :rtype: ``bool``
        """
        body = {"restart_server": {"stop_type": "hard"}}
        self.connection.request(
            "1.3/server/{}/restart".format(node.id),
            method="POST",
            data=json.dumps(body),
        )
        return True

    def start_node(self, node):
        """
        Start the given node.

        :param node: the node to start
        :type node: :class:`Node`

        :rtype: ``bool``
        """
        self.connection.request("1.3/server/{}/start".format(node.id), method="POST")
        return True

    def stop_node(self, node, ex_stop_type="hard", ex_timeout=None):
        """
        Stop the given node.

        :param node: the node to stop
        :type node: :class:`Node`

        :param ex_stop_type: Stop type, ``hard`` or ``soft``. Default is
                             ``hard`` to match the destroy helper behavior.
                             (optional)
        :type ex_stop_type: ``str``

        :param ex_timeout: Stop timeout in seconds when using a soft stop.
                           (optional)
        :type ex_timeout: ``int``

        :rtype: ``bool``
        """
        stop_server = {"stop_type": ex_stop_type}
        if ex_timeout is not None:
            stop_server["timeout"] = ex_timeout

        self.connection.request(
            "1.3/server/{}/stop".format(node.id),
            method="POST",
            data=json.dumps({"stop_server": stop_server}),
        )
        return True

    def destroy_node(self, node):
        """
        Destroy the given node

        The disk resources, attached to node,  will not be removed.

        :param       node: the node to destroy
        :type        node: :class:`Node`

        :rtype: ``bool``
        """

        operations = UpcloudNodeOperations(self.connection)
        destroyer = UpcloudNodeDestroyer(operations)
        return destroyer.destroy_node(node.id)

    def _node_ids(self):
        """
        Returns list of server uids currently on upcloud
        """
        response = self.connection.request("1.3/server")
        servers = response.object["servers"]["server"]
        return [server["uuid"] for server in servers]

    def _to_nodes(self, servers):
        return [self._to_node(server) for server in servers]

    def _to_node(self, server, state=None):
        ip_addresses = server["ip_addresses"]["ip_address"]
        public_ips = [ip["address"] for ip in ip_addresses if ip["access"] == "public"]
        private_ips = [ip["address"] for ip in ip_addresses if ip["access"] == "private"]

        extra = self._copy_dict_if_present(("password", "vnc_password"), server)
        return Node(
            id=server["uuid"],
            name=server["title"],
            state=state or self.NODE_STATE_MAP[server["state"]],
            public_ips=public_ips,
            private_ips=private_ips,
            driver=self,
            extra=extra,
        )

    def _to_node_locations(self, zones):
        return [self._construct_node_location(zone) for zone in zones]

    def _construct_node_location(self, zone):
        return NodeLocation(
            id=zone["id"],
            name=zone["description"],
            country=self._parse_country(zone["id"]),
            driver=self,
        )

    def _parse_country(self, zone_id):
        """Parses the country information out of zone_id.
        Zone_id format [country]_[city][number], like fi_hel1"""
        return zone_id.split("-")[0].upper()

    def _to_node_sizes(self, plans, prices, location):
        plan_price = PlanPrice(prices)
        return [self._to_node_size(plan, plan_price, location) for plan in plans]

    def _to_node_size(self, plan, plan_price, location):
        extra = self._copy_dict(("core_number", "storage_tier"), plan)
        return NodeSize(
            id=plan["name"],
            name=plan["name"],
            ram=plan["memory_amount"],
            disk=plan["storage_size"],
            bandwidth=plan["public_traffic_out"],
            price=plan_price.get_price(plan["name"], location),
            driver=self,
            extra=extra,
        )

    def _to_node_images(self, images):
        return [self._construct_node_image(image) for image in images]

    def _construct_node_image(self, image):
        extra = self._copy_dict(("access", "license", "size", "state", "type"), image)
        return NodeImage(id=image["uuid"], name=image["title"], driver=self, extra=extra)

    def _to_volumes(self, volumes):
        return [self._to_volume(volume) for volume in volumes]

    def _to_volume(self, volume):
        extra_keys = (
            "access",
            "backup_rule",
            "backups",
            "encrypted",
            "labels",
            "license",
            "origin",
            "part_of_plan",
            "progress",
            "servers",
            "tier",
            "type",
            "zone",
        )
        extra = {}
        for key in extra_keys:
            if key in volume:
                extra[key] = volume[key]

        return StorageVolume(
            id=volume["uuid"],
            name=volume["title"],
            size=int(volume["size"]),
            driver=self,
            state=self.STORAGE_VOLUME_STATE_MAP.get(volume["state"], StorageVolumeState.UNKNOWN),
            extra=extra,
        )

    def _copy_dict(self, keys, d):
        extra = {}
        for key in keys:
            extra[key] = d[key]
        return extra

    def _copy_dict_if_present(self, keys, d):
        extra = {}
        for key in keys:
            if key in d:
                extra[key] = d[key]
        return extra
