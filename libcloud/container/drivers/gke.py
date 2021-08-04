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

from libcloud.common.google import GoogleOAuth2Credential
from libcloud.container.base import ContainerCluster
from libcloud.container.providers import Provider
from libcloud.container.drivers.kubernetes import KubernetesContainerDriver
from libcloud.common.google import GoogleResponse
from libcloud.common.google import GoogleBaseConnection
API_VERSION = 'v1'


class GKECluster(ContainerCluster):
    def __init__(self, id, name, node_count, location, driver, config, extra):
        super().__init__(id, name, driver, extra)
        self.node_count = node_count
        self.location = location
        self.config = config


class GKEResponse(GoogleResponse):
    pass


class GKEConnection(GoogleBaseConnection):
    """
    Connection class for the GKE driver.

    GKEConnection extends :class:`google.GoogleBaseConnection` for 3 reasons:
      1. modify request_path for GKE URI.
      2. Implement gce_params functionality described below.
      3. Add request_aggregated_items method for making aggregated API calls.

    """
    host = 'container.googleapis.com'
    responseCls = GKEResponse

    def __init__(self, user_id, key, secure, auth_type=None,
                 credential_file=None, project=None, **kwargs):
        super(GKEConnection, self).__init__(
            user_id, key, secure=secure, auth_type=auth_type,
            credential_file=credential_file, **kwargs)
        self.request_path = '/%s/projects/%s' % (API_VERSION, project)
        self.gke_params = None

    def pre_connect_hook(self, params, headers):
        """
        Update URL parameters with values from self.gke_params.

        @inherits: :class:`GoogleBaseConnection.pre_connect_hook`
        """
        params, headers = super(GKEConnection, self).pre_connect_hook(params,
                                                                      headers)
        if self.gke_params:
            params.update(self.gke_params)
        return params, headers

    def request(self, *args, **kwargs):
        """
        Perform request then do GKE-specific processing of URL params.

        @inherits: :class:`GoogleBaseConnection.request`
        """
        response = super(GKEConnection, self).request(*args, **kwargs)

        # If gce_params has been set, then update the pageToken with the
        # nextPageToken so it can be used in the next request.
        if self.gke_params:
            if 'nextPageToken' in response.object:
                self.gke_params['pageToken'] = response.object['nextPageToken']
            elif 'pageToken' in self.gke_params:
                del self.gke_params['pageToken']
            self.gke_params = None

        return response


