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
from libcloud.common.google import GoogleBaseError
from libcloud.common.google import ResourceNotFoundError
from libcloud.common.google import ResourceExistsError
from libcloud.common.types import ProviderError

from libcloud.compute.base import Node, NodeDriver, NodeImage, NodeLocation
from libcloud.compute.base import NodeSize, StorageVolume, VolumeSnapshot
from libcloud.compute.base import UuidMixin
from libcloud.compute.providers import Provider
from libcloud.compute.types import NodeState
from libcloud.utils.iso8601 import parse_date

API_VERSION = 'v1'
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
    """
    Connection class for the GCE driver.

    GCEConnection extends :class:`google.GoogleBaseConnection` for 2 reasons:
      1. modify request_path for GCE URI.
      2. Implement gce_params functionality described below.

    If the parameter gce_params is set to a dict prior to calling request(),
    the URL parameters will be updated to include those key/values FOR A
    SINGLE REQUEST. If the response contains a nextPageToken,
    gce_params['pageToken'] will be set to its value. This can be used to
    implement paging in list:

    >>> params, more_results = {'maxResults': 2}, True
    >>> while more_results:
    ...     driver.connection.gce_params=params
    ...     driver.ex_list_urlmaps()
    ...     more_results = 'pageToken' in params
    ...
    [<GCEUrlMap id="..." name="cli-map">, <GCEUrlMap id="..." name="lc-map">]
    [<GCEUrlMap id="..." name="web-map">]
    """
    host = 'www.googleapis.com'
    responseCls = GCEResponse

    def __init__(self, user_id, key, secure, auth_type=None,
                 credential_file=None, project=None, **kwargs):
        super(GCEConnection, self).__init__(user_id, key, secure=secure,
                                            auth_type=auth_type,
                                            credential_file=credential_file,
                                            **kwargs)
        self.request_path = '/compute/%s/projects/%s' % (API_VERSION,
                                                         project)
        self.gce_params = None

    def pre_connect_hook(self, params, headers):
        """
        Update URL parameters with values from self.gce_params.

        @inherits: :class:`GoogleBaseConnection.pre_connect_hook`
        """
        params, headers = super(GCEConnection, self).pre_connect_hook(params,
                                                                      headers)
        if self.gce_params:
            params.update(self.gce_params)
        return params, headers

    def request(self, *args, **kwargs):
        """
        Perform request then do GCE-specific processing of URL params.

        @inherits: :class:`GoogleBaseConnection.request`
        """
        response = super(GCEConnection, self).request(*args, **kwargs)

        # If gce_params has been set, then update the pageToken with the
        # nextPageToken so it can be used in the next request.
        if self.gce_params:
            if 'nextPageToken' in response.object:
                self.gce_params['pageToken'] = response.object['nextPageToken']
            elif 'pageToken' in self.gce_params:
                del self.gce_params['pageToken']
            self.gce_params = None

        return response


class GCEList(object):
    """
    An Iterator that wraps list functions to provide additional features.

    GCE enforces a limit on the number of objects returned by a list operation,
    so users with more than 500 objects of a particular type will need to use
    filter(), page() or both.

    >>> l=GCEList(driver, driver.ex_list_urlmaps)
    >>> for sublist in l.filter('name eq ...-map').page(1):
    ...   sublist
    ...
    [<GCEUrlMap id="..." name="cli-map">]
    [<GCEUrlMap id="..." name="web-map">]

    One can create a GCEList manually, but it's slightly easier to use the
    ex_list() method of :class:`GCENodeDriver`.
    """

    def __init__(self, driver, list_fn, **kwargs):
        """
        :param  driver: An initialized :class:``GCENodeDriver``
        :type   driver: :class:``GCENodeDriver``

        :param  list_fn: A bound list method from :class:`GCENodeDriver`.
        :type   list_fn: ``instancemethod``
        """
        self.driver = driver
        self.list_fn = list_fn
        self.kwargs = kwargs
        self.params = {}

    def __iter__(self):
        list_fn = self.list_fn
        more_results = True
        while more_results:
            self.driver.connection.gce_params = self.params
            yield list_fn(**self.kwargs)
            more_results = 'pageToken' in self.params

    def __repr__(self):
        return '<GCEList list="%s" params="%s">' % (
            self.list_fn.__name__, repr(self.params))

    def filter(self, expression):
        """
        Filter results of a list operation.

        GCE supports server-side filtering of resources returned by a list
        operation. Syntax of the filter expression is fully descripted in the
        GCE API reference doc, but in brief it is::

            FIELD_NAME COMPARISON_STRING LITERAL_STRING

        where FIELD_NAME is the resource's property name, COMPARISON_STRING is
        'eq' or 'ne', and LITERAL_STRING is a regular expression in RE2 syntax.

        >>> for sublist in l.filter('name eq ...-map'):
        ...   sublist
        ...
        [<GCEUrlMap id="..." name="cli-map">, \
                <GCEUrlMap id="..." name="web-map">]

        API reference: https://cloud.google.com/compute/docs/reference/latest/
        RE2 syntax: https://github.com/google/re2/blob/master/doc/syntax.txt

        :param  expression: Filter expression described above.
        :type   expression: ``str``

        :return: This :class:`GCEList` instance
        :rtype:  :class:`GCEList`
        """
        self.params['filter'] = expression
        return self

    def page(self, max_results=500):
        """
        Limit the number of results by each iteration.

        This implements the paging functionality of the GCE list methods and
        returns this GCEList instance so that results can be chained:

        >>> for sublist in GCEList(driver, driver.ex_list_urlmaps).page(2):
        ...   sublist
        ...
        [<GCEUrlMap id="..." name="cli-map">, \
                <GCEUrlMap id="..." name="lc-map">]
        [<GCEUrlMap id="..." name="web-map">]

        :keyword  max_results: Maximum number of results to return per
                               iteration. Defaults to the GCE default of 500.
        :type     max_results: ``int``

        :return: This :class:`GCEList` instance
        :rtype:  :class:`GCEList`
        """
        self.params['maxResults'] = max_results
        return self


class GCELicense(UuidMixin):
    """A GCE License used to track software usage in GCE nodes."""
    def __init__(self, id, name, driver, charges_use_fee, extra=None):
        self.id = str(id)
        self.name = name
        self.driver = driver
        self.charges_use_fee = charges_use_fee
        self.extra = extra or {}
        UuidMixin.__init__(self)

    def destroy(self):
        raise ProviderError("Can not destroy a License resource.")

    def __repr__(self):
        return '<GCELicense id="%s" name="%s" charges_use_fee="%s">' % (
            self.id, self.name, self.charges_use_fee)


class GCEDiskType(UuidMixin):
    """A GCE DiskType resource."""
    def __init__(self, id, name, zone, driver, extra=None):
        self.id = str(id)
        self.name = name
        self.zone = zone
        self.driver = driver
        self.extra = extra
        UuidMixin.__init__(self)

    def destroy(self):
        raise ProviderError("Can not destroy a DiskType resource.")

    def __repr__(self):
        return '<GCEDiskType id="%s" name="%s" zone="%s">' % (
            self.id, self.name, self.zone)


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

    def destroy(self):
        """
        Destroy this address.

        :return: True if successful
        :rtype:  ``bool``
        """
        return self.driver.ex_destroy_address(address=self)

    def __repr__(self):
        return '<GCEAddress id="%s" name="%s" address="%s" region="%s">' % (
            self.id, self.name, self.address,
            (hasattr(self.region, "name") and self.region.name or self.region))


class GCEBackendService(UuidMixin):
    """A GCE Backend Service."""

    def __init__(self, id, name, backends, healthchecks, port, port_name,
                 protocol, timeout, driver, extra=None):
        self.id = str(id)
        self.name = name
        self.backends = backends or []
        self.healthchecks = healthchecks or []
        self.port = port
        self.port_name = port_name
        self.protocol = protocol
        self.timeout = timeout
        self.driver = driver
        self.extra = extra or {}
        UuidMixin.__init__(self)

    def __repr__(self):
        return '<GCEBackendService id="%s" name="%s">' % (
            self.id, self.name)

    def destroy(self):
        """
        Destroy this Backend Service.

        :return: True if successful
        :rtype:  ``bool``
        """
        return self.driver.ex_destroy_backendservice(backendservice=self)


class GCEFailedDisk(object):
    """Dummy Node object for disks that are not created."""
    def __init__(self, name, error, code):
        self.name = name
        self.error = error
        self.code = code

    def __repr__(self):
        return '<GCEFailedDisk name="%s" error_code="%s">' % (
            self.name, self.code)


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
        self.extra = extra or {}
        UuidMixin.__init__(self)

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

    def __repr__(self):
        return '<GCEHealthCheck id="%s" name="%s" path="%s" port="%s">' % (
            self.id, self.name, self.path, self.port)


class GCEFirewall(UuidMixin):
    """A GCE Firewall rule class."""
    def __init__(self, id, name, allowed, network, source_ranges, source_tags,
                 target_tags, driver, extra=None):
        self.id = str(id)
        self.name = name
        self.network = network
        self.allowed = allowed
        self.source_ranges = source_ranges
        self.source_tags = source_tags
        self.target_tags = target_tags
        self.driver = driver
        self.extra = extra
        UuidMixin.__init__(self)

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

    def __repr__(self):
        return '<GCEFirewall id="%s" name="%s" network="%s">' % (
            self.id, self.name, self.network.name)


class GCEForwardingRule(UuidMixin):
    def __init__(self, id, name, region, address, protocol, targetpool, driver,
                 extra=None):
        self.id = str(id)
        self.name = name
        self.region = region
        self.address = address
        self.protocol = protocol
        # TODO: 'targetpool' should more correctly be 'target' since a
        # forwarding rule's target can be something besides a targetpool
        self.targetpool = targetpool
        self.driver = driver
        self.extra = extra
        UuidMixin.__init__(self)

    def destroy(self):
        """
        Destroy this Forwarding Rule

        :return:  True if successful
        :rtype:   ``bool``
        """
        return self.driver.ex_destroy_forwarding_rule(forwarding_rule=self)

    def __repr__(self):
        return '<GCEForwardingRule id="%s" name="%s" address="%s">' % (
            self.id, self.name, self.address)


class GCENodeImage(NodeImage):
    """A GCE Node Image class."""
    def __init__(self, id, name, driver, extra=None):
        super(GCENodeImage, self).__init__(id, name, driver, extra=extra)

    def delete(self):
        """
        Delete this image

        :return: True if successful
        :rtype:  ``bool``
        """
        return self.driver.ex_delete_image(image=self)

    def deprecate(self, replacement, state, deprecated=None, obsolete=None,
                  deleted=None):
        """
        Deprecate this image

        :param  replacement: Image to use as a replacement
        :type   replacement: ``str`` or :class: `GCENodeImage`

        :param  state: Deprecation state of this image. Possible values include
                       \'DELETED\', \'DEPRECATED\' or \'OBSOLETE\'.
        :type   state: ``str``

        :param  deprecated: RFC3339 timestamp to mark DEPRECATED
        :type   deprecated: ``str`` or ``None``

        :param  obsolete: RFC3339 timestamp to mark OBSOLETE
        :type   obsolete: ``str`` or ``None``

        :param  deleted: RFC3339 timestamp to mark DELETED
        :type   deleted: ``str`` or ``None``

        :return: True if successful
        :rtype:  ``bool``
        """
        return self.driver.ex_deprecate_image(self, replacement, state,
                                              deprecated, obsolete, deleted)


class GCENetwork(UuidMixin):
    """A GCE Network object class."""
    def __init__(self, id, name, cidr, driver, extra=None):
        self.id = str(id)
        self.name = name
        self.cidr = cidr
        self.driver = driver
        self.extra = extra
        UuidMixin.__init__(self)

    def destroy(self):
        """
        Destroy this network

        :return: True if successful
        :rtype:  ``bool``
        """
        return self.driver.ex_destroy_network(network=self)

    def __repr__(self):
        return '<GCENetwork id="%s" name="%s" cidr="%s">' % (
            self.id, self.name, self.cidr)


class GCERoute(UuidMixin):
    """A GCE Route object class."""
    def __init__(self, id, name, dest_range, priority, network="default",
                 tags=None, driver=None, extra=None):
        self.id = str(id)
        self.name = name
        self.dest_range = dest_range
        self.priority = priority
        self.network = network
        self.tags = tags
        self.driver = driver
        self.extra = extra
        UuidMixin.__init__(self)

    def destroy(self):
        """
        Destroy this route

        :return: True if successful
        :rtype:  ``bool``
        """
        return self.driver.ex_destroy_route(route=self)

    def __repr__(self):
        return '<GCERoute id="%s" name="%s" dest_range="%s" network="%s">' % (
            self.id, self.name, self.dest_range, self.network.name)


class GCENodeSize(NodeSize):
    """A GCE Node Size (MachineType) class."""
    def __init__(self, id, name, ram, disk, bandwidth, price, driver,
                 extra=None):
        self.extra = extra
        super(GCENodeSize, self).__init__(id, name, ram, disk, bandwidth,
                                          price, driver, extra=extra)


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

    def set_common_instance_metadata(self, metadata=None, force=False):
        """
        Set common instance metadata for the project. Common uses
        are for setting 'sshKeys', or setting a project-wide
        'startup-script' for all nodes (instances).  Passing in
        ``None`` for the 'metadata' parameter will clear out all common
        instance metadata *except* for 'sshKeys'. If you also want to
        update 'sshKeys', set the 'force' paramater to ``True``.

        :param  metadata: Dictionay of metadata. Can be either a standard
                          python dictionary, or the format expected by
                          GCE (e.g. {'items': [{'key': k1, 'value': v1}, ...}]
        :type   metadata: ``dict`` or ``None``

        :param  force: Force update of 'sshKeys'. If force is ``False`` (the
                       default), existing sshKeys will be retained. Setting
                       force to ``True`` will either replace sshKeys if a new
                       a new value is supplied, or deleted if no new value
                       is supplied.
        :type   force: ``bool``

        :return: True if successful
        :rtype:  ``bool``
        """
        return self.driver.ex_set_common_instance_metadata(self, metadata)

    def set_usage_export_bucket(self, bucket, prefix=None):
        """
        Used to retain Compute Engine resource usage, storing the CSV data in
        a Google Cloud Storage bucket. See the
        `docs <https://cloud.google.com/compute/docs/usage-export>`_ for more
        information. Please ensure you have followed the necessary setup steps
        prior to enabling this feature (e.g. bucket exists, ACLs are in place,
        etc.)

        :param  bucket: Name of the Google Cloud Storage bucket. Specify the
                        name in either 'gs://<bucket_name>' or the full URL
                        'https://storage.googleapis.com/<bucket_name>'.
        :type   bucket: ``str``

        :param  prefix: Optional prefix string for all reports.
        :type   prefix: ``str`` or ``None``

        :return: True if successful
        :rtype:  ``bool``
        """
        return self.driver.ex_set_usage_export_bucket(self, bucket, prefix)

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


class GCESnapshot(VolumeSnapshot):
    def __init__(self, id, name, size, status, driver, extra=None,
                 created=None):
        self.name = name
        self.status = status
        super(GCESnapshot, self).__init__(id, driver, size, extra, created)


class GCETargetHttpProxy(UuidMixin):
    def __init__(self, id, name, urlmap, driver, extra=None):
        self.id = str(id)
        self.name = name
        self.urlmap = urlmap
        self.driver = driver
        self.extra = extra or {}
        UuidMixin.__init__(self)

    def __repr__(self):
        return '<GCETargetHttpProxy id="%s" name="%s">' % (
            self.id, self.name)

    def destroy(self):
        """
        Destroy this Target HTTP Proxy.

        :return:  True if successful
        :rtype:   ``bool``
        """
        return self.driver.ex_destroy_targethttpproxy(targethttpproxy=self)


class GCETargetInstance(UuidMixin):
    def __init__(self, id, name, zone, node, driver, extra=None):
        self.id = str(id)
        self.name = name
        self.zone = zone
        self.node = node
        self.driver = driver
        self.extra = extra
        UuidMixin.__init__(self)

    def destroy(self):
        """
        Destroy this Target Instance

        :return:  True if successful
        :rtype:   ``bool``
        """
        return self.driver.ex_destroy_targetinstance(targetinstance=self)

    def __repr__(self):
        return '<GCETargetInstance id="%s" name="%s" zone="%s" node="%s">' % (
            self.id, self.name, self.zone.name,
            (hasattr(self.node, 'name') and self.node.name or self.node))


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

    def set_backup_targetpool(self, backup_targetpool, failover_ratio=0.1):
        """
        Set a backup targetpool.

        :param  backup_targetpool: The existing targetpool to use for
                                   failover traffic.
        :type   backup_targetpool: :class:`GCETargetPool`

        :param  failover_ratio: The percentage of healthy VMs must fall at or
                                below this value before traffic will be sent
                                to the backup targetpool (default 0.10)
        :type   failover_ratio: ``float``

        :return:  True if successful
        :rtype:   ``bool``
        """
        return self.driver.ex_targetpool_set_backup_targetpool(
            targetpool=self, backup_targetpool=backup_targetpool,
            failover_ratio=failover_ratio)

    def get_health(self, node=None):
        """
        Return a hash of target pool instances and their health.

        :param  node: Optional node to specify if only a specific node's
                      health status should be returned
        :type   node: ``str``, ``Node``, or ``None``

        :return: List of hashes of nodes and their respective health
        :rtype:  ``list`` of ``dict``
        """
        return self.driver.ex_targetpool_get_health(targetpool=self, node=node)

    def destroy(self):
        """
        Destroy this Target Pool

        :return:  True if successful
        :rtype:   ``bool``
        """
        return self.driver.ex_destroy_targetpool(targetpool=self)

    def __repr__(self):
        return '<GCETargetPool id="%s" name="%s" region="%s">' % (
            self.id, self.name, self.region.name)


