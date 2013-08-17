
try:
    import simplejson as json
except ImportError:
    import json

from libcloud.utils.py3 import httplib
from libcloud.utils.py3 import urlparse

try:
    parse_qsl = urlparse.parse_qsl
except AttributeError:
    import cgi
    parse_qsl = cgi.parse_qsl

from libcloud.common.types import LibcloudError
from libcloud.loadbalancer.base import LoadBalancer, Member, Algorithm
from libcloud.loadbalancer.types import State
from libcloud.loadbalancer.drivers.cloudstack import CloudStackLBDriver

from libcloud.test import MockHttpTestCase
from libcloud.test.file_fixtures import LoadBalancerFileFixtures


class CloudStackMockHttp(MockHttpTestCase):
    next_job_id = 0
    jobs = {}

    def __init__(self, *args, **kwargs):
        MockHttpTestCase.__init__(self, *args, **kwargs)

    def _test_path(self, method, url, body, headers):
        url = urlparse.urlparse(url)
        query = dict(parse_qsl(url.query))

        self.assertTrue('apiKey' in query)
        self.assertTrue('command' in query)
        self.assertTrue('response' in query)
        self.assertTrue('signature' in query)

        self.assertTrue(query['response'] == 'json')

        del query['apiKey']
        del query['response']
        del query['signature']
        command = query.pop('command')

        return getattr(self, '_cmd_' + command)(**query)

    @property
    def driver(self):
        return self.test.mock

    def async_response(self, resultname, results):
        jobid = self.next_job_id
        self.next_job_id += 1
        self.jobs[jobid] = results

        body = json.dumps({
            resultname + 'response': {'jobid': jobid},
            })

        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _from_balancer(self, balancer):
        state = {
            State.RUNNING: 'Active',
            State.PENDING: 'Add',
        }.get(balancer.state, '')

        return {
           "id": balancer.id,
           "name": balancer.name,
           "publicipid":34000,
           "publicip":"1.1.1.49",
           "publicport":"80",
           "privateport":"80",
           "algorithm":"roundrobin",
           "account":"fakeaccount",
           "domainid":801,
           "domain":"AA000062-libcloud-dev",
           "state":state,
        }

    def _from_member(self, member):
        return {
            "id":member.id,
            "name":"test_1308874974",
            "displayname":"test_1308874974",
            "account":"fakeaccount",
            "domainid":801,
            "domain":"AA000062-libcloud-dev",
            "created":"2011-06-24T00:22:56+0000",
            "state":"Running",
            "haenable":False,
            "zoneid":1,
                "zonename":"Sydney",
                "templateid":421,
                "templatename":"XEN Basic Ubuntu 10.04 Server x64 PV r2.0",
                "templatedisplaytext":"XEN Basic Ubuntu 10.04 Server x64 PV r2.0",
                "passwordenabled":False,
                "serviceofferingid":105,
                "serviceofferingname":"Compute Micro PRD",
                "cpunumber":1,
                "cpuspeed":1200,
                "memory":384,
                "cpuused":"0.14%",
                "networkkbsread":2185,
                "networkkbswrite":109,
                "guestosid":12,
                "rootdeviceid":0,
                "rootdevicetype":"IscsiLUN",
                "securitygroup":[],
                "nic":[{
                    "id":3914,
                    "networkid":860,
                    "netmask":"255.255.240.0",
                    "gateway":"1.1.1.1",
                    "ipaddress":member.ip,
                    "traffictype":"Guest",
                    "type":"Virtual",
                    "isdefault":True
                 }],
                "hypervisor":"XenServer"
            }

    def _cmd_listLoadBalancerRules(self, id=None):
        balancers = []
        for b in self.driver.list_balancers():
            if id and b.id != id:
                continue
            balancers.append(self._from_balancer(b))

        response = {
            'listloadbalancerrulesresponse': {
                'loadbalancerrule': balancers,
            }
        }

        body = json.dumps(response)
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _cmd_createLoadBalancerRule(self, algorithm, name, privateport, publicport, publicipid):
        balancer = self.driver.create_balancer(
            name=name,
            port=publicport,
            protocol='tcp',
            algorithm=algorithm,
            members=[],
        )

        response = {
            'createloadbalancerruleresponse': {
                'loadbalancer': self._from_balancer(balancer)
            }
        }

        body = json.dumps(response)
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _cmd_deleteLoadBalancerRule(self, id):
        self.driver.get_balancer(id).destroy()
        return self.async_response('deleteloadbalancerrule', {'success': True})

    def _cmd_listLoadBalancerRuleInstances(self, id):
        balancer = self.driver.get_balancer(id)

        members = []
        for m in balancer.list_members():
            members.append(self._from_member(m))

        response = {
            'listloadbalancerruleinstancesresponse': {
                'loadbalancerruleinstance': members
            }
        }

        body = json.dumps(response)
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _cmd_assignToLoadBalancerRule(self, id, virtualmachineids):
        balancer = self.driver.get_balancer(id)
        member = Member(id=virtualmachineids, ip=None, port=None)
        balancer.attach_member(member)
        
        return self.async_response('assigntoloadbalancerrule', {'success': True})

    def _cmd_removeFromLoadBalancerRule(self, id, virtualmachineids):
        balancer = self.driver.get_balancer(id)
        for member in balancer.list_members():
            if member.id == virtualmachineids:
                balancer.detach_member(member)

        return self.async_response('removefromloadbalancerrule', {'success': True})

    def _cmd_associateIpAddress(self, **kwargs):
        # FIXME: Do we need to return id: 34000 along with result?
        response = {
            "ipaddress": {
                "id":34000,
                "ipaddress":"1.1.1.49",
                "allocated":"2011-06-24T05:52:55+0000",
                "zoneid":1,
                "zonename":"Sydney",
                "issourcenat":False,
                "account":"fakeaccount",
                "domainid":801,
                "domain":"AA000062-libcloud-dev",
                "forvirtualnetwork":True,
                "isstaticnat":False,
                "associatednetworkid":860,
                "networkid":200,
                "state":"Allocating"
                }
            }
        return self.async_response('associateipaddress', response)

    def _cmd_disassociateIpAddress(self, **kwargs):
        return self.async_response('disassociateipaddress', {'success': True})

    def _cmd_listZones(self, **kwargs):
        response = {
            'listzonesresponse': {
                'zone': [{
                    'id': 1,
                    'name': 'Sydney',
                    'networktype': 'Advanced',
                    'securitygroupsenabled': False,
                }],
            }
        }

        body = json.dumps(response)
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])

    def _cmd_queryAsyncJobResult(self, jobid):
        assert int(jobid) in self.jobs

        response = {
            'queryasyncjobresultresponse': {
                'jobid': jobid,
                'jobstatus': 1,
                'jobprocstatus': 0,
                'jobresultcode': 0,
                'jobresulttype': 'object',
                'jobresult': self.jobs[int(jobid)],
            }
        }

        body = json.dumps(response)
        return (httplib.OK, body, {}, httplib.responses[httplib.OK])
