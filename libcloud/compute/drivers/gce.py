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
Module for Google Compute Engine Driver.
"""
from __future__ import with_statement

import datetime
import time
import sys
import os
import getpass

from libcloud.common.google import GoogleResponse
from libcloud.common.google import GoogleBaseConnection
from libcloud.common.google import ResourceNotFoundError

from libcloud.common.types import MalformedResponseError
from libcloud.compute.base import Node, NodeDriver, NodeImage, NodeLocation
from libcloud.compute.base import NodeSize, StorageVolume, UuidMixin
from libcloud.compute.providers import Provider
from libcloud.compute.types import NodeState, LibcloudError

API_VERSION = 'v1beta15'
DEFAULT_TASK_COMPLETION_TIMEOUT = 180


def timestamp_to_datetime(timestamp):
    """
    Return a datetime object that corresponds to the time in an RFC3339
    timestamp.

    @param  timestamp: RFC3339 timestamp string
    @type   timestamp: C{str}

    @return:  Datetime object corresponding to timestamp
    @rtype:   C{datetime}
    """
    # We remove timezone offset and microseconds (Python 2.5 strptime doesn't
    # support %f)
    ts = datetime.datetime.strptime(timestamp[:-10], '%Y-%m-%dT%H:%M:%S')
    tz_hours = int(timestamp[-5:-3])
    tz_mins = int(timestamp[-2:]) * int(timestamp[-6:-5] + '1')
    tz_delta = datetime.timedelta(hours=tz_hours, minutes=tz_mins)
    return ts + tz_delta


class GCEResponse(GoogleResponse):
    pass


class GCEConnection(GoogleBaseConnection):
    """Connection class for the GCE driver."""
    host = 'www.googleapis.com'
    responseCls = GCEResponse

    def __init__(self, user_id, key, secure, auth_type=None,
                 credential_file=None, project=None, **kwargs):
        self.scope = ['https://www.googleapis.com/auth/compute']
        super(GCEConnection, self).__init__(user_id, key, secure=secure,
                                            auth_type=auth_type,
                                            credential_file=credential_file,
                                            **kwargs)
        self.request_path = '/compute/%s/projects/%s' % (API_VERSION,
                                                         project)


class GCEAddress(UuidMixin):
    """A GCE Static address."""
    def __init__(self, id, name, address, region, driver, extra=None):
        self.id = str(id)
        self.name = name
        self.address = address
        self.region = region
        self.driver = driver
        self.extra = extra
        UuidMixin.__init__(self)

    def __repr__(self):
        return '<GCEAddress id="%s" name="%s" address="%s">' % (
            self.id, self.name, self.address)

    def destroy(self):
        """
        Destroy this address.

        @return: True if successful
        @rtype:  C{bool}
        """
        return self.driver.ex_destroy_address(address=self)


class GCEFailedNode(object):
    """Dummy Node object for nodes that are not created."""
    def __init__(self, name, error, code):
        self.name = name
        self.error = error
        self.code = code

    def __repr__(self):
        return '<GCEFailedNode name="%s" error_code="%s">' % (
            self.name, self.code)


class GCEHealthCheck(UuidMixin):
    """A GCE Http Health Check class."""
    def __init__(self, id, name, path, port, interval, timeout,
                 unhealthy_threshold, healthy_threshold, driver, extra=None):
        self.id = str(id)
        self.name = name
        self.path = path
        self.port = port
        self.interval = interval
        self.timeout = timeout
        self.unhealthy_threshold = unhealthy_threshold
        self.healthy_threshold = healthy_threshold
        self.driver = driver
        self.extra = extra
        UuidMixin.__init__(self)

    def __repr__(self):
        return '<GCEHealthCheck id="%s" name="%s" path="%s" port="%s">' % (
            self.id, self.name, self.path, self.port)

    def destroy(self):
        """
        Destroy this Health Check.

        @return:  True if successful
        @rtype:   C{bool}
        """
        return self.driver.ex_destroy_healthcheck(healthcheck=self)

    def update(self):
        """
        Commit updated healthcheck values.

        @return:  Updated Healthcheck object
        @rtype:   L{GCEHealthcheck}
        """
        return self.driver.ex_update_healthcheck(healthcheck=self)


class GCEFirewall(UuidMixin):
    """A GCE Firewall rule class."""
    def __init__(self, id, name, allowed, network, source_ranges, source_tags,
                 driver, extra=None):
        self.id = str(id)
        self.name = name
        self.network = network
        self.allowed = allowed
        self.source_ranges = source_ranges
        self.source_tags = source_tags
        self.driver = driver
        self.extra = extra
        UuidMixin.__init__(self)

    def __repr__(self):
        return '<GCEFirewall id="%s" name="%s" network="%s">' % (
            self.id, self.name, self.network.name)

    def destroy(self):
        """
        Destroy this firewall.

        @return: True if successful
        @rtype:  C{bool}
        """
        return self.driver.ex_destroy_firewall(firewall=self)

    def update(self):
        """
        Commit updated firewall values.

        @return:  Updated Firewall object
        @rtype:   L{GCEFirewall}
        """
        return self.driver.ex_update_firewall(firewall=self)


class GCEForwardingRule(UuidMixin):
    def __init__(self, id, name, region, address, protocol, targetpool, driver,
                 extra=None):
        self.id = str(id)
        self.name = name
        self.region = region
        self.address = address
        self.protocol = protocol
        self.targetpool = targetpool
        self.driver = driver
        self.extra = extra
        UuidMixin.__init__(self)

    def __repr__(self):
        return '<GCEForwardingRule id="%s" name="%s" address="%s">' % (
            self.id, self.name, self.address)

    def destroy(self):
        """
        Destroy this Forwarding Rule

        @return:  True if successful
        @rtype:   C{bool}
        """
        return self.driver.ex_destroy_forwarding_rule(forwarding_rule=self)


class GCENetwork(UuidMixin):
    """A GCE Network object class."""
    def __init__(self, id, name, cidr, driver, extra=None):
        self.id = str(id)
        self.name = name
        self.cidr = cidr
        self.driver = driver
        self.extra = extra
        UuidMixin.__init__(self)

    def __repr__(self):
        return '<GCENetwork id="%s" name="%s" cidr="%s">' % (
            self.id, self.name, self.cidr)

    def destroy(self):
        """
        Destroy this newtwork

        @return: True if successful
        @rtype:  C{bool}
        """
        return self.driver.ex_destroy_network(network=self)


class GCENodeSize(NodeSize):
    """A GCE Node Size (MachineType) class."""
    def __init__(self, id, name, ram, disk, bandwidth, price, driver,
                 extra=None):
        self.extra = extra
        super(GCENodeSize, self).__init__(id, name, ram, disk, bandwidth,
                                          price, driver)


class GCEProject(UuidMixin):
    """GCE Project information."""
    def __init__(self, id, name, metadata, quotas, driver, extra=None):
        self.id = str(id)
        self.name = name
        self.metadata = metadata
        self.quotas = quotas
        self.driver = driver
        self.extra = extra
        UuidMixin.__init__(self)

    def __repr__(self):
        return '<GCEProject id="%s" name="%s">' % (self.id, self.name)


class GCERegion(UuidMixin):
    def __init__(self, id, name, status, zones, quotas, deprecated, driver,
                 extra=None):
        self.id = str(id)
        self.name = name
        self.status = status
        self.zones = zones
        self.quotas = quotas
        self.deprecated = deprecated
        self.driver = driver
        self.extra = extra
        UuidMixin.__init__(self)

    def __repr__(self):
        return '<GCERegion id="%s" name="%s", status="%s">' % (
            self.id, self.name, self.status)


class GCETargetPool(UuidMixin):
    def __init__(self, id, name, region, healthchecks, nodes, driver,
                 extra=None):
        self.id = str(id)
        self.name = name
        self.region = region
        self.healthchecks = healthchecks
        self.nodes = nodes
        self.driver = driver
        self.extra = extra
        UuidMixin.__init__(self)

    def __repr__(self):
        return '<GCETargetPool id="%s" name="%s" region="%s">' % (
            self.id, self.name, self.region.name)

    def add_node(self, node):
        """
        Add a node to this target pool.

        @param  node: Node to add
        @type   node: C{str} or L{Node}

        @return:  True if successful
        @rtype:   C{bool}
        """
        return self.driver.ex_targetpool_add_node(targetpool=self, node=node)

    def remove_node(self, node):
        """
        Remove a node from this target pool.

        @param  node: Node to remove
        @type   node: C{str} or L{Node}

        @return:  True if successful
        @rtype:   C{bool}
        """
        return self.driver.ex_targetpool_remove_node(targetpool=self,
                                                     node=node)

    def add_healthcheck(self, healthcheck):
        """
        Add a healthcheck to this target pool.

        @param  healthcheck: Healthcheck to add
        @type   healthcheck: C{str} or L{GCEHealthCheck}

        @return:  True if successful
        @rtype:   C{bool}
        """
        return self.driver.ex_targetpool_add_healthcheck(
            targetpool=self, healthcheck=healthcheck)

    def remove_healthcheck(self, healthcheck):
        """
        Remove a healthcheck from this target pool.

        @param  healthcheck: Healthcheck to remove
        @type   healthcheck: C{str} or L{GCEHealthCheck}

        @return:  True if successful
        @rtype:   C{bool}
        """
        return self.driver.ex_targetpool_remove_healthcheck(
            targetpool=self, healthcheck=healthcheck)

    def destroy(self):
        """
        Destroy this Target Pool

        @return:  True if successful
        @rtype:   C{bool}
        """
        return self.driver.ex_destroy_targetpool(targetpool=self)


class GCEZone(NodeLocation):
    """Subclass of NodeLocation to provide additional information."""
    def __init__(self, id, name, status, maintenance_windows, quotas,
                 deprecated, driver, extra=None):
        self.status = status
        self.maintenance_windows = maintenance_windows
        self.quotas = quotas
        self.deprecated = deprecated
        self.extra = extra
        country = name.split('-')[0]
        super(GCEZone, self).__init__(id=str(id), name=name, country=country,
                                      driver=driver)

    def _now(self):
        """
        Returns current UTC time.

        Can be overridden in unittests.
        """
        return datetime.datetime.utcnow()

    def _get_next_maint(self):
        """
        Returns the next Maintenance Window.

        @return:  A dictionary containing maintenance window info
                  The dictionary contains 4 keys with values of type C{str}
                      - C{name}: The name of the maintence window
                      - C{description}: Description of the maintenance window
                      - C{beginTime}: RFC3339 Timestamp
                      - C{endTime}: RFC3339 Timestamp
        @rtype:   C{dict}
        """
        begin = None
        next_window = None
        if len(self.maintenance_windows) == 1:
            return self.maintenance_windows[0]
        for mw in self.maintenance_windows:
            begin_next = timestamp_to_datetime(mw['beginTime'])
            if (not begin) or (begin_next < begin):
                begin = begin_next
                next_window = mw
        return next_window

    def _get_time_until_mw(self):
        """
        Returns time until next maintenance window.

        @return:  Time until next maintenance window
        @rtype:   C{datetime.timedelta}
        """
        next_window = self._get_next_maint()
        now = self._now()
        next_begin = timestamp_to_datetime(next_window['beginTime'])
        return next_begin - now

    def _get_next_mw_duration(self):
        """
        Returns the duration of the next maintenance window.

        @return:  Duration of next maintenance window
        @rtype:   C{datetime.timedelta}
        """
        next_window = self._get_next_maint()
        next_begin = timestamp_to_datetime(next_window['beginTime'])
        next_end = timestamp_to_datetime(next_window['endTime'])
        return next_end - next_begin

    @property
    def time_until_mw(self):
        """
        Returns the time until the next Maintenance Window as a
        datetime.timedelta object.
        """
        return self._get_time_until_mw()

    @property
    def next_mw_duration(self):
        """
        Returns the duration of the next Maintenance Window as a
        datetime.timedelta object.
        """
        return self._get_next_mw_duration()

    def __repr__(self):
        return '<GCEZone id="%s" name="%s" status="%s">' % (self.id, self.name,
                                                            self.status)


class GCENodeDriver(NodeDriver):
    """
    Base class for GCE Node Driver.
    """
    connectionCls = GCEConnection
    api_name = 'googleapis'
    name = "Google Compute Engine"
    type = Provider.GCE
    website = 'https://www.googleapis.com/'

    NODE_STATE_MAP = {
        "PROVISIONING": NodeState.PENDING,
        "STAGING": NodeState.PENDING,
        "RUNNING": NodeState.RUNNING,
        "STOPPED": NodeState.TERMINATED,
        "STOPPING": NodeState.TERMINATED,
        "TERMINATED": NodeState.TERMINATED
    }

    def __init__(self, user_id, key, datacenter=None, project=None,
                 auth_type=None, **kwargs):
        """
        @param  user_id: The email address (for service accounts) or Client ID
                         (for installed apps) to be used for authentication.
        @type   user_id: C{str}

        @param  key: The RSA Key (for service accounts) or file path containing
                     key or Client Secret (for installed apps) to be used for
                     authentication.
        @type   key: C{str}

        @keyword  datacenter: The name of the datacenter (zone) used for
                              operations.
        @type     datacenter: C{str}

        @keyword  project: Your GCE project name. (required)
        @type     project: C{str}

        @keyword  auth_type: Accepted values are "SA" or "IA"
                             ("Service Account" or "Installed Application").
                             If not supplied, auth_type will be guessed based
                             on value of user_id.
        @type     auth_type: C{str}
        """
        self.auth_type = auth_type
        self.project = project
        if not self.project:
            raise ValueError('Project name must be specified using '
                             '"project" keyword.')
        super(GCENodeDriver, self).__init__(user_id, key, **kwargs)

        # Cache Zone and Region information to reduce API calls and
        # increase speed
        self.base_path = '/compute/%s/projects/%s' % (API_VERSION,
                                                      self.project)
        self.zone_list = self.ex_list_zones()
        self.zone_dict = {}
        for zone in self.zone_list:
            self.zone_dict[zone.name] = zone
        if datacenter:
            self.zone = self.ex_get_zone(datacenter)
        else:
            self.zone = None

        self.region_list = self.ex_list_regions()
        self.region_dict = {}
        for region in self.region_list:
            self.region_dict[region.name] = region

        if self.zone:
            self.region = self._get_region_from_zone(self.zone)
        else:
            self.region = None

    def _ex_connection_class_kwargs(self):
        return {'auth_type': self.auth_type,
                'project': self.project}

    def _get_region_from_zone(self, zone):
        """
        Return the Region object that contains the given Zone object.

        @param  zone: Zone object
        @type   zone: L{GCEZone}

        @return:  Region object that contains the zone
        @rtype:   L{GCERegion}
        """
        for region in self.region_list:
            zones = [z.name for z in region.zones]
            if zone.name in zones:
                return region

    def _find_zone(self, name, res_type, region=False):
        """
        Find the zone for a named resource.

        @param  name: Name of resource to find
        @type   name: C{str}

        @param  res_type: Type of resource to find.
                          Examples include: 'disks', 'instances' or 'addresses'
        @type   res_type: C{str}

        @keyword  region: If True, find a region instead of a zone.
        @keyword  region: C{bool}

        @return:  Name of zone (or region) that the resource is in.
        @rtype:   C{str}
        """
        request = '/aggregated/%s' % res_type
        res_list = self.connection.request(request).object
        for k, v in res_list['items'].items():
            for res in v.get(res_type, []):
                if res['name'] == name:
                    if region:
                        return k.replace('regions/', '')
                    else:
                        return k.replace('zones/', '')

    def _match_images(self, project, partial_name):
        """
        Find the latest image, given a partial name.

        For example, providing 'debian-7' will return the image object for the
        most recent image with a name that starts with 'debian-7' in the
        supplied project.  If no project is given, it will search your own
        project.

        @param  project:  The name of the project to search for images.
                          Examples include: 'debian-cloud' and 'centos-cloud'.
        @type   project:  C{str} or C{None}

        @param  partial_name: The full name or beginning of a name for an
                              image.
        @type   partial_name: C{str}

        @return:  The latest image object that maches the partial name or None
                  if no matching image is found.
        @rtype:   L{NodeImage} or C{None}
        """
        project_images = self.list_images(project)
        partial_match = []
        for image in project_images:
            if image.name == partial_name:
                return image
            if image.name.startswith(partial_name):
                ts = timestamp_to_datetime(image.extra['creationTimestamp'])
                if not partial_match or partial_match[0] < ts:
                    partial_match = [ts, image]

        if partial_match:
            return partial_match[1]

    def ex_list_addresses(self, region=None):
        """
        Return a list of static addreses for a region or all.

        @keyword  region: The region to return addresses from. For example:
                          'us-central1'.  If None, will return addresses from
                          region of self.zone.  If 'all', will return all
                          addresses.
        @type     region: C{str} or C{None}

        @return: A list of static address objects.
        @rtype: C{list} of L{GCEAddress}
        """
        list_addresses = []
        # Use provided region or default region
        region = region or self.region
        # Setting region to 'all' overrides the default region
        if region == 'all':
            region = None
        if region is None:
            request = '/aggregated/addresses'
        elif hasattr(region, 'name'):
            request = '/regions/%s/addresses' % region.name
        else:
            request = '/regions/%s/addresses' % region
        response = self.connection.request(request, method='GET').object

        if 'items' in response:
            # The aggregated result returns dictionaries for each region
            if region is None:
                for v in response['items'].values():
                    region_addresses = [self._to_address(a) for a in
                                        v.get('addresses', [])]
                    list_addresses.extend(region_addresses)
            else:
                list_addresses = [self._to_address(a) for a in
                                  response['items']]
        return list_addresses

    def ex_list_healthchecks(self):
        """
        Return the list of health checks.

        @return: A list of health check objects.
        @rtype: C{list} of L{GCEHealthCheck}
        """
        list_healthchecks = []
        request = '/global/httpHealthChecks'
        response = self.connection.request(request, method='GET').object
        list_healthchecks = [self._to_healthcheck(h) for h in
                             response.get('items', [])]
        return list_healthchecks

    def ex_list_firewalls(self):
        """
        Return the list of firewalls.

        @return: A list of firewall objects.
        @rtype: C{list} of L{GCEFirewall}
        """
        list_firewalls = []
        request = '/global/firewalls'
        response = self.connection.request(request, method='GET').object
        list_firewalls = [self._to_firewall(f) for f in
                          response.get('items', [])]
        return list_firewalls

    def ex_list_forwarding_rules(self, region=None):
        """
        Return the list of forwarding rules for a region or all.

        @keyword  region: The region to return forwarding rules from.  For
                          example: 'us-central1'.  If None, will return
                          forwarding rules from the region of self.region
                          (which is based on self.zone).  If 'all', will
                          return all forwarding rules.
        @type     region: C{str} or L{GCERegion} or C{None}

        @return: A list of forwarding rule objects.
        @rtype: C{list} of L{GCEForwardingRule}
        """
        list_forwarding_rules = []
        # Use provided region or default region
        region = region or self.region
        # Setting region to 'all' overrides the default region
        if region == 'all':
            region = None
        if region is None:
            request = '/aggregated/forwardingRules'
        elif hasattr(region, 'name'):
            request = '/regions/%s/forwardingRules' % region.name
        else:
            request = '/regions/%s/forwardingRules' % region
        response = self.connection.request(request, method='GET').object

        if 'items' in response:
            # The aggregated result returns dictionaries for each region
            if region is None:
                for v in response['items'].values():
                    region_forwarding_rules = [self._to_forwarding_rule(f) for
                                               f in v.get('forwardingRules',
                                                          [])]
                    list_forwarding_rules.extend(region_forwarding_rules)
            else:
                list_forwarding_rules = [self._to_forwarding_rule(f) for f in
                                         response['items']]
        return list_forwarding_rules

    def list_images(self, ex_project=None):
        """
        Return a list of image objects for a project.

        @keyword  ex_project: Optional alternate project name.
        @type     ex_project: C{str} or C{None}

        @return:  List of NodeImage objects
        @rtype:   C{list} of L{NodeImage}
        """
        list_images = []
        request = '/global/images'
        if ex_project is None:
            response = self.connection.request(request, method='GET').object
        else:
            # Save the connection request_path
            save_request_path = self.connection.request_path
            # Override the connection request path
            new_request_path = save_request_path.replace(self.project,
                                                         ex_project)
            self.connection.request_path = new_request_path
            response = self.connection.request(request, method='GET').object
            # Restore the connection request_path
            self.connection.request_path = save_request_path
        list_images = [self._to_node_image(i) for i in
                       response.get('items', [])]
        return list_images

    def list_locations(self):
        """
        Return a list of locations (zones).

        The L{ex_list_zones} method returns more comprehensive results, but
        this is here for compatibility.

        @return: List of NodeLocation objects
        @rtype: C{list} of L{NodeLocation}
        """
        list_locations = []
        request = '/zones'
        response = self.connection.request(request, method='GET').object
        list_locations = [self._to_node_location(l) for l in response['items']]
        return list_locations

    def ex_list_networks(self):
        """
        Return the list of networks.

        @return: A list of network objects.
        @rtype: C{list} of L{GCENetwork}
        """
        list_networks = []
        request = '/global/networks'
        response = self.connection.request(request, method='GET').object
        list_networks = [self._to_network(n) for n in
                         response.get('items', [])]
        return list_networks

    def list_nodes(self, ex_zone=None):
        """
        Return a list of nodes in the current zone or all zones.

        @keyword  ex_zone:  Optional zone name or 'all'
        @type     ex_zone:  C{str} or L{GCEZone} or L{NodeLocation} or C{None}

        @return:  List of Node objects
        @rtype:   C{list} of L{Node}
        """
        list_nodes = []
        # Use provided zone or default zone
        zone = ex_zone or self.zone
        # Setting ex_zone to 'all' overrides the default zone
        if zone == 'all':
            zone = None
        if zone is None:
            request = '/aggregated/instances'
        elif hasattr(zone, 'name'):
            request = '/zones/%s/instances' % zone.name
        else:
            request = '/zones/%s/instances' % zone

        response = self.connection.request(request, method='GET').object

        if 'items' in response:
            # The aggregated response returns a dict for each zone
            if zone is None:
                for v in response['items'].values():
                    zone_nodes = [self._to_node(i) for i in
                                  v.get('instances', [])]
                    list_nodes.extend(zone_nodes)
            else:
                list_nodes = [self._to_node(i) for i in response['items']]
        return list_nodes

    def ex_list_regions(self):
        """
        Return the list of regions.

        @return: A list of region objects.
        @rtype: C{list} of L{GCERegion}
        """
        list_regions = []
        request = '/regions'
        response = self.connection.request(request, method='GET').object
        list_regions = [self._to_region(r) for r in response['items']]
        return list_regions

    def list_sizes(self, location=None):
        """
        Return a list of sizes (machineTypes) in a zone.

        @keyword  location: Location or Zone for sizes
        @type     location: C{str} or L{GCEZone} or L{NodeLocation} or C{None}

        @return:  List of GCENodeSize objects
        @rtype:   C{list} of L{GCENodeSize}
        """
        list_sizes = []
        location = location or self.zone
        if location == 'all':
            location = None
        if location is None:
            request = '/aggregated/machineTypes'
        elif hasattr(location, 'name'):
            request = '/zones/%s/machineTypes' % location.name
        else:
            request = '/zones/%s/machineTypes' % location

        response = self.connection.request(request, method='GET').object

        if 'items' in response:
            # The aggregated response returns a dict for each zone
            if location is None:
                for v in response['items'].values():
                    zone_sizes = [self._to_node_size(s) for s in
                                  v.get('machineTypes', [])]
                    list_sizes.extend(zone_sizes)
            else:
                list_sizes = [self._to_node_size(s) for s in response['items']]
        return list_sizes

    def ex_list_targetpools(self, region=None):
        """
        Return the list of target pools.

        @return:  A list of target pool objects
        @rtype:   C{list} of L{GCETargetPool}
        """
        list_targetpools = []
        # Use provided region or default region
        region = region or self.region
        # Setting region to 'all' overrides the default region
        if region == 'all':
            region = None
        if region is None:
            request = '/aggregated/targetPools'
        elif hasattr(region, 'name'):
            request = '/regions/%s/targetPools' % region.name
        else:
            request = '/regions/%s/targetPools' % region
        response = self.connection.request(request, method='GET').object

        if 'items' in response:
            # The aggregated result returns dictionaries for each region
            if region is None:
                for v in response['items'].values():
                    region_targetpools = [self._to_targetpool(t) for t in
                                          v.get('targetPools', [])]
                    list_targetpools.extend(region_targetpools)
            else:
                list_targetpools = [self._to_targetpool(t) for t in
                                    response['items']]
        return list_targetpools

    def list_volumes(self, ex_zone=None):
        """
        Return a list of volumes for a zone or all.

        Will return list from provided zone, or from the default zone unless
        given the value of 'all'.

        @keyword  ex_zone: The zone to return volumes from.
        @type     ex_zone: C{str} or L{GCEZone} or L{NodeLocation} or C{None}

        @return: A list of volume objects.
        @rtype: C{list} of L{StorageVolume}
        """
        list_volumes = []
        zone = ex_zone or self.zone
        if zone == 'all':
            zone = None
        if zone is None:
            request = '/aggregated/disks'
        elif hasattr(zone, 'name'):
            request = '/zones/%s/disks' % zone.name
        else:
            request = '/zones/%s/disks' % zone

        response = self.connection.request(request, method='GET').object
        if 'items' in response:
            # The aggregated response returns a dict for each zone
            if zone is None:
                for v in response['items'].values():
                    zone_volumes = [self._to_storage_volume(d) for d in
                                    v.get('disks', [])]
                    list_volumes.extend(zone_volumes)
            else:
                list_volumes = [self._to_storage_volume(d) for d in
                                response['items']]
        return list_volumes

    def ex_list_zones(self):
        """
        Return the list of zones.

        @return: A list of zone objects.
        @rtype: C{list} of L{GCEZone}
        """
        list_zones = []
        request = '/zones'
        response = self.connection.request(request, method='GET').object
        list_zones = [self._to_zone(z) for z in response['items']]
        return list_zones

    def ex_create_address(self, name, region=None):
        """
        Create a static address in a region.

        @param  name: Name of static address
        @type   name: C{str}

        @keyword  region: Name of region for the address (e.g. 'us-central1')
        @type     region: C{str} or L{GCERegion}

        @return:  Static Address object
        @rtype:   L{GCEAddress}
        """
        region = region or self.region
        if not hasattr(region, 'name'):
            region = self.ex_get_region(region)
        elif region is None:
            raise GCEError('REGION_NOT_SPECIFIED',
                           'Region must be provided for an address')
        address_data = {'name': name}
        request = '/regions/%s/addresses' % region.name
        response = self.connection.async_request(request, method='POST',
                                                 data=address_data).object
        return self.ex_get_address(name, region=region)

    def ex_create_healthcheck(self, name, host=None, path=None, port=None,
                              interval=None, timeout=None,
                              unhealthy_threshold=None,
                              healthy_threshold=None):
        """
        Create an Http Health Check.

        @param  name: Name of health check
        @type   name: C{str}

        @keyword  host: Hostname of health check requst.  Defaults to empty and
                        public IP is used instead.
        @type     host: C{str}

        @keyword  path: The request path for the check.  Defaults to /.
        @type     path: C{str}

        @keyword  port: The TCP port number for the check.  Defaults to 80.
        @type     port: C{int}

        @keyword  interval: How often (in seconds) to check.  Defaults to 5.
        @type     interval: C{int}

        @keyword  timeout: How long to wait before failing. Defaults to 5.
        @type     timeout: C{int}

        @keyword  unhealthy_threshold: How many failures before marking
                                       unhealthy.  Defaults to 2.
        @type     unhealthy_threshold: C{int}

        @keyword  healthy_threshold: How many successes before marking as
                                     healthy.  Defaults to 2.
        @type     healthy_threshold: C{int}

        @return:  Health Check object
        @rtype:   L{GCEHealthCheck}
        """
        hc_data = {}
        hc_data['name'] = name
        if host:
            hc_data['host'] = host
        # As of right now, the 'default' values aren't getting set when called
        # through the API, so set them explicitly
        hc_data['requestPath'] = path or '/'
        hc_data['port'] = port or 80
        hc_data['checkIntervalSec'] = interval or 5
        hc_data['timeoutSec'] = timeout or 5
        hc_data['unhealthyThreshold'] = unhealthy_threshold or 2
        hc_data['healthyThreshold'] = healthy_threshold or 2

        request = '/global/httpHealthChecks'

        response = self.connection.async_request(request, method='POST',
                                                 data=hc_data).object
        return self.ex_get_healthcheck(name)

    def ex_create_firewall(self, name, allowed, network='default',
                           source_ranges=None, source_tags=None):
        """
        Create a firewall on a network.

        Firewall rules should be supplied in the "allowed" field.  This is a
        list of dictionaries formated like so ("ports" is optional)::
            [{"IPProtocol": "<protocol string or number>",
              "ports": [ "<port_numbers or ranges>"}]

        For example, to allow tcp on port 8080 and udp on all ports, 'allowed'
        would be::
            [{"IPProtocol": "tcp",
              "ports": ["8080"]},
             {"IPProtocol": "udp"}]
        See U{Firewall Reference<https://developers.google.com/compute/docs/
        reference/latest/firewalls/insert>} for more information.

        @param  name: Name of the firewall to be created
        @type   name: C{str}

        @param  allowed: List of dictionaries with rules
        @type   allowed: C{list} of C{dict}

        @keyword  network: The network that the firewall applies to.
        @type     network: C{str} or L{GCENetwork}

        @keyword  source_ranges: A list of IP ranges in CIDR format that the
                                 firewall should apply to. Defaults to
                                 ['0.0.0.0/0']
        @type     source_ranges: C{list} of C{str}

        @keyword  source_tags: A list of instance tags which the rules apply
        @type     source_tags: C{list} of C{str}

        @return:  Firewall object
        @rtype:   L{GCEFirewall}
        """
        firewall_data = {}
        if not hasattr(network, 'name'):
            nw = self.ex_get_network(network)
        else:
            nw = network

        firewall_data['name'] = name
        firewall_data['allowed'] = allowed
        firewall_data['network'] = nw.extra['selfLink']
        firewall_data['sourceRanges'] = source_ranges or ['0.0.0.0/0']
        if source_tags is not None:
            firewall_data['sourceTags'] = source_tags

        request = '/global/firewalls'

        response = self.connection.async_request(request, method='POST',
                                                 data=firewall_data).object
        return self.ex_get_firewall(name)

    def ex_create_forwarding_rule(self, name, targetpool, region=None,
                                  protocol='tcp', port_range=None,
                                  address=None):
        """
        Create a forwarding rule.

        @param  name: Name of forwarding rule to be created
        @type   name: C{str}

        @param  targetpool: Target pool to apply the rule to
        @param  targetpool: C{str} or L{GCETargetPool}

        @keyword  region: Region to create the forwarding rule in.  Defaults to
                          self.region
        @type     region: C{str} or L{GCERegion}

        @keyword  protocol: Should be 'tcp' or 'udp'
        @type     protocol: C{str}

        @keyword  port_range: Optional single port number or range separated
                              by a dash.  Examples: '80', '5000-5999'.
        @type     port_range: C{str}

        @keyword  address: Optional static address for forwarding rule. Must be
                           in same region.
        @type     address: C{str} or L{GCEAddress}

        @return:  Forwarding Rule object
        @rtype:   L{GCEForwardingRule}
        """
        forwarding_rule_data = {}
        region = region or self.region
        if not hasattr(region, 'name'):
            region = self.ex_get_region(region)
        if not hasattr(targetpool, 'name'):
            targetpool = self.ex_get_targetpool(targetpool, region)

        forwarding_rule_data['name'] = name
        forwarding_rule_data['region'] = region.extra['selfLink']
        forwarding_rule_data['target'] = targetpool.extra['selfLink']
        forwarding_rule_data['protocol'] = protocol.upper()
        if address:
            if not hasattr(address, 'name'):
                address = self.ex_get_address(address, region)
            forwarding_rule_data['IPAddress'] = address.extra['selfLink']
        if port_range:
            forwarding_rule_data['portRange'] = port_range

        request = '/regions/%s/forwardingRules' % region.name

        response = self.connection.async_request(
            request, method='POST', data=forwarding_rule_data).object

        return self.ex_get_forwarding_rule(name)

    def ex_create_network(self, name, cidr):
        """
        Create a network.

        @param  name: Name of network to be created
        @type   name: C{str}

        @param  cidr: Address range of network in CIDR format.
        @type  cidr: C{str}

        @return:  Network object
        @rtype:   L{GCENetwork}
        """
        network_data = {}
        network_data['name'] = name
        network_data['IPv4Range'] = cidr

        request = '/global/networks'

        response = self.connection.async_request(request, method='POST',
                                                 data=network_data).object

        return self.ex_get_network(name)

    def _create_node_req(self, name, size, image, location, network,
                         tags=None, metadata=None, boot_disk=None,
                         persistent_disk=False):
        """
        Returns a request and body to create a new node.  This is a helper
        method to suppor both L{create_node} and L{ex_create_multiple_nodes}.

        @param  name: The name of the node to create.
        @type   name: C{str}

        @param  size: The machine type to use.
        @type   size: L{GCENodeSize}

        @param  image: The image to use to create the node (or, if using a
                       persistent disk, the image the disk was created from).
        @type   image: L{NodeImage}

        @param  location: The location (zone) to create the node in.
        @type   location: L{NodeLocation} or L{GCEZone}

        @param  network: The network to associate with the node.
        @type   network: L{GCENetwork}

        @keyword  tags: A list of tags to assiciate with the node.
        @type     tags: C{list} of C{str}

        @keyword  metadata: Metadata dictionary for instance.
        @type     metadata: C{dict}

        @keyword  boot_disk:  Persistent boot disk to attach.
        @type     L{StorageVolume}

        @keyword  persistent_disk: If True, create a persistent disk instead of
                                   an ephemeral one.  Has no effect if
                                   boot_disk is specified.
        @type     persistent_disk: C{bool}

        @return:  A tuple containing a request string and a node_data dict.
        @rtype:   C{tuple} of C{str} and C{dict}
        """
        node_data = {}
        node_data['machineType'] = size.extra['selfLink']
        node_data['name'] = name
        if tags:
            node_data['tags'] = {'items': tags}
        if metadata:
            node_data['metadata'] = metadata
        if (not boot_disk) and persistent_disk:
            boot_disk = self.create_volume(None, name, location=location,
                                           image=image)
        if boot_disk:
            disks = [{'kind': 'compute#attachedDisk',
                      'boot': True,
                      'type': 'PERSISTENT',
                      'mode': 'READ_WRITE',
                      'deviceName': boot_disk.name,
                      'zone': boot_disk.extra['zone'].extra['selfLink'],
                      'source': boot_disk.extra['selfLink']}]
            node_data['disks'] = disks
            node_data['kernel'] = image.extra['preferredKernel']
        else:
            node_data['image'] = image.extra['selfLink']

        ni = [{'kind': 'compute#instanceNetworkInterface',
               'accessConfigs': [{'name': 'External NAT',
                                  'type': 'ONE_TO_ONE_NAT'}],
               'network': network.extra['selfLink']}]
        node_data['networkInterfaces'] = ni

        request = '/zones/%s/instances' % location.name

        return request, node_data

    def create_node(self, name, size, image, location=None,
                    ex_network='default', ex_tags=None, ex_metadata=None,
                    ex_boot_disk=None, ex_persistent_disk=False):
        """
        Create a new node and return a node object for the node.

        @param  name: The name of the node to create.
        @type   name: C{str}

        @param  size: The machine type to use.
        @type   size: C{str} or L{GCENodeSize}

        @param  image: The image to use to create the node (or, if attaching
                       a persistent disk, the image used to create the disk)
        @type   image: C{str} or L{NodeImage}

        @keyword  location: The location (zone) to create the node in.
        @type     location: C{str} or L{NodeLocation} or L{GCEZone} or C{None}

        @keyword  ex_network: The network to associate with the node.
        @type     ex_network: C{str} or L{GCENetwork}

        @keyword  ex_tags: A list of tags to assiciate with the node.
        @type     ex_tags: C{list} of C{str} or C{None}

        @keyword  ex_metadata: Metadata dictionary for instance.
        @type     ex_metadata: C{dict} or C{None}

        @keyword  ex_boot_disk: The boot disk to attach to the instance.
        @type     ex_boot_disk: L{StorageVolume} or C{str}

        @keyword  ex_persistent_disk: If True, create a persistent_disk instead
                                      of a ephemeral one.  Has no effect if
                                      ex_boot_disk is specified.
        @type     ex_persistent_disk: C{bool}

        @return:  A Node object for the new node.
        @rtype:   L{Node}
        """
        location = location or self.zone
        if not hasattr(location, 'name'):
            location = self.ex_get_zone(location)
        if not hasattr(size, 'name'):
            size = self.ex_get_size(size, location)
        if not hasattr(ex_network, 'name'):
            ex_network = self.ex_get_network(ex_network)
        if not hasattr(image, 'name'):
            image = self.ex_get_image(image)

        request, node_data = self._create_node_req(name, size, image,
                                                   location, ex_network,
                                                   ex_tags, ex_metadata,
                                                   ex_boot_disk,
                                                   ex_persistent_disk)
        response = self.connection.async_request(request, method='POST',
                                                 data=node_data).object

        return self.ex_get_node(name, location.name)

    def ex_create_multiple_nodes(self, base_name, size, image, number,
                                 location=None, ex_network='default',
                                 ex_tags=None, ex_metadata=None,
                                 ignore_errors=True, ex_persistent_disk=False,
                                 timeout=DEFAULT_TASK_COMPLETION_TIMEOUT):
        """
        Create multiple nodes and return a list of Node objects.

        Nodes will be named with the base name and a number.  For example, if
        the base name is 'libcloud' and you create 3 nodes, they will be
        named::
            libcloud-000
            libcloud-001
            libcloud-002

        @param  base_name: The base name of the nodes to create.
        @type   base_name: C{str}

        @param  size: The machine type to use.
        @type   size: C{str} or L{GCENodeSize}

        @param  image: The image to use to create the nodes.
        @type   image: C{str} or L{NodeImage}

        @param  number: The number of nodes to create.
        @type   number: C{int}

        @keyword  location: The location (zone) to create the nodes in.
        @type     location: C{str} or L{NodeLocation} or L{GCEZone} or C{None}

        @keyword  ex_network: The network to associate with the nodes.
        @type     ex_network: C{str} or L{GCENetwork}

        @keyword  ex_tags: A list of tags to assiciate with the nodes.
        @type     ex_tags: C{list} of C{str} or C{None}

        @keyword  ex_metadata: Metadata dictionary for instances.
        @type     ex_metadata: C{dict} or C{None}

        @keyword  ignore_errors: If True, don't raise Exceptions if one or
                                 more nodes fails.
        @type     ignore_errors: C{bool}

        @keyword  persistent_disk: If True, create persistent boot disks
                                   instead of ephemeral ones.
        @type     persistent_disk: C{bool}

        @keyword  timeout: The number of seconds to wait for all nodes to be
                           created before timing out.

        @return:  A list of Node objects for the new nodes.
        @rtype:   C{list} of L{Node}
        """
        node_data = {}
        location = location or self.zone
        if not hasattr(location, 'name'):
            location = self.ex_get_zone(location)
        if not hasattr(size, 'name'):
            size = self.ex_get_size(size, location)
        if not hasattr(ex_network, 'name'):
            ex_network = self.ex_get_network(ex_network)
        if not hasattr(image, 'name'):
            image = self.ex_get_image(image)

        node_list = [None] * number
        responses = []
        for i in range(number):
            name = '%s-%03d' % (base_name, i)
            request, node_data = self._create_node_req(
                name, size, image, location, ex_network, ex_tags, ex_metadata,
                persistent_disk=ex_persistent_disk)
            response = self.connection.request(request, method='POST',
                                               data=node_data)
            responses.append(response.object)

        start_time = time.time()
        complete = False
        while not complete:
            if (time.time() - start_time >= timeout):
                raise Exception("Timeout (%s sec) while waiting for multiple "
                                "instances")
            complete = True
            for i, operation in enumerate(responses):
                if operation is None:
                    continue
                error = None
                try:
                    response = self.connection.request(
                        operation['selfLink']).object
                except:
                    e = sys.exc_info()[1]
                    error = e.value
                    code = e.code
                    if not ignore_errors:
                        raise e
                if response['status'] == 'DONE':
                    responses[i] = None
                    name = '%s-%03d' % (base_name, i)
                    if error:
                        node_list[i] = GCEFailedNode(name, error, code)
                    else:
                        node_list[i] = self.ex_get_node(name, location.name)
                else:
                    complete = False
                    time.sleep(2)
        return node_list

    def ex_create_targetpool(self, name, region=None, healthchecks=None,
                             nodes=None):
        """
        Create a target pool.

        @param  name: Name of target pool
        @type   name: C{str}

        @keyword  region: Region to create the target pool in. Defaults to
                          self.region
        @type     region: C{str} or L{GCERegion} or C{None}

        @keyword  healthchecks: Optional list of health checks to attach
        @type     healthchecks: C{list} of C{str} or L{GCEHealthCheck}

        @keyword  nodes:  Optional list of nodes to attach to the pool
        @type     nodes:  C{list} of C{str} or L{Node}

        @return:  Target Pool object
        @rtype:   L{GCETargetPool}
        """
        region = region or self.region
        targetpool_data = {}
        targetpool_data['name'] = name
        if not hasattr(region, 'name'):
            region = self.ex_get_region(region)
        targetpool_data['region'] = region.extra['selfLink']

        if healthchecks:
            if not hasattr(healthchecks[0], 'name'):
                hc_list = [self.ex_get_healthcheck(h).extra['selfLink'] for h
                           in healthchecks]
            else:
                hc_list = [h.extra['selfLink'] for h in healthchecks]
            targetpool_data['healthChecks'] = hc_list
        if nodes:
            if not hasattr(nodes[0], 'name'):
                node_list = [self.ex_get_node(n, 'all').extra['selfLink'] for n
                             in nodes]
            else:
                node_list = [n.extra['selfLink'] for n in nodes]
            targetpool_data['instances'] = node_list

        request = '/regions/%s/targetPools' % region.name

        response = self.connection.async_request(request, method='POST',
                                                 data=targetpool_data).object

        return self.ex_get_targetpool(name, region)

    def create_volume(self, size, name, location=None, image=None,
                      snapshot=None):
        """
        Create a volume (disk).

        @param  size: Size of volume to create (in GB). Can be None if image
                      or snapshot is supplied.
        @type   size: C{int} or C{str} or C{None}

        @param  name: Name of volume to create
        @type   name: C{str}

        @keyword  location: Location (zone) to create the volume in
        @type     location: C{str} or L{GCEZone} or L{NodeLocation} or C{None}

        @keyword  image: Image to create disk from.
        @type     image: L{NodeImage} or C{str} or C{None}

        @keyword  snapshot: Snapshot to create image from (needs full URI)
        @type     snapshot: C{str}

        @return:  Storage Volume object
        @rtype:   L{StorageVolume}
        """
        volume_data = {}
        params = None
        volume_data['name'] = name
        if size:
            volume_data['sizeGb'] = str(size)
        if image:
            if not hasattr(image, 'name'):
                image = self.ex_get_image(image)
            params = {'sourceImage': image.extra['selfLink']}
            volume_data['description'] = 'Image: %s' % image.extra['selfLink']
        if snapshot:
            volume_data['sourceSnapshot'] = snapshot
            volume_data['description'] = 'Snapshot: %s' % snapshot
        location = location or self.zone
        if not hasattr(location, 'name'):
            location = self.ex_get_zone(location)
        request = '/zones/%s/disks' % location.name
        response = self.connection.async_request(request, method='POST',
                                                 data=volume_data,
                                                 params=params).object

        return self.ex_get_volume(name, location)

    def ex_update_healthcheck(self, healthcheck):
        """
        Update a health check with new values.

        To update, change the attributes of the health check object and pass
        the updated object to the method.

        @param  healthcheck: A healthcheck object with updated values.
        @type   healthcheck: L{GCEHealthCheck}

        @return:  An object representing the new state of the health check.
        @rtype:   L{GCEHealthCheck}
        """
        hc_data = {}
        hc_data['name'] = healthcheck.name
        hc_data['requestPath'] = healthcheck.path
        hc_data['port'] = healthcheck.port
        hc_data['checkIntervalSec'] = healthcheck.interval
        hc_data['timeoutSec'] = healthcheck.timeout
        hc_data['unhealthyThreshold'] = healthcheck.unhealthy_threshold
        hc_data['healthyThreshold'] = healthcheck.healthy_threshold
        if healthcheck.extra['host']:
            hc_data['host'] = healthcheck.extra['host']
        if healthcheck.extra['description']:
            hc_data['description'] = healthcheck.extra['description']

        request = '/global/httpHealthChecks/%s' % healthcheck.name

        response = self.connection.async_request(request, method='PUT',
                                                 data=hc_data).object

        return self.ex_get_healthcheck(healthcheck.name)

    def ex_update_firewall(self, firewall):
        """
        Update a firewall with new values.

        To update, change the attributes of the firewall object and pass the
        updated object to the method.

        @param  firewall: A firewall object with updated values.
        @type   firewall: L{GCEFirewall}

        @return:  An object representing the new state of the firewall.
        @rtype:   L{GCEFirewall}
        """
        firewall_data = {}
        firewall_data['name'] = firewall.name
        firewall_data['allowed'] = firewall.allowed
        firewall_data['network'] = firewall.network.extra['selfLink']
        if firewall.source_ranges:
            firewall_data['sourceRanges'] = firewall.source_ranges
        if firewall.source_tags:
            firewall_data['sourceTags'] = firewall.source_tags
        if firewall.extra['description']:
            firewall_data['description'] = firewall.extra['description']

        request = '/global/firewalls/%s' % firewall.name

        response = self.connection.async_request(request, method='PUT',
                                                 data=firewall_data).object

        return self.ex_get_firewall(firewall.name)

    def ex_targetpool_add_node(self, targetpool, node):
        """
        Add a node to a target pool.

        @param  targetpool: The targetpool to add node to
        @type   targetpool: C{str} or L{GCETargetPool}

        @param  node: The node to add
        @type   node: C{str} or L{Node}

        @returns: True if successful
        @rtype:   C{bool}
        """
        if not hasattr(targetpool, 'name'):
            targetpool = self.ex_get_targetpool(targetpool)
        if not hasattr(node, 'name'):
            node = self.ex_get_node(node, 'all')

        targetpool_data = {'instance': node.extra['selfLink']}

        request = '/regions/%s/targetPools/%s/addInstance' % (
            targetpool.region.name, targetpool.name)
        response = self.connection.async_request(request, method='POST',
                                                 data=targetpool_data).object
        targetpool.nodes.append(node)
        return True

    def ex_targetpool_add_healthcheck(self, targetpool, healthcheck):
        """
        Add a health check to a target pool.

        @param  targetpool: The targetpool to add health check to
        @type   targetpool: C{str} or L{GCETargetPool}

        @param  healthcheck: The healthcheck to add
        @type   healthcheck: C{str} or L{GCEHealthCheck}

        @returns: True if successful
        @rtype:   C{bool}
        """
        if not hasattr(targetpool, 'name'):
            targetpool = self.ex_get_targetpool(targetpool)
        if not hasattr(healthcheck, 'name'):
            healthcheck = self.ex_get_healthcheck(healthcheck)

        targetpool_data = {'healthCheck': healthcheck.extra['selfLink']}

        request = '/regions/%s/targetPools/%s/addHealthCheck' % (
            targetpool.region.name, targetpool.name)
        response = self.connection.async_request(request, method='POST',
                                                 data=targetpool_data).object
        targetpool.healthchecks.append(healthcheck)
        return True

    def ex_targetpool_remove_node(self, targetpool, node):
        """
        Remove a node from a target pool.

        @param  targetpool: The targetpool to remove node from
        @type   targetpool: C{str} or L{GCETargetPool}

        @param  node: The node to remove
        @type   node: C{str} or L{Node}

        @returns: True if successful
        @rtype:   C{bool}
        """
        if not hasattr(targetpool, 'name'):
            targetpool = self.ex_get_targetpool(targetpool)
        if not hasattr(node, 'name'):
            node = self.ex_get_node(node, 'all')

        targetpool_data = {'instance': node.extra['selfLink']}

        request = '/regions/%s/targetPools/%s/removeInstance' % (
            targetpool.region.name, targetpool.name)
        response = self.connection.async_request(request, method='POST',
                                                 data=targetpool_data).object
        # Remove node object from node list
        index = None
        for i, nd in enumerate(targetpool.nodes):
            if nd.name == node.name:
                index = i
        if index is not None:
            targetpool.nodes.pop(index)
        return True

    def ex_targetpool_remove_healthcheck(self, targetpool, healthcheck):
        """
        Remove a health check from a target pool.

        @param  targetpool: The targetpool to remove health check from
        @type   targetpool: C{str} or L{GCETargetPool}

        @param  healthcheck: The healthcheck to remove
        @type   healthcheck: C{str} or L{GCEHealthCheck}

        @returns: True if successful
        @rtype:   C{bool}
        """
        if not hasattr(targetpool, 'name'):
            targetpool = self.ex_get_targetpool(targetpool)
        if not hasattr(healthcheck, 'name'):
            healthcheck = self.ex_get_healthcheck(healthcheck)

        targetpool_data = {'healthCheck': healthcheck.extra['selfLink']}

        request = '/regions/%s/targetPools/%s/removeHealthCheck' % (
            targetpool.region.name, targetpool.name)
        response = self.connection.async_request(request, method='POST',
                                                 data=targetpool_data).object
        # Remove healthcheck object from healthchecks list
        index = None
        for i, hc in enumerate(targetpool.healthchecks):
            if hc.name == healthcheck.name:
                index = i
        if index is not None:
            targetpool.healthchecks.pop(index)
        return True

    def reboot_node(self, node):
        """
        Reboot a node.

        @param  node: Node to be rebooted
        @type   node: L{Node}

        @return:  True if successful, False if not
        @rtype:   C{bool}
        """
        request = '/zones/%s/instances/%s/reset' % (node.extra['zone'].name,
                                                    node.name)
        response = self.connection.async_request(request, method='POST',
                                                 data='ignored').object
        return True

    def ex_set_node_tags(self, node, tags):
        """
        Set the tags on a Node instance.

        Note that this updates the node object directly.

        @param  node: Node object
        @type   node: L{Node}

        @param  tags: List of tags to apply to the object
        @type   tags: C{list} of C{str}

        @return:  True if successful
        @rtype:   C{bool}
        """
        request = '/zones/%s/instances/%s/setTags' % (node.extra['zone'].name,
                                                      node.name)

        tags_data = {}
        tags_data['items'] = tags
        tags_data['fingerprint'] = node.extra['tags_fingerprint']

        response = self.connection.async_request(request, method='POST',
                                                 data=tags_data).object
        new_node = self.ex_get_node(node.name, node.extra['zone'])
        node.extra['tags'] = new_node.extra['tags']
        node.extra['tags_fingerprint'] = new_node.extra['tags_fingerprint']
        return True

    def deploy_node(self, name, size, image, script, location=None,
                    ex_network='default', ex_tags=None):
        """
        Create a new node and run a script on start-up.

        @param  name: The name of the node to create.
        @type   name: C{str}

        @param  size: The machine type to use.
        @type   size: C{str} or L{GCENodeSize}

        @param  image: The image to use to create the node.
        @type   image: C{str} or L{NodeImage}

        @param  script: File path to start-up script
        @type   script: C{str}

        @keyword  location: The location (zone) to create the node in.
        @type     location: C{str} or L{NodeLocation} or L{GCEZone} or C{None}

        @keyword  ex_network: The network to associate with the node.
        @type     ex_network: C{str} or L{GCENetwork}

        @keyword  ex_tags: A list of tags to assiciate with the node.
        @type     ex_tags: C{list} of C{str} or C{None}

        @return:  A Node object for the new node.
        @rtype:   L{Node}
        """
        with open(script, 'r') as f:
            script_data = f.read()
        metadata = {'items': [{'key': 'startup-script',
                               'value': script_data}]}

        return self.create_node(name, size, image, location=location,
                                ex_network=ex_network, ex_tags=ex_tags,
                                ex_metadata=metadata)

    def attach_volume(self, node, volume, device=None, ex_mode=None,
                      ex_boot=False):
        """
        Attach a volume to a node.

        If volume is None, a scratch disk will be created and attached.

        @param  node: The node to attach the volume to
        @type   node: L{Node}

        @param  volume: The volume to attach. If none, a scratch disk will be
                        attached.
        @type   volume: L{StorageVolume} or C{None}

        @keyword  device: The device name to attach the volume as. Defaults to
                          volume name.
        @type     device: C{str}

        @keyword  ex_mode: Either 'READ_WRITE' or 'READ_ONLY'
        @type     ex_mode: C{str}

        @keyword  ex_boot: If true, disk will be attached as a boot disk
        @type     ex_boot: C{bool}

        @return:  True if successful
        @rtype:   C{bool}
        """
        volume_data = {}
        if volume is None:
            volume_data['type'] = 'SCRATCH'
        else:
            volume_data['type'] = 'PERSISTENT'
            volume_data['source'] = volume.extra['selfLink']
        volume_data['kind'] = 'compute#attachedDisk'
        volume_data['mode'] = ex_mode or 'READ_WRITE'

        if device:
            volume_data['deviceName'] = device
        else:
            volume_data['deviceName'] = volume.name

        volume_data['boot'] = ex_boot

        request = '/zones/%s/instances/%s/attachDisk' % (
            node.extra['zone'].name, node.name)
        response = self.connection.async_request(request, method='POST',
                                                 data=volume_data).object
        return True

    def detach_volume(self, volume, ex_node=None):
        """
        Detach a volume from a node.

        @param  volume: Volume object to detach
        @type   volume: L{StorageVolume}

        @keyword  ex_node: Node object to detach volume from (required)
        @type     ex_node: L{Node}

        @return:  True if successful
        @rtype:   C{bool}
        """
        if not ex_node:
            return False
        request = '/zones/%s/instances/%s/detachDisk?deviceName=%s' % (
            ex_node.extra['zone'].name, ex_node.name, volume.name)

        response = self.connection.async_request(request, method='POST',
                                                 data='ignored').object
        return True

    def ex_destroy_address(self, address):
        """
        Destroy a static address.

        @param  address: Address object to destroy
        @type   address: L{GCEAddress}

        @return:  True if successful
        @rtype:   C{bool}
        """
        request = '/regions/%s/addresses/%s' % (address.region.name,
                                                address.name)

        response = self.connection.async_request(request,
                                                 method='DELETE').object
        return True

    def ex_destroy_healthcheck(self, healthcheck):
        """
        Destroy a healthcheck.

        @param  healthcheck: Health check object to destroy
        @type   healthcheck: L{GCEHealthCheck}

        @return:  True if successful
        @rtype:   C{bool}
        """
        request = '/global/httpHealthChecks/%s' % healthcheck.name
        response = self.connection.async_request(request,
                                                 method='DELETE').object
        return True

    def ex_destroy_firewall(self, firewall):
        """
        Destroy a firewall.

        @param  firewall: Firewall object to destroy
        @type   firewall: L{GCEFirewall}

        @return:  True if successful
        @rtype:   C{bool}
        """
        request = '/global/firewalls/%s' % firewall.name
        response = self.connection.async_request(request,
                                                 method='DELETE').object
        return True

    def ex_destroy_forwarding_rule(self, forwarding_rule):
        """
        Destroy a forwarding rule.

        @param  forwarding_rule: Forwarding Rule object to destroy
        @type   forwarding_rule: L{GCEForwardingRule}

        @return:  True if successful
        @rtype:   C{bool}
        """
        request = '/regions/%s/forwardingRules/%s' % (
            forwarding_rule.region.name, forwarding_rule.name)
        response = self.connection.async_request(request,
                                                 method='DELETE').object
        return True

    def ex_destroy_network(self, network):
        """
        Destroy a network.

        @param  network: Network object to destroy
        @type   network: L{GCENetwork}

        @return:  True if successful
        @rtype:   C{bool}
        """
        request = '/global/networks/%s' % network.name
        response = self.connection.async_request(request,
                                                 method='DELETE').object
        return True

    def destroy_node(self, node):
        """
        Destroy a node.

        @param  node: Node object to destroy
        @type   node: L{Node}

        @return:  True if successful
        @rtype:   C{bool}
        """
        request = '/zones/%s/instances/%s' % (node.extra['zone'].name,
                                              node.name)
        response = self.connection.async_request(request,
                                                 method='DELETE').object
        return True

    def ex_destroy_multiple_nodes(self, nodelist, ignore_errors=True,
                                  timeout=DEFAULT_TASK_COMPLETION_TIMEOUT):
        """
        Destroy multiple nodes at once.

        @param  nodelist: List of nodes to destroy
        @type   nodelist: C{list} of L{Node}

        @keyword  ignore_errors: If true, don't raise an exception if one or
                                 more nodes fails to be destroyed.
        @type     ignore_errors: C{bool}

        @keyword  timeout: Number of seconds to wait for all nodes to be
                           destroyed.
        @type     timeout: C{int}

        @return:  A list of boolean values.  One for each node.  True means
                  that the node was successfully destroyed.
        @rtype:   C{list} of C{bool}
        """
        responses = []
        success = [False] * len(nodelist)
        complete = False
        start_time = time.time()
        for node in nodelist:
            request = '/zones/%s/instances/%s' % (node.extra['zone'].name,
                                                  node.name)
            try:
                response = self.connection.request(request,
                                                   method='DELETE').object
            except:
                e = sys.exc_info()[1]
                response = None
                if not ignore_errors:
                    raise e
            responses.append(response)

        while not complete:
            if (time.time() - start_time >= timeout):
                raise Exception("Timeout (%s sec) while waiting to delete "
                                "multiple instances")
            complete = True
            for i, operation in enumerate(responses):
                if operation is None:
                    continue
                no_errors = True
                try:
                    response = self.connection.request(
                        operation['selfLink']).object
                except:
                    e = sys.exc_info()[1]
                    no_errors = False
                    if not ignore_errors:
                        raise e
                if response['status'] == 'DONE':
                    responses[i] = None
                    success[i] = no_errors
                else:
                    complete = False
                    time.sleep(2)
        return success

    def ex_destroy_targetpool(self, targetpool):
        """
        Destroy a target pool.

        @param  targetpool: TargetPool object to destroy
        @type   targetpool: L{GCETargetPool}

        @return:  True if successful
        @rtype:   C{bool}
        """
        request = '/regions/%s/targetPools/%s' % (targetpool.region.name,
                                                  targetpool.name)

        response = self.connection.async_request(request,
                                                 method='DELETE').object
        return True

    def destroy_volume(self, volume):
        """
        Destroy a volume.

        @param  volume: Volume object to destroy
        @type   volume: L{StorageVolume}

        @return:  True if successful
        @rtype:   C{bool}
        """
        request = '/zones/%s/disks/%s' % (volume.extra['zone'].name,
                                          volume.name)
        response = self.connection.async_request(request,
                                                 method='DELETE').object
        return True

    def ex_get_address(self, name, region=None):
        """
        Return an Address object based on an address name and optional region.

        @param  name: The name of the address
        @type   name: C{str}

        @keyword  region: The region to search for the address in
        @type     region: C{str} L{GCERegion} or C{None}

        @return:  An Address object for the address
        @rtype:   L{GCEAddress}
        """
        region = region or self.region or self._find_zone(name, 'addresses',
                                                          region=True)
        if not region:
            raise ResourceNotFoundError(
                'Address %s not found in any region.' % name, None, None)
        if not hasattr(region, 'name'):
            region = self.ex_get_region(region)
        request = '/regions/%s/addresses/%s' % (region.name, name)
        response = self.connection.request(request, method='GET').object
        return self._to_address(response)

    def ex_get_healthcheck(self, name):
        """
        Return a HealthCheck object based on the healthcheck name.

        @param  name: The name of the healthcheck
        @type   name: C{str}

        @return:  A GCEHealthCheck object
        @rtype:   L{GCEHealthCheck}
        """
        request = '/global/httpHealthChecks/%s' % name
        response = self.connection.request(request, method='GET').object
        return self._to_healthcheck(response)

    def ex_get_firewall(self, name):
        """
        Return a Firewall object based on the firewall name.

        @param  name: The name of the firewall
        @type   name: C{str}

        @return:  A GCEFirewall object
        @rtype:   L{GCEFirewall}
        """
        request = '/global/firewalls/%s' % name
        response = self.connection.request(request, method='GET').object
        return self._to_firewall(response)

    def ex_get_forwarding_rule(self, name, region=None):
        """
        Return a Forwarding Rule object based on the forwarding rule name.

        @param  name: The name of the forwarding rule
        @type   name: C{str}

        @keyword  region: The region to search for the rule in
        @type     region: C{str} or C{None}

        @return:  A GCEForwardingRule object
        @rtype:   L{GCEForwardingRule}
        """
        region = region or self.region or self._find_zone(name,
                                                          'forwardingRules',
                                                          region=True)
        if not region:
            raise ResourceNotFoundError(
                'Forwarding Rule %s not found in any region.' % name,
                None, None)
        if not hasattr(region, 'name'):
            region = self.ex_get_region(region)
        request = '/regions/%s/forwardingRules/%s' % (region.name, name)
        response = self.connection.request(request, method='GET').object
        return self._to_forwarding_rule(response)

    def ex_get_image(self, partial_name):
        """
        Return an NodeImage object based on the name or link provided.

        @param  partial_name: The name, partial name, or full path of a GCE
                              image.
        @type   partial_name: C{str}

        @return:  NodeImage object based on provided information or None if an
                  image with that name is not found.
        @rtype:   L{NodeImage} or C{None}
        """
        if partial_name.startswith('https://'):
            response = self.connection.request(partial_name, method='GET')
            return self._to_node_image(response.object)
        image = self._match_images(None, partial_name)
        if not image:
            if partial_name.startswith('debian'):
                image = self._match_images('debian-cloud', partial_name)
            elif partial_name.startswith('centos'):
                image = self._match_images('centos-cloud', partial_name)

        return image

    def ex_get_network(self, name):
        """
        Return a Network object based on a network name.

        @param  name: The name of the network
        @type   name: C{str}

        @return:  A Network object for the network
        @rtype:   L{GCENetwork}
        """
        request = '/global/networks/%s' % name
        response = self.connection.request(request, method='GET').object
        return self._to_network(response)

    def ex_get_node(self, name, zone=None):
        """
        Return a Node object based on a node name and optional zone.

        @param  name: The name of the node
        @type   name: C{str}

        @keyword  zone: The zone to search for the node in.  If set to 'all',
                        search all zones for the instance.
        @type     zone: C{str} or L{GCEZone} or L{NodeLocation} or C{None}

        @return:  A Node object for the node
        @rtype:   L{Node}
        """
        zone = zone or self.zone or self._find_zone(name, 'instances')
        if zone == 'all':
            zone = self._find_zone(name, 'instances')
        if not zone:
            raise ResourceNotFoundError('Node %s not found in any zone'
                                        % name, None, None)
        if not hasattr(zone, 'name'):
            zone = self.ex_get_zone(zone)
        request = '/zones/%s/instances/%s' % (zone.name, name)
        response = self.connection.request(request, method='GET').object
        return self._to_node(response)

    def ex_get_project(self):
        """
        Return a Project object with project-wide information.

        @return:  A GCEProject object
        @rtype:   L{GCEProject}
        """
        response = self.connection.request('', method='GET').object
        return self._to_project(response)

    def ex_get_size(self, name, zone=None):
        """
        Return a size object based on a machine type name and zone.

        @param  name: The name of the node
        @type   name: C{str}

        @keyword  zone: The zone to search for the machine type in
        @type     zone: C{str} or L{GCEZone} or L{NodeLocation} or C{None}

        @return:  A GCENodeSize object for the machine type
        @rtype:   L{GCENodeSize}
        """
        zone = zone or self.zone
        if not hasattr(zone, 'name'):
            zone = self.ex_get_zone(zone)
        request = '/zones/%s/machineTypes/%s' % (zone.name, name)
        response = self.connection.request(request, method='GET').object
        return self._to_node_size(response)

    def ex_get_volume(self, name, zone=None):
        """
        Return a Volume object based on a volume name and optional zone.

        @param  name: The name of the volume
        @type   name: C{str}

        @keyword  zone: The zone to search for the volume in
        @type     zone: C{str} or L{GCEZone} or L{NodeLocation} or C{None}

        @return:  A StorageVolume object for the volume
        @rtype:   L{StorageVolume}
        """
        zone = zone or self.zone or self._find_zone(name, 'disks')
        if not zone:
            raise ResourceNotFoundError('Volume %s not found in any zone'
                                        % name, None, None)
        if not hasattr(zone, 'name'):
            zone = self.ex_get_zone(zone)
        request = '/zones/%s/disks/%s' % (zone.name, name)
        response = self.connection.request(request, method='GET').object
        return self._to_storage_volume(response)

    def ex_get_region(self, name):
        """
        Return a Region object based on the region name.

        @param  name: The name of the region.
        @type   name: C{str}

        @return:  A GCERegion object for the region
        @rtype:   L{GCERegion}
        """
        if name.startswith('https://'):
            short_name = name.split('/')[-1]
            request = name
        else:
            short_name = name
            request = '/regions/%s' % name
        # Check region cache first
        if short_name in self.region_dict:
            return self.region_dict[short_name]
        # Otherwise, look up region information
        response = self.connection.request(request, method='GET').object
        return self._to_region(response)

    def ex_get_targetpool(self, name, region=None):
        """
        Return a TargetPool object based on a name and optional region.

        @param  name: The name of the target pool
        @type   name: C{str}

        @keyword  region: The region to search for the target pool in
        @type     region: C{str} or L{GCERegion} or C{None}

        @return:  A TargetPool object for the pool
        @rtype:   L{GCETargetPool}
        """
        region = region or self.region or self._find_zone(name, 'targetPools',
                                                          region=True)
        if not region:
            raise ResourceNotFoundError(
                'Targetpool %s not found in any region.' % name, None, None)
        if not hasattr(region, 'name'):
            region = self.ex_get_region(region)
        request = '/regions/%s/targetPools/%s' % (region.name, name)
        response = self.connection.request(request, method='GET').object
        return self._to_targetpool(response)

    def ex_get_zone(self, name):
        """
        Return a Zone object based on the zone name.

        @param  name: The name of the zone.
        @type   name: C{str}

        @return:  A GCEZone object for the zone or None if not found
        @rtype:   L{GCEZone} or C{None}
        """
        if name.startswith('https://'):
            short_name = name.split('/')[-1]
            request = name
        else:
            short_name = name
            request = '/zones/%s' % name
        # Check zone cache first
        if short_name in self.zone_dict:
            return self.zone_dict[short_name]
        # Otherwise, look up zone information
        try:
            response = self.connection.request(request, method='GET').object
        except ResourceNotFoundError:
            return None
        return self._to_zone(response)

    def _to_address(self, address):
        """
        Return an Address object from the json-response dictionary.

        @param  address: The dictionary describing the address.
        @type   address: C{dict}

        @return: Address object
        @rtype: L{GCEAddress}
        """
        extra = {}

        region = self.ex_get_region(address['region'])

        extra['selfLink'] = address['selfLink']
        extra['status'] = address['status']
        extra['creationTimestamp'] = address['creationTimestamp']

        return GCEAddress(id=address['id'], name=address['name'],
                          address=address['address'],
                          region=region, driver=self, extra=extra)

    def _to_healthcheck(self, healthcheck):
        """
        Return a HealthCheck object from the json-response dictionary.

        @param  healthcheck: The dictionary describing the healthcheck.
        @type   healthcheck: C{dict}

        @return: HealthCheck object
        @rtype: L{GCEHealthCheck}
        """
        extra = {}
        extra['selfLink'] = healthcheck['selfLink']
        extra['creationTimestamp'] = healthcheck['creationTimestamp']
        extra['description'] = healthcheck.get('description')
        extra['host'] = healthcheck.get('host')

        return GCEHealthCheck(
            id=healthcheck['id'], name=healthcheck['name'],
            path=healthcheck['requestPath'], port=healthcheck['port'],
            interval=healthcheck['checkIntervalSec'],
            timeout=healthcheck['timeoutSec'],
            unhealthy_threshold=healthcheck['unhealthyThreshold'],
            healthy_threshold=healthcheck['healthyThreshold'],
            driver=self, extra=extra)

    def _to_firewall(self, firewall):
        """
        Return a Firewall object from the json-response dictionary.

        @param  firewall: The dictionary describing the firewall.
        @type   firewall: C{dict}

        @return: Firewall object
        @rtype: L{GCEFirewall}
        """
        extra = {}
        extra['selfLink'] = firewall['selfLink']
        extra['creationTimestamp'] = firewall['creationTimestamp']
        extra['description'] = firewall.get('description')
        extra['network_name'] = firewall['network'].split('/')[-1]

        network = self.ex_get_network(extra['network_name'])
        source_ranges = firewall.get('sourceRanges')
        source_tags = firewall.get('sourceTags')

        return GCEFirewall(id=firewall['id'], name=firewall['name'],
                           allowed=firewall['allowed'], network=network,
                           source_ranges=source_ranges,
                           source_tags=source_tags,
                           driver=self, extra=extra)

    def _to_forwarding_rule(self, forwarding_rule):
        """
        Return a Forwarding Rule object from the json-response dictionary.

        @param  forwarding_rule: The dictionary describing the rule.
        @type   forwarding_rule: C{dict}

        @return: ForwardingRule object
        @rtype: L{GCEForwardingRule}
        """
        extra = {}
        # Use .get to work around a current API bug.
        extra['selfLink'] = forwarding_rule.get('selfLink')
        extra['portRange'] = forwarding_rule['portRange']
        extra['creationTimestamp'] = forwarding_rule['creationTimestamp']
        extra['description'] = forwarding_rule.get('description')

        region = self.ex_get_region(forwarding_rule['region'])
        targetpool = self.ex_get_targetpool(
            forwarding_rule['target'].split('/')[-1])

        return GCEForwardingRule(id=forwarding_rule['id'],
                                 name=forwarding_rule['name'], region=region,
                                 address=forwarding_rule['IPAddress'],
                                 protocol=forwarding_rule['IPProtocol'],
                                 targetpool=targetpool,
                                 driver=self, extra=extra)

    def _to_network(self, network):
        """
        Return a Network object from the json-response dictionary.

        @param  network: The dictionary describing the network.
        @type   network: C{dict}

        @return: Network object
        @rtype: L{GCENetwork}
        """
        extra = {}

        extra['selfLink'] = network['selfLink']
        extra['gatewayIPv4'] = network['gatewayIPv4']
        extra['description'] = network.get('description')
        extra['creationTimestamp'] = network['creationTimestamp']

        return GCENetwork(id=network['id'], name=network['name'],
                          cidr=network['IPv4Range'],
                          driver=self, extra=extra)

    def _to_node_image(self, image):
        """
        Return an Image object from the json-response dictionary.

        @param  image: The dictionary describing the image.
        @type   image: C{dict}

        @return: Image object
        @rtype: L{NodeImage}
        """
        extra = {}
        extra['preferredKernel'] = image['preferredKernel']
        extra['description'] = image['description']
        extra['creationTimestamp'] = image['creationTimestamp']
        extra['selfLink'] = image['selfLink']
        return NodeImage(id=image['id'], name=image['name'], driver=self,
                         extra=extra)

    def _to_node_location(self, location):
        """
        Return a Location object from the json-response dictionary.

        @param  location: The dictionary describing the location.
        @type   location: C{dict}

        @return: Location object
        @rtype: L{NodeLocation}
        """
        return NodeLocation(id=location['id'], name=location['name'],
                            country=location['name'].split('-')[0],
                            driver=self)

    def _to_node(self, node):
        """
        Return a Node object from the json-response dictionary.

        @param  node: The dictionary describing the node.
        @type   node: C{dict}

        @return: Node object
        @rtype: L{Node}
        """
        public_ips = []
        private_ips = []
        extra = {}

        extra['status'] = node['status']
        extra['description'] = node.get('description')
        extra['zone'] = self.ex_get_zone(node['zone'])
        extra['image'] = node.get('image')
        extra['machineType'] = node['machineType']
        extra['disks'] = node['disks']
        extra['networkInterfaces'] = node['networkInterfaces']
        extra['id'] = node['id']
        extra['selfLink'] = node['selfLink']
        extra['name'] = node['name']
        extra['metadata'] = node['metadata']
        extra['tags_fingerprint'] = node['tags']['fingerprint']

        if 'items' in node['tags']:
            tags = node['tags']['items']
        else:
            tags = []
        extra['tags'] = tags

        for network_interface in node['networkInterfaces']:
            private_ips.append(network_interface['networkIP'])
            for access_config in network_interface['accessConfigs']:
                public_ips.append(access_config['natIP'])

        # For the node attributes, use just machine and image names, not full
        # paths.  Full paths are available in the "extra" dict.
        if extra['image']:
            image = extra['image'].split('/')[-1]
        else:
            image = None
        size = node['machineType'].split('/')[-1]

        return Node(id=node['id'], name=node['name'],
                    state=self.NODE_STATE_MAP[node['status']],
                    public_ips=public_ips, private_ips=private_ips,
                    driver=self, size=size, image=image, extra=extra)

    def _to_node_size(self, machine_type):
        """
        Return a Size object from the json-response dictionary.

        @param  machine_type: The dictionary describing the machine.
        @type   machine_type: C{dict}

        @return: Size object
        @rtype: L{GCENodeSize}
        """
        extra = {}
        extra['selfLink'] = machine_type['selfLink']
        extra['zone'] = self.ex_get_zone(machine_type['zone'])
        extra['description'] = machine_type['description']
        extra['guestCpus'] = machine_type['guestCpus']
        extra['creationTimestamp'] = machine_type['creationTimestamp']
        try:
            price = self._get_size_price(size_id=machine_type['name'])
        except KeyError:
            price = None

        return GCENodeSize(id=machine_type['id'], name=machine_type['name'],
                           ram=machine_type['memoryMb'],
                           disk=machine_type['imageSpaceGb'],
                           bandwidth=0, price=price, driver=self, extra=extra)

    def _to_project(self, project):
        """
        Return a Project object from the json-response dictionary.

        @param  project: The dictionary describing the project.
        @type   project: C{dict}

        @return: Project object
        @rtype: L{GCEProject}
        """
        extra = {}
        extra['selfLink'] = project['selfLink']
        extra['creationTimestamp'] = project['creationTimestamp']
        extra['description'] = project['description']
        metadata = project['commonInstanceMetadata'].get('items')

        return GCEProject(id=project['id'], name=project['name'],
                          metadata=metadata, quotas=project['quotas'],
                          driver=self, extra=extra)

    def _to_region(self, region):
        """
        Return a Region object from the json-response dictionary.

        @param  region: The dictionary describing the region.
        @type   region: C{dict}

        @return: Region object
        @rtype: L{GCERegion}
        """
        extra = {}
        extra['selfLink'] = region['selfLink']
        extra['creationTimestamp'] = region['creationTimestamp']
        extra['description'] = region['description']

        quotas = region.get('quotas')
        zones = [self.ex_get_zone(z) for z in region['zones']]
        # Work around a bug that will occasionally list missing zones in the
        # region output
        zones = [z for z in zones if z is not None]
        deprecated = region.get('deprecated')

        return GCERegion(id=region['id'], name=region['name'],
                         status=region['status'], zones=zones,
                         quotas=quotas, deprecated=deprecated,
                         driver=self, extra=extra)

    def _to_storage_volume(self, volume):
        """
        Return a Volume object from the json-response dictionary.

        @param  volume: The dictionary describing the volume.
        @type   volume: C{dict}

        @return: Volume object
        @rtype: L{StorageVolume}
        """
        extra = {}
        extra['selfLink'] = volume['selfLink']
        extra['zone'] = self.ex_get_zone(volume['zone'])
        extra['status'] = volume['status']
        extra['creationTimestamp'] = volume['creationTimestamp']
        extra['description'] = volume.get('description')

        return StorageVolume(id=volume['id'], name=volume['name'],
                             size=volume['sizeGb'], driver=self, extra=extra)

    def _to_targetpool(self, targetpool):
        """
        Return a Target Pool object from the json-response dictionary.

        @param  targetpool: The dictionary describing the volume.
        @type   targetpool: C{dict}

        @return: Target Pool object
        @rtype:  L{GCETargetPool}
        """
        extra = {}
        extra['selfLink'] = targetpool['selfLink']
        extra['description'] = targetpool.get('description')
        region = self.ex_get_region(targetpool['region'])
        healthcheck_list = [self.ex_get_healthcheck(h.split('/')[-1]) for h
                            in targetpool.get('healthChecks', [])]
        node_list = []
        for n in targetpool.get('instances', []):
            node_path = n.split('/')
            name = node_path[-1]
            zone = node_path[-3]
            # Nodes that do not exist can be part of a target pool.  If the
            # node does not exist, use the URL of the node instead of the node
            # object.
            try:
                node = self.ex_get_node(name, zone)
            except ResourceNotFoundError:
                node = n
            node_list.append(node)

        return GCETargetPool(id=targetpool['id'], name=targetpool['name'],
                             region=region, healthchecks=healthcheck_list,
                             nodes=node_list, driver=self, extra=extra)

    def _to_zone(self, zone):
        """
        Return a Zone object from the json-response dictionary.

        @param  zone: The dictionary describing the zone.
        @type   zone: C{dict}

        @return: Zone object
        @rtype: L{GCEZone}
        """
        extra = {}
        extra['selfLink'] = zone['selfLink']
        extra['creationTimestamp'] = zone['creationTimestamp']
        extra['description'] = zone['description']

        deprecated = zone.get('deprecated')

        return GCEZone(id=zone['id'], name=zone['name'], status=zone['status'],
                       maintenance_windows=zone.get('maintenanceWindows'),
                       quotas=zone['quotas'], deprecated=deprecated,
                       driver=self, extra=extra)