class GCEUrlMap(UuidMixin):
    """A GCE URL Map."""

    def __init__(self, id, name, default_service, host_rules, path_matchers,
                 tests, driver, extra=None):
        self.id = str(id)
        self.name = name
        self.default_service = default_service
        self.host_rules = host_rules or []
        self.path_matchers = path_matchers or []
        self.tests = tests or []
        self.driver = driver
        self.extra = extra or {}
        UuidMixin.__init__(self)

    def __repr__(self):
        return '<GCEUrlMap id="%s" name="%s">' % (
            self.id, self.name)

    def destroy(self):
        """
        Destroy this URL Map

        :return:  True if successful
        :rtype:   ``bool``
        """
        return self.driver.ex_destroy_urlmap(urlmap=self)


class GCEZone(NodeLocation):
    """Subclass of NodeLocation to provide additional information."""
    def __init__(self, id, name, status, maintenance_windows, deprecated,
                 driver, extra=None):
        self.status = status
        self.maintenance_windows = maintenance_windows
        self.deprecated = deprecated
        self.extra = extra
        country = name.split('-')[0]
        super(GCEZone, self).__init__(id=str(id), name=name, country=country,
                                      driver=driver)

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

    def _now(self):
        """
        Returns current UTC time.

        Can be overridden in unittests.
        """
        return datetime.datetime.utcnow()

    def _get_next_maint(self):
        """
        Returns the next Maintenance Window.

        :return:  A dictionary containing maintenance window info (or None if
                  no maintenance windows are scheduled)
                  The dictionary contains 4 keys with values of type ``str``
                      - name: The name of the maintenance window
                      - description: Description of the maintenance window
                      - beginTime: RFC3339 Timestamp
                      - endTime: RFC3339 Timestamp
        :rtype:   ``dict`` or ``None``
        """
        begin = None
        next_window = None
        if not self.maintenance_windows:
            return None
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

        :return:  Time until next maintenance window (or None if no
                  maintenance windows are scheduled)
        :rtype:   :class:`datetime.timedelta` or ``None``
        """
        next_window = self._get_next_maint()
        if not next_window:
            return None
        now = self._now()
        next_begin = timestamp_to_datetime(next_window['beginTime'])
        return next_begin - now

    def _get_next_mw_duration(self):
        """
        Returns the duration of the next maintenance window.

        :return:  Duration of next maintenance window (or None if no
                  maintenance windows are scheduled)
        :rtype:   :class:`datetime.timedelta` or ``None``
        """
        next_window = self._get_next_maint()
        if not next_window:
            return None
        next_begin = timestamp_to_datetime(next_window['beginTime'])
        next_end = timestamp_to_datetime(next_window['endTime'])
        return next_end - next_begin

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
    website = 'https://cloud.google.com/'

    # Google Compute Engine node states are mapped to Libcloud node states
    # per the following dict. GCE does not have an actual 'stopped' state
    # but instead uses a 'terminated' state to indicate the node exists
    # but is not running. In order to better match libcloud, GCE maps this
    # 'terminated' state to 'STOPPED'.
    # Also, when a node is deleted from GCE, it no longer exists and instead
    # will result in a ResourceNotFound error versus returning a placeholder
    # node in a 'terminated' state.
    # For more details, please see GCE's docs,
    # https://cloud.google.com/compute/docs/instances#checkmachinestatus
    NODE_STATE_MAP = {
        "PROVISIONING": NodeState.PENDING,
        "STAGING": NodeState.PENDING,
        "RUNNING": NodeState.RUNNING,
        "STOPPING": NodeState.PENDING,
        "TERMINATED": NodeState.STOPPED,
        "UNKNOWN": NodeState.UNKNOWN
    }

    AUTH_URL = "https://www.googleapis.com/auth/"
    SA_SCOPES_MAP = {
        # list derived from 'gcloud compute instances create --help'
        "bigquery": "bigquery",
        "compute-ro": "compute.readonly",
        "compute-rw": "compute",
        "datastore": "datastore",
        "sql": "sqlservice",
        "sql-admin": "sqlservice.admin",
        "storage-full": "devstorage.full_control",
        "storage-ro": "devstorage.read_only",
        "storage-rw": "devstorage.read_write",
        "taskqueue": "taskqueue",
        "userinfo-email": "userinfo.email"
    }

    IMAGE_PROJECTS = {
        "centos-cloud": ["centos"],
        "coreos-cloud": ["coreos"],
        "debian-cloud": ["debian", "backports"],
        "gce-nvme": ["nvme-backports"],
        "google-containers": ["container-vm"],
        "opensuse-cloud": ["opensuse"],
        "rhel-cloud": ["rhel"],
        "suse-cloud": ["sles", "suse"],
        "ubuntu-os-cloud": ["ubuntu"],
        "windows-cloud": ["windows"],
    }

    def __init__(self, user_id, key=None, datacenter=None, project=None,
                 auth_type=None, scopes=None, credential_file=None, **kwargs):
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

        :keyword  auth_type: Accepted values are "SA" or "IA" or "GCE"
                             ("Service Account" or "Installed Application" or
                             "GCE" if libcloud is being used on a GCE instance
                             with service account enabled).
                             If not supplied, auth_type will be guessed based
                             on value of user_id or if the code is being
                             executed in a GCE instance.
        :type     auth_type: ``str``

        :keyword  scopes: List of authorization URLs. Default is empty and
                          grants read/write to Compute, Storage, DNS.
        :type     scopes: ``list``

        :keyword  credential_file: Path to file for caching authentication
                                   information used by GCEConnection.
        :type     credential_file: ``str``
        """
        if not project:
            raise ValueError('Project name must be specified using '
                             '"project" keyword.')

        self.auth_type = auth_type
        self.project = project
        self.scopes = scopes
        self.credential_file = credential_file or \
            '~/.gce_libcloud_auth' + '.' + self.project

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

    def ex_add_access_config(self, node, name, nic, nat_ip=None,
                             config_type=None):
        """
        Add a network interface access configuration to a node.

        :keyword  node: The existing target Node (instance) that will receive
                        the new access config.
        :type     node: ``Node``

        :keyword  name: Name of the new access config.
        :type     node: ``str``

        :keyword  nat_ip: The external existing static IP Address to use for
                          the access config. If not provided, an ephemeral
                          IP address will be allocated.
        :type     nat_ip: ``str`` or ``None``

        :keyword  config_type: The type of access config to create. Currently
                               the only supported type is 'ONE_TO_ONE_NAT'.
        :type     config_type: ``str`` or ``None``

        :return: True if successful
        :rtype:  ``bool``
        """
        if not isinstance(node, Node):
            raise ValueError("Must specify a valid libcloud node object.")
        node_name = node.name
        zone_name = node.extra['zone'].name

        config = {'name': name}
        if config_type is None:
            config_type = 'ONE_TO_ONE_NAT'
        config['type'] = config_type

        if nat_ip is not None:
            config['natIP'] = nat_ip
        params = {'networkInterface': nic}
        request = '/zones/%s/instances/%s/addAccessConfig' % (zone_name,
                                                              node_name)
        self.connection.async_request(request, method='POST',
                                      data=config, params=params)
        return True

    def ex_delete_access_config(self, node, name, nic):
        """
        Delete a network interface access configuration from a node.

        :keyword  node: The existing target Node (instance) for the request.
        :type     node: ``Node``

        :keyword  name: Name of the access config.
        :type     node: ``str``

        :keyword  nic: Name of the network interface.
        :type     nic: ``str``

        :return: True if successful
        :rtype:  ``bool``
        """
        if not isinstance(node, Node):
            raise ValueError("Must specify a valid libcloud node object.")
        node_name = node.name
        zone_name = node.extra['zone'].name

        params = {'accessConfig': name, 'networkInterface': nic}
        request = '/zones/%s/instances/%s/deleteAccessConfig' % (zone_name,
                                                                 node_name)
        self.connection.async_request(request, method='POST', params=params)
        return True

    def ex_set_node_metadata(self, node, metadata):
        """
        Set metadata for the specified node.

        :keyword  node: The existing target Node (instance) for the request.
        :type     node: ``Node``

        :keyword  metadata: Set (or clear with None) metadata for this
                            particular node.
        :type     metadata: ``dict`` or ``None``

        :return: True if successful
        :rtype:  ``bool``
        """
        if not isinstance(node, Node):
            raise ValueError("Must specify a valid libcloud node object.")
        node_name = node.name
        zone_name = node.extra['zone'].name
        if 'metadata' in node.extra and \
                'fingerprint' in node.extra['metadata']:
            current_fp = node.extra['metadata']['fingerprint']
        else:
            current_fp = 'absent'
        body = self._format_metadata(current_fp, metadata)
        request = '/zones/%s/instances/%s/setMetadata' % (zone_name,
                                                          node_name)
        self.connection.async_request(request, method='POST', data=body)
        return True

    def ex_get_serial_output(self, node):
        """
        Fetch the console/serial port output from the node.

        :keyword  node: The existing target Node (instance) for the request.
        :type     node: ``Node``

        :return: A string containing serial port output of the node.
        :rtype:  ``str``
        """
        if not isinstance(node, Node):
            raise ValueError("Must specify a valid libcloud node object.")
        node_name = node.name
        zone_name = node.extra['zone'].name
        request = '/zones/%s/instances/%s/serialPort' % (zone_name,
                                                         node_name)
        response = self.connection.request(request, method='GET').object
        return response['contents']

    def ex_list(self, list_fn, **kwargs):
        """
        Wrap a list method in a :class:`GCEList` iterator.

        >>> for sublist in driver.ex_list(driver.ex_list_urlmaps).page(1):
        ...   sublist
        ...
        [<GCEUrlMap id="..." name="cli-map">]
        [<GCEUrlMap id="..." name="lc-map">]
        [<GCEUrlMap id="..." name="web-map">]

        :param  list_fn: A bound list method from :class:`GCENodeDriver`.
        :type   list_fn: ``instancemethod``

        :return: An iterator that returns sublists from list_fn.
        :rtype: :class:`GCEList`
        """
        return GCEList(driver=self, list_fn=list_fn, **kwargs)

    def ex_list_disktypes(self, zone=None):
        """
        Return a list of DiskTypes for a zone or all.

        :keyword  zone: The zone to return DiskTypes from. For example:
                        'us-central1-a'.  If None, will return DiskTypes from
                        self.zone.  If 'all', will return all DiskTypes.
        :type     zone: ``str`` or ``None``

        :return: A list of static DiskType objects.
        :rtype: ``list`` of :class:`GCEDiskType`
        """
        list_disktypes = []
        zone = self._set_zone(zone)
        if zone is None:
            request = '/aggregated/diskTypes'
        else:
            request = '/zones/%s/diskTypes' % (zone.name)
        response = self.connection.request(request, method='GET').object

        if 'items' in response:
            # The aggregated result returns dictionaries for each region
            if zone is None:
                for v in response['items'].values():
                    zone_disktypes = [self._to_disktype(a) for a in
                                      v.get('diskTypes', [])]
                    list_disktypes.extend(zone_disktypes)
            else:
                list_disktypes = [self._to_disktype(a) for a in
                                  response['items']]
        return list_disktypes

    def ex_set_usage_export_bucket(self, bucket, prefix=None):
        """
        Used to retain Compute Engine resource usage, storing the CSV data in
        a Google Cloud Storage bucket. See the
        `docs <https://cloud.google.com/compute/docs/usage-export>`_ for more
        information. Please ensure you have followed the necessary setup steps
        prior to enabling this feature (e.g. bucket exists, ACLs are in place,
        etc.)

        :param  bucket: Name of the Google Cloud Storage bucket. Specify the
                        name in either 'gs://<bucket_name>' or the full URL
                        'https://storage.googleapis.com/<bucket_name>'.
        :type   bucket: ``str``

        :param  prefix: Optional prefix string for all reports.
        :type   prefix: ``str`` or ``None``

        :return: True if successful
        :rtype:  ``bool``
        """
        if bucket.startswith('https://www.googleapis.com/') or \
                bucket.startswith('gs://'):
            data = {'bucketName': bucket}
        else:
            raise ValueError("Invalid bucket name: %s" % bucket)
        if prefix:
            data['reportNamePrefix'] = prefix

        request = '/setUsageExportBucket'
        self.connection.async_request(request, method='POST', data=data)
        return True

    def ex_set_common_instance_metadata(self, metadata=None, force=False):
        """
        Set common instance metadata for the project. Common uses
        are for setting 'sshKeys', or setting a project-wide
        'startup-script' for all nodes (instances).  Passing in
        ``None`` for the 'metadata' parameter will clear out all common
        instance metadata *except* for 'sshKeys'. If you also want to
        update 'sshKeys', set the 'force' paramater to ``True``.

        :param  metadata: Dictionay of metadata. Can be either a standard
                          python dictionary, or the format expected by
                          GCE (e.g. {'items': [{'key': k1, 'value': v1}, ...}]
        :type   metadata: ``dict`` or ``None``

        :param  force: Force update of 'sshKeys'. If force is ``False`` (the
                       default), existing sshKeys will be retained. Setting
                       force to ``True`` will either replace sshKeys if a new
                       a new value is supplied, or deleted if no new value
                       is supplied.
        :type   force: ``bool``

        :return: True if successful
        :rtype:  ``bool``
        """
        if metadata:
            metadata = self._format_metadata('na', metadata)

        request = '/setCommonInstanceMetadata'

        project = self.ex_get_project()
        current_metadata = project.extra['commonInstanceMetadata']
        fingerprint = current_metadata['fingerprint']
        md_items = []
        if 'items' in current_metadata:
            md_items = current_metadata['items']

        # grab copy of current 'sshKeys' in case we want to retain them
        current_keys = ""
        for md in md_items:
            if md['key'] == 'sshKeys':
                current_keys = md['value']

        new_md = self._set_project_metadata(metadata, force, current_keys)

        md = {'fingerprint': fingerprint, 'items': new_md}
        self.connection.async_request(request, method='POST', data=md)
        return True

    def ex_list_addresses(self, region=None):
        """
        Return a list of static addresses for a region, 'global', or all.

        :keyword  region: The region to return addresses from. For example:
                          'us-central1'.  If None, will return addresses from
                          region of self.zone.  If 'all', will return all
                          addresses. If 'global', it will return addresses in
                          the global namespace.
        :type     region: ``str`` or ``None``

        :return: A list of static address objects.
        :rtype: ``list`` of :class:`GCEAddress`
        """
        list_addresses = []
        if region != 'global':
            region = self._set_region(region)
        if region is None:
            request = '/aggregated/addresses'
        elif region == 'global':
            request = '/global/addresses'
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

    def ex_list_backendservices(self):
        """
        Return a list of backend services.

        :return: A list of backend service objects.
        :rtype: ``list`` of :class:`GCEBackendService`
        """
        list_backendservices = []
        response = self.connection.request('/global/backendServices',
                                           method='GET').object

        list_backendservices = [self._to_backendservice(d) for d in
                                response.get('items', [])]

        return list_backendservices

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

    def ex_list_forwarding_rules(self, region=None, global_rules=False):
        """
        Return the list of forwarding rules for a region or all.

        :keyword  region: The region to return forwarding rules from.  For
                          example: 'us-central1'.  If None, will return
                          forwarding rules from the region of self.region
                          (which is based on self.zone).  If 'all', will
                          return forwarding rules for all regions, which does
                          not include the global forwarding rules.
        :type     region: ``str`` or :class:`GCERegion` or ``None``

        :keyword  global_rules: List global forwarding rules instead of
                                per-region rules.  Setting True will cause
                                'region' parameter to be ignored.
        :type     global_rules: ``bool``

        :return: A list of forwarding rule objects.
        :rtype: ``list`` of :class:`GCEForwardingRule`
        """
        list_forwarding_rules = []
        if global_rules:
            region = None
            request = '/global/forwardingRules'
        else:
            region = self._set_region(region)
            if region is None:
                request = '/aggregated/forwardingRules'
            else:
                request = '/regions/%s/forwardingRules' % (region.name)
        response = self.connection.request(request, method='GET').object

        if 'items' in response:
            # The aggregated result returns dictionaries for each region
            if not global_rules and region is None:
                for v in response['items'].values():
                    region_forwarding_rules = [self._to_forwarding_rule(f) for
                                               f in v.get('forwardingRules',
                                                          [])]
                    list_forwarding_rules.extend(region_forwarding_rules)
            else:
                list_forwarding_rules = [self._to_forwarding_rule(f) for f in
                                         response['items']]
        return list_forwarding_rules

    def list_images(self, ex_project=None, ex_include_deprecated=False):
        """
        Return a list of image objects. If no project is specified, a list of
        all non-deprecated global and vendor images images is returned. By
        default, only non-deprecated images are returned.

        :keyword  ex_project: Optional alternate project name.
        :type     ex_project: ``str``, ``list`` of ``str``, or ``None``

        :keyword  ex_include_deprecated: If True, even DEPRECATED images will
                                         be returned.
        :type     ex_include_deprecated: ``bool``

        :return:  List of GCENodeImage objects
        :rtype:   ``list`` of :class:`GCENodeImage`
        """
        dep = ex_include_deprecated
        if ex_project is not None:
            return self.ex_list_project_images(ex_project=ex_project,
                                               ex_include_deprecated=dep)
        image_list = self.ex_list_project_images(ex_project=None,
                                                 ex_include_deprecated=dep)
        for img_proj in list(self.IMAGE_PROJECTS.keys()):
            try:
                image_list.extend(
                    self.ex_list_project_images(ex_project=img_proj,
                                                ex_include_deprecated=dep))
            except:
                # do not break if an OS type is invalid
                pass
        return image_list

    def ex_list_project_images(self, ex_project=None,
                               ex_include_deprecated=False):
        """
        Return a list of image objects for a project. If no project is
        specified, only a list of 'global' images is returned.

        :keyword  ex_project: Optional alternate project name.
        :type     ex_project: ``str``, ``list`` of ``str``, or ``None``

        :keyword  ex_include_deprecated: If True, even DEPRECATED images will
                                         be returned.
        :type     ex_include_deprecated: ``bool``

        :return:  List of GCENodeImage objects
        :rtype:   ``list`` of :class:`GCENodeImage`
        """
        list_images = []
        request = '/global/images'
        if ex_project is None:
            response = self.connection.request(request, method='GET').object
            for img in response.get('items', []):
                if 'deprecated' not in img:
                    list_images.append(self._to_node_image(img))
                else:
                    if ex_include_deprecated:
                        list_images.append(self._to_node_image(img))
        else:
            list_images = []
            # Save the connection request_path
            save_request_path = self.connection.request_path
            if isinstance(ex_project, str):
                ex_project = [ex_project]
            for proj in ex_project:
                # Override the connection request path
                new_request_path = save_request_path.replace(self.project,
                                                             proj)
                self.connection.request_path = new_request_path
                try:
                    response = self.connection.request(request,
                                                       method='GET').object
                except:
                    raise
                finally:
                    # Restore the connection request_path
                    self.connection.request_path = save_request_path
                for img in response.get('items', []):
                    if 'deprecated' not in img:
                        list_images.append(self._to_node_image(img))
                    else:
                        if ex_include_deprecated:
                            list_images.append(self._to_node_image(img))
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

    def ex_list_routes(self):
        """
        Return the list of routes.

        :return: A list of route objects.
        :rtype: ``list`` of :class:`GCERoute`
        """
        list_routes = []
        request = '/global/routes'
        response = self.connection.request(request, method='GET').object
        list_routes = [self._to_route(n) for n in
                       response.get('items', [])]
        return list_routes

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

    def ex_list_snapshots(self):
        """
        Return the list of disk snapshots in the project.

        :return:  A list of snapshot objects
        :rtype:   ``list`` of :class:`GCESnapshot`
        """
        list_snapshots = []
        request = '/global/snapshots'
        response = self.connection.request(request, method='GET').object
        list_snapshots = [self._to_snapshot(s) for s in
                          response.get('items', [])]
        return list_snapshots

    def ex_list_targethttpproxies(self):
        """
        Return the list of target HTTP proxies.

        :return:  A list of target http proxy objects
        :rtype:   ``list`` of :class:`GCETargetHttpProxy`
        """
        request = '/global/targetHttpProxies'
        response = self.connection.request(request, method='GET').object
        return [self._to_targethttpproxy(u) for u in
                response.get('items', [])]

    def ex_list_targetinstances(self, zone=None):
        """
        Return the list of target instances.

        :return:  A list of target instance objects
        :rtype:   ``list`` of :class:`GCETargetInstance`
        """
        list_targetinstances = []
        zone = self._set_zone(zone)
        if zone is None:
            request = '/aggregated/targetInstances'
        else:
            request = '/zones/%s/targetInstances' % (zone.name)
        response = self.connection.request(request, method='GET').object

        if 'items' in response:
            # The aggregated result returns dictionaries for each region
            if zone is None:
                for v in response['items'].values():
                    zone_targetinstances = [self._to_targetinstance(t) for t in
                                            v.get('targetInstances', [])]
                    list_targetinstances.extend(zone_targetinstances)
            else:
                list_targetinstances = [self._to_targetinstance(t) for t in
                                        response['items']]
        return list_targetinstances

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

    def ex_list_urlmaps(self):
        """
        Return the list of URL Maps in the project.

        :return:  A list of url map objects
        :rtype:   ``list`` of :class:`GCEUrlMap`
        """
        request = '/global/urlMaps'
        response = self.connection.request(request, method='GET').object
        return [self._to_urlmap(u) for u in response.get('items', [])]

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

    def ex_create_address(self, name, region=None, address=None,
                          description=None):
        """
        Create a static address in a region, or a global address.

        :param  name: Name of static address
        :type   name: ``str``

        :keyword  region: Name of region for the address (e.g. 'us-central1')
                          Use 'global' to create a global address.
        :type     region: ``str`` or :class:`GCERegion`

        :keyword  address: Ephemeral IP address to promote to a static one
                           (e.g. 'xxx.xxx.xxx.xxx')
        :type     address: ``str`` or ``None``

        :keyword  description: Optional descriptive comment.
        :type     description: ``str`` or ``None``

        :return:  Static Address object
        :rtype:   :class:`GCEAddress`
        """
        region = region or self.region
        if region != 'global' and not hasattr(region, 'name'):
            region = self.ex_get_region(region)
        elif region is None:
            raise ValueError('REGION_NOT_SPECIFIED',
                             'Region must be provided for an address')
        address_data = {'name': name}
        if address:
            address_data['address'] = address
        if description:
            address_data['description'] = description
        if region == 'global':
            request = '/global/addresses'
        else:
            request = '/regions/%s/addresses' % (region.name)
        self.connection.async_request(request, method='POST',
                                      data=address_data)
        return self.ex_get_address(name, region=region)

    def ex_create_backendservice(self, name, healthchecks):
        """
        Create a global backend service.

        :param  name: Name of the backend service
        :type   name: ``str``

        :keyword  healthchecks: A list of HTTP Health Checks to use for this
                                service.  There must be at least one.
        :type     healthchecks: ``list`` of (``str`` or
                                :class:`GCEHealthCheck`)

        :return:  A Backend Service object
        :rtype:   :class:`GCEBackendService`
        """
        backendservice_data = {'name': name, 'healthChecks': []}

        for hc in healthchecks:
            if not hasattr(hc, 'extra'):
                hc = self.ex_get_healthcheck(name=hc)
            backendservice_data['healthChecks'].append(hc.extra['selfLink'])

        request = '/global/backendServices'
        self.connection.async_request(request, method='POST',
                                      data=backendservice_data)
        return self.ex_get_backendservice(name)

    def ex_create_healthcheck(self, name, host=None, path=None, port=None,
                              interval=None, timeout=None,
                              unhealthy_threshold=None,
                              healthy_threshold=None,
                              description=None):
        """
        Create an Http Health Check.

        :param  name: Name of health check
        :type   name: ``str``

        :keyword  host: Hostname of health check request.  Defaults to empty
                        and public IP is used instead.
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

        :keyword  description: The description of the check.  Defaults to None.
        :type     description: ``str`` or ``None``

        :return:  Health Check object
        :rtype:   :class:`GCEHealthCheck`
        """
        hc_data = {}
        hc_data['name'] = name
        if host:
            hc_data['host'] = host
        if description:
            hc_data['description'] = description
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
                           source_ranges=None, source_tags=None,
                           target_tags=None):
        """
        Create a firewall on a network.

        Firewall rules should be supplied in the "allowed" field.  This is a
        list of dictionaries formated like so ("ports" is optional)::

            [{"IPProtocol": "<protocol string or number>",
              "ports": "<port_numbers or ranges>"}]

        For example, to allow tcp on port 8080 and udp on all ports, 'allowed'
        would be::

            [{"IPProtocol": "tcp",
              "ports": ["8080"]},
             {"IPProtocol": "udp"}]

        See `Firewall Reference <https://developers.google.com/compute/docs/
        reference/latest/firewalls/insert>`_ for more information.

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

        :keyword  source_tags: A list of source instance tags the rules apply
                               to.
        :type     source_tags: ``list`` of ``str``

        :keyword  target_tags: A list of target instance tags the rules apply
                               to.
        :type     target_tags: ``list`` of ``str``

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
        if source_ranges is None:
            source_ranges = ['0.0.0.0/0']
        firewall_data['sourceRanges'] = source_ranges
        if source_tags is not None:
            firewall_data['sourceTags'] = source_tags
        if target_tags is not None:
            firewall_data['targetTags'] = target_tags

        request = '/global/firewalls'

        self.connection.async_request(request, method='POST',
                                      data=firewall_data)
        return self.ex_get_firewall(name)

    def ex_create_forwarding_rule(self, name, target=None, region=None,
                                  protocol='tcp', port_range=None,
                                  address=None, description=None,
                                  global_rule=False, targetpool=None):
        """
        Create a forwarding rule.

        :param  name: Name of forwarding rule to be created
        :type   name: ``str``

        :keyword  target: The target of this forwarding rule.  For global
                          forwarding rules this must be a global
                          TargetHttpProxy. For regional rules this may be
                          either a TargetPool or TargetInstance. If passed
                          a string instead of the object, it will be the name
                          of a TargetHttpProxy for global rules or a
                          TargetPool for regional rules.  A TargetInstance
                          must be passed by object. (required)
        :type     target: ``str`` or :class:`GCETargetHttpProxy` or
                          :class:`GCETargetInstance` or :class:`GCETargetPool`

        :keyword  region: Region to create the forwarding rule in.  Defaults to
                          self.region.  Ignored if global_rule is True.
        :type     region: ``str`` or :class:`GCERegion`

        :keyword  protocol: Should be 'tcp' or 'udp'
        :type     protocol: ``str``

        :keyword  port_range: Single port number or range separated by a dash.
                              Examples: '80', '5000-5999'.  Required for global
                              forwarding rules, optional for regional rules.
        :type     port_range: ``str``

        :keyword  address: Optional static address for forwarding rule. Must be
                           in same region.
        :type     address: ``str`` or :class:`GCEAddress`

        :keyword  description: The description of the forwarding rule.
                               Defaults to None.
        :type     description: ``str`` or ``None``

        :keyword  targetpool: Deprecated parameter for backwards compatibility.
                              Use target instead.
        :type     targetpool: ``str`` or :class:`GCETargetPool`

        :return:  Forwarding Rule object
        :rtype:   :class:`GCEForwardingRule`
        """
        forwarding_rule_data = {'name': name}
        if global_rule:
            if not hasattr(target, 'name'):
                target = self.ex_get_targethttpproxy(target)
        else:
            region = region or self.region
            if not hasattr(region, 'name'):
                region = self.ex_get_region(region)
            forwarding_rule_data['region'] = region.extra['selfLink']

            if not target:
                target = targetpool  # Backwards compatibility
            if not hasattr(target, 'name'):
                target = self.ex_get_targetpool(target, region)

        forwarding_rule_data['target'] = target.extra['selfLink']
        forwarding_rule_data['IPProtocol'] = protocol.upper()
        if address:
            if not hasattr(address, 'name'):
                address = self.ex_get_address(
                    address, 'global' if global_rule else region)
            forwarding_rule_data['IPAddress'] = address.address
        if port_range:
            forwarding_rule_data['portRange'] = port_range
        if description:
            forwarding_rule_data['description'] = description

        if global_rule:
            request = '/global/forwardingRules'
        else:
            request = '/regions/%s/forwardingRules' % (region.name)

        self.connection.async_request(request, method='POST',
                                      data=forwarding_rule_data)

        return self.ex_get_forwarding_rule(name, global_rule=global_rule)

    def ex_create_image(self, name, volume, description=None,
                        use_existing=True, wait_for_completion=True):
        """
        Create an image from the provided volume.

        :param  name: The name of the image to create.
        :type   name: ``str``

        :param  volume: The volume to use to create the image, or the
                        Google Cloud Storage URI
        :type   volume: ``str`` or :class:`StorageVolume`

        :keyword    description: Description of the new Image
        :type       description: ``str``

        :keyword  use_existing: If True and an image with the given name
                                already exists, return an object for that
                                image instead of attempting to create
                                a new image.
        :type     use_existing: ``bool``

        :keyword  wait_for_completion: If True, wait until the new image is
                                       created before returning a new NodeImage
                                       Otherwise, return a new NodeImage
                                       instance, and let the user track the
                                       creation progress
        :type     wait_for_completion: ``bool``

        :return:    A GCENodeImage object for the new image
        :rtype:     :class:`GCENodeImage`

        """
        image_data = {}
        image_data['name'] = name
        image_data['description'] = description
        if isinstance(volume, StorageVolume):
            image_data['sourceDisk'] = volume.extra['selfLink']
            image_data['zone'] = volume.extra['zone'].name
        elif isinstance(volume, str) and \
                volume.startswith('https://') and volume.endswith('tar.gz'):
            image_data['rawDisk'] = {'source': volume, 'containerType': 'TAR'}
        else:
            raise ValueError('Source must be instance of StorageVolume or URI')

        request = '/global/images'

        try:
            if wait_for_completion:
                self.connection.async_request(request, method='POST',
                                              data=image_data)
            else:
                self.connection.request(request, method='POST',
                                        data=image_data)

        except ResourceExistsError:
            e = sys.exc_info()[1]
            if not use_existing:
                raise e

        return self.ex_get_image(name)

    def ex_create_route(self, name, dest_range, priority=500,
                        network="default", tags=None, next_hop=None,
                        description=None):
        """
        Create a route.

        :param  name: Name of route to be created
        :type   name: ``str``

        :param  dest_range: Address range of route in CIDR format.
        :type   dest_range: ``str``

        :param  priority: Priority value, lower values take precedence
        :type   priority: ``int``

        :param  network: The network the route belongs to. Can be either the
                         full URL of the network or a libcloud object.
        :type   network: ``str`` or ``GCENetwork``

        :param  tags: List of instance-tags for routing, empty for all nodes
        :type   tags: ``list`` of ``str`` or ``None``

        :param  next_hop: Next traffic hop. Use ``None`` for the default
                          Internet gateway, or specify an instance or IP
                          address.
        :type   next_hop: ``str``, ``Node``, or ``None``

        :param  description: Custom description for the route.
        :type   description: ``str`` or ``None``

        :return:  Route object
        :rtype:   :class:`GCERoute`
        """
        route_data = {}
        route_data['name'] = name
        route_data['destRange'] = dest_range
        route_data['priority'] = priority
        route_data['description'] = description
        if isinstance(network, str) and network.startswith('https://'):
            network_uri = network
        elif isinstance(network, str):
            network = self.ex_get_network(network)
            network_uri = network.extra['selfLink']
        else:
            network_uri = network.extra['selfLink']
        route_data['network'] = network_uri
        route_data['tags'] = tags
        if next_hop is None:
            url = 'https://www.googleapis.com/compute/%s/projects/%s/%s' % (
                  API_VERSION, self.project,
                  "global/gateways/default-internet-gateway")
            route_data['nextHopGateway'] = url
        elif isinstance(next_hop, str):
            route_data['nextHopIp'] = next_hop
        else:
            node = self.ex_get_node(next_hop)
            route_data['nextHopInstance'] = node.extra['selfLink']

        request = '/global/routes'
        self.connection.async_request(request, method='POST',
                                      data=route_data)

        return self.ex_get_route(name)

    def ex_create_network(self, name, cidr, description=None):
        """
        Create a network.

        :param  name: Name of network to be created
        :type   name: ``str``

        :param  cidr: Address range of network in CIDR format.
        :type   cidr: ``str``

        :param  description: Custom description for the network.
        :type   description: ``str`` or ``None``

        :return:  Network object
        :rtype:   :class:`GCENetwork`
        """
        network_data = {}
        network_data['name'] = name
        network_data['IPv4Range'] = cidr
        network_data['description'] = description

        request = '/global/networks'

        self.connection.async_request(request, method='POST',
                                      data=network_data)

        return self.ex_get_network(name)

    def create_node(self, name, size, image, location=None,
                    ex_network='default', ex_tags=None, ex_metadata=None,
                    ex_boot_disk=None, use_existing_disk=True,
                    external_ip='ephemeral', ex_disk_type='pd-standard',
                    ex_disk_auto_delete=True, ex_service_accounts=None,
                    description=None, ex_can_ip_forward=None,
                    ex_disks_gce_struct=None, ex_nic_gce_struct=None,
                    ex_on_host_maintenance=None, ex_automatic_restart=None):
        """
        Create a new node and return a node object for the node.

        :param  name: The name of the node to create.
        :type   name: ``str``

        :param  size: The machine type to use.
        :type   size: ``str`` or :class:`GCENodeSize`

        :param  image: The image to use to create the node (or, if attaching
                       a persistent disk, the image used to create the disk)
        :type   image: ``str`` or :class:`GCENodeImage` or ``None``

        :keyword  location: The location (zone) to create the node in.
        :type     location: ``str`` or :class:`NodeLocation` or
                            :class:`GCEZone` or ``None``

        :keyword  ex_network: The network to associate with the node.
        :type     ex_network: ``str`` or :class:`GCENetwork`

        :keyword  ex_tags: A list of tags to associate with the node.
        :type     ex_tags: ``list`` of ``str`` or ``None``

        :keyword  ex_metadata: Metadata dictionary for instance.
        :type     ex_metadata: ``dict`` or ``None``

        :keyword  ex_boot_disk: The boot disk to attach to the instance.
        :type     ex_boot_disk: :class:`StorageVolume` or ``str`` or ``None``

        :keyword  use_existing_disk: If True and if an existing disk with the
                                     same name/location is found, use that
                                     disk instead of creating a new one.
        :type     use_existing_disk: ``bool``

        :keyword  external_ip: The external IP address to use.  If 'ephemeral'
                               (default), a new non-static address will be
                               used.  If 'None', then no external address will
                               be used.  To use an existing static IP address,
                               a GCEAddress object should be passed in.
        :type     external_ip: :class:`GCEAddress` or ``str`` or ``None``

        :keyword  ex_disk_type: Specify a pd-standard (default) disk or pd-ssd
                                for an SSD disk.
        :type     ex_disk_type: ``str`` or :class:`GCEDiskType`

        :keyword  ex_disk_auto_delete: Indicate that the boot disk should be
                                       deleted when the Node is deleted. Set to
                                       True by default.
        :type     ex_disk_auto_delete: ``bool``

        :keyword  ex_service_accounts: Specify a list of serviceAccounts when
                                       creating the instance. The format is a
                                       list of dictionaries containing email
                                       and list of scopes, e.g.
                                       [{'email':'default',
                                         'scopes':['compute', ...]}, ...]
                                       Scopes can either be full URLs or short
                                       names. If not provided, use the
                                       'default' service account email and a
                                       scope of 'devstorage.read_only'. Also
                                       accepts the aliases defined in
                                       'gcloud compute'.
        :type     ex_service_accounts: ``list``

        :keyword  description: The description of the node (instance).
        :type     description: ``str`` or ``None``

        :keyword  ex_can_ip_forward: Set to ``True`` to allow this node to
                                  send/receive non-matching src/dst packets.
        :type     ex_can_ip_forward: ``bool`` or ``None``

        :keyword  ex_disks_gce_struct: Support for passing in the GCE-specific
                                       formatted disks[] structure. No attempt
                                       is made to ensure proper formatting of
                                       the disks[] structure. Using this
                                       structure obviates the need of using
                                       other disk params like 'ex_boot_disk',
                                       etc. See the GCE docs for specific
                                       details.
        :type     ex_disks_gce_struct: ``list`` or ``None``

        :keyword  ex_nic_gce_struct: Support passing in the GCE-specific
                                     formatted networkInterfaces[] structure.
                                     No attempt is made to ensure proper
                                     formatting of the networkInterfaces[]
                                     data. Using this structure obviates the
                                     need of using 'external_ip' and
                                     'ex_network'.  See the GCE docs for
                                     details.
        :type     ex_nic_gce_struct: ``list`` or ``None``