class GKEContainerDriver(KubernetesContainerDriver):
    """
    GKE Container Driver class.

    This is the primary driver for interacting with Google Container
    Engine. It contains all of the standard libcloud methods,
    plus additional ex_* methods for more features.

    Note that many methods allow either objects or strings (or lists of
    objects/strings).  In most cases, passing strings instead of objects
    will result in additional GKE API calls.
    """
    connectionCls = GKEConnection
    api_name = 'google'
    name = "Google Container Engine"
    type = Provider.GKE
    website = 'https://container.googleapis.com'
    supports_clusters = True

    AUTH_URL = "https://container.googleapis.com/auth/"

    def __init__(self, user_id, key=None, datacenter=None, project=None,
                 auth_type=None, scopes=None, redirect_uri=None,
                 credential_file=None, host=None, port=443, **kwargs):
        """
        :param  user_id: The email address (for service accounts) or Client ID
                         (for installed apps) to be used for authentication.
        :type   user_id: ``str``

        :param  key: The RSA Key (for service accounts) or file path containing
                     key or Client Secret (for installed apps) to be used for
                     authentication.
        :type   key: ``str``

        :keyword  datacenter: The name of the datacenter (zone) used for
                              operations.
        :type     datacenter: ``str``

        :keyword  project: Your GKE project name. (required)
        :type     project: ``str``

        :keyword  auth_type: Accepted values are "SA" or "IA" or "GKE"
                             ("Service Account" or "Installed Application" or
                             "GKE" if libcloud is being used on a GKE instance
                             with service account enabled).
                             If not supplied, auth_type will be guessed based
                             on value of user_id or if the code is being
                             executed in a GKE instance.
        :type     auth_type: ``str``

        :keyword  scopes: List of authorization URLs. Default is empty and
                          grants read/write to Compute, Storage, DNS.
        :type     scopes: ``list``

        :keyword  credential_file: Path to file for caching authentication
                                   information used by GKEConnection.
        :type     credential_file: ``str``
        """
        if not project:
            raise ValueError('Project name must be specified using '
                             '"project" keyword.')
        if host is None:
            host = GKEContainerDriver.website
        self.auth_type = auth_type
        self.project = project
        self.scopes = scopes
        self.redirect_uri = redirect_uri
        self.zone = None
        if datacenter is not None:
            self.zone = datacenter
        self.credential_file = credential_file or \
            GoogleOAuth2Credential.default_credential_file + '.' + self.project

        super(GKEContainerDriver, self).__init__(user_id, key,
                                                 secure=True, host=None,
                                                 port=None, **kwargs)

        self.base_path = '/%s/projects/%s' % (API_VERSION, self.project)
        self.website = GKEContainerDriver.website

    def _ex_connection_class_kwargs(self):
        return {'auth_type': self.auth_type,
                'project': self.project,
                'scopes': self.scopes,
                'redirect_uri': self.redirect_uri,
                'credential_file': self.credential_file}

    def ex_get_cluster(self, zone, name):
        """
        Return cluster information in the given zone

        :keyword  zone:  Zone name
        :type     zone:  ``str`` or :class:`GCEZone` or
                            :class:`NodeLocation`

        :keyword  name:  Cluster name
        :type     name:  ``str``

        :rtype: :class:`GKECluster`
        """
        request = "/zones/%s/clusters/%s" % (zone, name)
        data = self.connection.request(request, method='GET').object
        return self._to_cluster(data)

    def ex_create_cluster(self, zone, name, initial_node_count=1):
        """
        Create cluster in the given zone

        :keyword  zone:  Zone name
        :type     zone:  ``str`` or :class:`GCEZone` or
                            :class:`NodeLocation`

        :keyword  name:  Cluster name
        :type     name:  ``str``

        :keyword  initial_node_count:  The number of nodes to create
        :type     initial_node_count:  ``int``

        :rtype: :class:`GKECluster`
        """
        request = "/zones/%s/clusters" % (zone)
        body = {
            "cluster": {
                "name": name,
                "nodePools": [
                    {
                        "name": "default-pool",
                        "initialNodeCount": initial_node_count
                    }
                ]
            }
        }
        data = self.connection.request(
            request,
            method='POST',
            data=body
        ).object
        return self._to_cluster(data)

    def ex_update_cluster(self, zone, name, update_dict):
        """
        Rename cluster in the given zone

        :keyword  zone:  Zone name
        :type     zone:  ``str`` or :class:`GCEZone` or
                            :class:`NodeLocation`

        :keyword  name:  Cluster name
        :type     name:  ``str``

        :keyword  update_dict:  Cluster update object:
            https://cloud.google.com/kubernetes-engine/docs/reference/rest/v1/ClusterUpdate 
        :type     update_dict:  ``str``

        :rtype: :class:`GKECluster`
        """
        request = "/zones/%s/clusters/%s" % (zone, name)
        body = {"update": update_dict}
        data = self.connection.request(
            request,
            method='PUT',
            data=body
        ).object
        return self._to_cluster(data)

    def ex_destroy_cluster(self, zone, name):
        """
        Destroy cluster in the given zone

        :keyword  zone:  Zone name
        :type     zone:  ``str`` or :class:`GCEZone` or
                            :class:`NodeLocation`
        :keyword  name:  Cluster name
        :type     name:  ``str``

        :rtype: :class:`GKECluster`
        """
        request = "/zones/%s/clusters/%s" % (zone, name)
        data = self.connection.request(request, method='DELETE').object
        return self._to_cluster(data)

    def list_clusters(self, ex_zone='-'):
        """
        Return a list of cluster information in the current zone or all zones.

        :keyword  ex_zone:  Optional zone name or '-'
        :type     ex_zone:  ``str`` or :class:`GCEZone` or
                            :class:`NodeLocation` or '-'

        :rtype: ``list`` of :class:`GKECluster`
        """
        request = "/zones/%s/clusters" % (ex_zone)
        data = self.connection.request(request, method='GET').object
        return self._to_clusters(data)

    def get_server_config(self, ex_zone):
        """
        Return configuration info about the Container Engine service.

        :keyword  ex_zone:  Zone name
        :type     ex_zone:  ``str`` or :class:`GCEZone` or
                            :class:`NodeLocation`
        """
        request = "/zones/%s/serverconfig" % (ex_zone)
        response = self.connection.request(request, method='GET').object
        return response

    def _to_clusters(self, data):
        return [self._to_cluster(c) for c in data.get('clusters', [])]

    def _to_cluster(self, data):
        return GKECluster(
            id=data.pop('id'),
            name=data.pop('name'),
            node_count=data.pop('currentNodeCount'),
            location=data.pop('location'),
            driver=self.connection.driver,
            config={k: data.pop(k)
                    for k in list(data)
                    if k in [
                'initialNodeCount',
                'nodeConfig',
                'addonsConfig',
                'legacyAbac',
                'networkPolicy',
                'ipAllocationPolicy',
                'masterAuthorizedNetworksConfig',
                'binaryAuthorization',
                'autoscaling',
                'networkConfig',
                'resourceUsageExportConfig',
                'authenticatorGroupsConfig',
                'privateClusterConfig',
                'databaseEncryption',
                'verticalPodAutoscaling',
                'shieldedNodes',
                'workloadIdentityConfig',
            ]},
            extra=data
        )
