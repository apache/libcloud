from libcloud.utils.py3 import ET
from libcloud.common.nttcis import NttCisConnection
from libcloud.common.nttcis import NttCisPool
from libcloud.common.nttcis import NttCisPoolMember
from libcloud.common.nttcis import NttCisVirtualListener
from libcloud.common.nttcis import NttCisVIPNode
from libcloud.common.nttcis import NttCisDefaultHealthMonitor
from libcloud.common.nttcis import NttCisPersistenceProfile
from libcloud.common.nttcis import \
    NttCisVirtualListenerCompatibility
from libcloud.common.nttcis import NttCisDefaultiRule
from libcloud.common.nttcis import API_ENDPOINTS
from libcloud.common.nttcis import DEFAULT_REGION
from libcloud.common.nttcis import TYPES_URN
from libcloud.utils.misc import reverse_dict
from libcloud.utils.xml import fixxpath, findtext, findall
from libcloud.loadbalancer.types import State
from libcloud.loadbalancer.base import Algorithm, Driver, LoadBalancer
from libcloud.loadbalancer.base import Member
from libcloud.loadbalancer.types import Provider


class NttCisDRSDriver(Driver):
    """
    NttCis node driver.
    """

    selected_region = None
    connectionCls = NttCisConnection
    name = 'NTTC-CIS DRS Consistencty Groups'
    website = 'https://cloud.nttcis.com/'
    type = Provider.NTTCIS
    api_version = 1.0

    network_domain_id = None

    def __init__(self, key, secret=None, secure=True, host=None, port=None,
                 api_version=None, region=DEFAULT_REGION, **kwargs):

        if region not in API_ENDPOINTS and host is None:
            raise ValueError(
                'Invalid region: %s, no host specified' % (region))
        if region is not None:
            self.selected_region = API_ENDPOINTS[region]

        super(NttCisDRSDriver, self).__init__(key=key, secret=secret,
                                                    secure=secure, host=host,
                                                    port=port,
                                                    api_version=api_version,
                                                    region=region,
                                                    **kwargs)
