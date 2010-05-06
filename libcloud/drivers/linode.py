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
#
# Maintainer: Jed Smith <jsmith@linode.com>
#
# BETA TESTING THE LINODE API AND DRIVERS
#
# A beta account that incurs no financial charge may be arranged for.  Please
# contact Jed Smith <jsmith@linode.com> for your request.
#
"""
Linode driver
"""
from libcloud.types import Provider, NodeState, InvalidCredsException
from libcloud.base import ConnectionKey, Response
from libcloud.base import NodeDriver, NodeSize, Node, NodeLocation
from libcloud.base import NodeAuthPassword, NodeAuthSSHKey
from libcloud.base import NodeImage
from copy import copy
import os

# JSON is included in the standard library starting with Python 2.6.  For 2.5
# and 2.4, there's a simplejson egg at: http://pypi.python.org/pypi/simplejson
try: import json
except: import simplejson as json


class LinodeException(Exception):
    """
    Exception class for Linode driver
    """
    def __str__(self):
        return "(%u) %s" % (self.args[0], self.args[1])
    def __repr__(self):
        return "<LinodeException code %u '%s'>" % (self.args[0], self.args[1])

# For beta accounts, change this to "beta.linode.com".
LINODE_API = "api.linode.com"

# For beta accounts, change this to "/api/".
LINODE_ROOT = "/"


class LinodeResponse(Response):
    # Wraps a Linode API HTTP response.

    def __init__(self, response):
        # Given a response object, slurp the information from it.
        self.body = response.read()
        self.status = response.status
        self.headers = dict(response.getheaders())
        self.error = response.reason
        self.invalid = LinodeException(0xFF,
                                       "Invalid JSON received from server")

        # Move parse_body() to here;  we can't be sure of failure until we've
        # parsed the body into JSON.
        self.action, self.object, self.errors = self.parse_body()

        if self.error == "Moved Temporarily":
            raise LinodeException(0xFA,
                                  "Redirected to error page by API.  Bug?")

        if not self.success():
            # Raise the first error, as there will usually only be one
            raise self.errors[0]

    def parse_body(self):
        # Parse the body of the response into JSON.  Will return None if the
        # JSON response chokes the parser.  Returns a triple:
        #    (action, data, errorarray)
        try:
            js = json.loads(self.body)
            if ("DATA" not in js
                or "ERRORARRAY" not in js
                or "ACTION" not in js):

                return (None, None, [self.invalid])
            errs = [self._make_excp(e) for e in js["ERRORARRAY"]]
            return (js["ACTION"], js["DATA"], errs)
        except:
            # Assume invalid JSON, and use an error code unused by Linode API.
            return (None, None, [self.invalid])

    def parse_error(self):
        # Obtain the errors from the response.  Will always return a list.
        try:
            js = json.loads(self.body)
            if "ERRORARRAY" not in js:
                return [self.invalid]
            return [self._make_excp(e) for e in js["ERRORARRAY"]]
        except:
            return [self.invalid]

    def success(self):
        # Does the response indicate success?  If ERRORARRAY has more than one
        # entry, we'll say no.
        return len(self.errors) == 0

    def _make_excp(self, error):
        # Make an exception from an entry in ERRORARRAY.
        if "ERRORCODE" not in error or "ERRORMESSAGE" not in error:
            return None
        if error["ERRORCODE"] ==  4:
            return InvalidCredsException(error["ERRORMESSAGE"])
        return LinodeException(error["ERRORCODE"], error["ERRORMESSAGE"])


class LinodeConnection(ConnectionKey):
    """
    Connection class for the LinodeConnection driver

    Wraps Linode HTTPS connection, and passes along the connection key.
    """

    host = LINODE_API
    responseCls = LinodeResponse

    def add_default_params(self, params):
        params["api_key"] = self.key
        # Be explicit about this in case the default changes.
        params["api_responseFormat"] = "json"
        return params


