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

from requests.auth import HTTPBasicAuth
import requests

from libcloud.container.base import ContainerImage

__all__ = [
    'HubClient'
]


class HubClient(object):
    """
    A client for the Docker Hub API

    The hub is based on the v1 registry API
    """
    host = 'registry.hub.docker.com'
    base_url = 'https://%s/' % (host)

    def __init__(self, username=None, password=None):
        """
        Construct a Docker hub client

        :param username: (optional) Your Hub account username
        :type  username: ``str``

        :param password: (optional) Your hub account password
        :type  password: ``str``
        """
        if username is not None:
            self.auth = HTTPBasicAuth(username, password)
        else:
            self.auth = None

    def list_tags(self, repository_name, namespace='library', max_count=100):
        """
        List the tags (versions) in a repository

        :param  repository_name: The name of the repository e.g. 'ubuntu'
        :type   repository_name: ``str``

        :param  namespace: (optional) The docker namespace
        :type   namespace: ``str``

        :param  max_count: The maximum number of records to return
        :type   max_count: ``int``

        :return: A list of tags
        :rtype: ``list`` of ``object``
        """
        path = 'v2/repositories/%s/%s/tags/?page=1&page_size=%s' \
               % (namespace, repository_name, max_count)
        response = requests.get(self.base_url + path, auth=self.auth)
        return response.json().results

    def list_image_ids(self, repository_name, namespace='library'):
        """
        List the image IDs (versions) in a repository

        :param  repository_name: The name of the repository e.g. 'ubuntu'
        :type   repository_name: ``str``

        :param  namespace: (optional) The docker namespace
        :type   namespace: ``str``

        :return: A list of ids
        :rtype: ``list`` of ``object``
        """
        path = 'v1/repositories/%s/%s/images' % (namespace, repository_name)
        response = requests.get(self.base_url + path, auth=self.auth)
        return response.json()

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
        path = 'v2/repositories/%s/%s' % (namespace, repository_name)
        response = requests.get(self.base_url + path, auth=self.auth)
        return response.json()

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
        path = 'v2/repositories/%s/%s/tags/%s' \
               % (namespace, repository_name, tag)
        response = requests.get(self.base_url + path, auth=self.auth)
        obj = response.json()
        path = '%s/%s:%s' % (self.host, repository_name, tag)
        return ContainerImage(
            id=obj['id'],
            path=path,
            name=path,
            version=tag,
            extra={
                'full_size': obj['full_size']
            },
            driver=None
        )
