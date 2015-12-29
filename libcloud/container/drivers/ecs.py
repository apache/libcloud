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
        List the installed container images, in ECS these are
        equivalent to the containers within task definitions.

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
        request = None
        if cluster is not None:
            request = {'cluster': cluster.id}
        if image is not None:
            request['family'] = image.name
        list_response = self.connection.request(
            ROOT,
            data=request,
            headers=self._get_headers('ListTasks')
        ).object
        containers = self.ex_list_containers_for_task(
            list_response['taskArns'])
        return containers

    def deploy_container(self, name, image, cluster=None,
                         parameters=None, start=True, ex_cpu=10, ex_memory=500,
                         ex_container_port=None, ex_host_port=None):
        """
        Creates a task definition from a container image that can be run
        in a cluster.

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
        data = {}
        data['containerDefinitions'] = [
            {
                "mountPoints": [],
                "name": name,
                "image": image.name,
                "cpu": ex_cpu,
                "environment": [],
                "memory": ex_memory,
                "portMappings": [
                    {
                        "containerPort": ex_container_port,
                        "hostPort": ex_host_port
                    }
                ],
                "essential": True,
                "volumesFrom": []
            }
        ]
        data['family'] = name
        response = self.connection.request(
            ROOT,
            data=data,
            headers=self._get_headers('RegisterTaskDefinition')
        ).object
        if start:
            return self.ex_start_task(
                response['taskDefinition']['taskDefinitionArn'])[0]
        else:
            return Container(
                id=None,
                name=name,
                image=image,
                state=ContainerState.RUNNING,
                ip_addresses=[],
                extra={
                    'taskDefinitionArn':
                        response['taskDefinition']['taskDefinitionArn']
                },
                driver=self.connection.driver
            )

    def get_container(self, id):
        """
        Get a container by ID

        :param id: The ID of the container to get
        :type  id: ``str``

        :rtype: :class:`Container`
        """
        containers = self.ex_list_containers_for_task([id])
        return containers[0]

    def start_container(self, container, count=1):
        """
        Start a deployed task

        :param container: The container to start
        :type  container: :class:`Container`

        :param count: Number of containers to start
        :type  count: ``int``

        :rtype: :class:`Container`
        """
        return self.ex_start_task(container.extra['taskDefinitionArn'], count)

    def stop_container(self, container):
        """
        Stop a deployed container

        :param container: The container to stop
        :type  container: :class:`Container`

        :rtype: :class:`Container`
        """
        request = {'task': container.extra['taskArn']}
        response = self.connection.request(
            ROOT,
            data=request,
            headers=self._get_headers('StopTask')
        ).object
        containers = []
        containers.extend(self._to_containers(
            response['task'],
            container.extra['taskDefinitionArn']))
        return containers

    def restart_container(self, container):
        """
        Restart a deployed container

        :param container: The container to restart
        :type  container: :class:`Container`

        :rtype: :class:`Container`
        """
        self.stop_container(container)
        return self.start_container(container)

    def destroy_container(self, container):
        """
        Destroy a deployed container

        :param container: The container to destroy
        :type  container: :class:`Container`

        :rtype: :class:`Container`
        """
        return self.stop_container(container)

    def ex_start_task(self, task_arn, count=1):
        """
        Run a task definition and get the containers

        :param task_arn: The task ARN to Run
        :type  task_arn: ``str``

        :param count: The number of containers to start
        :type  count: ``int``

        :rtype: ``list`` of :class:`Container`
        """
        request = None
        request = {'count': count,
                   'taskDefinition': task_arn}
        response = self.connection.request(
            ROOT,
            data=request,
            headers=self._get_headers('RunTask')
        ).object
        containers = []
        for task in response['tasks']:
            containers.extend(self._to_containers(task, task_arn))
        return containers

    def ex_list_containers_for_task(self, task_arns):
        """
        Get a list of containers by ID collection (ARN)

        :param task_arns: The list of ARNs
        :type  task_arns: ``list`` of ``str``

        :rtype: ``list`` of :class:`Container`
        """
        describe_request = {'tasks': task_arns}
        descripe_response = self.connection.request(
            ROOT,
            data=describe_request,
            headers=self._get_headers('DescribeTasks')
        ).object
        containers = []
        for task in descripe_response['tasks']:
            containers.extend(self._to_containers(
                task, task['taskDefinitionArn']))
        return containers

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

    def _to_containers(self, data, task_definition_arn):
        clusters = []
        for cluster in data['containers']:
            clusters.append(self._to_container(cluster, task_definition_arn))
        return clusters

    def _to_container(self, data, task_definition_arn):
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
                'taskArn': data['taskArn'],
                'taskDefinitionArn': task_definition_arn
            },
            driver=self.connection.driver
        )
