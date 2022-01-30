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
import hashlib

from libcloud.container.base import (
    Container,
    ContainerDriver,
    ContainerImage,
    ContainerCluster,
)

from libcloud.common.kubernetes import KubernetesException
from libcloud.common.kubernetes import KubernetesBasicAuthConnection
from libcloud.common.kubernetes import KubernetesDriverMixin

from libcloud.container.providers import Provider
from libcloud.container.types import ContainerState

from libcloud.compute.types import NodeState
from libcloud.compute.base import Node
from libcloud.compute.base import NodeSize
from libcloud.compute.base import NodeImage

from libcloud.utils.misc import to_n_cpus
from libcloud.utils.misc import to_cpu_str
from libcloud.utils.misc import to_memory_str
from libcloud.utils.misc import to_n_bytes

__all__ = ["KubernetesContainerDriver"]


ROOT_URL = "/api/"


def sum_resources(self, *resource_dicts):
    total_cpu = 0
    total_memory = 0
    for rd in resource_dicts:
        total_cpu += to_n_cpus(rd.get("cpu", "0m"))
        total_memory += to_n_bytes(rd.get("memory", "0K"))
    return {"cpu": to_cpu_str(total_cpu), "memory": to_memory_str(total_memory)}


class KubernetesPod(object):
    def __init__(
        self,
        id,
        name,
        containers,
        namespace,
        state,
        ip_addresses,
        created_at,
        node_name,
        extra,
    ):
        """
        A Kubernetes pod
        """
        self.id = id
        self.name = name
        self.containers = containers
        self.namespace = namespace
        self.state = state
        self.ip_addresses = ip_addresses
        self.created_at = created_at
        self.node_name = node_name
        self.extra = extra


class KubernetesNamespace(ContainerCluster):
    """
    A Kubernetes namespace
    """


