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
from __future__ import with_statement

import re
import os
import shlex
import socket
import time
import platform
import subprocess
import mimetypes
import paramiko
import atexit
import logging
import netaddr
import random
import hashlib

from tempfile import NamedTemporaryFile
from os.path import join as pjoin
from collections import defaultdict

try:
    from lxml import etree as ET
except ImportError:
    from xml.etree import ElementTree as ET

from libcloud.compute.base import NodeDriver, Node, NodeImage, NodeSize
from libcloud.compute.base import NodeState
from libcloud.compute.types import Provider
from libcloud.utils.networking import is_public_subnet
from libcloud.utils.networking import is_valid_ip_address
from libcloud.utils.py3 import basestring

try:
    import libvirt
    have_libvirt = True
except ImportError:
    raise RuntimeError('Missing "libvirt" dependency. You can install it using '
                       'pip. For example ./bin/pip install libvirt-python')


log = logging.getLogger('libcloud.compute.drivers.libvirt')


ALLOW_LIBVIRT_LOCALHOST = False
IMAGES_LOCATION = "/var/lib/libvirt/images"

# directory to store cloudinit related files etc
LIBCLOUD_DIRECTORY = "/var/lib/libvirt/libcloud"

# disk image types to create VMs from
DISK_IMAGE_TYPES = ('.img', '.raw', '.qcow', '.qcow2')


