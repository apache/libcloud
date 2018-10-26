from libcloud.utils.py3 import ET
from libcloud.common.nttcis import NttCisConnection
from libcloud.common.nttcis import API_ENDPOINTS
from libcloud.common.nttcis import DEFAULT_REGION
from libcloud.drs.types import Provider
from libcloud.drs.base import Driver
from libcloud.common.types import LibcloudError


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

        super(NttCisDRSDriver, self).__init__(key=key,
                                              secret=secret,
                                              secure=secure, host=host,
                                              port=port,
                                              api_version=api_version,
                                              region=region,
                                              **kwargs)