n
        :keyword  ex_on_host_maintenance: Defines whether node should be
                                          terminated or migrated when host
                                          machine goes down. Acceptable values
                                          are: 'MIGRATE' or 'TERMINATE' (If
                                          not supplied, value will be reset to
                                          GCE default value for the instance
                                          type.)
        :type     ex_on_host_maintenance: ``str`` or ``None``

        :keyword  ex_automatic_restart: Defines whether the instance should be
                                        automatically restarted when it is
                                        terminated by Compute Engine. (If not
                                        supplied, value will be set to the GCE
                                        default value for the instance type.)
        :type     ex_automatic_restart: ``bool`` or ``None``

        :return:  A Node object for the new node.
        :rtype:   :class:`Node`
        """
        if ex_boot_disk and ex_disks_gce_struct:
            raise ValueError("Cannot specify both 'ex_boot_disk' and "
                             "'ex_disks_gce_struct'")

        if not image and not ex_boot_disk and not ex_disks_gce_struct:
            raise ValueError("Missing root device or image. Must specify an "
                             "'image', existing 'ex_boot_disk', or use the "
                             "'ex_disks_gce_struct'.")

        location = location or self.zone
        if not hasattr(location, 'name'):
            location = self.ex_get_zone(location)
        if not hasattr(size, 'name'):
            size = self.ex_get_size(size, location)
        if not hasattr(ex_network, 'name'):
            ex_network = self.ex_get_network(ex_network)
        if image and not hasattr(image, 'name'):
            image = self.ex_get_image(image)
        if not hasattr(ex_disk_type, 'name'):
            ex_disk_type = self.ex_get_disktype(ex_disk_type, zone=location)
        if ex_boot_disk and not hasattr(ex_boot_disk, 'name'):
            ex_boot_disk = self.ex_get_disk(ex_boot_disk, zone=location)

        # Use disks[].initializeParams to auto-create the boot disk
        if not ex_disks_gce_struct and not ex_boot_disk:
            ex_disks_gce_struct = [{
                'autoDelete': ex_disk_auto_delete,
                'boot': True,
                'type': 'PERSISTENT',
                'mode': 'READ_WRITE',
                'deviceName': name,
                'initializeParams': {
                    'diskName': name,
                    'diskType': ex_disk_type.extra['selfLink'],
                    'sourceImage': image.extra['selfLink']
                }
            }]

        request, node_data = self._create_node_req(name, size, image,
                                                   location, ex_network,
                                                   ex_tags, ex_metadata,
                                                   ex_boot_disk, external_ip,
                                                   ex_disk_type,
                                                   ex_disk_auto_delete,
                                                   ex_service_accounts,
                                                   description,
                                                   ex_can_ip_forward,
                                                   ex_disks_gce_struct,
                                                   ex_nic_gce_struct,
                                                   ex_on_host_maintenance,
                                                   ex_automatic_restart)
        self.connection.async_request(request, method='POST', data=node_data)
        return self.ex_get_node(name, location.name)

    def ex_create_multiple_nodes(self, base_name, size, image, number,
                                 location=None, ex_network='default',
                                 ex_tags=None, ex_metadata=None,
                                 ignore_errors=True, use_existing_disk=True,
                                 poll_interval=2, external_ip='ephemeral',
                                 ex_disk_type='pd-standard',
                                 ex_disk_auto_delete=True,
                                 ex_service_accounts=None,
                                 timeout=DEFAULT_TASK_COMPLETION_TIMEOUT,
                                 description=None,
                                 ex_can_ip_forward=None,
                                 ex_disks_gce_struct=None,
                                 ex_nic_gce_struct=None,
                                 ex_on_host_maintenance=None,
                                 ex_automatic_restart=None):
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
        :type   image: ``str`` or :class:`GCENodeImage`

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

        :keyword  use_existing_disk: If True and if an existing disk with the
                                     same name/location is found, use that
                                     disk instead of creating a new one.
        :type     use_existing_disk: ``bool``

        :keyword  poll_interval: Number of seconds between status checks.
        :type     poll_interval: ``int``

        :keyword  external_ip: The external IP address to use.  If 'ephemeral'
                               (default), a new non-static address will be
                               used. If 'None', then no external address will
                               be used. (Static addresses are not supported for
                               multiple node creation.)
        :type     external_ip: ``str`` or None

        :keyword  ex_disk_type: Specify a pd-standard (default) disk or pd-ssd
                                for an SSD disk.
        :type     ex_disk_type: ``str`` or :class:`GCEDiskType`

        :keyword  ex_disk_auto_delete: Indicate that the boot disk should be
                                       deleted when the Node is deleted. Set to
                                       True by default.
        :type     ex_disk_auto_delete: ``bool``

        :keyword  ex_service_accounts: Specify a list of serviceAccounts when
                                       creating the instance. The format is a
                                       list of dictionaries containing email
                                       and list of scopes, e.g.
                                       [{'email':'default',
                                         'scopes':['compute', ...]}, ...]
                                       Scopes can either be full URLs or short
                                       names. If not provided, use the
                                       'default' service account email and a
                                       scope of 'devstorage.read_only'. Also
                                       accepts the aliases defined in
                                       'gcloud compute'.
        :type     ex_service_accounts: ``list``

        :keyword  timeout: The number of seconds to wait for all nodes to be
                           created before timing out.
        :type     timeout: ``int``

        :keyword  description: The description of the node (instance).
        :type     description: ``str`` or ``None``

        :keyword  ex_can_ip_forward: Set to ``True`` to allow this node to
                                  send/receive non-matching src/dst packets.
        :type     ex_can_ip_forward: ``bool`` or ``None``

        :keyword  ex_disks_gce_struct: Support for passing in the GCE-specific
                                       formatted disks[] structure. No attempt
                                       is made to ensure proper formatting of
                                       the disks[] structure. Using this
                                       structure obviates the need of using
                                       other disk params like 'ex_boot_disk',
                                       etc. See the GCE docs for specific
                                       details.
        :type     ex_disks_gce_struct: ``list`` or ``None``

        :keyword  ex_nic_gce_struct: Support passing in the GCE-specific
                                     formatted networkInterfaces[] structure.
                                     No attempt is made to ensure proper
                                     formatting of the networkInterfaces[]
                                     data. Using this structure obviates the
                                     need of using 'external_ip' and
                                     'ex_network'.  See the GCE docs for
                                     details.
        :type     ex_nic_gce_struct: ``list`` or ``None``
n
        :keyword  ex_on_host_maintenance: Defines whether node should be
                                          terminated or migrated when host
                                          machine goes down. Acceptable values
                                          are: 'MIGRATE' or 'TERMINATE' (If
                                          not supplied, value will be reset to
                                          GCE default value for the instance
                                          type.)
        :type     ex_on_host_maintenance: ``str`` or ``None``

        :keyword  ex_automatic_restart: Defines whether the instance should be
                                        automatically restarted when it is
                                        terminated by Compute Engine. (If not
                                        supplied, value will be set to the GCE
                                        default value for the instance type.)
        :type     ex_automatic_restart: ``bool`` or ``None``

        :return:  A list of Node objects for the new nodes.
        :rtype:   ``list`` of :class:`Node`
        """
        location = location or self.zone
        if not hasattr(location, 'name'):
            location = self.ex_get_zone(location)
        if not hasattr(size, 'name'):
            size = self.ex_get_size(size, location)
        if not hasattr(ex_network, 'name'):
            ex_network = self.ex_get_network(ex_network)
        if image and not hasattr(image, 'name'):
            image = self.ex_get_image(image)
        if not hasattr(ex_disk_type, 'name'):
            ex_disk_type = self.ex_get_disktype(ex_disk_type, zone=location)

        node_attrs = {'size': size,
                      'image': image,
                      'location': location,
                      'network': ex_network,
                      'tags': ex_tags,
                      'metadata': ex_metadata,
                      'ignore_errors': ignore_errors,
                      'use_existing_disk': use_existing_disk,
                      'external_ip': external_ip,
                      'ex_disk_type': ex_disk_type,
                      'ex_disk_auto_delete': ex_disk_auto_delete,
                      'ex_service_accounts': ex_service_accounts,
                      'description': description,
                      'ex_can_ip_forward': ex_can_ip_forward,
                      'ex_disks_gce_struct': ex_disks_gce_struct,
                      'ex_nic_gce_struct': ex_nic_gce_struct,
                      'ex_on_host_maintenance': ex_on_host_maintenance,
                      'ex_automatic_restart': ex_automatic_restart}

        # List for holding the status information for disk/node creation.
        status_list = []

        for i in range(number):
            name = '%s-%03d' % (base_name, i)

            status = {'name': name,
                      'node_response': None,
                      'node': None,
                      'disk_response': None,
                      'disk': None}

            status_list.append(status)

        # Create disks for nodes
        for status in status_list:
            self._multi_create_disk(status, node_attrs)

        start_time = time.time()
        complete = False
        while not complete:
            if (time.time() - start_time >= timeout):
                raise Exception("Timeout (%s sec) while waiting for multiple "
                                "instances")
            complete = True
            time.sleep(poll_interval)
            for status in status_list:
                # If disk does not yet exist, check on its status
                if not status['disk']:
                    self._multi_check_disk(status, node_attrs)

                # If disk exists, but node does not, create the node or check
                # on its status if already in progress.
                if status['disk'] and not status['node']:
                    if not status['node_response']:
                        self._multi_create_node(status, node_attrs)
                    else:
                        self._multi_check_node(status, node_attrs)
                # If any of the nodes have not been created (or failed) we are
                # not done yet.
                if not status['node']:
                    complete = False

        # Return list of nodes
        node_list = []
        for status in status_list:
            node_list.append(status['node'])
        return node_list

    def ex_create_targethttpproxy(self, name, urlmap):
        """
        Create a target HTTP proxy.

        :param  name: Name of target HTTP proxy
        :type   name: ``str``

        :keyword  urlmap: URL map defining the mapping from URl to the
                           backendservice.
        :type     healthchecks: ``str`` or :class:`GCEUrlMap`

        :return:  Target Pool object
        :rtype:   :class:`GCETargetPool`
        """
        targetproxy_data = {'name': name}

        if not hasattr(urlmap, 'name'):
            urlmap = self.ex_get_urlmap(urlmap)
        targetproxy_data['urlMap'] = urlmap.extra['selfLink']

        request = '/global/targetHttpProxies'
        self.connection.async_request(request, method='POST',
                                      data=targetproxy_data)

        return self.ex_get_targethttpproxy(name)

    def ex_create_targetinstance(self, name, zone=None, node=None,
                                 description=None, nat_policy="NO_NAT"):
        """
        Create a target instance.

        :param  name: Name of target instance
        :type   name: ``str``

        :keyword  region: Zone to create the target pool in. Defaults to
                          self.zone
        :type     region: ``str`` or :class:`GCEZone` or ``None``

        :keyword  node: The actual instance to be used as the traffic target.
        :type     node: ``str`` or :class:`Node`

        :keyword  description: A text description for the target instance
        :type     description: ``str`` or ``None``

        :keyword  nat_policy: The NAT option for how IPs are NAT'd to the node.
        :type     nat_policy: ``str``

        :return:  Target Instance object
        :rtype:   :class:`GCETargetInstance`
        """
        zone = zone or self.zone
        targetinstance_data = {}
        targetinstance_data['name'] = name
        if not hasattr(zone, 'name'):
            zone = self.ex_get_zone(zone)
        targetinstance_data['zone'] = zone.extra['selfLink']
        if node is not None:
            if not hasattr(node, 'name'):
                node = self.ex_get_node(node, zone)
            targetinstance_data['instance'] = node.extra['selfLink']
        targetinstance_data['natPolicy'] = nat_policy
        if description:
            targetinstance_data['description'] = description

        request = '/zones/%s/targetInstances' % (zone.name)
        self.connection.async_request(request, method='POST',
                                      data=targetinstance_data)
        return self.ex_get_targetinstance(name, zone)

    def ex_create_targetpool(self, name, region=None, healthchecks=None,
                             nodes=None, session_affinity=None,
                             backup_pool=None, failover_ratio=None):
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

        :keyword  session_affinity:  Optional algorithm to use for session
                                     affinity.
        :type     session_affinity:  ``str``

        :keyword  backup_pool: Optional backup targetpool to take over traffic
                               if the failover_ratio is exceeded.
        :type     backup_pool: ``GCETargetPool`` or ``None``

        :keyword  failover_ratio: The percentage of healthy VMs must fall at
                                  or below this value before traffic will be
                                  sent to the backup_pool.
        :type     failover_ratio: :class:`GCETargetPool` or ``None``

        :return:  Target Pool object
        :rtype:   :class:`GCETargetPool`
        """
        targetpool_data = {}
        region = region or self.region
        if backup_pool and not failover_ratio:
            failover_ratio = 0.1
            targetpool_data['failoverRatio'] = failover_ratio
            targetpool_data['backupPool'] = backup_pool.extra['selfLink']
        if failover_ratio and not backup_pool:
            e = "Must supply a backup targetPool when setting failover_ratio"
            raise ValueError(e)
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
        if session_affinity:
            targetpool_data['sessionAffinity'] = session_affinity

        request = '/regions/%s/targetPools' % (region.name)

        self.connection.async_request(request, method='POST',
                                      data=targetpool_data)

        return self.ex_get_targetpool(name, region)

    def ex_create_urlmap(self, name, default_service):
        """
        Create a URL Map.

        :param  name: Name of the URL Map.
        :type   name: ``str``

        :keyword  default_service: Default backend service for the map.
        :type     default_service: ``str`` or :class:`GCEBackendService`

        :return:  URL Map object
        :rtype:   :class:`GCEUrlMap`
        """
        urlmap_data = {'name': name}

        # TODO: support hostRules, pathMatchers, tests
        if not hasattr(default_service, 'name'):
            default_service = self.ex_get_backendservice(default_service)
        urlmap_data['defaultService'] = default_service.extra['selfLink']

        request = '/global/urlMaps'
        self.connection.async_request(request, method='POST',
                                      data=urlmap_data)

        return self.ex_get_urlmap(name)

    def create_volume(self, size, name, location=None, snapshot=None,
                      image=None, use_existing=True,
                      ex_disk_type='pd-standard'):
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

        :keyword  snapshot: Snapshot to create image from
        :type     snapshot: :class:`GCESnapshot` or ``str`` or ``None``

        :keyword  image: Image to create disk from.
        :type     image: :class:`GCENodeImage` or ``str`` or ``None``

        :keyword  use_existing: If True and a disk with the given name already
                                exists, return an object for that disk instead
                                of attempting to create a new disk.
        :type     use_existing: ``bool``

        :keyword  ex_disk_type: Specify a pd-standard (default) disk or pd-ssd
                                for an SSD disk.
        :type     ex_disk_type: ``str`` or :class:`GCEDiskType`

        :return:  Storage Volume object
        :rtype:   :class:`StorageVolume`
        """
        request, volume_data, params = self._create_vol_req(
            size, name, location, snapshot, image, ex_disk_type)
        try:
            self.connection.async_request(request, method='POST',
                                          data=volume_data, params=params)
        except ResourceExistsError:
            e = sys.exc_info()[1]
            if not use_existing:
                raise e

        return self.ex_get_volume(name, location)

    def create_volume_snapshot(self, volume, name):
        """
        Create a snapshot of the provided Volume.

        :param  volume: A StorageVolume object
        :type   volume: :class:`StorageVolume`

        :return:  A GCE Snapshot object
        :rtype:   :class:`GCESnapshot`
        """
        snapshot_data = {}
        snapshot_data['name'] = name
        request = '/zones/%s/disks/%s/createSnapshot' % (
            volume.extra['zone'].name, volume.name)
        self.connection.async_request(request, method='POST',
                                      data=snapshot_data)

        return self.ex_get_snapshot(name)

    def list_volume_snapshots(self, volume):
        """
        List snapshots created from the provided volume.

        For GCE, snapshots are global, but while the volume they were
        created from still exists, the source disk for the snapshot is
        tracked.

        :param  volume: A StorageVolume object
        :type   volume: :class:`StorageVolume`

        :return:  A list of Snapshot objects
        :rtype:   ``list`` of :class:`GCESnapshot`
        """
        volume_snapshots = []
        volume_link = volume.extra['selfLink']
        all_snapshots = self.ex_list_snapshots()
        for snapshot in all_snapshots:
            if snapshot.extra['sourceDisk'] == volume_link:
                volume_snapshots.append(snapshot)
        return volume_snapshots

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
        if firewall.target_tags:
            firewall_data['targetTags'] = firewall.target_tags
        if firewall.extra['description']:
            firewall_data['description'] = firewall.extra['description']

        request = '/global/firewalls/%s' % (firewall.name)

        self.connection.async_request(request, method='PUT',
                                      data=firewall_data)

        return self.ex_get_firewall(firewall.name)

    def ex_targetpool_get_health(self, targetpool, node=None):
        """
        Return a hash of target pool instances and their health.

        :param  targetpool: Targetpool containing healthchecked instances.
        :type   targetpool: :class:`GCETargetPool`

        :param  node: Optional node to specify if only a specific node's
                      health status should be returned
        :type   node: ``str``, ``Node``, or ``None``

        :return: List of hashes of instances and their respective health,
                 e.g. [{'node': ``Node``, 'health': 'UNHEALTHY'}, ...]
        :rtype:  ``list`` of ``dict``
        """
        health = []
        region_name = targetpool.region.name
        request = '/regions/%s/targetPools/%s/getHealth' % (region_name,
                                                            targetpool.name)

        if node is not None:
            if hasattr(node, 'name'):
                node_name = node.name
            else:
                node_name = node

        nodes = targetpool.nodes
        for node_object in nodes:
            if node:
                if node_name == node_object.name:
                    body = {'instance': node_object.extra['selfLink']}
                    resp = self.connection.request(request, method='POST',
                                                   data=body).object
                    status = resp['healthStatus'][0]['healthState']
                    health.append({'node': node_object, 'health': status})
            else:
                body = {'instance': node_object.extra['selfLink']}
                resp = self.connection.request(request, method='POST',
                                               data=body).object
                status = resp['healthStatus'][0]['healthState']
                health.append({'node': node_object, 'health': status})
        return health

    def ex_targetpool_set_backup_targetpool(self, targetpool,
                                            backup_targetpool,
                                            failover_ratio=0.1):
        """
        Set a backup targetpool.

        :param  targetpool: The existing primary targetpool
        :type   targetpool: :class:`GCETargetPool`

        :param  backup_targetpool: The existing targetpool to use for
                                   failover traffic.
        :type   backup_targetpool: :class:`GCETargetPool`

        :param  failover_ratio: The percentage of healthy VMs must fall at or
                                below this value before traffic will be sent
                                to the backup targetpool (default 0.10)
        :type   failover_ratio: ``float``

        :return:  True if successful
        :rtype:   ``bool``
        """
        region = targetpool.region.name
        name = targetpool.name
        req_data = {'target': backup_targetpool.extra['selfLink']}
        params = {'failoverRatio': failover_ratio}

        request = '/regions/%s/targetPools/%s/setBackup' % (region, name)
        self.connection.async_request(request, method='POST', data=req_data,
                                      params=params)
        return True

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
        if hasattr(node, 'name'):
            node_uri = node.extra['selfLink']
        else:
            if node.startswith('https://'):
                node_uri = node
            else:
                node = self.ex_get_node(node, 'all')
                node_uri = node.extra['selfLink']

        targetpool_data = {'instances': [{'instance': node_uri}]}

        request = '/regions/%s/targetPools/%s/addInstance' % (
            targetpool.region.name, targetpool.name)
        self.connection.async_request(request, method='POST',
                                      data=targetpool_data)
        if all((node_uri != n) and
               (not hasattr(n, 'extra') or n.extra['selfLink'] != node_uri)
               for n in targetpool.nodes):
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

        targetpool_data = {
            'healthChecks': [{'healthCheck': healthcheck.extra['selfLink']}]
        }

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

        if hasattr(node, 'name'):
            node_uri = node.extra['selfLink']
        else:
            if node.startswith('https://'):
                node_uri = node
            else:
                node = self.ex_get_node(node, 'all')
                node_uri = node.extra['selfLink']

        targetpool_data = {'instances': [{'instance': node_uri}]}

        request = '/regions/%s/targetPools/%s/removeInstance' % (
            targetpool.region.name, targetpool.name)
        self.connection.async_request(request, method='POST',
                                      data=targetpool_data)
        # Remove node object from node list
        index = None
        for i, nd in enumerate(targetpool.nodes):
            if nd == node_uri or (hasattr(nd, 'extra') and
                                  nd.extra['selfLink'] == node_uri):
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

        targetpool_data = {
            'healthChecks': [{'healthCheck': healthcheck.extra['selfLink']}]
        }

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

    def ex_set_node_scheduling(self, node, on_host_maintenance=None,
                               automatic_restart=None):
        """Set the maintenance behavior for the node.

        See `Scheduling <https://developers.google.com/compute/
        docs/instances#onhostmaintenance>`_ documentation for more info.

        :param  node: Node object
        :type   node: :class:`Node`

        :keyword  on_host_maintenance: Defines whether node should be
                                       terminated or migrated when host machine
                                       goes down. Acceptable values are:
                                       'MIGRATE' or 'TERMINATE' (If not
                                       supplied, value will be reset to GCE
                                       default value for the instance type.)
        :type     on_host_maintenance: ``str``

        :keyword  automatic_restart: Defines whether the instance should be
                                     automatically restarted when it is
                                     terminated by Compute Engine. (If not
                                     supplied, value will be set to the GCE
                                     default value for the instance type.)
        :type     automatic_restart: ``bool``

        :return:  True if successful.
        :rtype:   ``bool``
        """
        if not hasattr(node, 'name'):
            node = self.ex_get_node(node, 'all')
        if on_host_maintenance is not None:
            on_host_maintenance = on_host_maintenance.upper()
            ohm_values = ['MIGRATE', 'TERMINATE']
            if on_host_maintenance not in ohm_values:
                raise ValueError('on_host_maintenance must be one of %s' %
                                 ','.join(ohm_values))

        request = '/zones/%s/instances/%s/setScheduling' % (
            node.extra['zone'].name, node.name)

        scheduling_data = {}
        if on_host_maintenance is not None:
            scheduling_data['onHostMaintenance'] = on_host_maintenance
        if automatic_restart is not None:
            scheduling_data['automaticRestart'] = automatic_restart

        self.connection.async_request(request, method='POST',
                                      data=scheduling_data)

        new_node = self.ex_get_node(node.name, node.extra['zone'])
        node.extra['scheduling'] = new_node.extra['scheduling']

        ohm = node.extra['scheduling'].get('onHostMaintenance')
        ar = node.extra['scheduling'].get('automaticRestart')

        success = True
        if on_host_maintenance not in [None, ohm]:
            success = False
        if automatic_restart not in [None, ar]:
            success = False

        return success

    def deploy_node(self, name, size, image, script, location=None,
                    ex_network='default', ex_tags=None,
                    ex_service_accounts=None):
        """
        Create a new node and run a script on start-up.

        :param  name: The name of the node to create.
        :type   name: ``str``

        :param  size: The machine type to use.
        :type   size: ``str`` or :class:`GCENodeSize`

        :param  image: The image to use to create the node.
        :type   image: ``str`` or :class:`GCENodeImage`

        :param  script: File path to start-up script
        :type   script: ``str``

        :keyword  location: The location (zone) to create the node in.
        :type     location: ``str`` or :class:`NodeLocation` or
                            :class:`GCEZone` or ``None``

        :keyword  ex_network: The network to associate with the node.
        :type     ex_network: ``str`` or :class:`GCENetwork`

        :keyword  ex_tags: A list of tags to associate with the node.
        :type     ex_tags: ``list`` of ``str`` or ``None``

        :keyword  ex_service_accounts: Specify a list of serviceAccounts when
                                       creating the instance. The format is a
                                       list of dictionaries containing email
                                       and list of scopes, e.g.
                                       [{'email':'default',
                                         'scopes':['compute', ...]}, ...]
                                       Scopes can either be full URLs or short
                                       names. If not provided, use the
                                       'default' service account email and a
                                       scope of 'devstorage.read_only'. Also
                                       accepts the aliases defined in
                                       'gcloud compute'.
        :type     ex_service_accounts: ``list``

        :return:  A Node object for the new node.
        :rtype:   :class:`Node`
        """
        with open(script, 'r') as f:
            script_data = f.read()
        # TODO(erjohnso): allow user defined metadata here...
        metadata = {'items': [{'key': 'startup-script',
                               'value': script_data}]}

        return self.create_node(name, size, image, location=location,
                                ex_network=ex_network, ex_tags=ex_tags,
                                ex_metadata=metadata,
                                ex_service_accounts=ex_service_accounts)

    def attach_volume(self, node, volume, device=None, ex_mode=None,
                      ex_boot=False, ex_type=None, ex_source=None,
                      ex_auto_delete=None, ex_initialize_params=None,
                      ex_licenses=None, ex_interface=None):
        """
        Attach a volume to a node.

        If volume is None, an ex_source URL must be provided.

        :param  node: The node to attach the volume to
        :type   node: :class:`Node` or ``None``

        :param  volume: The volume to attach.
        :type   volume: :class:`StorageVolume` or ``None``

        :keyword  device: The device name to attach the volume as. Defaults to
                          volume name.
        :type     device: ``str``

        :keyword  ex_mode: Either 'READ_WRITE' or 'READ_ONLY'
        :type     ex_mode: ``str``

        :keyword  ex_boot: If true, disk will be attached as a boot disk
        :type     ex_boot: ``bool``

        :keyword  ex_type: Specify either 'PERSISTENT' (default) or 'SCRATCH'.
        :type     ex_type: ``str``

        :keyword  ex_source: URL (full or partial) of disk source. Must be
                             present if not using an existing StorageVolume.
        :type     ex_source: ``str`` or ``None``

        :keyword  ex_auto_delete: If set, the disk will be auto-deleted
                                  if the parent node/instance is deleted.
        :type     ex_auto_delete: ``bool`` or ``None``

        :keyword  ex_initialize_params: Allow user to pass in full JSON
                                        struct of `initializeParams` as
                                        documented in GCE's API.
        :type     ex_initialize_params: ``dict`` or ``None``

        :keyword  ex_licenses: List of strings representing licenses
                               associated with the volume/disk.
        :type     ex_licenses: ``list`` of ``str``

        :keyword  ex_interface: User can specify either 'SCSI' (default) or
                                'NVME'.
        :type     ex_interface: ``str`` or ``None``

        :return:  True if successful
        :rtype:   ``bool``
        """
        if volume is None and ex_source is None:
            raise ValueError("Must supply either a StorageVolume or "
                             "set `ex_source` URL for an existing disk.")
        if volume is None and device is None:
            raise ValueError("Must supply either a StorageVolume or "
                             "set `device` name.")

        volume_data = {}
        if ex_source:
            volume_data['source'] = ex_source
        if ex_initialize_params:
            volume_data['initialzeParams'] = ex_initialize_params
        if ex_licenses:
            volume_data['licenses'] = ex_licenses
        if ex_interface:
            volume_data['interface'] = ex_interface
        if ex_type:
            volume_data['type'] = ex_type

        volume_data['source'] = ex_source or volume.extra['selfLink']
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

    def ex_set_volume_auto_delete(self, volume, node, auto_delete=True):
        """
        Sets the auto-delete flag for a volume attached to a node.

        :param  volume: Volume object to auto-delete
        :type   volume: :class:`StorageVolume`

        :param   ex_node: Node object to auto-delete volume from
        :type    ex_node: :class:`Node`

        :keyword auto_delete: Flag to set for the auto-delete value
        :type    auto_delete: ``bool`` (default True)

        :return:  True if successful
        :rtype:   ``bool``
        """
        request = '/zones/%s/instances/%s/setDiskAutoDelete' % (
            node.extra['zone'].name, node.name
        )
        delete_params = {
            'deviceName': volume.name,
            'autoDelete': auto_delete,
        }
        self.connection.async_request(request, method='POST',
                                      params=delete_params)
        return True

    def ex_destroy_address(self, address):
        """
        Destroy a static address.

        :param  address: Address object to destroy
        :type   address: ``str`` or :class:`GCEAddress`

        :return:  True if successful
        :rtype:   ``bool``
        """
        if not hasattr(address, 'name'):
            address = self.ex_get_address(address)

        if hasattr(address.region, 'name'):
            request = '/regions/%s/addresses/%s' % (address.region.name,
                                                    address.name)
        else:
            request = '/global/addresses/%s' % (address.name)

        self.connection.async_request(request, method='DELETE')
        return True

    def ex_destroy_backendservice(self, backendservice):
        """
        Destroy a Backend Service.

        :param  backendservice: BackendService object to destroy
        :type   backendservice: :class:`GCEBackendService`

        :return:  True if successful
        :rtype:   ``bool``
        """
        request = '/global/backendServices/%s' % backendservice.name

        self.connection.async_request(request, method='DELETE')
        return True

    def ex_delete_image(self, image):
        """
        Delete a specific image resource.

        :param  image: Image object to delete
        :type   image: ``str`` or :class:`GCENodeImage`

        :return: True if successful
        :rtype:  ``bool``
        """
        if not hasattr(image, 'name'):
            image = self.ex_get_image(image)

        request = '/global/images/%s' % (image.name)
        self.connection.async_request(request, method='DELETE')
        return True

    def ex_deprecate_image(self, image, replacement, state=None,
                           deprecated=None, obsolete=None, deleted=None):
        """
        Deprecate a specific image resource.

        :param  image: Image object to deprecate
        :type   image: ``str`` or :class: `GCENodeImage`

        :param  replacement: Image object to use as a replacement
        :type   replacement: ``str`` or :class: `GCENodeImage`

        :param  state: State of the image
        :type   state: ``str``

        :param  deprecated: RFC3339 timestamp to mark DEPRECATED
        :type   deprecated: ``str`` or ``None``

        :param  obsolete: RFC3339 timestamp to mark OBSOLETE
        :type   obsolete: ``str`` or ``None``

        :param  deleted: RFC3339 timestamp to mark DELETED
        :type   deleted: ``str`` or ``None``

        :return: True if successful
        :rtype:  ``bool``
        """
        if not hasattr(image, 'name'):
            image = self.ex_get_image(image)

        if not hasattr(replacement, 'name'):
            replacement = self.ex_get_image(replacement)

        if state is None:
            state = 'DEPRECATED'

        possible_states = ['DELETED', 'DEPRECATED', 'OBSOLETE']

        if state not in possible_states:
            raise ValueError('state must be one of %s'
                             % ','.join(possible_states))

        image_data = {
            'state': state,
            'replacement': replacement.extra['selfLink'],
        }

        for attribute, value in [('deprecated', deprecated),
                                 ('obsolete', obsolete),
                                 ('deleted', deleted)]:
            if value is None:
                continue

            try:
                timestamp_to_datetime(value)
            except:
                raise ValueError('%s must be an RFC3339 timestamp' % attribute)
            image_data[attribute] = value

        request = '/global/images/%s/deprecate' % (image.name)

        self.connection.request(
            request, method='POST', data=image_data).object

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
        if forwarding_rule.region:
            request = '/regions/%s/forwardingRules/%s' % (
                forwarding_rule.region.name, forwarding_rule.name)
        else:
            request = '/global/forwardingRules/%s' % forwarding_rule.name
        self.connection.async_request(request, method='DELETE')
        return True

    def ex_destroy_route(self, route):
        """
        Destroy a route.

        :param  route: Route object to destroy
        :type   route: :class:`GCERoute`

        :return:  True if successful
        :rtype:   ``bool``
        """
        request = '/global/routes/%s' % (route.name)
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

    def ex_start_node(self, node):
        """
        Start a node that is stopped and in TERMINATED state.

        :param  node: Node object to start
        :type   node: :class:`Node`

        :return:  True if successful
        :rtype:   ``bool``
        """
        request = '/zones/%s/instances/%s/start' % (node.extra['zone'].name,
                                                    node.name)
        self.connection.async_request(request, method='POST')
        return True

    def ex_stop_node(self, node):
        """
        Stop a running node.

        :param  node: Node object to stop
        :type   node: :class:`Node`

        :return:  True if successful
        :rtype:   ``bool``
        """
        request = '/zones/%s/instances/%s/stop' % (node.extra['zone'].name,
                                                   node.name)
        self.connection.async_request(request, method='POST')
        return True

    def destroy_node(self, node, destroy_boot_disk=False):
        """
        Destroy a node.

        :param  node: Node object to destroy
        :type   node: :class:`Node`

        :keyword  destroy_boot_disk: If true, also destroy the node's
                                     boot disk. (Note that this keyword is not
                                     accessible from the node's .destroy()
                                     method.)
        :type     destroy_boot_disk: ``bool``

        :return:  True if successful
        :rtype:   ``bool``
        """
        request = '/zones/%s/instances/%s' % (node.extra['zone'].name,
                                              node.name)
        self.connection.async_request(request, method='DELETE')
        if destroy_boot_disk and node.extra['boot_disk']:
            node.extra['boot_disk'].destroy()
        return True

    def ex_destroy_multiple_nodes(self, node_list, ignore_errors=True,
                                  destroy_boot_disk=False, poll_interval=2,
                                  timeout=DEFAULT_TASK_COMPLETION_TIMEOUT):
        """
        Destroy multiple nodes at once.

        :param  node_list: List of nodes to destroy
        :type   node_list: ``list`` of :class:`Node`

        :keyword  ignore_errors: If true, don't raise an exception if one or
                                 more nodes fails to be destroyed.
        :type     ignore_errors: ``bool``

        :keyword  destroy_boot_disk: If true, also destroy the nodes' boot
                                     disks.
        :type     destroy_boot_disk: ``bool``

        :keyword  poll_interval: Number of seconds between status checks.
        :type     poll_interval: ``int``

        :keyword  timeout: Number of seconds to wait for all nodes to be
                           destroyed.
        :type     timeout: ``int``

        :return:  A list of boolean values.  One for each node.  True means
                  that the node was successfully destroyed.
        :rtype:   ``list`` of ``bool``
        """
        status_list = []
        complete = False
        start_time = time.time()
        for node in node_list:
            request = '/zones/%s/instances/%s' % (node.extra['zone'].name,
                                                  node.name)
            try:
                response = self.connection.request(request,
                                                   method='DELETE').object
            except GoogleBaseError:
                self._catch_error(ignore_errors=ignore_errors)
                response = None

            status = {'node': node,
                      'node_success': False,
                      'node_response': response,
                      'disk_success': not destroy_boot_disk,
                      'disk_response': None}

            status_list.append(status)

        while not complete:
            if (time.time() - start_time >= timeout):
                raise Exception("Timeout (%s sec) while waiting to delete "
                                "multiple instances")
            complete = True
            for status in status_list:
                # If one of the operations is running, check the status
                operation = status['node_response'] or status['disk_response']
                delete_disk = False
                if operation:
                    no_errors = True
                    try:
                        response = self.connection.request(
                            operation['selfLink']).object
                    except GoogleBaseError:
                        self._catch_error(ignore_errors=ignore_errors)
                        no_errors = False
                        response = {'status': 'DONE'}
                    if response['status'] == 'DONE':
                        # If a node was deleted, update status and indicate
                        # that the disk is ready to be deleted.
                        if status['node_response']:
                            status['node_response'] = None
                            status['node_success'] = no_errors
                            delete_disk = True
                        else:
                            status['disk_response'] = None
                            status['disk_success'] = no_errors
                # If we are destroying disks, and the node has been deleted,
                # destroy the disk.
                if delete_disk and destroy_boot_disk:
                    boot_disk = status['node'].extra['boot_disk']
                    if boot_disk:
                        request = '/zones/%s/disks/%s' % (
                            boot_disk.extra['zone'].name, boot_disk.name)
                        try:
                            response = self.connection.request(
                                request, method='DELETE').object
                        except GoogleBaseError:
                            self._catch_error(ignore_errors=ignore_errors)
                            no_errors = False
                            response = None
                        status['disk_response'] = response
                    else:  # If there is no boot disk, ignore
                        status['disk_success'] = True
                operation = status['node_response'] or status['disk_response']
                if operation:
                    time.sleep(poll_interval)
                    complete = False

        success = []
        for status in status_list:
            s = status['node_success'] and status['disk_success']
            success.append(s)
        return success

    def ex_destroy_targethttpproxy(self, targethttpproxy):
        """
        Destroy a target HTTP proxy.

        :param  targethttpproxy: TargetHttpProxy object to destroy
        :type   targethttpproxy: :class:`GCETargetHttpProxy`

        :return:  True if successful
        :rtype:   ``bool``
        """
        request = '/global/targetHttpProxies/%s' % targethttpproxy.name
        self.connection.async_request(request, method='DELETE')
        return True

    def ex_destroy_targetinstance(self, targetinstance):
        """
        Destroy a target instance.

        :param  targetinstance: TargetInstance object to destroy
        :type   targetinstance: :class:`GCETargetInstance`

        :return:  True if successful
        :rtype:   ``bool``
        """
        request = '/zones/%s/targetInstances/%s' % (targetinstance.zone.name,
                                                    targetinstance.name)
        self.connection.async_request(request, method='DELETE')
        return True

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

    def ex_destroy_urlmap(self, urlmap):
        """
        Destroy a URL map.

        :param  urlmap: UrlMap object to destroy
        :type   urlmap: :class:`GCEUrlMap`

        :return:  True if successful
        :rtype:   ``bool``
        """
        request = '/global/urlMaps/%s' % urlmap.name

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
        self.connection.async_request(request, method='DELETE')
        return True

    def destroy_volume_snapshot(self, snapshot):
        """
        Destroy a snapshot.

        :param  snapshot: Snapshot object to destroy
        :type   snapshot: :class:`GCESnapshot`

        :return:  True if successful
        :rtype:   ``bool``
        """
        request = '/global/snapshots/%s' % (snapshot.name)
        self.connection.async_request(request, method='DELETE')
        return True

    def ex_get_license(self, project, name):
        """
        Return a License object for specified project and name.

        :param  name: The project to reference when looking up the license.
        :type   name: ``str``

        :param  name: The name of the License
        :type   name: ``str``

        :return:  A DiskType object for the name
        :rtype:   :class:`GCEDiskType`
        """
        saved_request_path = self.connection.request_path
        new_request_path = saved_request_path.replace(self.project, project)
        self.connection.request_path = new_request_path

        request = '/global/licenses/%s' % (name)
        response = self.connection.request(request, method='GET').object
        self.connection.request_path = saved_request_path

        return self._to_license(response)

    def ex_get_disktype(self, name, zone=None):
        """
        Return a DiskType object based on a name and optional zone.

        :param  name: The name of the DiskType
        :type   name: ``str``

        :keyword  zone: The zone to search for the DiskType in (set to
                          'all' to search all zones)
        :type     zone: ``str`` :class:`GCEZone` or ``None``

        :return:  A DiskType object for the name
        :rtype:   :class:`GCEDiskType`
        """
        zone = self._set_zone(zone)
        request = '/zones/%s/diskTypes/%s' % (zone.name, name)
        response = self.connection.request(request, method='GET').object
        return self._to_disktype(response)

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
        if region == 'global':
            request = '/global/addresses/%s' % (name)
        else:
            region = self._set_region(region) or self._find_zone_or_region(
                name, 'addresses', region=True, res_name='Address')
            request = '/regions/%s/addresses/%s' % (region.name, name)
        response = self.connection.request(request, method='GET').object
        return self._to_address(response)

    def ex_get_backendservice(self, name):
        """
        Return a Backend Service object based on name

        :param  name: The name of the backend service
        :type   name: ``str``

        :return:  A BackendService object for the backend service
        :rtype:   :class:`GCEBackendService`
        """
        request = '/global/backendServices/%s' % name
        response = self.connection.request(request, method='GET').object
        return self._to_backendservice(response)

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

    def ex_get_forwarding_rule(self, name, region=None, global_rule=False):
        """
        Return a Forwarding Rule object based on the forwarding rule name.

        :param  name: The name of the forwarding rule
        :type   name: ``str``

        :keyword  region: The region to search for the rule in (set to 'all'
                          to search all regions).
        :type     region: ``str`` or ``None``

        :keyword  global_rule: Set to True to get a global forwarding rule.
                                Region will be ignored if True.
        :type     global_rule: ``bool``

        :return:  A GCEForwardingRule object
        :rtype:   :class:`GCEForwardingRule`
        """
        if global_rule:
            request = '/global/forwardingRules/%s' % name
        else:
            region = self._set_region(region) or self._find_zone_or_region(
                name, 'forwardingRules', region=True,
                res_name='ForwardingRule')
            request = '/regions/%s/forwardingRules/%s' % (region.name, name)

        response = self.connection.request(request, method='GET').object
        return self._to_forwarding_rule(response)

    def ex_get_image(self, partial_name, ex_project_list=None):
        """
        Return an GCENodeImage object based on the name or link provided.

        :param  partial_name: The name, partial name, or full path of a GCE
                              image.
        :type   partial_name: ``str``

        :return:  GCENodeImage object based on provided information or None if
                  an image with that name is not found.
        :rtype:   :class:`GCENodeImage` or raise ``ResourceNotFoundError``
        """
        if partial_name.startswith('https://'):
            response = self.connection.request(partial_name, method='GET')
            return self._to_node_image(response.object)
        image = self._match_images(ex_project_list, partial_name)
        if not image:
            for img_proj, short_list in self.IMAGE_PROJECTS.items():
                for short_name in short_list:
                    if partial_name.startswith(short_name):
                        image = self._match_images(img_proj, partial_name)

        if not image:
            raise ResourceNotFoundError('Could not find image \'%s\'' % (
                                        partial_name), None, None)
        return image

    def ex_get_route(self, name):
        """
        Return a Route object based on a route name.

        :param  name: The name of the route
        :type   name: ``str``

        :return:  A Route object for the named route
        :rtype:   :class:`GCERoute`
        """
        request = '/global/routes/%s' % (name)
        response = self.connection.request(request, method='GET').object
        return self._to_route(response)

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

    def ex_get_snapshot(self, name):
        """
        Return a Snapshot object based on snapshot name.

        :param  name: The name of the snapshot
        :type   name: ``str``

        :return:  A GCESnapshot object for the snapshot
        :rtype:   :class:`GCESnapshot`
        """
        request = '/global/snapshots/%s' % (name)
        response = self.connection.request(request, method='GET').object
        return self._to_snapshot(response)

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

    def ex_get_targethttpproxy(self, name):
        """
        Return a Target HTTP Proxy object based on its name.

        :param  name: The name of the target HTTP proxy.
        :type   name: ``str``

        :return:  A Target HTTP Proxy object for the pool
        :rtype:   :class:`GCETargetHttpProxy`
        """
        request = '/global/targetHttpProxies/%s' % name
        response = self.connection.request(request, method='GET').object
        return self._to_targethttpproxy(response)

    def ex_get_targetinstance(self, name, zone=None):
        """
        Return a TargetInstance object based on a name and optional zone.

        :param  name: The name of the target instance
        :type   name: ``str``

        :keyword  zone: The zone to search for the target instance in (set to
                          'all' to search all zones).
        :type     zone: ``str`` or :class:`GCEZone` or ``None``

        :return:  A TargetInstance object for the instance
        :rtype:   :class:`GCETargetInstance`
        """
        zone = self._set_zone(zone) or self._find_zone_or_region(
            name, 'targetInstances', res_name='TargetInstance')
        request = '/zones/%s/targetInstances/%s' % (zone.name, name)
        response = self.connection.request(request, method='GET').object
        return self._to_targetinstance(response)

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

    def ex_get_urlmap(self, name):
        """
        Return a URL Map object based on name

        :param  name: The name of the url map
        :type   name: ``str``

        :return:  A URL Map object for the backend service
        :rtype:   :class:`GCEUrlMap`
        """
        request = '/global/urlMaps/%s' % name
        response = self.connection.request(request, method='GET').object
        return self._to_urlmap(response)

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

    def ex_copy_image(self, name, url, description=None):
        """
        Copy an image to your image collection.

        :param  name: The name of the image
        :type   name: ``str``

        :param  url: The URL to the image. The URL can start with `gs://`
        :param  url: ``str``

        :param  description: The description of the image
        :type   description: ``str``

        :return:  NodeImage object based on provided information or None if an
                  image with that name is not found.
        :rtype:   :class:`NodeImage` or ``None``
        """

        # the URL for an image can start with gs://
        if url.startswith('gs://'):
            url = url.replace('gs://', 'https://storage.googleapis.com/', 1)

        image_data = {
            'name': name,
            'description': description,
            'sourceType': 'RAW',
            'rawDisk': {
                'source': url,
            },
        }

        request = '/global/images'
        self.connection.async_request(request, method='POST',
                                      data=image_data)
        return self.ex_get_image(name)

    def _ex_connection_class_kwargs(self):
        return {'auth_type': self.auth_type,
                'project': self.project,
                'scopes': self.scopes,
                'credential_file': self.credential_file}

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
        :rtype:   ``dict``
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

    def _get_object_by_kind(self, url):
        """
        Fetch a resource and return its object representation by mapping its
        'kind' parameter to the appropriate class.  Returns ``None`` if url is
        ``None``

        :param  url: fully qualified URL of the resource to request from GCE
        :type   url: ``str``

        :return:  Object representation of the requested resource.
        "rtype:   :class:`object` or ``None``
        """
        if not url:
            return None

        # Relies on GoogleBaseConnection.morph_action_hook to rewrite
        # the URL to a request
        response = self.connection.request(url, method='GET').object
        return GCENodeDriver.KIND_METHOD_MAP[response['kind']](self, response)

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

        :return:  The latest image object that matches the partial name or None
                  if no matching image is found.
        :rtype:   :class:`GCENodeImage` or ``None``
        """
        project_images = self.list_images(ex_project=project,
                                          ex_include_deprecated=True)
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

    def _create_node_req(self, name, size, image, location, network=None,
                         tags=None, metadata=None, boot_disk=None,
                         external_ip='ephemeral', ex_disk_type='pd-standard',
                         ex_disk_auto_delete=True, ex_service_accounts=None,
                         description=None, ex_can_ip_forward=None,
                         ex_disks_gce_struct=None, ex_nic_gce_struct=None,
                         ex_on_host_maintenance=None,
                         ex_automatic_restart=None):
        """
        Returns a request and body to create a new node.  This is a helper
        method to support both :class:`create_node` and
        :class:`ex_create_multiple_nodes`.

        :param  name: The name of the node to create.
        :type   name: ``str``

        :param  size: The machine type to use.
        :type   size: :class:`GCENodeSize`

        :param  image: The image to use to create the node (or, if using a
                       persistent disk, the image the disk was created from).
        :type   image: :class:`GCENodeImage` or ``None``

        :param  location: The location (zone) to create the node in.
        :type   location: :class:`NodeLocation` or :class:`GCEZone`

        :param  network: The network to associate with the node.
        :type   network: :class:`GCENetwork`

        :keyword  tags: A list of tags to associate with the node.
        :type     tags: ``list`` of ``str``

        :keyword  metadata: Metadata dictionary for instance.
        :type     metadata: ``dict``

        :keyword  boot_disk: Persistent boot disk to attach.
        :type     :class:`StorageVolume` or ``None``

        :keyword  external_ip: The external IP address to use.  If 'ephemeral'
                               (default), a new non-static address will be
                               used.  If 'None', then no external address will
                               be used.  To use an existing static IP address,
                               a GCEAddress object should be passed in. This
                               param will be ignored if also using the
                               ex_nic_gce_struct param.
        :type     external_ip: :class:`GCEAddress` or ``str`` or None

        :keyword  ex_disk_type: Specify a pd-standard (default) disk or pd-ssd
                                for an SSD disk.
        :type     ex_disk_type: ``str`` or :class:`GCEDiskType` or ``None``

        :keyword  ex_disk_auto_delete: Indicate that the boot disk should be
                                       deleted when the Node is deleted. Set to
                                       True by default.
        :type     ex_disk_auto_delete: ``bool``

        :keyword  ex_service_accounts: Specify a list of serviceAccounts when
                                       creating the instance. The format is a
                                       list of dictionaries containing email
                                       and list of scopes, e.g.
                                       [{'email':'default',
                                         'scopes':['compute', ...]}, ...]
                                       Scopes can either be full URLs or short
                                       names. If not provided, use the
                                       'default' service account email and a
                                       scope of 'devstorage.read_only'. Also
                                       accepts the aliases defined in
                                       'gcloud compute'.
        :type     ex_service_accounts: ``list``

        :keyword  description: The description of the node (instance).
        :type     description: ``str`` or ``None``

        :keyword  ex_can_ip_forward: Set to ``True`` to allow this node to
                                  send/receive non-matching src/dst packets.
        :type     ex_can_ip_forward: ``bool`` or ``None``

        :keyword  ex_disks_gce_struct: Support for passing in the GCE-specific
                                       formatted disks[] structure. No attempt
                                       is made to ensure proper formatting of
                                       the disks[] structure. Using this
                                       structure obviates the need of using
                                       other disk params like 'boot_disk',
                                       etc. See the GCE docs for specific
                                       details.
        :type     ex_disks_gce_struct: ``list`` or ``None``

        :keyword  ex_nic_gce_struct: Support passing in the GCE-specific
                                     formatted networkInterfaces[] structure.
                                     No attempt is made to ensure proper
                                     formatting of the networkInterfaces[]
                                     data. Using this structure obviates the
                                     need of using 'external_ip' and
                                     'ex_network'.  See the GCE docs for
                                     details.
        :type     ex_nic_gce_struct: ``list`` or ``None``