class KubernetesContainerDriver(KubernetesDriverMixin, ContainerDriver):
    type = Provider.KUBERNETES
    name = "Kubernetes"
    website = "http://kubernetes.io"
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
                ROOT_URL + "v1/pods", enforce_unicode_response=True
            ).object
        except Exception as exc:
            errno = getattr(exc, "errno", None)
            if errno == 111:
                raise KubernetesException(
                    errno,
                    "Make sure kube host is accessible" "and the API port is correct",
                )
            raise

        pods = [self._to_pod(value) for value in result["items"]]
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

    def list_namespaces(self):
        """
        Get a list of namespaces that pods can be deployed into

        :rtype: ``list`` of :class:`.KubernetesNamespace`
        """
        try:
            result = self.connection.request(ROOT_URL + "v1/namespaces/").object
        except Exception as exc:
            errno = getattr(exc, "errno", None)
            if errno == 111:
                raise KubernetesException(
                    errno,
                    "Make sure kube host is accessible" "and the API port is correct",
                )
            raise

        namespaces = [self._to_namespace(value) for value in result["items"]]
        return namespaces

    def get_namespace(self, id):
        """
        Get a namespace by ID

        :param id: The ID of the namespace to get
        :type  id: ``str``

        :rtype: :class:`.KubernetesNamespace`
        """
        result = self.connection.request(ROOT_URL + "v1/namespaces/%s" % id).object

        return self._to_namespace(result)

    def delete_namespace(self, namespace):
        """
        Delete a namespace

        :return: ``True`` if the destroy was successful, otherwise ``False``.
        :rtype: ``bool``
        """
        self.connection.request(
            ROOT_URL + "v1/namespaces/%s" % namespace.id, method="DELETE"
        ).object
        return True

    def create_namespace(self, name, location=None):
        """
        Create a namespace

        :param  name: The name of the namespace
        :type   name: ``str``

        :param  location: The location to create the namespace in
        :type   location: :class:`.ClusterLocation`

        :rtype: :class:`.KubernetesNamespace`
        """
        request = {"metadata": {"name": name}}
        result = self.connection.request(
            ROOT_URL + "v1/namespaces", method="POST", data=json.dumps(request)
        ).object
        return self._to_namespace(result)

    def deploy_container(
        self, name, image, namespace=None, parameters=None, start=True
    ):
        """
        Deploy an installed container image.
        In kubernetes this deploys a single container Pod.
        https://cloud.google.com/container-engine/docs/pods/single-container

        :param name: The name of the new container
        :type  name: ``str``

        :param image: The container image to deploy
        :type  image: :class:`.ContainerImage`

        :param namespace: The namespace to deploy to, None is default
        :type  namespace: :class:`.KubernetesNamespace`

        :param parameters: Container Image parameters
        :type  parameters: ``str``

        :param start: Start the container on deployment
        :type  start: ``bool``

        :rtype: :class:`.Container`
        """
        if namespace is None:
            namespace = "default"
        else:
            namespace = namespace.id
        request = {
            "metadata": {"name": name},
            "spec": {"containers": [{"name": name, "image": image.name}]},
        }
        result = self.connection.request(
            ROOT_URL + "v1/namespaces/%s/pods" % namespace,
            method="POST",
            data=json.dumps(request),
        ).object
        return self._to_namespace(result)

    def destroy_container(self, container):
        """
        Destroy a deployed container. Because the containers are single
        container pods, this will delete the pod.

        :param container: The container to destroy
        :type  container: :class:`.Container`

        :rtype: ``bool``
        """
        return self.ex_destroy_pod(container.extra["namespace"], container.extra["pod"])

    def ex_list_pods(self, fetch_metrics=False):
        """
        List available Pods

        :rtype: ``list`` of :class:`.KubernetesPod`
        """
        result = self.connection.request(
            ROOT_URL + "v1/pods", enforce_unicode_response=True
        ).object
        metrics = None
        if fetch_metrics:
            try:
                metrics = {
                    (
                        metric["metadata"]["name"],
                        metric["metadata"]["namespace"],
                    ): metric["containers"]
                    for metric in self.ex_list_pods_metrics()
                }
            except Exception:
                pass

        return [self._to_pod(value, metrics=metrics) for value in result["items"]]

    def ex_destroy_pod(self, namespace, pod_name):
        """
        Delete a pod and the containers within it.
        """
        self.connection.request(
            ROOT_URL + "v1/namespaces/%s/pods/%s" % (namespace, pod_name),
            method="DELETE",
        ).object
        return True

    def ex_list_nodes(self):
        """
        List available Nodes

        :rtype: ``list`` of :class:`.Node`
        """
        result = self.connection.request(
            ROOT_URL + "v1/nodes", enforce_unicode_response=True
        ).object
        return [self._to_node(node) for node in result["items"]]

    def ex_destroy_node(self, node_name):
        """
        Destroy a node.
        """
        self.connection.request(
            ROOT_URL + f"v1/nodes/{node_name}", method="DELETE"
        ).object
        return True

    def ex_get_version(self):
        """Get Kubernetes version"""
        return self.connection.request("/version").object["gitVersion"]

    def ex_list_nodes_metrics(self):
        return self.connection.request(
            "/apis/metrics.k8s.io/v1beta1/nodes", enforce_unicode_response=True
        ).object["items"]

    def ex_list_pods_metrics(self):
        return self.connection.request(
            "/apis/metrics.k8s.io/v1beta1/pods", enforce_unicode_response=True
        ).object["items"]

    def ex_list_services(self):
        return self.connection.request(
            ROOT_URL + "v1/services", enforce_unicode_response=True
        ).object["items"]

    def _to_node(self, data):
        """
        Convert an API node data object to a `Node` object
        """
        ID = data["metadata"]["uid"]
        name = data["metadata"]["name"]
        driver = self.connection.driver
        memory = data["status"].get("capacity", {}).get("memory", "0K")
        cpu = data["status"].get("capacity", {}).get("cpu", "1")
        if isinstance(cpu, str) and not cpu.isnumeric():
            cpu = to_n_cpus(cpu)
        image_name = data["status"]["nodeInfo"].get("osImage")
        image = NodeImage(image_name, image_name, driver)
        size_name = f"{cpu} vCPUs, {memory} Ram"
        size_id = hashlib.md5(size_name.encode("utf-8")).hexdigest()
        extra_size = {"cpus": cpu}
        size = NodeSize(
            id=size_id,
            name=size_name,
            ram=memory,
            disk=0,
            bandwidth=0,
            price=0,
            driver=driver,
            extra=extra_size,
        )
        extra = {"memory": memory, "cpu": cpu}
        extra["os"] = data["status"]["nodeInfo"].get("operatingSystem")
        extra["kubeletVersion"] = data["status"]["nodeInfo"]["kubeletVersion"]
        extra["provider_id"] = data["spec"]["providerID"]
        for condition in data["status"]["conditions"]:
            if condition["type"] == "Ready" and condition["status"] == "True":
                state = NodeState.RUNNING
                break
        else:
            state = NodeState.UNKNOWN
        public_ips, private_ips = [], []
        for address in data["status"]["addresses"]:
            if address["type"] == "InternalIP":
                private_ips.append(address["address"])
            elif address["type"] == "ExternalIP":
                public_ips.append(address["address"])
        created_at = datetime.datetime.strptime(
            data["metadata"]["creationTimestamp"], "%Y-%m-%dT%H:%M:%SZ"
        )
        return Node(
            id=ID,
            name=name,
            state=state,
            public_ips=public_ips,
            private_ips=private_ips,
            driver=driver,
            image=image,
            size=size,
            extra=extra,
            created_at=created_at,
        )

    def _to_pod(self, data, metrics=None):
        """
        Convert an API response to a Pod object
        """
        id_ = data["metadata"]["uid"]
        name = data["metadata"]["name"]
        namespace = data["metadata"]["namespace"]
        state = data["status"]["phase"].lower()
        node_name = data["spec"].get("nodeName")
        container_statuses = data["status"].get("containerStatuses", {})
        containers = []
        extra = {"resources": {}}
        if metrics:
            try:
                extra["metrics"] = metrics[name, namespace]
            except KeyError:
                pass

        # response contains the status of the containers in a separate field
        for container in data["spec"]["containers"]:
            if container_statuses:
                spec = list(
                    filter(lambda i: i["name"] == container["name"], container_statuses)
                )[0]
            else:
                spec = container_statuses
            container_obj = self._to_container(container, spec, data)
            # Calculate new resources
            resources = extra["resources"]
            container_resources = container_obj.extra.get("resources", {})
            resources["limits"] = sum_resources(
                resources.get("limits", {}), container_resources.get("limits", {})
            )
            extra["resources"]["requests"] = sum_resources(
                resources.get("requests", {}), container_resources.get("requests", {})
            )
            containers.append(container_obj)
        ip_addresses = [ip_dict["ip"] for ip_dict in data["status"].get("podIPs", [])]
        created_at = datetime.datetime.strptime(
            data["metadata"]["creationTimestamp"], "%Y-%m-%dT%H:%M:%SZ"
        )

        return KubernetesPod(
            id=id_,
            name=name,
            namespace=namespace,
            state=state,
            ip_addresses=ip_addresses,
            containers=containers,
            created_at=created_at,
            node_name=node_name,
            extra=extra,
        )

    def _to_container(self, data, container_status, pod_data):
        """
        Convert container in Container instances
        """
        state = container_status.get("state")
        created_at = None
        if state:
            started_at = list(state.values())[0].get("startedAt")
            if started_at:
                created_at = datetime.datetime.strptime(
                    started_at, "%Y-%m-%dT%H:%M:%SZ"
                )
        extra = {
            "pod": pod_data["metadata"]["name"],
            "namespace": pod_data["metadata"]["namespace"],
        }
        resources = data.get("resources")
        if resources:
            extra["resources"] = resources
        return Container(
            id=container_status.get("containerID") or data["name"],
            name=data["name"],
            image=ContainerImage(
                id=container_status.get("imageID") or data["image"],
                name=data["image"],
                path=None,
                version=None,
                driver=self.connection.driver,
            ),
            ip_addresses=None,
            state=(
                ContainerState.RUNNING if container_status else ContainerState.UNKNOWN
            ),
            driver=self.connection.driver,
            created_at=created_at,
            extra=extra,
        )

    def _to_namespace(self, data):
        """
        Convert an API node data object to a `KubernetesNamespace` object
        """
        return KubernetesNamespace(
            id=data["metadata"]["name"],
            name=data["metadata"]["name"],
            driver=self.connection.driver,
            extra={"phase": data["status"]["phase"]},
        )


def ts_to_str(timestamp):
    """
    Return a timestamp as a nicely formated datetime string.
    """
    date = datetime.datetime.fromtimestamp(timestamp)
    date_string = date.strftime("%d/%m/%Y %H:%M %Z")
    return date_string
