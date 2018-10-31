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
    exception_msg = driver.create_consistency_group(
        "sdk_test2_cg", "100", "032f3967-00e4-4780-b4ef-8587460f9dd4",
        "aee58575-38e2-495f-89d3-854e6a886411",
        description="A test consistency group")


    assert exception_msg == 'The drsEligible flag for target Server aee58575-38e2-495f-89d3-854e6a886411 must be set.'


class NttCisMockHttp(MockHttp):

    fixtures = DRSFileFixtures('nttcis')

    def _oec_0_9_myaccount(self, method, url, body, headers):
        body = self.fixtures.load('oec_0_9_myaccount.xml')
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _caas_2_7_8a8f6abc_2745_4d8a_9cbc_8dabe5a7d0e4_consistencyGroup_createConsistencyGroup(self, method, url, body, headers):
        body = self.fixtures.load(
            'drs_ineligible.xml'
        )
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])