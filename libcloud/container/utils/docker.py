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

from base64 import b64encode

from libcloud.common.base import Connection, JsonResponse
from libcloud.container.base import ContainerImage

__all__ = [
    'RegistryClient',
    'HubClient'
]


class DockerHubConnection(Connection):
    responseCls = JsonResponse

    def __init__(self, host, username=None, password=None,
                 secure=True,
                 port=None, url=None, timeout=None,
                 proxy_url=None, backoff=None, retry_delay=None):
        super(DockerHubConnection, self).__init__(secure=secure, host=host,
                                                  port=port, url=url,
                                                  timeout=timeout,
                                                  proxy_url=proxy_url,
                                                  backoff=backoff,
                                                  retry_delay=retry_delay)
        self.username = username
        self.password = password

    def add_default_headers(self, headers):
        headers['Content-Type'] = 'application/json'
        if self.username is not None:
            authstr = 'Basic ' + str(
                b64encode(
                    ('%s:%s' % (self.username,
                                self.password))
                    .encode('latin1'))
                .strip()
            )
            headers['Authorization'] = authstr
        return headers


class RegistryClient(object):
    """
    A client for the Docker v2 registry API
    """
    connectionCls = DockerHubConnection

    def __init__(self, host, username=None, password=None, **kwargs):
        """
        Construct a Docker hub client

        :param username: (optional) Your Hub account username
        :type  username: ``str``

        :param password: (optional) Your hub account password
        :type  password: ``str``
        """
        self.connection = self.connectionCls(host,
                                             username,
                                             password,
                                             **kwargs)

    def list_images(self, repository_name, namespace='library', max_count=100):
        """
        List the tags (versions) in a repository

        :param  repository_name: The name of the repository e.g. 'ubuntu'
        :type   repository_name: ``str``

        :param  namespace: (optional) The docker namespace
        :type   namespace: ``str``

        :param  max_count: The maximum number of records to return
        :type   max_count: ``int``

        :return: A list of images
        :rtype: ``list`` of :class:`libcloud.container.base.ContainerImage`
        """
        path = '/v2/repositories/%s/%s/tags/?page=1&page_size=%s' \
               % (namespace, repository_name, max_count)
        response = self.connection.request(path)
        images = []
        for image in response.object['results']:
            images.append(self._to_image(repository_name, image))
        return images

    def get_repository(self, repository_name, namespace='library'):
        """
        Get the information about a specific repository

        :param  repository_name: The name of the repository e.g. 'ubuntu'
        :type   repository_name: ``str``

        :param  namespace: (optional) The docker namespace
        :type   namespace: ``str``

        :return: The details of the repository
        :rtype: ``object``
        """
        path = '/v2/repositories/%s/%s/' % (namespace, repository_name)
        response = self.connection.request(path)
        return response.object

    def get_image(self, repository_name, tag='latest', namespace='library'):
        """
        Get an image from a repository with a specific tag

        :param repository_name: The name of the repository, e.g. ubuntu
        :type  repository_name: ``str``

        :param  tag: (optional) The image tag (defaults to latest)
        :type   tag: ``str``

        :param  namespace: (optional) The docker namespace
        :type   namespace: ``str``

        :return: A container image
        :rtype: :class:`libcloud.container.base.ContainerImage`
        """
        path = '/v2/repositories/%s/%s/tags/%s/' \
               % (namespace, repository_name, tag)
        response = self.connection.request(path)
        return self._to_image(repository_name, response.object)

    def _to_image(self, repository_name, obj):
        path = '%s/%s:%s' % (self.connection.host,
                             repository_name,
                             obj['name'])
        return ContainerImage(
            id=obj['id'],
            path=path,
            name=path,
            version=obj['name'],
            extra={
                'full_size': obj['full_size']
            },
            driver=None
        )


class HubClient(RegistryClient):
    """
    A client for the Docker Hub API

    The hub is based on the v2 registry API
    """
    host = 'registry.hub.docker.com'

    def __init__(self, username=None, password=None, **kwargs):
        """
        Construct a Docker hub client

        :param username: (optional) Your Hub account username
        :type  username: ``str``

        :param password: (optional) Your hub account password
        :type  password: ``str``
        """
        super(HubClient, self).__init__(self.host, username,
                                        password, **kwargs)
