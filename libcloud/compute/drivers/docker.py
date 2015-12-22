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
import datetime
import shlex
import re

try:
    import simplejson as json
except:
    import json

from libcloud.utils.py3 import httplib
from libcloud.utils.py3 import b

from libcloud.compute.providers import Provider
from libcloud.common.base import JsonResponse, ConnectionUserAndKey
from libcloud.compute.types import (NodeState, InvalidCredsError)
from libcloud.compute.base import (Node, NodeDriver, NodeImage,
                                   NodeSize)

VALID_RESPONSE_CODES = [httplib.OK, httplib.ACCEPTED, httplib.CREATED,
                        httplib.NO_CONTENT]


class DockerResponse(JsonResponse):

    valid_response_codes = [httplib.OK, httplib.ACCEPTED, httplib.CREATED,
                            httplib.NO_CONTENT]

    def parse_body(self):
        if len(self.body) == 0 and not self.parse_zero_length_body:
            return self.body

        try:
            # error responses are tricky in Docker. Eg response could be
            # an error, but response status could still be 200
            body = json.loads(self.body)
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
        return self.body

    def success(self):
        return self.status in self.valid_response_codes


class DockerConnection(ConnectionUserAndKey):

    responseCls = DockerResponse
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


class DockerNodeDriver(NodeDriver):
    """
    Docker node driver class.

    >>> from libcloud.compute.providers import get_driver
    >>> driver = get_driver('docker')
    >>> conn = driver(host='198.61.239.128', port=4243)
    >>> conn.list_nodes()
    or connecting to http basic auth protected https host:
    >>> conn = driver('user', 'pass', host='https://198.61.239.128', port=443)

    connect with tls authentication, by providing a hostname, port, a private
    key file (.pem) and certificate (.pem) file
    >>> conn = driver(host='https://198.61.239.128',
        port=4243, key_file='key.pem', cert_file='cert.pem')
    """

    type = Provider.DOCKER
    name = 'Docker'
    website = 'http://docker.io'
    connectionCls = DockerConnection
    features = {'create_node': ['password']}

    def __init__(self, key=None, secret=None, secure=False, host='localhost',
                 port=4243, key_file=None, cert_file=None):

        super(DockerNodeDriver, self).__init__(key=key, secret=secret,
                                               secure=secure, host=host,
                                               port=port, key_file=key_file,
                                               cert_file=cert_file)
        if host.startswith('https://'):
            secure = True

        # strip the prefix
        prefixes = ['http://', 'https://']
        for prefix in prefixes:
            if host.startswith(prefix):
                host = host.strip(prefix)

        if key_file or cert_file:
            # docker tls authentication-
            # https://docs.docker.com/articles/https/
            # We pass two files, a key_file with the
            # private key and cert_file with the certificate
            # libcloud will handle them through LibcloudHTTPSConnection
            if not (key_file and cert_file):
                raise Exception(
                    'Needs both private key file and '
                    'certificate file for tls authentication')
            self.connection.key_file = key_file
            self.connection.cert_file = cert_file
            self.connection.secure = True
        else:
            self.connection.secure = secure

        self.connection.host = host
        self.connection.port = port

    def create_node(self, name, image, command=None, hostname=None, user='',
                    stdin_open=True, tty=True,
                    mem_limit=0, ports=None, environment=None, dns=None,
                    volumes=None, volumes_from=None,
                    network_disabled=False, entrypoint=None,
                    cpu_shares=None, working_dir='', domainname=None,
                    memswap_limit=0, port_bindings=None):
        """
        Create a container

        Create a container, based on an image and optionally specify command
        and other settings. If image is not found, try to pull it
        After the container is created, start it
        """
        command = shlex.split(str(command))
        if port_bindings is None:
            port_bindings = {}
        params = {
            'name': name
        }

        payload = {
            'Hostname': hostname,
            'Domainname': domainname,
            'ExposedPorts': ports,
            'User': user,
            'Tty': tty,
            'OpenStdin': stdin_open,
            'StdinOnce': False,
            'Memory': mem_limit,
            'AttachStdin': True,
            'AttachStdout': True,
            'AttachStderr': True,
            'Env': environment,
            'Cmd': command,
            'Dns': dns,
            'Image': image,
            'Volumes': volumes,
            'VolumesFrom': volumes_from,
            'NetworkDisabled': network_disabled,
            'Entrypoint': entrypoint,
            'CpuShares': cpu_shares,
            'WorkingDir': working_dir,
            'MemorySwap': memswap_limit,
            'PublishAllPorts': True,
            'PortBindings': port_bindings,
        }

        data = json.dumps(payload)
        try:
            result = self.connection.request('/containers/create', data=data,
                                             params=params, method='POST')
        except Exception as e:
            # if image not found, try to pull it
            if e.message.startswith('No such image:'):
                try:
                    self.ex_pull_image(image=image)
                    result = self.connection.request('/containers/create',
                                                     data=data, params=params,
                                                     method='POST')
                except:
                    raise Exception('No such image: %s' % image)
            else:
                raise Exception(e)

        id_ = result.object['Id']

        payload = {
            'Binds': [],
            'PublishAllPorts': True,
            'PortBindings': port_bindings,
        }

        data = json.dumps(payload)
        result = self.connection.request(
            '/containers/%s/start' % id_, data=data,
            method='POST')

        return Node(id=id_, name=id_, state=NodeState.RUNNING,
                    public_ips=[], private_ips=[],
                    driver=self.connection.driver, extra={})

    def list_sizes(self, location=None):
        """
        List sizes on this docker server (default size)

        :param location: The location at which to list sizes
        :type location: :class:`.NodeLocation`

        :return: list of node size objects
        :rtype: ``list`` of :class:`.NodeSize`
        """
        return (
            [NodeSize(
                id='default',
                name='default',
                ram='unlimited',
                disk='unlimited',
                bandwidth='unlimited',
                price=0,
                driver=self)]
        )

    def list_images(self, location=None):
        "Return list of images as NodeImage objects"

        result = self.connection.request('/images/json').object
        images = []
        for image in result:
            try:
                name = image.get('RepoTags')[0]
            except:
                name = image.get('Id')
            images.append(NodeImage(
                id=image.get('Id'),
                name=name,
                driver=self.connection.driver,
                extra={
                    "created": image.get('Created'),
                    "size": image.get('Size'),
                    "virtual_size": image.get('VirtualSize'),
                },
            ))

        return images

    def list_nodes(self, show_all=True):
        """
        List running and stopped containers
        show_all=False will show only running containers

        :param show_all: Show all images
        :type  show_all: ``bool``

        :return:  list of node objects
        :rtype: ``list`` of :class:`.Node`
        """
        try:
            result = self.connection.request(
                "/containers/ps?all=%s" %
                str(show_all)).object
        except Exception as exc:
            if hasattr(exc, 'errno') and exc.errno == 111:
                raise Exception(
                    'Make sure docker host is accessible'
                    'and the API port is correct')
            raise

        nodes = [self._to_node(value) for value in result]
        return nodes

    def ex_inspect_node(self, node):
        """
        Inspect a container
        """
        result = self.connection.request("/containers/%s/json" %
                                         node.id).object

        name = result.get('Name').strip('/')
        if result['State']['Running']:
            state = NodeState.RUNNING
        else:
            state = NodeState.STOPPED

        extra = {
            'image': result.get('Image'),
            'volumes': result.get('Volumes'),
            'env': result.get('Config', {}).get('Env'),
            'ports': result.get('ExposedPorts'),
            'network_settings': result.get('NetworkSettings', {})
        }
        node_id = result.get('Id')
        if not node_id:
            node_id = result.get('ID', '')
        node = (Node(id=node_id,
                     name=name,
                     state=state,
                     public_ips=[self.connection.host],
                     private_ips=[],
                     driver=self.connection.driver,
                     extra=extra))
        return node

    def ex_list_processes(self, node):
        """
        List processes running inside a container
        """
        result = self.connection.request("/containers/%s/top" % node.id).object

        return result

    def reboot_node(self, node):
        """
        Restart a container

        :param node: The node to be rebooted
        :type node: :class:`.Node`

        :return: True if the reboot was successful, otherwise False
        :rtype: ``bool``
        """
        data = json.dumps({'t': 10})
        # number of seconds to wait before killing the container
        result = self.connection.request('/containers/%s/restart' % (node.id),
                                         data=data, method='POST')
        return result.status in VALID_RESPONSE_CODES

    def destroy_node(self, node):
        """
        Remove a container

        :param node: The node to be destroyed
        :type node: :class:`.Node`

        :return: True if the destroy was successful, False otherwise.
        :rtype: ``bool``
        """
        result = self.connection.request('/containers/%s' % (node.id),
                                         method='DELETE')
        return result.status in VALID_RESPONSE_CODES

    def ex_start_node(self, node):
        """
        Start a container

        :param node: The node to be started
        :type node: :class:`.Node`

        :return: True if the start was successful, False otherwise.
        :rtype: ``bool``
        """
        payload = {
            'Binds': [],
            'PublishAllPorts': True,
        }
        data = json.dumps(payload)
        result = self.connection.request('/containers/%s/start' % (node.id),
                                         method='POST', data=data)
        return result.status in VALID_RESPONSE_CODES

    def ex_stop_node(self, node):
        """
        Stop a container

        :param node: The node to be stopped
        :type node: :class:`.Node`

        :return: True if the stop was successful, False otherwise.
        :rtype: ``bool``
        """
        result = self.connection.request('/containers/%s/stop' % (node.id),
                                         method='POST')
        return result.status in VALID_RESPONSE_CODES

    def ex_rename_node(self, node, name):
        """
        Rename a container

        :param node: The node to be renamed
        :type node: :class:`.Node`

        :return: True if the rename was successful, False otherwise.
        :rtype: ``bool``
        """
        result = self.connection.request('/containers/%s/rename?name=%s'
                                         % (node.id, name),
                                         method='POST')
        return result.status in VALID_RESPONSE_CODES

    def ex_get_logs(self, node, stream=False):
        """
        Get container logs

        If stream == True, logs will be yielded as a stream
        From Api Version 1.11 and above we need a GET request to get the logs
        Logs are in different format of those of Version 1.10 and below

        """
        payload = {}
        data = json.dumps(payload)

        if float(self._get_api_version()) > 1.10:
            result = self.connection.request(
                "/containers/%s/logs?follow=%s&stdout=1&stderr=1" %
                (node.id, str(stream))).object
            logs = json.loads(result)
        else:
            result = self.connection.request(
                "/containers/%s/attach?logs=1&stream=%s&stdout=1&stderr=1" %
                (node.id, str(stream)), method='POST', data=data)
            logs = result.body

        return logs

    def ex_search_images(self, term):
        """Search for an image on Docker.io.
           Returns a list of NodeImage objects

           >>> images = conn.search_images(term='mistio')
           >>> images
           [<NodeImage: id=rolikeusch/docker-mistio...>,
            <NodeImage: id=mist/mistio, name=mist/mistio, driver=Docker  ...>]
        """

        term = term.replace(' ', '+')
        result = self.connection.request('/images/search?term=%s' %
                                         term).object
        images = []
        for image in result:
            name = image.get('name')
            images.append(NodeImage(
                id=name,
                name=name,
                driver=self.connection.driver,
                extra={
                    "description": image.get('description'),
                    "is_official": image.get('is_official'),
                    "is_trusted": image.get('is_trusted'),
                    "star_count": image.get('star_count'),
                },
            ))

        return images

    def ex_pull_image(self, image):
        """Create an image,
        Create an image either by pull it from the registry or by
        importing it
        >>> image = conn.ex_pull_image(image='mist/mistio')
        >>> image
        <NodeImage: id=0ec05daec99f, name=mist/mistio, driver=Docker  ...>

        """

        payload = {
        }
        data = json.dumps(payload)

        result = self.connection.request('/images/create?fromImage=%s' %
                                         (image), data=data, method='POST')
        if "errorDetail" in result.body:
            raise Exception(result.body)
        try:
            # get image id
            image_id = re.findall(
                r'{"status":"Download complete"'
                r',"progressDetail":{},"id":"\w+"}',
                result.body)[-1]
            image_id = json.loads(image_id).get('id')
        except:
            image_id = image

        image = NodeImage(id=image_id, name=image,
                          driver=self.connection.driver, extra={})
        return image

    def ex_delete_image(self, image):
        "Remove image from the filesystem"
        result = self.connection.request('/images/%s' % (image),
                                         method='DELETE')
        return result.status in VALID_RESPONSE_CODES

    def _to_node(self, data):
        """Convert node in Node instances
        """
        try:
            name = data.get('Names')[0].strip('/')
        except:
            name = data.get('Id')
        if 'Exited' in data.get('Status'):
            state = NodeState.STOPPED
        elif data.get('Status').startswith('Up '):
            state = NodeState.RUNNING
        else:
            state = NodeState.STOPPED

        ports = json.dumps(data.get('Ports', {}))
        extra = {
            'id': data.get('Id'),
            'status': data.get('Status'),
            'created': ts_to_str(data.get('Created')),
            'image': data.get('Image'),
            'ports': ports,
            'command': data.get('Command'),
            'sizerw': data.get('SizeRw'),
            'sizerootfs': data.get('SizeRootFs'),
        }

        node = (Node(id=data['Id'],
                     name=name,
                     state=state,
                     public_ips=[self.connection.host],
                     private_ips=[],
                     driver=self.connection.driver,
                     extra=extra))
        return node

    def _get_api_version(self):
        """
        Get the docker API version information
        """
        result = self.connection.request('/version').object
        api_version = result.get('ApiVersion')

        return api_version


def ts_to_str(timestamp):
    """Return a timestamp as a nicely formated datetime string."""
    date = datetime.datetime.fromtimestamp(timestamp)
    date_string = date.strftime("%d/%m/%Y %H:%M %Z")
    return date_string
