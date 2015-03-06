import json
import re

from libcloud.compute.base import Node, NodeDriver
from libcloud.common.onapp import OnAppConnection

__all__ = [
    "OnAppNodeDriver",
    "OnAppNode",
    "OnAppIpAddress",
    "OnAppNetworkInterface"
]

"""
Define the extra dictionary for specific resources
"""
RESOURCE_EXTRA_ATTRIBUTES_MAP = {
    "node": {
        "add_to_marketplace": {
            "key_name": "add_to_marketplace",
            "transform_func": bool
        },
        "admin_note": {
            "key_name": "admin_note",
            "transform_func": str
        },
        "allow_resize_without_reboot": {
            "key_name": "allow_resize_without_reboot",
            "transform_func": bool
        },
        "allowed_hot_migrate": {
            "key_name": "allowed_hot_migrate",
            "transform_func": bool
        },
        "allowed_swap": {
            "key_name": "allowed_swap",
            "transform_func": bool
        },
        "booted": {
            "key_name": "booted",
            "transform_func": bool
        },
        "built": {
            "key_name": "built",
            "transform_func": bool
        },
        "cpu_priority": {
            "key_name": "cpu_priority",
            "transform_func": int
        },
        "cpu_shares": {
            "key_name": "cpu_shares",
            "transform_func": int
        },
        "cpu_sockets": {
            "key_name": "cpu_sockets",
            "transform_func": int
        },
        "cpu_threads": {
            "key_name": "cpu_threads",
            "transform_func": int
        },
        "cpu_units": {
            "key_name": "cpu_units",
            "transform_func": int
        },
        "cpus": {
            "key_name": "cpus",
            "transform_func": int
        },
        "created_at": {
            "key_name": "created_at",
            "transform_func": str
        },
        "customer_network_id": {
            "key_name": "customer_network_id",
            "transform_func": str
        },
        "deleted_at": {
            "key_name": "deleted_at",
            "transform_func": str
        },
        "edge_server_type": {
            "key_name": "edge_server_type",
            "transform_func": str
        },
        "enable_autoscale": {
            "key_name": "enable_autoscale",
            "transform_func": bool
        },
        "enable_monitis": {
            "key_name": "enable_monitis",
            "transform_func": bool
        },
        "firewall_notrack": {
            "key_name": "firewall_notrack",
            "transform_func": bool
        },
        "hostname": {
            "key_name": "hostname",
            "transform_func": str
        },
        "hypervisor_id": {
            "key_name": "hypervisor_id",
            "transform_func": int
        },
        "id": {
            "key_name": "id",
            "transform_func": int
        },
        "initial_root_password": {
            "key_name": "initial_root_password",
            "transform_func": str
        },
        "initial_root_password_encrypted": {
            "key_name": "initial_root_password_encrypted",
            "transform_func": bool
        },
        "local_remote_access_ip_address": {
            "key_name": "local_remote_access_ip_address",
            "transform_func": str
        },
        "local_remote_access_port": {
            "key_name": "local_remote_access_port",
            "transform_func": int
        },
        "locked": {
            "key_name": "locked",
            "transform_func": bool
        },
        "memory": {
            "key_name": "memory",
            "transform_func": int
        },
        "min_disk_size": {
            "key_name": "min_disk_size",
            "transform_func": int
        },
        "monthly_bandwidth_used": {
            "key_name": "monthly_bandwidth_used",
            "transform_func": int
        },
        "note": {
            "key_name": "note",
            "transform_func": str
        },
        "operating_system": {
            "key_name": "operating_system",
            "transform_func": str
        },
        "operating_system_distro": {
            "key_name": "operating_system_distro",
            "transform_func": str
        },
        "preferred_hvs": {
            "key_name": "preferred_hvs",
            "transform_func": list
        },
        "price_per_hour": {
            "key_name": "price_per_hour",
            "transform_func": float
        },
        "price_per_hour_powered_off": {
            "key_name": "price_per_hour_powered_off",
            "transform_func": float
        },
        "recovery_mode": {
            "key_name": "recovery_mode",
            "transform_func": bool
        },
        "remote_access_password": {
            "key_name": "remote_access_password",
            "transform_func": str
        },
        "service_password": {
            "key_name": "service_password",
            "transform_func": str
        },
        "state": {
            "key_name": "state",
            "transform_func": str
        },
        "storage_server_type": {
            "key_name": "storage_server_type",
            "transform_func": str
        },
        "strict_virtual_machine_id": {
            "key_name": "strict_virtual_machine_id",
            "transform_func": str
        },
        "support_incremental_backups": {
            "key_name": "support_incremental_backups",
            "transform_func": bool
        },
        "suspended": {
            "key_name": "suspended",
            "transform_func": bool
        },
        "template_id": {
            "key_name": "template_id",
            "transform_func": int
        },
        "template_label": {
            "key_name": "template_label",
            "transform_func": str
        },
        "total_disk_size": {
            "key_name": "total_disk_size",
            "transform_func": int
        },
        "updated_at": {
            "key_name": "updated_at",
            "transform_func": str
        },
        "user_id": {
            "key_name": "user_id",
            "transform_func": int
        },
        "vip": {
            "key_name": "vip",
            "transform_func": bool
        },
        "xen_id": {
            "key_name": "xen_id",
            "transform_func": int
        }
    }
}


