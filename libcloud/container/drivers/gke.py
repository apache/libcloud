from libcloud.common.google import GoogleOAuth2Credential
from libcloud.container.providers import Provider
from libcloud.container.drivers.kubernetes import KubernetesConnection, KubernetesContainerDriver

API_VERSION = 'v1'


class GKEContainerDriver(KubernetesContainerDriver):
    """
    GCE Node Driver class.

    This is the primary driver for interacting with Google Container Engine.  It
    contains all of the standard libcloud methods, plus additional ex_* methods
    for more features.

    Note that many methods allow either objects or strings (or lists of
    objects/strings).  In most cases, passing strings instead of objects will
    result in additional GKE API calls.
    """
    connectionCls = KubernetesConnection
    api_name = 'google'
    name = "Google Container Engine"
    type = Provider.GKE
    website = 'https://container.googleapis.com'
    supports_clusters = True

    # Google Compute Engine node states are mapped to Libcloud node states
    # per the following dict. GCE does not have an actual 'stopped' state
    # but instead uses a 'terminated' state to indicate the node exists
    # but is not running. In order to better match libcloud, GCE maps this
    # 'terminated' state to 'STOPPED'.
    # Also, when a node is deleted from GCE, it no longer exists and instead
    # will result in a ResourceNotFound error versus returning a placeholder
    # node in a 'terminated' state.
    # For more details, please see GCE's docs,
    # https://cloud.google.com/compute/docs/instances#checkmachinestatus

    AUTH_URL = "https://www.googleapis.com/auth/"

    BACKEND_SERVICE_PROTOCOLS = ['HTTP', 'HTTPS', 'HTTP2', 'TCP', 'SSL']

    def __init__(self, user_id, key=None, datacenter=None, project=None,
                 auth_type=None, scopes=None, credential_file=None, host=None, port=443, **kwargs):
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

        :keyword  project: Your GCE project name. (required)
        :type     project: ``str``

        :keyword  auth_type: Accepted values are "SA" or "IA" or "GCE"
                             ("Service Account" or "Installed Application" or
                             "GCE" if libcloud is being used on a GCE instance
                             with service account enabled).
                             If not supplied, auth_type will be guessed based
                             on value of user_id or if the code is being
                             executed in a GCE instance.
        :type     auth_type: ``str``

        :keyword  scopes: List of authorization URLs. Default is empty and
                          grants read/write to Compute, Storage, DNS.
        :type     scopes: ``list``

        :keyword  credential_file: Path to file for caching authentication
                                   information used by GCEConnection.
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
        self.credential_file = credential_file or \
            GoogleOAuth2Credential.default_credential_file + '.' + self.project

        super(GKEContainerDriver, self).__init__(user_id, key, host=host, port=port, **kwargs)

        self.base_path = '/%s/projects/%s' % (API_VERSION,
                                                      self.project)
        self.website = GKEContainerDriver.website

    def list_clusters(self, zone=None):
        """
        """
        request = "/zones/%s/clusters" % (zone)
        if zone is None:
            request = "/zones/clusters"
        # https://container.googleapis.com/v1/projects/{projectId}/zones/{zone}/clusters
        print(self.website+self.base_path+request)
        response = self.connection.request(self.base_path + request, method='GET').object
        print(response)
