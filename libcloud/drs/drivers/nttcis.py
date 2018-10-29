from libcloud.utils.py3 import ET
from libcloud.common.nttcis import NttCisConnection
from libcloud.common.nttcis import API_ENDPOINTS
from libcloud.common.nttcis import DEFAULT_REGION
from libcloud.drs.types import Provider
from libcloud.drs.base import Driver
from libcloud.common.nttcis import TYPES_URN
from libcloud.utils.xml import fixxpath, findtext, findall
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

    def _ex_connection_class_kwargs(self):
        """
            Add the region to the kwargs before the connection is instantiated
        """

        kwargs = super(NttCisDRSDriver,
                       self)._ex_connection_class_kwargs()
        kwargs['region'] = self.selected_region
        return kwargs

    def create_consistency_group(self, name, journal_size_gb ,
                                 source_server_id, target_server_id,
                                 description=None):
        """
        Create a consistency group

        :param name: Name of consistency group
        :type name: ``str``
        :param journal_size_gb: Journal size in GB
        :type journal_size_gb: ``str``
        :param source_server_id: Id of the server to copy
        :type source_server_id: ``str``
        :param target_server_id: Id of the server to receive the copy
        :type: ``str``
        :param description: (Optional) Description of consistency group
        :type: ``str``
        :return: :class: `NttCisConsistenccyGroup`
        """

        consistency_group_elm = ET.Element('createConsistencyGroup',
                                           {'xmlns': TYPES_URN})
        ET.SubElement(consistency_group_elm, "name").text = name
        if description is not None:
            ET.SubElement(
                consistency_group_elm,"description").text = description
        ET.SubElement(
            consistency_group_elm, "journalSizeGb").text = journal_size_gb
        server_pair = ET.SubElement(consistency_group_elm, "serverPair")
        ET.SubElement(
            server_pair, "sourceServerId").text = source_server_id
        ET.SubElement(
            server_pair, "targetServerId").text = target_server_id
        response = self.connection.request_with_orgId_api_2(
            "consistencyGroup/createConsistencyGroup",
            method="POST",
            data=ET.tostring(consistency_group_elm)).object
        response_code = findtext(response, 'responseCode', TYPES_URN)
        try:
            assert response_code in ['IN_PROGRESS', 'OK']
        except AssertionError:
            return response_code
        else:
            info = findtext(response, "info", TYPES_URN)
            print(info)
