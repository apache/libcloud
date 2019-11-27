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

from libcloud.container.base import (Container, ContainerDriver, ContainerImage)
from libcloud.container.providers import Provider
from libcloud.container.types import ContainerState

class LXDConnection:
    pass

class LXDContainerDriver(ContainerDriver):
    """
    Driver for LXC containers
    """
    type = Provider.LXC
    name = 'LXC'
    website = 'https://linuxcontainers.org/'
    connectionCls = LXDConnection
    supports_clusters = False
    version = '1.0'

    def __init__(self, key='', secret='', secure=False, 
                 host='localhost', port='8443', 
                 key_file=None,
                 cert_file=None, ca_cert=None, **kwargs):

        super(LXDContainerDriver, self).__init__(key=key,
                                                 secret=secret,
                                                 secure=secure, 
                                                 host=host,
                                                 port=port,
                                                 key_file=key_file,
                                                 cert_file=cert_file, 
                                                 **kwargs)
    
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
        result = self.connection.request("/v%s/containers/%s/" %
                                         (self.version, id)).object

        return self._to_container(result)

    def start_container(self, container):
        """
        Start a ontainer

        :param container: The container to start
        :type  container: :class:`libcloud.container.base.Container`

        :rtype: :class:`libcloud.container.base.Container`
        """
        return container

    def stop_container(self, container):
        """
        Stop a container

        :param container: The container to be stopped
        :type  container: :class:`libcloud.container.base.Container`

        :return: The container refreshed with current data
        :rtype: :class:`libcloud.container.base.Container
        """
        result = self.connection.request('/v%s/containers/%s/state?action=stop&\
                                         timeout=30&force=true&stateful=true' %
                                         (self.version, container.name),
                                         method='PUT')
         # we have an error                                         
        if result['type'] == 'error':
            pass
        return self.get_container(id=container.name)

    def list_containers(self, image=None, cluster=None):
        """
        List the deployed container images

        :param image: Filter to containers with a certain image
        :type  image: :class:`.ContainerImage`

        :param cluster: Filter to containers in a cluster
        :type  cluster: :class:`.ContainerCluster`

        :rtype: ``list`` of :class:`.Container`
        """
        raise NotImplementedError(
            'list_containers not implemented for this driver')

    def restart_container(self, container):
        """
        Restart a deployed container

        :param container: The container to restart
        :type  container: :class:`.Container`

        :rtype: :class:`.Container`
        """
        raise NotImplementedError(
            'restart_container not implemented for this driver')

    def destroy_container(self, container):
        """
        Destroy a deployed container

        :param container: The container to destroy
        :type  container: :class:`.Container`

        :rtype: :class:`.Container`
        """
        raise NotImplementedError(
            'destroy_container not implemented for this driver')


    def _to_container(self, data):
        """
        Convert container in Container instances
        """
        arch = data['architecture']
        config = data['config']
        created_at = data['created_at']
        name = data['name']
        state=data['status']

        if state == 'Running':
            state = ContainerState.RUNNING
        else:
            state = ContainerState.STOPPED

        extra = dict()
        image = ContainerImage(id="?", name="?", path="/", version="/",
                               driver="/", extra=None)

        container = Container(driver=self, name=name, id=name,
                              state=state, image=image, ip_addresses=[], extra=extra)

        return container
