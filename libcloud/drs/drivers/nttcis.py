import re
import functools
from libcloud.utils.py3 import ET
from libcloud.common.nttcis import NttCisConnection
from libcloud.common.nttcis import API_ENDPOINTS
from libcloud.common.nttcis import DEFAULT_REGION
from libcloud.common.nttcis import process_xml
from libcloud.drs.types import Provider
from libcloud.drs.base import Driver
from libcloud.common.nttcis import TYPES_URN
from libcloud.utils.xml import fixxpath, findtext, findall
from libcloud.common.types import LibcloudError


def get_params(func):
    @functools.wraps(func)
    def paramed(*args, **kwargs):

        if kwargs:
            for k, v in kwargs.items():
                old_key = k
                matches = re.findall(r'_(\w)', k)
                for match in matches:
                    k = k.replace('_'+match, match.upper())
                del kwargs[old_key]
                kwargs[k] = v
            params = kwargs
            result = func(args[0], params)
        else:
            result = func(args[0])
        return result
    return paramed


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
        return response_code in ['IN_PROGRESS', 'OK']

    @get_params
    def list_consistency_groups(self, params={}):
        """
        Functions takes a named parameter that must be one of the following
        :param params: A dictionary composed of one of the follwing keys and a value
                       target_data_center_id:
                       source_network_domain_id:
                       target_network_domain_id:
                       source_server_id:
                       target_server_id:
                       name:
                       state:
                       operation_status:
                       drs_infrastructure_status:
        :return:  `list` of :class: `NttCisConsistencyGroup`
        """

        response = self.connection.request_with_orgId_api_2(
            'consistencyGroup/consistencyGroup', params=params).object
        cgs = self._to_consistency_groups(response)
        return cgs

    def get_consistency_group(self, consistency_group_id):
        """
        Retrieves a Consistency by it's id and is more efficient thatn listing
        all consistency groups and filtering that result.
        :param consistency_group_id: An id of a consistency group
        :type consistency_group_id: ``str``
        :return: :class: `NttCisConsistencygroup`
        """
        response = self.connection.request_with_orgId_api_2(
            "consistencyGroup/consistencyGroup/%s" % consistency_group_id
        ).object
        cg = self._to_process(response)
        return cg

    def list_consistency_group_snapshots(self, consistency_group_id):
        params = {"consistencyGroupId": consistency_group_id}
        paged_result = self.connection.request_with_orgId_api_2(
            'consistencyGroup/snapshot',
            method='GET',
            params=params
        ).object
        snapshots = self._to_process(paged_result)
        return snapshots

    def _to_consistency_groups(self, object):
        cgs = findall(object, 'consistencyGroup', TYPES_URN)
        return [self._to_process(el) for el in cgs]

    def _to_snapshots(self, object):
        snapshots = []
        for element in object.findall(fixxpath("snapshot", TYPES_URN)):
            snapshots.append(self._to_process(element))
        return snapshots

    def _to_process(self, element):
        return process_xml(ET.tostring(element))
