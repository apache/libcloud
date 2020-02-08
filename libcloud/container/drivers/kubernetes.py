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

import datetime
import json

from libcloud.container.base import (Container, ContainerDriver,
                                     ContainerImage, ContainerCluster)

from libcloud.common.kubernetes import KubernetesException
from libcloud.common.kubernetes import KubernetesBasicAuthConnection
from libcloud.common.kubernetes import KubernetesDriverMixin

from libcloud.container.providers import Provider
from libcloud.container.types import ContainerState

__all__ = [
    'KubernetesContainerDriver'
]


ROOT_URL = '/api/'


class KubernetesPod(object):
    def __init__(self, name, containers, namespace):
        """
        A Kubernetes pod
        """
        self.name = name
        self.containers = containers
        self.namespace = namespace


class KubernetesContainerDriver(KubernetesDriverMixin, ContainerDriver):
    type = Provider.KUBERNETES
    name = 'Kubernetes'
    website = 'http://kubernetes.io'
    connectionCls = KubernetesBasicAuthConnection
    supports_clusters = True

    def list_containers(self, image=None, all=True):
        """
        List the deployed container images

        :param image: Filter to containers with a certain image
        :type  image: :class:`libcloud.container.base.ContainerImage`

        :param all: Show all container (including stopped ones)
        :type  all: ``bool``

        :rtype: ``list`` of :class:`libcloud.container.base.Container`
        """
        try:
            result = self.connection.request(
                ROOT_URL + "v1/pods").object
        except Exception as exc:
            errno = getattr(exc, 'errno', None)
            if errno == 111:
                raise KubernetesException(
                    errno,
                    'Make sure kube host is accessible'
                    'and the API port is correct')
            raise

        pods = [self._to_pod(value) for value in result['items']]
        containers = []
        for pod in pods:
            containers.extend(pod.containers)
        return containers

    def get_container(self, id):
        """
        Get a container by ID

        :param id: The ID of the container to get
        :type  id: ``str``

        :rtype: :class:`libcloud.container.base.Container`
        """
        containers = self.list_containers()
        match = [container for container in containers if container.id == id]
        return match[0]

    def list_clusters(self):
        """
        Get a list of namespaces that pods can be deployed into

        :param  location: The location to search in
        :type   location: :class:`libcloud.container.base.ClusterLocation`

        :rtype: ``list`` of :class:`libcloud.container.base.ContainerCluster`
        """
        try:
            result = self.connection.request(
                ROOT_URL + "v1/namespaces/").object
        except Exception as exc:
            errno = getattr(exc, 'errno', None)
            if errno == 111:
                raise KubernetesException(
                    errno,
                    'Make sure kube host is accessible'
                    'and the API port is correct')
            raise

        clusters = [self._to_cluster(value) for value in result['items']]
        return clusters

    def get_cluster(self, id):
        """
        Get a cluster by ID

        :param id: The ID of the cluster to get
        :type  id: ``str``

        :rtype: :class:`libcloud.container.base.ContainerCluster`
        """
        result = self.connection.request(ROOT_URL + "v1/namespaces/%s" %
                                         id).object

        return self._to_cluster(result)

    def destroy_cluster(self, cluster):
        """
        Delete a cluster (namespace)

        :return: ``True`` if the destroy was successful, otherwise ``False``.
        :rtype: ``bool``
        """
        self.connection.request(ROOT_URL + "v1/namespaces/%s" %
                                cluster.id, method='DELETE').object
        return True

    def create_cluster(self, name, location=None):
        """
        Create a container cluster (a namespace)

        :param  name: The name of the cluster
        :type   name: ``str``

        :param  location: The location to create the cluster in
        :type   location: :class:`.ClusterLocation`

        :rtype: :class:`.ContainerCluster`
        """
        request = {
            'metadata': {
                'name': name
            }
        }
        result = self.connection.request(ROOT_URL + "v1/namespaces",
                                         method='POST',
                                         data=json.dumps(request)).object
        return self._to_cluster(result)

    def deploy_container(self, name, image, cluster=None,
                         parameters=None, start=True):
        """
        Deploy an installed container image.
        In kubernetes this deploys a single container Pod.
        https://cloud.google.com/container-engine/docs/pods/single-container

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
        if cluster is None:
            namespace = 'default'
        else:
            namespace = cluster.id
        request = {
            "metadata": {
                "name": name
            },
            "spec": {
                "containers": [
                    {
                        "name": name,
                        "image": image.name
                    }
                ]
            }
        }
        result = self.connection.request(ROOT_URL + "v1/namespaces/%s/pods"
                                         % namespace,
                                         method='POST',
                                         data=json.dumps(request)).object
        return self._to_cluster(result)

    def destroy_container(self, container):
        """
        Destroy a deployed container. Because the containers are single
        container pods, this will delete the pod.

        :param container: The container to destroy
        :type  container: :class:`.Container`

        :rtype: ``bool``
        """
        return self.ex_destroy_pod(container.extra['namespace'],
                                   container.extra['pod'])

    def ex_list_pods(self):
        """
        List available Pods

        :rtype: ``list`` of :class:`.KubernetesPod`
        """
        result = self.connection.request(ROOT_URL + "v1/pods").object
        return [self._to_pod(value) for value in result['items']]

    def ex_destroy_pod(self, namespace, pod_name):
        """
        Delete a pod and the containers within it.
        """
        self.connection.request(
            ROOT_URL + "v1/namespaces/%s/pods/%s" % (
                namespace, pod_name),
            method='DELETE').object
        return True

    def _to_pod(self, data):
        """
        Convert an API response to a Pod object
        """
        container_statuses = data['status']['containerStatuses']
        containers = []
        # response contains the status of the containers in a separate field
        for container in data['spec']['containers']:
            spec = list(filter(lambda i: i['name'] == container['name'],
                               container_statuses))[0]
            containers.append(
                self._to_container(container, spec, data)
            )
        return KubernetesPod(
            name=data['metadata']['name'],
            namespace=data['metadata']['namespace'],
            containers=containers)

    def _to_container(self, data, container_status, pod_data):
        """
        Convert container in Container instances
        """
        return Container(
            id=container_status['containerID'],
            name=data['name'],
            image=ContainerImage(
                id=container_status['imageID'],
                name=data['image'],
                path=None,
                version=None,
                driver=self.connection.driver),
            ip_addresses=None,
            state=ContainerState.RUNNING,
            driver=self.connection.driver,
            extra={
                'pod': pod_data['metadata']['name'],
                'namespace': pod_data['metadata']['namespace']
            })

    def _to_cluster(self, data):
        """
        Convert namespace to a cluster
        """
        metadata = data['metadata']
        status = data['status']
        return ContainerCluster(
            id=metadata['name'],
            name=metadata['name'],
            driver=self.connection.driver,
            extra={'phase': status['phase']})


def ts_to_str(timestamp):
    """
    Return a timestamp as a nicely formated datetime string.
    """
    date = datetime.datetime.fromtimestamp(timestamp)
    date_string = date.strftime("%d/%m/%Y %H:%M %Z")
    return date_string
