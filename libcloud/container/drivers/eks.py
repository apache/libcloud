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
EKS_TARGET_BASE = 'AmazonEC2ContainerServiceV%s' % \
                  (EKS_VERSION.replace('-', ''))


class EKSJsonConnection(SignedAWSConnection):
    version = EKS_VERSION
    host = EKS_HOST
    responseCls = AWSJsonResponse
    service_name = 'eks'

    def set_host(self, value):
        self.host = value
        self.connection.host = value


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
