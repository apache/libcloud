import json
import socket

from libcloud.compute.base import (Node, NodeDriver, NodeState,
                                   KeyPair, NodeLocation, NodeImage)
from libcloud.common.onapp import OnAppConnection
from libcloud.utils.networking import is_public_subnet
from libcloud.utils.publickey import get_pubkey_ssh2_fingerprint
from libcloud.compute.providers import Provider

__all__ = [
    "OnAppNodeDriver"
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
        "hypervisor_type": {
            "key_name": "hypervisor_type",
            "transform_func": str
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


class OnAppNodeDriver(NodeDriver):
    """
    Base OnApp node driver.
    """

    connectionCls = OnAppConnection
    type = Provider.ONAPP
    name = 'OnApp'
    website = 'http://onapp.com/'

    def __init__(self, key=None, secret=None,
                 host='onapp.com', port=443,
                 verify=True
                 ):
        """
        :param key: username
        :param secret: password
        :param host: onapp host
        :param port: onapp host port
        """
        if not key or not secret:
            raise Exception("Key and secret not specified")

        secure = False if host.startswith('http://') else True
        port = 80 if host.startswith('http://') else 443

        # strip the prefix
        prefixes = ['http://', 'https://']
        for prefix in prefixes:
            if host.startswith(prefix):
                host = host.replace(prefix, '')
        host = host.split('/')[0]

        super(OnAppNodeDriver, self).__init__(key=key,
                                              secret=secret,
                                              host=host,
                                              port=port,
                                              secure=secure)

        self.connection.secure = secure

        self.connection.host = host
        self.connection.port = port

        try:
            socket.setdefaulttimeout(15)
            so = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            so.connect((host, int(port)))
            so.close()
        except:
            raise Exception("Make sure onapp host is accessible and port "
                            "%s is open" % port)
        # do not verify SSL certificate
        if not verify:
            self.connection.connection.ca_cert = False

    def create_node(self, name, ex_memory, ex_cpus, ex_cpu_shares,
                    ex_hostname, ex_template_id, ex_primary_disk_size,
                    ex_swap_disk_size, ex_required_virtual_machine_build=1,
                    ex_required_ip_address_assignment=1,
                    ex_required_virtual_machine_startup=1, **kwargs):
        """
        Add a VS

        :param  kwargs: All keyword arguments to create a VS
        :type   kwargs: ``dict``

        :rtype: :class:`OnAppNode`
        """
        server_params = dict(
            label=name,
            memory=ex_memory,
            cpus=ex_cpus,
            cpu_shares=ex_cpu_shares,
            hostname=ex_hostname,
            template_id=ex_template_id,
            primary_disk_size=ex_primary_disk_size,
            swap_disk_size=ex_swap_disk_size,
            required_virtual_machine_build=ex_required_virtual_machine_build,
            required_ip_address_assignment=ex_required_ip_address_assignment,
            required_virtual_machine_startup=
            ex_required_virtual_machine_startup,
            rate_limit=kwargs.get("rate_limit")
        )

        server_params.update(OnAppNodeDriver._create_args_to_params(**kwargs))
        data = json.dumps({"virtual_machine": server_params})

        response = self.connection.request(
            "/virtual_machines.json",
            data=data,
            headers={
                "Content-type": "application/json"},
            method="POST")

        return self._to_node(response.object["virtual_machine"])

    def create_key_pair(self, user, key):
        """
        Creates an ssh key, given a user id and public key
        """
        action = "/users/{identifier}/ssh_keys.json".format(
            identifier=user)
        data = {"ssh_key": {"key": key}}
        response = self.connection.request(
            action,
            data=json.dumps(data),
            headers={
                "Content-type": "application/json"},
            method="POST")
        return self._to_key(response.object["ssh_key"])

    def ex_start_node(self, node):
        """
        Start a node
        """
        action = "/virtual_machines/{identifier}/startup.json".format(
            identifier=node.id)

        result = self.connection.request(action, method="POST")
        return True if result.status == 201 else False

    def ex_stop_node(self, node):
        """
        Stop a node
        """
        action = "/virtual_machines/{identifier}/shutdown.json".format(
            identifier=node.id)

        result = self.connection.request(action, method="POST")
        return True if result.status == 201 else False

    def ex_suspend_node(self, node):
        """
        Suspend a node
        """
        action = "/virtual_machines/{identifier}/suspend.json".format(
            identifier=node.id)

        result = self.connection.request(action, method="POST")
        return True if result.status == 201 else False

    def ex_resume_node(self, node):
        """
        Resume a node
        To activate a VS again, use the same request as to suspend it
        """
        return self.ex_suspend_node(node)

    def ex_resize_node(self, node, **kwargs):
        """
        Resize a node

        Backend might reboot VM when executing the call
        Valid kwargs: memory, cpus, cpu_shares, cpu_units
        Eg: conn.ex_resize_node(node, memory=1024, cpus=2)

        """
        data = json.dumps({"virtual_machine": kwargs})

        response = self.connection.request(
            "/virtual_machines/{identifier}.json".format(
                identifier=node.id),
            data=data,
            headers={
                "Content-type": "application/json"},
            method="PUT")
        if response.status == 204:
            return True
        else:
            return False

    def reboot_node(self, node):
        """
        Reboot a node
        """
        action = "/virtual_machines/{identifier}/reboot.json".format(
            identifier=node.id)

        result = self.connection.request(action, method="POST")
        return True if result.status == 201 else False

    def destroy_node(self,
                     node,
                     ex_convert_last_backup=0,
                     ex_destroy_all_backups=0):
        """
        Delete a VS

        :param node: OnApp node
        :type  node: :class: `OnAppNode`

        :param convert_last_backup: set 1 to convert the last VS's backup to
                                    template, otherwise set 0
        :type  convert_last_backup: ``int``

        :param destroy_all_backups: set 1 to destroy all existing backups of
                                    this VS, otherwise set 0
        :type  destroy_all_backups: ``int``
        """
        server_params = {
            "convert_last_backup": ex_convert_last_backup,
            "destroy_all_backups": ex_destroy_all_backups
        }
        action = "/virtual_machines/{identifier}.json".format(
            identifier=node.id)

        self.connection.request(action, params=server_params, method="DELETE")
        return True

    def ex_set_ssh_keys(self, node):
        """
        Assign SSH keys of all administrators and a VS owner to a VM
        This will reboot the VM
        """
        action = "/virtual_machines/{identifier}/set_ssh_keys.json".format(
            identifier=node.id)

        result = self.connection.request(action, method="POST")
        return True if result.status == 201 else False

    def list_nodes(self):
        """
        List all VS

        :rtype: ``list`` of :class:`OnAppNode`
        """
        response = self.connection.request("/virtual_machines.json")
        nodes = [self._to_node(vm["virtual_machine"])
                 for vm in response.object]
        return nodes

    def ex_list_key_pairs(self):
        response = self.connection.request("/settings/ssh_keys.json")
        keys = [self._to_key(key['ssh_key']) for key in response.object]
        return keys

    def list_locations(self):
        """
        List locations

        :rtype: ``list`` of :class:`NodeLocation`
        """
        locations = self.connection.request("/settings/location_groups.json")

        node_locations = []
        for location in locations.object:
            l = location['location_group']
            extra = {}
            federated = True if l.get("federated") else False
            extra["federated"] = federated
            extra["created_at"] = l.get("created_at")
            extra["updated_at"] = l.get("updated_at")

            if federated:
                name = "%s (federated) - %s" % (l["city"], l["country"])
            else:
                name = "%s - %s" % (l["city"], l["country"])

            node_location = NodeLocation(id=l["id"],
                                         name=name,
                                         country=l["country"],
                                         extra=extra,
                                         driver=self)
            node_locations.append(node_location)

        return node_locations

    def list_sizes(self):
        return []

    def list_images(self):
        """
        List images
        Contains hypervisor_group_id on extra

        :rtype: ``list`` of :class:`NodeImage`
        """
        response = self.connection.request("/template_store.json")
        images = []
        for template_list in response.object:
            images.extend(self._to_images(template_list))
        # remove duplicates
        d = {}
        for image in images:
            d[image.id] = image
        return d.values()

    def ex_list_networks(self):
        response = self.connection.request("/settings/network_zones.json")
        networks = []
        for network in response.object:
            if network["network_group"]["location_group_id"]:
                networks.append(self._to_network(network["network_group"]))
        return networks

    def ex_list_profile_info(self):
        # list profile info
        response = self.connection.request("/profile.json")
        ret = response.object['user']
        return ret

    def _to_node(self, data):
        identifier = data["identifier"]
        name = data["label"]
        private_ips = []
        public_ips = []
        for ip in data.get("ip_addresses", []):
            address = ip["ip_address"]['address']
            try:
                if is_public_subnet(address):
                    public_ips.append(address)
                else:
                    private_ips.append(address)
            except:
                # IPV6 not supported
                pass
        extra = OnAppNodeDriver._get_extra_dict(
            data, RESOURCE_EXTRA_ATTRIBUTES_MAP["node"]
        )
        state = NodeState.RUNNING if extra.get('booted') else NodeState.STOPPED
        if extra.get('state') == 'failed':
            state = NodeState.ERROR
        elif extra.get('state') == 'building':
            state = NodeState.PENDING

        if extra.get('suspended'):
            state = NodeState.SUSPENDED

        return Node(identifier,
                    name,
                    state,
                    public_ips,
                    private_ips,
                    self,
                    extra=extra)

    def _to_key(self, key):
        pub = key.get('key')
        return KeyPair(name=key.get('id'),
                       public_key=pub,
                       fingerprint=get_pubkey_ssh2_fingerprint(pub),
                       driver=self
                       )

    def _to_images(self, template_list):
        if template_list.get('hypervisor_group_id'):
            h = template_list.get('hypervisor_group_id')
            images = [self._to_image(image, hypervisor_group_id=h)
                      for image in template_list['relations']]
        else:
            image_objects = template_list['relations']
            # get images out of depth 0,1,2
            for child in template_list['children']:
                if child['relations']:
                    image_objects.extend(child['relations'])
                if child['children']:
                    for c in child['children']:
                        image_objects.extend(c['relations'])
            images = [self._to_image(image) for image in image_objects]

        return images

    def _to_image(self, image, hypervisor_group_id=None):
        extra = {}
        if hypervisor_group_id:
            extra['hypervisor_group_id'] = hypervisor_group_id
        extra['min_disk_size'] = \
            image['image_template'].get('min_disk_size')
        extra['min_memory_size'] = \
            image['image_template'].get('min_memory_size')
        extra['virtualization'] = \
            image['image_template'].get('virtualization')
        image_name = image['image_template'].get('label')
        image_id = image['image_template'].get('id')
        return NodeImage(id=image_id,
                         name=image_name,
                         driver=self,
                         extra=extra)

    def _to_network(self, network):
        extra = {}
        extra["location_group_id"] = network["location_group_id"]
        return Network(id=network["id"],
                       name=network["label"],
                       cidr_block=None,
                       extra=extra
                       )

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
            value = response.get(values["key_name"])

            extra[attribute] = transform_func(value) if value else None
        return extra

    @staticmethod
    def _create_args_to_params(**kwargs):
        """
        Extract server params from keyword args to create a VS

        :param   kwargs: keyword args
        :return: ``dict``
        """
        params = [
            "ex_cpu_sockets",
            "ex_cpu_threads",
            "ex_enable_autoscale",
            "ex_data_store_group_primary_id",
            "ex_data_store_group_swap_id",
            "ex_hypervisor_group_id",
            "ex_hypervisor_id",
            "ex_initial_root_password",
            "ex_note",
            "ex_primary_disk_min_iops",
            "ex_primary_network_id",
            "ex_primary_network_group_id",
            "ex_recipe_ids",
            "ex_required_automatic_backup",
            "ex_selected_ip_address_id",
            "ex_swap_disk_min_iops",
            "ex_type_of_format",
            "ex_custom_recipe_variables",
            "ex_licensing_key",
            "ex_licensing_server_id",
            "ex_licensing_type",
        ]
        server_params = {}

        for p in params:
            value = kwargs.get(p)
            if value:
                server_params[p[3:]] = value
        return server_params


class Network(object):
    def __init__(self, id, name, cidr_block, extra=None):
        self.id = id
        self.name = name
        self.cidr_block = cidr_block
        self.extra = extra or {}

    def __repr__(self):
        return (('<Network: id=%s, name=%s')
                % (self.id, self.name))
