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

import base64
import re
import os

import collections

try:
    import simplejson as json
except Exception:
    import json

from libcloud.utils.py3 import httplib
from libcloud.utils.py3 import b

from libcloud.common.base import JsonResponse, ConnectionUserAndKey
from libcloud.common.base import KeyCertificateConnection
from libcloud.common.types import InvalidCredsError

from libcloud.container.base import (Container, ContainerDriver,
                                     ContainerImage)
from libcloud.common.exceptions import BaseHTTPError

from libcloud.compute.base import StorageVolume

from libcloud.container.providers import Provider
from libcloud.container.types import ContainerState

# Acceptable success strings comping from LXD API
LXD_API_SUCCESS_STATUS = ['Success']
LXD_API_STATE_ACTIONS = ['stop', 'start', 'restart', 'freeze', 'unfreeze']
LXD_API_IMAGE_SOURCE_TYPE = ["image", "migration", "copy", "none"]

# the wording used by LXD to indicate that an error
# occurred for a request
LXD_ERROR_STATUS_RESP = 'error'


# helpers
def strip_http_prefix(host):
    # strip the prefix
    prefixes = ['http://', 'https://']
    for prefix in prefixes:
        if host.startswith(prefix):
            host = host.strip(prefix)
    return host


def check_certificates(key_file, cert_file, **kwargs):
    """
    Basic checks for the provided certificates in LXDtlsConnection
    """

    # there is no point attempting to connect if either is missing
    if key_file is None or cert_file is None:
        raise InvalidCredsError("TLS Connection requires specification "
                                "of a key file and a certificate file")

    # if they are not none they may be empty strings
    # or certificates that are not appropriate
    if key_file == '' or cert_file == '':
        raise InvalidCredsError("TLS Connection requires specification "
                                "of a key file and a certificate file")

    # if none of the above check the types
    if 'key_files_allowed' in kwargs.keys():
        key_file_suffix = key_file.split('.')

        if key_file_suffix[-1] not in kwargs['key_files_allowed']:
            raise InvalidCredsError("Valid key files are: " +
                                    str(kwargs['key_files_allowed']) +
                                    "you provided: " + key_file_suffix[-1])

            # if none of the above check the types
    if 'cert_files_allowed' in kwargs.keys():
        cert_file_suffix = cert_file.split('.')

        if cert_file_suffix[-1] not in kwargs['cert_files_allowed']:
            raise InvalidCredsError("Valid certification files are: " +
                                    str(kwargs['cert_files_allowed']) +
                                    "you provided: " + cert_file_suffix[-1])

    # if all these are good check the paths
    keypath = os.path.expanduser(key_file)
    is_file_path = os.path.exists(keypath) and os.path.isfile(keypath)
    if not is_file_path:
        raise InvalidCredsError('You need a key file to authenticate with '
                                'LXD tls. This can be found in the server.')

    certpath = os.path.expanduser(cert_file)
    is_file_path = os.path.exists(certpath) and os.path.isfile(certpath)
    if not is_file_path:
        raise InvalidCredsError('You need a certificate file to '
                                'authenticate with LXD tls. '
                                'This can be found in the server.')


def assert_response(response_dict, status_code):
    """
    Basic checks that the response is of the type
    the client is expecting
    """

    # if the type of the response is an error
    if response_dict['type'] == LXD_ERROR_STATUS_RESP:
        # an error returned
        raise LXDAPIException(message="response type is error",
                              response_dict=response_dict)

    # anything else apart from the status_code given should be treated as error
    if response_dict['status_code'] != status_code:
        # we have an unknown error
        msg = "Status code should be {0}\
         but is {1}".format(status_code, response_dict['status_code'])
        raise LXDAPIException(message=msg,
                              response_dict=response_dict)


class LXDAPIException(Exception):
    """
    Basic exception to be thrown when LXD API
    returns with some kind of error
    """

    def __init__(self, message="Unknown Error Occurred", response_dict=None):
        self.message = message
        self.response_dict = response_dict

        super(LXDAPIException, self).__init__(message)

    def __str__(self):
        return self.message


class LXDStoragePool(object):
    """
    Utility class representing an LXD storage pool
    https://lxd.readthedocs.io/en/latest/storage/
    """
    def __init__(self, name, driver, used_by, config, managed):

        # the name of the storage pool
        self.name = name

        # the driver (or type of storage pool). e.g. ‘zfs’ or ‘btrfs’, etc.
        self.driver = driver

        # which containers (by API endpoint /1.0/containers/<name>)
        # are using this storage-pool.
        self.used_by = used_by

        # a dictionary with some information about the storage-pool.
        # e.g. size, source (path), volume.size, etc.
        self.config = config

        # Boolean that indicates whether LXD manages the pool or not.
        self.managed = managed


class LXDServerInfo(object):
    """
    Wraps the response form /1.0
    """

    @classmethod
    def build_from_response(cls, metadata):

        server_info = LXDServerInfo()
        server_info.api_extensions = metadata.get("api_extensions", None)
        server_info.api_status = metadata.get("api_status", None)
        server_info.api_version = metadata.get("api_version", None)
        server_info.auth = metadata.get("auth", None)
        server_info.config = metadata.get("config", None)
        server_info.environment = metadata.get("environment", None)
        server_info.public = metadata.get("public", None)
        return server_info

    def __init__(self):

        # List of API extensions added after
        # the API was marked stable
        self.api_extensions = None

        # API implementation status
        # (one of, development, stable or deprecated)
        self.api_status = None

        # The API version as a string
        self.api_version = None

        # Authentication state,
        # one of "guest", "untrusted" or "trusted"
        self.auth = None

        self.config = None

        # Various information about the host (OS, kernel, ...)
        self.environment = None

        self.public = None

    def __str__(self):
        return str(self.api_extensions) + str(self.api_status) + \
            str(self.api_version) + str(self.auth) + str(self.config) + \
            str(self.environment) + \
            str(self.public)