class LibvirtNodeDriver(NodeDriver):
    """
    Libvirt (http://libvirt.org/) node driver.

    To enable debug mode, set LIBVIR_DEBUG environment variable.
    """

    type = Provider.LIBVIRT
    name = 'Libvirt'
    website = 'http://libvirt.org/'
    _uri = None

    NODE_STATE_MAP = {
        0: NodeState.TERMINATED,  # no state
        1: NodeState.RUNNING,  # domain is running
        2: NodeState.PENDING,  # domain is blocked on resource
        3: NodeState.SUSPENDED,  # domain is paused by user
        4: NodeState.TERMINATED,  # domain is being shut down
        5: NodeState.TERMINATED,  # domain is shut off
        6: NodeState.UNKNOWN,  # domain is crashed
        7: NodeState.UNKNOWN,  # domain is suspended by guest power management
    }

    def __init__(self, host, user='root', ssh_key=None,
                 ssh_port=22, tcp_port=5000, hypervisor=None):
        """
        Supports three ways to connect: local system, qemu+tcp, qemu+ssh
        :param host: IP address or hostname to connect to (usually the
        address of the KVM hypervisor)
        :param hypervisor: the IP address of the KVM hypervisor. Useful in case
        `host` has been substituted by a middleware
        :param user: the username to connect to the KVM hypervisor as
        :param ssh_key: a filename with the private key
        :param ssh_port: the SSH port to connect to when qemu+ssh is chosen
        :param tcp_port: the TCP port to connect to in case of qemu+tcp
        :return:
        """
        self._ssh_conn = None

        self.temp_key = None
        self.secret = None
        if host in ['localhost', '127.0.0.1', '0.0.0.0']:
            # local connection
            if ALLOW_LIBVIRT_LOCALHOST:
                uri = 'qemu:///system'
            else:
                raise Exception("In order to connect to local libvirt enable "
                                "ALLOW_LIBVIRT_LOCALHOST variable")
        else:
            if ssh_key:
                # Ensure ssh_key ends with newline
                # Prevents `invalid format` libvirtError
                if ssh_key[-1] != '\n':
                    ssh_key += '\n'
                # if ssh key is string create temp file
                if not os.path.isfile(ssh_key):
                    key_temp_file = NamedTemporaryFile(delete=False)
                    key_temp_file.write(ssh_key.encode())
                    key_temp_file.close()
                    self.secret = key_temp_file.name
                    self.temp_key = self.secret
                else:
                    self.secret = ssh_key
                # ssh connection
                # initially attempt to connect to host/port and raise
                # exception on failure
                try:
                    socket.setdefaulttimeout(15)
                    so = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    so.connect((host, ssh_port))
                    so.close()
                except:
                    raise Exception("Make sure host is accessible and ssh port is open")

                uri = 'qemu+ssh://%s@%s:%s/system?keyfile=%s&no_tty=1&no_verify=1' % (user, host, ssh_port, self.secret)
            else:
                # tcp connection
                try:
                    socket.setdefaulttimeout(15)
                    so = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    so.connect((host, tcp_port))
                    so.close()
                except:
                    raise Exception("If you don't specify an ssh key, libvirt "
                                    "will try to connect to port 5000 through "
                                    "qemu+tcp")

                uri = 'qemu+tcp://%s:%s/system' % (host, tcp_port)

        self._uri = uri
        self.host = host
        self.hypervisor = hypervisor if hypervisor else host
        self.ssh_port = ssh_port
        self.key = user

        try:
            self.connection = libvirt.open(uri)
        except Exception as exc:
            if 'Could not resolve' in str(exc):
                raise Exception("Make sure hostname is accessible")
            if 'Connection refused' in str(exc):
                raise Exception("Make sure hostname is accessible and libvirt "
                                "is running")
            if 'Permission denied' in str(exc):
                raise Exception("Make sure ssh key and username are valid")
            if 'End of file while reading data' in str(exc):
                raise Exception("Make sure libvirt is running and user %s is "
                                "authorised to connect" % user)
            raise Exception("Connection error")

            atexit.register(self.disconnect)

    def list_nodes(self, show_hypervisor=True):
        # active domains
        domain_ids = self.connection.listDomainsID()
        domains = [self.connection.lookupByID(id) for id in domain_ids]
        # non active domains
        inactive_domains = map(self.connection.lookupByName,
                               self.connection.listDefinedDomains())
        domains.extend(inactive_domains)

        # get the arp table of the hypervisor. Try to connect with provided
        # ssh key and paramiko

        # libvirt does not know the ip addresses of guest vms. One way to
        # get this info is by getting the arp table and providing it to the
        # libvirt connection. Then we can check what ip address each MAC
        # address has
        self.arp_table = {}
        cmd = "arp -an"
        self.arp_table = self._parse_arp_table(self._run_command(cmd).get('output'))

        nodes = [self._to_node(domain) for domain in domains]

        return nodes

    def _to_node(self, domain):
        state, max_mem, memory, vcpu_count, used_cpu_time = domain.info()
        state = self.NODE_STATE_MAP.get(state, NodeState.UNKNOWN)

        size_extra = {'cpus': vcpu_count}
        id_to_hash = str(memory) + str(vcpu_count)
        size_id = hashlib.md5(id_to_hash.encode("utf-8")).hexdigest()
        size_name = domain.name() + "-size"
        size = NodeSize(id=size_id, name=size_name, ram=memory / 1000, disk=0,
                        bandwidth=0, price=0, driver=self, extra=size_extra)

        public_ips, private_ips = [], []

        ip_addresses = self._get_ip_addresses_for_domain(domain)

        for ip_address in ip_addresses:
            if is_public_subnet(ip_address):
                public_ips.append(ip_address)
            else:
                private_ips.append(ip_address)

        # TODO This fails in most cases adding a considerable overhead due to
        # socket timeout. It should be implemented in a more efficient way.
        # try:
        #     # this will work only if real name is given to a guest VM's name.
        #     public_ip = socket.gethostbyname(domain.name())
        # except:
        #     public_ip = ''
        # if public_ip and public_ip not in ip_addresses:
        #     # avoid duplicate insertion in public ips
        #     public_ips.append(public_ip)

        try:
            xml_description = domain.XMLDesc()
        except:
            xml_description = ''

        from xml.dom import minidom
        xml = minidom.parseString(xml_description)
        diskTypes = xml.getElementsByTagName('disk')
        diskSizes = []
        for diskType in diskTypes:
            diskNodes = diskType.childNodes
            for diskNode in diskNodes:
                if diskNode.attributes and diskNode.getAttribute('file'):
                    try:
                        diskSizes.append(
                            domain.blockInfo(diskNode.getAttribute('file'))[0]
                        )
                    except Exception as exc:
                        log.error('Failed to fetch size for %s: %r' % (
                            diskNode.getAttribute('file'), exc))
                        continue
        size.disk = sum(diskSizes) / (1024 * 1024 * 1024)
        extra = {'uuid': domain.UUIDString(), 'os_type': domain.OSType(),
                 'types': self.connection.getType(),
                 'active': bool(domain.isActive()),
                 'hypervisor': self.host,
                 'memory': '%s MB' % str(memory / 1024), 'processors': vcpu_count,
                 'used_cpu_time': used_cpu_time, 'xml_description': xml_description}
        node = Node(id=domain.UUIDString(), name=domain.name(), state=state,
                    public_ips=public_ips, private_ips=private_ips, size=size,
                    driver=self, extra=extra)
        node._uuid = domain.UUIDString()  # we want to use a custom UUID
        return node

    def _get_ip_addresses_for_domain(self, domain):
        """
        Retrieve IP addresses for the provided domain.

        Note: This functionality is currently only supported on Linux and
        only works if this code is run on the same machine as the VMs run
        on.

        :return: IP addresses for the provided domain.
        :rtype: ``list``
        """
        result = []
        if platform.system() != 'Linux':
            # Only Linux is supported atm
            return result

        mac_addresses = self._get_mac_addresses_for_domain(domain=domain)

        for mac_address in mac_addresses:
            if mac_address not in self.arp_table:
                self._update_arp_table_with_mac(domain, mac_address)
            if mac_address not in self.arp_table:
                continue

            ip_addresses = self.arp_table[mac_address]
            result.extend(ip_addresses)

        return result

    def _update_arp_table_with_mac(self, domain, mac_address):
        """Update the ARP table given the MAC address of a domain.

        This method attempts to update `self.arp_table` as well as the KVM
        host's ARP table given a MAC address of an existing domain.

        This method is invoked if there's previously no entry in the host's
        ARP table regarding `mac_address`. In order to bring the ARP table
        up-to-date, the interface corresponding to `mac_address` is firstly
        found. Then an arp-scan is run on that interface to discover the
        available MAC-IP address combinations. The arp-scan may return MAC-
        IP address combinations for MAC addresses other than `mac_address`,
        which will be used to also proactively update the host's ARP table.
        This way, this method may not have to be called consistently, but
        rather for MAC addresses previously unseen.

        """
        # If the domain is inactive, return immediately, since no IP will be
        # assigned to it anyway.
        if not bool(domain.isActive()):
            return

        # Find the interface on the KVM host with which the `mac_address` of
        # the given domain is associated.
        command = "virsh domiflist %(name)s | grep %(mac)s | awk '{print $3}'"
        result = self._run_command(command % {'mac': mac_address,
                                              'name': domain.name()})
        if result.get('error'):
            return

        # Run arp-scan on the given interface using the local network config
        # in order to generate the IP addresses to scan. The result is going
        # to include all MAC-IP address combinations available on the given
        # interface, not just that of the provided `mac_address`.
        iface = result.get('output', '').strip('\n')
        result = self._run_command('arp-scan -I %s -l' % iface, su=True)
        if result.get('error'):
            return

        # Parse the result of `arp-scan` to end up with MAC-IP address tuples.
        regex = r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\t(.*)\t'
        match = re.findall(regex, result.get('output', ''))

        # Check if `ping` exists on the host. If it does, then we can use it
        # to ping each IP address returned by `arp-scan` so that the host's
        # ARP table is permanently updated, which will in turn prevent this
        # method from being always invoked.
        ping_exists = self._run_command('command -v ping').get('output')

        # Update `self.arp_table` and the host's ARP table.
        for ip, mac in match:
            if not is_valid_ip_address(ip):
                log.error('Found invalid IP address %s (%s)', ip, mac)
                continue
            if mac not in self.arp_table:
                if ping_exists:
                    self._run_command('ping -c 1 %s' % ip)
                self.arp_table.setdefault(mac, []).append(ip)

    def _get_mac_addresses_for_domain(self, domain):
        """
        Parses network interface MAC addresses from the provided domain.
        """
        xml = domain.XMLDesc()
        etree = ET.XML(xml)
        elems = etree.findall("devices/interface/mac")

        result = []
        for elem in elems:
            mac_address = elem.get('address')
            result.append(mac_address)

        return result

    def list_sizes(self):
        return []

    def list_locations(self):
        return []

    def list_images(self, location=IMAGES_LOCATION):
        """
        Returns iso images as NodeImages
        Searches inside IMAGES_LOCATION, unless other location is specified
        """
        cmd = f"find {location} -name '*.iso' -o -name '*.img' -o -name '*.raw' -o -name '*.qcow' -o -name '*.qcow2' -type f | xargs stat -c '%n %s'"
        output = self._run_command(cmd).get('output')
        if not output:
            return []
        images = []

        for image in output.strip().split('\n'):
            path, size = image.split(' ')
            name = path.replace(IMAGES_LOCATION + '/', '')
            size = int(size)
            nodeimage = NodeImage(id=path, name=name, driver=self, extra={'host': self.host, 'size': size})
            images.append(nodeimage)

        return images

    def reboot_node(self, node):
        domain = self._get_domain_for_node(node=node)
        return domain.reboot(flags=0) == 0

    def destroy_node(self, node):
        domain = self._get_domain_for_node(node=node)
        return domain.destroy() == 0

    def ex_undefine_node(self, node):
        domain = self._get_domain_for_node(node=node)
        return domain.undefine() == 0

    def start_node(self, node):
        domain = self._get_domain_for_node(node=node)
        return domain.create() == 0

    def stop_node(self, node):
        domain = self._get_domain_for_node(node=node)
        return domain.shutdown() == 0

    def ex_start_node(self, node):
        # NOTE: This method is here for backward compatibility reasons after
        # this method was promoted to be part of the standard compute API in
        # Libcloud v2.7.0
        """
        Start a stopped node.

        :param  node: Node which should be used
        :type   node: :class:`Node`

        :rtype: ``bool``
        """
        return self.start_node(node=node)

    def ex_stop_node(self, node):
        # NOTE: This method is here for backward compatibility reasons after
        # this method was promoted to be part of the standard compute API in
        # Libcloud v2.7.0
        """
        Shutdown a running node.

        Note: Usually this will result in sending an ACPI event to the node.

        :param  node: Node which should be used
        :type   node: :class:`Node`

        :rtype: ``bool``
        """
        return self.stop_node(node=node)

    def ex_suspend_node(self, node):
        """
        Suspend a running node.

        :param  node: Node which should be used
        :type   node: :class:`Node`

        :rtype: ``bool``
        """
        domain = self._get_domain_for_node(node=node)
        return domain.suspend() == 0

    def ex_resume_node(self, node):
        """
        Resume a suspended node.

        :param  node: Node which should be used
        :type   node: :class:`Node`

        :rtype: ``bool``
        """
        domain = self._get_domain_for_node(node=node)
        return domain.resume() == 0

    def ex_take_node_screenshot(self, node, directory, screen=0):
        """
        Take a screenshot of a monitoring of a running instance.

        :param node: Node to take the screenshot of.
        :type node: :class:`libcloud.compute.base.Node`

        :param directory: Path where the screenshot will be saved.
        :type directory: ``str``

        :param screen: ID of the monitor to take the screenshot of.
        :type screen: ``int``

        :return: Full path where the screenshot has been saved.
        :rtype: ``str``
        """
        if not os.path.exists(directory) or not os.path.isdir(directory):
            raise ValueError('Invalid value for directory argument')

        domain = self._get_domain_for_node(node=node)
        stream = self.connection.newStream()
        mime_type = domain.screenshot(stream=stream, screen=0)
        extensions = mimetypes.guess_all_extensions(type=mime_type)

        if extensions:
            extension = extensions[0]
        else:
            extension = '.png'

        name = 'screenshot-%s%s' % (int(time.time()), extension)
        file_path = pjoin(directory, name)

        with open(file_path, 'wb') as fp:
            def write(stream, buf, opaque):
                fp.write(buf)

            stream.recvAll(write, None)

        try:
            stream.finish()
        except Exception:
            # Finish is not supported by all backends
            pass

        return file_path

    def ex_get_capabilities(self):
        """
        Return hypervisor capabilities
        """
        capabilities = self.connection.getCapabilities()
        return capabilities

    def ex_get_hypervisor_hostname(self):
        """
        Return a system hostname on which the hypervisor is running.
        """
        hostname = self.connection.getHostname()
        return hostname

    def ex_get_hypervisor_sysinfo(self):
        """
        Retrieve hypervisor system information.

        :rtype: ``dict``
        """
        xml = self.connection.getSysinfo()
        etree = ET.XML(xml)

        attributes = ['bios', 'system', 'processor', 'memory_device']

        sysinfo = {}
        for attribute in attributes:
            element = etree.find(attribute)
            entries = self._get_entries(element=element)
            sysinfo[attribute] = entries

        return sysinfo

    def _ex_get_cidr_from_network_name(self, network_name):
        """Return the CIDR of the network with name `network_name`

        This method is meant to return a `netaddr.IPNetwork` instance.

        """
        for ex_net in (self.ex_list_networks() + self.ex_list_interfaces()):
            if network_name == ex_net.name:
                return ex_net.cidr
        return None

    def create_node(self, name, disk_size=4, ram=512,
                    cpu=1, image=None, disk_path=None, create_from_existing=None,
                    os_type='linux', networks=[], cloud_init=None, public_key=None,
                    env_vars=None, interface_name='ens', vnfs=[]):
        """
        Creates a VM

        If image is missing, we assume we are creating the VM by importing
        existing image (create_from_existing has to be specified)

        If image is specified, should be a path. Eg
        eg /var/lib/libvirt/images/CentOS-7-x86_64-Minimal-1503-01.iso

        If disk_path is specified, needs to be a path, eg /var/lib/libvirt/images/name.img

        If it exists, raise an error and exit, otherwise we will try to create
        with qemu-img - disk_size being the size of it (in gigabytes)

        Cases that are covered by this:
        1) Boot from iso -needs name, iso image, ram, cpu, disk space, size
        2) Import existing image - needs create_from_existing, ram, cpu
        3) Create from existing disk image (.raw, .qcow, .qcow2, .img). Can pass a public key and optionally
        cloud init file if img is a cloud-init enabled image. First we copy the disk image, then we resize it,
        and if cloud init specified (or public key) we create an iso through genisoimage that will be used to deploy the
        related cloudinit setting on first boot time
        """
        # name validator, name should be unique
        name = self.ex_name_validator(name)
        # check which case we are on. If both image and disk_path are empty, then fail with error.

        if not create_from_existing and not image:
            raise Exception("You have to specify at least an image iso, to boot from, or an existing disk_path to import")

        # Network names are required later on to define the domain's XML.
        # NOTE that `networks` can either already be a list of network
        # names or a list of python dicts. The former is the legacy way
        # of doing things. In case of the latter, each dict will include
        # additional information for static IP assignment. For now, the
        # only accepted key-value pairs are:
        # - ip:           the IPv4 address to statically assign to the
        #                 interface
        # - primary:      the primary interface, which will be assigned
        #                 a routing rule for the default GW
        # - gateway:      the IPv4 address for the default Gateway. If
        #                 not given, it will default to the first IP of
        #                 the interface's network's range following the
        #                 network's own IP address
        # - network_name: the name of the corresponding network, such as
        #                 'default'
        network_names = []
        for n in networks:
            if isinstance(n, basestring):
                network_names.append(n)
            else:
                network_names.append(n.get('network_name'))

        network_names = network_names or []

        network_interfaces_init = ''

        # If multiple networks are specified or static IP assignment has
        # been requested, we supply a custom network-interfaces field in
        # meta-data. We enumerate interfaces starting at 3, as in recent
        # cases interfaces are configured with predictable names, such
        # as 'ens3' by default, as per https://www.freedesktop.org/wiki/
        # Software/systemd/PredictableNetworkInterfaceNames/
        if networks and (len(networks) > 1 or isinstance(networks[0], dict)):
            i = 3
            for net in networks:
                cidr = None
                if isinstance(net, dict) and net.get('ip'):
                    ip, gw = net.get('ip'), net.get('gateway')
                    if not is_valid_ip_address(ip):
                        raise ValueError("Invalid IPv4 address %s" % ip)
                    if gw and not is_valid_ip_address(gw):
                        raise ValueError("Invalid IPv4 address for GW %s" % gw)
                    network_name = net['network_name']
                    cidr = self._ex_get_cidr_from_network_name(network_name)
                    mode = 'static'
                else:
                    mode = 'dhcp'

                if not network_interfaces_init:
                    network_interfaces_init = 'network-interfaces: |'
                if mode == 'static' and cidr:
                    network_interfaces_init += '\n' + '\n'.join((
                        '  auto %s%s' % (interface_name, i),
                        '  iface %s%s inet %s' % (interface_name, i, mode),
                        '  address %s' % net['ip'],
                        '  network %s' % cidr.network,
                        '  netmask %s' % cidr.netmask,
                        '  broadcast %s' % cidr.broadcast,
                    ))
                    if net.get('primary'):
                        gw = net.get('gateway') or cidr[1]
                        network_interfaces_init += '\n  gateway %s' % (gw)
                else:
                    network_interfaces_init += '\n' + '\n'.join((
                        '  auto %s%s' % (interface_name, i),
                        '  iface %s%s inet dhcp' % (interface_name, i),
                    ))
                i += 1

            if not (network_interfaces_init.count('dhcp') or
                    network_interfaces_init.count('gateway')):
                log.error('Default GW not set')


        # define the VM
        if image:
            if IMAGES_LOCATION not in image:
                image = IMAGES_LOCATION + "/" + image
            if not self.ex_validate_disk(image):
                raise Exception("You have specified %s as image which does not exist" % image)
            if image.endswith(DISK_IMAGE_TYPES):
                image_conf = ''
                if cloud_init or public_key:
                    # suppose the img is cloudinit based, create user-data and meta-data,
                    # gen an isoimage through it and specify it
                    directory = pjoin(LIBCLOUD_DIRECTORY, name)
                    output = self._run_command('mkdir -p %s' % directory).get('output')
                    if self.key != 'root':
                        output = self._run_command('chown -R %s %s' % (self.key, directory)).get('output')

                    # Create meta-data. Extend with public SSH key and custom
                    # network-interfaces, if applicable.
                    metadata = 'instance-id: %s\nlocal-hostname: %s' % (name,
                                                                        name)

                    if public_key:
                        metadata += '\npublic-keys:\n  - %s' % public_key

                    if network_interfaces_init:
                        metadata += '\n%s' % network_interfaces_init

                    metadata_file = pjoin(directory, 'meta-data')
                    output = self._run_command('echo "%s" > %s' % (metadata, metadata_file)).get('output')

                    if not cloud_init:
                        cloud_init = "#!/bin/bash\ntouch /tmp/hello"
                    userdata_file = pjoin(directory, 'user-data')
                    output = self._run_command('echo "%s" > %s' % (cloud_init, userdata_file)).get('output')
                    cloudinit_files = '%s %s' % (metadata_file, userdata_file)
                    configiso_file = pjoin(directory, 'config.iso')
                    error_output = self._run_command('genisoimage -o %s -V cidata -r -J %s' % (configiso_file, cloudinit_files)).get('error')
                    if "command not found" in error_output:
                        image_conf = ''
                    else:
                        image_conf = IMAGE_TEMPLATE % configiso_file
            else:
                image_conf = IMAGE_TEMPLATE % image
        else:
            image_conf = ''

        disk_size_gb = str(disk_size) + 'G'
        try:
            ram = int(ram) * 1000
        except:
            ram = 1024 * 1000
        # TODO: get available ram, cpu and disk and inform if not available
        if create_from_existing:
            # create_from_existing case
            # if create_from_existing is specified but the path does not exist
            # fail with error
            if not self.ex_validate_disk(create_from_existing):
                raise Exception("You have specified to create from an existing "
                                "disk path that does not exist")
            else:
                disk_path = create_from_existing
        if image:
            if not disk_path:
                # make a default disk_path of  /var/lib/libvirt/images/vm_name.img
                # the disk_path need not exist, so we can create it
                disk_path = '%s/%s.img' % (IMAGES_LOCATION, name)
                for i in range(1, 20):
                    if self.ex_validate_disk(disk_path):
                        disk_path = '%s/%s.img' % (IMAGES_LOCATION, name + str(i))
                    else:
                        break

            if image.endswith(DISK_IMAGE_TYPES):
                if self.ex_validate_disk(disk_path):
                    raise Exception("You have specified to copy %s to a "
                                    "path that exists" % image)
                else:
                    cmd = "qemu-img convert %s %s" % (image, disk_path)
                    run_cmd = self._run_command(cmd)
                    output = run_cmd.get('output')
                    error = run_cmd.get('error')
                    if error:
                        raise Exception('Failed to copy disk %s: %s' % (image, error))

                    cmd = "qemu-img resize %s %s" % (disk_path, disk_size_gb)
                    run_cmd = self._run_command(cmd)
                    output = run_cmd.get('output')
                    error = run_cmd.get('error')
                    if error and 'WARNING' not in error:
                        # ignore WARNINGS
                        raise Exception('Failed to set the size for disk %s: %s' % (disk_path, error))
            else:
                if not self.ex_validate_disk(disk_path):
                    # in case existing disk path is provided, no need to create it
                    self.ex_create_disk(disk_path, disk_size_gb)

        capabilities = self.ex_get_capabilities()
        if "<domain type='kvm'>" in capabilities:
            # kvm hypervisor supported by the system
            emu = 'kvm'
        else:
            # only qemu emulator available
            emu = 'qemu'

        # Add multiple interfaces based on the `networks` list provided. NOTE
        # that the RTL8139 virtual network interface driver does not support
        # VLANs. To use VLANs with a virtual machine, opt for another virtual
        # network interface like virtio.
        xml_net_conf = []
        xml_net_template = """
    <interface type='%(net_type)s'>
      <source %(net_type)s='%(net_name)s'/>
      <model type='virtio'/>
    </interface>"""

        # Create interface configuration. By default, the guest VM will be in
        # the "default" network, which behaves like a NAT.
        ex_nets_names = [n.name for n in self.ex_list_networks()]
        for net in network_names:
            net_name = net
            net_type = 'network' if net in ex_nets_names else 'bridge'
            xml_net_conf.append(xml_net_template % ({'net_type': net_type,
                                                     'net_name': net_name}))

        init_env = ""
        if env_vars:
            for env_var in env_vars:
                init_env += "<initenv name='%s'>%s</initenv>\n" % (env_var, env_vars[env_var])

        hostdev = ""
        for vnf in vnfs:
            domain, bus, slotf = vnf.split(':')
            slot, function = slotf.split('.')
            hostdev += """
    <hostdev mode='subsystem' type='pci' managed='yes'>
      <source>
        <address domain='0x%s' bus='0x%s' slot='0x%s' function='0x%s'/>
      </source>
    </hostdev>""" % (domain, bus, slot, function)
        conf = XML_CONF_TEMPLATE % (emu, name, ram, cpu, init_env, disk_path, image_conf, ''.join(xml_net_conf), hostdev)

        self.connection.defineXML(conf)

        # start the VM

        domain = self.connection.lookupByName(name)
        domain.create()

        nodes = self.list_nodes(show_hypervisor=False)
        for node in nodes:
            if node.name == name:
                return node

        return True

    def ex_clone_node(self, node, new_name=None, resume_node=False):
        """Clone a domain

        The only required parameters are the `node` to clone and a `new_name`,
        which is going to be the name/hostname of the new guest VM, thus also
        oughts to be unique.

        Extra steps may also be required as soon as the cloning is done, such
        as changing host-unique files, e.g. the contents of /etc/hostname. If
        custom network configuration had been set up for the original domain,
        the clone is going to inherit it, as well. If static IPs have been
        assigned, they would most probably have to change on the new node to
        avoid potential routing conflicts, etc. See /etc/network/ for such
        changes. On the other hand, if networking has been set up using DHCP,
        the aforementioned changes are deemed unnecessary.

        Finally, the original guest VM may be optionally resumed.

        """

        # Generate unique clone name, if not provided.
        new_name = new_name or '%s-clone-%s' % (node.name, random.randint(1,100))

        # Get the current domain.
        domain = self._get_domain_for_node(node)

        # If it's running, stop it.
        if bool(domain.isActive()):
            self.ex_stop_node(node)

        # Get the domain's XML description.
        et = ET.XML(domain.XMLDesc())

        # Replace the current name with `new_name`.
        for child in et.getchildren():
            if child.tag == 'name':
                new_child = et.makeelement('name')
                new_child.text = new_name
                et.replace(child, new_child)
                break
        else:
            raise Exception("Failed to change the 'name' element of the XML")

        # Remove the old domain's UUID.
        for child in et.getchildren():
            if child.tag == 'uuid':
                et.remove(child)
                break
        else:
            raise Exception("Failed to remove the 'uuid' element of the XML")

        # Remove the old domain's MAC addresses, so they can be auto-generated.
        for child in et.findall('devices/interface'):
            for grandchild in child.getchildren():
                if grandchild.tag == 'mac':
                    child.remove(grandchild)
                    break

        # Point disk path to its new location.
        for child in et.findall('devices/disk/source'):
            if child.get('file') and child.get('file').endswith('.img'):
                old_disk_path = child.get('file')
                new_disk_path = old_disk_path.replace(domain.name(), new_name)
                child.set('file', new_disk_path)
                break
        else:
            raise Exception("Failed to locate disk path in XML description")

        # Copy the disk to its new location, as specified above.
        output = self._run_command('cp %s %s' % (old_disk_path, new_disk_path))
        if output.get('error'):
            raise Exception("Error copying the clone's disk image from "
                            "%s to %s" % (old_disk_path, new_disk_path))

        # Define the new domain via the modified XML.
        self.connection.defineXML(ET.tostring(et).decode())

        # Start the new domain.
        new_domain = self.connection.lookupByName(new_name)
        new_domain.create()

        # Resume the stopped node.
        if resume_node:
            self.ex_resume_node(node)

        return True

    def ex_rename_node(self, node, name):
        domain = self._get_domain_for_node(node=node)
        return domain.rename(name) == 0

    def ex_name_validator(self, name):
        """
        Makes sure name is not in use, and checks
        it is comprised only by alphanumeric chars and -_."
        """
        if not re.search(r'^[0-9a-zA-Z-_.]+[0-9a-zA-Z]$', name):
            raise Exception("Alphanumeric, dots, dashes and underscores are only allowed in VM name")

        nodes = self.list_nodes(show_hypervisor=False)

        if name in [node.name for node in nodes]:
            raise Exception("VM with name %s already exists" % name)

        return name

    def ex_validate_disk(self, disk_path):
        """
        Check if disk_path exists
        """
        cmd = 'ls %s' % disk_path
        error = self._run_command(cmd).get('error')

        if error:
            return False
        else:
            return True

    def ex_create_disk(self, disk_path, disk_size):
        """
        Create disk using qemu-img
        """
        cmd = "qemu-img create -f raw %s %s" % (disk_path, disk_size)

        error = self._run_command(cmd).get('error')
        if error:
            return False
        else:
            return True

    def _get_domain_for_node(self, node):
        """
        Return libvirt domain object for the provided node.
        """
        domain = self.connection.lookupByUUIDString(node.uuid)
        return domain

    def _get_entries(self, element):
        """
        Parse entries dictionary.

        :rtype: ``dict``
        """
        elements = element.findall('entry')

        result = {}
        for element in elements:
            name = element.get('name')
            value = element.text
            result[name] = value

        return result

    def ex_list_networks(self):
        """Return a list of all networks

        This method returns a list of libcloud Network objects

        """
        networks = []
        try:
            for net in self.connection.listAllNetworks():
                extra = {
                    'bridge': net.bridgeName(),
                    'xml': net.XMLDesc(),
                    'host': self.host
                }
                networks.append(Network(net.UUIDString(), net.name(), extra))
        except:
            pass  # Not supported by all hypervisors.
        return networks

    def ex_list_interfaces(self):
        """Return a list of all interfaces

        This method returns all interfaces as a list of libcloud Networks

        """
        networks = []
        try:
            for net in self.connection.listAllInterfaces():
                if net.name() == 'lo':  # Skip loopback.
                    continue
                extra = {
                    'mac': net.MACString(),
                    'xml': net.XMLDesc(),
                    'host': self.host
                }
                networks.append(Network(net.name(), net.name(), extra))
        except Exception as exc:
            # Not supported by all hypervisors.
            log.error(exc)

        return networks

    def ex_list_vnfs(self):
        import json
        cmd = """cat <<EOF | /bin/bash
NIC_DIR="/sys/class/net"
printf "{\n"
f=0
for i in \$( ls \$NIC_DIR );
do
	if [ -d \"\${NIC_DIR}/\$i/device\" -a ! -L \"\${NIC_DIR}/\$i/device/physfn\" ]; then
		declare -a VF_PCI_BDF
		declare -a VF_INTERFACE
		declare -a NUMA
		k=0
		for j in \$( ls \"\${NIC_DIR}/\$i/device\" ) ;
		do
			if [[ \"\$j\" == \"virtfn\"* ]]; then
				VF_PCI=\$( readlink \"\${NIC_DIR}/\$i/device/\$j\" | cut -d '/' -f2 )
				VF_PCI_BDF[\$k]=\$VF_PCI
				#get the interface name for the VF at this PCI Address
				for iface in \$( ls \$NIC_DIR );
				do
					link_dir=\$( readlink \${NIC_DIR}/\$iface )
					if [[ \"\$link_dir\" == *\"\$VF_PCI\"* ]]; then
						VF_INTERFACE[\$k]=\$iface
					fi
				done
				((k++))
			fi
		done
		NUM_VFs=\${#VF_PCI_BDF[@]}
		if [[ \$NUM_VFs -gt 0 ]]; then
			#get the PF Device Description
			PF_PCI=\$( readlink \"\${NIC_DIR}/\$i/device\" | cut -d '/' -f4 )
			PF_VENDOR=\$( lspci -vmmks \$PF_PCI | grep ^Vendor | cut -f2)
			PF_NAME=\$( lspci -vmmks \$PF_PCI | grep ^Device | cut -f2).
			if [[ \$f -gt 0 ]]; then
				printf \",\n\"
			else
				f=1
			fi
			printf \"\t\\\"\$i\\\": {\n\t\t\\\"vendor\\\": \\\"\$PF_VENDOR\\\", \n\t\t\\\"name\\\": \\\"\$PF_NAME\\\", \n\t\t\\\"vfs\\\": [\n\"
			for (( l = 0; l < \$NUM_VFs; l++ )) ;
			do
				if [[ \$l -gt 0 ]]; then
					printf \",\n\"
				fi
				NUMA=\$( cat \${NIC_DIR}/\${VF_INTERFACE[\$l]}/device/numa_node )
				printf \"\t\t\t{\\\"pci_bdf\\\": \\\"\${VF_PCI_BDF[\$l]}\\\", \\\"interface\\\": \\\"\${VF_INTERFACE[\$l]}\\\", \\\"numa\\\\": \\\"\$NUMA\\\"}\"
			done
			printf "\n\t\t]\n\t}"
			unset VF_PCI_BDF
			unset VF_INTERFACE
			unset NUMA
		fi
	fi
done
printf "\n}\n"
EOF
        """
        output = self._run_command(cmd).get('output')
        devices = json.loads(output)
        vnfs = []
        for d in devices:
            device = devices[d]
            for vf in device['vfs']:
               vf['device'] = {'vendor': device['vendor'], 'name': device['name'], 'interface': d}
               vnfs.append(vf)
        return vnfs

    def _parse_arp_table(self, arp_output):
        """
        Parse arp command output and return a dictionary which maps mac address
        to an IP address.

        :return: Dictionary which maps mac address to IP address.
        :rtype: ``dict``
        """
        lines = arp_output.split('\n')

        arp_table = defaultdict(list)
        for line in lines:
            match = re.match('.*?\((.*?)\) at (.*?)\s+', line)

            if not match:
                continue

            groups = match.groups()
            ip_address = groups[0]
            mac_address = groups[1]
            arp_table[mac_address].append(ip_address)

        return arp_table

    @property
    def ssh_connection(self):
        """Return a cached SSH connection object."""
        if self._ssh_conn is None:
            self._ssh_conn = self._ssh_connect()
        return self._ssh_conn

    def _ssh_connect(self):
        """Connect over SSH and return the SSHClient object.

        This method is meant to be called only by `self.ssh_connection` in
        order to establish an SSH, if one has not already been established.

        """
        assert self.secret and self._uri != 'qemu:///system'
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(self.host, port=self.ssh_port, username=self.key,
                    key_filename=self.secret, timeout=None,
                    allow_agent=False, look_for_keys=False)
        return ssh

    def _ssh_disconnect(self):
        """Close the SSH connection, if previously established."""
        if self._ssh_conn is not None:
            self._ssh_conn.close()
            self._ssh_conn = None

    def _run_command(self, cmd, su=False):
        """Run a command on a local or remote hypervisor.

        If the hypervisor is remote, `paramiko` is used to connect over SSH.

        If `su` is True or the user does not belong to the `libvirtd` group,
        then the command is run with `sudo -n`.

        """
        error, output = '', ''
        original_cmd = cmd

        # Prepend `sudo` to `cmd`, if necessary.
        if su is True:
            cmd = """
run() {
    if [ ! $( command -v sudo ) ] ; then
        exec "$@"
    else
        exec sudo -n "$@"
    fi
}

run %s
""" % cmd
        else:
            cmd = """
run() {
    if [ "$( groups | grep libvirtd )" ] || [ ! $( command -v sudo ) ] ; then
        exec "$@"
    else
        exec sudo -n "$@"
    fi
}

run %s
""" % cmd

        # Run the command using either `paramiko` or `subprocess`.
        if self._uri == 'qemu:///system':
            try:
                output = subprocess.check_output(cmd, shell=True)
            except subprocess.CalledProcessError as err:
                error = str(err)
                log.warn('Failed to run "%s" at %s: %r', cmd, self._uri, err)
        else:
            try:
                stdin, stdout, stderr = self.ssh_connection.exec_command(cmd)
                error, output = stderr.read(), stdout.read()
            except Exception as exc:
                log.warn('Failed to run "%s" at %s: %r', cmd, self.host, exc)

        if 'Permission denied' in error.decode() and not su:
            return self._run_command(original_cmd, True)
        return {'output': output.decode(), 'error': error.decode()}

    def disconnect(self):
        # Close the libvirt connection to the hypevisor.
        try:
            self.connection.close()
        except Exception as exc:
            log.warn('Failed to close connection to %s: %r', self._uri, exc)

        # Close the SSH connection to the hypervisor.
        try:
            self._ssh_disconnect()
        except Exception as exc:
            log.warn('Failed to close connection to %s: %r', self.host, exc)

        # Remove the SSH key from disk.
        try:
            os.remove(self.temp_key)
        except Exception as exc:
            log.warn('Failed to remove %s: %r', self.temp_key, exc)

    def __del__(self):
        """Disconnect completely upon garbage collection."""
        self.disconnect()