n
        :keyword  ex_on_host_maintenance: Defines whether node should be
                                          terminated or migrated when host
                                          machine goes down. Acceptable values
                                          are: 'MIGRATE' or 'TERMINATE' (If
                                          not supplied, value will be reset to
                                          GCE default value for the instance
                                          type.)
        :type     ex_on_host_maintenance: ``str`` or ``None``

        :keyword  ex_automatic_restart: Defines whether the instance should be
                                        automatically restarted when it is
                                        terminated by Compute Engine. (If not
                                        supplied, value will be set to the GCE
                                        default value for the instance type.)
        :type     ex_automatic_restart: ``bool`` or ``None``

        :return:  A tuple containing a request string and a node_data dict.
        :rtype:   ``tuple`` of ``str`` and ``dict``
        """
        node_data = {}
        node_data['machineType'] = size.extra['selfLink']
        node_data['name'] = name
        if tags:
            node_data['tags'] = {'items': tags}
        if metadata:
            node_data['metadata'] = self._format_metadata(fingerprint='na',
                                                          metadata=metadata)

        # by default, new instances will match the same serviceAccount and
        # scope set in the Developers Console and Cloud SDK
        if not ex_service_accounts:
            set_scopes = [{
                'email': 'default',
                'scopes': [self.AUTH_URL + 'devstorage.read_only']
            }]
        elif not isinstance(ex_service_accounts, list):
            raise ValueError("ex_service_accounts field is not a list.")
        else:
            set_scopes = []
            for sa in ex_service_accounts:
                if not isinstance(sa, dict):
                    raise ValueError("ex_service_accounts needs to be a list "
                                     "of dicts, got: '%s - %s'" % (
                                         str(type(sa)), str(sa)))
                if 'email' not in sa:
                    sa['email'] = 'default'
                if 'scopes' not in sa:
                    sa['scopes'] = [self.AUTH_URL + 'devstorage.read_only']
                ps = []
                for scope in sa['scopes']:
                    if scope.startswith(self.AUTH_URL):
                        ps.append(scope)
                    elif scope in self.SA_SCOPES_MAP:
                        ps.append(self.AUTH_URL + self.SA_SCOPES_MAP[scope])
                    else:
                        ps.append(self.AUTH_URL + scope)
                sa['scopes'] = ps
                set_scopes.append(sa)
        node_data['serviceAccounts'] = set_scopes

        if boot_disk and ex_disks_gce_struct:
            raise ValueError("Cannot specify both 'boot_disk' and "
                             "'ex_disks_gce_struct'. Use one or the other.")

        if not image and not boot_disk and not ex_disks_gce_struct:
            raise ValueError("Missing root device or image. Must specify an "
                             "'image', existing 'boot_disk', or use the "
                             "'ex_disks_gce_struct'.")

        if boot_disk:
            if not isinstance(ex_disk_auto_delete, bool):
                raise ValueError("ex_disk_auto_delete field is not a bool.")
            disks = [{'boot': True,
                      'type': 'PERSISTENT',
                      'mode': 'READ_WRITE',
                      'deviceName': boot_disk.name,
                      'autoDelete': ex_disk_auto_delete,
                      'zone': boot_disk.extra['zone'].extra['selfLink'],
                      'source': boot_disk.extra['selfLink']}]
            node_data['disks'] = disks

        if ex_disks_gce_struct:
            node_data['disks'] = ex_disks_gce_struct

        if ex_nic_gce_struct is not None:
            if hasattr(external_ip, 'address'):
                raise ValueError("Cannot specify both a static IP address "
                                 "and 'ex_nic_gce_struct'. Use one or the "
                                 "other.")
            if hasattr(network, 'name'):
                if network.name == 'default':
                    # assume this is just the default value from create_node()
                    # and since the user specified ex_nic_gce_struct, the
                    # struct should take precedence
                    network = None
                else:
                    raise ValueError("Cannot specify both 'network' and "
                                     "'ex_nic_gce_struct'. Use one or the "
                                     "other.")

        if network:
            ni = [{'kind': 'compute#instanceNetworkInterface',
                   'network': network.extra['selfLink']}]
            if external_ip:
                access_configs = [{'name': 'External NAT',
                                   'type': 'ONE_TO_ONE_NAT'}]
                if hasattr(external_ip, 'address'):
                    access_configs[0]['natIP'] = external_ip.address
                ni[0]['accessConfigs'] = access_configs
        else:
            ni = ex_nic_gce_struct
        node_data['networkInterfaces'] = ni

        if description:
            node_data['description'] = str(description)
        if ex_can_ip_forward:
            node_data['canIpForward'] = True
        scheduling = {}
        if ex_on_host_maintenance:
            if isinstance(ex_on_host_maintenance, str) and \
                    ex_on_host_maintenance in ['MIGRATE', 'TERMINATE']:
                scheduling['onHostMaintenance'] = ex_on_host_maintenance
            else:
                scheduling['onHostMaintenance'] = 'MIGRATE'
        if ex_automatic_restart is not None:
            scheduling['automaticRestart'] = ex_automatic_restart
        if scheduling:
            node_data['scheduling'] = scheduling

        request = '/zones/%s/instances' % (location.name)
        return request, node_data

    def _multi_create_disk(self, status, node_attrs):
        """Create disk for ex_create_multiple_nodes.

        :param  status: Dictionary for holding node/disk creation status.
                        (This dictionary is modified by this method)
        :type   status: ``dict``

        :param  node_attrs: Dictionary for holding node attribute information.
                            (size, image, location, ex_disk_type, etc.)
        :type   node_attrs: ``dict``
        """
        disk = None
        # Check for existing disk
        if node_attrs['use_existing_disk']:
            try:
                disk = self.ex_get_volume(status['name'],
                                          node_attrs['location'])
            except ResourceNotFoundError:
                pass

        if disk:
            status['disk'] = disk
        else:
            # Create disk and return response object back in the status dict.
            # Or, if there is an error, mark as failed.
            disk_req, disk_data, disk_params = self._create_vol_req(
                None, status['name'], location=node_attrs['location'],
                image=node_attrs['image'],
                ex_disk_type=node_attrs['ex_disk_type'])
            try:
                disk_res = self.connection.request(
                    disk_req, method='POST', data=disk_data,
                    params=disk_params).object
            except GoogleBaseError:
                e = self._catch_error(
                    ignore_errors=node_attrs['ignore_errors'])
                error = e.value
                code = e.code
                disk_res = None
                status['disk'] = GCEFailedDisk(status['name'],
                                               error, code)
            status['disk_response'] = disk_res

    def _multi_check_disk(self, status, node_attrs):
        """Check disk status for ex_create_multiple_nodes.

        :param  status: Dictionary for holding node/disk creation status.
                        (This dictionary is modified by this method)
        :type   status: ``dict``

        :param  node_attrs: Dictionary for holding node attribute information.
                            (size, image, location, etc.)
        :type   node_attrs: ``dict``
        """
        error = None
        try:
            response = self.connection.request(
                status['disk_response']['selfLink']).object
        except GoogleBaseError:
            e = self._catch_error(ignore_errors=node_attrs['ignore_errors'])
            error = e.value
            code = e.code
            response = {'status': 'DONE'}
        if response['status'] == 'DONE':
            status['disk_response'] = None
            if error:
                status['disk'] = GCEFailedDisk(status['name'], error, code)
            else:
                status['disk'] = self.ex_get_volume(status['name'],
                                                    node_attrs['location'])

    def _multi_create_node(self, status, node_attrs):
        """Create node for ex_create_multiple_nodes.

        :param  status: Dictionary for holding node/disk creation status.
                        (This dictionary is modified by this method)
        :type   status: ``dict``

        :param  node_attrs: Dictionary for holding node attribute information.
                            (size, image, location, etc.)
        :type   node_attrs: ``dict``
        """
        # If disk has an error, set the node as failed and return
        if hasattr(status['disk'], 'error'):
            status['node'] = status['disk']
            return

        # Create node and return response object in status dictionary.
        # Or, if there is an error, mark as failed.
        request, node_data = self._create_node_req(
            status['name'], node_attrs['size'], node_attrs['image'],
            node_attrs['location'], node_attrs['network'], node_attrs['tags'],
            node_attrs['metadata'],
            external_ip=node_attrs['external_ip'],
            ex_service_accounts=node_attrs['ex_service_accounts'],
            description=node_attrs['description'],
            ex_can_ip_forward=node_attrs['ex_can_ip_forward'],
            ex_disks_gce_struct=node_attrs['ex_disks_gce_struct'],
            ex_nic_gce_struct=node_attrs['ex_nic_gce_struct'],
            ex_on_host_maintenance=node_attrs['ex_on_host_maintenance'],
            ex_automatic_restart=node_attrs['ex_automatic_restart'])

        try:
            node_res = self.connection.request(
                request, method='POST', data=node_data).object
        except GoogleBaseError:
            e = self._catch_error(ignore_errors=node_attrs['ignore_errors'])
            error = e.value
            code = e.code
            node_res = None
            status['node'] = GCEFailedNode(status['name'],
                                           error, code)
        status['node_response'] = node_res

    def _multi_check_node(self, status, node_attrs):
        """Check node status for ex_create_multiple_nodes.

        :param  status: Dictionary for holding node/disk creation status.
                        (This dictionary is modified by this method)
        :type   status: ``dict``

        :param  node_attrs: Dictionary for holding node attribute information.
                            (size, image, location, etc.)
        :type   node_attrs: ``dict``
        """
        error = None
        try:
            response = self.connection.request(
                status['node_response']['selfLink']).object
        except GoogleBaseError:
            e = self._catch_error(ignore_errors=node_attrs['ignore_errors'])
            error = e.value
            code = e.code
            response = {'status': 'DONE'}
        if response['status'] == 'DONE':
            status['node_response'] = None
        if error:
            status['node'] = GCEFailedNode(status['name'],
                                           error, code)
        else:
            status['node'] = self.ex_get_node(status['name'],
                                              node_attrs['location'])

    def _create_vol_req(self, size, name, location=None, snapshot=None,
                        image=None, ex_disk_type='pd-standard'):
        """
        Assemble the request/data for creating a volume.

        Used by create_volume and ex_create_multiple_nodes

        :param  size: Size of volume to create (in GB). Can be None if image
                      or snapshot is supplied.
        :type   size: ``int`` or ``str`` or ``None``

        :param  name: Name of volume to create
        :type   name: ``str``

        :keyword  location: Location (zone) to create the volume in
        :type     location: ``str`` or :class:`GCEZone` or
                            :class:`NodeLocation` or ``None``

        :keyword  snapshot: Snapshot to create image from
        :type     snapshot: :class:`GCESnapshot` or ``str`` or ``None``

        :keyword  image: Image to create disk from.
        :type     image: :class:`GCENodeImage` or ``str`` or ``None``

        :keyword  ex_disk_type: Specify pd-standard (default) or pd-ssd
        :type     ex_disk_type: ``str`` or :class:`GCEDiskType`

        :return:  Tuple containing the request string, the data dictionary and
                  the URL parameters
        :rtype:   ``tuple``
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
            if not hasattr(snapshot, 'name'):
                # Check for full URI to not break backward-compatibility
                if snapshot.startswith('https'):
                    snapshot = self._get_components_from_path(snapshot)['name']
                snapshot = self.ex_get_snapshot(snapshot)
            snapshot_link = snapshot.extra['selfLink']
            volume_data['sourceSnapshot'] = snapshot_link
            volume_data['description'] = 'Snapshot: %s' % (snapshot_link)
        location = location or self.zone
        if not hasattr(location, 'name'):
            location = self.ex_get_zone(location)
        if hasattr(ex_disk_type, 'name'):
            volume_data['type'] = ex_disk_type.extra['selfLink']
        elif ex_disk_type.startswith('https'):
            volume_data['type'] = ex_disk_type
        else:
            volume_data['type'] = 'https://www.googleapis.com/compute/'
            volume_data['type'] += '%s/projects/%s/zones/%s/diskTypes/%s' % (
                API_VERSION, self.project, location.name, ex_disk_type)
        request = '/zones/%s/disks' % (location.name)

        return request, volume_data, params

    def _to_disktype(self, disktype):
        """
        Return a DiskType object from the JSON-response dictionary.

        :param  disktype: The dictionary describing the disktype.
        :type   disktype: ``dict``

        :return: DiskType object
        :rtype: :class:`GCEDiskType`
        """
        extra = {}

        zone = self.ex_get_zone(disktype['zone'])

        extra['selfLink'] = disktype.get('selfLink')
        extra['creationTimestamp'] = disktype.get('creationTimestamp')
        extra['description'] = disktype.get('description')
        extra['valid_disk_size'] = disktype.get('validDiskSize')
        extra['default_disk_size_gb'] = disktype.get('defaultDiskSizeGb')
        type_id = "%s:%s" % (zone.name, disktype['name'])

        return GCEDiskType(id=type_id, name=disktype['name'],
                           zone=zone, driver=self, extra=extra)

    def _to_address(self, address):
        """
        Return an Address object from the JSON-response dictionary.

        :param  address: The dictionary describing the address.
        :type   address: ``dict``

        :return: Address object
        :rtype: :class:`GCEAddress`
        """
        extra = {}

        if 'region' in address:
            region = self.ex_get_region(address['region'])
        else:
            region = 'global'

        extra['selfLink'] = address.get('selfLink')
        extra['status'] = address.get('status')
        extra['description'] = address.get('description', None)
        if address.get('users', None) is not None:
            extra['users'] = address.get('users')
        extra['creationTimestamp'] = address.get('creationTimestamp')

        return GCEAddress(id=address['id'], name=address['name'],
                          address=address['address'],
                          region=region, driver=self, extra=extra)

    def _to_backendservice(self, backendservice):
        """
        Return a Backend Service object from the JSON-response dictionary.

        :param  backendservice: The dictionary describing the backend service.
        :type   backendservice: ``dict``

        :return: BackendService object
        :rtype: :class:`GCEBackendService`
        """
        extra = {}

        for extra_key in ('selfLink', 'creationTimestamp', 'fingerprint',
                          'description'):
            extra[extra_key] = backendservice.get(extra_key)

        backends = backendservice.get('backends', [])
        healthchecks = [self._get_object_by_kind(h) for h in
                        backendservice.get('healthChecks', [])]

        return GCEBackendService(id=backendservice['id'],
                                 name=backendservice['name'],
                                 backends=backends,
                                 healthchecks=healthchecks,
                                 port=backendservice['port'],
                                 port_name=backendservice['portName'],
                                 protocol=backendservice['protocol'],
                                 timeout=backendservice['timeoutSec'],
                                 driver=self, extra=extra)

    def _to_healthcheck(self, healthcheck):
        """
        Return a HealthCheck object from the JSON-response dictionary.

        :param  healthcheck: The dictionary describing the healthcheck.
        :type   healthcheck: ``dict``

        :return: HealthCheck object
        :rtype: :class:`GCEHealthCheck`
        """
        extra = {}
        extra['selfLink'] = healthcheck.get('selfLink')
        extra['creationTimestamp'] = healthcheck.get('creationTimestamp')
        extra['description'] = healthcheck.get('description')
        extra['host'] = healthcheck.get('host')

        return GCEHealthCheck(
            id=healthcheck['id'], name=healthcheck['name'],
            path=healthcheck.get('requestPath'), port=healthcheck.get('port'),
            interval=healthcheck.get('checkIntervalSec'),
            timeout=healthcheck.get('timeoutSec'),
            unhealthy_threshold=healthcheck.get('unhealthyThreshold'),
            healthy_threshold=healthcheck.get('healthyThreshold'),
            driver=self, extra=extra)

    def _to_firewall(self, firewall):
        """
        Return a Firewall object from the JSON-response dictionary.

        :param  firewall: The dictionary describing the firewall.
        :type   firewall: ``dict``

        :return: Firewall object
        :rtype: :class:`GCEFirewall`
        """
        extra = {}
        extra['selfLink'] = firewall.get('selfLink')
        extra['creationTimestamp'] = firewall.get('creationTimestamp')
        extra['description'] = firewall.get('description')
        extra['network_name'] = self._get_components_from_path(
            firewall['network'])['name']

        network = self.ex_get_network(extra['network_name'])
        source_ranges = firewall.get('sourceRanges')
        source_tags = firewall.get('sourceTags')
        target_tags = firewall.get('targetTags')

        return GCEFirewall(id=firewall['id'], name=firewall['name'],
                           allowed=firewall.get('allowed'), network=network,
                           source_ranges=source_ranges,
                           source_tags=source_tags,
                           target_tags=target_tags,
                           driver=self, extra=extra)

    def _to_forwarding_rule(self, forwarding_rule):
        """
        Return a Forwarding Rule object from the JSON-response dictionary.

        :param  forwarding_rule: The dictionary describing the rule.
        :type   forwarding_rule: ``dict``

        :return: ForwardingRule object
        :rtype: :class:`GCEForwardingRule`
        """
        extra = {}
        extra['selfLink'] = forwarding_rule.get('selfLink')
        extra['portRange'] = forwarding_rule.get('portRange')
        extra['creationTimestamp'] = forwarding_rule.get('creationTimestamp')
        extra['description'] = forwarding_rule.get('description')

        region = forwarding_rule.get('region')
        if region:
            region = self.ex_get_region(region)
        target = self._get_object_by_kind(forwarding_rule['target'])

        return GCEForwardingRule(id=forwarding_rule['id'],
                                 name=forwarding_rule['name'], region=region,
                                 address=forwarding_rule.get('IPAddress'),
                                 protocol=forwarding_rule.get('IPProtocol'),
                                 targetpool=target, driver=self, extra=extra)

    def _to_network(self, network):
        """
        Return a Network object from the JSON-response dictionary.

        :param  network: The dictionary describing the network.
        :type   network: ``dict``

        :return: Network object
        :rtype: :class:`GCENetwork`
        """
        extra = {}

        extra['selfLink'] = network.get('selfLink')
        extra['gatewayIPv4'] = network.get('gatewayIPv4')
        extra['description'] = network.get('description')
        extra['creationTimestamp'] = network.get('creationTimestamp')

        return GCENetwork(id=network['id'], name=network['name'],
                          cidr=network.get('IPv4Range'),
                          driver=self, extra=extra)

    def _to_route(self, route):
        """
        Return a Route object from the JSON-response dictionary.

        :param  route: The dictionary describing the route.
        :type   route: ``dict``

        :return: Route object
        :rtype: :class:`GCERoute`
        """
        extra = {}

        extra['selfLink'] = route.get('selfLink')
        extra['description'] = route.get('description')
        extra['creationTimestamp'] = route.get('creationTimestamp')
        network = route.get('network')
        priority = route.get('priority')

        if 'nextHopInstance' in route:
            extra['nextHopInstance'] = route['nextHopInstance']
        if 'nextHopIp' in route:
            extra['nextHopIp'] = route['nextHopIp']
        if 'nextHopNetwork' in route:
            extra['nextHopNetwork'] = route['nextHopNetwork']
        if 'nextHopGateway' in route:
            extra['nextHopGateway'] = route['nextHopGateway']
        if 'warnings' in route:
            extra['warnings'] = route['warnings']

        return GCERoute(id=route['id'], name=route['name'],
                        dest_range=route.get('destRange'), priority=priority,
                        network=network, tags=route.get('tags'),
                        driver=self, extra=extra)

    def _to_node_image(self, image):
        """
        Return an Image object from the JSON-response dictionary.

        :param  image: The dictionary describing the image.
        :type   image: ``dict``

        :return: Image object
        :rtype: :class:`GCENodeImage`
        """
        extra = {}
        if 'preferredKernel' in image:
            extra['preferredKernel'] = image.get('preferredKernel', None)
        extra['description'] = image.get('description', None)
        extra['creationTimestamp'] = image.get('creationTimestamp')
        extra['selfLink'] = image.get('selfLink')
        if 'deprecated' in image:
            extra['deprecated'] = image.get('deprecated', None)
        extra['sourceType'] = image.get('sourceType', None)
        extra['rawDisk'] = image.get('rawDisk', None)
        extra['status'] = image.get('status', None)
        extra['archiveSizeBytes'] = image.get('archiveSizeBytes', None)
        extra['diskSizeGb'] = image.get('diskSizeGb', None)
        if 'sourceDisk' in image:
            extra['sourceDisk'] = image.get('sourceDisk', None)
        if 'sourceDiskId' in image:
            extra['sourceDiskId'] = image.get('sourceDiskId', None)
        if 'licenses' in image:
            lic_objs = self._licenses_from_urls(licenses=image['licenses'])
            extra['licenses'] = lic_objs

        return GCENodeImage(id=image['id'], name=image['name'], driver=self,
                            extra=extra)

    def _to_node_location(self, location):
        """
        Return a Location object from the JSON-response dictionary.

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
        Return a Node object from the JSON-response dictionary.

        :param  node: The dictionary describing the node.
        :type   node: ``dict``

        :return: Node object
        :rtype: :class:`Node`
        """
        public_ips = []
        private_ips = []
        extra = {}

        extra['status'] = node.get('status', "UNKNOWN")
        extra['statusMessage'] = node.get('statusMessage')
        extra['description'] = node.get('description')
        extra['zone'] = self.ex_get_zone(node['zone'])
        extra['image'] = node.get('image')
        extra['machineType'] = node.get('machineType')
        extra['disks'] = node.get('disks', [])
        extra['networkInterfaces'] = node.get('networkInterfaces')
        extra['id'] = node['id']
        extra['selfLink'] = node.get('selfLink')
        extra['kind'] = node.get('kind')
        extra['creationTimestamp'] = node.get('creationTimestamp')
        extra['name'] = node['name']
        extra['metadata'] = node.get('metadata', {})
        extra['tags_fingerprint'] = node['tags']['fingerprint']
        extra['scheduling'] = node.get('scheduling', {})
        extra['deprecated'] = True if node.get('deprecated', None) else False
        extra['canIpForward'] = node.get('canIpForward')
        extra['serviceAccounts'] = node.get('serviceAccounts', [])
        extra['scheduling'] = node.get('scheduling', {})
        extra['boot_disk'] = None

        for disk in extra['disks']:
            if disk.get('boot') and disk.get('type') == 'PERSISTENT':
                bd = self._get_components_from_path(disk['source'])
                extra['boot_disk'] = self.ex_get_volume(bd['name'], bd['zone'])

        if 'items' in node['tags']:
            tags = node['tags']['items']
        else:
            tags = []
        extra['tags'] = tags

        for network_interface in node.get('networkInterfaces', []):
            private_ips.append(network_interface.get('networkIP'))
            for access_config in network_interface.get('accessConfigs', []):
                public_ips.append(access_config.get('natIP'))

        # For the node attributes, use just machine and image names, not full
        # paths.  Full paths are available in the "extra" dict.
        image = None
        if extra['image']:
            image = self._get_components_from_path(extra['image'])['name']
        else:
            if extra['boot_disk'] and \
                    hasattr(extra['boot_disk'], 'extra') and \
                    'sourceImage' in extra['boot_disk'].extra and \
                    extra['boot_disk'].extra['sourceImage'] is not None:
                src_image = extra['boot_disk'].extra['sourceImage']
                image = self._get_components_from_path(src_image)['name']
            extra['image'] = image
        size = self._get_components_from_path(node['machineType'])['name']

        return Node(id=node['id'], name=node['name'],
                    state=self.NODE_STATE_MAP[node['status']],
                    public_ips=public_ips, private_ips=private_ips,
                    driver=self, size=size, image=image, extra=extra)

    def _to_node_size(self, machine_type):
        """
        Return a Size object from the JSON-response dictionary.

        :param  machine_type: The dictionary describing the machine.
        :type   machine_type: ``dict``

        :return: Size object
        :rtype: :class:`GCENodeSize`
        """
        extra = {}
        extra['selfLink'] = machine_type.get('selfLink')
        extra['zone'] = self.ex_get_zone(machine_type['zone'])
        extra['description'] = machine_type.get('description')
        extra['guestCpus'] = machine_type.get('guestCpus')
        extra['creationTimestamp'] = machine_type.get('creationTimestamp')
        try:
            price = self._get_size_price(size_id=machine_type['name'])
        except KeyError:
            price = None

        return GCENodeSize(id=machine_type['id'], name=machine_type['name'],
                           ram=machine_type.get('memoryMb'),
                           disk=machine_type.get('imageSpaceGb'),
                           bandwidth=0, price=price, driver=self, extra=extra)

    def _to_project(self, project):
        """
        Return a Project object from the JSON-response dictionary.

        :param  project: The dictionary describing the project.
        :type   project: ``dict``

        :return: Project object
        :rtype: :class:`GCEProject`
        """
        extra = {}
        extra['selfLink'] = project.get('selfLink')
        extra['creationTimestamp'] = project.get('creationTimestamp')
        extra['description'] = project.get('description')
        metadata = project['commonInstanceMetadata'].get('items')
        if 'commonInstanceMetadata' in project:
            # add this struct to get 'fingerprint' too
            extra['commonInstanceMetadata'] = project['commonInstanceMetadata']
        if 'usageExportLocation' in project:
            extra['usageExportLocation'] = project['usageExportLocation']

        return GCEProject(id=project['id'], name=project['name'],
                          metadata=metadata, quotas=project.get('quotas'),
                          driver=self, extra=extra)

    def _to_region(self, region):
        """
        Return a Region object from the JSON-response dictionary.

        :param  region: The dictionary describing the region.
        :type   region: ``dict``

        :return: Region object
        :rtype: :class:`GCERegion`
        """
        extra = {}
        extra['selfLink'] = region.get('selfLink')
        extra['creationTimestamp'] = region.get('creationTimestamp')
        extra['description'] = region.get('description')

        quotas = region.get('quotas')
        zones = [self.ex_get_zone(z) for z in region.get('zones', [])]
        # Work around a bug that will occasionally list missing zones in the
        # region output
        zones = [z for z in zones if z is not None]
        deprecated = region.get('deprecated')

        return GCERegion(id=region['id'], name=region['name'],
                         status=region.get('status'), zones=zones,
                         quotas=quotas, deprecated=deprecated,
                         driver=self, extra=extra)

    def _to_snapshot(self, snapshot):
        """
        Return a Snapshot object from the JSON-response dictionary.

        :param  snapshot: The dictionary describing the snapshot
        :type   snapshot: ``dict``

        :return:  Snapshot object
        :rtype:   :class:`VolumeSnapshot`
        """
        extra = {}
        extra['selfLink'] = snapshot.get('selfLink')
        extra['creationTimestamp'] = snapshot.get('creationTimestamp')
        extra['sourceDisk'] = snapshot.get('sourceDisk')
        if 'description' in snapshot:
            extra['description'] = snapshot['description']
        if 'sourceDiskId' in snapshot:
            extra['sourceDiskId'] = snapshot['sourceDiskId']
        if 'storageBytes' in snapshot:
            extra['storageBytes'] = snapshot['storageBytes']
        if 'storageBytesStatus' in snapshot:
            extra['storageBytesStatus'] = snapshot['storageBytesStatus']
        if 'licenses' in snapshot:
            lic_objs = self._licenses_from_urls(licenses=snapshot['licenses'])
            extra['licenses'] = lic_objs

        try:
            created = parse_date(snapshot.get('creationTimestamp'))
        except ValueError:
            created = None

        return GCESnapshot(id=snapshot['id'], name=snapshot['name'],
                           size=snapshot['diskSizeGb'],
                           status=snapshot.get('status'), driver=self,
                           extra=extra, created=created)

    def _to_storage_volume(self, volume):
        """
        Return a Volume object from the JSON-response dictionary.

        :param  volume: The dictionary describing the volume.
        :type   volume: ``dict``

        :return: Volume object
        :rtype: :class:`StorageVolume`
        """
        extra = {}
        extra['selfLink'] = volume.get('selfLink')
        extra['zone'] = self.ex_get_zone(volume['zone'])
        extra['status'] = volume.get('status')
        extra['creationTimestamp'] = volume.get('creationTimestamp')
        extra['description'] = volume.get('description')
        extra['sourceImage'] = volume.get('sourceImage')
        extra['sourceImageId'] = volume.get('sourceImageId')
        extra['sourceSnapshot'] = volume.get('sourceSnapshot')
        extra['sourceSnapshotId'] = volume.get('sourceSnapshotId')
        extra['options'] = volume.get('options')
        if 'licenses' in volume:
            lic_objs = self._licenses_from_urls(licenses=volume['licenses'])
            extra['licenses'] = lic_objs

        extra['type'] = volume.get('type', 'pd-standard').split('/')[-1]

        return StorageVolume(id=volume['id'], name=volume['name'],
                             size=volume['sizeGb'], driver=self, extra=extra)

    def _to_targethttpproxy(self, targethttpproxy):
        """
        Return a Target HTTP Proxy object from the JSON-response dictionary.

        :param  targethttpproxy: The dictionary describing the proxy.
        :type   targethttpproxy: ``dict``

        :return: Target HTTP Proxy object
        :rtype:  :class:`GCETargetHttpProxy`
        """
        extra = dict([(k, targethttpproxy.get(k)) for k in (
            'creationTimestamp', 'description', 'selfLink')])

        urlmap = self._get_object_by_kind(targethttpproxy.get('urlMap'))

        return GCETargetHttpProxy(id=targethttpproxy['id'],
                                  name=targethttpproxy['name'],
                                  urlmap=urlmap, driver=self, extra=extra)

    def _to_targetinstance(self, targetinstance):
        """
        Return a Target Instance object from the JSON-response dictionary.

        :param  targetinstance: The dictionary describing the target instance.
        :type   targetinstance: ``dict``

        :return: Target Instance object
        :rtype:  :class:`GCETargetInstance`
        """
        node = None
        extra = {}
        extra['selfLink'] = targetinstance.get('selfLink')
        extra['description'] = targetinstance.get('description')
        extra['natPolicy'] = targetinstance.get('natPolicy')
        zone = self.ex_get_zone(targetinstance['zone'])
        if 'instance' in targetinstance:
            node_name = targetinstance['instance'].split('/')[-1]
            try:
                node = self.ex_get_node(node_name, zone)
            except ResourceNotFoundError:
                node = targetinstance['instance']

        return GCETargetInstance(id=targetinstance['id'],
                                 name=targetinstance['name'], zone=zone,
                                 node=node, driver=self, extra=extra)

    def _to_targetpool(self, targetpool):
        """
        Return a Target Pool object from the JSON-response dictionary.

        :param  targetpool: The dictionary describing the volume.
        :type   targetpool: ``dict``

        :return: Target Pool object
        :rtype:  :class:`GCETargetPool`
        """
        extra = {}
        extra['selfLink'] = targetpool.get('selfLink')
        extra['description'] = targetpool.get('description')
        extra['sessionAffinity'] = targetpool.get('sessionAffinity')
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

        if 'failoverRatio' in targetpool:
            extra['failoverRatio'] = targetpool['failoverRatio']
        if 'backupPool' in targetpool:
            tp_split = targetpool['backupPool'].split('/')
            extra['backupPool'] = self.ex_get_targetpool(tp_split[10],
                                                         tp_split[8])

        return GCETargetPool(id=targetpool['id'], name=targetpool['name'],
                             region=region, healthchecks=healthcheck_list,
                             nodes=node_list, driver=self, extra=extra)

    def _format_metadata(self, fingerprint, metadata=None):
        """
        Convert various data formats into the metadata format expected by
        Google Compute Engine and suitable for passing along to the API. Can
        accept the following formats:

          (a) [{'key': 'k1', 'value': 'v1'}, ...]
          (b) [{'k1': 'v1'}, ...]
          (c) {'key': 'k1', 'value': 'v1'}
          (d) {'k1': 'v1', 'k2': v2', ...}
          (e) {'items': [...]}       # does not check for valid list contents

        The return value is a 'dict' that GCE expects, e.g.

          {'fingerprint': 'xx...',
           'items': [{'key': 'key1', 'value': 'val1'},
                     {'key': 'key2', 'value': 'val2'},
                     ...,
                    ]
          }

        :param  fingerprint: Current metadata fingerprint
        :type   fingerprint: ``str``

        :param  metadata: Variety of input formats.
        :type   metadata: ``list``, ``dict``, or ``None``

        :return: GCE-friendly metadata dict
        :rtype:  ``dict``
        """
        if not metadata:
            return {'fingerprint': fingerprint, 'items': []}
        md = {'fingerprint': fingerprint}

        # Check `list` format. Can support / convert the following:
        # (a) [{'key': 'k1', 'value': 'v1'}, ...]
        # (b) [{'k1': 'v1'}, ...]
        if isinstance(metadata, list):
            item_list = []
            for i in metadata:
                if isinstance(i, dict):
                    # check (a)
                    if 'key' in i and 'value' in i and len(i) == 2:
                        item_list.append(i)
                    # check (b)
                    elif len(i) == 1:
                        item_list.append({'key': list(i.keys())[0],
                                          'value': list(i.values())[0]})
                    else:
                        raise ValueError("Unsupported metadata format.")
                else:
                    raise ValueError("Unsupported metadata format.")
            md['items'] = item_list

        # Check `dict` format. Can support / convert the following:
        # (c) {'key': 'k1', 'value': 'v1'}
        # (d) {'k1': 'v1', 'k2': 'v2', ...}
        # (e) {'items': [...]}
        if isinstance(metadata, dict):
            # Check (c)
            if 'key' in metadata and 'value' in metadata and \
                    len(metadata) == 2:
                md['items'] = [metadata]
            # check (d)
            elif len(metadata) == 1:
                if 'items' in metadata:
                    # check (e)
                    if isinstance(metadata['items'], list):
                        md['items'] = metadata['items']
                    else:
                        raise ValueError("Unsupported metadata format.")
                else:
                    md['items'] = [{'key': list(metadata.keys())[0],
                                   'value': list(metadata.values())[0]}]
            else:
                # check (d)
                md['items'] = []
                for k, v in metadata.items():
                    md['items'].append({'key': k, 'value': v})

        if 'items' not in md:
            raise ValueError("Unsupported metadata format.")
        return md

    def _to_urlmap(self, urlmap):
        """
        Return a UrlMap object from the JSON-response dictionary.

        :param  zone: The dictionary describing the url-map.
        :type   zone: ``dict``

        :return: Zone object
        :rtype: :class:`GCEUrlMap`
        """
        extra = dict([(k, urlmap.get(k)) for k in (
            'creationTimestamp', 'description', 'fingerprint', 'selfLink')])

        default_service = self._get_object_by_kind(
            urlmap.get('defaultService'))

        host_rules = urlmap.get('hostRules', [])
        path_matchers = urlmap.get('pathMatchers', [])
        tests = urlmap.get('tests', [])

        return GCEUrlMap(id=urlmap['id'], name=urlmap['name'],
                         default_service=default_service,
                         host_rules=host_rules, path_matchers=path_matchers,
                         tests=tests, driver=self, extra=extra)

    def _to_zone(self, zone):
        """
        Return a Zone object from the JSON-response dictionary.

        :param  zone: The dictionary describing the zone.
        :type   zone: ``dict``

        :return: Zone object
        :rtype: :class:`GCEZone`
        """
        extra = {}
        extra['selfLink'] = zone.get('selfLink')
        extra['creationTimestamp'] = zone.get('creationTimestamp')
        extra['description'] = zone.get('description')
        extra['region'] = zone.get('region')

        deprecated = zone.get('deprecated')

        return GCEZone(id=zone['id'], name=zone['name'], status=zone['status'],
                       maintenance_windows=zone.get('maintenanceWindows'),
                       deprecated=deprecated, driver=self, extra=extra)

    def _to_license(self, license):
        """
        Return a License object from the JSON-response dictionary.

        :param  license: The dictionary describing the license.
        :type   license: ``dict``

        :return: License object
        :rtype: :class:`GCELicense`
        """
        extra = {}
        extra['selfLink'] = license.get('selfLink')
        extra['kind'] = license.get('kind')

        return GCELicense(id=license['name'], name=license['name'],
                          charges_use_fee=license['chargesUseFee'],
                          driver=self, extra=extra)

    def _set_project_metadata(self, metadata=None, force=False,
                              current_keys=""):
        """
        Return the GCE-friendly dictionary of metadata with/without an
        entry for 'sshKeys' based on params for 'force' and 'current_keys'.
        This method was added to simplify the set_common_instance_metadata
        method and make it easier to test.

        :param  metadata: The GCE-formatted dict (e.g. 'items' list of dicts)
        :type   metadata: ``dict`` or ``None``

        :param  force: Flag to specify user preference for keeping current_keys
        :type   force: ``bool``

        :param  current_keys: The value, if any, of existing 'sshKeys'
        :type   current_keys: ``str``

        :return: GCE-friendly metadata dict
        :rtype:  ``dict``
        """
        if metadata is None:
            # User wants to delete metdata, but if 'force' is False
            # and we already have sshKeys, we should retain them.
            # Otherwise, delete ALL THE THINGS!
            if not force and current_keys:
                new_md = [{'key': 'sshKeys', 'value': current_keys}]
            else:
                new_md = []
        else:
            # User is providing new metadata. If 'force' is False, they
            # want to preserve existing sshKeys, otherwise 'force' is True
            # and the user wants to add/replace sshKeys.
            new_md = metadata['items']
            if not force and current_keys:
                # not sure how duplicate keys would be resolved, so ensure
                # existing 'sshKeys' entry is removed.
                updated_md = []
                for d in new_md:
                    if d['key'] != 'sshKeys':
                        updated_md.append({'key': d['key'],
                                          'value': d['value']})
                new_md = updated_md
                new_md.append({'key': 'sshKeys', 'value': current_keys})
        return new_md

    def _licenses_from_urls(self, licenses):
        """
        Convert a list of license selfLinks into a list of :class:`GCELicense`
        objects.

        :param  licenses: A list of GCE license selfLink URLs.
        :type   licenses: ``list`` of ``str``

        :return: List of :class:`GCELicense` objects.
        :rtype:  ``list``
        """
        return_list = []
        for license in licenses:
            selfLink_parts = license.split('/')
            lic_proj = selfLink_parts[6]
            lic_name = selfLink_parts[-1]
            return_list.append(self.ex_get_license(project=lic_proj,
                                                   name=lic_name))
        return return_list

    KIND_METHOD_MAP = {
        'compute#address': _to_address,
        'compute#backendService': _to_backendservice,
        'compute#disk': _to_storage_volume,
        'compute#firewall': _to_firewall,
        'compute#forwardingRule': _to_forwarding_rule,
        'compute#httpHealthCheck': _to_healthcheck,
        'compute#image': _to_node_image,
        'compute#instance': _to_node,
        'compute#machineType': _to_node_size,
        'compute#network': _to_network,
        'compute#project': _to_project,
        'compute#region': _to_region,
        'compute#snapshot': _to_snapshot,
        'compute#targetHttpProxy': _to_targethttpproxy,
        'compute#targetInstance': _to_targetinstance,
        'compute#targetPool': _to_targetpool,
        'compute#urlMap': _to_urlmap,
        'compute#zone': _to_zone,
    }