class OnAppNode(Node):
    """
    Subclass of Node so we can expose our extension methods.
    """

    def __init__(self, identifier, label, ip_addresses, extra, driver):
        """
        @note: This is a non-standard extension API, and only works for
               CloudStack.

        :param      identifier: the VS identifier
        :type       identifier: ``str``

        :param      label: the VS label
        :type       label: ``str``

        :param      ip_addresses: an array of ip addresses with their details
                                  assigned to this VS
        :type       ip_addresses: ``list`` of :class:`OnAppIpAddress`

        :param      extra: a list of extra arguments
        :type       extra: ``dict``

        :param      driver: NodeDriver instance
        :type       driver: class:`OnAppNodeDriver`

        :rtype:     :class:`OnAppNode`
        """
        self.identifier = identifier
        self.label = self.name = label
        self.ip_addresses = ip_addresses
        self.extra = extra

        def is_ip_private(ip_addr):
            # https://en.wikipedia.org/wiki/Private_network
            priv_lo = re.compile("^127\.\d{1,3}\.\d{1,3}\.\d{1,3}$")
            priv_24 = re.compile("^10\.\d{1,3}\.\d{1,3}\.\d{1,3}$")
            priv_20 = re.compile("^192\.168\.\d{1,3}.\d{1,3}$")
            priv_16 = re.compile(
                "^172.(1[6-9]|2[0-9]|3[0-1]).[0-9]{1,3}.[0-9]{1,3}$")

            return any([priv_lo.match(ip_addr), priv_24.match(ip_addr),
                        priv_20.match(ip_addr),
                        priv_16.match(ip_addr)])

        public_ips = []
        private_ips = []
        for ip in self.ip_addresses:
            if is_ip_private(ip.address):
                private_ips.append(ip.address)
            else:
                public_ips.append(ip.address)

        super(OnAppNode, self).__init__(
            id=identifier,
            name=label,
            state=extra['state'],
            public_ips=public_ips,
            private_ips=private_ips,
            driver=driver,
            size=None,
            image=extra['template_id'],
            extra=extra)

    def __repr__(self):
        return "<OnAppNode: identifier=%s, label=%s, ip_address=<%s>" % \
               (self.identifier, self.label, repr(self.ip_addresses[0]))


