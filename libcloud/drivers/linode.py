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

"""libcloud driver for the Linode(R) API

This driver implements all libcloud functionality for the Linode API.  Since the
API is a bit more fine-grained, create_node abstracts a significant amount of
work (and may take a while to run).

Linode home page                    http://www.linode.com/
Linode API documentation            http://www.linode.com/api/
Alternate bindings for reference    http://github.com/tjfontaine/linode-python

Linode(R) is a registered trademark of Linode, LLC.

Maintainer: Jed Smith <jed@linode.com>"""

from libcloud.types import Provider, NodeState, InvalidCredsException
from libcloud.base import ConnectionKey, Response
from libcloud.base import NodeDriver, NodeSize, Node, NodeLocation
from libcloud.base import NodeAuthPassword, NodeAuthSSHKey
from libcloud.base import NodeImage
from copy import copy
import os

# Where requests go - in beta situations, this information may change.
LINODE_API = "api.linode.com"
LINODE_ROOT = "/"

# Map of TOTALRAM to PLANID, allows us to figure out what plan
# a particular node is on (updated with new plan sizes 6/28/10)
LINODE_PLAN_IDS = {512:'1',
                   768:'2',
                  1024:'3',
                  1536:'4',
                  2048:'5',
                  4096:'6',
                  8192:'7',
                 12288:'8',
                 16384:'9',
                 20480:'10'}

# JSON is included in the standard library starting with Python 2.6.  For 2.5
# and 2.4, there's a simplejson egg at: http://pypi.python.org/pypi/simplejson
try: import json
except: import simplejson as json


class LinodeException(Exception):
    """Error originating from the Linode API

    This class wraps a Linode API error, a list of which is available in the
    API documentation.  All Linode API errors are a numeric code and a
    human-readable description.
    """
    def __str__(self):
        return "(%u) %s" % (self.args[0], self.args[1])
    def __repr__(self):
        return "<LinodeException code %u '%s'>" % (self.args[0], self.args[1])


class LinodeResponse(Response):
    """Linode API response

    Wraps the HTTP response returned by the Linode API, which should be JSON in
    this structure:

       {
         "ERRORARRAY": [ ... ],
         "DATA": [ ... ],
         "ACTION": " ... "
       }

    libcloud does not take advantage of batching, so a response will always
    reflect the above format.  A few weird quirks are caught here as well."""
    def __init__(self, response):
        """Instantiate a LinodeResponse from the HTTP response

        @keyword response: The raw response returned by urllib
        @return: parsed L{LinodeResponse}"""
        self.body = response.read()
        self.status = response.status
        self.headers = dict(response.getheaders())
        self.error = response.reason
        self.invalid = LinodeException(0xFF,
                                       "Invalid JSON received from server")

        # Move parse_body() to here;  we can't be sure of failure until we've
        # parsed the body into JSON.
        self.action, self.object, self.errors = self.parse_body()
        if not self.success():
            # Raise the first error, as there will usually only be one
            raise self.errors[0]

    def parse_body(self):
        """Parse the body of the response into JSON objects

        If the response chokes the parser, action and data will be returned as
        None and errorarray will indicate an invalid JSON exception.

        @return: triple of action (C{str}), data, and errors (C{list})"""
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
        """Parse errors from the response

        @return: C{list} of errors, possibly empty"""
        try:
            js = json.loads(self.body)
            if "ERRORARRAY" not in js:
                return [self.invalid]
            return [self._make_excp(e) for e in js["ERRORARRAY"]]
        except:
            return [self.invalid]

    def success(self):
        """Check the response for success

        The way we determine success is by the presence of an error in
        ERRORARRAY.  If one is there, we assume the whole request failed.

        @return: C{bool} indicating a successful request"""
        return len(self.errors) == 0

    def _make_excp(self, error):
        """Convert an API error to a LinodeException instance

        @keyword error: JSON object containing C{ERRORCODE} and C{ERRORMESSAGE}
        @type error: dict"""
        if "ERRORCODE" not in error or "ERRORMESSAGE" not in error:
            return None
        if error["ERRORCODE"] == 4:
            return InvalidCredsException(error["ERRORMESSAGE"])
        return LinodeException(error["ERRORCODE"], error["ERRORMESSAGE"])


class LinodeConnection(ConnectionKey):
    """A connection to the Linode API

    Wraps SSL connections to the Linode API, automagically injecting the
    parameters that the API needs for each request."""
    host = LINODE_API
    responseCls = LinodeResponse

    def add_default_params(self, params):
        """Add parameters that are necessary for every request

        This method adds C{api_key} and C{api_responseFormat} to the request."""
        params["api_key"] = self.key
        # Be explicit about this in case the default changes.
        params["api_responseFormat"] = "json"
        return params


