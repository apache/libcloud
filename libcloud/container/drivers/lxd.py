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
                 host='localhost',
                 port=8443, ca_cert='', key_file=None, cert_file=None, **kwargs):

        self._check_certificates(key_file=key_file, cert_file=cert_file, **kwargs)

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

    def _check_certificates(self, key_file, cert_file, **kwargs):

        """
        Basic checks for the provided certificates
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
                raise InvalidCredsError("Valid key files are: "+str(kwargs['key_files_allowed'])+
                                        "you provided: "+key_file_suffix[-1])

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



class LXDContainerDriver(ContainerDriver):
    """
    Driver for LXD containers
    https://lxd.readthedocs.io/en/stable-2.0/rest-api/
    """
    type = Provider.LXD
    name = 'LXD'
    website = 'https://linuxcontainers.org/'
    connectionCls = LXDConnection
    supports_clusters = False
    version = '1.0'

    def __init__(self, key='', secret='',
                 secure=False, host='localhost',
                 port=8443, key_file=None,
                 cert_file=None, ca_cert=None):

        if key_file:
            self.connectionCls = LXDtlsConnection
            self.key_file = key_file
            self.cert_file = cert_file
            secure = True

        if host.startswith('https://'):
            secure = True

        # strip the prefix
        prefixes = ['http://', 'https://']
        for prefix in prefixes:
            if host.startswith(prefix):
                host = host.strip(prefix)

        super(LXDContainerDriver, self).__init__(key=key,
                                                 secret=secret,
                                                 secure=secure,
                                                 host=host,
                                                 port=port,
                                                 key_file=key_file,
                                                 cert_file=cert_file)

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
                                       name=%s&password=%s'%(self.version, certificate, name, password), method='POST')

    def deploy_container(self, name, image, cluster=None,
                         parameters=None, start=True):

        """
        Deploy an installed container image

        :param name: The name of the new container
        :type  name: ``str``

        :param image: The container image to deploy
        :type  image: :class:`.ContainerImage`

        :param cluster: The cluster to deploy to, None is default
        :type  cluster: :class:`.ContainerCluster`

        :param parameters: Container Image parameters
        :type  parameters: ``str``

        :param start: Start the container on deployment
        :type  start: ``bool``

        :rtype: :class:`.Container`
        """

        return None

    def get_container(self, id):

        """
        Get a container by ID

        :param id: The ID of the container to get
        :type  id: ``str``

        :rtype: :class:`libcloud.container.base.Container`
        """
        result = self.connection.request("/%s/containers/%s/" %
                                         (self.version, id)).object

        return self._to_container(result)

    def start_container(self, container):
        """
        Start a ontainer

        :param container: The container to start
        :type  container: :class:`libcloud.container.base.Container`

        :rtype: :class:`libcloud.container.base.Container`
        """

        return self._do_container_action(container=container,
                                         action='start',
                                         timeout=30,
                                         force=True,
                                         stateful=True)

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

    def list_containers(self, image=None, cluster=None):
        """
        List the deployed container images

        :param image: Filter to containers with a certain image
        :type  image: :class:`.ContainerImage`

        :param cluster: Filter to containers in a cluster
        :type  cluster: :class:`.ContainerCluster`

        :rtype: ``list`` of :class:`.Container`
        """
        
        result = self.connection.request(action='/%s/containers'
                                       %(self.version))
        #containers = [self._to_container(value) for value in result]
        return result #containers

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
        raise NotImplementedError(
            'destroy_container not implemented for this driver')

    def list_images(self):
        """
        List the installed container images

        :rtype: ``list`` of :class:`.ContainerImage`
        """
        result = self.connection.request('/%s/images/'%(self.version))
        images = []

        for image in result:
            images.append(self._do_get_image(fingerprint=image.split("/")[-1]))
        return images

    def _to_container(self, data):
        """
        Convert container in Container instances
        """
        arch = data['architecture']
        config = data['config']
        created_at = data['created_at']
        name = data['name']
        state = data['status']

        if state == 'Running':
            state = ContainerState.RUNNING
        else:
            state = ContainerState.STOPPED

        extra = dict()
        image = ContainerImage(id="?", name="?", path="/", version="/",
                               driver="/", extra=None)

        container = Container(driver=self, name=name, id=name,
                              state=state, image=image,
                              ip_addresses=[], extra=extra)

        return container

    def _do_container_action(self, container, action,
                             timeout, force, stateful):
        """
        change the container state by performing the given action
        """
        if action == 'start' or action == 'restart':
            force = 'false'
        else:
            force = str(force).lower()

        result = self.connection.request('/%s/containers/%s/state?action=%s&\
                                         timeout=%s&force=%s&stateful=%s'%
                                         (self.version, action, timeout,
                                          force, stateful, container.name),
                                         method='PUT')
        if result['type'] == 'error':
            pass

        return self.get_container(id=container.name)

    def _do_get_image(self, fingerprint):
        """
        Returns a container image from the given image url

        :param image_url: URL of image
        :type  path: ``str``

        :rtype: :class:`.ContainerImage`
        """
        result = self.connection.request('/%s/images/%s'%(self.version, fingerprint))
        name = result["aliases"][0]["name"]
        extra=dict()
        return ContainerImage(id=name, name=name, version=None, driver=self.connection.driver, extra=None)

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
        return {"key_file":self.key_file, "cert_file":self.cert_file}