LXDContainerExecuteResult = collections.namedtuple('LXDContainerExecuteResult',
                                                   ['uuid',
                                                    'secret_0',
                                                    'secret_1',
                                                    'secret_2',
                                                    'control',
                                                    'output',
                                                    'result'])


class LXDResponse(JsonResponse):
    valid_response_codes = [httplib.OK, httplib.ACCEPTED, httplib.CREATED,
                            httplib.NO_CONTENT]

    def parse_body(self):

        if len(self.body) == 0 and not self.parse_zero_length_body:
            return self.body

        try:
            content_type = self.headers.get('content-type', 'application/json')
            if content_type == 'application/json' or content_type == '':
                if self.headers.get('transfer-encoding') == 'chunked' and \
                        'fromImage' in self.request.url:
                    body = [json.loads(chunk) for chunk in
                            self.body.strip().replace('\r', '').split('\n')]
                else:
                    body = json.loads(self.body)
            else:
                body = self.body
        except ValueError:
            m = re.search('Error: (.+?)"', self.body)
            if m:
                error_msg = m.group(1)
                raise Exception(error_msg)
            else:
                msg = ('ConnectionError: Failed to parse JSON response '
                       '(body=%s)' % (self.body))
                raise Exception(msg)
        return body

    def parse_error(self):
        if self.status == 401:
            raise InvalidCredsError('Invalid credentials')
        return self.body

    def success(self):
        return self.status in self.valid_response_codes


class LXDConnection(ConnectionUserAndKey):
    responseCls = LXDResponse
    timeout = 60

    def add_default_headers(self, headers):
        """
        Add parameters that are necessary for every request
        If user and password are specified, include a base http auth
        header
        """
        headers['Content-Type'] = 'application/json'
        if self.user_id and self.key:
            user_b64 = base64.b64encode(b('%s:%s' % (self.user_id, self.key)))
            headers['Authorization'] = 'Basic %s' % (user_b64.decode('utf-8'))
        return headers


class LXDtlsConnection(KeyCertificateConnection):

    responseCls = LXDResponse

    def __init__(self, key, secret, secure=True,
                 host='localhost', port=8443, ca_cert='',
                 key_file=None, cert_file=None,
                 certificate_validator=None, **kwargs):

        if certificate_validator is not None:
            certificate_validator(key_file=key_file, cert_file=cert_file)
        else:
            check_certificates(key_file=key_file,
                               cert_file=cert_file, **kwargs)

        super(LXDtlsConnection, self).__init__(key_file=key_file,
                                               cert_file=cert_file,
                                               secure=secure, host=host,
                                               port=port, url=None,
                                               proxy_url=None,
                                               timeout=None, backoff=None,
                                               retry_delay=None)

        self.key_file = key_file
        self.cert_file = cert_file

    def add_default_headers(self, headers):
        headers['Content-Type'] = 'application/json'
        return headers


