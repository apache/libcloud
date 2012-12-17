# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
VCL driver
"""

import sys
import time

from libcloud.utils.py3 import xmlrpclib

from libcloud.common.types import InvalidCredsError, LibcloudError
from libcloud.compute.types import Provider, NodeState
from libcloud.compute.base import NodeDriver, Node
from libcloud.compute.base import NodeSize, NodeImage


class VCLSafeTransport(xmlrpclib.SafeTransport):
    def __init__(self, datetime, user, passwd, host):

        self._pass = passwd
        self._use_datetime = datetime
        self._connection = (None, None)
        self._extra_headers = []

    def send_content(self, connection, request_body):
        connection.putheader('Content-Type', 'text/xml')
        connection.putheader('X-APIVERSION', '2')
        connection.putheader('X-User', self._user)
        connection.putheader('X-Pass', self._pass)
        connection.putheader('Content-Length', str(len(request_body)))
        connection.endheaders(request_body)


class VCLProxy(xmlrpclib.ServerProxy):
    API_POSTFIX = '/index.php?mode=xmlrpccall'
    transportCls = VCLSafeTransport

    def __init__(self, user, key, secure, host, port, driver, verbose=False):
        url = ''
        cls = self.transportCls

        if secure:
            url = 'https://'
            port = port or 443
        else:
            url = 'http://'
            port = port or 80

        url += host + ':' + str(port)
        url += VCLProxy.API_POSTFIX

        self.API = url
        t = cls(0, user, key, self.API)

        xmlrpclib.ServerProxy.__init__(
            self,
            uri=self.API,
            transport=t,
            verbose=verbose
        )


class VCLConnection(object):
    """
    Connection class for the VCL driver
    """

    proxyCls = VCLProxy
    driver = None

    def __init__(self, user, key, secure, host, port):
        self.user = user
        self.key = key
        self.secure = secure
        self.host = host
        self.port = port

    def request(self, method, *args, **kwargs):
        sl = self.proxyCls(user=self.user, key=self.key, secure=self.secure,
                           host=self.host, port=self.port, driver=self.driver)

        try:
            return getattr(sl, method)(*args)
        except xmlrpclib.Fault:
            e = sys.exc_info()[1]
            if e.faultCode == 'VCL_Account':
                raise InvalidCredsError(e.faultString)
            raise LibcloudError(e, driver=self.driver)


class VCLNodeDriver(NodeDriver):
    """
    VCL node driver

    @keyword   host: The VCL host to which you make requests(required)
    @type      host: C{str}
    """

    NODE_STATE_MAP = {
        'ready': NodeState.RUNNING,
        'failed': NodeState.TERMINATED,
        'timedout': NodeState.TERMINATED,
        'loading': NodeState.PENDING,
        'time': NodeState.PENDING,
        'future': NodeState.PENDING,
        'error': NodeState.UNKNOWN,
        'notready': NodeState.PENDING,
        'notavailable': NodeState.TERMINATED,
        'success': NodeState.PENDING
    }

    connectionCls = VCLConnection
    name = 'VCL'
    website = 'http://incubator.apache.org/vcl/'
    type = Provider.VCL

    def __init__(self, key, secret, secure=True, host=None, port=None, *args,
                 **kwargs):
        """
        @param    key:    API key or username to used (required)
        @type     key:    C{str}

        @param    secret: Secret password to be used (required)
        @type     secret: C{str}

        @param    secure: Weither to use HTTPS or HTTP.
        @type     secure: C{bool}

        @param    host: Override hostname used for connections. (required)
        @type     host: C{str}

        @param    port: Override port used for connections.
        @type     port: C{int}

        @rtype: C{None}
        """
        if not host:
            raise Exception('When instantiating VCL driver directly ' +
                            'you also need to provide host')

        self.key = key
        self.host = host
        self.secret = secret
        self.connection = self.connectionCls(key, secret, secure, host, port)
        self.connection.driver = self

    def _vcl_request(self, method, *args):
        res = self.connection.request(
            method,
            *args
        )
        if(res['status'] == 'error'):
            raise LibcloudError(res['errormsg'], driver=self)
        return res

    def create_node(self, **kwargs):
        """Create a new VCL reservation
        size and name ignored, image is the id from list_image

        @inherits: L{NodeDriver.create_node}

        @keyword    image: image is the id from list_image
        @type       image: C{str}

        @keyword    start: start time as unix timestamp
        @type       start: C{str}

        @keyword    length: length of time in minutes
        @type       length: C{str}
        """

        image = kwargs["image"]
        start = kwargs.get('start', int(time.time()))
        length = kwargs.get('length', '60')

        res = self._vcl_request(
            "XMLRPCaddRequest",
            image.id,
            start,
            length
        )

        return Node(
            id=res['requestid'],
            name=image.name,
            state=self.NODE_STATE_MAP[res['status']],
            public_ips=[],
            private_ips=[],
            driver=self,
            image=image.name
        )

    def destroy_node(self, node):
        """
        End VCL reservation for the node passed in.
        Throws error if request fails.

        @param  node: The node to be destroyed
        @type   node: L{Node}

        @rtype: C{bool}
        """
        try:
            self._vcl_request(
                'XMLRPCendRequest',
                node.id
            )
        except LibcloudError:
            return False
        return True

    def _to_image(self, img):
        return NodeImage(
            id=img['id'],
            name=img['name'],
            driver=self.connection.driver
        )

    def list_images(self, location=None):
        """
        List images available to the user provided credentials

        @inherits: L{NodeDriver.list_images}
        """
        res = self.connection.request(
            "XMLRPCgetImages"
        )
        return [self._to_image(i) for i in res]

    def list_sizes(self, location=None):
        """
        VCL does not choosing sizes for node creation.
        Size of images are statically set by administrators.

        @inherits: L{NodeDriver.list_sizes}
        """
        return [NodeSize(
            't1.micro',
            'none',
            '512',
            0, 0, 0, self)
        ]

    def _to_connect_data(self, request_id, ipaddr):
        res = self._vcl_request(
            "XMLRPCgetRequestConnectData",
            request_id,
            ipaddr
        )
        return res

    def _to_status(self, requestid, imagename, ipaddr):
        res = self._vcl_request(
            "XMLRPCgetRequestStatus",
            requestid
        )

        public_ips = []
        extra = []
        if(res['status'] == 'ready'):
            cdata = self._to_connect_data(requestid, ipaddr)
            public_ips = [cdata['serverIP']]
            extra = {
                'user': cdata['user'],
                'pass': cdata['password']
            }
        return Node(
            id=requestid,
            name=imagename,
            state=self.NODE_STATE_MAP[res['status']],
            public_ips=public_ips,
            private_ips=[],
            driver=self,
            image=imagename,
            extra=extra
        )

    def _to_nodes(self, res, ipaddr):
        return [self._to_status(
            h['requestid'],
            h['imagename'],
            ipaddr
        ) for h in res]

    def list_nodes(self, ipaddr):
        """
        List nodes

        @param  ipaddr: IP address which should be used
        @type   ipaddr: C{str}

        @rtype: C{list} of L{Node}
        """
        res = self._vcl_request(
            "XMLRPCgetRequestIds"
        )
        return self._to_nodes(res['requests'], ipaddr)

    def ex_update_node_access(self, node, ipaddr):
        """
        Update the remote ip accessing the node.

        @param node: the reservation node to update
        @type  node: L{Node}

        @param ipaddr: the ipaddr used to access the node
        @type  ipaddr: C{str}

        @return: node with updated information
        @rtype: L{Node}
        """
        return self._to_status(node.id, node.image, ipaddr)

    def ex_extend_request_time(self, node, minutes):
        """
        Time in minutes to extend the requested node's reservation time

        @param node: the reservation node to update
        @type  node: L{Node}

        @param minutes: the number of mintes to update
        @type  minutes: C{str}

        @return: true on success, throws error on failure
        @rtype: C{bool}
        """
        return self._vcl_request(
            "XMLRPCextendRequest",
            node.id,
            minutes
        )

    def ex_get_request_end_time(self, node):
        """
        Get the ending time of the node reservation.

        @param node: the reservation node to update
        @type  node: L{Node}

        @return: unix timestamp
        @rtype: C{int}
        """
        res = self._vcl_request(
            "XMLRPCgetRequestIds"
        )
        time = 0
        for i in res['requests']:
                if i['requestid'] == node.id:
                        time = i['end']
        return time