class LinodeNodeDriver(NodeDriver):
    """
    Linode node driver

    The meat of Linode operations.
    """
    type = Provider.LINODE
    name = "Linode"
    connectionCls = LinodeConnection

    def __init__(self, key):
        self.datacenter = None
        NodeDriver.__init__(self, key)

    # Converts Linode's state from DB to a NodeState constant.
    # Some of these are lightly questionable.
    LINODE_STATES = {
        -2: NodeState.UNKNOWN,              # Boot Failed
        -1: NodeState.PENDING,              # Being Created
         0: NodeState.PENDING,              # Brand New
         1: NodeState.RUNNING,              # Running
         2: NodeState.REBOOTING,            # Powered Off (TODO: Extra state?)
         3: NodeState.REBOOTING,            # Shutting Down (?)
         4: NodeState.UNKNOWN               # Reserved
    }

    def list_nodes(self):
        # List
        # Provide a list of all nodes that this API key has access to.
        params = { "api_action": "linode.list" }
        data = self.connection.request(LINODE_ROOT, params=params).object
        return [self._to_node(n) for n in data]

    def reboot_node(self, node):
        # Reboot
        # Execute a shutdown and boot job for the given Node.
        params = { "api_action": "linode.reboot", "LinodeID": node.id }
        self.connection.request(LINODE_ROOT, params=params)
        return True

    def destroy_node(self, node):
        # Destroy
        # Terminates a Node.  With prejudice.
        params = { "api_action": "linode.delete", "LinodeID": node.id,
            "skipChecks": True }
        self.connection.request(LINODE_ROOT, params=params)
        return True

    def create_node(self, **kwargs):
        """Create a new linode instance

        See L{NodeDriver.create_node} for more keyword args.

        @keyword    ex_swap: Size of the swap partition in MB (128).
        @type       ex_swap: C{number}

        @keyword    ex_rsize: Size of the root partition (plan size - swap).
        @type       ex_rsize: C{number}

        @keyword    ex_kernel: A kernel ID from avail.kernels (Latest 2.6).
        @type       ex_kernel: C{number}

        @keyword    ex_payment: One of 1, 12, or 24; subscription length (1)
        @type       ex_payment: C{number}

        @keyword    ex_comment: Comments to store with the config
        @type       ex_comment: C{str}
        """
        #    Labels to override what's generated (default on right):
        #       lconfig      [%name] Instance
        #       lrecovery    [%name] Finnix Recovery Configuration
        #       lroot        [%name] %distro
        #       lswap        [%name] Swap Space
        #
        # Datacenter logic:
        #
        #   As Linode requires choosing a datacenter, a little logic is done.
        #
        #   1. If the API key in use has all its Linodes in one DC, that DC will
        #      be chosen (and can be overridden with linode_set_datacenter).
        #
        #   2. Otherwise (for both the "No Linodes" and "different DC" cases), a
        #      datacenter must explicitly be chosen using linode_set_datacenter.
        #
        # Please note that for safety, only 5 Linodes can be created per hour.

        name = kwargs["name"]
        chosen = kwargs["location"].id
        image = kwargs["image"]
        size = kwargs["size"]
        auth = kwargs["auth"]

        # Step 0: Parameter validation before we purchase
        # We're especially careful here so we don't fail after purchase, rather
        # than getting halfway through the process and having the API fail.

        # Plan ID
        plans = self.list_sizes()
        if size.id not in [p.id for p in plans]:
            raise LinodeException(0xFB, "Invalid plan ID -- avail.plans")

        # Payment schedule
        payment = "1" if "ex_payment" not in kwargs else str(kwargs["ex_payment"])
        if payment not in ["1", "12", "24"]:
            raise LinodeException(0xFB, "Invalid subscription (1, 12, 24)")

        ssh = None
        root = None
        # SSH key and/or root password
        if isinstance(auth, NodeAuthSSHKey):
            ssh = auth.pubkey
        elif isinstance(auth, NodeAuthPassword):
            root = auth.password

        if not ssh and not root:
            raise LinodeException(0xFB, "Need SSH key or root password")
        if not root is None and len(root) < 6:
            raise LinodeException(0xFB, "Root password is too short")

        # Swap size
        try: swap = 128 if "ex_swap" not in kwargs else int(kwargs["ex_swap"])
        except: raise LinodeException(0xFB, "Need an integer swap size")

        # Root partition size
        imagesize = (size.disk - swap) if "ex_rsize" not in kwargs else \
            int(kwargs["ex_rsize"])
        if (imagesize + swap) > size.disk:
            raise LinodeException(0xFB, "Total disk images are too big")

        # Distribution ID
        distros = self.list_images()
        if image.id not in [d.id for d in distros]:
            raise LinodeException(0xFB,
                                  "Invalid distro -- avail.distributions")

        # Kernel
        if "ex_kernel" in kwargs:
            kernel = kwargs["ex_kernel"]
        else:
            if image.extra['64bit']:
                kernel = 111 if image.extra['pvops'] else 107
            else:
                kernel = 110 if image.extra['pvops'] else 60
        params = { "api_action": "avail.kernels" }
        kernels = self.connection.request(LINODE_ROOT, params=params).object
        if kernel not in [z["KERNELID"] for z in kernels]:
            raise LinodeException(0xFB, "Invalid kernel -- avail.kernels")

        # Comments
        comments = "Created by libcloud <http://www.libcloud.org>" if \
            "ex_comment" not in kwargs else kwargs["ex_comment"]

        # Labels
        label = {
            "lconfig": "[%s] Configuration Profile" % name,
            "lrecovery": "[%s] Finnix Recovery Configuration" % name,
            "lroot": "[%s] %s Disk Image" % (name, image.name),
            "lswap": "[%s] Swap Space" % name
        }
        for what in ["lconfig", "lrecovery", "lroot", "lswap"]:
            if what in kwargs:
                label[what] = kwargs[what]

        # Step 1: linode.create
        params = {
            "api_action":   "linode.create",
            "DatacenterID": chosen,
            "PlanID":       size.id,
            "PaymentTerm":  payment
        }
        data = self.connection.request(LINODE_ROOT, params=params).object
        linode = { "id": data["LinodeID"] }

        # Step 2: linode.disk.createfromdistribution
        if not root:
            root = os.urandom(8).encode('hex')
        params = {
            "api_action":       "linode.disk.createfromdistribution",
            "LinodeID":         linode["id"],
            "DistributionID":   image.id,
            "Label":            label["lroot"],
            "Size":             imagesize,
            "rootPass":         root,
        }
        if ssh: params["rootSSHKey"] = ssh
        data = self.connection.request(LINODE_ROOT, params=params).object
        linode["rootimage"] = data["DiskID"]

        # Step 3: linode.disk.create for swap
        params = {
            "api_action":       "linode.disk.create",
            "LinodeID":         linode["id"],
            "Label":            label["lswap"],
            "Type":             "swap",
            "Size":             swap
        }
        data = self.connection.request(LINODE_ROOT, params=params).object
        linode["swapimage"] = data["DiskID"]

        # Step 4: linode.config.create for main profile
        disks = "%s,%s,,,,,,," % (linode["rootimage"], linode["swapimage"])
        params = {
            "api_action":       "linode.config.create",
            "LinodeID":         linode["id"],
            "KernelID":         kernel,
            "Label":            label["lconfig"],
            "Comments":         comments,
            "DiskList":         disks
        }
        data = self.connection.request(LINODE_ROOT, params=params).object
        linode["config"] = data["ConfigID"]

        # TODO: Recovery image (Finnix)

        # Step 5: linode.boot
        params = {
            "api_action":       "linode.boot",
            "LinodeID":         linode["id"],
            "ConfigID":         linode["config"]
        }
        data = self.connection.request(LINODE_ROOT, params=params).object

        # Make a node out of it and hand it back
        params = { "api_action": "linode.list", "LinodeID": linode["id"] }
        data = self.connection.request(LINODE_ROOT, params=params).object
        return self._to_node(data[0])

    def list_sizes(self, location=None):
        # List Sizes
        # Retrieve all available Linode plans.
        # FIXME: Prices get mangled due to 'float'.
        params = { "api_action": "avail.linodeplans" }
        data = self.connection.request(LINODE_ROOT, params=params).object
        sizes = []
        for obj in data:
            n = NodeSize(id=obj["PLANID"], name=obj["LABEL"], ram=obj["RAM"],
                    disk=(obj["DISK"] * 1024), bandwidth=obj["XFER"],
                    price=obj["PRICE"], driver=self.connection.driver)
            sizes.append(n)
        return sizes

    def list_images(self, location=None):
        # List Images
        # Retrieve all available Linux distributions.
        params = { "api_action": "avail.distributions" }
        data = self.connection.request(LINODE_ROOT, params=params).object
        distros = []
        for obj in data:
            i = NodeImage(id=obj["DISTRIBUTIONID"],
                          name=obj["LABEL"],
                          driver=self.connection.driver,
                          extra={'pvops': obj['REQUIRESPVOPSKERNEL'],
                                 '64bit': obj['IS64BIT']})
            distros.append(i)
        return distros

    def list_locations(self):
        params = { "api_action": "avail.datacenters" }
        data = self.connection.request(LINODE_ROOT, params=params).object
        nl = []
        for dc in data:
            country = None
            #TODO: this is a hack!
            if dc["LOCATION"][-3:] == "USA":
                country = "US"
            elif dc["LOCATION"][-2:] == "UK":
                country = "GB"
            else:
                raise LinodeException(
                    0xFD,
                    "Unable to convert data center location to country: '%s'"
                    % dc["LOCATION"]
                )
            nl.append(NodeLocation(dc["DATACENTERID"],
                                   dc["LOCATION"],
                                   country,
                                   self))
        return nl

    def linode_set_datacenter(self, did):
        # Set the datacenter for create requests.
        #
        # Create will try to guess, based on where all of the API key's
        # Linodes are located; if they are all in one location, Create will
        # make a new node there.  If there are NO Linodes on the account or
        # Linodes are in multiple locations, it is imperative to set this or
        # creates will fail.
        params = { "api_action": "avail.datacenters" }
        data = self.connection.request(LINODE_ROOT, params=params).object
        for dc in data:
            if did == dc["DATACENTERID"]:
                self.datacenter = did
                return

        dcs = ", ".join([d["DATACENTERID"] for d in data])
        self.datacenter = None
        raise LinodeException(0xFD, "Invalid datacenter (use one of %s)" % dcs)

    def _to_node(self, obj):
        # Convert a returned Linode instance into a Node instance.
        lid = obj["LINODEID"]

        # Get the IP addresses for a Linode
        params = { "api_action": "linode.ip.list", "LinodeID": lid }
        req = self.connection.request(LINODE_ROOT, params=params)
        if not req.success() or len(req.object) == 0:
            return None

        public_ip = []
        private_ip = []
        for ip in req.object:
            if ip["ISPUBLIC"]:
                public_ip.append(ip["IPADDRESS"])
            else:
                private_ip.append(ip["IPADDRESS"])

        n = Node(id=lid, name=obj["LABEL"],
            state=self.LINODE_STATES[obj["STATUS"]], public_ip=public_ip,
            private_ip=private_ip, driver=self.connection.driver)
        n.extra = copy(obj)
        return n

    features = {"create_node": ["ssh_key", "password"]}
