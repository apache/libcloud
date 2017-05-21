from libcloud.common.google import GoogleOAuth2Credential


class GKENodeDriver(NodeDriver):
    """
    GCE Node Driver class.

    This is the primary driver for interacting with Google Container Engine.  It
    contains all of the standard libcloud methods, plus additional ex_* methods
    for more features.

    Note that many methods allow either objects or strings (or lists of
    objects/strings).  In most cases, passing strings instead of objects will
    result in additional GKE API calls.
    """
    connectionCls = GKEConnection
    api_name = 'google'
    name = "Google Container Engine"
    type = Provider.GKE
    website = 'https://container.googleapis.com'

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
    NODE_STATE_MAP = {
        "PROVISIONING": NodeState.PENDING,
        "STAGING": NodeState.PENDING,
        "RUNNING": NodeState.RUNNING,
        "STOPPING": NodeState.PENDING,
        "TERMINATED": NodeState.STOPPED,
        "UNKNOWN": NodeState.UNKNOWN
    }

    AUTH_URL = "https://www.googleapis.com/auth/"
    SA_SCOPES_MAP = {
        # list derived from 'gcloud compute instances create --help'
        "bigquery": "bigquery",
        "cloud-platform": "cloud-platform",
        "compute-ro": "compute.readonly",
        "compute-rw": "compute",
        "datastore": "datastore",
        "logging-write": "logging.write",
        "monitoring": "monitoring",
        "monitoring-write": "monitoring.write",
        "service-control": "servicecontrol",
        "service-management": "service.management",
        "sql": "sqlservice",
        "sql-admin": "sqlservice.admin",
        "storage-full": "devstorage.full_control",
        "storage-ro": "devstorage.read_only",
        "storage-rw": "devstorage.read_write",
        "taskqueue": "taskqueue",
        "useraccounts-ro": "cloud.useraccounts.readonly",
        "useraccounts-rw": "cloud.useraccounts",
        "userinfo-email": "userinfo.email"
    }

    IMAGE_PROJECTS = {
        "centos-cloud": ["centos"],
        "coreos-cloud": ["coreos"],
        "debian-cloud": ["debian", "backports"],
        "gce-nvme": ["nvme-backports"],
        "google-containers": ["container-vm"],
        "opensuse-cloud": ["opensuse"],
        "rhel-cloud": ["rhel"],
        "suse-cloud": ["sles", "suse"],
        "ubuntu-os-cloud": ["ubuntu"],
        "windows-cloud": ["windows"],
    }

    BACKEND_SERVICE_PROTOCOLS = ['HTTP', 'HTTPS', 'HTTP2', 'TCP', 'SSL']

    def __init__(self, user_id, key=None, datacenter=None, project=None,
                 auth_type=None, scopes=None, credential_file=None, **kwargs):
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

        self.auth_type = auth_type
        self.project = project
        self.scopes = scopes
        self.credential_file = credential_file or \
            GoogleOAuth2Credential.default_credential_file + '.' + self.project

        super(GCENodeDriver, self).__init__(user_id, key, **kwargs)

        # Cache Zone and Region information to reduce API calls and
        # increase speed
        self.base_path = '/%s/projects/%s' % (API_VERSION,
                                                      self.project)
        self.zone_list = self.ex_list_zones()
        self.zone_dict = {}
        for zone in self.zone_list:
            self.zone_dict[zone.name] = zone
        if datacenter:
            self.zone = self.ex_get_zone(datacenter)
        else:
            self.zone = None

        self.region_list = self.ex_list_regions()
        self.region_dict = {}
        for region in self.region_list:
            self.region_dict[region.name] = region

        if self.zone:
            self.region = self._get_region_from_zone(self.zone)
        else:
            self.region = None

        # Volume details are looked up in this name-zone dict.
        # It is populated if the volume name is not found or the dict is empty.
        self._ex_volume_dict = {}