class LXDContainerDriver(ContainerDriver):
    """
    Driver for LXD REST API of LXC containers
    https://lxd.readthedocs.io/en/stable-2.0/rest-api/
    https://github.com/lxc/lxd/blob/master/doc/rest-api.md
    """
    type = Provider.LXD
    name = 'LXD'
    website = 'https://linuxcontainers.org/'
    connectionCls = LXDConnection

    # LXD supports clustering but still the functionality
    # is not implemented yet on our side
    supports_clusters = False
    version = '1.0'
    default_time_out = 30

    # default configuration when creating a container
    # if the architecture is not specified
    # by the client code then the underlying
    # host architecture should be picked up by
    # LXC.
    default_architecture = ''
    default_profiles = 'default'

    # An ephemeral container means that it
    # will be restroyed once it is stopped
    default_ephemeral = False

    def __init__(self, key='', secret='', secure=False,
                 host='localhost', port=8443, key_file=None,
                 cert_file=None, ca_cert=None,
                 certificate_validator=check_certificates):

        if key_file:

            if not cert_file:
                # LXD tls authentication-
                # We pass two files, a key_file with the
                # private key and cert_file with the certificate
                # libcloud will handle them through LibcloudHTTPSConnection

                raise LXDAPIException(message='Need both private key and'
                                              ' certificate files for '
                                              'tls authentication')

            self.connectionCls = LXDtlsConnection
            self.key_file = key_file
            self.cert_file = cert_file
            self.certificate_validator = certificate_validator
            secure = True

        if host.startswith('https://'):
            secure = True

        host = strip_http_prefix(host=host)

        super(LXDContainerDriver, self).__init__(key=key, secret=secret,
                                                 secure=secure, host=host,
                                                 port=port,
                                                 key_file=key_file,
                                                 cert_file=cert_file)

        if ca_cert:
            self.connection.connection.ca_cert = ca_cert
        else:
            # do not verify SSL certificate
            self.connection.connection.ca_cert = False

        self.connection.secure = secure
        self.connection.host = host
        self.connection.port = port
        self.version = self._get_api_version()

    def ex_get_api_endpoints(self):
        """
        Description: List of supported APIs
        Authentication: guest
        Operation: sync
        Return: list of supported API endpoint URLs

        """
        response = self.connection.request("/")
        response_dict = response.parse_body()
        assert_response(response_dict=response_dict, status_code=200)
        return response_dict["metadata"]

    def ex_get_server_configuration(self):
        """

        Description: Server configuration and environment information
        Authentication: guest, untrusted or trusted
        Operation: sync
        Return: Dict representing server state

        The returned configuration depends on whether the connection
        is trusted or not
        :rtype: :class: .LXDServerInfo

        """
        response = self.connection.request("/%s" % (self.version))
        response_dict = response.parse_body()
        assert_response(response_dict=response_dict, status_code=200)
        meta = response_dict["metadata"]
        return LXDServerInfo.build_from_response(metadata=meta)

    def deploy_container(self, name, image, cluster=None,
                         parameters=None, start=True,
                         ex_architecture=default_architecture,
                         ex_profiles=None,
                         ex_ephemeral=default_ephemeral,
                         ex_config=None, ex_devices=None,
                         ex_instance_type=None):

        """
        Create a new container
        Authentication: trusted
        Operation: async

        :param name: The name of the new container.
        64 chars max, ASCII, no slash, no colon and no comma
        :type  name: ``str``

        :param image: The container image to deploy. Currently not used
        :type  image: :class:`.ContainerImage`

        :param cluster: The cluster to deploy to, None is default
        :type  cluster: :class:`.ContainerCluster`

        :param parameters: Container Image parameters.
        This parameter should represent the
        the ``source`` dictioanry expected by the  LXD API call. For more
        information how this parameter should be structured see
        https://github.com/lxc/lxd/blob/master/doc/rest-api.md
        :type  parameters: ``str``

        :param start: Start the container on deployment. True is the default
        :type  start: ``bool``

        :param ex_architecture: string e.g. x86_64
        :type  ex_architecture: ``str``

        :param ex_profiles: List of profiles
        :type  ex_profiles: ``list``

        :param ex_ephemeral: Whether to destroy the container on shutdown
        :type  ex_ephemeral: ``bool``

        :param ex_config: Config override e.g.  {"limits.cpu": "2"}
        :type  ex_config: ``dict``

        :param ex_devices: optional list of devices the container should have
        :type  ex_devices: ``dict``

        :param ex_instance_type: An optional instance type
        to use as basis for limits e.g. "c2.micro"
        :type  ex_instance_type: ``str``

        :rtype: :class:`libcloud.container.base.Container`
        """
        cont_params = \
            LXDContainerDriver._fix_cont_params(architecture=ex_architecture,
                                                profiles=ex_profiles,
                                                ephemeral=ex_profiles,
                                                config=ex_config,
                                                devices=ex_devices,
                                                instance_type=ex_instance_type)

        if parameters:
            parameters = json.loads(parameters)

        container = self._deploy_container_from_image(name=name, image=image,
                                                      parameters=parameters,
                                                      cont_params=cont_params)

        if start:
            container.start()

        return container

    def get_container(self, id, ex_get_ip_addr=True):

        """
        Get a container by ID

        :param id: The ID of the container to get
        :type  id: ``str``

        :param ex_get_ip_addr: Indicates whether ip addresses
        should also be included. This requires an extra GET request
        :type  ex_get_ip_addr: ``boolean```

        :rtype: :class:`libcloud.container.base.Container`
        """
        req = "/%s/containers/%s" % (self.version, id)
        response = self.connection.request(req)
        result_dict = response.parse_body()
        assert_response(response_dict=result_dict, status_code=200)

        metadata = result_dict["metadata"]

        ips = []
        if ex_get_ip_addr:
            req = "/%s/containers/%s/state" % (self.version, id)
            ip_response = self.connection.request(req)

            ip_result_dict = ip_response.parse_body()
            assert_response(response_dict=ip_result_dict, status_code=200)

            if ip_result_dict["metadata"]["network"] is not None:
                networks = ip_result_dict["metadata"]["network"]["eth0"]

                # the list of addresses
                addresses = networks["addresses"]

                for item in addresses:
                    ips.append(item["address"])

        metadata.update({"ips": ips})
        return self._to_container(metadata=metadata)

    def start_container(self, container, ex_timeout=default_time_out,
                        ex_force=True, ex_stateful=True):
        """
        Start a container

        :param container: The container to start
        :type  container: :class:`libcloud.container.base.Container`

        :param ex_timeout: Time to wait for the operation to complete
        :type  ex_timeout: ``int``

        :param ex_force:
        :type  ex_force: ``boolean``

        :param ex_stateful:
        :type  ex_stateful: ``boolean``

        :rtype: :class:`libcloud.container.base.Container`
        """
        return self._do_container_action(container=container, action='start',
                                         timeout=ex_timeout,
                                         force=ex_force, stateful=ex_stateful)

    def stop_container(self, container, ex_timeout=default_time_out,
                       ex_force=True, ex_stateful=True):
        """
        Stop the given container

        :param container: The container to be stopped
        :type  container: :class:`libcloud.container.base.Container`

        :param ex_timeout: Time to wait for the operation to complete
        :type  ex_timeout: ``int``

        :param ex_force:
        :type  ex_force: ``boolean``

        :param ex_stateful:
        :type  ex_stateful: ``boolean``

        :rtype: :class:`libcloud.container.base.Container
        """
        return self._do_container_action(container=container, action='stop',
                                         timeout=ex_timeout,
                                         force=ex_force, stateful=ex_stateful)

    def restart_container(self, container, ex_timeout=default_time_out,
                          ex_force=True, ex_stateful=True):
        """
        Restart a deployed container

        :param container: The container to restart
        :type  container: :class:`.Container`

        :param ex_timeout: Time to wait for the operation to complete
        :type  ex_timeout: ``int``

        :param ex_force:
        :type  ex_force: ``boolean``

        :param ex_stateful:
        :type  ex_stateful: ``boolean``

        :rtype: :class:`libcloud.container.base.Container
        """
        return self._do_container_action(container=container, action='restart',
                                         timeout=ex_timeout,
                                         force=ex_force, stateful=ex_stateful)

    def ex_freeze_container(self, container, ex_timeout=default_time_out):

        """
        Set the given container into a freeze state

        :param container: The container to restart
        :type  container: :class:`.Container`

        :param ex_timeout: Time to wait for the operation to complete
        :type  ex_timeout: ``int``

        :rtype :class: `libcloud.container.base.Container
        """

        return self._do_container_action(container=container,
                                         action='freeze',
                                         timeout=ex_timeout,
                                         force=True, stateful=True)

    def ex_unfreeze_container(self, container, ex_timeout=default_time_out):

        """
        Set the given container into  unfreeze state

        :param container: The container to restart
        :type  container: :class:`.Container`

        :param ex_timeout: Time to wait for the operation to complete
        :type  ex_timeout: ``int``

        :rtype :class: `libcloud.container.base.Container
        """

        return self._do_container_action(container=container,
                                         action='unfreeze',
                                         timeout=ex_timeout,
                                         force=True, stateful=True)

    def destroy_container(self, container, ex_timeout=default_time_out):
        """
        Destroy a deployed container. Raises and exception
        if he container is running

        :param container: The container to destroy
        :type  container: :class:`.Container`

        :param ex_timeout: Time to wait for the operation to complete
        :type  ex_timeout ``int``

        :rtype: :class:`libcloud.container.base.Container
        """

        # Return: background operation or standard error
        req = '/%s/containers/%s' % (self.version, container.name)
        response = self.connection.request(req, method='DELETE')

        response_dict = response.parse_body()
        assert_response(response_dict=response_dict, status_code=100)

        try:

            # wait until the timeout...but util getting here the operation
            # may have finished already
            id = response_dict['metadata']['id']
            req = '/%s/operations/%s/wait?timeout=%s' % (self.version,
                                                         id,
                                                         ex_timeout)
            response = self.connection.request(req)
        except BaseHTTPError as e:

            message_list = e.message.split(",")
            message = message_list[0].split(":")[-1]

            # if not found assume the operation completed
            if message != '"not found"':
                # something is wrong
                raise LXDAPIException(message=e.message)

        response_dict = response.parse_body()
        assert_response(response_dict=response_dict, status_code=200)

        # return a dummy container
        container = Container(driver=self, name=container.name,
                              id=container.name,
                              state=ContainerState.TERMINATED,
                              image=None, ip_addresses=[],
                              extra=None)
        return container

    def ex_execute_cmd_on_container(self, cont_id, command, **config):
        """
        Description: run a remote command
        Operation: async

        Return: Depends on the  the configuration

        if wait-for-websocket=true and interactive=false
        returns a LXDContainerExecuteResult with:
            uuid=uuid,
            secret_0=fds["0"],
            secret_1=fds["1"],
            secret_2=fds["2"],
            control=fds["control"],
            output={}, result=None

        if wait-for-websocket=true and interactive=true
        returns a LXDContainerExecuteResult with:
            uuid=uuid,
            secret_0=fds["0"],
            secret_1=None,
            secret_2=None,
            control=fds["control"],
            output={}, result=None

        if interactive=false and record-output=true
        returns a LXDContainerExecuteResult with:
            uuid=uuid,
            secret_0=None,
            secret_1=None,
            secret_2=None,
            control=None,
            output=output, result=result

        if none of the above it assumes that the command has
        been executed and returns LXDContainerExecuteResult with:
            uuid=uuid,
            secret_0=None,
            secret_1=None,
            secret_2=None,
            control=None,
            output=None, result=result


        in all the above uuid is the operation id

        :param cont_id: The container name to run the commands
        ":type cont_id: ``str``

        :param command: a list of strings indicating the commands
        and their arguments e.g: ["/bin/bash ls -l"]
        :type  command ``list``

        :param config: Dict with extra arguments.

            For example:

            width:  Initial width of the terminal default 80
            height: Initial height of the terminal default 25
            user:   User to run the command as default 1000
            group: Group to run the  command as default 1000
            cwd: Current working directory default /tmp

            wait-for-websocket: Whether to wait for a connection
            before starting the process. Default False

            record-output: Whether to store stdout and stderr
            (only valid with wait-for-websocket=false)
            (requires API extension container_exec_recording). Default False

            interactive: Whether to allocate a pts device
            instead of PIPEs. Default true

        :type config ``dict``

        :rtype LXDContainerExecuteResult
        """

        input = {"command": command}
        input = LXDContainerDriver._create_exec_configuration(input, **config)
        data = json.dumps(input)
        req = "/%s/containers/%s/exec" % (self.version, cont_id)

        # Return: background operation +
        # optional websocket information or standard error
        response = self.connection.request(req, method="POST", data=data)

        response_dict = response.parse_body()
        assert_response(response_dict=response_dict, status_code=100)

        fds = response_dict['metadata']['metadata']['fds']
        uuid = response_dict['metadata']['id']

        if input["wait-for-websocket"] is True and\
                input["interactive"] is False:
            return LXDContainerExecuteResult(uuid=uuid,
                                             secret_0=fds["0"],
                                             secret_1=fds["1"],
                                             secret_2=fds["2"],
                                             control=fds["control"],
                                             output={}, result=None)

        elif input["wait-for-websocket"] is True and\
                input["interactive"] is True:

            return LXDContainerExecuteResult(uuid=uuid,
                                             secret_0=fds["0"],
                                             secret_1=None,
                                             secret_2=None,
                                             control=fds["control"],
                                             output={}, result=None)

        elif input["interactive"] is False and\
                input["record-output"] is True:

            output = response_dict['metadata']['metadata']['output']
            result = response_dict['metadata']['metadata']['result']
            return LXDContainerExecuteResult(uuid=uuid,
                                             secret_0=None,
                                             secret_1=None,
                                             secret_2=None,
                                             control=None,
                                             output=output, result=result)

        else:

            result = response_dict['metadata']['metadata']['result']
            return LXDContainerExecuteResult(uuid=uuid,
                                             secret_0=None,
                                             secret_1=None,
                                             secret_2=None,
                                             control=None,
                                             output={}, result=result)

    def list_containers(self, image=None, cluster=None, ex_detailed=True):
        """
        List the deployed container images

        :param image: Filter to containers with a certain image
        :type  image: :class:`.ContainerImage`

        :param cluster: Filter to containers in a cluster
        :type  cluster: :class:`.ContainerCluster`

        :param ex_detailed: Flag indicating whether detail info
        of the containers is required. This will cause a
        GET request for every container present in the
        host. Default is True
        :type ex_detailed: ``bool``

        :rtype: ``list`` of :class:`libcloud.container.base.Container
        """

        result = self.connection.request('/%s/containers' % self.version)
        result = result.parse_body()

        # how to treat the errors????
        assert_response(response_dict=result, status_code=200)

        meta = result['metadata']
        containers = []
        for item in meta:
            container_id = item.split('/')[-1]
            if not ex_detailed:

                container = Container(driver=self, name=container_id,
                                      state=ContainerState.UNKNOWN,
                                      id=container_id,
                                      image=image, ip_addresses=[],
                                      extra={})
            else:
                container = self.get_container(id=container_id)
            containers.append(container)

        return containers

    def ex_get_image(self, fingerprint):
        """
        Returns a container image from the given image fingerprint

        :param fingerprint: image fingerprint
        :type  fingerprint: ``str``

        :rtype: :class:`.ContainerImage`
        """
        req = '/%s/images/%s' % (self.version, fingerprint)
        response = self.connection.request(req)

        #  parse the LXDResponse into a dictionary
        response_dict = response.parse_body()
        assert_response(response_dict=response_dict, status_code=200)

        return self._to_image(metadata=response_dict['metadata'])

    def install_image(self, path, ex_timeout=default_time_out,
                      **ex_img_data):

        """
        Install a container image from a remote path. Not that the
        path currently is not used. Image data should be provided
        int the ex_img_data under the key 'image_data'. Creating
        an image in LXD is an asynchronous operation

        :param path: Path to the container image
        :type  path: ``str``

        :param ex_timeout: Time to wait before signaling timeout
        :type  ex_timeout: ``int``

        :param ex_img_data: Dictionary describing the image data
        :type  ex_img_data: ``dict``

        :rtype: :class:`.ContainerImage`
        """

        if not ex_img_data:
            msg = "Install an image for LXD requires " \
                  "specification of image_data"
            raise LXDAPIException(message=msg)

        # Return: background operation or standard error
        data = ex_img_data['image_data']
        response = self.connection.request('/%s/images' % (self.version),
                                           method='POST', json=data)

        response_dict = response.parse_body()
        # a background operation is expected
        # to be returned status_code = 100 --> Operation created
        assert_response(response_dict=response_dict, status_code=100)

        try:

            # wait until the timeout...but util getting here the operation
            # may have finished already
            id = response_dict['metadata']['id']
            req = '/%s/operations/%s/wait?timeout=%s' % (self.version,
                                                         id,
                                                         ex_timeout)
            response = self.connection.request(req)
        except BaseHTTPError as e:

            message_list = e.message.split(",")
            message = message_list[0].split(":")[-1]

            # if not found assume the operation completed
            if message != '"not found"':
                # something is wrong
                raise LXDAPIException(message=e.message)

        response_dict = response.parse_body()
        assert_response(response_dict=response_dict, status_code=200)
        return self._to_image(metadata=response_dict['metadata'])

    def list_images(self):
        """
        List of URLs for images the server is publishing

        :rtype: ``list`` of :class:`.ContainerImage`
        """
        response = self.connection.request('/%s/images' % (self.version))

        #  parse the LXDResponse into a dictionary
        response_dict = response.parse_body()

        assert_response(response_dict=response_dict, status_code=200)

        metadata = response_dict['metadata']
        images = []

        for image in metadata:
            fingerprint = image.split("/")[-1]
            images.append(self.ex_get_image(fingerprint=fingerprint))
        return images

    def ex_list_storage_pools(self, detailed=True):
        """
        Returns a list of storage pools defined currently defined on the host

        Description: list of storage pools
        Authentication: trusted
        Operation: sync

        ":rtype: list of StoragePool items
        """

        # Return: list of storage pools that are currently defined on the host
        response = self.connection.request("/%s/storage-pools" % self.version)

        response_dict = response.parse_body()
        assert_response(response_dict=response_dict, status_code=200)

        pools = []
        for pool_item in response_dict['metadata']:
            pool_name = pool_item.split('/')[-1]

            if not detailed:
                # attempt to create a minimal StoragePool
                pools.append(self._to_storage_pool({"name": pool_name,
                                                    "driver": None,
                                                    "used_by": None,
                                                    "config": None,
                                                    "managed": None}))
            else:
                pools.append(self.ex_get_storage_pool(id=pool_name))

        return pools

    def ex_get_storage_pool(self, id):
        """
        Returns  information about a storage pool
        :param id: the name of the storage pool
        :rtype: :class: StoragePool
        """

        # Return: dict representing a storage pool
        req = "/%s/storage-pools/%s" % (self.version, id)
        response = self.connection.request(req)

        response_dict = response.parse_body()
        assert_response(response_dict=response_dict, status_code=200)

        if not response_dict['metadata']:
            msg = "Storage pool with name {0} has no data".format(id)
            raise LXDAPIException(message=msg)

        return self._to_storage_pool(data=response_dict['metadata'])

    def ex_create_storage_pool(self, definition):

        """
        Create a storage_pool from definition.

        Implements POST /1.0/storage-pools

        The `definition` parameter defines
        what the storage pool will be.  An
        example config for the zfs driver is:

                   {
                       "config": {
                           "size": "10GB"
                       },
                       "driver": "zfs",
                       "name": "pool1"
                   }

        Note that **all** fields in the `definition` parameter are strings.
        Note that size has to be at least 64M in order to create the pool

        For further details on the storage pool types see:
        https://lxd.readthedocs.io/en/latest/storage/

        The function returns the a `StoragePool` instance, if it is
        successfully created, otherwise an LXDAPIException is raised.

        :param definition: the fields to pass to the LXD API endpoint
        :type definition: dict

        :returns: a storage pool if successful,
        raises NotFound if not found
        :rtype: :class:`StoragePool`

        :raises: :class:`LXDAPIExtensionNotAvailable`
        if the 'storage' api extension is missing.
        :raises: :class:`LXDAPIException`
        if the storage pool couldn't be created.
        """

        if not definition:
            raise LXDAPIException("Cannot create a storage pool "
                                  " without a definition")

        data = json.dumps(definition)

        # Return: standard return value or standard error
        response = self.connection.request("/%s/storage-pools" % self.version,
                                           method='POST', data=data)

        response_dict = response.parse_body()
        assert_response(response_dict=response_dict, status_code=200)

        return self.ex_get_storage_pool(id=definition["name"])

    def ex_delete_storage_pool(self, id):
        """Delete the storage pool.

        Implements DELETE /1.0/storage-pools/<self.name>

        Deleting a storage pool may fail if it is being used.  See the LXD
        documentation for further details.

        :raises: :class:`LXDAPIException` if the storage pool can't be deleted.
        """

        # Return: standard return value or standard error
        req = "/%s/storage-pools/%s" % (self.version, id)
        response = self.connection.request(req, method='DELETE')

        response_dict = response.parse_body()
        assert_response(response_dict=response_dict, status_code=200)

    def ex_list_storage_pool_volumes(self, pool_id, detailed=True):
        """
        Description: list of storage volumes
        associated with the given storage pool

        :param pool_id: the id of the storage pool to query
        :param detailed: boolean flag.
        If True extra API calls are made to fill in the missing details
                                       of the storage volumes

        Authentication: trusted
        Operation: sync
        Return: list of storage volumes that
        currently exist on a given storage pool

        :rtype: A list of :class: StorageVolume
        """

        req = "/%s/storage-pools/%s/volumes" % (self.version, pool_id)
        response = self.connection.request(req)
        response_dict = response.parse_body()
        assert_response(response_dict=response_dict, status_code=200)

        volumes = []

        for volume in response_dict['metadata']:
            volume = volume.split("/")
            name = volume[-1]
            type = volume[-2]

            if not detailed:
                metadata = {'config': {'size': None}, "name": name,
                            "type": type, "used_by": None}
                volumes.append(self._to_storage_volume(metadata=metadata))
            else:
                volume = self.ex_get_storage_pool_volume(pool_id=pool_id,
                                                         type=type, name=name)
                volumes.append(volume)

        return volumes

    def ex_get_storage_pool_volume(self, pool_id, type, name):
        """
        Description: information about a storage volume
        of a given type on a storage pool
        Introduced: with API extension storage
        Authentication: trusted
        Operation: sync
        Return: A StorageVolume  representing a storage volume
        """
        req = "/%s/storage-pools/%s/volumes/%s/%s" % (self.version,
                                                      pool_id,
                                                      type, name)
        response = self.connection.request(req)
        response_dict = response.parse_body()
        assert_response(response_dict=response_dict, status_code=200)

        return self._to_storage_volume(response_dict["metadata"])

    def ex_create_storage_pool_volume(self, pool_id, definition):
        """
        Create a new storage volume on a given storage pool

        Operation: sync or async (when copying an existing volume)

        :return: A StorageVolume  representing a storage volume
        """

        if not definition:
            raise LXDAPIException("Cannot create a storage volume "
                                  "without a definition")

        data = json.dumps(definition)

        # Return: standard return value or standard error
        req = "/%s/storage-pools/%s/volumes" % (self.version, pool_id)
        response = self.connection.request(req, method='POST', data=data)

        response_dict = response.parse_body()
        assert_response(response_dict=response_dict, status_code=200)

        return self.ex_get_storage_pool_volume(pool_id=pool_id,
                                               type=definition["type"],
                                               name=definition["name"])

    def ex_replace_storage_volume_config(self, pool_id, type,
                                         name, definition):
        """
        Replace the storage volume information
        :param pool_id:
        :param type:
        :param name:
        :param definition
        :return:
        """

        if not definition:
            raise LXDAPIException("Cannot create a storage "
                                  "volume without a definition")

        data = json.dumps(definition)
        response = self.connection.request("/%s/storage-pools/%s/volumes/%s/%s"
                                           % (self.version, pool_id,
                                              type, name),
                                           method="PUT", data=data)

        response_dict = response.parse_body()
        assert_response(response_dict=response_dict, status_code=200)
        return self.ex_get_storage_pool_volume(pool_id=pool_id,
                                               type=type, name=name)

    def ex_delete_storage_pool_volume(self, pool_id, type, name):
        """
        Delete a storage volume of a given type on a given storage pool

        :param pool_id:
        :type ``str``

        :param type:
        :type  ``str``

        :param name:
        :type ``str``

        :return:
        """

        response = self.connection.request("/%s/storage-pools/%s/volumes/%s/%s"
                                           % (self.version, pool_id,
                                              type, name),
                                           method="DELETE")
        response_dict = response.parse_body()
        assert_response(response_dict=response_dict, status_code=200)
        return True

    def _to_container(self, metadata):
        """
        Returns Container instance built from the given metadata

        :param metadata: dictionary with the container metadata
        :type  metadata: ``dict``

        :rtype :class:`libcloud.container.base.Container
        """

        name = metadata['name']
        state = metadata['status']

        if state == 'Running':
            state = ContainerState.RUNNING
        elif state == 'Frozen':
            state = ContainerState.PAUSED
        else:
            state = ContainerState.STOPPED

        extra = metadata
        img_id = metadata['config'].get('volatile.base_image', None)
        img_version = metadata['config'].get('image.version', None)
        ips = metadata["ips"]

        image = ContainerImage(id=img_id, name=img_id, path=None,
                               version=img_version, driver=self, extra=None)

        container = Container(driver=self, name=name, id=name,
                              state=state, image=image,
                              ip_addresses=ips, extra=extra)

        return container

    def _do_container_action(self, container, action,
                             timeout, force, stateful):
        """
        change the container state by performing the given action
        action may be either stop, start, restart, freeze or unfreeze
        """

        if action not in LXD_API_STATE_ACTIONS:
            raise ValueError("Invalid action specified")

        # cache the state of the container
        state = container.state

        data = {"action": action, "timeout": timeout}
        data = json.dumps(data)

        # checkout this for stateful:
        # https://discuss.linuxcontainers.org/t/error-in-live-migration/1928
        # looks like we are getting "err":"Unable to perform
        # container live migration. CRIU isn't installed"
        # in the response when stateful is True so remove it for now
        req = '/%s/containers/%s/state' % (self.version, container.name)
        response = self.connection.request(req, method='PUT', data=data)

        response_dict = response.parse_body()

        # a background operation is expected to
        # be returned status_code = 100 --> Operation created
        assert_response(response_dict=response_dict,
                        status_code=100)

        if not timeout:
            timeout = LXDContainerDriver.default_time_out

        try:
            id = response_dict['metadata']['id']
            req = '/%s/operations/%s/wait?timeout=%s' % (self.version,
                                                         id, timeout)
            response = self.connection.request(req)

        except BaseHTTPError as e:

            message_list = e.message.split(",")
            message = message_list[0].split(":")[-1]

            # if not found assume the operation completed
            if message != '"not found"':
                # something is wrong
                raise LXDAPIException(message=e.message)

        # if the container is ephemeral and the action is to stop
        # then the container is removed so return sth dummy
        if state == ContainerState.RUNNING and\
                container.extra['ephemeral'] and action == 'stop':
            # return a dummy container otherwise we get 404 error
            container = Container(driver=self, name=container.name,
                                  id=container.name,
                                  state=ContainerState.TERMINATED, image=None,
                                  ip_addresses=[], extra=None)
            return container

        return self.get_container(id=container.name)

    def _to_image(self, metadata):
        """
        Returns a container image from the given metadata

        :param metadata:
        :type  metadata: ``dict``

        :rtype: :class:`.ContainerImage`
        """
        aliases = metadata.get('aliases', [])

        if aliases:
            name = metadata.get('aliases')[0].get('name')
        else:
            name = metadata.get('fingerprint')

        version = metadata.get('update_source').get('alias')
        extra = metadata

        return ContainerImage(id=name, name=name, path=None,
                              version=version, driver=self, extra=extra)

    def _to_storage_pool(self, data):
        """
        Given a dictionary with the storage pool configuration
        it returns a StoragePool object
        :param data: the storage pool configuration
        :return: :class: .StoragePool
        """

        return LXDStoragePool(name=data['name'], driver=data['driver'],
                              used_by=data['used_by'], config=['config'],
                              managed=False)

    def _deploy_container_from_image(self, name, image, parameters,
                                     cont_params,
                                     timeout=default_time_out):
        """
        Deploy a new container from the given image

        :param name: the name of the container
        :param image: .ContainerImage

        :param parameters: string describing the source attribute
        :type  parameters ``str``

        :param cont_params: dictionary describing the container configuration
        :type  cont_params: dict

        :param timeout: Time to wait for the operation before timeout
        :type  timeout: int

        :rtype: :class: .Container
        """

        if cont_params is None:
            raise LXDAPIException(message="cont_params "
                                          "must be a valid dict")

        # container without a pre-populated rootfs
        # see https://github.com/lxc/lxd/blob/master/doc/rest-api.md
        # can be "image", "migration", "copy" or "none"
        data = {'name': name, 'source': {'type': 'none'}}

        if parameters:
            data['source'].update(parameters["source"])

        if data['source']['type'] not in LXD_API_IMAGE_SOURCE_TYPE:
            msg = "source type must in " + str(LXD_API_IMAGE_SOURCE_TYPE)
            raise LXDAPIException(message=msg)

        # add also the other container parameters
        data.update(cont_params)

        data = json.dumps(data)

        # Return: background operation or standard error
        response = self.connection.request('/%s/containers' % self.version,
                                           method='POST', data=data)
        response_dict = response.parse_body()

        # a background operation is expected to
        # be returned status_code = 100 --> Operation created
        assert_response(response_dict=response_dict, status_code=100)

        # make sure we don't wait indefinitely
        # until the operation is done
        if not timeout:
            timeout = LXDContainerDriver.default_time_out

        try:
            # wait untitl the timeout...but util getting here the operation
            # may have finished already
            id = response_dict['metadata']['id']
            req_str = '/%s/operations/%s/wait?timeout=%s' % (self.version,
                                                             id,
                                                             timeout)
            response = self.connection.request(req_str)
        except BaseHTTPError as e:

            message_list = e.message.split(",")
            message = message_list[0].split(":")[-1]
            if message != '"not found"':
                # somthing is wrong
                raise LXDAPIException(message=e.message)

        return self.get_container(id=name)

    def _to_storage_volume(self, metadata):
        """
        Returns StorageVolume object from metadata
        :param metadata: dict representing the volume
        :rtype: StorageVolume
        """

        size = 0
        if "size" in metadata['config'].keys():
            size = LXDContainerDriver._to_gb(metadata['config'].pop('size'))

        extra = {"type": metadata["type"],
                 "used_by": metadata["used_by"],
                 "config": metadata['config']}

        return StorageVolume(id=metadata['name'], name=metadata['name'],
                             driver=self, size=size, extra=extra)

    def _get_api_version(self):
        """
        Get the LXD API version
        """
        return LXDContainerDriver.version

    def _ex_connection_class_kwargs(self):
        """
        Return extra connection keyword arguments which are passed to the
        Connection class constructor.
        """

        if hasattr(self, "key_file") and hasattr(self, "cert_file"):
            return {"key_file": self.key_file,
                    "cert_file": self.cert_file,
                    "certificate_validator": self.certificate_validator}
        return super(LXDContainerDriver, self)._ex_connection_class_kwargs()

    @staticmethod
    def _create_exec_configuration(input, **config):
        """
        Prepares the input parameters for executyion API call
        """

        if "environment" in config.keys():
            input["environment"] = config["environment"]

        if "width" in config.keys():
            input["width"] = config["width"]
        else:
            input["width"] = 80

        if "height" in config.keys():
            input["width"] = config["height"]
        else:
            input["height"] = 25

        if "user" in config.keys():
            input["user"] = config["user"]

        if "group" in config.keys():
            input["group"] = config["group"]

        if "cwd" in config.keys():
            input["cwd"] = config["cwd"]

        if "wait-for-websocket" in config.keys():
            input["wait-for-websocket"] = config["wait-for-websocket"]
        else:
            input["wait-for-websocket"] = False

        if "record-output" in config.keys():
            input["record-output"] = config["record-output"]
        else:
            input["record-output"] = False

        if "interactive" in config.keys():
            input["interactive"] = config["interactive"]
        else:
            input["interactive"] = True

        return input

    @staticmethod
    def _fix_cont_params(architecture, profiles,
                         ephemeral, config,
                         devices, instance_type):
        """
        Returns a dict with the container parameters
        """

        cont_params = {}

        # add also the other container parameters
        if architecture is not None:
            cont_params['architecture'] = architecture

        if profiles is not None:
            cont_params["profiles"] = profiles
        else:
            cont_params["profiles"] = [LXDContainerDriver.default_profiles]

        if ephemeral is not None:
            cont_params["ephemeral"] = ephemeral
        else:
            cont_params["ephemeral"] = LXDContainerDriver.default_ephemeral

        if config is not None:
            cont_params["config"] = config

        if devices is not None:
            cont_params["devices"] = devices

        if instance_type is not None:
            cont_params["instance_type"] = instance_type

        return cont_params

    @staticmethod
    def _to_gb(size):
        """
        Convert the given size in bytes to gigabyte
        :param size: in bytes
        :return: int representing the gigabytes
        """
        size = int(size)
        return size // 10**9
