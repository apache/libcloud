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

__all__ = [
    'ElasticContainerDriver'
]


from libcloud.container.base import (ContainerDriver, Container,
                                     ContainerCluster, ContainerImage)
from libcloud.container.types import ContainerState
from libcloud.common.base import JsonResponse
from libcloud.common.aws import SignedAWSConnection


VERSION = '2014-11-13'
HOST = 'ecs.%s.amazonaws.com'
ROOT = '/%s/' % (VERSION)
TARGET_BASE = 'AmazonEC2ContainerServiceV%s' % (VERSION.replace('-', ''))


class ECSResponse(JsonResponse):
    """
    Amazon ECS response class.
    ECS API uses JSON unlike the s3, elb drivers
    """


class ECSConnection(SignedAWSConnection):
    version = VERSION
    host = HOST
    responseCls = ECSResponse
    service_name = 'ecs'


class ElasticContainerDriver(ContainerDriver):
    name = 'Amazon Elastic Container Service'
    website = 'https://aws.amazon.com/ecs/details/'
    connectionCls = ECSConnection
    supports_clusters = False
    status_map = {
        'RUNNING': ContainerState.RUNNING
    }

    def __init__(self, access_id, secret, region):
        super(ElasticContainerDriver, self).__init__(access_id, secret)
        self.region = region
        self.connection.host = HOST % (region)

    def list_clusters(self):
        """
        Get a list of potential locations to deploy clusters into

        :param  location: The location to search in
        :type   location: :class:`ClusterLocation`

        :rtype: ``list`` of :class:`ContainerCluster`
        """
        params = {'Action': 'DescribeClusters'}
        data = self.connection.request(
            ROOT,
            params=params,
            headers=self._get_headers(params['Action'])
            ).object
        return self._to_clusters(data)

    def create_cluster(self, name, location=None):
        """
        Create a container cluster

        :param  name: The name of the cluster
        :type   name: ``str``

        :param  location: The location to create the cluster in
        :type   location: :class:`ClusterLocation`

        :rtype: :class:`ContainerCluster`
        """
        params = {'Action': 'CreateCluster'}
        request = {'clusterName': name}
        response = self.connection.request(
            ROOT,
            params=params,
            data=request,
            headers=self._get_headers(params['Action'])
            ).object
        return self._to_cluster(response['cluster'])

    def destroy_cluster(self, cluster):
        """
        Delete a cluster

        :return: ``True`` if the destroy was successful, otherwise ``False``.
        :rtype: ``bool``
        """
        params = {'Action': 'DeleteCluster'}
        request = {'cluster': cluster.id}
        data = self.connection.request(
            ROOT,
            params=params,
            data=request,
            headers=self._get_headers(params['Action'])
            ).object
        return data['cluster']['status'] == 'INACTIVE'

    def install_image(self, path):
        """
        Install a container image from a remote path.

        :param path: Path to the container image
        :type  path: ``str``

        :rtype: :class:`ContainerImage`
        """
        raise NotImplementedError(
            'install_image not implemented for this driver')

    def list_images(self):
        """
        List the installed container images

        :rtype: ``list`` of :class:`ContainerImage`
        """
        raise NotImplementedError(
            'list_images not implemented for this driver')

    def list_containers(self, image=None, cluster=None):
        """
        List the deployed container images

        :param image: Filter to containers with a certain image
        :type  image: :class:`ContainerImage`

        :param cluster: Filter to containers in a cluster
        :type  cluster: :class:`ContainerCluster`

        :rtype: ``list`` of :class:`Container`
        """
        params = {'Action': 'DescribeTasks'}
        request = None
        if cluster is not None:
            request = {'cluster': cluster.id}
        response = self.connection.request(
            ROOT,
            params=params,
            data=request,
            headers=self._get_headers(params['Action'])
            ).object
        containers = []
        for task in response['tasks']:
            containers.extend(self._to_containers(task))
        return containers

    def deploy_container(self, name, image, cluster=None,
                         parameters=None, start=True):
        """
        Deploy an installed container image

        :param name: The name of the new container
        :type  name: ``str``

        :param image: The container image to deploy
        :type  image: :class:`ContainerImage`

        :param cluster: The cluster to deploy to, None is default
        :type  cluster: :class:`ContainerCluster`

        :param parameters: Container Image parameters
        :type  parameters: ``str``

        :param start: Start the container on deployment
        :type  start: ``bool``

        :rtype: :class:`Container`
        """
        raise NotImplementedError(
            'deploy_container not implemented for this driver')

    def get_container(self, id):
        """
        Get a container by ID

        :param id: The ID of the container to get
        :type  id: ``str``

        :rtype: :class:`Container`
        """
        raise NotImplementedError(
            'get_container not implemented for this driver')

    def start_container(self, container):
        """
        Start a deployed container

        :param container: The container to start
        :type  container: :class:`Container`

        :rtype: :class:`Container`
        """
        raise NotImplementedError(
            'start_container not implemented for this driver')

    def stop_container(self, container):
        """
        Stop a deployed container

        :param container: The container to stop
        :type  container: :class:`Container`

        :rtype: :class:`Container`
        """
        raise NotImplementedError(
            'stop_container not implemented for this driver')

    def restart_container(self, container):
        """
        Restart a deployed container

        :param container: The container to restart
        :type  container: :class:`Container`

        :rtype: :class:`Container`
        """
        raise NotImplementedError(
            'restart_container not implemented for this driver')

    def destroy_container(self, container):
        """
        Destroy a deployed container

        :param container: The container to destroy
        :type  container: :class:`Container`

        :rtype: :class:`Container`
        """
        raise NotImplementedError(
            'destroy_container not implemented for this driver')

    def _get_headers(self, action):
        return {'x-amz-target': '%s.%s' %
                (TARGET_BASE, action)}

    def _to_clusters(self, data):
        clusters = []
        for cluster in data['clusters']:
            clusters.append(self._to_cluster(cluster))
        return clusters

    def _to_cluster(self, data):
        return ContainerCluster(
            id=data['clusterArn'],
            name=data['clusterName'],
            driver=self.connection.driver
        )

    def _to_containers(self, data):
        clusters = []
        for cluster in data['containers']:
            clusters.append(self._to_container(cluster))
        return clusters

    def _to_container(self, data):
        return Container(
            id=data['containerArn'],
            name=data['name'],
            image=ContainerImage(
                id=None,
                name=data['name'],
                path=None,
                version=None,
                driver=self.connection.driver
                ),
            ip_addresses=None,
            state=self.status_map.get(data['lastStatus'], None),
            extra={
                'taskArn': data['taskArn']
            },
            driver=self.connection.driver
        )
