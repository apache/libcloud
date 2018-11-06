import pytest


import sys
from types import GeneratorType
from libcloud.utils.py3 import httplib
from libcloud.utils.py3 import ET
from libcloud.common.types import InvalidCredsError
from libcloud.common.nttcis import NttCisAPIException, NetworkDomainServicePlan
from libcloud.common.nttcis import TYPES_URN
from libcloud.drs.drivers.nttcis import NttCisDRSDriver as NttCis
from libcloud.compute.drivers.nttcis import NttCisNic
from libcloud.compute.base import Node, NodeAuthPassword, NodeLocation
from libcloud.test import MockHttp, unittest
from libcloud.test.file_fixtures import DRSFileFixtures
from libcloud.test.secrets import NTTCIS_PARAMS
from libcloud.utils.xml import fixxpath, findtext, findall


@pytest.fixture()
def driver():
    NttCis.connectionCls.active_api_version = "2.7"
    NttCis.connectionCls.conn_class = NttCisMockHttp
    NttCisMockHttp.type = None
    driver = NttCis(*NTTCIS_PARAMS)
    return driver


def test_ineligible_server(driver):
    NttCisMockHttp.type = 'INPROGRESS'
    with pytest.raises(NttCisAPIException) as excinfo:
        driver.create_consistency_group(
            "sdk_test2_cg", "100", "032f3967-00e4-4780-b4ef-8587460f9dd4",
            "aee58575-38e2-495f-89d3-854e6a886411",
            description="A test consistency group")
    assert excinfo.value.msg == 'The drsEligible flag for target Server ' \
                                'aee58575-38e2-495f-89d3-854e6a886411 must be set.'


def test_list_consistency_groups(driver):
    cgs = driver.list_consistency_groups()
    assert isinstance(cgs, list)
    assert hasattr(cgs[0], 'serverPair')


def test_get_consistency_group(driver):
    cg = driver.get_consistency_group("3710c093-7dcc-4a21-bd07-af9f4d93b6b5")
    assert cg.id == "3710c093-7dcc-4a21-bd07-af9f4d93b6b5"


def test_get_consistency_group_by_name(driver):
    cgs = driver.list_consistency_groups(name="skd_test2_cg")
    assert cgs[0].id == "3710c093-7dcc-4a21-bd07-af9f4d93b6b5"


def test_expand_journal(driver):
    cg_id = "3710c093-7dcc-4a21-bd07-af9f4d93b6b5"
    size_gb = "100"
    result = driver.expand_journal(cg_id, size_gb)
    assert result is True


def test_start_failover_preview(driver):
    pass


class NttCisMockHttp(MockHttp):

    fixtures = DRSFileFixtures('nttcis')

    def _oec_0_9_myaccount(self, method, url, body, headers):
        body = self.fixtures.load('oec_0_9_myaccount.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _oec_0_9_myaccount_INPROGRESS(self, method, url, body, headers):
        body = self.fixtures.load('oec_0_9_myaccount.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_consistencyGroup_createConsistencyGroup_INPROGRESS(self,
                                                                                                          method,
                                                                                                          url,
                                                                                                          body,
                                                                                                          headers):
        body = self.fixtures.load(
            'drs_ineligible.xml'
        )
        return (httplib.BAD_REQUEST, body, {}, httplib.responses[httplib.OK])

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_consistencyGroup_consistencyGroup(self,
                                                                                         method,
                                                                                         url,
                                                                                         body,
                                                                                         headers):
        body = self.fixtures.load("list_consistency_groups.xml")
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_consistencyGroup_consistencyGroup_3710c093_7dcc_4a21_bd07_af9f4d93b6b5(self,
                                                                                                                              method,
                                                                                                                              url,
                                                                                                                              body,
                                                                                                                              headers):
        body = self.fixtures.load("get_consistency_group.xml")
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_consistencyGroup_consistencyGroup_name(self,
                                                                                                                              method,
                                                                                                                              url,
                                                                                                                              body,
                                                                                                                              headers):
        body = self.fixtures.load("list_cg_by_params.xml")
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_consistencyGroup_expandJournal(self,
                                                                                                                              method,
                                                                                                                              url,
                                                                                                                              body,
                                                                                                                              headers):
        body = self.fixtures.load("expand_cg.xml")
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])