class Network(object):

    def __init__(self, id, name, extra={}):
        self.id = str(id)
        self.name = name
        self.extra = extra

    @property
    def xml(self):
        """Return the XML description of self."""
        return self.extra.get('xml', '')

    @property
    def cidr(self):
        """Return a `netaddr.IPNetwork` instance representing self."""
        if self.is_network:
            children = ET.XML(self.xml).findall('ip')
            if children:
                child = children[0]
                return netaddr.IPNetwork('%s/%s' % (child.get('address'),
                                                    child.get('netmask')))
        if self.is_interface:
            children = ET.XML(self.xml).findall('protocol')
            children = [
                c for
                c in children if c.get('family') == 'ipv4'
            ]
            grandchildren = [
                g for c in children for g in c.findall('ip')
            ]
            if grandchildren:
                child = grandchildren[0]
                return netaddr.IPNetwork('%s/%s' % (child.get('address'),
                                                    child.get('prefix')))
        return None

    @property
    def is_network(self):
        """Return True if self is part of self.list_networks."""
        return self.xml and ET.XML(self.xml).tag == 'network'

    @property
    def is_interface(self):
        """Return True if self is an interface as in bridged networks."""
        return self.xml and ET.XML(self.xml).tag == 'interface'

    def __repr__(self):
        return '<Network id="%s" name="%s">' % (self.id, self.name)


