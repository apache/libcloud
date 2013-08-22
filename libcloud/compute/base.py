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
Provides base classes for working with drivers
"""

import sys
import time
import hashlib
import os
import socket
import struct
import binascii

from libcloud.utils.py3 import b

import libcloud.compute.ssh
from libcloud.pricing import get_size_price
from libcloud.compute.types import NodeState, DeploymentError
from libcloud.compute.ssh import SSHClient

# @@TR: are the imports below part of the public api for this
# module? They aren't used in here ...
from libcloud.common.base import ConnectionKey, ConnectionUserAndKey
from libcloud.common.base import BaseDriver
from libcloud.httplib_ssl import LibcloudHTTPSConnection
from libcloud.common.base import LibcloudHTTPConnection
from libcloud.common.types import LibcloudError


# How long to wait for the node to come online after creating it
NODE_ONLINE_WAIT_TIMEOUT = 10 * 60

# How long to try connecting to a remote SSH server when running a deployment
# script.
SSH_CONNECT_TIMEOUT = 5 * 60


__all__ = [
    "Node",
    "NodeState",
    "NodeSize",
    "NodeImage",
    "NodeLocation",
    "NodeAuthSSHKey",
    "NodeAuthPassword",
    "NodeDriver",

    # @@TR: do the following need exporting?
    "ConnectionKey",
    "ConnectionUserAndKey",
    "LibcloudHTTPSConnection",
    "LibcloudHTTPConnection"
]


class UuidMixin(object):
    """
    Mixin class for get_uuid function.
    """

    def __init__(self):
        self._uuid = None

    def get_uuid(self):
        """Unique hash for a node, node image, or node size

        :return: ``string``

        The hash is a function of an SHA1 hash of the node, node image,
        or node size's ID and its driver which means that it should be
        unique between all objects of its type.
        In some subclasses (e.g. GoGridNode) there is no ID
        available so the public IP address is used.  This means that,
        unlike a properly done system UUID, the same UUID may mean a
        different system install at a different time

        >>> from libcloud.compute.drivers.dummy import DummyNodeDriver
        >>> driver = DummyNodeDriver(0)
        >>> node = driver.create_node()
        >>> node.get_uuid()
        'd3748461511d8b9b0e0bfa0d4d3383a619a2bb9f'

        Note, for example, that this example will always produce the
        same UUID!
        """
        if not self._uuid:
            self._uuid = hashlib.sha1(b('%s:%s' %
                                      (self.id, self.driver.type))).hexdigest()

        return self._uuid

    @property
    def uuid(self):
        return self.get_uuid()


class Node(UuidMixin):
    """
    Provide a common interface for handling nodes of all types.

    The Node object provides the interface in libcloud through which
    we can manipulate nodes in different cloud providers in the same
    way.  Node objects don't actually do much directly themselves,
    instead the node driver handles the connection to the node.

    You don't normally create a node object yourself; instead you use
    a driver and then have that create the node for you.

    >>> from libcloud.compute.drivers.dummy import DummyNodeDriver
    >>> driver = DummyNodeDriver(0)
    >>> node = driver.create_node()
    >>> node.public_ips[0]
    '127.0.0.3'
    >>> node.name
    'dummy-3'

    You can also get nodes from the driver's list_node function.

    >>> node = driver.list_nodes()[0]
    >>> node.name
    'dummy-1'

    the node keeps a reference to its own driver which means that we
    can work on nodes from different providers without having to know
    which is which.

    >>> driver = DummyNodeDriver(72)
    >>> node2 = driver.create_node()
    >>> node.driver.creds
    0
    >>> node2.driver.creds
    72

    Althrough Node objects can be subclassed, this isn't normally
    done.  Instead, any driver specific information is stored in the
    "extra" proproperty of the node.

    >>> node.extra
    {'foo': 'bar'}

    """

    def __init__(self, id, name, state, public_ips, private_ips,
                 driver, size=None, image=None, extra=None):
        self.id = str(id) if id else None
        self.name = name
        self.state = state
        self.public_ips = public_ips if public_ips else []
        self.private_ips = private_ips if private_ips else []
        self.driver = driver
        self.size = size
        self.image = image
        self.extra = extra or {}
        UuidMixin.__init__(self)

    # Note: getters and setters bellow are here only for backward
    # compatibility. They will be removed in the next release.

    def _set_public_ips(self, value):
        self.public_ips = value

    def _get_public_ips(self):
        return self.public_ips

    def _set_private_ips(self, value):
        self.private_ips = value

    def _get_private_ips(self):
        return self.private_ips

    public_ip = property(fget=_get_public_ips, fset=_set_public_ips)
    private_ip = property(fget=_get_private_ips, fset=_set_private_ips)

    def reboot(self):
        """Reboot this node

        :return: ``bool``

        This calls the node's driver and reboots the node

        >>> from libcloud.compute.drivers.dummy import DummyNodeDriver
        >>> driver = DummyNodeDriver(0)
        >>> node = driver.create_node()
        >>> from libcloud.compute.types import NodeState
        >>> node.state == NodeState.RUNNING
        True
        >>> node.state == NodeState.REBOOTING
        False
        >>> node.reboot()
        True
        >>> node.state == NodeState.REBOOTING
        True
        """
        return self.driver.reboot_node(self)

    def destroy(self):
        """Destroy this node

        :return: ``bool``

        This calls the node's driver and destroys the node

        >>> from libcloud.compute.drivers.dummy import DummyNodeDriver
        >>> driver = DummyNodeDriver(0)
        >>> from libcloud.compute.types import NodeState
        >>> node = driver.create_node()
        >>> node.state == NodeState.RUNNING
        True
        >>> node.destroy()
        True
        >>> node.state == NodeState.RUNNING
        False

        """
        return self.driver.destroy_node(self)

    def __repr__(self):
        return (('<Node: uuid=%s, name=%s, state=%s, public_ips=%s, '
                 'provider=%s ...>')
                % (self.uuid, self.name, self.state, self.public_ips,
                   self.driver.name))


class NodeSize(UuidMixin):
    """
    A Base NodeSize class to derive from.

    NodeSizes are objects which are typically returned a driver's
    list_sizes function.  They contain a number of different
    parameters which define how big an image is.

    The exact parameters available depends on the provider.

    N.B. Where a parameter is "unlimited" (for example bandwidth in
    Amazon) this will be given as 0.

    >>> from libcloud.compute.drivers.dummy import DummyNodeDriver
    >>> driver = DummyNodeDriver(0)
    >>> size = driver.list_sizes()[0]
    >>> size.ram
    128
    >>> size.bandwidth
    500
    >>> size.price
    4
    """

    def __init__(self, id, name, ram, disk, bandwidth, price, driver):
        self.id = str(id)
        self.name = name
        self.ram = ram
        self.disk = disk
        self.bandwidth = bandwidth
        self.price = price
        self.driver = driver
        UuidMixin.__init__(self)

    def __repr__(self):
        return (('<NodeSize: id=%s, name=%s, ram=%s disk=%s bandwidth=%s '
                 'price=%s driver=%s ...>')
                % (self.id, self.name, self.ram, self.disk, self.bandwidth,
                   self.price, self.driver.name))


class NodeImage(UuidMixin):
    """
    An operating system image.

    NodeImage objects are typically returned by the driver for the
    cloud provider in response to the list_images function

    >>> from libcloud.compute.drivers.dummy import DummyNodeDriver
    >>> driver = DummyNodeDriver(0)
    >>> image = driver.list_images()[0]
    >>> image.name
    'Ubuntu 9.10'

    Apart from name and id, there is no further standard information;
    other parameters are stored in a driver specific "extra" variable

    When creating a node, a node image should be given as an argument
    to the create_node function to decide which OS image to use.

    >>> node = driver.create_node(image=image)

    """

    def __init__(self, id, name, driver, extra=None):
        self.id = str(id)
        self.name = name
        self.driver = driver
        self.extra = extra or {}
        UuidMixin.__init__(self)

    def __repr__(self):
        return (('<NodeImage: id=%s, name=%s, driver=%s  ...>')
                % (self.id, self.name, self.driver.name))


class NodeLocation(object):
    """
    A physical location where nodes can be.

    >>> from libcloud.compute.drivers.dummy import DummyNodeDriver
    >>> driver = DummyNodeDriver(0)
    >>> location = driver.list_locations()[0]
    >>> location.country
    'US'
    """

    def __init__(self, id, name, country, driver):
        self.id = str(id)
        self.name = name
        self.country = country
        self.driver = driver

    def __repr__(self):
        return (('<NodeLocation: id=%s, name=%s, country=%s, driver=%s>')
                % (self.id, self.name, self.country, self.driver.name))


class NodeAuthSSHKey(object):
    """
    An SSH key to be installed for authentication to a node.

    This is the actual contents of the users ssh public key which will
    normally be installed as root's public key on the node.

    >>> pubkey = '...' # read from file
    >>> from libcloud.compute.base import NodeAuthSSHKey
    >>> k = NodeAuthSSHKey(pubkey)
    >>> k
    <NodeAuthSSHKey>
    """

    def __init__(self, pubkey):
        self.pubkey = pubkey

    def __repr__(self):
        return '<NodeAuthSSHKey>'


class NodeAuthPassword(object):
    """
    A password to be used for authentication to a node.
    """
    def __init__(self, password, generated=False):
        self.password = password
        self.generated = generated

    def __repr__(self):
        return '<NodeAuthPassword>'


class StorageVolume(UuidMixin):
    """
    A base StorageVolume class to derive from.
    """

    def __init__(self, id, name, size, driver, extra=None):
        self.id = id
        self.name = name
        self.size = size
        self.driver = driver
        self.extra = extra
        UuidMixin.__init__(self)

    def attach(self, node, device=None):
        """
        Attach this volume to a node.

        :param node: Node to attach volume to
        :type node: :class:`Node`

        :param device: Where the device is exposed,
                            e.g. '/dev/sdb (optional)
        :type device: ``str``

        :return s ``bool``
        """

        return self.driver.attach_volume(node=node, volume=self, device=device)

    def detach(self):
        """
        Detach this volume from its node

        :return s ``bool``
        """

        return self.driver.detach_volume(volume=self)

    def list_snapshots(self):
        """
        :return s ``list`` of ``VolumeSnapshot``
        """
        return self.driver.list_volume_snapshots(volume=self)

    def snapshot(self, name):
        """
        Creates a snapshot of this volume.

        :return s ``VolumeSnapshot``
        """
        return self.driver.create_volume_snapshot(volume=self, name=name)

    def destroy(self):
        """
        Destroy this storage volume.

        :return s ``bool``
        """

        return self.driver.destroy_volume(volume=self)

    def __repr__(self):
        return '<StorageVolume id=%s size=%s driver=%s>' % (
               self.id, self.size, self.driver.name)


class VolumeSnapshot(object):
    def __init__(self, driver):
        self.driver = driver

    def destroy(self):
        """
        Destroys this snapshot.

        :return s ``bool``
        """
        return self.driver.destroy_volume_snapshot(snapshot=self)


class NodeDriver(BaseDriver):
    """
    A base NodeDriver class to derive from

    This class is always subclassed by a specific driver.  For
    examples of base behavior of most functions (except deploy node)
    see the dummy driver.

    """

    connectionCls = ConnectionKey
    name = None
    type = None
    port = None
    features = {"create_node": []}
    """
    List of available features for a driver.
        - :class:`create_node`
            - ssh_key: Supports :class:`NodeAuthSSHKey` as an authentication method
              for nodes.
            - password: Supports :class:`NodeAuthPassword` as an authentication
              method for nodes.
            - generates_password: Returns a password attribute on the Node
              object returned from creation.
    """

    NODE_STATE_MAP = {}

    def __init__(self, key, secret=None, secure=True, host=None, port=None,
                 api_version=None, **kwargs):
        super(NodeDriver, self).__init__(key=key, secret=secret, secure=secure,
                                         host=host, port=port,
                                         api_version=api_version, **kwargs)

    def _get_and_check_auth(self, auth):
        """
        Helper function for providers supporting L{NodeAuthPassword} or
        L{NodeAuthSSHKey}

        Validates that only a supported object type is passed to the auth
        parameter and raises an exception if it is not.

        If no L{NodeAuthPassword} object is provided but one is expected then a
        password is automatically generated.
        """

        if isinstance(auth, NodeAuthPassword):
            if 'password' in self.features['create_node']:
                return auth
            raise LibcloudError(
                'Password provided as authentication information, but password'
                'not supported', driver=self)

        if isinstance(auth, NodeAuthSSHKey):
            if 'ssh_key' in self.features['create_node']:
                return auth
            raise LibcloudError(
                'SSH Key provided as authentication information, but SSH Key'
                'not supported', driver=self)

        if 'password' in self.features['create_node']:
            value = os.urandom(16)
            value = binascii.hexlify(value).decode('ascii')
            return NodeAuthPassword(value, generated=True)

        if auth:
            raise LibcloudError(
                '"auth" argument provided, but it was not a NodeAuthPassword'
                'or NodeAuthSSHKey object', driver=self)

    def create_node(self, **kwargs):
        """
        Create a new node instance. This instance will be started
        automatically.

        Not all hosting API's are created equal and to allow libcloud to support
        as many as possible there are some standard supported variations of
        ``create_node``. These are declared using a ``features`` API. You can
        inspect ``driver.features['create_node']`` to see what variation of the
        API you are dealing with:

        ``ssh_key``
            You can inject a public key into a new node allows key based SSH
            authentication.
        ``password``
            You can inject a password into a new node for SSH authentication.
            If no password is provided libcloud will generated a password.
            The password will be available as
            ``return_value.extra['password']``.
        ``generates_password``
            The hosting provider will generate a password. It will be returned
            to you via ``return_value.extra['password']``.

        Some drivers allow you to set how you will authenticate with the
        instance that is created. You can inject this initial authentication
        information via the ``auth`` parameter.

        If a driver supports the ``ssh_key`` feature flag for ``created_node``
        you can upload a public key into the new instance::

            >>> auth = NodeAuthSSHKey('pubkey data here')
            >>> node = driver.create_node("test_node", auth=auth)

        If a driver supports the ``password`` feature flag for ``create_node``
        you can set a password::

            >>> auth = NodeAuthPassword('mysecretpassword')
            >>> node = driver.create_node("test_node", auth=auth)

        If a driver supports the ``password`` feature and you don't provide the
        ``auth`` argument libcloud will assign a password::

            >>> node = driver.create_node("test_node")
            >>> password = node.extra['password']

        A password will also be returned in this way for drivers that declare
        the ``generates_password`` feature, though in that case the password is
        actually provided to the driver API by the hosting provider rather than
        generated by libcloud.

        You can only pass a :class:`NodeAuthPassword` or
        :class:`NodeAuthSSHKey` to ``create_node`` via the auth parameter if
        has the corresponding feature flag.

        :param name:   String with a name for this new node (required)
        :type name:   ``str``

        :param size:   The size of resources allocated to this node.
                            (required)
        :type size:   :class:`NodeSize`

        :param image:  OS Image to boot on node. (required)
        :type image:  :class:`NodeImage`

        :param location: Which data center to create a node in. If empty,
                              undefined behavoir will be selected. (optional)
        :type location: :class:`NodeLocation`

        :param auth:   Initial authentication information for the node
                            (optional)
        :type auth:   :class:`NodeAuthSSHKey` or :class:`NodeAuthPassword`

        :return: The newly created node.
        :rtype: :class:`Node`
        """
        raise NotImplementedError(
            'create_node not implemented for this driver')

    def destroy_node(self, node):
        """Destroy a node.

        Depending upon the provider, this may destroy all data associated with
        the node, including backups.

        :param node: The node to be destroyed
        :type node: :class:`Node`

        :return: True if the destroy was successful, otherwise False
        :rtype: ``bool``
        """
        raise NotImplementedError(
            'destroy_node not implemented for this driver')

    def reboot_node(self, node):
        """
        Reboot a node.

        :param node: The node to be rebooted
        :type node: :class:`Node`

        :return: True if the reboot was successful, otherwise False
        :rtype: ``bool``
        """
        raise NotImplementedError(
            'reboot_node not implemented for this driver')

    def list_nodes(self):
        """
        List all nodes
        :return:  list of node objects
        :rtype: ``list`` of :class:`Node`
        """
        raise NotImplementedError(
            'list_nodes not implemented for this driver')

    def list_images(self, location=None):
        """
        List images on a provider

        :param location: The location at which to list images
        :type location: :class:`NodeLocation`

        :return: list of node image objects
        :rtype: ``list`` of :class:`NodeImage`
        """
        raise NotImplementedError(
            'list_images not implemented for this driver')

    def list_sizes(self, location=None):
        """
        List sizes on a provider

        :param location: The location at which to list sizes
        :type location: :class:`NodeLocation`

        :return: list of node size objects
        :rtype: ``list`` of :class:`NodeSize`
        """
        raise NotImplementedError(
            'list_sizes not implemented for this driver')

    def list_locations(self):
        """
        List data centers for a provider

        :return: list of node location objects
        :rtype: ``list`` of :class:`NodeLocation`
        """
        raise NotImplementedError(
            'list_locations not implemented for this driver')

    def deploy_node(self, **kwargs):
        """
        Create a new node, and start deployment.

        In order to be able to SSH into a created node access credentials are
        required.

        A user can pass either a :class:`NodeAuthPassword` or
        :class:`NodeAuthSSHKey` to the ``auth`` argument. If the
        ``create_node`` implementation supports that kind if credential (as
        declared in ``self.features['create_node']``) then it is passed on to
        ``create_node``. Otherwise it is not passed on to ``create_node`` and
        it is only used for authentication.

        If the ``auth`` parameter is not supplied but the driver declares it
        supports ``generates_password`` then the password returned by
        ``create_node`` will be used to SSH into the server.

        Finally, if the ``ssh_key_file`` is supplied that key will be used to
        SSH into the server.

        This function may raise a :class:`DeploymentException`, if a create_node
        call was successful, but there is a later error (like SSH failing or
        timing out).  This exception includes a Node object which you may want
        to destroy if incomplete deployments are not desirable.

        >>> from libcloud.compute.drivers.dummy import DummyNodeDriver
        >>> from libcloud.compute.deployment import ScriptDeployment
        >>> from libcloud.compute.deployment import MultiStepDeployment
        >>> from libcloud.compute.base import NodeAuthSSHKey
        >>> driver = DummyNodeDriver(0)
        >>> key = NodeAuthSSHKey('...') # read from file
        >>> script = ScriptDeployment("yum -y install emacs strace tcpdump")
        >>> msd = MultiStepDeployment([key, script])
        >>> def d():
        ...     try:
        ...         node = driver.deploy_node(deploy=msd)
        ...     except NotImplementedError:
        ...         print ("not implemented for dummy driver")
        >>> d()
        not implemented for dummy driver

        Deploy node is typically not overridden in subclasses.  The
        existing implementation should be able to handle most such.

        :param deploy: Deployment to run once machine is online and
                            availble to SSH.
        :type deploy: :class:`Deployment`

        :param ssh_username: Optional name of the account which is used
                                  when connecting to
                                  SSH server (default is root)
        :type ssh_username: ``str``

        :param ssh_alternate_usernames: Optional list of ssh usernames to
                                             try to connect with if using the
                                             default one fails
        :type ssh_alternate_usernames: ``list``

        :param ssh_port: Optional SSH server port (default is 22)
        :type ssh_port: ``int``

        :param ssh_timeout: Optional SSH connection timeout in seconds
                                 (default is 10)
        :type ssh_timeout: ``float``

        :param auth:   Initial authentication information for the node
                            (optional)
        :type auth:   :class:`NodeAuthSSHKey` or :class:`NodeAuthPassword`

        :param ssh_key: A path (or paths) to an SSH private key with which
                             to attempt to authenticate. (optional)
        :type ssh_key: ``str`` or ``list`` of ``str``

        :param timeout: How many seconds to wait before timing out.
                             (default is 600)
        :type timeout: ``int``

        :param max_tries: How many times to retry if a deployment fails
                               before giving up (default is 3)
        :type max_tries: ``int``

        :param ssh_interface: The interface to wait for. Default is
                                   'public_ips', other option is 'private_ips'.
        :type ssh_interface: ``str``
        """
        if not libcloud.compute.ssh.have_paramiko:
            raise RuntimeError('paramiko is not installed. You can install ' +
                               'it using pip: pip install paramiko')

        if 'auth' in kwargs:
            auth = kwargs['auth']
            if not isinstance(auth, (NodeAuthSSHKey, NodeAuthPassword)):
                raise NotImplementedError(
                    'If providing auth, only NodeAuthSSHKey or'
                    'NodeAuthPassword is supported')
        elif 'ssh_key' in kwargs:
            # If an ssh_key is provided we can try deploy_node
            pass
        elif 'create_node' in self.features:
            f = self.features['create_node']
            if not 'generates_password' in f and not "password" in f:
                raise NotImplementedError(
                    'deploy_node not implemented for this driver')
        else:
            raise NotImplementedError(
                'deploy_node not implemented for this driver')

        node = self.create_node(**kwargs)
        max_tries = kwargs.get('max_tries', 3)

        password = None
        if 'auth' in kwargs:
            if isinstance(kwargs['auth'], NodeAuthPassword):
                password = kwargs['auth'].password
        elif 'password' in node.extra:
            password = node.extra['password']

        ssh_interface = kwargs.get('ssh_interface', 'public_ips')

        # Wait until node is up and running and has IP assigned
        try:
            node, ip_addresses = self.wait_until_running(
                nodes=[node],
                wait_period=3,
                timeout=kwargs.get('timeout', NODE_ONLINE_WAIT_TIMEOUT),
                ssh_interface=ssh_interface)[0]
        except Exception:
            e = sys.exc_info()[1]
            raise DeploymentError(node=node, original_exception=e, driver=self)

        ssh_username = kwargs.get('ssh_username', 'root')
        ssh_alternate_usernames = kwargs.get('ssh_alternate_usernames', [])
        ssh_port = kwargs.get('ssh_port', 22)
        ssh_timeout = kwargs.get('ssh_timeout', 10)
        ssh_key_file = kwargs.get('ssh_key', None)
        timeout = kwargs.get('timeout', SSH_CONNECT_TIMEOUT)

        deploy_error = None

        for username in ([ssh_username] + ssh_alternate_usernames):
            try:
                self._connect_and_run_deployment_script(
                    task=kwargs['deploy'], node=node,
                    ssh_hostname=ip_addresses[0], ssh_port=ssh_port,
                    ssh_username=username, ssh_password=password,
                    ssh_key_file=ssh_key_file, ssh_timeout=ssh_timeout,
                    timeout=timeout, max_tries=max_tries)
            except Exception:
                # Try alternate username
                # Todo: Need to fix paramiko so we can catch a more specific
                # exception
                e = sys.exc_info()[1]
                deploy_error = e
            else:
                # Script sucesfully executed, don't try alternate username
                deploy_error = None
                break

        if deploy_error is not None:
            raise DeploymentError(node=node, original_exception=deploy_error,
                                  driver=self)

        return node

    def create_volume(self, size, name, location=None, snapshot=None):
        """
        Create a new volume.

        :param size: Size of volume in gigabytes (required)
        :type size: ``int``

        :param name: Name of the volume to be created
        :type name: ``str``

        :param location: Which data center to create a volume in. If
                               empty, undefined behavoir will be selected.
                               (optional)
        :type location: :class:`NodeLocation`

        :param snapshot:  Name of snapshot from which to create the new
                               volume.  (optional)
        :type snapshot:  ``str``

        :return: The newly created volume.
        :rtype: :class:`StorageVolume`
        """
        raise NotImplementedError(
            'create_volume not implemented for this driver')

    def destroy_volume(self, volume):
        """
        Destroys a storage volume.

        :param volume: Volume to be destroyed
        :type volume: :class:`StorageVolume`

        :rtype: ``bool``
        """

        raise NotImplementedError(
            'destroy_volume not implemented for this driver')

    def attach_volume(self, node, volume, device=None):
        """
        Attaches volume to node.

        :param Node node: Node to attach volume to.
        :param StorageVolume volume: Volume to attach.
        :param str device: Where the device is exposed, e.g. '/dev/sdb'

        :return bool:
        """
        raise NotImplementedError('attach not implemented for this driver')

    def detach_volume(self, volume):
        """
        Detaches a volume from a node.

        :param StorageVolume volume: Volume to be detached
        :return bool:
        """

        raise NotImplementedError('detach not implemented for this driver')

    def list_volumes(self):
        """
        List storage volumes.

        :return [StorageVolume]:
        """
        raise NotImplementedError(
            'list_volumes not implemented for this driver')

    def list_volume_snapshots(self, volume):
        """
        List snapshots for a storage volume.

        :rtype: ``list`` of :class:`VolumeSnapshot`
        """
        raise NotImplementedError(
            'list_volume_snapshots not implemented for this driver')

    def create_volume_snapshot(self, volume, name):
        """
        Creates a snapshot of the storage volume.

        :rtype: :class:`VolumeSnapshot`
        """
        raise NotImplementedError(
            'create_volume_snapshot not implemented for this driver')

    def destroy_volume_snapshot(self, snapshot):
        """
        Destroys a snapshot.

        :rtype: :class:`bool`
        """
        raise NotImplementedError(
            'destroy_volume_snapshot not implemented for this driver')

    def _wait_until_running(self, node, wait_period=3, timeout=600,
                            ssh_interface='public_ips', force_ipv4=True):
        # This is here for backward compatibility and will be removed in the
        # next major release
        return self.wait_until_running(nodes=[node], wait_period=wait_period,
                                       timeout=timeout,
                                       ssh_interface=ssh_interface,
                                       force_ipv4=force_ipv4)

    def wait_until_running(self, nodes, wait_period=3, timeout=600,
                           ssh_interface='public_ips', force_ipv4=True):
        """
        Block until the given nodes are fully booted and have an IP address
        assigned.

        :param nodes: list of node instances.
        :type nodes: ``List`` of :class:`Node`

        :param wait_period: How many seconds to between each loop
                                 iteration (default is 3)
        :type wait_period: ``int``

        :param timeout: How many seconds to wait before timing out
                             (default is 600)
        :type timeout: ``int``

        :param ssh_interface: The interface to wait for.
                                   Default is 'public_ips', other option is
                                   'private_ips'.
        :type ssh_interface: ``str``

        :param force_ipv4: Ignore ipv6 IP addresses (default is True).
        :type force_ipv4: ``bool``

        :return: ``[(Node, ip_addresses)]`` list of tuple of Node instance and
                 list of ip_address on success.
        :rtype: ``list`` of ``tuple``
        """
        def is_supported(address):
            """Return True for supported address"""
            if force_ipv4 and not is_valid_ip_address(address=address,
                                                      family=socket.AF_INET):
                return False
            return True

        def filter_addresses(addresses):
            """Return list of supported addresses"""
            return [a for a in addresses if is_supported(a)]

        start = time.time()
        end = start + timeout

        if ssh_interface not in ['public_ips', 'private_ips']:
            raise ValueError('ssh_interface argument must either be' +
                             'public_ips or private_ips')

        uuids = set([n.uuid for n in nodes])
        while time.time() < end:
            nodes = self.list_nodes()
            nodes = list([n for n in nodes if n.uuid in uuids])

            if len(nodes) > len(uuids):
                found_uuids = [n.uuid for n in nodes]
                msg = ('Unable to match specified uuids ' +
                       '(%s) with existing nodes. Found ' % (uuids) +
                       'multiple nodes with same uuid: (%s)' % (found_uuids))
                raise LibcloudError(value=msg, driver=self)

            running_nodes = [n for n in nodes if n.state == NodeState.RUNNING]
            addresses = [filter_addresses(getattr(n, ssh_interface)) for n in
                         running_nodes]
            if len(running_nodes) == len(uuids) == len(addresses):
                return list(zip(running_nodes, addresses))
            else:
                time.sleep(wait_period)
                continue

        raise LibcloudError(value='Timed out after %s seconds' % (timeout),
                            driver=self)

    def _ssh_client_connect(self, ssh_client, wait_period=1.5, timeout=300):
        """
        Try to connect to the remote SSH server. If a connection times out or
        is refused it is retried up to timeout number of seconds.

        :param ssh_client: A configured SSHClient instance
        :type ssh_client: ``SSHClient``

        :param wait_period: How many seconds to wait between each loop
                                 iteration (default is 1.5)
        :type wait_period: ``int``

        :param timeout: How many seconds to wait before timing out
                             (default is 600)
        :type timeout: ``int``

        :return: ``SSHClient`` on success
        """
        start = time.time()
        end = start + timeout

        while time.time() < end:
            try:
                ssh_client.connect()
            except (IOError, socket.gaierror, socket.error):
                # Retry if a connection is refused or timeout
                # occurred
                ssh_client.close()
                time.sleep(wait_period)
                continue
            else:
                return ssh_client

        raise LibcloudError(value='Could not connect to the remote SSH ' +
                            'server. Giving up.', driver=self)

    def _connect_and_run_deployment_script(self, task, node, ssh_hostname,
                                           ssh_port, ssh_username,
                                           ssh_password, ssh_key_file,
                                           ssh_timeout, timeout, max_tries):
        ssh_client = SSHClient(hostname=ssh_hostname,
                               port=ssh_port, username=ssh_username,
                               password=ssh_password,
                               key=ssh_key_file,
                               timeout=ssh_timeout)

        # Connect to the SSH server running on the node
        ssh_client = self._ssh_client_connect(ssh_client=ssh_client,
                                              timeout=timeout)

        # Execute the deployment task
        self._run_deployment_script(task=task, node=node,
                                    ssh_client=ssh_client,
                                    max_tries=max_tries)

    def _run_deployment_script(self, task, node, ssh_client, max_tries=3):
        """
        Run the deployment script on the provided node. At this point it is
        assumed that SSH connection has already been established.

        :param task: Deployment task to run on the node.
        :type task: ``Deployment``

        :param node: Node to operate one
        :type node: ``Node``

        :param ssh_client: A configured and connected SSHClient instance
        :type ssh_client: ``SSHClient``

        :param max_tries: How many times to retry if a deployment fails
                               before giving up (default is 3)
        :type max_tries: ``int``

        :return: ``Node`` Node instance on success.
        """
        tries = 0
        while tries < max_tries:
            try:
                node = task.run(node, ssh_client)
            except Exception:
                e = sys.exc_info()[1]
                tries += 1
                if tries >= max_tries:
                    e = sys.exc_info()[1]
                    raise LibcloudError(value='Failed after %d tries: %s'
                                        % (max_tries, str(e)), driver=self)
            else:
                ssh_client.close()
                return node

    def _get_size_price(self, size_id):
        return get_size_price(driver_type='compute',
                              driver_name=self.api_name,
                              size_id=size_id)


def is_private_subnet(ip):
    """
    Utility function to check if an IP address is inside a private subnet.

    :type ip: ``str``
    :param ip: IP address to check

    :return: ``bool`` if the specified IP address is private.
    """
    priv_subnets = [{'subnet': '10.0.0.0', 'mask': '255.0.0.0'},
                    {'subnet': '172.16.0.0', 'mask': '255.240.0.0'},
                    {'subnet': '192.168.0.0', 'mask': '255.255.0.0'}]

    ip = struct.unpack('I', socket.inet_aton(ip))[0]

    for network in priv_subnets:
        subnet = struct.unpack('I', socket.inet_aton(network['subnet']))[0]
        mask = struct.unpack('I', socket.inet_aton(network['mask']))[0]

        if (ip & mask) == (subnet & mask):
            return True

    return False


def is_valid_ip_address(address, family=socket.AF_INET):
    """
    Check if the provided address is valid IPv4 or IPv6 adddress.

    :return: ``bool`` True if the provided address is valid.
    """
    try:
        socket.inet_pton(family, address)
    except socket.error:
        return False
    return True


if __name__ == "__main__":
    import doctest
    doctest.testmod()
