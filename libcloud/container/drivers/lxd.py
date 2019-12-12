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

from libcloud.container.providers import Provider
from libcloud.container.types import ContainerState

# Acceptable success strings comping from LXD API
LXD_API_SUCCESS_STATUS = ['Success']
LXD_API_STATE_ACTIONS = ['stop', 'start', 'restart', 'freeze', 'unfreeze']

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
            raise InvalidCredsError("Valid key files are: " + str(kwargs['key_files_allowed']) +
                                    "you provided: " + key_file_suffix[-1])

            # if none of the above check the types
    if 'cert_files_allowed' in kwargs.keys():
        cert_file_suffix = cert_file.split('.')

        if cert_file_suffix[-1] not in kwargs['cert_files_allowed']:
            raise InvalidCredsError("Valid certification files are: " + str(kwargs['cert_files_allowed']) +
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
        raise InvalidCredsError('You need a certificate file to authenticate with '
                                'LXD tls. This can be found in the server.')


def assert_response(response_dict, status_code=200):

    # if the type of the response is an error
    if response_dict['type'] == LXD_ERROR_STATUS_RESP:
        # an error returned
        raise LXDAPIException(response=response_dict)

    # anything else apart from the status_code given should be treated as error
    if response_dict['status_code'] != status_code:
        # we have an unknown error
        raise LXDAPIException.with_other_msg(other_msg="Status code should be {0} but is {1}".format(status_code, response_dict['status_code']))

def get_img_extra_from_meta(metadata):
    """
    A ContainerImage type only allows for some basic image data
    and encapsulates any further image info into the extra dictionary
    This function is meant to construct this dictionaly for LXD
    :param metadata: dictionary with the metadata of the image
    """
    return metadata


class LXDAPIException(Exception):
    """
    Basic exception to be thrown when LXD API
    returns with some kind of error
    """

    @classmethod
    def with_other_msg(cls, other_msg):
        return cls(response=None, other_msg=other_msg)

    def __init__(self, response, other_msg="Unknown Error Occurred"):
        super(LXDAPIException, self).__init__()
        self.lxd_response = response
        self.other_msg = other_msg

    def __str__(self):

        response = ""

        if self.lxd_response is not None:
            if 'type' in self.lxd_response.keys():
                response += 'type: {0} '.format(self.lxd_response['type'])

            if 'error_code' in self.lxd_response.keys():
                response = 'error_code: {0} '.format(self.lxd_response['error_code'])

            if 'error' in self.lxd_response.keys():
                response = 'error: {0} '.format(self.lxd_response['error'])

        if response == "":
            response = self.other_msg

        return str(response)

class StoragePool(object):
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


class LXDResponse(JsonResponse):
    valid_response_codes = [httplib.OK, httplib.ACCEPTED, httplib.CREATED,
                            httplib.NO_CONTENT]

    def parse_body(self):

        if len(self.body) == 0 and not self.parse_zero_length_body:
            return self.body

        try:
            # error responses are tricky in Docker. Eg response could be
            # an error, but response status could still be 200
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
                raise Exception(
                    'ConnectionError: Failed to parse JSON response')
        return body

    def parse_error(self):
        if self.status == 401:
            raise InvalidCredsError('Invalid credentials')
        else:
            print(self.status)
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
                 key_file=None, cert_file=None, **kwargs):

        if 'certificate_validator' in kwargs.keys():
            certificate_validator = kwargs.pop('certificate_validator')
            certificate_validator(key_file=key_file, cert_file=cert_file)
        else:
            check_certificates(key_file=key_file, cert_file=cert_file, **kwargs)

        super(LXDtlsConnection, self).__init__(key_file=key_file, cert_file=cert_file,
                                               secure=secure, host=host, port=port, url=None,
                                               proxy_url=None, timeout=None, backoff=None, retry_delay=None)

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

    def __init__(self, key='', secret='', secure=False,
                 host='localhost', port=8443, key_file=None,
                 cert_file=None, ca_cert=None, certificate_validator=check_certificates ):

        if key_file:
            self.connectionCls = LXDtlsConnection
            self.key_file = key_file
            self.cert_file = cert_file
            self.certificate_validator = certificate_validator
            secure = True

        if host.startswith('https://'):
            secure = True

        host = strip_http_prefix(host=host)

        super(LXDContainerDriver, self).__init__(key=key, secret=secret, secure=secure, host=host,
                                                 port=port, key_file=key_file, cert_file=cert_file)

        if key_file or cert_file:
            # LXD tls authentication-
            # We pass two files, a key_file with the
            # private key and cert_file with the certificate
            # libcloud will handle them through LibcloudHTTPSConnection
            if not (key_file and cert_file):
                raise Exception(
                    'Needs both private key file and '
                    'certificate file for tls authentication')

        if ca_cert:
            self.connection.connection.ca_cert = ca_cert
        else:
            # do not verify SSL certificate
            self.connection.connection.ca_cert = False

        self.connection.secure = secure
        self.connection.host = host
        self.connection.port = port
        self.version = self._get_api_version()

    def get_api_endpoints(self):
        """
        Returns the API endpoints. This is allowed to everyone
        :return: LXDResponse that describes the API endpoints
        """
        return self.connection.request("/")

    def get_to_version(self):
        """
        GET to /1.0 This is allowed to everyone
        :return: LXDResponse 
        """
        return self.connection.request("/%s"%(self.version))

    def post_certificate(self, certificate, name, password):
        """
        Add a new trusted certificate
        Authentication: trusted or untrusted
        Operation: sync
        Return: standard return value or standard error
        """
        return self.connection.request('/%s/certificates?type=client&certificate=%s&\
                                       name=%s&password=%s' % (self.version, certificate, 
                                                                name, password), method='POST')

    def deploy_container(self, name, image, cluster=None,
                         parameters=None, start=True):

        """
        Create a new container
        Authentication: trusted
        Operation: async
        Return: background operation or standard error

        :param name: The name of the new container
        :type  name: ``str``

        :param image: The container image to deploy
        :type  image: :class:`.ContainerImage`

        :param cluster: The cluster to deploy to, None is default
        :type  cluster: :class:`.ContainerCluster`

        :param parameters: Container configuration parameters
        :type  parameters: ``str``

        :param start: Start the container on deployment
        :type  start: ``bool``

        :rtype: :class:`.Container`
        """

        # TODO: Perhaps we should save us the trouble and
        # check if the container exists. If yes then simply
        # return this container?

        if isinstance(image, ContainerImage):
            container = self._deploy_container_from_image(name=name, image=image, parameters=parameters)
        elif image is not None:
            # assume that the image is a fingerprint
            image = self.get_image(fingerprint=image)
            container = self._deploy_container_from_image(name=name, image=image, parameters=parameters)
        else:
            raise ValueError(" image parameter must either be a footprint or a ContainerImage")

        if start:
            container.start()
        return container

    def get_container(self, id):

        """
        Get a container by ID

        :param id: The ID of the container to get
        :type  id: ``str``

        :rtype: :class:`libcloud.container.base.Container`
        """
        result = self.connection.request("/%s/containers/%s" %
                                         (self.version, id))
        result = result.parse_body()
        assert_response(response_dict=result)
        return self._to_container(result['metadata'])

    def start_container(self, container):
        """
        Start a container

        :param container: The container to start
        :type  container: :class:`libcloud.container.base.Container`

        :rtype: :class:`libcloud.container.base.Container`
        """

        return self._do_container_action(container=container, action='start',
                                         timeout=30, force=True, stateful=True)

    def stop_container(self, container):
        """
        Stop a container

        :param container: The container to be stopped
        :type  container: :class:`libcloud.container.base.Container`

        :return: The container refreshed with current data
        :rtype: :class:`libcloud.container.base.Container
        """
        return self._do_container_action(container=container, action='stop',
                                         timeout=30, force=True, stateful=True)

    def restart_container(self, container):
        """
        Restart a deployed container

        :param container: The container to restart
        :type  container: :class:`.Container`

        :rtype: :class:`.Container`
        """
        return self._do_container_action(container=container, action='restart',
                                         timeout=30, force=True, stateful=True)

    def destroy_container(self, container):
        """
        Destroy a deployed container

        :param container: The container to destroy
        :type  container: :class:`.Container`

        :rtype: :class:`.Container`
        """
        # Return: background operation or standard error
        response =  self.connection.request('/%s/containers/%s' %
                                       (self.version, container.name), method='DELETE')

        response = response.parse_body()
        assert_response(response_dict=response, status_code=100)
        return response

    def list_containers(self, image=None, cluster=None):
        """
        List the deployed container images

        :param image: Filter to containers with a certain image
        :type  image: :class:`.ContainerImage`

        :param cluster: Filter to containers in a cluster
        :type  cluster: :class:`.ContainerCluster`

        :rtype: ``list`` of :class:`.Container`
        """

        result = self.connection.request(action='/%s/containers' % self.version)
        result = result.parse_body()

        # how to treat the errors????
        assert_response(response_dict=result)

        meta = result['metadata']
        containers = []
        for item in meta:
            container_id = item.split('/')[-1]
            container = self.get_container(id=container_id)
            containers.append(container)

        return containers

    def get_image(self, fingerprint):
        """
        Returns a container image from the given image fingerprint

        :type  fingerprint: ``str``

        :rtype: :class:`.ContainerImage`
        """

        response = self.connection.request('/%s/images/%s' % (self.version, fingerprint))

        #  parse the LXDResponse into a dictionary
        response_dict = response.parse_body()
        assert_response(response_dict=response_dict)

        return self._do_get_image(metadata=response_dict['metadata'])

    def get_img_by_name(self, img_name):
        """
        Returns the ContainerImage that has the given name
        :param img_name: the name of the image to retrieve
        :return:
        """

        images = self.list_images()

        for img in images:
            if img.name == img_name:
                return img

        raise ValueError("Image: {} does not exist".format(img_name))

    def list_images(self):
        """
        List the installed container images

        :rtype: ``list`` of :class:`.ContainerImage`
        """
        response = self.connection.request('/%s/images'%(self.version))

        #  parse the LXDResponse into a dictionary
        response_dict = response.parse_body()

        assert_response(response_dict=response_dict)

        metadata = response_dict['metadata']
        images = []

        for image in metadata:
            fingerprint = image.split("/")[-1]
            images.append(self.get_image(fingerprint=fingerprint))
        return images

    def list_storage_pools(self):
        """
        Returns a list of storage pools defined currently defined on the host
        e.g. [ "/1.0/storage-pools/default", ]

        Description: list of storage pools
        Authentication: trusted
        Operation: sync

        """
        # Return: list of storage pools that are currently defined on the host
        response = self.connection.request("/%s/storage-pools" % self.version)

        response_dict = response.parse_body()
        assert_response(response_dict=response_dict)

        pools = []
        for pool_item in response_dict['metadata']:
            pool_name = pool_item.split('/')[-1]
            pools.append(self.get_storage_pool(id=pool_name))

        return pools

    def get_storage_pool(self, id):
        """
        Returns  information about a storage pool
        :param id: the name of the storage pool
        :rtype: :class: StoragePool
        """

        # Return: dict representing a storage pool
        response = self.connection.request("/%s/storage-pools/%s" % (self.version, id))

        response_dict = response.parse_body()
        assert_response(response_dict=response_dict)

        if not response_dict['metadata']:
            raise LXDAPIException.with_other_msg(other_msg="Storage pool with name {0} has no data".format(id))

        return self._to_storage_pool(data=response_dict['metadata'])

    def create_storage_pool(self, definition):

        """Create a storage_pool from config.

        Implements POST /1.0/storage-pools

        The `definition` parameter defines what the storage pool will be.  An
        example config for the zfs driver is:

                   {
                       "config": {
                           "size": "10GB"
                       },
                       "driver": "zfs",
                       "name": "pool1"
                   }

        Note that **all** fields in the `definition` parameter are strings.

        For further details on the storage pool types see:
        https://lxd.readthedocs.io/en/latest/storage/

        The function returns the a `StoragePool` instance, if it is
        successfully created, otherwise an Exception is raised.

        :param definition: the fields to pass to the LXD API endpoint
        :type definition: dict
        :returns: a storage pool if successful, raises NotFound if not found
        :rtype: :class:`pylxd.models.storage_pool.StoragePool`
        :raises: :class:`pylxd.exceptions.LXDAPIExtensionNotAvailable` if the
                   'storage' api extension is missing.
        :raises: :class:`pylxd.exceptions.LXDAPIException` if the storage pool
                   couldn't be created.
        """

        response = self.connection.request("/%s/storage-pools" % (self.version),
                                           method='POST', json=definition)

        raise NotImplementedError("This function has not been finished yet")

    def delete_storage_pool(self):
        """Delete the storage pool.

        Implements DELETE /1.0/storage-pools/<self.name>

        Deleting a storage pool may fail if it is being used.  See the LXD
        documentation for further details.

        :raises: :class:`pylxd.exceptions.LXDAPIException` if the storage pool
                   can't be deleted.
        """

        raise NotImplementedError("This function has not been yet")

    def _to_container(self, data):
        """
        Convert container in Container instances given the
        the data received from the LXD API call parsed in a dictionary
        """

        name = data['name']
        state = data['status']

        if state == 'Running':
            state = ContainerState.RUNNING
        else:
            state = ContainerState.STOPPED

        extra = dict()
        image = ContainerImage(id="?", name="?", path="/", version="/",
                               driver="/", extra=extra)

        container = Container(driver=self, name=name, id=name,
                              state=state, image=image,
                              ip_addresses=[], extra=extra)

        return container

    def _do_container_action(self, container, action,
                             timeout, force, stateful):
        """
        change the container state by performing the given action
        action may be either stop, start, restart, freeze or unfreeze
        """

        if action not in LXD_API_STATE_ACTIONS:
            raise ValueError("Invalid action specified")

        # if action == 'start' or action == 'restart':
        #    force = False

        json = {"action":action, "timeout":timeout, "force":force}

        # checkout this for stateful: https://discuss.linuxcontainers.org/t/error-in-live-migration/1928
        # looks like we are getting "err":"Unable to perform container live migration. CRIU isn't installed"
        # in the response when stateful is True so remove it for now
                #"stateful":stateful, "force":force}

        response = self.connection.request('/%s/containers/%s/state' %
                                         (self.version, container.name), method='PUT', json=json)

        response_dict = response.parse_body()

        # a background operation is expected to be returned status_code = 100 --> Operation created
        assert_response(response_dict=response_dict, status_code=100)

        return self.get_container(id=container.name)

    def _do_get_image(self, metadata):
        """
        Returns a container image from the given image

        :param image_url: URL of image
        :type  path: ``str``

        :rtype: :class:`.ContainerImage`
        """
        name = metadata.get('aliases')[0].get('name')
        id = name
        version = metadata.get('update_source').get('alias')

        extra = get_img_extra_from_meta(metadata=metadata)
        return ContainerImage(id=id, name=name, path=None, version=version, 
                              driver=self.connection.driver, extra=extra)

    def _to_storage_pool(self, data):
        """
        Given a dictionary with the storage pool configuration
        it returns a StoragePool object
        :param data: the storage pool configuration
        :return: :class: .StoragePool
        """

        return StoragePool(name=data['name'], driver=data['driver'],
                           used_by=data['used_by'], config=['config'],
                           managed=False)

    def _deploy_container_from_image(self, name, image, parameters):
        """
        Deploy a new container from the given image
        :param name: the name of the container
        :param image: .ContainerImage

        :rtype: :class: .Container
        """

        # if we are given a ContainerImage then use it
        # to create the containers
        data = {'name': name, 'source': {'type': 'image', 'alias':image.name}}

        if parameters is not None:
            data.update(parameters)

        # Return: background operation or standard error
        response = self.connection.request('/%s/containers' % self.version, method='POST', json=data)
        response_dict = response.parse_body()

        # a background operation is expected to be returned status_code = 100 --> Operation created
        assert_response(response_dict=response_dict, status_code=100)

        # need sth else here like Container...perhaps self.get_container(id=name)
        return self.get_container(id=name)

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
            return {"key_file":self.key_file,
                    "cert_file":self.cert_file,
                    "certificate_validator":self.certificate_validator}
        return  super(LXDContainerDriver, self)._ex_connection_class_kwargs()