XML_CONF_TEMPLATE = '''
<domain type='%s'>
  <name>%s</name>
  <memory>%s</memory>
  <vcpu>%s</vcpu>
  <os>
   <type arch='x86_64'>hvm</type>
    <boot dev='hd'/>
    <boot dev='cdrom'/>
    %s
  </os>
 <features>
    <acpi/>
  </features>
  <clock offset='utc'/>
  <on_poweroff>destroy</on_poweroff>
  <on_reboot>restart</on_reboot>
  <on_crash>restart</on_crash>
  <devices>
    <disk type='file' device='disk'>
      <driver name='qemu' type='raw' io='native' cache='none'/>
      <source file='%s'/>
      <target dev='hda' bus='virtio'/>
    </disk>%s%s
    <console type='pty'>
      <target type='serial'/>
    </console>
    <console type='pty'>
      <target type='virtio'/>
    </console>
    <input type='mouse' bus='ps2'/>
    <graphics type='vnc' port='-1' autoport='yes' listen='127.0.0.1'/>
    <video>
      <model type='cirrus' vram='9216' heads='1'/>
    </video>
    %s
  </devices>
</domain>
'''

IMAGE_TEMPLATE = '''
    <disk type='file' device='cdrom'>
      <driver name='qemu' type='raw'/>
      <source file='%s'/>
     <target dev='hdb' bus='ide'/>
     <readonly/>
    </disk>
'''
