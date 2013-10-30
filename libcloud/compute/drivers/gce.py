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

from libcloud.common.google import GoogleResponse
from libcloud.common.google import GoogleBaseConnection
from libcloud.common.google import ResourceNotFoundError

from libcloud.compute.base import Node, NodeDriver, NodeImage, NodeLocation
from libcloud.compute.base import NodeSize, StorageVolume, UuidMixin
from libcloud.compute.providers import Provider
from libcloud.compute.types import NodeState

API_VERSION = 'v1beta15'
DEFAULT_TASK_COMPLETION_TIMEOUT = 180


def timestamp_to_datetime(timestamp):
    """
    Return a datetime object that corresponds to the time in an RFC3339
    timestamp.

    :param  timestamp: RFC3339 timestamp string
    :type   timestamp: ``str``

    :return:  Datetime object corresponding to timestamp
    :rtype:   :class:`datetime.datetime`
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

        :return: True if successful
        :rtype:  ``bool``
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

        :return:  True if successful
        :rtype:   ``bool``
        """
        return self.driver.ex_destroy_healthcheck(healthcheck=self)

    def update(self):
        """
        Commit updated healthcheck values.

        :return:  Updated Healthcheck object
        :rtype:   :class:`GCEHealthcheck`
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

        :return: True if successful
        :rtype:  ``bool``
        """
        return self.driver.ex_destroy_firewall(firewall=self)

    def update(self):
        """
        Commit updated firewall values.

        :return:  Updated Firewall object
        :rtype:   :class:`GCEFirewall`
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

        :return:  True if successful
        :rtype:   ``bool``
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

        :return: True if successful
        :rtype:  ``bool``
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

        :param  node: Node to add
        :type   node: ``str`` or :class:`Node`

        :return:  True if successful
        :rtype:   ``bool``
        """
        return self.driver.ex_targetpool_add_node(targetpool=self, node=node)

    def remove_node(self, node):
        """
        Remove a node from this target pool.

        :param  node: Node to remove
        :type   node: ``str`` or :class:`Node`

        :return:  True if successful
        :rtype:   ``bool``
        """
        return self.driver.ex_targetpool_remove_node(targetpool=self,
                                                     node=node)

    def add_healthcheck(self, healthcheck):
        """
        Add a healthcheck to this target pool.

        :param  healthcheck: Healthcheck to add
        :type   healthcheck: ``str`` or :class:`GCEHealthCheck`

        :return:  True if successful
        :rtype:   ``bool``
        """
        return self.driver.ex_targetpool_add_healthcheck(
            targetpool=self, healthcheck=healthcheck)

    def remove_healthcheck(self, healthcheck):
        """
        Remove a healthcheck from this target pool.

        :param  healthcheck: Healthcheck to remove
        :type   healthcheck: ``str`` or :class:`GCEHealthCheck`

        :return:  True if successful
        :rtype:   ``bool``
        """
        return self.driver.ex_targetpool_remove_healthcheck(
            targetpool=self, healthcheck=healthcheck)

    def destroy(self):
        """
        Destroy this Target Pool

        :return:  True if successful
        :rtype:   ``bool``
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

        :return:  A dictionary containing maintenance window info
                  The dictionary contains 4 keys with values of type ``str``
                      - name: The name of the maintence window
                      - description: Description of the maintenance window
                      - beginTime: RFC3339 Timestamp
                      - endTime: RFC3339 Timestamp
        :rtype:   ``dict``
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

        :return:  Time until next maintenance window
        :rtype:   :class:`datetime.timedelta`
        """
        next_window = self._get_next_maint()
        now = self._now()
        next_begin = timestamp_to_datetime(next_window['beginTime'])
        return next_begin - now

    def _get_next_mw_duration(self):
        """
        Returns the duration of the next maintenance window.

        :return:  Duration of next maintenance window
        :rtype:   :class:`datetime.timedelta`
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
    GCE Node Driver class.

    This is the primary driver for interacting with Google Compute Engine.  It
    contains all of the standard libcloud methods, plus additional ex_* methods
    for more features.

    Note that many methods allow either objects or strings (or lists of
    objects/strings).  In most cases, passing strings instead of objects will
    result in additional GCE API calls.
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
        :param  user_id: The email address (for service accounts) or Client ID
                         (for installed apps) to be used for authentication.
        :type   user_id: ``str``

        :param  key: The RSA Key (for service accounts) or file path containing
                     key or Client Secret (for installed apps) to be used for
                     authentication.
        :type   key: ``str``

        :keyword  datacenter: The name of the datacenter (zone) used for
                              operations.
        :type     datacenter: ``str``

        :keyword  project: Your GCE project name. (required)
        :type     project: ``str``

        :keyword  auth_type: Accepted values are "SA" or "IA"
                             ("Service Account" or "Installed Application").
                             If not supplied, auth_type will be guessed based
                             on value of user_id.
        :type     auth_type: ``str``
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

    def _catch_error(self, ignore_errors=False):
        """
        Catch an exception and raise it unless asked to ignore it.

        :keyword  ignore_errors: If true, just return the error.  Otherwise,
                                 raise the error.
        :type     ignore_errors: ``bool``

        :return:  The exception that was raised.
        :rtype:   :class:`Exception`
        """
        e = sys.exc_info()[1]
        if ignore_errors:
            return e
        else:
            raise e

    def _get_components_from_path(self, path):
        """
        Return a dictionary containing name & zone/region from a request path.

        :param  path: HTTP request path (e.g.
                      '/project/pjt-name/zones/us-central1-a/instances/mynode')
        :type   path: ``str``

        :return:  Dictionary containing name and zone/region of resource
        :rtype    ``dict``
        """
        region = None
        zone = None
        glob = False
        components = path.split('/')
        name = components[-1]
        if components[-4] == 'regions':
            region = components[-3]
        elif components[-4] == 'zones':
            zone = components[-3]
        elif components[-3] == 'global':
            glob = True

        return {'name': name, 'region': region, 'zone': zone, 'global': glob}

    def _get_region_from_zone(self, zone):
        """
        Return the Region object that contains the given Zone object.

        :param  zone: Zone object
        :type   zone: :class:`GCEZone`

        :return:  Region object that contains the zone
        :rtype:   :class:`GCERegion`
        """
        for region in self.region_list:
            zones = [z.name for z in region.zones]
            if zone.name in zones:
                return region

    def _find_zone_or_region(self, name, res_type, region=False,
                             res_name=None):
        """
        Find the zone or region for a named resource.

        :param  name: Name of resource to find
        :type   name: ``str``

        :param  res_type: Type of resource to find.
                          Examples include: 'disks', 'instances' or 'addresses'
        :type   res_type: ``str``

        :keyword  region: If True, search regions instead of zones
        :type     region: ``bool``

        :keyword  res_name: The name of the resource type for error messages.
                            Examples: 'Volume', 'Node', 'Address'
        :keyword  res_name: ``str``

        :return:  Zone/Region object for the zone/region for the resource.
        :rtype:   :class:`GCEZone` or :class:`GCERegion`
        """
        if region:
            rz = 'region'
        else:
            rz = 'zone'
        rz_name = None
        res_name = res_name or res_type
        request = '/aggregated/%s' % (res_type)
        res_list = self.connection.request(request).object
        for k, v in res_list['items'].items():
            for res in v.get(res_type, []):
                if res['name'] == name:
                    rz_name = k.replace('%ss/' % (rz), '')
                    break
        if not rz_name:
            raise ResourceNotFoundError(
                '%s \'%s\' not found in any %s.' % (res_name, name, rz),
                None, None)
        else:
            getrz = getattr(self, 'ex_get_%s' % (rz))
            return getrz(rz_name)

    def _match_images(self, project, partial_name):
        """
        Find the latest image, given a partial name.

        For example, providing 'debian-7' will return the image object for the
        most recent image with a name that starts with 'debian-7' in the
        supplied project.  If no project is given, it will search your own
        project.

        :param  project:  The name of the project to search for images.
                          Examples include: 'debian-cloud' and 'centos-cloud'.
        :type   project:  ``str`` or ``None``

        :param  partial_name: The full name or beginning of a name for an
                              image.
        :type   partial_name: ``str``

        :return:  The latest image object that maches the partial name or None
                  if no matching image is found.
        :rtype:   :class:`NodeImage` or ``None``
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

    def _set_region(self, region):
        """
        Return the region to use for listing resources.

        :param  region: A name, region object, None, or 'all'
        :type   region: ``str`` or :class:`GCERegion` or ``None``

        :return:  A region object or None if all regions should be considered
        :rtype:   :class:`GCERegion` or ``None``
        """
        region = region or self.region

        if region == 'all' or region is None:
            return None

        if not hasattr(region, 'name'):
            region = self.ex_get_region(region)
        return region

    def _set_zone(self, zone):
        """
        Return the zone to use for listing resources.

        :param  zone: A name, zone object, None, or 'all'
        :type   region: ``str`` or :class:`GCEZone` or ``None``

        :return:  A zone object or None if all zones should be considered
        :rtype:   :class:`GCEZone` or ``None``
        """
        zone = zone or self.zone

        if zone == 'all' or zone is None:
            return None

        if not hasattr(zone, 'name'):
            zone = self.ex_get_zone(zone)
        return zone

    def ex_list_addresses(self, region=None):
        """
        Return a list of static addreses for a region or all.

        :keyword  region: The region to return addresses from. For example:
                          'us-central1'.  If None, will return addresses from
                          region of self.zone.  If 'all', will return all
                          addresses.
        :type     region: ``str`` or ``None``

        :return: A list of static address objects.
        :rtype: ``list`` of :class:`GCEAddress`
        """
        list_addresses = []
        region = self._set_region(region)
        if region is None:
            request = '/aggregated/addresses'
        else:
            request = '/regions/%s/addresses' % (region.name)
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

        :return: A list of health check objects.
        :rtype: ``list`` of :class:`GCEHealthCheck`
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

        :return: A list of firewall objects.
        :rtype: ``list`` of :class:`GCEFirewall`
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

        :keyword  region: The region to return forwarding rules from.  For
                          example: 'us-central1'.  If None, will return
                          forwarding rules from the region of self.region
                          (which is based on self.zone).  If 'all', will
                          return all forwarding rules.
        :type     region: ``str`` or :class:`GCERegion` or ``None``

        :return: A list of forwarding rule objects.
        :rtype: ``list`` of :class:`GCEForwardingRule`
        """
        list_forwarding_rules = []
        region = self._set_region(region)
        if region is None:
            request = '/aggregated/forwardingRules'
        else:
            request = '/regions/%s/forwardingRules' % (region.name)
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

        :keyword  ex_project: Optional alternate project name.
        :type     ex_project: ``str`` or ``None``

        :return:  List of NodeImage objects
        :rtype:   ``list`` of :class:`NodeImage`
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

        The :class:`ex_list_zones` method returns more comprehensive results,
        but this is here for compatibility.

        :return: List of NodeLocation objects
        :rtype: ``list`` of :class:`NodeLocation`
        """
        list_locations = []
        request = '/zones'
        response = self.connection.request(request, method='GET').object
        list_locations = [self._to_node_location(l) for l in response['items']]
        return list_locations

    def ex_list_networks(self):
        """
        Return the list of networks.

        :return: A list of network objects.
        :rtype: ``list`` of :class:`GCENetwork`
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

        :keyword  ex_zone:  Optional zone name or 'all'
        :type     ex_zone:  ``str`` or :class:`GCEZone` or
                            :class:`NodeLocation` or ``None``

        :return:  List of Node objects
        :rtype:   ``list`` of :class:`Node`
        """
        list_nodes = []
        zone = self._set_zone(ex_zone)
        if zone is None:
            request = '/aggregated/instances'
        else:
            request = '/zones/%s/instances' % (zone.name)

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

        :return: A list of region objects.
        :rtype: ``list`` of :class:`GCERegion`
        """
        list_regions = []
        request = '/regions'
        response = self.connection.request(request, method='GET').object
        list_regions = [self._to_region(r) for r in response['items']]
        return list_regions

    def list_sizes(self, location=None):
        """
        Return a list of sizes (machineTypes) in a zone.

        :keyword  location: Location or Zone for sizes
        :type     location: ``str`` or :class:`GCEZone` or
                            :class:`NodeLocation` or ``None``

        :return:  List of GCENodeSize objects
        :rtype:   ``list`` of :class:`GCENodeSize`
        """
        list_sizes = []
        zone = self._set_zone(location)
        if zone is None:
            request = '/aggregated/machineTypes'
        else:
            request = '/zones/%s/machineTypes' % (zone.name)

        response = self.connection.request(request, method='GET').object

        if 'items' in response:
            # The aggregated response returns a dict for each zone
            if zone is None:
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

        :return:  A list of target pool objects
        :rtype:   ``list`` of :class:`GCETargetPool`
        """
        list_targetpools = []
        region = self._set_region(region)
        if region is None:
            request = '/aggregated/targetPools'
        else:
            request = '/regions/%s/targetPools' % (region.name)
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

        :keyword  ex_zone: The zone to return volumes from.
        :type     ex_zone: ``str`` or :class:`GCEZone` or
                            :class:`NodeLocation` or ``None``

        :return: A list of volume objects.
        :rtype: ``list`` of :class:`StorageVolume`
        """
        list_volumes = []
        zone = self._set_zone(ex_zone)
        if zone is None:
            request = '/aggregated/disks'
        else:
            request = '/zones/%s/disks' % (zone.name)

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

        :return: A list of zone objects.
        :rtype: ``list`` of :class:`GCEZone`
        """
        list_zones = []
        request = '/zones'
        response = self.connection.request(request, method='GET').object
        list_zones = [self._to_zone(z) for z in response['items']]
        return list_zones

    def ex_create_address(self, name, region=None):
        """
        Create a static address in a region.

        :param  name: Name of static address
        :type   name: ``str``

        :keyword  region: Name of region for the address (e.g. 'us-central1')
        :type     region: ``str`` or :class:`GCERegion`

        :return:  Static Address object
        :rtype:   :class:`GCEAddress`
        """
        region = region or self.region
        if not hasattr(region, 'name'):
            region = self.ex_get_region(region)
        elif region is None:
            raise ValueError('REGION_NOT_SPECIFIED',
                             'Region must be provided for an address')
        address_data = {'name': name}
        request = '/regions/%s/addresses' % (region.name)
        self.connection.async_request(request, method='POST',
                                      data=address_data)
        return self.ex_get_address(name, region=region)

    def ex_create_healthcheck(self, name, host=None, path=None, port=None,
                              interval=None, timeout=None,
                              unhealthy_threshold=None,
                              healthy_threshold=None):
        """
        Create an Http Health Check.

        :param  name: Name of health check
        :type   name: ``str``

        :keyword  host: Hostname of health check requst.  Defaults to empty and
                        public IP is used instead.
        :type     host: ``str``

        :keyword  path: The request path for the check.  Defaults to /.
        :type     path: ``str``

        :keyword  port: The TCP port number for the check.  Defaults to 80.
        :type     port: ``int``

        :keyword  interval: How often (in seconds) to check.  Defaults to 5.
        :type     interval: ``int``

        :keyword  timeout: How long to wait before failing. Defaults to 5.
        :type     timeout: ``int``

        :keyword  unhealthy_threshold: How many failures before marking
                                       unhealthy.  Defaults to 2.
        :type     unhealthy_threshold: ``int``

        :keyword  healthy_threshold: How many successes before marking as
                                     healthy.  Defaults to 2.
        :type     healthy_threshold: ``int``

        :return:  Health Check object
        :rtype:   :class:`GCEHealthCheck`
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

        self.connection.async_request(request, method='POST', data=hc_data)
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

        :param  name: Name of the firewall to be created
        :type   name: ``str``

        :param  allowed: List of dictionaries with rules
        :type   allowed: ``list`` of ``dict``

        :keyword  network: The network that the firewall applies to.
        :type     network: ``str`` or :class:`GCENetwork`

        :keyword  source_ranges: A list of IP ranges in CIDR format that the
                                 firewall should apply to. Defaults to
                                 ['0.0.0.0/0']
        :type     source_ranges: ``list`` of ``str``

        :keyword  source_tags: A list of instance tags which the rules apply
        :type     source_tags: ``list`` of ``str``

        :return:  Firewall object
        :rtype:   :class:`GCEFirewall`
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

        self.connection.async_request(request, method='POST',
                                      data=firewall_data)
        return self.ex_get_firewall(name)

    def ex_create_forwarding_rule(self, name, targetpool, region=None,
                                  protocol='tcp', port_range=None,
                                  address=None):
        """
        Create a forwarding rule.

        :param  name: Name of forwarding rule to be created
        :type   name: ``str``

        :param  targetpool: Target pool to apply the rule to
        :param  targetpool: ``str`` or :class:`GCETargetPool`

        :keyword  region: Region to create the forwarding rule in.  Defaults to
                          self.region
        :type     region: ``str`` or :class:`GCERegion`

        :keyword  protocol: Should be 'tcp' or 'udp'
        :type     protocol: ``str``

        :keyword  port_range: Optional single port number or range separated
                              by a dash.  Examples: '80', '5000-5999'.
        :type     port_range: ``str``

        :keyword  address: Optional static address for forwarding rule. Must be
                           in same region.
        :type     address: ``str`` or :class:`GCEAddress`

        :return:  Forwarding Rule object
        :rtype:   :class:`GCEForwardingRule`
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

        request = '/regions/%s/forwardingRules' % (region.name)

        self.connection.async_request(request, method='POST',
                                      data=forwarding_rule_data)

        return self.ex_get_forwarding_rule(name)

    def ex_create_network(self, name, cidr):
        """
        Create a network.

        :param  name: Name of network to be created
        :type   name: ``str``

        :param  cidr: Address range of network in CIDR format.
        :type  cidr: ``str``

        :return:  Network object
        :rtype:   :class:`GCENetwork`
        """
        network_data = {}
        network_data['name'] = name
        network_data['IPv4Range'] = cidr

        request = '/global/networks'

        self.connection.async_request(request, method='POST',
                                      data=network_data)

        return self.ex_get_network(name)

    def _create_node_req(self, name, size, image, location, network,
                         tags=None, metadata=None, boot_disk=None,
                         persistent_disk=False):
        """
        Returns a request and body to create a new node.  This is a helper
        method to suppor both :class:`create_node` and
        :class:`ex_create_multiple_nodes`.

        :param  name: The name of the node to create.
        :type   name: ``str``

        :param  size: The machine type to use.
        :type   size: :class:`GCENodeSize`

        :param  image: The image to use to create the node (or, if using a
                       persistent disk, the image the disk was created from).
        :type   image: :class:`NodeImage`

        :param  location: The location (zone) to create the node in.
        :type   location: :class:`NodeLocation` or :class:`GCEZone`

        :param  network: The network to associate with the node.
        :type   network: :class:`GCENetwork`

        :keyword  tags: A list of tags to assiciate with the node.
        :type     tags: ``list`` of ``str``

        :keyword  metadata: Metadata dictionary for instance.
        :type     metadata: ``dict``

        :keyword  boot_disk:  Persistent boot disk to attach.
        :type     :class:`StorageVolume`

        :keyword  persistent_disk: If True, create a persistent disk instead of
                                   an ephemeral one.  Has no effect if
                                   boot_disk is specified.
        :type     persistent_disk: ``bool``

        :return:  A tuple containing a request string and a node_data dict.
        :rtype:   ``tuple`` of ``str`` and ``dict``
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

        request = '/zones/%s/instances' % (location.name)

        return request, node_data

    def create_node(self, name, size, image, location=None,
                    ex_network='default', ex_tags=None, ex_metadata=None,
                    ex_boot_disk=None, ex_persistent_disk=False):
        """
        Create a new node and return a node object for the node.

        :param  name: The name of the node to create.
        :type   name: ``str``

        :param  size: The machine type to use.
        :type   size: ``str`` or :class:`GCENodeSize`

        :param  image: The image to use to create the node (or, if attaching
                       a persistent disk, the image used to create the disk)
        :type   image: ``str`` or :class:`NodeImage`

        :keyword  location: The location (zone) to create the node in.
        :type     location: ``str`` or :class:`NodeLocation` or
                            :class:`GCEZone` or ``None``

        :keyword  ex_network: The network to associate with the node.
        :type     ex_network: ``str`` or :class:`GCENetwork`

        :keyword  ex_tags: A list of tags to assiciate with the node.
        :type     ex_tags: ``list`` of ``str`` or ``None``

        :keyword  ex_metadata: Metadata dictionary for instance.
        :type     ex_metadata: ``dict`` or ``None``

        :keyword  ex_boot_disk: The boot disk to attach to the instance.
        :type     ex_boot_disk: :class:`StorageVolume` or ``str``

        :keyword  ex_persistent_disk: If True, create a persistent_disk instead
                                      of a ephemeral one.  Has no effect if
                                      ex_boot_disk is specified.
        :type     ex_persistent_disk: ``bool``

        :return:  A Node object for the new node.
        :rtype:   :class:`Node`
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
        self.connection.async_request(request, method='POST', data=node_data)

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

        :param  base_name: The base name of the nodes to create.
        :type   base_name: ``str``

        :param  size: The machine type to use.
        :type   size: ``str`` or :class:`GCENodeSize`

        :param  image: The image to use to create the nodes.
        :type   image: ``str`` or :class:`NodeImage`

        :param  number: The number of nodes to create.
        :type   number: ``int``

        :keyword  location: The location (zone) to create the nodes in.
        :type     location: ``str`` or :class:`NodeLocation` or
                            :class:`GCEZone` or ``None``

        :keyword  ex_network: The network to associate with the nodes.
        :type     ex_network: ``str`` or :class:`GCENetwork`

        :keyword  ex_tags: A list of tags to assiciate with the nodes.
        :type     ex_tags: ``list`` of ``str`` or ``None``

        :keyword  ex_metadata: Metadata dictionary for instances.
        :type     ex_metadata: ``dict`` or ``None``

        :keyword  ignore_errors: If True, don't raise Exceptions if one or
                                 more nodes fails.
        :type     ignore_errors: ``bool``

        :keyword  persistent_disk: If True, create persistent boot disks
                                   instead of ephemeral ones.
        :type     persistent_disk: ``bool``

        :keyword  timeout: The number of seconds to wait for all nodes to be
                           created before timing out.

        :return:  A list of Node objects for the new nodes.
        :rtype:   ``list`` of :class:`Node`
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
                    e = self._catch_error(ignore_errors=ignore_errors)
                    error = e.value
                    code = e.code
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

        :param  name: Name of target pool
        :type   name: ``str``

        :keyword  region: Region to create the target pool in. Defaults to
                          self.region
        :type     region: ``str`` or :class:`GCERegion` or ``None``

        :keyword  healthchecks: Optional list of health checks to attach
        :type     healthchecks: ``list`` of ``str`` or :class:`GCEHealthCheck`

        :keyword  nodes:  Optional list of nodes to attach to the pool
        :type     nodes:  ``list`` of ``str`` or :class:`Node`

        :return:  Target Pool object
        :rtype:   :class:`GCETargetPool`
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

        request = '/regions/%s/targetPools' % (region.name)

        self.connection.async_request(request, method='POST',
                                      data=targetpool_data)

        return self.ex_get_targetpool(name, region)

    def create_volume(self, size, name, location=None, image=None,
                      snapshot=None):
        """
        Create a volume (disk).

        :param  size: Size of volume to create (in GB). Can be None if image
                      or snapshot is supplied.
        :type   size: ``int`` or ``str`` or ``None``

        :param  name: Name of volume to create
        :type   name: ``str``

        :keyword  location: Location (zone) to create the volume in
        :type     location: ``str`` or :class:`GCEZone` or
                            :class:`NodeLocation` or ``None``

        :keyword  image: Image to create disk from.
        :type     image: :class:`NodeImage` or ``str`` or ``None``

        :keyword  snapshot: Snapshot to create image from (needs full URI)
        :type     snapshot: ``str``

        :return:  Storage Volume object
        :rtype:   :class:`StorageVolume`
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
            volume_data['description'] = 'Image: %s' % (
                image.extra['selfLink'])
        if snapshot:
            volume_data['sourceSnapshot'] = snapshot
            volume_data['description'] = 'Snapshot: %s' % (snapshot)
        location = location or self.zone
        if not hasattr(location, 'name'):
            location = self.ex_get_zone(location)
        request = '/zones/%s/disks' % (location.name)
        self.connection.async_request(request, method='POST',
                                      data=volume_data,
                                      params=params)

        return self.ex_get_volume(name, location)

    def ex_update_healthcheck(self, healthcheck):
        """
        Update a health check with new values.

        To update, change the attributes of the health check object and pass
        the updated object to the method.

        :param  healthcheck: A healthcheck object with updated values.
        :type   healthcheck: :class:`GCEHealthCheck`

        :return:  An object representing the new state of the health check.
        :rtype:   :class:`GCEHealthCheck`
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

        request = '/global/httpHealthChecks/%s' % (healthcheck.name)

        self.connection.async_request(request, method='PUT',
                                      data=hc_data)

        return self.ex_get_healthcheck(healthcheck.name)

    def ex_update_firewall(self, firewall):
        """
        Update a firewall with new values.

        To update, change the attributes of the firewall object and pass the
        updated object to the method.

        :param  firewall: A firewall object with updated values.
        :type   firewall: :class:`GCEFirewall`

        :return:  An object representing the new state of the firewall.
        :rtype:   :class:`GCEFirewall`
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

        request = '/global/firewalls/%s' % (firewall.name)

        self.connection.async_request(request, method='PUT',
                                      data=firewall_data)

        return self.ex_get_firewall(firewall.name)

    def ex_targetpool_add_node(self, targetpool, node):
        """
        Add a node to a target pool.

        :param  targetpool: The targetpool to add node to
        :type   targetpool: ``str`` or :class:`GCETargetPool`

        :param  node: The node to add
        :type   node: ``str`` or :class:`Node`

        :returns: True if successful
        :rtype:   ``bool``
        """
        if not hasattr(targetpool, 'name'):
            targetpool = self.ex_get_targetpool(targetpool)
        if not hasattr(node, 'name'):
            node = self.ex_get_node(node, 'all')

        targetpool_data = {'instance': node.extra['selfLink']}

        request = '/regions/%s/targetPools/%s/addInstance' % (
            targetpool.region.name, targetpool.name)
        self.connection.async_request(request, method='POST',
                                      data=targetpool_data)
        targetpool.nodes.append(node)
        return True

    def ex_targetpool_add_healthcheck(self, targetpool, healthcheck):
        """
        Add a health check to a target pool.

        :param  targetpool: The targetpool to add health check to
        :type   targetpool: ``str`` or :class:`GCETargetPool`

        :param  healthcheck: The healthcheck to add
        :type   healthcheck: ``str`` or :class:`GCEHealthCheck`

        :returns: True if successful
        :rtype:   ``bool``
        """
        if not hasattr(targetpool, 'name'):
            targetpool = self.ex_get_targetpool(targetpool)
        if not hasattr(healthcheck, 'name'):
            healthcheck = self.ex_get_healthcheck(healthcheck)

        targetpool_data = {'healthCheck': healthcheck.extra['selfLink']}

        request = '/regions/%s/targetPools/%s/addHealthCheck' % (
            targetpool.region.name, targetpool.name)
        self.connection.async_request(request, method='POST',
                                      data=targetpool_data)
        targetpool.healthchecks.append(healthcheck)
        return True

    def ex_targetpool_remove_node(self, targetpool, node):
        """
        Remove a node from a target pool.

        :param  targetpool: The targetpool to remove node from
        :type   targetpool: ``str`` or :class:`GCETargetPool`

        :param  node: The node to remove
        :type   node: ``str`` or :class:`Node`

        :returns: True if successful
        :rtype:   ``bool``
        """
        if not hasattr(targetpool, 'name'):
            targetpool = self.ex_get_targetpool(targetpool)
        if not hasattr(node, 'name'):
            node = self.ex_get_node(node, 'all')

        targetpool_data = {'instance': node.extra['selfLink']}

        request = '/regions/%s/targetPools/%s/removeInstance' % (
            targetpool.region.name, targetpool.name)
        self.connection.async_request(request, method='POST',
                                      data=targetpool_data)
        # Remove node object from node list
        index = None
        for i, nd in enumerate(targetpool.nodes):
            if nd.name == node.name:
                index = i
                break
        if index is not None:
            targetpool.nodes.pop(index)
        return True

    def ex_targetpool_remove_healthcheck(self, targetpool, healthcheck):
        """
        Remove a health check from a target pool.

        :param  targetpool: The targetpool to remove health check from
        :type   targetpool: ``str`` or :class:`GCETargetPool`

        :param  healthcheck: The healthcheck to remove
        :type   healthcheck: ``str`` or :class:`GCEHealthCheck`

        :returns: True if successful
        :rtype:   ``bool``
        """
        if not hasattr(targetpool, 'name'):
            targetpool = self.ex_get_targetpool(targetpool)
        if not hasattr(healthcheck, 'name'):
            healthcheck = self.ex_get_healthcheck(healthcheck)

        targetpool_data = {'healthCheck': healthcheck.extra['selfLink']}

        request = '/regions/%s/targetPools/%s/removeHealthCheck' % (
            targetpool.region.name, targetpool.name)
        self.connection.async_request(request, method='POST',
                                      data=targetpool_data)
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

        :param  node: Node to be rebooted
        :type   node: :class:`Node`

        :return:  True if successful, False if not
        :rtype:   ``bool``
        """
        request = '/zones/%s/instances/%s/reset' % (node.extra['zone'].name,
                                                    node.name)
        self.connection.async_request(request, method='POST',
                                      data='ignored')
        return True

    def ex_set_node_tags(self, node, tags):
        """
        Set the tags on a Node instance.

        Note that this updates the node object directly.

        :param  node: Node object
        :type   node: :class:`Node`

        :param  tags: List of tags to apply to the object
        :type   tags: ``list`` of ``str``

        :return:  True if successful
        :rtype:   ``bool``
        """
        request = '/zones/%s/instances/%s/setTags' % (node.extra['zone'].name,
                                                      node.name)

        tags_data = {}
        tags_data['items'] = tags
        tags_data['fingerprint'] = node.extra['tags_fingerprint']

        self.connection.async_request(request, method='POST',
                                      data=tags_data)
        new_node = self.ex_get_node(node.name, node.extra['zone'])
        node.extra['tags'] = new_node.extra['tags']
        node.extra['tags_fingerprint'] = new_node.extra['tags_fingerprint']
        return True

    def deploy_node(self, name, size, image, script, location=None,
                    ex_network='default', ex_tags=None):
        """
        Create a new node and run a script on start-up.

        :param  name: The name of the node to create.
        :type   name: ``str``

        :param  size: The machine type to use.
        :type   size: ``str`` or :class:`GCENodeSize`

        :param  image: The image to use to create the node.
        :type   image: ``str`` or :class:`NodeImage`

        :param  script: File path to start-up script
        :type   script: ``str``

        :keyword  location: The location (zone) to create the node in.
        :type     location: ``str`` or :class:`NodeLocation` or
                            :class:`GCEZone` or ``None``

        :keyword  ex_network: The network to associate with the node.
        :type     ex_network: ``str`` or :class:`GCENetwork`

        :keyword  ex_tags: A list of tags to assiciate with the node.
        :type     ex_tags: ``list`` of ``str`` or ``None``

        :return:  A Node object for the new node.
        :rtype:   :class:`Node`
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

        :param  node: The node to attach the volume to
        :type   node: :class:`Node`

        :param  volume: The volume to attach. If none, a scratch disk will be
                        attached.
        :type   volume: :class:`StorageVolume` or ``None``

        :keyword  device: The device name to attach the volume as. Defaults to
                          volume name.
        :type     device: ``str``

        :keyword  ex_mode: Either 'READ_WRITE' or 'READ_ONLY'
        :type     ex_mode: ``str``

        :keyword  ex_boot: If true, disk will be attached as a boot disk
        :type     ex_boot: ``bool``

        :return:  True if successful
        :rtype:   ``bool``
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
        self.connection.async_request(request, method='POST',
                                      data=volume_data)
        return True

    def detach_volume(self, volume, ex_node=None):
        """
        Detach a volume from a node.

        :param  volume: Volume object to detach
        :type   volume: :class:`StorageVolume`

        :keyword  ex_node: Node object to detach volume from (required)
        :type     ex_node: :class:`Node`

        :return:  True if successful
        :rtype:   ``bool``
        """
        if not ex_node:
            return False
        request = '/zones/%s/instances/%s/detachDisk?deviceName=%s' % (
            ex_node.extra['zone'].name, ex_node.name, volume.name)

        self.connection.async_request(request, method='POST',
                                      data='ignored')
        return True

    def ex_destroy_address(self, address):
        """
        Destroy a static address.

        :param  address: Address object to destroy
        :type   address: :class:`GCEAddress`

        :return:  True if successful
        :rtype:   ``bool``
        """
        request = '/regions/%s/addresses/%s' % (address.region.name,
                                                address.name)

        self.connection.async_request(request, method='DELETE')
        return True

    def ex_destroy_healthcheck(self, healthcheck):
        """
        Destroy a healthcheck.

        :param  healthcheck: Health check object to destroy
        :type   healthcheck: :class:`GCEHealthCheck`

        :return:  True if successful
        :rtype:   ``bool``
        """
        request = '/global/httpHealthChecks/%s' % (healthcheck.name)
        self.connection.async_request(request, method='DELETE')
        return True

    def ex_destroy_firewall(self, firewall):
        """
        Destroy a firewall.

        :param  firewall: Firewall object to destroy
        :type   firewall: :class:`GCEFirewall`

        :return:  True if successful
        :rtype:   ``bool``
        """
        request = '/global/firewalls/%s' % (firewall.name)
        self.connection.async_request(request, method='DELETE')
        return True

    def ex_destroy_forwarding_rule(self, forwarding_rule):
        """
        Destroy a forwarding rule.

        :param  forwarding_rule: Forwarding Rule object to destroy
        :type   forwarding_rule: :class:`GCEForwardingRule`

        :return:  True if successful
        :rtype:   ``bool``
        """
        request = '/regions/%s/forwardingRules/%s' % (
            forwarding_rule.region.name, forwarding_rule.name)
        self.connection.async_request(request, method='DELETE')
        return True

    def ex_destroy_network(self, network):
        """
        Destroy a network.

        :param  network: Network object to destroy
        :type   network: :class:`GCENetwork`

        :return:  True if successful
        :rtype:   ``bool``
        """
        request = '/global/networks/%s' % (network.name)
        self.connection.async_request(request, method='DELETE')
        return True

    def destroy_node(self, node):
        """
        Destroy a node.

        :param  node: Node object to destroy
        :type   node: :class:`Node`

        :return:  True if successful
        :rtype:   ``bool``
        """
        request = '/zones/%s/instances/%s' % (node.extra['zone'].name,
                                              node.name)
        self.connection.async_request(request, method='DELETE')
        return True

    def ex_destroy_multiple_nodes(self, nodelist, ignore_errors=True,
                                  timeout=DEFAULT_TASK_COMPLETION_TIMEOUT):
        """
        Destroy multiple nodes at once.

        :param  nodelist: List of nodes to destroy
        :type   nodelist: ``list`` of :class:`Node`

        :keyword  ignore_errors: If true, don't raise an exception if one or
                                 more nodes fails to be destroyed.
        :type     ignore_errors: ``bool``

        :keyword  timeout: Number of seconds to wait for all nodes to be
                           destroyed.
        :type     timeout: ``int``

        :return:  A list of boolean values.  One for each node.  True means
                  that the node was successfully destroyed.
        :rtype:   ``list`` of ``bool``
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
                self._catch_error(ignore_errors=ignore_errors)
                response = None
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
                    self._catch_error(ignore_errors=ignore_errors)
                    no_errors = False
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

        :param  targetpool: TargetPool object to destroy
        :type   targetpool: :class:`GCETargetPool`

        :return:  True if successful
        :rtype:   ``bool``
        """
        request = '/regions/%s/targetPools/%s' % (targetpool.region.name,
                                                  targetpool.name)

        self.connection.async_request(request, method='DELETE')
        return True

    def destroy_volume(self, volume):
        """
        Destroy a volume.

        :param  volume: Volume object to destroy
        :type   volume: :class:`StorageVolume`

        :return:  True if successful
        :rtype:   ``bool``
        """
        request = '/zones/%s/disks/%s' % (volume.extra['zone'].name,
                                          volume.name)
        self.connection.async_request(request,
                                      method='DELETE')
        return True

    def ex_get_address(self, name, region=None):
        """
        Return an Address object based on an address name and optional region.

        :param  name: The name of the address
        :type   name: ``str``

        :keyword  region: The region to search for the address in (set to
                          'all' to search all regions)
        :type     region: ``str`` :class:`GCERegion` or ``None``

        :return:  An Address object for the address
        :rtype:   :class:`GCEAddress`
        """
        region = self._set_region(region) or self._find_zone_or_region(
            name, 'addresses', region=True, res_name='Address')
        request = '/regions/%s/addresses/%s' % (region.name, name)
        response = self.connection.request(request, method='GET').object
        return self._to_address(response)

    def ex_get_healthcheck(self, name):
        """
        Return a HealthCheck object based on the healthcheck name.

        :param  name: The name of the healthcheck
        :type   name: ``str``

        :return:  A GCEHealthCheck object
        :rtype:   :class:`GCEHealthCheck`
        """
        request = '/global/httpHealthChecks/%s' % (name)
        response = self.connection.request(request, method='GET').object
        return self._to_healthcheck(response)

    def ex_get_firewall(self, name):
        """
        Return a Firewall object based on the firewall name.

        :param  name: The name of the firewall
        :type   name: ``str``

        :return:  A GCEFirewall object
        :rtype:   :class:`GCEFirewall`
        """
        request = '/global/firewalls/%s' % (name)
        response = self.connection.request(request, method='GET').object
        return self._to_firewall(response)

    def ex_get_forwarding_rule(self, name, region=None):
        """
        Return a Forwarding Rule object based on the forwarding rule name.

        :param  name: The name of the forwarding rule
        :type   name: ``str``

        :keyword  region: The region to search for the rule in (set to 'all'
                          to search all regions).
        :type     region: ``str`` or ``None``

        :return:  A GCEForwardingRule object
        :rtype:   :class:`GCEForwardingRule`
        """
        region = self._set_region(region) or self._find_zone_or_region(
            name, 'forwardingRules', region=True, res_name='ForwardingRule')
        request = '/regions/%s/forwardingRules/%s' % (region.name, name)
        response = self.connection.request(request, method='GET').object
        return self._to_forwarding_rule(response)

    def ex_get_image(self, partial_name):
        """
        Return an NodeImage object based on the name or link provided.

        :param  partial_name: The name, partial name, or full path of a GCE
                              image.
        :type   partial_name: ``str``

        :return:  NodeImage object based on provided information or None if an
                  image with that name is not found.
        :rtype:   :class:`NodeImage` or ``None``
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

        :param  name: The name of the network
        :type   name: ``str``

        :return:  A Network object for the network
        :rtype:   :class:`GCENetwork`
        """
        request = '/global/networks/%s' % (name)
        response = self.connection.request(request, method='GET').object
        return self._to_network(response)

    def ex_get_node(self, name, zone=None):
        """
        Return a Node object based on a node name and optional zone.

        :param  name: The name of the node
        :type   name: ``str``

        :keyword  zone: The zone to search for the node in.  If set to 'all',
                        search all zones for the instance.
        :type     zone: ``str`` or :class:`GCEZone` or
                        :class:`NodeLocation` or ``None``

        :return:  A Node object for the node
        :rtype:   :class:`Node`
        """
        zone = self._set_zone(zone) or self._find_zone_or_region(
            name, 'instances', res_name='Node')
        request = '/zones/%s/instances/%s' % (zone.name, name)
        response = self.connection.request(request, method='GET').object
        return self._to_node(response)

    def ex_get_project(self):
        """
        Return a Project object with project-wide information.

        :return:  A GCEProject object
        :rtype:   :class:`GCEProject`
        """
        response = self.connection.request('', method='GET').object
        return self._to_project(response)

    def ex_get_size(self, name, zone=None):
        """
        Return a size object based on a machine type name and zone.

        :param  name: The name of the node
        :type   name: ``str``

        :keyword  zone: The zone to search for the machine type in
        :type     zone: ``str`` or :class:`GCEZone` or
                        :class:`NodeLocation` or ``None``

        :return:  A GCENodeSize object for the machine type
        :rtype:   :class:`GCENodeSize`
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

        :param  name: The name of the volume
        :type   name: ``str``

        :keyword  zone: The zone to search for the volume in (set to 'all' to
                        search all zones)
        :type     zone: ``str`` or :class:`GCEZone` or :class:`NodeLocation`
                        or ``None``

        :return:  A StorageVolume object for the volume
        :rtype:   :class:`StorageVolume`
        """
        zone = self._set_zone(zone) or self._find_zone_or_region(
            name, 'disks', res_name='Volume')
        request = '/zones/%s/disks/%s' % (zone.name, name)
        response = self.connection.request(request, method='GET').object
        return self._to_storage_volume(response)

    def ex_get_region(self, name):
        """
        Return a Region object based on the region name.

        :param  name: The name of the region.
        :type   name: ``str``

        :return:  A GCERegion object for the region
        :rtype:   :class:`GCERegion`
        """
        if name.startswith('https://'):
            short_name = self._get_components_from_path(name)['name']
            request = name
        else:
            short_name = name
            request = '/regions/%s' % (name)
        # Check region cache first
        if short_name in self.region_dict:
            return self.region_dict[short_name]
        # Otherwise, look up region information
        response = self.connection.request(request, method='GET').object
        return self._to_region(response)

    def ex_get_targetpool(self, name, region=None):
        """
        Return a TargetPool object based on a name and optional region.

        :param  name: The name of the target pool
        :type   name: ``str``

        :keyword  region: The region to search for the target pool in (set to
                          'all' to search all regions).
        :type     region: ``str`` or :class:`GCERegion` or ``None``

        :return:  A TargetPool object for the pool
        :rtype:   :class:`GCETargetPool`
        """
        region = self._set_region(region) or self._find_zone_or_region(
            name, 'targetPools', region=True, res_name='TargetPool')
        request = '/regions/%s/targetPools/%s' % (region.name, name)
        response = self.connection.request(request, method='GET').object
        return self._to_targetpool(response)

    def ex_get_zone(self, name):
        """
        Return a Zone object based on the zone name.

        :param  name: The name of the zone.
        :type   name: ``str``

        :return:  A GCEZone object for the zone or None if not found
        :rtype:   :class:`GCEZone` or ``None``
        """
        if name.startswith('https://'):
            short_name = self._get_components_from_path(name)['name']
            request = name
        else:
            short_name = name
            request = '/zones/%s' % (name)
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

        :param  address: The dictionary describing the address.
        :type   address: ``dict``

        :return: Address object
        :rtype: :class:`GCEAddress`
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

        :param  healthcheck: The dictionary describing the healthcheck.
        :type   healthcheck: ``dict``

        :return: HealthCheck object
        :rtype: :class:`GCEHealthCheck`
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

        :param  firewall: The dictionary describing the firewall.
        :type   firewall: ``dict``

        :return: Firewall object
        :rtype: :class:`GCEFirewall`
        """
        extra = {}
        extra['selfLink'] = firewall['selfLink']
        extra['creationTimestamp'] = firewall['creationTimestamp']
        extra['description'] = firewall.get('description')
        extra['network_name'] = self._get_components_from_path(
            firewall['network'])['name']

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

        :param  forwarding_rule: The dictionary describing the rule.
        :type   forwarding_rule: ``dict``

        :return: ForwardingRule object
        :rtype: :class:`GCEForwardingRule`
        """
        extra = {}
        # Use .get to work around a current API bug.
        extra['selfLink'] = forwarding_rule.get('selfLink')
        extra['portRange'] = forwarding_rule['portRange']
        extra['creationTimestamp'] = forwarding_rule['creationTimestamp']
        extra['description'] = forwarding_rule.get('description')

        region = self.ex_get_region(forwarding_rule['region'])
        targetpool = self.ex_get_targetpool(
            self._get_components_from_path(forwarding_rule['target'])['name'])

        return GCEForwardingRule(id=forwarding_rule['id'],
                                 name=forwarding_rule['name'], region=region,
                                 address=forwarding_rule['IPAddress'],
                                 protocol=forwarding_rule['IPProtocol'],
                                 targetpool=targetpool,
                                 driver=self, extra=extra)

    def _to_network(self, network):
        """
        Return a Network object from the json-response dictionary.

        :param  network: The dictionary describing the network.
        :type   network: ``dict``

        :return: Network object
        :rtype: :class:`GCENetwork`
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

        :param  image: The dictionary describing the image.
        :type   image: ``dict``

        :return: Image object
        :rtype: :class:`NodeImage`
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

        :param  location: The dictionary describing the location.
        :type   location: ``dict``

        :return: Location object
        :rtype: :class:`NodeLocation`
        """
        return NodeLocation(id=location['id'], name=location['name'],
                            country=location['name'].split('-')[0],
                            driver=self)

    def _to_node(self, node):
        """
        Return a Node object from the json-response dictionary.

        :param  node: The dictionary describing the node.
        :type   node: ``dict``

        :return: Node object
        :rtype: :class:`Node`
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
            image = self._get_components_from_path(extra['image'])['name']
        else:
            image = None
        size = self._get_components_from_path(node['machineType'])['name']

        return Node(id=node['id'], name=node['name'],
                    state=self.NODE_STATE_MAP[node['status']],
                    public_ips=public_ips, private_ips=private_ips,
                    driver=self, size=size, image=image, extra=extra)

    def _to_node_size(self, machine_type):
        """
        Return a Size object from the json-response dictionary.

        :param  machine_type: The dictionary describing the machine.
        :type   machine_type: ``dict``

        :return: Size object
        :rtype: :class:`GCENodeSize`
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

        :param  project: The dictionary describing the project.
        :type   project: ``dict``

        :return: Project object
        :rtype: :class:`GCEProject`
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

        :param  region: The dictionary describing the region.
        :type   region: ``dict``

        :return: Region object
        :rtype: :class:`GCERegion`
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

        :param  volume: The dictionary describing the volume.
        :type   volume: ``dict``

        :return: Volume object
        :rtype: :class:`StorageVolume`
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

        :param  targetpool: The dictionary describing the volume.
        :type   targetpool: ``dict``

        :return: Target Pool object
        :rtype:  :class:`GCETargetPool`
        """
        extra = {}
        extra['selfLink'] = targetpool['selfLink']
        extra['description'] = targetpool.get('description')
        region = self.ex_get_region(targetpool['region'])
        healthcheck_list = [self.ex_get_healthcheck(h.split('/')[-1]) for h
                            in targetpool.get('healthChecks', [])]
        node_list = []
        for n in targetpool.get('instances', []):
            # Nodes that do not exist can be part of a target pool.  If the
            # node does not exist, use the URL of the node instead of the node
            # object.
            comp = self._get_components_from_path(n)
            try:
                node = self.ex_get_node(comp['name'], comp['zone'])
            except ResourceNotFoundError:
                node = n
            node_list.append(node)

        return GCETargetPool(id=targetpool['id'], name=targetpool['name'],
                             region=region, healthchecks=healthcheck_list,
                             nodes=node_list, driver=self, extra=extra)

    def _to_zone(self, zone):
        """
        Return a Zone object from the json-response dictionary.

        :param  zone: The dictionary describing the zone.
        :type   zone: ``dict``

        :return: Zone object
        :rtype: :class:`GCEZone`
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
