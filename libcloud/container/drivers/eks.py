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

try:
    import simplejson as json
except ImportError:
    import json

from libcloud.container.base import ContainerDriver, ContainerCluster
from libcloud.common.aws import SignedAWSConnection, AWSJsonResponse

__all__ = [
    'ElasticKubernetesDriver'
]


EKS_VERSION = '2017-11-01'
EKS_HOST = 'eks.%s.amazonaws.com'
ROOT = '/'
CLUSTERS_ENDPOINT = f'{ROOT}clusters/'


class EKSJsonConnection(SignedAWSConnection):
    version = EKS_VERSION
    host = EKS_HOST
    responseCls = AWSJsonResponse
    service_name = 'eks'


class ElasticKubernetesDriver(ContainerDriver):
    name = 'Amazon Elastic Kubernetes Service'
    website = 'https://aws.amazon.com/eks/'
    connectionCls = EKSJsonConnection
    supports_clusters = True

    def __init__(self, access_id, secret, region):
        super().__init__(access_id, secret, host=EKS_HOST % (region))
        self.region = region
        self.region_name = region

    def _ex_connection_class_kwargs(self):
        return {'signature_version': '4'}

    def list_clusters(self):
        """
        Get a list of clusters

        :rtype: ``list`` of :class:`libcloud.container.base.ContainerCluster`
        """
        names = self.connection.request(
            CLUSTERS_ENDPOINT).object['clusters']
        clusters = [self.get_cluster(name) for name in names]
        return clusters

    def get_cluster(self, name):
        """
        Get a cluster description

        :param  name: The name of the cluster
        :type   name: ``str``

        :rtype: ``list`` of :class:`libcloud.container.base.ContainerCluster`
        """
        endpoint = f'{CLUSTERS_ENDPOINT}{name}'
        data = self.connection.request(
            endpoint).object
        return self._to_cluster(data['cluster'])

    def create_cluster(self, name, role_arn, vpc_id, subnet_ids,
                       security_group_ids):
        """
        Create a cluster

        :param  name: The name of the cluster
        :type   name: ``str``

        :param role_arn: The Amazon Resource Name (ARN) of the IAM role that
                         provides permissions for the Kubernetes control plane
                         to make calls to AWS API operations on your behalf
        :type role_arn: ``str``

        :param vpc_id: The VPC associated with the cluster
        :type vpc_id: ``str``

        :param subnet_ids: The subnets associated with the cluster
        :type subnet_ids: ``list`` of ``str``

        :param security_group_ids: The security groups associated with the
                                   cross-account elastic network interfaces
                                   that are used to allow communication
                                   between your nodes and the Kubernetes
                                   control plane
        :type security_group_ids: ``list`` of ``str``
        """
        request = {
            'name': name,
            'roleArn': role_arn,
            'resourcesVpcConfig': {
                'vpcId': vpc_id,
                'subnetIds': subnet_ids,
                'securityGroudIds': security_group_ids,
            }
        }
        response = self.connection.request(
            CLUSTERS_ENDPOINT,
            method='POST',
            data=json.dumps(request)
        ).object
        return self._to_cluster(response['cluster'])

    def delete_cluster(self, name):
        """
        Delete a cluster

        :param  name: The name of the cluster
        :type   name: ``str``

        :return: ``True`` if the destroy was successful, otherwise ``False``
        :rtype: ``bool``
        """
        endpoint = f'{CLUSTERS_ENDPOINT}{name}'
        data = self.connection.request(endpoint, method='DELETE').object
        return data['cluster']['status'] == 'DELETING'

    def _to_cluster(self, data):
        return ContainerCluster(
            id=data['arn'],
            name=data['name'],
            driver=self.connection.driver,
            extra=data
        )