class LinodeNodeDriver(NodeDriver):
    """libcloud driver for the Linode API

    Rough mapping of which is which:

        list_nodes              linode.list
        reboot_node             linode.reboot
        destroy_node            linode.delete
        create_node             linode.create, linode.update,
                                linode.disk.createfromdistribution,
                                linode.disk.create, linode.config.create,
                                linode.ip.addprivate, linode.boot
        list_sizes              avail.linodeplans
        list_images             avail.distributions
        list_locations          avail.datacenters

    For more information on the Linode API, be sure to read the reference:

        http://www.linode.com/api/
    """
    type = Provider.LINODE
    name = "Linode"
    connectionCls = LinodeConnection
    _linode_plan_ids = LINODE_PLAN_IDS

    def __init__(self, key):
        """Instantiate the driver with the given API key

        @keyword key: the API key to use
        @type key: C{str}"""
        self.datacenter = None
        NodeDriver.__init__(self, key)

    # Converts Linode's state from DB to a NodeState constant.
    # Some of these are lightly questionable.
    LINODE_STATES = {
        -2: NodeState.UNKNOWN,              # Boot Failed
        -1: NodeState.PENDING,              # Being Created
         0: NodeState.PENDING,              # Brand New
         1: NodeState.RUNNING,              # Running
         2: NodeState.REBOOTING,            # Powered Off
         3: NodeState.REBOOTING,            # Shutting Down
         4: NodeState.UNKNOWN               # Reserved
    }

    def list_nodes(self):
        """List all Linodes that the API key can access

        This call will return all Linodes that the API key in use has access to.
        If a node is in this list, rebooting will work; however, creation and
        destruction are a separate grant.

        @return: C{list} of L{Node} objects that the API key can access"""
        params = { "api_action": "linode.list" }
        data = self.connection.request(LINODE_ROOT, params=params).object
        return [self._to_node(n) for n in data]

    def reboot_node(self, node):
        """Reboot the given Linode

        Will issue a shutdown job followed by a boot job, using the last booted
        configuration.  In most cases, this will be the only configuration.

        @keyword node: the Linode to reboot
        @type node: L{Node}"""
        params = { "api_action": "linode.reboot", "LinodeID": node.id }
        self.connection.request(LINODE_ROOT, params=params)
        return True

    def destroy_node(self, node):
        """Destroy the given Linode

        Will remove the Linode from the account and issue a prorated credit. A
        grant for removing Linodes from the account is required, otherwise this
        method will fail.

        In most cases, all disk images must be removed from a Linode before the
        Linode can be removed; however, this call explicitly skips those
        safeguards.  There is no going back from this method.

        @keyword node: the Linode to destroy
        @type node: L{Node}"""
        params = { "api_action": "linode.delete", "LinodeID": node.id,
            "skipChecks": True }
        self.connection.request(LINODE_ROOT, params=params)
        return True

    def create_node(self, **kwargs):
        """Create a new Linode, deploy a Linux distribution, and boot

        This call abstracts much of the functionality of provisioning a Linode
        and getting it booted.  A global grant to add Linodes to the account is
        required, as this call will result in a billing charge.

        Note that there is a safety valve of 5 Linodes per hour, in order to
        prevent a runaway script from ruining your day.

        @keyword name: the name to assign the Linode (mandatory)
        @type name: C{str}

        @keyword image: which distribution to deploy on the Linode (mandatory)
        @type image: L{NodeImage}

        @keyword size: the plan size to create (mandatory)
        @type size: L{NodeSize}

        @keyword auth: an SSH key or root password (mandatory)
        @type auth: L{NodeAuthSSHKey} or L{NodeAuthPassword}

        @keyword location: which datacenter to create the Linode in
        @type location: L{NodeLocation}

        @keyword ex_swap: size of the swap partition in MB (128)
        @type ex_swap: C{int}

        @keyword ex_rsize: size of the root partition in MB (plan size - swap).
        @type ex_rsize: C{int}

        @keyword ex_kernel: a kernel ID from avail.kernels (Latest 2.6 Stable).
        @type ex_kernel: C{str}

        @keyword ex_payment: one of 1, 12, or 24; subscription length (1)
        @type ex_payment: C{int}

        @keyword ex_comment: a small comment for the configuration (libcloud)
        @type ex_comment: C{str}

        @keyword ex_private: whether or not to request a private IP (False)
        @type ex_private: C{bool}

        @keyword lconfig: what to call the configuration (generated)
        @type lconfig: C{str}

        @keyword lroot: what to call the root image (generated)
        @type lroot: C{str}

        @keyword lswap: what to call the swap space (generated)
        @type lswap: C{str}

        @return: a L{Node} representing the newly-created Linode
        """
        name = kwargs["name"]
        image = kwargs["image"]
        size = kwargs["size"]
        auth = kwargs["auth"]

        # Pick a location (resolves LIBCLOUD-41 in JIRA)
        if "location" in kwargs:
            chosen = kwargs["location"].id
        elif self.datacenter:
            chosen = self.datacenter
        else:
            raise LinodeException(0xFB, "Need to select a datacenter first")

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
        comments = "Created by Apache libcloud <http://www.libcloud.org>" if \
            "ex_comment" not in kwargs else kwargs["ex_comment"]

        # Labels
        label = {
            "lconfig": "[%s] Configuration Profile" % name,
            "lroot": "[%s] %s Disk Image" % (name, image.name),
            "lswap": "[%s] Swap Space" % name
        }
        for what in ["lconfig", "lroot", "lswap"]:
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

        # Step 1b. linode.update to rename the Linode
        params = {
            "api_action": "linode.update",
            "LinodeID": linode["id"],
            "Label": name
        }
        data = self.connection.request(LINODE_ROOT, params=params).object

        # Step 1c. linode.ip.addprivate if it was requested
        if "ex_private" in kwargs and kwargs["ex_private"]:
            params = {
                "api_action":   "linode.ip.addprivate",
                "LinodeID":     linode["id"]
            }
            data = self.connection.request(LINODE_ROOT, params=params).object

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
        """List available Linode plans

        Gets the sizes that can be used for creating a Linode.  Since available
        Linode plans vary per-location, this method can also be passed a
        location to filter the availability.

        @keyword location: the facility to retrieve plans in
        @type location: NodeLocation

        @return: a C{list} of L{NodeSize}s"""
        params = { "api_action": "avail.linodeplans" }
        data = self.connection.request(LINODE_ROOT, params=params).object
        sizes = []
        for obj in data:
            n = NodeSize(id=obj["PLANID"], name=obj["LABEL"], ram=obj["RAM"],
                    disk=(obj["DISK"] * 1024), bandwidth=obj["XFER"],
                    price=obj["PRICE"], driver=self.connection.driver)
            sizes.append(n)
        return sizes

    def list_images(self):
        """List available Linux distributions

        Retrieve all Linux distributions that can be deployed to a Linode.

        @return: a C{list} of L{NodeImage}s"""
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
        """List available facilities for deployment

        Retrieve all facilities that a Linode can be deployed in.

        @return: a C{list} of L{NodeLocation}s"""
        params = { "api_action": "avail.datacenters" }
        data = self.connection.request(LINODE_ROOT, params=params).object
        nl = []
        for dc in data:
            country = None
            if "USA" in dc["LOCATION"]: country = "US"
            elif "UK" in dc["LOCATION"]: country = "GB"
            else: country = "??"
            nl.append(NodeLocation(dc["DATACENTERID"],
                                   dc["LOCATION"],
                                   country,
                                   self))
        return nl

    def linode_set_datacenter(self, dc):
        """Set the default datacenter for Linode creation

        Since Linodes must be created in a facility, this function sets the
        default that L{create_node} will use.  If a C{location} keyword is not
        passed to L{create_node}, this method must have already been used.

        @keyword dc: the datacenter to create Linodes in unless specified
        @type dc: L{NodeLocation}"""
        did = dc.id
        params = { "api_action": "avail.datacenters" }
        data = self.connection.request(LINODE_ROOT, params=params).object
        for datacenter in data:
            if did == dc["DATACENTERID"]:
                self.datacenter = did
                return

        dcs = ", ".join([d["DATACENTERID"] for d in data])
        self.datacenter = None
        raise LinodeException(0xFD, "Invalid datacenter (use one of %s)" % dcs)

    def _to_node(self, obj):
        """Convert a returned JSON Linode into a Node instance

        @keyword obj: a JSON dictionary representing the Linode
        @type obj: C{dict}
        @return: L{Node}"""
        lid = str(obj["LINODEID"])

        # Get the IP addresses for the Linode
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
        n.extra["PLANID"] = self._linode_plan_ids.get(obj.get("TOTALRAM"))
        return n

    features = {"create_node": ["ssh_key", "password"]}
