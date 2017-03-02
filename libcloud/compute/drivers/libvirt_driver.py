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

try:
    import libvirt
    have_libvirt = True
except ImportError:
    raise RuntimeError('Missing "libvirt" dependency. You can install it using '
                       'pip. For example ./bin/pip install libvirt-python')

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
                # if ssh key is string create temp file
                if not os.path.isfile(ssh_key):
                    key_temp_file = NamedTemporaryFile(delete=False)
                    key_temp_file.write(ssh_key)
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
            if 'Could not resolve' in exc.message:
                raise Exception("Make sure hostname is accessible")
            if 'Connection refused' in exc.message:
                raise Exception("Make sure hostname is accessible and libvirt "
                                "is running")
            if 'Permission denied' in exc.message:
                raise Exception("Make sure ssh key and username are valid")
            if 'End of file while reading data' in exc.message:
                raise Exception("Make sure libvirt is running and user %s is "
                                "authorised to connect" % user)
            raise Exception("Connection error")

            atexit.register(self.disconnect)

    def __del__(self):
        self.disconnect()

    def disconnect(self):
        # closes connection to the hypevisor
        try:
            self.connection.close()
        except:
            pass

        if not self.temp_key:
            return

        try:
            os.remove(self.temp_key)
        except Exception:
            pass

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

        if show_hypervisor:
            public_ips, private_ips = [], []
            # append hypervisor as well
            name = self.connection.getHostname()
            try:
                if is_public_subnet(socket.gethostbyname(self.hypervisor)):
                    public_ips.append(self.hypervisor)
                else:
                    private_ips.append(self.hypervisor)
            except:
                public_ips.append(self.hypervisor)

            extra = {'tags': {'type': 'hypervisor'}}
            node = Node(id=self.hypervisor, name=name, state=NodeState.RUNNING,
                        public_ips=public_ips, private_ips=private_ips,
                        driver=self, extra=extra)
            nodes.append(node)

        return nodes

    def _to_node(self, domain):
        state, max_mem, memory, vcpu_count, used_cpu_time = domain.info()
        state = self.NODE_STATE_MAP.get(state, NodeState.UNKNOWN)

        public_ips, private_ips = [], []

        ip_addresses = self._get_ip_addresses_for_domain(domain)

        for ip_address in ip_addresses:
            if is_public_subnet(ip_address):
                public_ips.append(ip_address)
            else:
                private_ips.append(ip_address)
        try:
            # this will work only if real name is given to a guest VM's name.
            public_ip = socket.gethostbyname(domain.name())
        except:
            public_ip = ''
        if public_ip and public_ip not in ip_addresses:
            # avoid duplicate insertion in public ips
            public_ips.append(public_ip)

        try:
            xml_description = domain.XMLDesc()
        except:
            xml_description = ''

        extra = {'uuid': domain.UUIDString(), 'os_type': domain.OSType(),
                 'types': self.connection.getType(),
                 'hypervisor_name': self.connection.getHostname(),
                 'memory': '%s MB' % str(memory / 1024), 'processors': vcpu_count,
                 'used_cpu_time': used_cpu_time, 'xml_description': xml_description}
        node = Node(id=domain.UUIDString(), name=domain.name(), state=state,
                    public_ips=public_ips, private_ips=private_ips,
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
            if mac_address in self.arp_table:
                ip_addresses = self.arp_table[mac_address]
                result.extend(ip_addresses)

        return result

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
        """
        Returns sizes
        """
        sizes = []
        # append a min size
        size_id = "1:512"
        name = "CPU 1, RAM 512 MB"
        size = NodeSize(id=size_id, name=name, ram=512, disk=1, bandwidth=None,
                        price=None, driver=self, extra={'cpu': 1})
        sizes.append(size)

        try:
            # not supported by all hypervisors
            info = self.connection.getInfo()
            total_ram = info[1]
            total_cores = info[2]

            for core in range(1, total_cores + 1):
                for ram in range(1024, total_ram + 1, 1024):
                    size_id = "%s:%s" % (core, ram)
                    name = "CPU %s, RAM %s GB" % (core, str(ram / 1024))
                    size = NodeSize(id=size_id, name=name, ram=ram, disk=1,
                                    bandwidth=None, price=None, driver=self,
                                    extra={'cpu': core})
                    sizes.append(size)
        except:
            pass
        return sizes

    def list_locations(self):
        return []

    def list_images(self, location=IMAGES_LOCATION):
        """
        Returns iso images as NodeImages
        Searches inside IMAGES_LOCATION, unless other location is specified
        """
        images = []
        cmd = "find %s -name '*.iso' -o -name '*.img' -o -name '*.raw' -o -name '*.qcow' -o -name '*.qcow2'" % location
        output = self._run_command(cmd).get('output')

        if output:
            for image in output.strip().split('\n'):
                name = image.replace(IMAGES_LOCATION + '/', '')
                nodeimage = NodeImage(id=image, name=name, driver=self, extra={})
                images.append(nodeimage)

        return images

    def reboot_node(self, node):
        domain = self._get_domain_for_node(node=node)
        return domain.reboot(flags=0) == 0

    def destroy_node(self, node):
        domain = self._get_domain_for_node(node=node)
        return domain.destroy() == 0

    def ex_undefine_node(self, node):
        cmd = "virsh destroy %s" % node.id
        output = self._run_command(cmd).get('output')
        cmd = "virsh undefine %s" % node.id
        output = self._run_command(cmd).get('output')

        return True

    def ex_start_node(self, node):
        """
        Start a stopped node.

        :param  node: Node which should be used
        :type   node: :class:`Node`

        :rtype: ``bool``
        """
        domain = self._get_domain_for_node(node=node)
        return domain.create() == 0

    def ex_stop_node(self, node):
        """
        Shutdown a running node.

        Note: Usually this will result in sending an ACPI event to the node.

        :param  node: Node which should be used
        :type   node: :class:`Node`

        :rtype: ``bool``
        """
        domain = self._get_domain_for_node(node=node)
        return domain.shutdown() == 0

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

    def create_node(self, name, disk_size=4, ram=512,
                    cpu=1, image=None, disk_path=None, create_from_existing=None,
                    os_type='linux', networks=[], cloud_init=None, public_key=None):
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
        # define the VM
        if image:
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

                    if public_key:
                        metadata = \
'''instance-id: %s
local-hostname: %s
public-keys:
  - %s''' % (name, name, public_key)
                    else:
                        metadata = \
'''instance-id: %s
local-hostname: %s''' % (name, name)

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

        if networks:
            network = networks[0]
        else:
            network = 'default'

        net_type = 'network'
        net_name = network

        if network in self.ex_list_bridges():
            # network is a bridge
            net_type = 'bridge'
            net_name = network

        conf = XML_CONF_TEMPLATE % (emu, name, ram, cpu, disk_path, image_conf, net_type, net_type, net_name)

        self.connection.defineXML(conf)

        # start the VM

        domain = self.connection.lookupByName(name)
        domain.create()

        nodes = self.list_nodes(show_hypervisor=False)
        for node in nodes:
            if node.name == name:
                return node

        return True

    def ex_clone_vm(self, node, new_name=None):
        """
        Clones a VM
        """
        # TODO
        # if VM is running, raise exception and exit
        # step1: get existing node conf through loookupbyname and fetch disk info
        # step2: remove uuid and mac from new node conf
        # step3: set name in new node conf
        # step4: cp disk img to new one
        # step4: define new xml
        # step5: start new node

        return None

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

    def ex_list_bridges(self):
        bridges = []
        try:
            # not supported by all hypervisors
            for net in self.connection.listAllNetworks():
                    bridges.append(net.bridgeName())
        except:
            pass
        return bridges

    def ex_list_networks(self):
        networks = [Network('default', 'default')]
        try:
            # not supported by all hypervisors
            for net in self.connection.listAllNetworks():
                net_name = net.bridgeName()
                networks.append(Network(net_name, net_name))
        except:
            pass
        return networks

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

    def _run_command(self, cmd):
        """
        Run a command on a local or remote hypervisor
        If the hypervisor is remote, run the command with paramiko
        """
        output = ''
        error = ''
        # run cmd with sudo prefix in case user is not root
        if self.key != 'root':
            cmd = 'sudo %s' % cmd
        if self.secret:
            try:
                ssh = paramiko.SSHClient()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

                ssh.connect(self.host, username=self.key, key_filename=self.secret,
                            port=self.ssh_port, timeout=None, allow_agent=False,
                            look_for_keys=False)
                stdin, stdout, stderr = ssh.exec_command(cmd)

                output = stdout.read()
                error = stderr.read()
                ssh.close()
            except:
                pass
        else:
            if ALLOW_LIBVIRT_LOCALHOST and self._uri == 'qemu:///system':
                try:
                    cmd = shlex.split(cmd)
                    child = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                             stderr=subprocess.PIPE)
                    output, _ = child.communicate()
                except:
                    pass
        return {'output': output, 'error': error}


class Network(object):

    def __init__(self, id, name, extra={}):
        self.id = str(id)
        self.name = name
        self.extra = extra

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
    </disk>%s
    <interface type='%s'>
      <source %s='%s'/>
      <model type='virtio'/>
    </interface>
    <input type='mouse' bus='ps2'/>
    <graphics type='vnc' port='-1' autoport='yes' listen='127.0.0.1'/>
    <video>
      <model type='cirrus' vram='9216' heads='1'/>
    </video>
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
