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

import re
import base64

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
STS_HOST = 'sts.%s.amazonaws.com'
ROOT = '/'
CLUSTERS_ENDPOINT = f'{ROOT}clusters/'


class EKSCluster(ContainerCluster):
    def __init__(self, id, name, location, driver, config, extra,
                 credentials=None):
        super().__init__(id, name, driver, extra)
        self.location = location
        self.config = config
        self.credentials = credentials


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

        :rtype: ``list`` of :class:`EKSCluster`
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

        :rtype: :class:`EKSCluster`
        """
        endpoint = f'{CLUSTERS_ENDPOINT}{name}'
        data = self.connection.request(
            endpoint).object
        cluster = self._to_cluster(data['cluster'])
        cluster.credentials = self.get_cluster_credentials(cluster)
        return cluster

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

        :rtype: :class:`EKSCluster`
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

    def destroy_cluster(self, name):
        """
        Destroy a cluster

        :param  name: The name of the cluster
        :type   name: ``str``

        :return: ``True`` if the destroy was successful, otherwise ``False``
        :rtype: ``bool``
        """
        endpoint = f'{CLUSTERS_ENDPOINT}{name}'
        data = self.connection.request(endpoint, method='DELETE').object
        return data['cluster']['status'] == 'DELETING'

    def get_cluster_credentials(self, cluster):
        """
        Return cluster kubernetes credentials

        :keyword  name:  Cluster name or object
        :type     name:  ``str`` or :class:`EKSCluster`

        :rtype: ``dict``
        """
        if isinstance(cluster, str):
            cluster = self.get_cluster(cluster)
        host, port = cluster.extra['endpoint'], '443'
        token = self._get_cluster_token(cluster.name)
        credentials = dict(host=host, port=port, token=token)
        return credentials

    def _get_cluster_token(self, cluster_name):
        host = STS_HOST % (self.region)
        url = f'https://{host}/?Action=GetCallerIdentity&Version=2011-06-15'
        params = {
            'method': 'GET',
            'url': url,
            'body': {},
            'headers': {
                'x-k8s-aws-id': cluster_name
            },
            'context': {}
        }
        signed_url = self.connection.signer.generate_sts_presigned_url(
            params=params,
            host=host)
        base64_url = base64.urlsafe_b64encode(
            signed_url.encode('utf-8')).decode('utf-8')
        return 'k8s-aws-v1.' + re.sub(r'=*', '', base64_url)

    def _to_cluster(self, data):
        return EKSCluster(
            id=data.pop('arn'),
            name=data.pop('name'),
            location=self.region,
            driver=self.connection.driver,
            config={k: data.pop(k)
                    for k in list(data) if k.endswith('Config')},
            extra=data
        )