class OnAppIpAddress(object):
    """
    An IP address
    """

    def __init__(self, address=None, broadcast=None, created_at=None,
                 customer_network_id=None, disallowed_primary=None, free=None,
                 gateway=None, hypervisor_id=None, id=None,
                 ip_address_pool_id=None, netmask=None, network_address=None,
                 network_id=None, pxe=None, updated_at=None, user_id=None):
        """
        :param      address: IP address
        :type       address: ``str``

        :param      broadcast: broadcast address
        :type       broadcast: ``str``

        :param      created_at: the date in the [YYYY][MM][DD]T[hh][mm][ss]Z
                                format
        :type       created_at: ``str``

        :param      customer_network_id: the ID of the customer VLAN the IP
                                         address belongs to
        :type       customer_network_id: ``int``

        :param      disallowed_primary: true if not allowed to be used as
                                        primary (for VS build), otherwise false
        :type       disallowed_primary: ``bool``

        :param      free: true if free, otherwise false
        :type       free: ``bool``

        :param      gateway: gateway address
        :type       gateway: ``str``

        :param      hypervisor_id: the ID of a hypervisor the IP address is
                                   associated with
        :type       hypervisor_id: ``int``

        :param      id: IP address id
        :type       id: ``int``

        :param      ip_address_pool_id: ID of the IP address pool the IP
                                        address is associated with
        :type       ip_address_pool_id: ``int``

        :param      netmask: netmask for the IP address
        :type       netmask: ``str``

        :param      network_address: the address of the network
        :type       network_address: ``str``

        :param      network_id: the ID of the network
        :type       network_id: ``int``

        :param      pxe: true, if this hypervisor address can be used for
                         cloudbooting a hypervisor
        :type       pxe: ``bool``

        :param      updated_at: the date when the network was updated in the
                                    [YYYY][MM][DD]T[hh][mm][ss]Z format
        :type       updated_at: ``str``

        :param      user_id: the ID of the user this IP address is assigned to
        :type       user_id: ``int``

        :rtype:     :class:`OnAppIpAddress`
        """
        self.address = address
        self.broadcast = broadcast
        self.created_at = created_at
        self.customer_network_id = customer_network_id
        self.disallowed_primary = disallowed_primary
        self.free = free
        self.gateway = gateway
        self.hypervisor_id = hypervisor_id
        self.id = id
        self.ip_address_pool_id = ip_address_pool_id
        self.netmask = netmask
        self.network_address = network_address
        self.network_id = network_id
        self.pxe = pxe
        self.updated_at = updated_at
        self.user_id = user_id

    def __repr__(self):
        return "<OnAppIpAddress>: id=%s, address=%s" % (self.id, self.address)


class OnAppNetworkInterface(object):
    """
    OnApp network interface
    """

    def __init__(self, label=None, usage=None, created_at=None, updated_at=None,
                 primary=None, usage_month_rolled_at=None, id=None,
                 mac_address=None, usage_last_reset_at=None,
                 default_firewall_rule=None, rate_limit=None,
                 virtual_machine_id=None, network_join_id=None,
                 identifier=None):
        """
        :param label: network interface name
        :type  label: ``str``

        :param usage:
        :type  usage: ``str``

        :param created_at: the timestamp in the database when this network
                           interface was created
        :type  created_at: ``str``

        :param updated_at: the timestamp in the database when this network
                           interface was updated
        :type  updated_at: ``str``

        :param primary: true if this network interface is primary, otherwise
                        false
        :type  primary: ``bool``

        :param usage_month_rolled_at:

        :param id: the ID of this network interface
        :type  id: ``int``

        :param mac_address: network interface MAC address
        :type  mac_address: ``str``

        :param usage_last_reset_at:
        :type  usage_last_reset_at:

        :param default_firewall_rule:
        :type  default_firewall_rule: ``str``

        :param rate_limit: port speed in Mbps
        :type  rate_limit: ``int``

        :param virtual_machine_id: the ID of a virtual server to which this
                                   network interface is attached
        :type  virtual_machine_id: ``int``

        :param network_join_id: the ID of the network join to which this
                                network interface belongs
        :type  network_join_id: ``int``

        :param identifier: the identifier in the database of this network
                           interface
        :type  identifier: ``str``

        :rtype: :class:`OnAppNetworkInterface`
        """
        self.label = label
        self.usage = usage
        self.created_at = created_at
        self.updated_at = updated_at
        self.primary = primary
        self.usage_month_rolled_at = usage_month_rolled_at
        self.id = id
        self.mac_address = mac_address
        self.usage_last_reset_at = usage_last_reset_at
        self.default_firewall_rule = default_firewall_rule
        self.rate_limit = rate_limit
        self.virtual_machine_id = virtual_machine_id
        self.network_join_id = network_join_id
        self.identifier = identifier

    def __repr__(self):
        return "<OnAppNetworkInterface>: id=%s, label=%s, rate_limit=%s, primary=%s, network_join_id=%s" % \
               (self.id, self.label, self.rate_limit, self.primary,
                self.network_join_id)


