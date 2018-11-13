import re
import functools
from libcloud.utils.py3 import ET
from libcloud.common.nttcis import NttCisConnection
from libcloud.common.nttcis import API_ENDPOINTS
from libcloud.common.nttcis import DEFAULT_REGION
from libcloud.common.nttcis import process_xml
from libcloud.drs.types import Provider
from libcloud.drs.base import DRSDriver
from libcloud.common.nttcis import TYPES_URN
from libcloud.utils.xml import fixxpath, findtext, findall


def get_params(func):
    @functools.wraps(func)
    def paramed(*args, **kwargs):

        if kwargs:
            for k, v in kwargs.items():
                old_key = k
                matches = re.findall(r'_(\w)', k)
                for match in matches:
                    k = k.replace('_' + match, match.upper())
                del kwargs[old_key]
                kwargs[k] = v
            params = kwargs
            result = func(args[0], params)
        else:
            result = func(args[0])
        return result
    return paramed


class NttCisDRSDriver(DRSDriver):
    """
    NttCis DRS driver.
    """

    selected_region = None
    connectionCls = NttCisConnection
    name = 'NTTC-CIS DRS Consistencty Groups'
    website = 'https://www.us.ntt.com/en/services/cloud/enterprise-cloud.html'
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

    def create_consistency_group(self, name, journal_size_gb,
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
                consistency_group_elm, "description").text = description
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
        :param params: A dictionary composed of one of the following keys
         and a value
                       * target_data_center_id=
                       * source_network_domain_id=
                       * target_network_domain_id=
                       * source_server_id=
                       * target_server_id=
                       * name=
                       * state=
                       * operation_status=
                       * drs_infrastructure_status=
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

    def list_consistency_group_snapshots(self, consistency_group_id,
                                         create_time_min=None,
                                         create_time_max=None):
        """
        Optional parameters identify the date of creation of Consistency Group
        snapshots in *XML Schema (XSD) date time format. Best used as a
        combination of createTime.MIN and createTime.MAX. If neither is
        provided then all snapshots up to the possible maximum of 1014
        will be returned. If MIN is provided by itself, all snapshots
        between the time specified by MIN and the point in time of
        execution will be returned. If MAX is provided by itself,
        then all snapshots up to that point in time (up to the
        maximum number of 1014) will be returned. MIN and MAX are
        inclusive for this API function

        :param consistency_group_id: The id of consistency group
        :type consistency_group_id: ``str``
        :param create_time_min: (Optional) in form YYYY-MM-DDT00:00.00.00Z or
                                           substitute time offset for Z, i.e,
                                           -05:00
        :type create_time_min: ``str``
        :param create_time_max: (Optional) in form YYYY-MM-DDT00:00:00.000Z or
                                           substitute time offset for Z, i.e,
                                           -05:00
        :type create_time_max: ``str``
        :return: `list` of :class" `NttCisSnapshots`
        """

        if create_time_min is None and create_time_max is None:
            params = {"consistencyGroupId": consistency_group_id}
        elif create_time_min and create_time_max:
            params = {"consistencyGroupId": consistency_group_id,
                      "createTime.MIN": create_time_min,
                      "createTime.MAX": create_time_max
                      }
        elif create_time_min or create_time_max:
            if create_time_max is not None:
                params = {"consistencyGroupId": consistency_group_id,
                          "createTime.MAX": create_time_max
                          }
            elif create_time_min is not None:
                params = {"consistencyGroupId": consistency_group_id,
                          "createTime.MIN": create_time_min
                          }
        paged_result = self.connection.request_with_orgId_api_2(
            'consistencyGroup/snapshot',
            method='GET',
            params=params
        ).object
        snapshots = self._to_process(paged_result)
        return snapshots

    def expand_journal(self, consistency_group_id, size_gb):
        """
        Expand the consistency group's journhal size in 100Gb increments
        :param consistency_group_id: The consistency group's UUID
        :type consistency_group_id: ``str``
        :param size_gb: Gb in 100 Gb increments
        :type size_gb: ``str``
        :return: ``bool``
        """

        expand_elm = ET.Element("expandJournal", {"id": consistency_group_id,
                                                  "xmlns": TYPES_URN})
        ET.SubElement(expand_elm, "sizeGb").text = size_gb
        response = self.connection.request_with_orgId_api_2(
            "consistencyGroup/expandJournal",
            method="POST",
            data=ET.tostring(expand_elm)).object
        response_code = findtext(response, 'responseCode', TYPES_URN)
        return response_code in ['IN_PROGRESS', 'OK']

    def start_failover_preview(self, consistency_group_id, snapshot_id):
        """
        Brings a Consistency Group into PREVIEWING_SNAPSHOT mode

        :param consistency_group_id: Id of the Consistency Group to put into
                                     PRIEVEW_MODE
        :type consistency_group_id: ``str``
        :param snapshot_id: Id of the Snapshot to preview
        :type snapshot_id: ``str``
        :return: True/False
        :rtype: ``bool``
        """
        preview_elm = ET.Element("startPreviewSnapshot",
                                 {"consistencyGroupId": consistency_group_id,
                                  "xmlns": TYPES_URN
                                  })
        ET.SubElement(preview_elm, "snapshotId").text = snapshot_id
        response = self.connection.request_with_orgId_api_2(
            "consistencyGroup/startPreviewSnapshot",
            method="POST",
            data=ET.tostring(preview_elm)).object
        response_code = findtext(response, 'responseCode', TYPES_URN)
        return response_code in ['IN_PROGRESS', 'OK']

    def stop_failover_preview(self, consistency_group_id):
        """
        Takes a Consistency Group out of PREVIEW_MODE and back to DRS_MODE

        :param consistency_group_id: Consistency Group's Id
        :type ``str``
        :return: True/False
        :rtype: ``bool``
        """
        preview_elm = ET.Element("stopPreviewSnapshot",
                                 {"consistencyGroupId": consistency_group_id,
                                  "xmlns": TYPES_URN})
        response = self.connection.request_with_orgId_api_2(
            "consistencyGroup/stopPreviewSnapshot",
            method="POST",
            data=ET.tostring(preview_elm)).object
        response_code = findtext(response, 'responseCode', TYPES_URN)
        return response_code in ['IN_PROGRESS', 'OK']

    def initiate_failover(self, consistency_group_id):
        """
        This method is irreversible.
        It will failover the Consistency Group while removing it as well.

        :param consistency_group_id: Consistency Group's Id to failover
        :type consistency_group_id: ``str``
        :return: True/False
        :rtype: ``bool``
        """
        failover_elm = ET.Element("initiateFailover",
                                  {"consistencyGroupId": consistency_group_id,
                                   "xmlns": TYPES_URN})
        response = self.connection.request_with_orgId_api_2(
            "consistencyGroup/initiateFailover",
            method="POST",
            data=ET.tostring(failover_elm)).object
        response_code = findtext(response, "responseCode", TYPES_URN)
        return response_code in ["IN_PROGRESS", "OK"]

    def delete_consistency_group(self, consistency_group_id):
        """
        Delete's a Consistency Group

        :param consistency_group_id: Id of Consistency Group to delete
        :type ``str``
        :return: True/False
        :rtype: ``bool``
        """
        delete_elm = ET.Element("deleteConsistencyGroup",
                                {"id": consistency_group_id,
                                 "xmlns": TYPES_URN})
        response = self.connection.request_with_orgId_api_2(
            "consistencyGroup/deleteConsistencyGroup",
            method="POST",
            data=ET.tostring(delete_elm)).object
        response_code = findtext(response, "responseCode", TYPES_URN)
        return response_code in ["IN_PROGRESS", "OK"]

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