class OnAppNodeDriver(NodeDriver):
    """
    Base OnApp node driver.
    """

    connectionCls = OnAppConnection

    def create_node(self, label, memory, cpus, cpu_shares, hostname,
                    template_id, primary_disk_size, swap_disk_size,
                    required_virtual_machine_build=1,
                    required_ip_address_assignment=1, **kwargs):
        """
        Add a VS

        :param  kwargs: All keyword arguments to create a VS
        :type   kwargs: ``dict``

        :rtype: :class:`OnAppNode`
        """
        server_params = dict()
        server_params["label"] = label
        server_params["memory"] = memory
        server_params["cpus"] = cpus
        server_params["cpu_shares"] = cpu_shares
        server_params["hostname"] = hostname
        server_params["template_id"] = template_id
        server_params["primary_disk_size"] = primary_disk_size
        server_params["swap_disk_size"] = swap_disk_size
        server_params[
            "required_virtual_machine_build"] = required_virtual_machine_build
        server_params[
            "required_ip_address_assignment"] = required_ip_address_assignment
        server_params["rate_limit"] = kwargs.get("rate_limit")

        server_params.update(OnAppNodeDriver._create_args_to_params(**kwargs))
        data = json.dumps({"virtual_machine": server_params})

        response = self.connection.request(
            "/virtual_machines.json",
            data=data,
            headers={
                "Content-type": "application/json"},
            method="POST")

        return self._to_node(response.object["virtual_machine"])

    def delete_node(self, identifier, convert_last_backup=0,
                    destroy_all_backups=0):
        """
        Delete a VS

        :param identifier: VS identifier
        :type  identifier: ``str``

        :param convert_last_backup: set 1 to convert the last VS's backup to
                                    template, otherwise set 0
        :type  convert_last_backup: ``int``

        :param destroy_all_backups: set 1 to destroy all existing backups of
                                    this VS, otherwise set 0
        :type  destroy_all_backups: ``int``
        """
        server_params = {
            "convert_last_backup": convert_last_backup,
            "destroy_all_backups": destroy_all_backups
        }
        action = "/virtual_machines/{identifier}.json".format(
            identifier=identifier)

        self.connection.request(action, params=server_params, method="DELETE")

    def list_nodes(self):
        """
        List all VS

        :rtype: ``list`` of :class:`OnAppNode`
        """
        response = self.connection.request("/virtual_machines.json")
        nodes = []
        for vm in response.object:
            nodes.append(self._to_node(vm["virtual_machine"]))
        return nodes

    def add_network_interface(self, identifier, label, network_join_id,
                              rate_limit=None, primary=True):
        """
        Add a new network interface to the node

        :param label: give the label of a network interface you wish to attach
        :type  label: ``str``

        :param network_join_id: set the ID of a physical network used to attach
                                this network interface
        :type  network_join_id: ``int``

        :param rate_limit: set the port speed of a network interface you wish
                           to attach
        :type  rate_limit: ``int``

        :param primary: set True if the interface is primary. Otherwise False.
        :type  primary: ``bool``
        """
        data = {"network_interface": {
            "label": label,
            "network_join_id": network_join_id,
            "primary": primary,
            "rate_limit": rate_limit
        }}

        response = self.connection.request(
            "/virtual_machines/%s/network_interfaces.json" % identifier,
            data=json.dumps(data),
            headers={
                "Content-type": "application/json"},
            method="POST")

        return OnAppNetworkInterface(**response.object["network_interface"])

    def delete_network_interface(self, identifier, network_interface_id):
        """
        Delete a network interface from virtual machine

        :param identifier: VS identifier
        :type  identifier: ``str``

        :param network_interface_id: Network interface id
        :type  identifier: ``int``
        """
        action = "/virtual_machines/{identifier}/network_interfaces/{network_interface_id}.json".format(
            identifier=identifier, network_interface_id=network_interface_id)

        self.connection.request(action, method="DELETE")

    def edit_network_interface(self, identifier, network_interface_id,
                               label=None, primary=None, rate_limit=None):
        """
        :param identifier: VS identifier
        :type  identifier: ``str``

        :param network_interface_id: Network interface id
        :type  identifier: ``int``

        :param label: network interfaces label
        :type  label: ``str``

        :param primary: 1 if this network interface is primary, otherwise 0
        :type  primary: ``bool``

        :param rate_limit: port speed in Mbps
        :type  rate_limit: ``int``
        :return:
        """
        data = {"network_interface": {
            "rate_limit": rate_limit
        }}
        if label is not None:
            data["network_interface"]["label"] = label
        if primary is not None:
            data["network_interface"]["primary"] = primary

        action = "/virtual_machines/{identifier}/network_interfaces/{network_interface_id}.json".format(
            identifier=identifier, network_interface_id=network_interface_id)

        self.connection.request(action,
                                data=json.dumps(data),
                                headers={
                                    "Content-type": "application/json"},
                                method="PUT")

    #
    # Methods to be implemented
    #
    def list_sizes(self, location=None):
        pass

    def list_locations(self):
        pass

    def reboot_node(self, node):
        pass

    def destroy_node(self, node):
        pass

    def list_volumes(self):
        pass

    def list_volume_snapshots(self, volume):
        pass

    def create_volume(self, size, name, location=None, snapshot=None):
        pass

    def create_volume_snapshot(self, volume, name):
        pass

    def attach_volume(self, node, volume, device=None):
        pass

    def detach_volume(self, volume):
        pass

    def destroy_volume(self, volume):
        pass

    def destroy_volume_snapshot(self, snapshot):
        pass

    def list_images(self, location=None):
        pass

    def create_image(self, node, name, description=None):
        pass

    def delete_image(self, node_image):
        pass

    def get_image(self, image_id):
        pass

    def copy_image(self, source_region, node_image, name, description=None):
        pass

    def list_key_pairs(self):
        pass

    def get_key_pair(self, name):
        pass

    def create_key_pair(self, name):
        pass

    def import_key_pair_from_string(self, name, key_material):
        pass

    def delete_key_pair(self, key_pair):
        pass

    #
    # Helper methods
    #

    def _to_node(self, data):
        identifier = data["identifier"]
        label = data["label"]
        ip_addresses = []
        for ip in data["ip_addresses"]:
            ip_addresses.append(OnAppIpAddress(**ip["ip_address"]))

        extra = OnAppNodeDriver._get_extra_dict(
            data, RESOURCE_EXTRA_ATTRIBUTES_MAP["node"]
        )
        return OnAppNode(identifier, label, ip_addresses, extra, self)

    @staticmethod
    def _get_extra_dict(response, mapping):
        """
        Extract attributes from the element based on rules provided in the
        mapping dictionary.

        :param   response: The JSON response to parse the values from.
        :type    response: ``dict``

        :param   mapping: Dictionary with the extra layout
        :type    mapping: ``dict``

        :rtype:  ``dict``
        """
        extra = {}
        for attribute, values in mapping.items():
            transform_func = values["transform_func"]
            value = response.get(values["key_name"], None)

            if value is not None:
                extra[attribute] = transform_func(value)
            else:
                extra[attribute] = None
        return extra

    @staticmethod
    def _create_args_to_params(**kwargs):
        """
        Extract server params from keyword args to create a VS

        :param   kwargs: keyword args
        :return: ``dict``
        """
        server_params = dict()

        cpu_sockets = kwargs.get("cpu_sockets")
        cpu_threads = kwargs.get("cpu_threads")
        enable_autoscale = kwargs.get("enable_autoscale")
        data_store_group_primary_id = kwargs.get("data_store_group_primary_id")
        data_store_group_swap_id = kwargs.get("data_store_group_swap_id")
        hypervisor_group_id = kwargs.get("hypervisor_group_id")
        hypervisor_id = kwargs.get("hypervisor_id")
        initial_root_password = kwargs.get("initial_root_password")
        note = kwargs.get("note")
        primary_disk_min_iops = kwargs.get("primary_disk_min_iops")
        primary_network_id = kwargs.get("primary_network_id")
        primary_network_group_id = kwargs.get("primary_network_group_id")
        recipe_ids = kwargs.get("recipe_ids")
        required_automatic_backup = kwargs.get("required_automatic_backup")
        required_virtual_machine_startup = kwargs.get(
            "required_virtual_machine_startup")
        selected_ip_address_id = kwargs.get("selected_ip_address_id")
        swap_disk_min_iops = kwargs.get("swap_disk_min_iops")
        type_of_format = kwargs.get("type_of_format")
        custom_recipe_variables = kwargs.get("custom_recipe_variables")
        licensing_key = kwargs.get("licensing_key")
        licensing_server_id = kwargs.get("licensing_server_id")
        licensing_type = kwargs.get("licensing_type")

        if cpu_sockets:
            server_params["cpu_sockets"] = cpu_sockets

        if cpu_threads:
            server_params["cpu_threads"] = cpu_threads

        if enable_autoscale:
            server_params["enable_autoscale"] = enable_autoscale

        if data_store_group_primary_id:
            server_params[
                "data_store_group_primary_id"] = data_store_group_primary_id

        if data_store_group_swap_id:
            server_params[
                "data_store_group_swap_id"] = data_store_group_swap_id

        if hypervisor_group_id:
            server_params["hypervisor_group_id"] = hypervisor_group_id

        if hypervisor_id:
            server_params["hypervisor_id"] = hypervisor_id

        if initial_root_password:
            server_params["initial_root_password"] = initial_root_password

        if note:
            server_params["note"] = note

        if primary_disk_min_iops:
            server_params["primary_disk_min_iops"] = primary_disk_min_iops

        if primary_network_id:
            server_params["primary_network_id"] = primary_network_id

        if primary_network_group_id:
            server_params[
                "primary_network_group_id"] = primary_network_group_id

        if recipe_ids:
            server_params["recipe_ids"] = recipe_ids

        if required_automatic_backup:
            server_params[
                "required_automatic_backup"] = required_automatic_backup

        if required_virtual_machine_startup:
            server_params[
                "required_virtual_machine_startup"] = required_virtual_machine_startup

        if selected_ip_address_id:
            server_params["selected_ip_address_id"] = selected_ip_address_id

        if swap_disk_min_iops:
            server_params["swap_disk_min_iops"] = swap_disk_min_iops

        if type_of_format:
            server_params["type_of_format"] = type_of_format

        if custom_recipe_variables:
            server_params["custom_recipe_variables"] = custom_recipe_variables

        if licensing_key:
            server_params["licensing_key"] = licensing_key

        if licensing_server_id:
            server_params["licensing_server_id"] = licensing_server_id

        if licensing_type:
            server_params["licensing_type"] = licensing_type

        return server_params
