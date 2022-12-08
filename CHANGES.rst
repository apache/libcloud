Changelog
=========

Changes in Apache Libcloud in development
-----------------------------------------

Common
~~~~~~

- Support for Python 3.6 which has been EOL for more than a year now has been
  removed.

  If you still want to use Libcloud with Python 3.6, you should use an older
  release which still supports Python 3.6.
  (GITHUB-1611)

Compute
~~~~~~~

- [CloudSigma] Update API URLs for US locations.
  (GITHUB-1781)
  [Mohsen Hassani - @ mohsen-hassani-cs]

- [GCP] Fix OAuth2 desktop client login.
  (GITHUB-1806, GITHUB-1807)
  [Veith Röthlingshöfer - @RunOrVeith]

Other
~~~~~

- Also run unit tests under Python 3.11 on CI/CD and indicate we also support
  Python 3.11.
  (GITHUB-1818)

Changes in Apache Libcloud 3.6.1
--------------------------------

Common
~~~~~~

- [OpenStack] Fix OpenStack Identitiy bug when auth url contains a path.

  (GITHUB-1717, GITHUB-1718)
  [Dimitris Galanis - @dimgal1]


- Update EC2 price scraping script to utilize official pricing API endpoint.

  Pricing file has also been updated to include latest EC2 pricing data.

  Complete raw pricing data file size has grown by ~1 MB (from ~2 MB to
  ~3 MB).

  By default when requesting pricing data we only cache pricing data in memory
  for used / requested drivers so a slight memory increase due to the pricing
  file size increase will only affect users who utilize pricing related
  functionality in the EC2 driver.

  (GITHUB-1715)
  [Eis D. Zaster - @Eis-D-Z]

Compute
~~~~~~~

- [EC2] Update ``list_images()`` method to better handle scenario when an image
  doesn't contain ``creationDate`` attribute (previously the code would throw if
  an image without ``creationDate`` was encountered).

  Reported by Juan Marcos Caicedo Mejía  - @juanmarcosdev.

  (GITHUB-1700, GITHUB-1701)
  [Tomaz Muraus - @Kami]

- [Azure ARM] Allow user to create volume / disks in specific zone by passing
  ``ex_zones`` argument to the ``create_volume()`` method.

  Also add new ``ex_sku_name`` and remove ``ex_account_type`` argument from
  that method.

  Also change ``DISK_API_VERSION`` version from ``2016-04-30-preview`` to
  ``2018-06-01``. This is needed to be able to support those changes. Code
  has been updated to handle slightly different response format for the
  volume API operations.

  (GITHUB-1736)
  [Palash Gandhi - @palashgandhi]

- [GCE] Add improved support for retrieving GCE image pricing data using
  ``libcloud.pricing.get_image_price("gce_images", ...)`` method.

  Existing way of retrieving image pricing using
  ``libcloud.pricing.get_pricing("compute", "gce_images")`` method continues to
  work.

  (GITHUB-1699)
  [Eis D. Zaster - @Eis-D-Z]

- [Azure ARM] Add new ``ex_create_additional_capabilities()`` method which allows
  user to set capabilities on a stopped node. This allows users to utilize ultra
  SSDs and similar.

  Also add support for new ``ex_iops`` and ``ex_throughput`` argument to the
  ``create_volume()`` method.

  (GITHUB-1744)
  [John Wren Kennedy - @jwk404]

Storage
~~~~~~~

- [Azure Blobs] Fix ``get_container()`` method and make sure Container ``etag``
  extra attribute contains the correct scheme (https or http), depending on the
  used endpoint.

  (GITHUB-1703, GITHUB-1712)
  [@KatiRG]

- [Azure Blobs] Fix `list_containers()`` method and make sure Container ``etag``
  extra attribute doesn't contain unncessary double quotes around the value
  (``"0x8CFBAB7B5B82D8E"`` -> ``0x8CFBAB7B5B82D8E``).

  (GITHUB-1712)
  [Tomaz Muraus - @Kami]

- [OVH] Add new driver for OVH Storage based on the S3 compatible storage
  endpoints.

  (GITHUB-1732)
  [Olivier Picquenot - @pcqnt]

Other / Development
~~~~~--------------

- All the imports in the code have been re-organized / sorted using the ``isort``
  library.

  Going forward, consistent import ordering will be automatically enforced
  using ``isort`` check on the CI.

  Developers can run the isort check locally using
  ``tox -e <isort|isort-check>`` command.

  (GITHUB-1761)
  [Tomaz Muraus - @Kami]

- Fix black config (``pyproject.toml``) and ensure max line length is correctly
  set to 100 characters everywhere.

  Also re-format code with this fixed / updated config option.

  (GITHUB-1761)
  [Tomaz Muraus - @Kami]

- Code has been reformatted using pyupgrade and Python 3.6 higher compatible
  syntax.

  (GITHUB-1765)
  [Tomaz Muraus - @Kami]

Changes in Apache Libcloud 3.6.0
--------------------------------

Compute
~~~~~~~

- [OpenStack] Fix error attaching/detaching a Floating IP to an OpenStack node
  when `ex_force_microversion` is set with 2.44 or newer microversion.

  (GITHUB-1674)
  [Miguel Caballer - @micafer]

- [OpenStack] Error in volume api calls if microversion is set in OpenStack.
  In previous version if `ex_force_microversion` is set, it is assumed to set
  it to the compute service. Now if only a version is set `2.67`, compute
  service is assumed but it can be also set the service name `volume 3.21`.

  (GITHUB-1675)
  [Miguel Caballer - @micafer]

- [OpenStack] Fix error creating and getting node in OpenStack when
  ex_force_microversion is set to a version newer than 2.47.

  (GITHUB-1672)
  [Miguel Caballer - @micafer]

- [EC2] Add support for new ``af-south-1`` region.
  (GITHUB-1688)
  [Balazs Baranyi - @balazsbaranyi]

- [SSH] Update deploy node and ParamikoSSHClient related code so it works
  with paramiko >= 2.9.0 and older OpenSSH server versions which doesn't
  support SHA-2 variants of RSA key verification algorithm.

  paramiko v2.9.0 introduced a change to prefer SHA-2 variants of RSA key
  verification algorithm. With this version paramiko would fail to connect
  to older OpenSSH servers which don't support this algorithm (e.g. default
  setup on Ubuntu 14.04) and throw authentication error.

  The code has been updated to be backward compatible. It first tries to
  connect to the server using default preferred algorithm values and in case
  this fails, it will fall back to the old approach with SHA-2 variants
  disabled.

  This functionality can be disabled by setting
  ``LIBCLOUD_PARAMIKO_SHA2_BACKWARD_COMPATIBILITY``environment variable to
  ``false``.

  For security reasons (to prevent possible downgrade attacks and similar) you
  are encouraged to do that in case you know you won't be connecting to any old
  OpenSSH servers.
  [Tomaz Muraus]

Storage
~~~~~~~

- [Google Storage] Fix public objects retrieval. In some scenarios, Google
  doesn't return ``etag`` header in the response (e.g. for gzip content
  encoding). The code has been updated to take this into account and not
  throw if the header is not present.

  (GITHUB-1682, GITHUB-1683)
  [Veith Röthlingshöfer - @RunOrVeith]

- [Azure Blobs] Add support for authenticating with Azure AD by passing
  ``auth_type="azureAd"`` argument to the driver constructor.

  (GITHUB-1663)
  [Brooke White - @brookewhite9]

DNS
~~~

- [GoDaddy] Fix ``list_zones()`` method so it doesn't throw if an item is
  missing ``expires`` attribute.
  (GITHUB-1681)
  [Dave Grenier - @livegrenier]

Container
~~~~~~~~~

- [Kubernetes] Various improvements in the driver - implement list methods for
  nodes, services, deployments, node/pod metrics, add more fields to Pods and
  Containers, rename clusters to namespaces, add type annotations.

  (GITHUB-1667)
  [Dimitris Galanis - @dimgal1]

Other
~~~~~

- Test code has been updated to utilize stdlib ``unittest.mock`` module instead
  of 3rd party PyPi ``mock`` package.

  (GITHUG-1684)
  Reported by @pgajdos.

Changes in Apache Libcloud 3.5.1
--------------------------------

Common
~~~~~~

- Update code which retries failed HTTP requests to also retry failed "raw"
  requests and make sure we also wrap and retry piece of code where Response
  class is instantiated and exceptions can be thrown.
  [Daniel Draper - @Germandrummer92]
  (GITHUB-1592)

Compute
~~~~~~~

- [GCE] Retrieve regions and zones lazily when they are first accessed (via
  self.zone_{dict,list} and self.region_{dict,list} attribute) instead of
  retrieving them inside the driver constructor.

  (GITHUB-1661, GITHUB-1661)
  [Dimitris Galanis - @dimgal1]

Changes in Apache Libcloud 3.5.0
--------------------------------

Common
~~~~~~

- Support for Python 3.5 which has been EOL for more than a year now has been
  removed.

  If you still want to use Libcloud with Python 3.5, you should use an older
  release which still supports Python 3.5.
  (GITHUB-1620)

- Update AWS error response parsing code so it also correctly handles error XML
  responses without a namespace in the response body.

  In some scenarios AWS returns error response without the namespace in the body
  and previous version of the code didn't handle that scenario.
  [Tomaz Muraus - @Kami]

Compute
~~~~~~~

- [EC2] Add support for new ``ap-east-1`` region.
  (GITHUB-1628)
  [Arturo Noha - @r2ronoha, Tomaz Muraus - @Kami]

- [OpenStack] Add Server Groups functions in OpenStack driver.
  (GITHUB-1629)
  [Miguel Caballer - @micafer]

- [OpenStack] OpenStack: Move floating IP functions to use network service
  instead of nova.

  This change affects all the floating ip related functions of the
  ``OpenStack_2_NodeDriver`` class. Two new classes have been added
  ``OpenStack_2_FloatingIpPool`` and ``OpenStack_2_FloatingIpAddress``.
  The main change applies to the FloatingIP class where ``node_id``
  property cannot be directly obtained from FloatingIP information and it
  must be gotten from the related Port information with the ``get_node_id``
  method.
  (GITHUB-1638)
  [Miguel Caballer - @micafer]

- [OpenStack] Avoid raising exception if ip is not found.
  (GITHUB-1595)
  [Miguel Caballer - @micafer]

- [Azure ARM] Add option to create node from Compute Gallery image.
  (GITHUB-1643)
  [Robert Harris - @rgharris]

- [Azure ARM] Add create node OS disk delete option.
  (GITHUB-1644)
  [Robert Harris - @rgharris]

- [EC2] Add missing ``creation_date`` NodeImage extra.
  (GITHUB-1641)
  [Thomas JOUANNOT - @mazerty]

- [GCE] Allow ``credentials`` argument which is provided to the driver
  constructor to also be either a Python dictionary with the credentials object
  or a JSON string with the serialized credentials object. That's in addition
  to supporting passing in path to the credentials file or string PEM version of
  the key.
  (GITHUB-1214)
  [@bverschueren]

- [OpenStack] Personality field in the server requests of OpenStack must
  be optional
  (GITHUB-1649)
  [Miguel Caballer - @micafer]

- [OpenStack] headers field are overwrited in case of POST of
  PUT methods in OpenStack connection
  (GITHUB-1650)
  [Miguel Caballer - @micafer]

- [EC2] Update supported EC2 regions and instance sizes and add support
  for eu-south-1 region.
  (GITHUB-1656)
  [Arturo Noha - @r2ronoha]

- [OpenStack] Add new ``ex_force_microversion`` constructor argument with which
  user can specify which micro version to use (
  https://docs.openstack.org/api-guide/compute/microversions.html).
  (GITHUB-1647, GITHUB-1648)

- [GCE] Add ``paginated_request()`` method to GCEConnection and update
  ``ex_list_project_images()`` method to utilize it.
  (GITHUB-1646, GITHUB-1655)
  [Miguel Caballer - @micafer]

- [OpenStack] Fix regression which was inadvertently introduced in #1557 which
  would cause some OpenStack authentication methods to not work and result in
  an exception.

  Reported by @LanderOtto via #1659.
  (GITHUB-1659, GITHUB-1660)
  [Tomaz Muraus - @Kami]

Storage
~~~~~~~

- [Local Storage] Fix object name prefix based filtering in the
  ``list_container_objects()`` method.

  A change in the previous release inadvertently introduced a regression which
  changed the behavior so the object name prefix based filtering didn't work
  correctly in all the scenarios.

  Reported by @louis-van-der-stam.
  (GITHUB-1631)
  [Tomaz Muraus - @Kami]

- [Local Storage] Objects returned by the ``list_container_objects()`` method
  are now returned sorted in the ascending order based on the object name.

  Previously the order was arbitrary and not stable and consistent across
  different environments and runs.

  (GITHUB-1631)
  [Tomaz Muraus - @Kami]

- [Scaleway] Add new driver for the Scaleway Object Storage.
  (GITHUB-1633)
  [@reixd]

Other
~~~~~

- Also run unit tests under Python 3.10 + Pyjion on CI/CD.
  (GITHUB-1626)

- All the code has been reformatted using black v21.10b0 and we will enforce
  black code style for all the new code going forward.

  Developers can re-format their code using new ``black`` tox target (``black
  -etox``) and they can check if there are any violations by running
  ``black-check`` target (``tox -eblack-check``).
  (GITHUB-1623, GITHUB-1624)

Changes in Apache Libcloud 3.4.1
--------------------------------

.. note::

  Libcloud depends on the ``requests`` library for performing HTTP(s) requests.

  Prior to ``requests`` v2.26.0, ``requests`` depended on ``chardet`` library
  which is licensed under LGPL (requests library itself is licensed under the
  Apache License 2.0 license).

  Since Libcloud is not an application, but a library which is usually used
  along many other libraries in the same (virtual) environment, we can't have
  a strict dependency on requests >= 2.26.0 since that would break a lot of
  installations where users already depend on and have an older version of
  requests installed.

  If you are using requests < 2.26.0 along the Libcloud library you are using
  version of chardet library (chardet is a direct dependency of the requests
  library) which license is not compatible with Apache Libcloud.

  If using a LGPL dependency is a problem for your application, you should
  ensure you are using requests >= 2.26.0.

  It's also worth noting that Apache Libcloud doesn't bundle any 3rd party
  dependencies with our release artifacts - we only provide source code
  artifacts on our website.

  When installing Libcloud from PyPi using pip, pip will also download and use
  the latest version of requests without the problematic chardet dependency,
  unless you already have older version of the requests library installed in
  the same environment where you also want to use Libcloud - in that case,
  Libcloud will use the dependency which is already available and installed.

Common
~~~~~~

- Fix a regression which was inadvertently introduced in v3.4.0 which prevented
  users from installing Libcloud under Python 3.5.

  Also revert ``requests`` minimum version required change and relax the
  minimum version requirement.

  Previous change would prevent Libcloud from being installed in environments
  where a conflicting (lower) version of requests library is required and
  already installed.

  As a library and not an application, Libcloud should specify as loose
  requirements as possible to prevent issues with conflicting requirements
  versions which could prevent Libcloud from being installed.
  (GITHUB-1594)

Changes in Apache Libcloud 3.4.0
--------------------------------

Common
~~~~~~

- Fix how we set HTTP request timeout on the underlying requests session
  object. requests library has changed how timeout is set so our old
  code had no affect.

  (GITHUB-1575, GITHUB-1576)
  [Dimitris Galanis - @dimgal1]

- Update setup.py metadata and indicate we also support Python 3.10.

- [Google] Update Google authentication code so so we don't try to contact
  GCE metadata server when determining auth credentials type when oAuth 2.0 /
  installed app type of credentials are used.

  (GITHUB-1591, GITHUB-1621)

  Reported by Veith Röthlingshöfer - @RunOrVeith.

- [Google] Update Google authentication code so we don't try to retry failed
  request when trying to determine if GCE metadata server is available when
  retrying is enabled globally (either via module level constant or via
  environment variable value).

  This will speed up scenarios when trying is enabled globally, but GCE
  metadata server is not available and different type of credentials are used
  (e.g. oAuth 2).

  (GITHUB-1591, GITHUB-1621)

  Reported by Veith Röthlingshöfer - @RunOrVeith.

- Update minimum ``requests`` version we require as part for install_requires
  in setup.py to ``2.26.0`` when using Python >= 3.6.

  This was done to avoid licensing issue with transitive dependency
  (``chardet``).

  NOTE: requests ``>=2.25.1`` will be used when using Python 3.5 since 2.26.0
  doesn't support Python 3.5 anymore.

  For more context, see https://github.com/psf/requests/pull/5797.
  (GITHUB-1594)

  Reported by Jarek Potiuk - @potiuk.

- Update HTTP connection and request retry code to be more flexible so user
  can specify and utilize custom retry logic which can be configured via
  connection retryCls attribute
  (``driver.connection.retryCls = MyRetryClass``).

  (GITHUB-1558)
  [Veith Röthlingshöfer - @RunOrVeith]

- HTTP connection and request retry logic has been updated so we still respect
  ``timeout`` argument when retrying requests due to rate limit being reached
  errors. Previously, we would try to retry indefinitely on
  ``RateLimitReachedError`` exceptions.

Storage
~~~~~~~

- [Azure Blobs] Respect Content-Encoding, Content-Language and Cache-Control
  headers when uploading blobs via stream.

  Reported by Veith Röthlingshöfer - @RunOrVeith.
  (GITHUB-1550)

- [Azure Blobs] Enable the Azure storage driver to be used with
  Azure Government, Azure China, and Azure Private Link by setting
  the driver host argument to the endpoint suffix for the environment.

  Reported by Melissa Kersh - @mkcello96
  (GITHUB-1551)

- [Local Storage] Optimize ``iterate_container_objects`` method to perform
  early filtering if ``prefix`` argument is provided.
  (GITHUB-1584)
  [@Ido-Levi]

Compute
~~~~~~~

- [Equinix Metal] Various improvements to the driver.

  (GITHUB-1548)
  [Dimitris Galanis - @dimgal1]

- [OpenStack] Fix error getting non existing description of Ports.

  (GITHUB-1543)
  [Miguel Caballer - @micafer]

- [Outscale] Various updates to the driver.
  (GITHUB-1549)
  [Tio Gobin - @tgn-outscale]

- [Ovh] Fix driver so it doesn't throw if a node is in resizing state.
  (GITHUB-1555)
  [Rob Juffermans - @robjuffermans]

- [OpenStack] Support volume v3 API endpoint in OpenStack driver.

  (GITHUB-1561)
  [Miguel Caballer - @micafer]

- [GCE] Get accelerators field in the GCE machineType.

  (GITHUB-1565)
  [Miguel Caballer - @micafer]

- [OpenStack] Support updating ``allowed_address_pairs`` on OpenStack ports
  using ``ex_update_port`` method.
  (GITHUB-1569)
  [@dpeschman]

- [OpenStack] Enable to get Volume Quota details in OpenStack driver.

  (GITHUB-1586)
  [Miguel Caballer - @micafer]

- [OpenStack] Add disabled property to OpenStack images.

  (GITHUB-1615)
  [Miguel Caballer - @micafer]

- [CloudSigma] Various updates, improvements and new functionality in the 
  driver (support for new regions, instance types, additional standard API an 
  extension methods, etc.).

  (GITHUB-1558)
  [Dimitris Galanis - @dimgal1]

- [OpenStack] Add binding:host_id value to the OpenStack port information.
  (GITHUB-1492)
  [Miguel Caballer - @micafer]

- [EC2] Add support for ``gp3`` and ``io2`` volume types. Also add
  ``ex_throughput`` argument to the ``create_volume`` method.
  (GITHUB-1596)
  [Palash Gandhi - @palashgandhi]

- [OpenStack] Add support for authenticating using application credentials.
  (GITHUB-1597, GITHUB-1598)
  [Daniela Bauer - @marianne013]

- [OpenStack] Add support for using optional external cache for auth tokens

  This cache can be shared by multiple processes which results in much less
  tokens being allocated when many different instances / processes
  are utilizing the same set of credentials.

  This functionality can be used by implementing a custom cache class with
  caching logic (e.g. storing cache context on a local filesystem, external
  system such as Redis or similar) + using ``ex_auth_cache`` driver constructor
  argument.
  (GITHUB-1460, GITHUB-1557)
  [@dpeschman]

- [Vultr] Implement support for Vultr API v2 and update driver to use v2 by
  default.
  (GITHUB-1609, GITHUB-1610)
  [Dimitris Galanis - @dimgal1]

DNS
~~~

- [CloudFlare] Enable authentication via API Tokens.
  [Clemens Wolff - @c-w]

- [DigitalOcean] Fix ``create_record()`` and ``update_record()`` method and
  pass ``None`` instead of string value ``null`` for priority, port and weight
  parameters if they are not provided as method arguments.
  (GITHUB-1570)
  [Gasper Vozel - @karantan]

- [NSOne] Fix MX records and root domain handling.
  (GITHUB-1571)
  [Gasper Vozel - @karantan]

- [Vultr] Implement support for Vultr API v2 and update driver to use v2 by
  default.
  (GITHUB-1609, GITHUB-1610)
  [Dimitris Galanis - @dimgal1]

Other
~~~~~

- Fix ``python_requires`` setup.py metadata item value.
  (GITHUB-1606)
  [Michał Górny - @mgorny]

- Update tox targets for unit tests to utilize ``pytest-xdist`` plugin to run
  tests in parallel in multiple processes to speed up the test runs.
  (GITHUB-1625)

Changes in Apache Libcloud 3.3.1
--------------------------------

Compute
~~~~~~~

- [EC2] Fix a regression introduced in v3.3.0 which would break EC2 driver for
  some regions because the driver would incorrectly try to use signature version
  2 for all the regions whereas some newer regions require signature version 4
  to be used.

  If you are unable to upgrade, you can use the following workaround, as long
  as you only use code which supports / works with authentication signature
  algorithm version 4:

  .. sourcecode:: python

    import libcloud.common.aws
    libcloud.common.aws.DEFAULT_SIGNATURE_VERSION = "4"

    # Instantiate affected driver here...

  Reported by @olegrtecno.
  (GITHUB-1545, GITHUB-1546)

- [EC2] Allow user to override which signature algorithm version is used for
  authentication by passing ``signature_version`` keyword argument to the EC2
  driver constructor.
  (GITHUB-1546)

Storage
~~~~~~~

- [Google Cloud Storage] Fix a bug and make sure we also correctly handle
  scenario in ``get_object()`` method when the object size is returned in
  ``x-goog-stored-content-length`` and not ``content-length`` header.

  Reported by Veith Röthlingshöfer - @RunOrVeith.
  (GITHUB-1544, GITHUB-1547)

- [Google Cloud Storage] Update ``get_object()`` method and ensure
  ``object.size`` attribute is an integer and not a string. This way it's
  consistent with ``list_objects()`` method.
  (GITHUB-1547)

Changes in Apache Libcloud 3.3.0
--------------------------------

Common
~~~~~~

- Fix a bug which would cause some prepared requests with empty bodies to be
  chunked which would cause some of the provider APIs such as OpenStack to
  return HTTP 400 errors.
  (GITHUB-1487, GITHUB-1488)
  [Michael Spagon - @mspagon]

- Optimize various code imports (remove unnecessary imports, make some lazy,
  etc.), so now importing most of the modules is around ~20-40% faster (~70
  vs ~140 ms) and in some cases such as EC2 driver even more.

  Now majority of the import time is spent in importing ``requests`` library.
  (GITHUB-1519)
  [Tomaz Muraus]

- ``libcloud.pricing.get_size_price()`` function has been updated so it only
  caches pricing data in memory for the requested drivers.

  This way we avoid caching data in memory for drivers which may never be
  used.

  If you want to revert to old behavior (cache pricing data for all the
  drivers in memory), you can do that by passing ``cache_all=True`` argument
  to that function or set ``libcloud.pricing.CACHE_ALL_PRICING_DATA`` module
  level variable to ``True``.

  Passing ``cache_all=True`` might come handy in situations where you know the
  application will work with a lot of different drivers - this way you can
  avoid multiple disk reads when requesting pricing data for different drivers.
  (GITHUB-1519)
  [Tomaz Muraus]

- Advertise Python 3.9 support in setup.py.

Compute
~~~~~~~

- [GCE] Fix ``ex_set_image_labels`` method using incorrect API path.
  (GITHUB-1485)
  [Poul Petersen - @petersen-poul]

- [OpenStack] Fix error setting ``ex_force_XXX_url`` without setting
  ``ex_force_base_url``.
  (GITHUB-1492)
  [Miguel Caballer - @micafer]

- [EC2] Update supported EC2 regions and instance sizes and add support 
  for eu-north-1 region.
  (GITHUB-1486)
  [Arturo Noha - @r2ronoha]

- [Ovh] Add support for multiple regions to the driver. User can select
  a region (location) by passing ``location`` argument to the driver
  constructor (e.g. ``location=ca``).
  (GITHUB-1494)
  [Dan Hunsaker - @danhunsaker]

- [GCE] Add support for creating nodes without a service account associated
  with them. Now when an empty list is passed for ``ex_service_accounts``
  argument, VM will be created without service account attached.

  For backward compatibility reasons, default value of ``None`` still means to
  use a default service account.
  (GITHUB-1497, GITHUB-1495)
  [David Tomaschik - Matir]

- [VSphere] Add new VMware VSphere driver which utilizes ``pyvmomi`` library
  and works under Python 3.

  If you want to use this driver, you need to install ``pyvmomi`` dependency -
  ``pip install pyvmomi``
  (GITHUB-1481)
  [Eis D. Zaster - @Eis-D-Z]

- [OpenStack] Enable to get Quota Set detail.
  (GITHUB-1495)
  [Miguel Caballer - @micafer]

- [OpenStack] Add ex_get_size_extra_specs function to OpenStack driver.
  (GITHUB-1517)
  [Miguel Caballer - @micafer]

- [OpenStack] Enable to get Neutron Quota details in OpenStack driver.
  (GITHUB-1514)
  [Miguel Caballer - @micafer]

- [DigitalOcean] ``_node_node`` method now ensures ``image`` and ``size``
  attributes are also set correctly and populated on the ``Node`` object.
  (GITHUB-1507, GITHUB-1508)
  [@sergerdn]

- [Vultr] Make sure ``private_ips`` attribute on the ``Node`` object is
  correctly populated when listing nodes. Also add additional values to the
  ``node.extra`` dictionary.
  (GITHUB-1506)
  [@sergerdn]

- [EC2] Optimize EC2 driver imports and move all the large constant files to
  separate modules in ``libcloud/compute/constants/ec2_*.py`` files.

  Previously all the constants were contained in
  ``libcloud/compute/constants.py`` file. That file was imported when importing
  EC2 driver which would add unnecessary import time and memory overhead in case
  this data was not actually used.

  Now most of the large imports are lazy and only happen when that data is
  needed (aka when ``list_sizes()`` method is called).

  ``libcloud/compute/constants.py`` file has also been removed.
  (GITHUB-1519)
  [Tomaz Muraus - @Kami]

- [Packet / Equinix Metal] Packet driver has been renamed to Equinix Metal. If
  your code uses Packet.net driver, you need to update it as per example in
  Upgrade Notes documentation section.
  (GITHUB-1511)
  [Dimitris Galanis - @dimgal1]

- [OutScale] Add various extension methods to the driver. For information on
  available extenion methods, please refer to the driver documentation.
  (GITHUB-1499)
  [@tgn-outscale]

- [Linode] Add support for Linode's API v4.
  (GITHUB-1504)
  [Dimitris Galanis - @dimgal1]

Storage
~~~~~~~

- Deprecated ``lockfile`` library which is used by the Local Storage driver has
  been replaced with ``fasteners`` library.
  [Tomaz Muraus - @Kami]

- [S3] Add support for ``us-gov-east-1`` region.
  (GITHUB-1509, GITHUB-1510)
  [Andy Spohn - @spohnan]

- [DigitalOcean Spaces] Add support for sfo2 regon.
  (GITHUB-1525)
  [Cristian Rasch - @cristianrasch]

- [MinIO] Add new driver for MinIO object storage (https://min.io).
  (GITHUB-1528, GITHUB-1454)
  [Tomaz Muraus - @Kami]

- [S3] Update S3 and other drivers which are based on the S3 one (Google
  Storage, RGW, MinIO) to correctly throw ``ContainerAlreadyExistsError`` if
  container creation fails because container with this name already exists.

  Previously in such scenario, ``InvalidContainerNameError`` exception which
  does not comply with the Libcloud standard API was thrown.
  (GITHUB-1528)
  [Tomaz Muraus - @Kami]

- Add new ``libcloud.common.base.ALLOW_PATH_DOUBLE_SLASHES`` module level
  variable.

  When this value is set to ``True`` (defaults to ``False`` for backward
  compatibility reasons), Libcloud won't try to sanitize the URL path and
  remove any double slashes.

  In most cases, this won't matter and sanitzing double slashes is a safer
  default, but in some cases such as S3, where double slashes can be a valid
  path (e.g. ``/my-bucket//path1/file.txt``), this option may come handy.

  When this variable is set to ``True``, behavior is also consistent with
  Libcloud versions prior to v2.0.0.

  Reported by Jonathan Hanson - @triplepoint.
  (GITHUB-1529)
  [Tomaz Muraus - @Kami]

DNS
~~~

- [Common] Fix a bug with the header value returned by the
  ``export_zone_to_bind_format`` method containing an invalid timestamp (value
  for the minute part of the timestamp was wrong and contained month number
  instead of the minutes value).

  Reported by Kurt Schwehr - @schwehr.

  (GITHUB-1500)
  [Tomaz Muraus - @Kami]

- [CloudFlare DNS] Add support for creating ``SSHFP`` records.
  (GITHUB-1512, GITHUB-1513)
  [Will Hughes - @insertjokehere]

- [DigitalOcean] Update driver and make sure request data is sent as part of
  HTTP request body on POST and PUT operations (previously it was sent as
  part of query params).
  (GITHUB-1505)
  [Andrew Starr-Bochicchio - @andrewsomething]

- [AuroraDNS] Throw correct exception on 403 authorization failed API error.
  (GITHUB-1521, GITHUB-1522)
  [Freek Dijkstra - @macfreek]

- [Linode] Add support for Linode's API v4.
  (GITHUB-1504)
  [Dimitris Galanis - @dimgal1]

- [CloudFlare] Update driver so it correctly throws
  ``RecordAlreadyExists`` error on various error responses which represent
  this error.
  [Tomaz Muraus - @Kami]

Changes in Apache Libcloud 3.2.0
--------------------------------

Common
~~~~~~

- ``libcloud.pricing.download_pricing_file`` function has been updated so it
  tries to download latest ``pricing.json`` file from our public read-only S3
  bucket.

  We now run a daily job as part of our CI/CD which scrapes provider prices and
  publishes the latest version of the ``pricing.json`` file to that bucket.

  For more information, please see
  https://libcloud.readthedocs.io/en/latest/compute/pricing.html.

Compute
~~~~~~~

- [OpenStack] Add `ex_get_network()` to the OpenStack driver to make it
  possible to retrieve a single network by using the ID.

  (GITHUB-1474)
  [Sander Roosingh - @SanderRoosingh]

- [OpenStack] Fix pagination in the ``list_images()`` method and make sure
  method returns all the images, even if the result is spread across multiple
  pages.

  (GITHUB-1467)
  [Thomas Bechtold - @toabctl]

- [GCE] Add script for scraping GCE pricing data and improve price addition in
  ``_to_node_size`` method.
  (GITHUB-1468)
  [Eis D. Zaster - @Eis-D-Z]

- [AWS EC2] Update script for scraping AWS EC2 pricing and update EC2 pricing
  data.
  (GITHUB-1469)
  [Eis D. Zaster - @Eis-D-Z]

- [Deployment] Add new ``wait_period`` argument to the ``deploy_node`` method
  and default it to 5 seconds.

  This argument tells Libcloud how long to wait between each poll interval when
  waiting for a node to come online and have IP address assigned to it.

  Previously this argument was not exposed to the end user and defaulted to 3
  seconds which means it would be quite easy to reach rate limits with some
  providers when spinning up many instances concurrently using the same
  credentials.
  [Tomaz Muraus - @Kami]

- [Azure ARM] Add script for scraping Azure ARM instance pricing data.
  (GITHUB-1470)
  [Eis D. Zaster - @Eis-D-Z]

- Update ``deploy_node()`` method to try to re-connect to the server if we
  receive "SSH connection not active" error when trying to run a deployment
  step.

  In some scenarios, connection may get closed by the server for whatever
  reason before finishing all the deployment steps and in this case only
  re-connecting would help and result in a successful outcome.
  [Tomaz Muraus - @Kami]

- [Deployment] Make ``FileDeployment`` class much faster and more efficient
  when working with large files or when running multiple ``FileDeployment``
  steps on a single node.

  This was achieved by implementing two changes on the ``ParamikoSSHClient``
  class:

  1. ``put()`` method now tries to re-use the existing open SFTP connection
     if one already exists instead of re-creating a new one for each
     ``put()`` call.
  2. New ``putfo()`` method has been added to the ``ParamikoSSHClient`` class
     which utilizes the underlying ``sftp.putfo()`` method.

     This method doesn't need to buffer the whole file content in memory and
     also supports pipelining which makes uploads much faster and more
     efficient for larger files.

  [Tomaz Muraus - @Kami]

- [Deployment] Add ``__repr__()`` and ``__str__()`` methods to all the
  Deployment classes.
  [Tomaz Muraus - @Kami]

- [Deployment] New ``keep_alive`` and ``use_compression`` arguments have been
  added to the ``ParamikoSSHClient`` class constructor.

  Right now those are not exposed yet to the ``deploy_node()`` method.
  [Tomaz Muraus - @Kami]

- [Deployment] Update ``ParamikoSSHClient.put()`` method so it returns a
  correct path when commands are being executed on a Windows machine.

  Also update related deployment classes so they correctly handle situation
  when we are executing commands on a Windows server.
  [Arthur Kamalov, Tomaz Muraus]

- [Outscale] Add a new driver for the Outscale provider. Existing Outscale
  driver utilizes the EC2 compatible API and this one utilizes native Outscale
  API.
  (GITHUB-1476)
  [Tio Gobin - @tgn-outscale]

- [KubeVirt] Add new methods for managing services which allows users to expose
  ports for the VMs (``ex_list_services``, ``ex_create_service``,
  ``ex_delete_service``).
  (GITHUB-1478)
  [Eis D. Zaster - @Eis-D-Z]

Container
~~~~~~~~~

- [LXD] Add new methods for managing network and storage pool capabilities and
  include other improvements in some of the existing methods.
  (GITHUB-1477)
  [Eis D. Zaster - @Eis-D-Z]

Changes in Apache Libcloud 3.1.0
--------------------------------

Compute
~~~~~~~

- [GCE] Add latest Ubuntu image families (Ubuntu 20.04) to the driver.

  (GITHUB-1449)
  [Christopher Lambert - @XN137]

- [DigitalOcean] Add ``location`` argument to the ``list_sizes()`` method.

  NOTE: Location filtering is performed on the client.
  (GITHUB-1455, GITHUB-1456)
  [RobertH1993]

- Fix ``deploy_node()`` so an exception is not thrown if any of the output
  (stdout / stderr) produced by the deployment script contains a non-valid utf-8
  character.

  Previously, user would see an error similar to "Failed after 3 tries: 'utf-8'
  codec can't decode byte 0xc0 in position 37: invalid start byte".

  And now we simply ignore byte sequences which we can't decode and include
  rest of the output which can be decoded.

  (GITHUB-1459)
  [Tomaz Muraus - @Kami]

- Add new ``timeout`` argument to ``ScriptDeployment`` and
  ``ScriptFileDeployment`` class constructor.

  With this argument, user can specify an optional run timeout for that
  deployment step run.
  (GITHUB-1445)
  [Tomaz Muraus - @Kami]

- [GiG G8] Fix retry functionality when creating port forwards and add support
  for automatically refresing the JWT auth token inside the connection class if
  it's about to expire in 60 seconds or less.
  (GITHUB-1465)
  [Jo De Boeck - @grimpy]

- [Azure ARM] Update ``create_node`` so an exception is thrown if user passes
  ``ex_use_managed_disks=False``, but doesn't provide a value for the
  ``ex_storage_account`` argument.
  (GITHUB-1448)
  [@antoinebourayne]

Storage
~~~~~~~

- [AWS S3] Make sure driver works correctly for objects with ``~`` in the name.

  Now when sanitizing the object name, we don't url encode ``~`` character.

  Reported by Michael Militzer - @mmilitzer.
  (GITHUB-1452, GITHUB-1457)
  [Tomaz Muraus]

DNS
~~~

- [CloudFlare] Update driver to include the whole error chain the thrown
  exception message field.

  This makes various issues easier to debug since the whole error context is
  included.
  [Tomaz Muraus]

- [Gandi Live, CloudFlare, GCE] Add support for managing ``CAA`` record types.

  When creating a ``CAA`` record, data field needs to be in the following
  format:

  ``<flags> <tag> <domain name>``

  For example:

  - ``0 issue caa.example.com``
  - ``0 issuewild caa.example.com``
  - ``0 iodef https://example.com/reports``

  (GITHUB-1463, GITHUB-1464)
  [Tomaz Muraus]

- [Gandi Live] Don't throw if ``extra['rrset_ttl']`` argument is not passed
  to the ``create_record`` method.
  (GITHUB-1463)
  [Tomaz Muraus]

Other
~~~~~

- Update ``contrib/Dockerfile`` which can be used for running tests so
  it only run tests with Python versions we support. This means dropping
  support for Python < 3.5 and adding support for Python 3.7 and 3.8.

  Also update it to use a more recent Ubuntu version (18.04) and Python 3
  for running tox target.
  (GITHUB-1451)
  [Tomaz Muraus - @Kami, HuiFeng Tang - @99Kies]

Changes in Apache Libcloud 3.0.0
--------------------------------

Common
~~~~~~

- Make sure ``auth_user_info`` variable on the OpenStack identify connection
  class is populated when using auth version ``3.x_password`` and
  ``3.x_oidc_access_token``.

  (GITHUB-1436)
  [@lln-ijinus, Tomaz Muraus)

- [OpenStack] Update OpenStack identity driver so a custom project can be
  selected using ``domain_name`` keyword argument containing a project id.

  Previously this argument value could only contain a project name, now the
  value will be checked against project name and id.

  (GITHUB-1439)
  [Miguel Caballer - @micafer]

Compute
~~~~~~~

- [GCE] Update ``create_node()`` method so it throws an exception if node
  location can't be inferred and location is not specified by the user (
  either by passing ``datacenter`` constructor argument or by passing
  ``location`` argument to the method).

  Reported by Kevin K. - @kbknapp.
  (GITHUB-1443)
  [Tomaz Muraus]

- [GCE] Update ``ex_get_disktype`` method so it works if ``zone`` argument is
  not set.
  (GITHUB-1443)
  [Tomaz Muraus]

- [GiG G8] Add new driver for GiG G8 provider (https://gig.tech/).
  (GITHUB-1437)
  [Jo De Boeck - @grimpy]

- Add new ``at_exit_func`` argument to ``deploy_node()`` method. With this
  argument user can specify which function will be called before exiting
  with the created node in question if the deploy process has been canceled
  after the node has been created, but before the method has fully finished.

  This comes handy since it simplifies various cleanup scenarios.
  (GITHUB-1445)
  [Tomaz Muraus - @Kami]

- [OpenStack] Fix auto assignment of volume device when using device name
  ``auto`` in the ``attach_volume`` method.
  (GITHUB-1444)
  [Joshua Hesketh - @jhesketh]

- [Kamatera] Add new driver for Kamatera provider (https://www.kamatera.com).
  (GITHUB-1442)
  [Ori Hoch - @OriHoch]

Storage
~~~~~~~

- Add new ``download_object_range`` and ``download_object_range_as_stream``
  methods for downloading part of the object content (aka range downloads) to
  the base storage API.

  Currently those methods are implemented for the local storage Azure Blobs,
  CloudFiles, S3 and any other provider driver which is based on the S3 one
  (such as Google Storage and DigitalOcean Spaces).
  (GITHUB-1431)
  [Tomaz Muraus]

- Add type annotations for the base storage API.
  (GITHUB-1410)
  [Clemens Wolff - @c-w]

- [Google Storage] Update the driver so it supports service account HMAC
  credentials.

  There was a bug in the code where we used the user id length check to
  determine the account type and that code check didn't take service
  account HMAC credentials (which contain a longer string) into account.

  Reported by Patrick Mézard - pmezard.
  (GITHUB-1437, GITHUB-1440)
  [Yoan Tournade - @MonsieurV]

DNS
~~~

- Add type annotations for the base DNS API.
  (GITHUB-1434)
  [Tomaz Muraus]

Container
~~~~~~~~~

- [Kubernetes] Add support for the client certificate and static token based
  authentication to the driver.
  (GITHUB-1421)
  [Tomaz Muraus]

- Add type annotations for the base container API.
  (GITHUB-1435)
  [Tomaz Muraus]


Changes in Apache Libcloud v2.8.3
---------------------------------

Compute
~~~~~~~

- Fix ``deploy_node()`` so an exception is not thrown if any of the output
  (stdout / stderr) produced by the deployment script contains a non-valid utf-8
  character.

  Previously, user would see an error similar to "Failed after 3 tries: 'utf-8'
  codec can't decode byte 0xc0 in position 37: invalid start byte".

  And now we simply ignore byte sequences which we can't decode and include
  rest of the output which can be decoded.

  (GITHUB-1459)
  [Tomaz Muraus - @Kami]

Storage
~~~~~~~

- [AWS S3] Make sure driver works correctly for objects with ``~`` in the name.

  Now when sanitizing the object name, we don't url encode ``~`` character.

  Reported by Michael Militzer - @mmilitzer.
  (GITHUB-1452, GITHUB-1457)
  [Tomaz Muraus]

Changes in Apache Libcloud v2.8.2
---------------------------------

Compute
~~~~~~~

- Add support for Ed25519 private keys for ``deploy_node()`` functionality
  when using paramiko >= 2.2.0.
  (GITHUB-1445)
  [Tomaz Muraus - @Kami]

- Fix ``deploy_node()`` so it correctly propagates an exception is a private key
  which is used is password protected, but no password is specified.

  Previously it incorrectly tried to retry on such exception. This means the
  exception would only bubble up after all the retry attempts have been
  exhausted.
  (GITHUB-1445)
  [Tomaz Muraus - @Kami]

- Allow user to specify password for encrypted keys by passing
  ``ssh_key_password`` argument to the ``deploy_node()`` method.

  Previously they
  (GITHUB-1445)
  [Tomaz Muraus - @Kami]

- Fix ``deploy_node()`` so it correctly propagates an exception if invalid
  or unsupported private key is used.

  Previously it incorrectly tried to retry on such exception. This means the
  exception would only bubble up after all the retry attempts have been
  exhausted.
  (GITHUB-1445)
  [Tomaz Muraus - @Kami]

- Fix ``deploy_node()`` method so we don't retry on fatal
  ``SSHCommandTimeoutError`` exception (exception which is thrown when a
  command which is running on remote host times out).
  (GITHUB-1445)
  [Tomaz Muraus - @Kami]

- Add new ``timeout`` argument to ``ScriptDeployment`` and
  ``ScriptFileDeployment`` class constructor.

  With this argument, user can specify an optional run timeout for that
  deployment step run.
  (GITHUB-1445)
  [Tomaz Muraus - @Kami]

- Add new ``stdout`` and ``stderr`` attribute to ``SSHCommandTimeoutError``
  class.

  Those attributes contain value of stdout and stderr produced so far.
  (GITHUB-1445)
  [Tomaz Muraus - @Kami]

- [OpenStack] Fix auto assignment of volume device when using device name
  ``auto`` in the ``attach_volume`` method.
  (GITHUB-1444)
  [Joshua Hesketh - @jhesketh]

Changes in Apache Libcloud v2.8.1
---------------------------------

Common
~~~~~~

- Fix ``LIBCLOUD_DEBUG_PRETTY_PRINT_RESPONSE`` functionality and make sure it
  works correctly under Python 3 when ``response.read()`` function returns
  unicode and not bytes.

  (GITHUB-1430)
  [Tomaz Muraus]

Compute
~~~~~~~

- [GCE] Fix ``list_nodes()`` method so it correctly handles pagination
  and returns all the nodes if there are more than 500 nodes available
  in total.

  Previously, only first 500 nodes were returned.

  Reported by @TheSushiChef.
  (GITHUB-1409, GITHUB-1360)
  [Tomaz Muraus]

- Fix some incorrect type annotations in the base compute API.

  Reported by @dpeschman.
  (GITHUB-1413)
  [Tomaz Muraus]

- [OpenStack] Fix error with getting node id in ``_to_floating_ip`` method
  when region is not called ``nova``.
  (GITHUB-1411, GITHUB-1412)
  [Miguel Caballer - @micafer]

- [EC2] Fix ``ex_userdata`` keyword argument in the ``create_node()`` method
  being ignored / not working correctly.

  NOTE: This regression has been inadvertently introduced in v2.8.0.
  (GITHUB-1426)
  [Dan Chaffelson - @Chaffelson]

- [EC2] Update ``create_volume`` method to automatically select first available
  availability zone if one is not explicitly provided via ``location`` argument.
  [Tomaz Muraus]

Storage
~~~~~~~

- [AWS S3] Fix upload object code so uploaded data MD5 checksum check is not
  performed at the end of the upload when AWS KMS server side encryption is
  used.

  If AWS KMS server side object encryption is used, ETag header value in the
  response doesn't contain data MD5 digest so we can't perform a checksum
  check.

  Reported by Jonathan Harden - @jfharden.
  (GITHUB-1401, GITHUB-1406)
  [Tomaz Muraus - @Kami]

- [Google Storage] Fix a bug when uploading an object would fail and result
  in 401 "invalid signature" error when object mime type contained mixed
  casing and when S3 Interoperability authentication method was used.

  Reported by Will Abson - wabson.
  (GITHUB-1417, GITHUB-1418)
  [Tomaz Muraus]

- Fix ``upload_object_via_stream`` method so "Illegal seek" errors which
  can arise when calculating iterator content hash are ignored. Those errors
  likely indicate that the underlying file handle / iterator is a pipe which
  doesn't support seek and that the error is not fatal and we should still
  proceed.

  Reported by Per Buer - @perbu.

  (GITHUB-1424, GITHUB-1427)
  [Tomaz Muraus]

DNS
~~~

- [Gandi Live] Update the driver and make sure it matches the latest service /
  API updates.
  (GITHUB-1416)
  [Ryan Lee - @zepheiryan]

- [CloudFlare] Fix ``export_zone_to_bind_format`` method.

  Previously it threw an exception, because ``record.extra`` dictionary
  didn't contain ``priority`` key.

  Reported by James Montgomery - @gh-jamesmontgomery.
  (GITHUB-1428, GITHUB-1429)
  [Tomaz Muraus]

Changes in Apache Libcloud v2.8.0
---------------------------------

Common
~~~~~~

- Fix a regression with ``get_driver()`` method not working if ``provider``
  argument value was a string (e.g. using ``get_driver('openstack')``
  instead of ``get_driver(Provider.OPENSTACK)``).

  Only officially supported and recommended approach still is to use
  ``Provider.FOO`` enum type constant, but since the string notation was
  unofficially supported in the past, we will still support it until the next
  major release.

  Reported by @dpeschman.
  (GITHUB-1391, GITHUB-1390)
  [Tomaz Muraus]

- Include ``py.typed`` data file to signal that this package contains type
  annotations / hints.

  NOTE: At the moment, type annotations are only available for the base
  compute API.
  [Tomaz Muraus]

- Fix universal wheel METADATA and ensure conditional dependencies
  (backports.ssl_match_hostname, typing, enum34) are handled correctly.

  Reported by Adam Terrey (@arterrey).
  (GITHUB-1392, GITHUB-1393)
  [Tomaz Muraus]

Compute
~~~~~~~

- [DigitalOcean] Fix ``attach_volume`` and ``detach_volume`` methods.
  Previously those two methods incorrectly passed volume id instead of
  volume name to the API. (GITHUB-1380)
  [@mpempekos]

- [GCE] Add ``ex_disk_size`` argument to the ``create_node`` method.
  (GITHUB-1386, GITHUB-1388)
  [Peter Yu - @yukw777]

- [VMware vCloud] Various improvements, fixes and additions to the driver.
  (GITHUB-1373)
  [OpenText Corporation]

- Update ``deploy_node()`` method so it now only passes non-deploy node
  keyword arguments + ``auth`` argument to the underlying ``create_node()``
  method. Previously it also passed ``deploy_node()`` specific arguments
  such as ``deploy``, ``ssh_username``, ``max_tries``, etc. to it.

  Because of that, a lot of the compute drivers which support deploy
  functionality needed to use ``**kwargs`` in ``create_node()`` method
  signature which made code hard to read and error prone.

  Also update various affected drivers to explicitly declare supported
  arguments in the  ``create_node()`` method signature (Dummy, Abiquo,
  Joyent, Bluebox, OpenStack, Gandy, VCL, vCloud, CloudStack, GoGrid
  HostVirtual, CloudSigma, ElasticStack, RimuHosting, SoftLayer, Voxel,
  Vpsnet, KTUcloud, BrightBox, ECP, OpenNebula, UPcloud).

  As part of this change, also various issues with invalid argument names
  were identified and fixed.
  (GITHUB-1389)
  [Tomaz Muraus]

- Add MyPy type annotations for ``create_node()`` and ``deploy_node()``
  method.
  (GITHUB-1389)
  [Tomaz Muraus]

- [GCE] Update ``deploy_node()`` method so it complies with the base compute
  API and accepts ``deploy`` argument.

  This method now also takes all the same keyword arguments which original
  ``create_node()`` takes.
  (GITHUB-1387)
  [Peter Yu - @yukw777, Tomaz Muraus]

- [Common] To make debugging and troubleshooting easier, add ``__repr__``
  and ``__str__`` method to the ``ScriptDeployment`` class.
  [Tomaz Muraus]

- [Common] Add type annotations / hints for rest of the base compute API
  classes and methods.
  [Tomaz Muraus]

Storage
~~~~~~~

- [AWS S3] Make sure ``host`` driver constructor argument has priority
  over ``region`` argument.

  This means if you specify ``host`` and ``region`` argument, host won't be
  inferred from the region, but ``host`` argument will be used for the actual
  connection host value.
  (GITHUB-1384, GITHUB-1383)
  [@gluap]

Changes in Apache Libcloud v2.7.0
---------------------------------

General
~~~~~~~

- Test code with Python 3.8 and advertise that we also support Python 3.8.
  (GITHUB-1371, GITHUB-1374)
  [Tomaz Muraus]

Common
~~~~~~

- [OpenStack] Fix OpenStack project scoped token authentication. The driver
  constructors now accept ``ex_tenant_domain_id`` argument which tells
  authentication service which domain id to use for the scoped authentication
  token. (GITHUB-1367)
  [kshtsk]

Compute
~~~~~~~

- Introduce type annotations for the base compute API methods. This means you
  can now leverage mypy to type check (with some limitations) your code which
  utilizes Libcloud compute API standard API methods.

  Keep in mind that at this point, type annotations are only available for
  standard compute API methods.
  (GITHUB-1306)
  [Tomaz Muraus]

- [Azure ARM] Fix ``attach_volume`` method and allow maximum of 64 disks to be
  added when LUN is not specified. Previously there was a bug and only a
  maximum of 63 disks could be added.
  (GITHUB-1372)
  [Palash Gandhi - @palashgandhi]

- New ``start_node`` and ``stop_node`` methods have been added to the base
  Libcloud compute API NodeDriver class.

  A lot of the existing compute drivers already implemented that functionality
  via extension methods (``ex_start_node``, ``ex_stop_node``) so it was decided
  to promote those methods to be part of the standard Libcloud compute API and
  update all the affected drivers.

  For backward compatibility reasons, existing ``ex_start`` and ``ex_stop_node``
  methods will still work until a next major release.

  (GITHUB-1375, GITHUB-1364)
  [Tomaz Muraus, @emakarov]

 - [GCE] Add new ``ex_set_volume_labels`` method for managing volume labels to
   the driver.
   (GITHUB-1376)
   [Rob Zimmerman - @zimventures]

- [EC2] Add support for new ``inf1.*`` instance types.
  [Tomaz Muraus]

Storage
~~~~~~~

- [S3] Update S3 driver so a single driver class can be used for different
  regions.

  Region which is used is controled by the ``region`` driver constructor
  argument.

  Previously, that driver followed "driver class per region" approach. That
  approach will be deprecated and removed in a future release.

  For more information, please refer to the Upgrade Notes documentation section.
  (GITHUB-1371)
  [Tomaz Muras]

- [S3] Add missing ``eu-north-1`` region to the S3 driver. (GITHUB-1370)
  [michaelsembwever]

- [S3] Add missing regions (eu-west-3, ap-northeast-3, me-south-1) to the driver.
  (GITHUB-1371)
  [Tomaz Muras]

- [S3] Update the driver to throw more user-friendly error message if user is
  using driver for a region X, but trying to upload / download object to / from
  a region Y. (GITHUB-1371)
  [Tomaz Muras]

Changes in Apache Libcloud 2.6.1
--------------------------------

Compute
~~~~~~~

- [Packet] Update ``list_sizes`` method so it accepts ``ex_project_id`` argument
  and works with project API tokens. (GITHUB-1351) [Dimitris Moraitis - @d-mo]

- [GCE] Fix ``GCEProject.set_common_instance_metadata`` and
  ``GCEproject.set_usage_export_bucket`` method. (GITHUB-1354)
  [Aitor Zabala - @aitorzabala, Tomaz Muraus - @Kami]

- [GCE] Add ``sync`` / ``ex_sync`` argument to the ``ex_stop_node``,
  ``ex_start_node`` and ``destroy_node`` method. When this argument is set to
  ``False``, method will return immediately without waiting polling and waiting
  for a long running API operation to finish before returning. For backward
  compatibility reasons, it defaults to ``True``. (GITHUB-1357)
  [Rob Zimmerman - zimventures]

- [GCE] Update list of image projects and add new ``centos-8`` and
  ``debian-10`` based images. (GITHUB-1358)
  [Christopher Lambert - XN137]

- [OpenStack v2] Add new ``ex_image_ref`` argument to the ``create_volume``
  method. This way bootable volumes can be created from specific images.
  (GITHUB-1363)
  [Rick van de Loo]

- [OpenStack v2] Update ``create_node_method`` and allow users to create
  nodes from bootable volumes without specifying ``image`` argument.
  (GITHUB-1362)
  [Rick van de Loo]

- [AWS] Re-generate and update available EC2 instance sizes and pricing data.
  [Tomaz Muraus]

Storage
~~~~~~~

- [Common, S3, GCS] Reuse TCP connections when uploading files (GITHUB-1353)
  [Quentin Pradet]

Load Balancer
~~~~~~~~~~~~~

- [AWS] Implement various create methods in the driver. (GITHUB-1349)
  [Anton Kozyrev - @Irvan]

Changes in Apache Libcloud 2.6.0
--------------------------------

General
~~~~~~~

- [OpenStack] Update OpenStack identity driver so a custom project can be
  selected using ``domain_name`` keyword argument. Previously, that wasn't
  possible and the first project which was returned by the API was always
  selected. (GITHUB-1293)
  [Miguel Caballer - @micafer]

- Add new ``extra`` attribute to the base ``NodeLocation`` class. (GITHUB-1282)
  [Dimitris Moraitis - @d-mo]

- Remove various code patterns which were in place for supporting multiple
  Python versions, including 2.5 and 2.6. Libcloud hasn't supported Python <
  2.7 for a while now, so we can remove that code. (GITHUB-1307)
  [Tomaz Muraus]

- Also run pylint on ``libcloud/compute/`` directory and fix various pylint
  violations. (GITHUB-1308)
  [Tomaz Muraus]

- [OpenStack] Remove unused variable in parse_error (GITHUB-1260)
  [Rick van de Loo]

- Add support for HTTPS proxies and fix ``driver.set_http_proxy()`` method.

  HTTPS proxy can be set up by either setting ``https_proxy`` / ``http_proxy``
  environment variable or by using
  ``driver.connection.connection.set_http_proxy`` method.

  For more information, please refer to the documentation -
  https://libcloud.readthedocs.io/en/latest/other/using-http-proxy.html
  (GITHUB-1314, GITHUB-1324)
  [Jim Liu - @hldh214, Tomaz Muraus]

- Fix paramiko debug logging which didn't work when using ``LIBCLOUD_DEBUG``
  environment variable. (GITHUB-1315)
  [Tomaz Muraaus]

- Update paramiko SSH deployment client so it automatically tries to convert
  private keys in PEM format with a header which paramiko doesn't recognize
  into a format which paramiko recognizes.

  NOTE: Paramiko only supports keys in PEM format. This means keys which start
  with "----BEGIN <TYPE> PRIVATE KEY-----". Keys in PKCS#8 and newer OpenSSH
  format are not supported.

  For more information, see https://libcloud.readthedocs.io/en/latest/compute/deployment.html#supported-private-ssh-key-types
  (GITHUB-1314)

- Update Paramiko SSH client to throw a more user-friendly error if a private
  key file in an unsupported format is used. (GITHUB-1314)
  [Tomaz Muraus]

- Fix HTTP(s) proxy support in the OpenStack drivers. (GITHUB-1324)
  [Gabe Van Engel - @gvengel]

- Fix logging connection class so it also works when data type is ``bytearray``
  or ``bytes``. (GITHUB-1339)
  [Tomaz Muraus]

Compute
~~~~~~~

- [Google Compute Engine] Fix the driver so ``list_nodes()`` method doesn't
  throw if there is a node in a ``SUSPENDED`` state.

  Also update the code so it doesn't crash if an unknown node state which is
  not defined locally is returned by the API when listing nodes. Such states
  are now mapped to ``UNKNOWN``. (GITHUB-1296, LIBCLOUD-1045)

  Reported by rafa alistair.
  [Tomaz Muraus]

- [OpenStack] Fix a bug with retrieving floating IP address when a
  ``device_owner`` of a port is ``compute:None``. (GITHUB-1295)
  [Miguel Caballer - @micafer]
- [Packet] Add various new extension methods to Packet.net driver
  (``ex_reinstall_node``, ``ex_list_projects``,
  ``ex_get_bgp_config_for_project``, ``ex_get_bgp_config``,
  ``ex_list_nodes_for_project``, etc.). (GITHUB-1282)
  [Dimitris Moraitis - @d-mo]

- [Maxihost] Add new compute driver for Maxihost provider
  (https://www.maxihost.com/). (GITHUB-1298)
  [Spyros Tzavaras - @mpempekos]

- [Azure ARM] Add various improvements to the Azure ARM driver:
  - Add functionality to resize a volume in Azure
  - Add functionality to update the network profile of a node
  - Add functionality to update a network interface's properties
  - Add functionality to check IP address availability (GITHUB-1244)
  [Palash Gandhi - @palashgandhi]

- [EC2] Allow user to pass arbitrary filters to ``list_volumes`` method by
  passing a dictionary with filters as ``ex_filters`` method argument value.
  (GITHUB-1300)
  [Palash Gandhi - @palashgandhi]

- [GCE] Add new ``ex_instancegroupmanager_set_autohealingpolicies`` method to
  the GCE driver.

  This method allows user to set the auto healing policies (health check to
  use and initial delay) on GCE instance group. (GITHUB-1286)
  [Kenta Morris - @kentamorris]

- [GCE] Update GCE driver to include new operating system images such as
  Ubuntu 18.04, RHEL 8, etc. (GITHUB-1304)
  [Christopher Lambert - @XN137]

- [GCE] Add new ``ex_resize_volume`` method to the driver. (GITHUB-1301)
  [Palash Gandhi - @palashgandhi]

- [OpenStack] Add various router management methods to the OpenStack
  driver. (GITHUB-1281)
  [Miguel Caballer - @micafer]

- [OpenStack] Fix ``ex_resize`` method. (GITHUB-1311)
  [Miguel Caballer - @micafer]

- [OpenStack] For consistency, rename ``ex_resize`` method to
  ``ex_resize_node``. For backward compatibility reasons, leave ``ex_resize``
  alias in place.
  [Tomaz Muraus]

- [Gridscale] Add new driver for Gridscale provider (https://gridscale.io).
  (GITHUB-1305, GITHUB-1315)
  [Sydney Weber - @PrinceSydney]

- [Oneandone] Update Oneandone driver to accomodate latest changes to the API.
  This means removing deprecated ``ex_remove_server_firewall_policy`` method
  and replacing ``port_from`` and ``port_to`` argument on the firewall policy
  with a single ``port`` attribute.
  (GITHUB-1230)
  [Amel Ajdinovic - @aajdinov]

- [DigitalOcean] Update ``list_locations`` method in the DigitalOcean driver
  to only returns regions which are available by default. If you want to list
  all the regions, you need to pass ``ex_available=False`` argument to the
  method. (GITHUB-1001)
  [Markos Gogoulos]

- [EC2] Add new ``ex_modify_subnet_attribute`` method to the EC2 driver.
  (GITHUB-1205)
  [Dan Hunsaker - @danhunsaker]

- [Azure ARM] Add ``ex_delete_public_ip`` method to the Azure ARM driver.
  (GITHUB-1318)
  [Reza Shahriari - redha1419]

- [EC2] Update EC2 driver to throw a more user-friendly exception if a user /
  developer tries to provide an invalid value type for an item value in the
  request ``params`` dictionary.

  Request parameters are sent via query parameters and not via request body,
  as such, only string values are supported. (GITHUB-1329, GITHUB-1321)

  Reported by James Bednell.
  [Tomaz Muraus]

- [OpenStack] Add new ``ex_remove_security_group_from_node`` method.
  (GITHUB-1331)
  [Miguel Caballer - @micafer]

- [OpenStack] Fix broken ``ex_update_port`` method.
  (GITHUB-1320)
  [Miguel Caballer - @micafer]

- [Softlayer] Fix a bug with driver incorrectly handling the value of
  ``ex_hourly`` argument in the ``create_node()`` method which caused nodes
  to always be created with hourly billing, even if this argument was set to
  ``False``. (GITHUB-1334, GITHUB-1335)
  [@r2ronoha]

- [GCE] Add optional ``cpuPlatform`` and ``minCpuPlatform`` attributes to the
  ``node.extra`` dictionary. (GITHUB-1342, GITHUB-1343)
  [@yairshemla]

Storage
~~~~~~~

- [Azure Blobs] Enable the Azure storage driver to be used with the Azurite
  Storage Emulator and Azure Blob Storage on IoT Edge.
  (LIBCLOUD-1037, GITHUB-1278)
  [Clemens Wolff - @c-w]

- [Azure Blobs] Fix a bug with Azure storage driver works when used against a
  storage account that was created using ``kind=BlobStrage``. This includes
  updating the minimum API version used / supported by the storage driver from
  ``2012-02-12`` to ``2014-02-14``. (LIBCLOUD-851, GITHUB-1202, GITHUB-1294)
  [Clemens Wolff - @c-w, Davis Kirkendall - @daviskirk]

- [Azure Blobs] Increase the maximum size of block blobs that can be created
  to 100 MB. This includes updating the minimum API version used / supported
  by the storage driver from ``2014-02-14`` to ``2016-05-31``. (GITHUB-1340)
  [Clemens Wolff - @c-w]

- [Azure Blobs] Set the minimum required version of requests to ``2.5.0`` since
  requests ``2.4.0`` and earlier exhibit XML parsing errors of Azure Storage
  responses. (GITHUB-1325, GITHUB-1322)
  [Clemens Wolff - @c-w]

- [Azure Blobs] Detect bad version of requests that leads to errors in parsing
  Azure Storage responses. This scenario is known to happen on RHEL 7.6 when
  requests was installed via yum. (GITHUB-1332, GITHUB-1322)
  [Clemens Wolff - @c-w]

- [Common, CloudFiles] Fix ``upload_object_via_stream`` and ensure we start
  from the beginning when calculating hash for the provided iterator. This way
  we avoid hash mismatch errors in scenario where provided iterator is already
  iterated / seeked upon before calculating the hash. (GITHUB-1326)
  [Gabe Van Engel - @gvengel, Tomaz Muraus]

- [Backblaze B2] Fix a bug with driver not working correctly due to a
  regression which was inadvertently introduced in one of the previous
  releases. (GITHUB-1338, GITHUB-1339)

  Reported by Shawn Nock - @nocko.
  [Tomaz Muraus]

- [Backblaze B2] Fix ``upload_object_via_stream`` method. (GITHUB-1339)
  [Tomaz Muraus]

DNS
~~~

- [Cloudflare] Re-write the Cloudflare DNS driver to use Cloudflare API v4.
  (LIBCLOUD-1001, LIBCLOUD-994, GITHUB-1292)
  [Clemens Wolff - @c-w]

- [Gandi LiveDNS] Add new driver for Gandi LiveDNS service. (GITHUB-1323)
  [Ryan Lee - @zepheiryan]

- [PowerDNS] Update driver so it works with API v3 and v4. #1328
  [@biggosh]

Changes in Apache Libcloud 2.5.0
--------------------------------

General
~~~~~~~

- [NTT CIS] Add loadbalancer and compute drivers for NTT-CIS, rename
  dimensiondata modules to NTT-CIS. (GITHUB-1250)
  [Mitch Raful]

- [NTT CIS] Fix loadbalancer docs. (GITHUB-1270)
  [Mitch Raful]

- Use assertIsNone instead of assertEqual with None in tests (GITHUB-1264)
  [Ken Dreyer]

- Updating command line arguments to current version in Azure examples.
  (GITHUB-1273)
  [mitar]

- [GCE, SoftLayer] Update GCE and Softlayer drivers to utilize crypto
  primitives from the ``cryptography`` library instead of deprecated and
  unmaintained ``PyCrypto`` library.

  (GITHUB-1280)
  [Ryan Petrello]

- Fix ``libcloud.enable_debug`` function so it doesn't leak open file handle
  and closes the open file when the program exits when a debug mode is used.
  [Tomaz Muraus]

* Update various drivers (CloudFiles, NTT CIS etc.) so they don't leak open
  file handles in some situations.
  [Tomaz Muraus]

Common
~~~~~~

- [OpenStack] Handle missing user enabled attribute (GITHUB-1261)
  [Ken Dreyer]

- [Google Cloud Storage] Handle Interoperability access keys of more than 20
  characters. (GITHUB-1272)
  [Yoan Tournade]

Compute
~~~~~~~

- [OpenStack] Implement OpenStack_1_1_NodeDriver ex_get_snapshot (GITHUB-1257)
  [Rick van de Loo]

- [OpenStack] Pagination in various OpenStack_2_NodeDriver methods (GITHUB-1263)
  [Rick van de Loo]

- [OpenStack] Implement OpenStack_2_NodeDriver ex_create_subnet (LIBCLOUD-874,
  GITHUB-1242)
  [Miguel Caballer]

- [OpenStack] Implement OpenStack_2_NodeDriver ex_delete_subnet (LIBCLOUD-874,
  GITHUB-1242)
  [Miguel Caballer]

- [OpenStack] Implement OpenStack_2_NodeDriver list_volumes (LIBCLOUD-874,
  GITHUB-1242)
  [Miguel Caballer]

- [OpenStack] Implement OpenStack_2_NodeDriver ex_get_volume (LIBCLOUD-874,
  GITHUB-1242)
  [Miguel Caballer]

- [OpenStack] Implement OpenStack_2_NodeDriver create_volume (LIBCLOUD-874,
  GITHUB-1242)
  [Miguel Caballer]

- [OpenStack] Implement OpenStack_2_NodeDriver destroy_volume (LIBCLOUD-874,
  GITHUB-1242)
  [Miguel Caballer]

- [OpenStack] Implement OpenStack_2_NodeDriver ex_list_snapshots (LIBCLOUD-874,
  GITHUB-1242)
  [Miguel Caballer]

- [OpenStack] Implement OpenStack_2_NodeDriver create_volume_snapshot
  (LIBCLOUD-874, GITHUB-1242)
  [Miguel Caballer]

- [OpenStack] Implement OpenStack_2_NodeDriver destroy_volume_snapshot
  (LIBCLOUD-874, GITHUB-1242)
  [Miguel Caballer]

- [OpenStack] Implement OpenStack_2_NodeDriver ex_list_security_groups
  (LIBCLOUD-874, GITHUB-1242)
  [Miguel Caballer]

- [OpenStack] Implement OpenStack_2_NodeDriver ex_create_security_group
  (LIBCLOUD-874, GITHUB-1242)
  [Miguel Caballer]

- [OpenStack] Implement OpenStack_2_NodeDriver ex_delete_security_group
  (LIBCLOUD-874, GITHUB-1242)
  [Miguel Caballer]

- [OpenStack] Implement OpenStack_2_NodeDriver ex_create_security_group_rule
  (LIBCLOUD-874, GITHUB-1242)
  [Miguel Caballer]

- [OpenStack] Implement OpenStack_2_NodeDriver ex_delete_security_group_rule
  (LIBCLOUD-874, GITHUB-1242)
  [Miguel Caballer]

- [OpenStack] Implement OpenStack_2_NodeDriver ex_list_floating_ip_pools
  (LIBCLOUD-874, GITHUB-1242)
  [Miguel Caballer]

- [OpenStack] Fix parse_error if 'code' not in API response message
  (GITHUB-1242)
  [Miguel Caballer]

- [OpenStack] Adapt _to_port function to work with old OpenStack versions
  (GITHUB-1242)
  [Miguel Caballer]

- [OpenStack] Use SUSPENDED NodeState in OpenStack driver (GITHUB-1269)
  [Miguel Caballer]

- [UpCloud] Update documentation for UpCloud driver (LIBCLOUD-1026,
  GITHUB-1259)
  [Ilari Mäkelä]

- [NTT CIS] Fix indenting in ex_initiate_drs_failover docstring (GITHUB-1271)
  [Rick van de Loo]

- [NTT CIS] Change endpoint 'canada' to 'ca' in libcloud/common/nttcis.py
  (GITHUB-1270)
  [Mitch Raful]

- [OpenStack] Fix ``detach_volume`` method so it works with v2 volumes.
  (GITHUB-1267)
  [Rick van de Loo]

- [CloudSigma] Fix CloudSigma driver so it correctly handles subscription
  objects without the ``start_time`` and / or ``end_time`` attribute.
  (GITHUB-1284, LIBCLOUD-1040)
  [aki-k, Tomaz Muraus]

Storage
~~~~~~~

- [Azure] Fix ``upload_object_via_stream`` method so it also works with
  iterators which don't implement ``seek()`` method. If the iterator doesn't
  support seek, entire iterator content will be buffered in memory.
  (LIBCLOUD-1043, GITHUB-1287)
  [Clemens Wolff]
- [CloudFiles] Fix ``download_object_as_stream`` method in the CloudFiles
  driver. This regression / bug was inadvertently introduced when migrating
  code to ``requests``.
  (LIBCLOUD-1039, GITHUB-1283)
  [Matt Seymour]
- [CloudFiles] Fix a bug with ``ChunkStreamReader`` class and make sure file
  descriptor is also closed if the iterator isn't fully exhausted or if the
  iterator is never read from.

  NOTE: This potential open file descriptor leakage only affected code which
  utilized ``ex_multipart_upload_object`` method.
  [Tomaz Muraus]

Container
~~~~~~~~~

- [Docker] Improve docstring for RegistryClient (GITHUB-1254)
  [Ken Dreyer]

DNS
~~~

- Add new driver for RcodeZero DNS (GITHUB-1256, LIBCLOUD-1025)
  [MikeAT]
- [DigitalOcean] Update DigitalOcean driver so it supports ``ttl`` attribute for
  ``Record`` objects. This includes support for specifying a record ttl via
  ``extra['ttl']`` attribute when creating and updating a record. (GITHUB-1252
  LIBCLOUD-1022) [Kevin Roy]

Storage
~~~~~~~

- Adds missing docs for param ex_prefix & adds to DummyStore. Add ex_prefix
  kwarg to the `list_container_objects` methods in the base and dummy classes.
  (GITHUB-1275)
  [RichardARPANET]

Changes in Apache Libcloud 2.4.0
--------------------------------

- Refuse installation with Python 2.6 and Python 3.3 (support was
  already dropped in Libcloud 2.3.0)

- Support Python 3.7 (GITHUB-1227, GITHUB-1236)
  [Andreas Hasenack, Andrew Starr-Bochicchio, Quentin Pradet]

- Cleanup various Python files
  (GITHUB-1182, GITHUB-1183, GITHUB-1185, GITHUB-1186, GITHUB-1187, GITHUB-1188)
  [Rémy Léone]

- Allow running tests with http_proxy set (GITHUB-1236)
  [Andreas Hasenack]

Common
~~~~~~

- [OpenStack] Document openstack_connection_kwargs method (GITHUB-1219)
  [Ken Dreyer]

- [OpenStack] Handle missing user email in OpenStackIdentityUser (GITHUB-1249)
  [Ken Dreyer]

Compute
~~~~~~~

- [ARM] Support OS disk size definition on node creation (GITHUB-1196)
  [Vojta Bartoš]

- [Digital Ocean] Support floating IPs (GITHUB-1177)
  [Rick van de Loo]

- [Digital Ocean] Support attach/detach for floating IPs (GITHUB-1191)
  [Rick van de Loo]

- [Digital Ocean] Add ex_get_node_details (GITHUB-1221)
  [Rick van de Loo]

- [Digital Ocean] Add tags extra attribute to create_node (GITHUB-1212)
  [Nikita Chebykin]

- [Dimension Data] Fix IndexError in list_images (GITHUB-1171)
  [Adam Friedman]

- [EC2] Add AWS eu-west-3 (Paris) region (GITHUB-1175)
  [Anthony Monthe]

- [EC2] Add description to ex_authorize_security_group_ingress (GITHUB-1122)
  [Arturo Noha]

- [EC2] Added script to automatically get EC2 instance sizes (GITHUB-1211)
  [Anthony Monthe, Quentin Pradet]

- [EC2] Update instance sizes (GITHUB-1238)
  [Ward Vandewege]

- [EC2] Accept tags when create a snapshot (LIBCLOUD-1014, GITHUB-1240)
  [Rafael Gonçalves]

- [GCE] Expand Firewall options coverage (LIBCLOUD-960, GITHUB-1144)
  [maxlip]

- [GCE] Expand network and subnetwork options coverage (LIBCLOUD-985,
  GITHUB-1181)
  [maxlip]

- [GCE] Extend ex_create_address to allow internal ip creation (GITHUB-1174)
  [Jeremy Solarz]

- [GCE] Allow shared VPC in managed instance group creation (GITHUB-1179)
  [Boris Chazalet]

- [GCE] Support disk_size parameter for boot disk when creating instance
  (LIBCLOUD-973, GITHUB-1162)
  [Rahul Paigavan]

- [GCE] Update public image projects list (LIBCLOUD-961, GITHUB-1143)
  [Sean Marlow]

- [GCE] Fix _find_zone_or_region for >500 instances (GITHUB-1203)
  [Léo Ferlin-Sutton]

- [GCE] Allow routing_mode=None in ex_create_network (GITHUB-1217)
  [Daniel Hunsaker]

- [OpenStack] Implement Glance Image API v2 (GITHUB-1151)
  [Rick van de Loo]

- [OpenStack] Fix spelling in ex_files description (GITHUB-1197)
  [Ken Dreyer]

- [OpenStack v2] Allow listing image members (GITHUB-1172)
  [Rick van de Loo]

- [OpenStack v2] Allow creating and accepting image members (GITHUB-1176)
  [Rick van de Loo]

- [OpenStack v2] Fix image members methods (GITHUB-1190)
  [Rick van de Loo]

- [OpenStack] Fix API doc for delete_floating_ip (GITHUB-1218)
  [Ken Dreyer]

- [OpenStack] Implement port attaching/detaching (GITHUB-1225)
  [Rick van de Loo]

- [OpenStack] Add methods for getting and creating ports (GITHUB-1226)
  [Alexander Grooff]

- [OpenStack] Add get_user method (GITHUB-1216)
  [Ken Dreyer]

- [OpenStack] Add ex_list_subnets to OpenStack_2_NodeDriver (GITHUB-1215,
  LIBCLOUD-604)
  [Miguel Caballer]

- [OpenStack] The OpenStack_2_NodeDriver uses two connections (GITHUB-1215,
  LIBCLOUD-997)
  [Miguel Caballer]

- [OpenStack] The OpenStack_2_NodeDriver /v2.0/networks instead of /os-networks
  (GITHUB-1215, LIBCLOUD-998)
  [Miguel Caballer]

- [Scaleway] New Scaleway driver (GITHUB-1121, GITHUB-1220)
  [Daniel Hunsaker, Nándor István Krácser, Rémy Léone]

- [Scaleway] Update Scaleway default API host (GITHUB-1239)
  [Rémy Léone]

DNS
~~~

- [Google Cloud DNS] Document driver instantiation (GITHUB-1198)
  [Gareth McFarlane]

Storage
~~~~~~~

- Update docstring for storage provider class (GITHUB-1201)
  [Clemens Wolff]

- [Azure Blob Storage] Allow filtering lists by prefix (LIBCLOUD-986,
  GITHUB-1193)
  [Joshua Hawkinson]

- [Azure Blob Storage] Update driver documentation (GITHUB-1208)
  [Clemens Wolff]

- [Azure Blob Storage] Fix upload/download streams (GITHUB-1231)
  [Michael Perel]

- [Azure Blob Storage] Fix PageBlob headers (GITHUB-1237)
  [Andreas Hasenack]

- [S3] Guess s3 upload content type (LIBCLOUD-958, GITHUB-1195)
  [Iuri de Silvio]

- [S3] Add Amazon S3 (cn-northwest-1) Storage Driver (GITHUB-1241)
  [@yangkang55]

Other
~~~~~

- Fixed spelling in 2.0 changes documentation (GITHUB-1228)
  [Jimmy Casey]

Changes in Apache Libcloud 2.3.0
--------------------------------

- Drop support for Python 2.6 and Python 3.3
  They're no longer supported, and the Python ecosystem is starting to
  drop support: two of our test dependencies no longer support them.
  [Quentin Pradet]

- Made pytest-runner optional (GITHUB-1167)
  [Vlad Glagolev]

Common
~~~~~~

- Improve warning when CA_CERTS_PATH is incorrectly passed as a list
  (GITHUB-1118)
  [Quentin Pradet]

- Cleaned up and corrected third-party drivers documentation (GITHUB-1148)
  [Daniel Hunsaker]

- Modernized a few Python examples (GITHUB-1164)
  [Batuhan Osman Taşkaya]

- [OpenStack] Authentify with updated Identity API
  (LIBCLOUD-965, GITHUB-1145)
  [Miguel Caballer]

Compute
~~~~~~~

- Fix "wait_until_running() method so it also works correctly and doesn't
  append "None" to the addresses list if node has no IP address.
  (GITHUB-1156, LIBCLOUD-971)
  [Tobias Paepke]

- [ARM] Fix checking for "location is None" in several functions (LIBCLOUD-926,
  GITHUB-1098)
  [Sameh Elsharkawy]

- [ARM] Fix error when using SSH key auth with Python 3 (GITHUB-1098)
  [Sameh Elsharkawy]

- [ARM] Fix API call on powerOff, understand PAUSED state (GITHUB-1003)
  [Markos Gogoulos]

- [ARM] Delete VHDs more reliably in destroy_node(), raise exception on
  unhandled errors (GITHUB-1120)
  [Lucas Di Pentima]

- [ARM] Fix api version used to list and delete NICs (GITHUB-1128)
  [Peter Amstutz]

- [ARM] Allow faster list_nodes() with ex_fetch_power_state=False
  (GITHUB-1126)
  [Peter Amstutz, Lucas Di Pentima]

- [ARM] Fix delete_old_vhd (GITHUB-1137)
  [Peter Amstutz, Lucas Di Pentima]

- [ARM] Limit number of retries in destroy_node (GITHUB-1134)
  [Peter Amstutz, Lucas Di Pentima]

- [ARM] Fix Retry-After header handling (GITHUB-1139)
  [Lucas Di Pentima]

- [CloudStack] Handle NICs without addresses (GITHUB-1141)
  [Pierre-Yves Ritschard]

- [CloudStack] Add change size and restore (LIBCLOUD-975, GITHUB-1166)
  [Mauro Murari]

- [Digital Ocean] Add ex_enable_ipv6 in DigitalOcean_v2 driver
  (GITHUB-1130)
  [Rick van de Loo]

- [Digital Ocean] Add support for tags in list_nodes()
  (LIBCLOUD-967, GITHUB-1149)
  [Mike Fischer]

- [Digital Ocean] Add rebuild and resize commands
  (LIBCLOUD-977, GITHUB-1169)
  [Adam Wight]

- [EC2] Add new x1.16xlarge and x1e.32xlarge instance type. (GITHUB-1101)
  [Anthony Monthe]

- [EC2] Add AWS EC2 c5 series (GITHUB-1147)
  [Anthony Monthe]

- [EC2] Add AWS EC2 M5 sizes (GITHUB-1159)
  [Anthony Monthe]

- [EC2] Update pricing information for EC2 instances.
  [Tomaz Muraus]

- [EC2] Allow cn-north-1 even without pricing information
  (LIBCLOUD-954, GITHUB-1127)
  [Quentin Pradet]

- [EC2] Fix EBS volume encryption (GITHUB-1008)
  [Sergey Babak]

- [ECS Aliyun] Support modify_security_group_attributes (GITHUB-1157)
  [Zhang Yiming]

- [GCE] Allow adding labels to images (GITHUB-1138)
  [Katriel Traum, Eric Johnson]

- [GCE] Allow adding license strings to images (GITHUB-1136)
  [Katriel Traum, Eric Johnson]

- [GCE] Support GCE node labels. (LIBCLOUD-934, GITHUB-1115)
  [@maxlip]

- [GCE] Fix `GCEList` pagination. (GITHUB-1095)
  [Yap Sok Ann]

- [GCE] Allow setting service account in instance templates (LIBCLOUD-947,
  GITHUB-1108)
  [Evan Carter]

- [GCE] Add support for private IP addresses in GCE instance creation
  (LIBCLOUD-944, GITHUB-1107)
  [Gareth Mcfarlane]

- [GCE] Allow for use of shared network (VPC) and subnetwork (GITHUB-1165)
  [Boris Chazalet]

- [GCE] Add support for accelerators (LIBCLOUD-963, GITHUB-1163)
  [Michael Johnson]

- [ProfitBricks] Update driver and add support for the new API v4. (GITHUB-1103)
  [Nurfet Becirevic]

- [ProfitBricks] Fix list_snapshots() method (GITHUB-1153)
  [Chad Phillips]

- [UpCloud] New driver for UpCloud (LIBCLOUD-938, GITHUB-1102)
  [Mika Lackman, Ilari Mäkelä]

- [UpCloud] Use disk size and storage tier also when creating node from template
  (LIBCLOUD-952, GITHUB-1124)
  [Mika Lackman]

- [UpCloud] Allow to define hostname and username
  (LIBCLOUD-951, LIBCLOUD-953, GITHUB-1123, GITHUB-1125)
  [Mika Lackman]

- [UpCloud] Add pricing information to list_sizes (LIBCLOUD-969, GITHUB-1152)
  [Mika Lackman]

Storage
~~~~~~~

- Added Digital Ocean Spaces driver (LIBCLOUD-955, GITHUB-1129)
  [Andrew Starr-Bochicchio]

- [Digital Ocean Spaces] Add support for AMS3 region (GITHUB-1142)
  [Andrew Starr-Bochicchio]

- [Digital Ocean Spaces] Add support for SGP1 region (GITHUB-1168)
  [Andrew Starr-Bochicchio]

- Fix a bug / regression which resulted in increased memory consumption when
  using ``download_object`` method. This method would store whole object
  content in memory even though there was no need for that.

  This regression was introduced in 2.0.0 when we moved to using ``requests``
  library.
  (GITHUB-1132)
  [Quentin Pradet]

- Fix a regression with hash computation performance and memory usage on object
  upload inadvertently introduced in 2.0.0 and make it more efficient.
  (GITHUB-1135)
  [Quentin Pradet]

Changes in Apache Libcloud 2.2.1
--------------------------------

Common
~~~~~~

- Fix an issue with installation failing on some operating system and file
  systems combinations (e.g. ecryptfs layered on top of ext4) which don't
  support file names longer than 143 characters. (LIBCLOUD-946, GITHUB-1112)

  Reported by Cyrille Verrier.
  [Tomaz Muraus]

Compute
~~~~~~~

- [EC2] add g3 instance types
  [GITHUB-1101]
  (@zulupro)

- [EC2] add 'end' to ec2 reserved_node
  [GITHUB-1099]
  (@xofer)

- Decrease sleep delay (from 1.5 to 0.2 seconds) inside paramiko client which
  is used to prevent busy waiting while waiting for data on the channel.

  This should cause deploy scripts which produce a lot of output in incremental
  manner to finish faster.
  [Tomaz Muraus]

- Fix a regression in the Azure ARM driver which didn't allow custom storage
  URI suffix to be used with create_node. (GITHUB-1110)
  [Lucas Di Pentima]

Tests
~~~~~

- Make sure we normalize header values and cast all the numbers to strings in
  base connection classes used by tests. (LIBCLOUD-945, GITHUB-1111)

  Reported by Erich Eckner.
  [Tomaz Muraus]

Changes in Apache Libcloud 2.2.0
--------------------------------

Compute
~~~~~~~

- [EC2] add g3 instance types
  [GITHUB-1101]
  (@zulupro)

- [EC2] add 'end' to ec2 reserved_node
  [GITHUB-1099]
  (@xofer)

Changes in Apache Libcloud 2.2.0
--------------------------------

Common
~~~~~~

- [GCE] Scrape prices for GCE Australia Region
  [GITHUB-1085]
  (Francisco Ros)

Compute
~~~~~~~

- [ARM] Add option to create static public IP
  [GITHUB-1091, LIBCLOUD-918]
  (Aki Ketolainen)

- [SOFTLAYER] Add `get_image` method to class
  [GITHUB-1066]
  (Francois Regnoult)

- [ARM] Add Storage support, volumes, snapshots
  [GITHUB-1087]
  (Sergey Babak)

Container
~~~~~~~~~

- [DOCKER] Fixes to support TLS connection
  [GITHUB-1067]
  (johnnyWalnut)

DNS
~~~

- [ROUTE53] Fix for TXT and SPF records, when user didn't escapsulate data in
  quotes, the API would fire error. As reported by @glyph
  [LIBCLOUD-875, GITHUB-1093]
  (Anthony Shaw)

- [LINODE] Add priority to the extra dictionary in record instances
  [GITHUB-1088]
  (@mete0r)

Load Balancer
~~~~~~~~~~~~~

- Fixed AWS ALB/ELB driver init method to instantiate nested connection object
  properly
  [LIBCLOUD-936, GITHUB-1089]
  (Anton Kozyrev)

Storage
~~~~~~~

- [CLOUDFILES] Update OpenStackSwiftConnection to work with auth version 3.0
  [GITHUB-1068]
  (Hakan Carlsson)

- [CLOUDFILES] Add SSL URI support
  [GITHUB-1076, LIBCLOUD-458]
  (@ayleph)

Changes in Apache Libcloud 2.1.0
--------------------------------

Common
~~~~~~

- [AWS] Update prices and fix some region names
  [GITHUB-1056]
  (Francisco Ros)

- Fix bug in utils.decorators wrap exception method, used by vsphere driver
  [GITHUB-1054]
  (Anthony Shaw)

- Use PyTest as the unit testing runner
  (Anthony Shaw)

- Use of LXML is now disabled by defalt, use
  ``libcloud.utils.py3.DEFAULT_LXML = True`` to reenable. LXML has
  compatibility issues with a number of drivers and etree is a standard
  package.
  [GITHUB-1038]
  (Anthony Shaw)

- Switch RawResponse class to use content body instead of text body, up to 10x
  performance improvement for methods like StorageDriver.download_object
  [GITHUB-1053]
  (Quentin Pradet)

Compute
~~~~~~~

- [OPENSTACK] Add support for Nova 2.x and Keystone 3
  [GITHUB-1052]
  (Anthony Shaw)

- [GCE] Add loadBalancingScheme parameter for
  ex_create_forwarding_rule method in GCE driver.
  [GITHUB-1079]
  (@sT331h0rs3)

- [GCE] Fix error codes not being parsed in certain scenarios
  [GITHUB-1074, LIBCLOUD-925]
  (micafer)

- [EC2] Fix node's Block Device Mapping was parsed from incorrect mapping.
  EbsInstanceBlockDevice is different from EbsBlockDevice.
  [GITHUB-1075]
  (Gennadiy Stas)

- [GANDI] Fixes the location name in image and instance type classes
  [GITHUB-1065]
  (Sayoun)

- [GCE] Fix method for create instance properties, it previously ignored the
  disk type parameter and defaulted to pd-standard.
  [GITHUB-1064]
  (Evan Carter)

- Fix missing return data from EC2 billing product methods
  [GITHUB-1062]
  (Alex Misstear)

- Handle [VULTR] API rate limiting
  [GITHUB-1058]
  (Francisco Ros)

- Fix Kili driver not correctly fixing the auth version for openstack to
  2.0_password
  [GITHUB-1054]
  (Anthony Shaw)

- [EC2] Add i3 instance types for AWS
  [GITHUB-1038]
  (Stephen Mullins)

- [VULTR] Extend extra dict of Vultr sizes to include additional fields
  (plan_type and available_locations)
  [GITHUB-1044]
  (Francisco Ros)

Container
~~~~~~~~~

- New driver for Google Container Engine
  [GITHUB-1059]
  (Andy Maheshwari)

- [KUBERNETES] Fix get_container method responding with None
  [GITHUB-1054]
  (Anthony Shaw)

- [DOCKER] Fix for start_container method
  [GITHUB-1049]
  (@johnnyWalnut)

- [DOCKER] fix add an extra check otherwise list_containers breaks with
  AttributeError when fromImages is specified
  [GITHUB-1043]
  (@johnnyWalnut)

Storage
~~~~~~~

- [S3] Fix raise in s3.upload_object_via_stream
  [LIBCLOUD-914, GITHUB-1055]
  (Quentin Pradet)

Changes in Apache Libcloud 2.0.0
--------------------------------

Common
~~~~~~

- Fix OpenStack drivers not correctly setting URLs when used with identity API,
  would default to 127.0.0.1 and service catalog URLs were not adhered to.
  [GITHUB-1037, LIBCLOUD-912, LIBCLOUD-904]
  (Anthony Shaw)

- Fix Aliyun ECS, Load balancer and storage adapters when using unicode UTF-8
  characters in the names of resources in 2.0.0rc2 < it would fail as a
  MalformedResponseError, Python 2.7 element tree was raising a unicode error
  [GITHUB-1032] [GITHUB-994]
  (Anthony Shaw)

- Refactor the test classes to use the full libcloud.http and
  libcloud.common.base modules, with Connection, Response all used with
  requests_mock. This increases our test coverages and catches bugs in
  drivers' custom parse_body and auth modules
  [GITHUB-1031]
  (Anthony Shaw)

- Rename libcloud.httplib_ssl to libcloud.http now that we don't use httplib
  [GITHUB-1028]
  (Anthony Shaw)

Compute
~~~~~~~

- [GOOGLE] Add test to check that can create a GCE volume at a given location
  [GITHUB-1048]
  (Francisco Ros)

- [GOOGLE] Fix GCENodeDriver.ex_get_volume() when zone param is of class
  GCEZone or NodeLocation
  [GITHUB-1047]
  (Francisco Ros)

- [GOOGLE] Fix call to GCENodeDriver._ex_populate_volume_dict
  [GITHUB-1046]
  (Francisco Ros)

- [ARM] Add support for Azure Cloud Environments as well as Locations
  [GITHUB-969]
  (Peter Amstutz)

- [EC2] Add support for ModifyVolume and DescribeVolumesModifications
  [GITHUB-1036]
  (Hennadii Stas)

- [ARM] Fix string representation of the VhdImage type and fix listing of
  Public IP addresses
  [GITHUB-1035]
  (Anthony Shaw)

- [GOOGLE] Remove validation checks for guestOsFeatures
  [GITHUB-1034]
  (Max Illfelder)

- [VSPHERE] Fix issue with authentication methods crashing
  [GITHUB-1031]
  (Anthony Shaw)

- [ARM] Add network security groups to azure ARM
  [GITHUB-1033]
  (Joseph Hall)

- [ARM] Add the ability to list resource groups
  [GITHUB-1032]
  (Joseph Hall)

- Add 1&1 compute driver
  [LIBCLOUD-911] [GITHUB-1029]
  (Jasmin Gacic)

- Fix Azure ARM driver condition for ex_list_publishers where location is
  specified
  [GITHUB-1030]
  (Joseph Hall)

- Added Import Snapshot and Describe Import Snapshot to EC2 compute driver
  [GITHUB-1023]
  (Nirzari Iyer)

- Add price_monthly extra param to digitalocean sizes
  [GITHUB-1021]
  (Francisco Ros)

- Add aliyun ecs instance join leave security group
  [GITHUB-992]
  (Jie Ren)

- Add keypair management to OnApp driver
  [GITHUB-1018]
  (Tinu Cleatus)

- Add missing regions in AWS storage and compute drivers
  [GITHUB-1019]
  (Alex Misstear)

- Add SR-IOV net support to images in EC2 compute driver
  [GITHUB-1020]
  (Alex Misstear)

- Fix - update t2.small image size from 11 CPU to 1
  [GITHUB-1022]
  (Francisco Ros)

- Added Billing Product for image in EC2 compute driver
  [GITHUB-1024]
  (Nirzari Iyer)

DNS
~~~

- Add OnApp driver
  [GITHUB-1017] [LIBCLOUD-907]
  (Tinu Cleatus)

Changes in Apache Libcloud 2.0.0rc2
-----------------------------------

Common
~~~~~~

- Fix LIBCLOUD_DEBUG trying to decompress already decompressed responses
  [LIBCLOUD-910]
  (Anthony Shaw)

- Added an integration test API and a test suite for validating functionality
  without mocking any libcloud subsystems
  [GITHUB-970]
  (Anthony Shaw)

- Fix for Linode classes since 2.0x
  [GITHUB-1026]
  (Anthony Shaw)

- Fix CertificateConnection not correctly signing requests in 2.0rc1, impacted
  Azure classic driver, OpenStack and Docker driver
  [GITHUB-1015]
  (Anthony Shaw)

- Change Cloudscale to cloudscale.ch.
  [GITHUB-993]
  (David Halter)

- Explicitly check if response is None in RawResponse class
  [GITHUB-1006] [LIBCLOUD-901]
  (Richard Xia)

Compute
~~~~~~~

- Outscale SAS doc improvements and logo update
  [GITHUB-950]
  (Javier M Mellid)

- [GCE] Allow preemptible instances to be created
  [GITHUB-954]
  (John Baublitz)

- Add support for forcing detachment of EBS volumes to EC2 driver
  [GITHUB-1007]
  (Sergey Babak)

- Fix Public IP not assigned when creating NIC on Azure ARM
  [GITHUB-1013] [LIBCLOUD-906]
  (Simone Ripamonti)

- [ONAPP] Add list images support for OnApp driver
  [GITHUB-1011]
  (Tinu Cleatus)

- [EC2] Add r4 instance types for AWS
  [GITHUB-997]
  (Jens Deppe)

- [EC2] support for AWS eu-west-2 and ca-central-1 regions
  [GITHUB-1009]
  (Marat Komarov)

- [EC2] Add P2 GPU instance types
  [GITHUB-996]
  (MJK)

- [EC2] Add method to modify snapshot attribute for EC2
  [GITHUB-990]
  (Sayan Chowdhury)

- [Linode] Add start, stop instance methods and fix incorrect state TERMINATED
  to STOPPED
  [GITHUB-986]
  (Markos Gogoulos)

- [EC2] Add ENA support for EC2 compute images
  [GITHUB-983]
  (Alex Misstear)

- [Azure ARM] fix typeerror on ex_list_nics
  [GITHUB-979]
  (Choi Jongu)

- [GCE] allow delete instances from managed group
  [GITHUB-975]
  (@zacharya19)

Storage
~~~~~~~

- Reintroduce S3 multipart upload support with signature v4
  [GITHUB-1005] [LIBCLOUD-834]
  (Alex Misstear)


Changes Apache Libcloud 2.0.0rc1
--------------------------------

Common
~~~~~~

- Fix DEBUG mode, also add support for using io.StringIO as the file handle
  when calling libcloud.enable_debug.
  (GITHUB-978, LIBCLOUD-887)
  [Anthony Shaw]

- Introduction of the requests package as the mechanism for making HTTP
  requests for all drivers.
  (GITHUB-928)
  [Anthony Shaw]

- Fix bug where custom port and secure flag would not get propagated to
  connection class.
  (GITHUB-972)
  [Anthony Shaw]

- Fix bug where custom port would not get propagated to connection.
  (GITHUB-971)
  [Anthony Shaw]

- Fix bug where instantiating a connection from URL and then requesting an
  action with a leading / would lead to a malformed URL.
  (GITHUB-976)
  [Anthony Shaw]

Compute
~~~~~~~

- Fix a bug in profitbricks driver where listing snapshots would request a
  malformed URL.
  [GITHUB-976]
  (Anthony Shaw)

- Fix LIBCLOUD-806 bug where vsphere driver cannot be instantiated.
  (GITHUB-967)
  [Anthony Shaw]

- [google compute] Improve performance of list nodes by caching volume
  information.
  (GITHUB-813, LIBCLOUD-826)
  [Tom Melendez]

Changes in Apache Libcloud 1.5.0
--------------------------------

Common
~~~~~~

- Set Dimension Data compute, backup and load balancer to default to 2.4 API.
  (GITHUB-961)
  [Samuel Chong]

Compute
~~~~~~~

- [azure] New method for accessing rate cards.
  (GITHUB-957)
  [Soren L. Hansen]

- [gce] Allow multiple preemptible instances to be created.
  (GITHUB-954)
  [John Baublitz]

- [openstack] Add new Connection class to support VOMS proxys to keystone
  servers.
  (GITHUB-959)
  [micafer]

- [outscale] Added support for changed API for describing quotas.
  (GITHUB-960)
  [Javier M. Mellid]

- [ec2] Added m4 instances to us-gov and brazil, added m4.16xlarge to all.
  (GITHUB-964)
  [Matthew Tyas]

- Add new CloudScale.ch driver
  (GITHUB-951)
  [Dave Halter]

- [google compute] Bug fix for ex_create_multiple_nodes Google Cloud disk auto
  delete.
  (GITHUB-955)
  [John Baublitz]

- [google compute] Add "MULTI_IP_SUBNET" guestOsFeatures option.
  (GITHUB-956)
  [Max Illfelder]

- [dimensiondata] Added support for 2.4 API, added support for image import,
  cloning. Add feature for changing NIC VLANs, add feature for changing NIC
  order for a server.
  (GITHUB-953)
  [Samuel Chong]

- [ec2] Add US-EAST2 (Ohio).
  (GITHUB-946)
  [Matthew Harris]

- [google compute] Fix to allow multiple node creation with subnets.
  (GITHUB-949)
  [John Baublitz]

Container
~~~~~~~~~

- [rancher] The scheme (secure) and port no longer need to be explicitly
  specified, allowing a user to simply copy in the string provided to them
  from Rancher.
  (GITHUB-958)
  [Matthew Ellison]

Changes in Apache Libcloud 1.4.0
--------------------------------

Compute
~~~~~~~

- Introduce new Azure ARM driver.
  [Peter Amstulz]

- [ec2] Fix the bug that created the node at ecs driver and implement the
  method for creating public ip.
  (GITHUB-943)
  [watermelo]

- [profitbricks] changes to the ProfitBricks compute driver to drop support
  for the old SOAP api (now end of life) and provide support for v3 of the
  REST api.
  (GITHUB-938)
  [Matt Finucane]

- [cloudsigma] Added Warsaw (waw) region.
  (GITHUB-942)
  [Kamil Chmielewski]

- [google compute] List images fix for projects > 500 images.
  (GITHUB-939)
  [Scott Crunkleton]

- [ec2] Add st1 and sc1 volume types to valid types.
  (GITHUB-925)
  [Sean Goller]

- [digital ocean] add ex_change_kernel in DigitalOcean_v2 driver.
  (GITHUB-922)
  [Rick van de Loo]

- [digital ocean] add ex_hard_reboot in DigitalOcean_v2 driver.
  (GITHUB-920)
  [Rick van de Loo]

- [openstack] add ex_start_node for the openstack driver.
  (GITHUB-919)
  [Rick van de Loo]

- [vultr] Extra Attributes for Node Creation on Vultr.
  (GITHUB-917)
  [Fahri Cihan Demirci]

- [vultr] Implement SSH Key Create/Delete Methods for Vultr.
  (GITHUB-914)
  [Fahri Cihan Demirci]

- [dimension data] No longer throw error when powering off a node that is
  already stopped.
  (GITHUB-912)
  [Samuel Chong]

- [dimension data] Refactor create_node for MCP2 to support CaaS API 2.3 feature.
  Can now specify Network Adapter Name for primary and additional NIC.
  Parameters in create_node function is tailored for MCP2.
  (GITHUB-902)
  [Samuel Chong]

- Volume snapshot operations, i.e. creating, listing and deleting volume
  snapshots, for the Digital Ocean driver.
  (LIBCLOUD-861, GITHUB-909)
  [Fahri Cihan Demirci]

- Added snapshot management to OVH compute.
  (GITHUB-897)
  [Anthony Monthe]

- [GCE] Support for HTTP(S) proxies with BackendServices.
  (GITHUB-856)
  [Tom Melendez]

Container
~~~~~~~~~

- [docker] As reported in the corresponding bug, the docker daemon will respond
  in an install_image call with all the messages produced during the procedure
  parsed as json docs. In that case the response headers also contain the value
  'transfer-encoding':'chunked'. That kind of response can now be parsed
  properly by the DockerResponse parse_body method. Also, another small change
  is that previously the id of the new image was marked in the json document as
  id, but now it's marked as sha256, so the regex used to discover the id has
  been updated.
  (GITHUB-918)
  [Pavlos Tzianos]

Load Balancing
~~~~~~~~~~~~~~

- Introduce AWS Application Load Balancer (ALB) driver.
  (LIBCLOUD-869, GITHUB-936)
  [Anton Kozyrev]

- Fix bug where GCE Load balancer supposes that all VMs have public ips.
  (LIBCLOUD-879, GITHUB-952)
  [Chris Walker]

Storage
~~~~~~~

- [s3] Add AP-Southeast2 as region.

- [google] Prevent GCE auth to hide S3 auth.
  (GITHUB-921)
  [Quentin Pradet]

- [GCS] Fixed some google_storage.py URL cleaning.
  (GITHUB-901)
  [Scott Crunkleton]

Changes in Apache Libcloud 1.3.0
--------------------------------

General
~~~~~~~

- Introduced new base API for instantiating drivers.
  (GITHUB-822)
  [Anthony Shaw]

- Added certificate path for SLES12/OpenSUSE12.
  (GITHUB-884)
  [Michael Calmer]

- Deprecate DigitalOcean v1 API support in favour of v2 API.
  (GITHUB-889, GITHUB-892)
  [Andrew Starr-Bochicchio]

- Deprecate RunAbove cloud drivers in favour of new OVH cloud driver.
  (GITHUB-891)
  [Anthony Monthe]


Compute
~~~~~~~

- Fix reporting function for detailed admin logs in Dimension Data Driver.
  (GITHUB-898)
  [Anthony Shaw]

- Added edit firewall functionality to Dimension Data driver.
  (GITHUB-893)
  [Samuel Chong]

- Bugfix - Fixed listing nodes issue in Python 3.
  (LIBCLOUD-858, GITHUB-894)
  [Fahri Cihan Demirci]

- Added FCU (Flexible Compute Unit) support to the Outscale driver.
  (GITHUB-890)
  [Javier M. Mellid]

- [google compute] Add "WINDOWS" guestOsFeatures option.
  (GITHUB-861)
  [Max Illfelder]

- When creating volumes on OpenStack with defaults for `location` or
  `volume_type`, newer OpenStack versions would throw errors. The OpenStack
  driver will now only post those arguments if non-`NoneType`.
  (GITHUB-857)
  [Allard Hoeve]

- When fetching the node details of a non-existing node, OpenStack would raise
  a `BaseHTTPError` instead of returning `None`, as was intended. Fixed tests
  and code.
  (GITHUB-864)

- Added `ex_stop_node` to the OpenStack driver.
  (GITHUB-865)
  [Allard Hoeve]

- When creating volume snapshot, the arguments `name` and `description` are
  truely optional when working with newer OpenStack versions. The OpenStack
  driver will now only post thost arguments if they are non-`NoneType`.
  (GITHUB-866)
  [Allard Hoeve]

- StorageVolumeSnapshot now has an attribute `name` that has the name of the
  snapshot if the provider supports it. This used to be `.extra['name']`, but
  that is inconsistent with `Node` and `StorageVolume`. The `extra` dict still
  holds `name` for backwards compatibility.
  (GITHUB-867)
  [Allard Hoeve]

Container
~~~~~~~~~

- Introduced new Rancher driver
  (GITHUB-876)
  [Mario Loria]

- Fixed bug in Docker util library for fetching images from the docker hub API.
  API was returning 301 and redirects were not being followed.
  (GITHUB-862)
  [Anthony Shaw]

Load Balancer
~~~~~~~~~~~~~

- Added fetch tags support in elb driver.
  (GITHUB-848)
  [Anton Kozyrev]

Storage
~~~~~~~

- Added storage permissions for Google Cloud Storage.
  (GITHUB-860)
  [Scott Crunkleton]

Changes in Apache Libcloud 1.2.1
--------------------------------

Backup
~~~~~~

- Fix issue enabling backups on Dimension Data driver.
  (GITHUB-858)
  [Mark Maglana, Jeff Dunham, Anthony Shaw]

Changes in Apache Libcloud 1.2.0
--------------------------------

General
~~~~~~~

- Fix caching of auth tokens in the Google Compute Engine drivers. Now we make
  sure that the file is truncated before writing a new token. Not truncating
  the file would cause issues if the new token is shorted then the existing one
  which is cached in the file.
  (GITHUB-844, LIBCLOUD-835)
  [Paul Tiplady]

Compute
~~~~~~~

- [gce] Fix image undeprecation in GCE.
  (GITHUB-852)
  [Max Illfelder]

- [gce] Added Managed Instance Groups.
  (GITHUB-842)
  [Tom Melendez]

- [gce] Allow undeprecation of an image.
  (GITHUB-851)
  [Max Illfelder]

- [cloudstack] BUGFIX Values with wildcards failed signature validation.
  (GITHUB-846)
  [Ronald van Zantvoot]

- [cloudstack] Added StorageState-Migrating to the cloudstack driver.
  (GITHUB-847)
  [Marc-Aurèle Brothier]

- [google compute] Update copy image logic to match create image.
  (GITHUB-828)
  [Max Illfelder]

- Removed HD attribute from the Abiquo compute driver to support the 3.4 API.
  (GITHUB-840)
  [David Freedman]

- Add image and size details to `list_nodes` response in Dimension Data driver.
  (GITHUB-832)
  [Anthony Shaw]

- Add support for changing VM admin password in VMware driver.
  (GITHUB-833)
  [Juan Font Alonso]

- Add Barcelona (Spain) region to the Aurora Compute driver.
  (GITHUB-835)
  [Wido den Hollander]

- Various improvements in the libvirt driver.
  (GITHUB-838)
  [Rene Kjellerup]

Load balancer
~~~~~~~~~~~~~

- Add support for temporary IAM role credentials (token) to the AWS ELB driver.
  (GITHUB-843)
  [Anton Kozyrev]

DNS
~~~

- Updated the 'extra' parameter in `update_record()` to be optional in aurora
  driver.
  (GITHUB-830)
  [Wido den Hollander]

- Support for iterating over records and zones in the Aurora DNS driver.
  (GITHUB-829)
  [Wido den Hollander]

- Add support for DS, PTR, SSFHFP and TLSA record type to the Aurora DNS
  driver.
  (GITHUB-834)
  [Wido den Hollander]

Container
~~~~~~~~~

- Add network mode and labels when creating containers within docker driver.
  (GITHUB-831)
  [Jamie Cressey]

Storage
~~~~~~~

- Fix authentication issue in S3/China region, disabled multipart uploads as
  not supported by region.
  (GITHUB-839)
  [Luke Morfitt]

Changes with Apache Libcloud 1.1.0
----------------------------------

General
~~~~~~~

- Add support for automatic SNI (SSL extension) using the hostname
  supplied to connect to.

  Note: This functionality is only available in Python 2.7.9 and
  Python >= 3.2.
  (LIBCLOUD-827, GITHUB-808)
  [David Freedman]

Compute
~~~~~~~

- Add support image guest OS features in GCE driver.
  (GITHUB-825)
  [Max Illfelder]

- Added forceCustimization option for vcloud director driver.
  (GITHUB-824)
  [Juan Font]

- Add node lookup by UUID for libvirt driver.
  (GITHUB-823)
  [Frank Wu]

- Add block storage support to DigitalOcean node driver.
  (GITHUB-807)
  [Adam Wolfe Gordon]

- Add SASL auth support to libvirt driver.
  (GITHUB-809)
  [Katana-Steel]

- Allow VIPs in Dimension Data driver to bind to any port.
  (GITHUB-818)
  [Mark Maglana]

- Add support for deleting a security group to the Aliyun ECS driver.
  (GITHUB-816)
  [Heng Wu]

- Add ``ex_force_customization`` argument to the ``ex_deploy_node`` in vCloud
  driver.
  (GITHUB-824)
  [Juan Font]

- Add support for listing  attributes for a particular security group
  (``ex_list_security_group_attributes``) to the Aliyun ECS driver.
  (GITHUB-826)
  [Heng Wu]

- Add new Mumbai, India region to the EC2 driver.
  [Tomaz Muraus]

- Add driver for the new AWS cn-north-1 region.
  (GITHUB-827, LIBCLOUD-820)
  [Jamie Cressey]

- Fix authentication with temporary IAM role credentials (token) in the EC2
  driver.
  (GITHUB-820)
  [Alejandro González]

Container
~~~~~~~~~

- Fixed API compatibility for Docker Container driver with API 1.24, set driver
  to use versioned URL for all communication. Backported changes to 1.21 API
  (GITHUB-821)
  [Anthony Shaw]

Load Balancer
~~~~~~~~~~~~~

- Added additional parameters to the Rackspace driver in `list_balancers` for
  filtering and searching.
  (GITHUB-803)
  [João Paulo Raittes]

Changes with Apache Libcloud 1.0.0
----------------------------------

General
~~~~~~~

- Fix a regression with ``timeout`` argument provided via
  ``_ex_connection_class_kwargs`` method being overriden with ``None`` inside
  the ``BaseDriver`` constructor method.

  Reported by Jay Rolette.
  (GITHUB-755)
  [Tomaz Muraus, Jay Rolette]

- Fix OpenStack v3 authentication and allow user to provide a custom value for
  the OpenStack ``domain`` parameter. Previously only possible value as a
  default value of ``Default``.
  (GITHUB-744)
  [Lionel Schaub]

- Add support for authenticating against Keystone and OpenStack based clouds
  using OpenID Connect tokens.
  (GITHUB-789)
  [Miguel Caballer]

Compute
~~~~~~~

- GCE nodes can be launched in a subnetwork
  (GITHUB-783)
  [Lars Larsson]

- Add Subnetworks to GCE driver
  (GITHUB-780)
  [Eric Johnson]

- Fix missing pricing data for GCE
  (LIBCLOUD-713, GITHUB-779)
  [Eric Johnson]

- Add Image Family support for GCE
  (GITHUB-778)
  [Rick Wright]

- Fix a race condition on GCE driver `list_nodes()`- Invoking GCE’s
  `list_nodes()` while some VMs are being shutdown can result in the following
  `libcloud.common.google.ResourceNotFoundError` exception to be raised.
  (GITHUB-727)
  [Lénaïc Huard]

- Allow user to filter nodes by location by adding optional `location`
  argument to the `list_nodes()` method in the CloudStack driver.
  (GITHUB-737)
  [Lionel Schaub]

- Fix OpenStack IP type resolution - make sure IP addresses are correctly
  categorized and assigned on `private_ips` and `public_ips` Node attribute.
  (GITHUB-738)
  [Lionel Schaub]

- Add new `Perth, Australia` and `Manila, Philippines` region to the CloudSigma
  v2 driver.
  [Tomaz Muraus]

- Update libvirt driver so it returns false if a non-local libvirt URL is used
  (right now only local instances are supported).
  (LIBCLOUD-820, GITHUB-788)
  [René Kjellerup]

- Update libvirt driver to use `ip neight` command instead of `arp` to retrieve
  node MAC address if `arp` command is not available or the current user
  doesn't have permission to use it.
  (LIBCLOUD-820, GITHUB-788)
  [René Kjellerup]

- Update ``create_volume`` method in the CloudStack driver and add
  ``ex_volume_type`` argument to it. If this argument is provided, a volume
  which names matches this argument value will be searched and selected among
  the available disk offerings.
  (GITHUB-785)
  [Greg Bishop]

Storage
~~~~~~~

- Add support for AWS signature v4 to the Outscale storage driver.
  (GITHUB-736)
  [Javier M. Mellid]

- Add new S3 RGW storage driver.
  (GITHUB-786, GITHUB-792)
  [Javier M. Mellid]

Loadbalancer
~~~~~~~~~~~~

- Update AWS ELB driver to use signature version 4 for authentication. This
  way, the driver also work with the `eu-central-1` region.
  (GITHUB-796)
  [Tobias Paepke]

DNS
~~~

- Add BuddyNS driver.
  (GITHUB-742)
  [Oltjano Terpollari]

- Added DNSPod driver (https://www.dnspod.com).
  (GITHUB-787)
  [Oltjano Terpollari]

Changes with Apache Libcloud 1.0.0-rc2
--------------------------------------

General
~~~~~~~

- Fix a bug with consuming stdout and stderr in the paramiko SSH client which
  would manifest itself under very rare condition when a consumed chunk only
  contained a single byte or part of a multi byte UTF-8 character.
  [Lakshmi Kannan, Tomaz Muraus]

- Increase default chunk size from ``1024`` to ``4096`` bytes in the paramiko
  SSH client. This results in smaller number of receive calls on the average.
  [Tomaz Muraus]

- Fix to Dimension Data API address for Middle-East and Africa
  (GITHUB-700)
  [Anthony Shaw]

- Addition of Dimension Data Australia federal government region to dimension data
  drivers.
  (GITHUB-700)
  [Anthony Shaw]

- Throw a more user-friendly exception on "No address associated with hostname".
  (GITHUB-711, GITHUB-714, LIBCLOUD-803)
  [Tomaz Muraus, Scott Crunkleton]

* Remove deprecated provider constants with the region in the name and related
  driver classes (e.g. ``EC2_US_EAST``, etc.).

  Those drivers have moved to single provider constant + ``region`` constructor
  argument model.
  [Tomaz Muraus]

* Introduce new `list_regions`` class method on the base driver class. This
  method is to be used with provider drivers which support multiple regions and
  ``region`` constructor argument. It allows users to enumerate available /
  supported regions.
  [Tomaz Muraus]

Compute
~~~~~~~

- [dimension data] added support for VMWare tools VM information inside list_nodes responses
  (GITHUB-734)
  [Jeff Dunham]

- [ec2] added ex_encrypted and ex_kms_key_id optional parameters to the create volume method
  (GITHUB-729)
  [Viktor Ognev]

- [dimension data] added support for managing host anti-affinity rules, added paging support to
  all supported calls and added support for requesting priority ordering when creating ACL rules
  (GITHUB-726)
  [Jeff Dunham]

- [openstack] when creating floating IPs, added pool_id as an optional argument
  (GITHUB-725)
  [marko-p]

- [google compute] Added setMachineType method to allow for changing sizes of instances
  (GITHUB-721)
  [Eric Johnson]

- [google compute] allow bypassing image search in standard project list
  (GITHUB-713)
  [Max Illfelder]

- Add support for requesting a MKS token for accessing the remote console in VMware
  vCloud driver
  (GITHUB-706)
  [Juan Font Alonso]

- Add support in VMware vCloud driver for v5.5 API, with snapshot support
  (GITHUB-658)
  [Juan Font Alonso]

- Added support for adding a family to an image on Google Compute Driver
  (GITHUB-704)
  [Max Illfelder]

- Deprecated IBM SCE, HP Helion, OpSource, Ninefold and CloudFrames drivers, removed
  driver code and tests.
  (GITHUB-701, LIBCLOUD-801)
  [Anthony Shaw]

- Introduced error messages (`libcloud.compute.deprecated`) for deprecated drivers
  (GITHUB-701, LIBCLOUD-801)
  [Anthony Shaw]

- New Compute drivers- BSNL, Indosat, Med-1, NTT-America, Internet Solutions
  (GITHUB-700)
  [Anthony Shaw]

- Fix to set default signature version for AWS Seoul region to v4, removed
  non-supported size (hs1.xlarge)
  (GITHUB-684)
  [Geunwoo Shin]

- Support filtering by location in list_nodes for dimension data compute driver
  fix lack of paging support
  (GITHUB-691)
  [Jeff Dunham]

- Support for filtering by IPv4, IPv6, network, network domain, VLAN in Dimension
  data driver.
  (GITHUB-694)
  [Jeff Dunham]

- Added `Node.created_at` which, on supported drivers, contains the datetime the
  node was first started.
  (GITHUB-698)
  [Allard Hoeve] [Rick van de Loo]

- New driver for Aliyun Elastic Compute Service.
  (LIBCLOUD-802, GITHUB-712)
  [Sam Song, Heng Wu]

Storage
~~~~~~~

- Added Outscale storage driver
  (GITHUB-730)
  [Javier M. Mellid]

- Improvements to Google Auth for Storage and Compute and MIME bug fix
  (LIBCLOUD-800, GITHUB-689)
  [Scott Crunkleton]

- Implement ``get_container``, ``get_object`` and ``upload_object_via_stream``
  methods in the Backblaze B2 storage driver.

  Note: Backblaze API doesn't upload streaming uploads so when using
  ``upload_object_via_stream`` whole file is read and buffered in memory.
  (GITHUB-696)
  [Jay jshridha]

- New driver for Aliyun OSS Storage Service.
  (LIBCLOUD-802, GITHUB-712)
  [Sam Song]

Loadbalancer
~~~~~~~~~~~~

- New driver for Aliyun SLB Loadbalancer Service.
  (LIBCLOUD-802, GITHUB-712)
  [Sam Song]

DNS
~~~~

- Added NearlyFreeSpeech.net (NSFN) driver
  [Ken Drayer]
  (GITHUB-733)

- Added Lua DNS driver
  [Oltjano Terpollari]
  (GITHUB-732)

- Added NSOne driver
  [Oltjano Terpollari]
  (GITHUB-710)

- Fix a bug in the GoDaddy driver - make sure ``host`` attribute on the
  connection class is correctly set to the hostname.
  [Tomaz Muraus]

- Fix handling of ``MX`` records in the Gandi driver.
  (GITHUB-718)
  [Ryan Lee]

Backup
~~~~~~

- Dimension Data - added additional testing, fixed bug on client response naming,
  added support for adding backup clients to a backup enabled node.
  (GITHUB-692, GITHUB-693, GITHUB-695)
  [Jeff Dunham]

Changes with Apache Libcloud 1.0.0-pre1
---------------------------------------

General
~~~~~~~

- Introduction of container based drivers for Docker, Rkt and Container-as-a-service
  providers
  (LIBCLOUD-781, GITHUB-666)
  [Anthony Shaw]

- Introduce a new ``libcloud.backup`` API for Backup as a Service projects and
  products.
  (GITHUB-621)
  [Anthony Shaw]

- Also retry failed HTTP(s) requests upon transient "read operation timed out"
  SSL error.
  (GITHUB-556, LIBCLOUD-728)
  [Scott Kruger]

- Throw a more user-friendly exception if a client fails to establish SSL / TLS
  connection with a server because of an unsupported SSL / TLS version.
  (GITHUB-682)
  [Tomaz Muraus]

Compute
~~~~~~~

- Add ap-northeast-2 region to EC2 driver (South Korea)
  (GITHUB-681)
  [Anthony Shaw]

- Added Added volume type to EC2 volume extra to EC2 driver.
  (GITHUB-680)
  [Gennadiy Stas]

- Add LazyObject class that provides lazy-loading, see `GCELicense` for usage
  (LIBCLOUD-786, GITHUB-665)
  [Scott Crunkleton]

- Added t2.nano instance type to EC2 Compute driver
  (GITHUB-663)
  [Anthony Shaw]

- Support for passing the image ID as a string instead of an instance of image when
  creating nodes in Dimension Data driver.
  (GITHUB-664)
  [Anthony Shaw]

DNS
~~~

- Add support for 'health checks' in Aurora DNS driver
  (GITHUB-672)
  [Wido den Hollander]

- Make sure ``ttl`` attribute is correctly parsed and added to the ``Record``
  ``extra`` dictionary.
  (GITHUB-675)
  [Wido den Hollander]

- Improve unit tests of Aurora DNS driver
  (GITHUB-679)
  [Wido den Hollander]

Changes with Apache Libcloud 0.20.1
-----------------------------------

Compute
~~~~~~~

- [google] Allow for old and new style service account client email address
  (LIBCLOUD-785)
  [Hoang Phan]

Changes with Apache Libcloud 0.20.0
-----------------------------------

General
~~~~~~~

- Added .editorconfig file for easier editing
  (GITHUB-625)
  [Misha Brukman]

- Fix a bug with Libcloud accidentally setting paramiko root logger level to
  DEBUG (this should only happen if ``LIBCLOUD_DEBUG`` environment variable is
  provided).

  Reported by John Bresnahan.
  (LIBCLOUD-765)
  [Tomaz Muraus, John Bresnahan]

- Simply travis and tox config (.travis.yml, tox.ini).
  (GITHUB-608)
  [Anthony Monthe]

- Fixed Python2.6 unit testing (and Google Cloud Storage tests)
  (GITHUB-648)
  [Scott Crunkleton]

Compute
~~~~~~~

- [google] Allow for old and new style service account client email address
  (LIBCLOUD-785)
  [Hoang Phan]

- Minor security improvement for storing cached GCE credentials
  (LIBCLOUD-718)
  [Siim Põder]

- Removed DreamHosts Compute Driver, DreamHosts users will now use the OpenStack Node driver since DreamHosts are OpenStack
  API compliant
  (GITHUB-655)
  [Stephano Maffulli]

- Added additional kwargs to the create_node method for Dimension Data driver, allowing the user to specify the RAM and
  CPU upfront. Added a ex_reconfigure_node method and ex_list_customer_images as well as updating the API to 2.1.
  (LIBCLOUD-783, GITHUB-656)
  [Anthony Shaw]

- The EC2 Instance Type updated with correct disk sizes (especially the disk size for the m3 instances),
  conversion errors between GiB an M[i]B, disk count were the cause.
  Added instance types - g2.8xlarge and t2.large.
  (GITHUB-646)
  [Philipp Hahn]

- Add update node, update VMware tools, add storage, change storage size or speed, remove storage to Dimension Data Driver.
  (LIBCLOUD-775, GITHUB-644)
  [Anthony Shaw]

- Include 'service_name' support in _parse_service_catalog_auth_v3 for Openstack Drivers
  (GITHUB-647)
  [Steve Gregory]

- Outscale inc & sas driver update
  (GITHUB-645)
  [@LordShion]

- Add new `eu-west-2` & `us-east-2` regions to the OUTSCALE_INC & OUTSCALE_SAS drivers.
  [Filipe Silva /lordshion]

- [google compute] add pricing data update script
  (GITHUB-464)
  [Misha Brukman]

- Fix a bug in the ``list_volumes`` method in the CloudStack driver so it
  returns an empty list if no volumes are found.
  (GITHUB-617)
  [Wido den Hollander]

- Return proper volume state for CloudStack volumes.
  (GITHUB-615, LIBCLOUD-764)
  [Wido den Hollander]

- Add support for multiple regions in Aurora compute driver
  (GITHUB-623)
  [Wido den Hollander]

- Fix value of ``node.extra['ip_addresses']`` node attribute in the CloudStack
  driver.
  (LIBCLOUD-767, GITHUB-627)
  [Atsushi Sasaki]

- Make sure that ``node.public_ips`` attribute in the CloudStack driver doesn't
  contain duplicated values..
  (LIBCLOUD-766, GITHUB-626)
  [Atsushi Sasaki]

- Allow user to wait for a resource to reach a desired state in the
  Dimension Data driver by using new ``ex_wait_for_state`` method.
  (LIBCLOUD-707, GITHUB-631)
  [Anthony Shaw]

- Added M4 pricing and instance information to EC2 driver
  (GITHUB-634)
  [Benjamin Zaitlen]

- Added C4 instance information to EC2 driver
  (GITHUB-638)
  [amitofs]

- Allow location of the datacenter to be supplied in ProfitBricks driver
  (LIBCLOUD-771, GITHUB-635)
  [Joel Reymont]

- Reduce redundant API calls in CloudStack driver
  (LIBCLOUD-590, GITHUB-641)
  [Atsushi Sasaki]

- Add an additional argument to libcloud.compute.drivers.GCENodeDriver.create_node
  to allow for creation of preemptible GCE instances
  (GITHUB-643)
  [@blawney]

- GoogleStorageDriver can now use either our S3 authentication or other Google Cloud Platform OAuth2 authentication methods.
  (GITHUB-633)
  [Scott Crunkleton]

- All NodeState, StorageVolumeState, VolumeSnapshotState and Provider attributes
  are now strings instead of integers.
  (GITHUB-624)
  [Allard Hoeve]

Storage
~~~~~~~

Loadbalancer
~~~~~~~~~~~~

DNS
~~~

- RackSpace driver - New DNS driver methods:
   - ex_iterate_ptr_records
   - ex_get_ptr_record
   - ex_create_ptr_record
   - ex_update_ptr_record
   - ex_delete_ptr_record

  This should cover all of the functionality offered by the Rackspace DNS API
  in regards to RDNS.
  (LIBCLOUD-780, GITHUB-652)
  [Greg Hill]

- Update ``create_record`` in the WorldWideDNS driver so it automatically
  selects a slot if one is not provided by the user via ``extra['entry']``
  argument.
  (GITHUB-621)
  [Alejandro Pereira]

- Introduce GoDaddy DNS Driver with examples and documentation.
  (LIBCLOUD-772, GITHUB-640, LIBCLOUD-778)
  [Anthony Shaw]

- Add new driver for CloudFlare DNS (https://www.cloudflare.com/dns/).
  (GITHUB-637)
  [Tomaz Muraus]

Changes with Apache Libcloud 0.19.0
-----------------------------------

General
~~~~~~~

- Update Rackspace AUTH_URL
  (LIBCLOUD-738)
  [Brian Curtin]

- Fix ``LIBCLOUD_DEBUG`` mode so it works on Python 3.x.
  [Tomaz Muraus]

- Fix Libcloud code so it doesn't throw an exception if simplejson < 2.1.0 is
  installed.
  (LIBCLOUD-714, GITHUB-577)
  [Erik Johnson]

- Fix endpoint URL for DimensionData Asia Pacific region.
  (GITHUB-585)
  [Anthony Shaw]

- Document potential time drift issue which could cause authentication in the
  GCE drivers to fail.
  (GITHUB-571)
  [Michal Tekel]

- Update documentation for EC2 - make sure they reflect region changes from
  0.14 release.
  (GITHUB-606)
  [James Guthrie]

Compute
~~~~~~~

- Fixed malformed XML requests with Dimension Data driver.
  (LIBCLOUD-760, GITHUB-610)
  [Anthony Shaw]

- Update list of scopes for Google Compute Engine driver.
  (GITHUB-607)
  [Otto Bretz]

- Allow user to filter VPC by project in the CloudStack driver by passing
  ``project`` argument to the ``ex_list_vps`` method.
  (GITHUB-516)
  [Syed Mushtaq Ahmed]

- Add volume management methods and other various improvements and fixes in the
  RunAbove driver.
  (GITHUB-561)
  [Anthony Monthe]

- Add support and update Dimension Data driver to use API v2.0 by default.
  (LIBCLOUD-736, GITHUB-564)
  [Anthony Shaw]

- Add new ``ex_virtual_network_name`` and ``ex_network_config`` argument to the
  `create_node`` method in the Azure driver. With those arguments user can now
  specify which virtual network to use.
  (GITHUB-569)
  [Jesaja Everling]

- Fix ``create_node`` method in the GCE driver calling inexistent method
  (ex_get_disk instead of ex_get_volume).
  (GITHUB-574)
  [Alex Poms]

- Allow user to pass ``proxy_url`` keyword argument to the VCloud driver
  constructor.
  (GITHUB-578)
  [Daniel Pool]

- Various fixes and improvements in the DimensionData driver (support for
  creating servers in MCP 1 and 2 data center, performance improvements in the
  location fetching, etc.).
  (GITHUB-587, GITHUB-593, LIBCLOUD-750, LIBCLOUD-753)
  [Anthony Shaw]

- Added ``ex_assign_public_ip`` argument to ``create_node`` in the EC2 driver.
  (GITHUB-590)
  [Kyle Long]

- Added ``ex_terminate_on_shutdown`` argument to ``create_node`` in the EC2
  driver.
  (GITHUB-595)
  [Kyle Long]

- Various fixes and improvements in the ``ex_authorize_security_group_ingress``
  in the CloudStack driver.
  (LIBCLOUD-749, GITHUB-580)
  [Lionel Schaub]

- Add pricing information for Softlayer.
  (LIBCLOUD-759, GITHUB-603)
  [David Wilson]

- Standardize VolumeSnapshot states into the ``state`` attribute.
  (LIBCLOUD-758, GITHUB-602)
  [Allard Hoeve]

Storage
~~~~~~~

- Add support for ``sa-east-1`` region to the Amazon S3 driver.
  (GITHUB-562)
  [Iuri de Silvio]

- Fix handling of binary data in Local storage driver on Python 3. Now the file
  which is to be written or read from is opened in the binary mode (``b`` flag).
  (LIBCLOUD-725, GITHUB-568)
  [Torf]

Loadbalancer
~~~~~~~~~~~~

- Add a new driver for DimensionData load-balancing service
  (http://cloud.dimensiondata.com/).
  (LIBCLOUD-737, GITHUB-567)
  [Anthony Shaw]

DNS
~~~

- Update Google Cloud DNS API from 'v1beta1' to 'v1'
  (GITHUB-583)
  [Misha Brukman]

- Add new driver for AuroraDNS service.
  (GITHUB-562, LIBCLOUD-735)
  [Wido den Hollander]

- Fix "_to_record" in the Route53 driver - make sure it doesn't throw if the
  record TTL is not available.
  [Tomaz Muraus]

- Add new driver for WorldWideDNS service
  (http://www.worldwidedns.net/home.asp).
  (GITHUB-566, LIBCLOUD-732)
  [Alejandro Pereira]

- Add new driver for DNSimple service (https://dnsimple.com/).
  (GITHUB-575, GITHUB-604, LIBCLOUD-739)
  [Alejandro Pereira, Patrick Humpal]

- Add new driver for PointDNS service (https://pointhq.com).
  (GITHUB-576, GITHUB-591, LIBCLOUD-740)
  [Alejandro Pereira]

- Add new driver for Vultr DNS service (https://www.vultr.com).
  (GITHUB-579, GITHUB-596, LIBCLOUD-745)
  [Alejandro Pereira, Janez Troha]

- Add new driver for Liquidweb DNS service (http://www.liquidweb.com/).
  (GITHUB-581, LIBCLOUD-746)
  [Oltjano Terpollari, Alejandro Pereira]

- Add new driver for Zonomi DNS hosting service (http://zonomi.com/).
  (GITHUB-582, LIBCLOUD-747)
  [Oltjano Terpollari, Alejandro Pereira]

- Add new driver for Durable DNS service (https://durabledns.com/).
  (GITHUB-588, LIBCLOUD-748)
  [Oltjano Terpollari, Alejandro Pereira]

Changes with Apache Libcloud 0.18.0
-----------------------------------

General
~~~~~~~

- Use native ``ssl.match_hostname`` functionality when running on Python >=
  3.2 and only require ``backports.ssl_match_hostname`` dependency on Python
  versions < 3.2.
  [Tomaz Muraus]

- Add support for AWS Signature version 4.

  Note: Currently only GET HTTP method is supported.
  (GITHUB-444)
  [Gertjan Oude Lohuis]

- Fix a bug in the debug mode logging (LIBCLOUD_DEBUG). Logging to the debug
  file would throw an exception if the text contained non-ascii characters.
  [Tomaz Muraus]

- Fix a bug with connection code throwing an exception if a port was a unicode
  type and not a str or int.
  (GITHUB-533, LIBCLOUD-716)
  [Avi Weit]

- Update ``is_valid_ip_address`` function so it also works on Windows.
  (GITHUB-343, GITHUB-498, LIBCLOUD-601, LIBCLOUD-686)
  [Nicolas Fraison, Samuel Marks]

- Add support for retrying failed HTTP requests.

  Retrying is off by default and can be enabled by setting
  ``LIBCLOUD_RETRY_FAILED_HTTP_REQUESTS`` environment variable.
  (GITHUB-515, LIBCLOUD-360, LIBCLOUD-709)

- Fix a bug in consuming stdout and stderr strams in Paramiko SSH client.
  In some cases (like connecting to localhost via SSH), exit_status_ready
  gets set immediately even before the while loop to consume the streams
  kicks in. In those cases, we will not have consumed the streams at all.
  (GITHUB-558)
  [Lakshmi Kannan]

Compute
~~~~~~~

- Google Compute now supports paginated lists including filtering.
  (GITHUB-491)
  [Lee Verberne]

- OpenStackNodeSize objects now support optional, additional fields that are
  supported in OpenStack 2.1: `ephemeral_disk`, `swap`, `extra`.
  (GITHUB-488, LIBCLOUD-682)
  [Greg Hill]

- StorageVolume objects now have an attribute `state` that holds a
  state variable that is standardized state across drivers. Drivers that
  currently support the `state` attribute are OpenStack and EC2.
  StorageVolume objects returned by drivers that do not support the
  attribute will have a `state` of `None`. When a provider returns a state
  that is unknown to the driver, the state will be `UNKNOWN`. Please report
  such states. A couple of drivers already put state fields in the `extra`
  fields of StorageVolumes. These fields were kept for
  backwards-compatibility and for reference.
  (GITHUB-476)
  [Allard Hoeve]

- StorageVolume objects on EC2 and OpenStack now have a key called snapshot_id
  in their extra dicts containing the snapshot ID the volume was based on.
  (GITHUB-479)
  [Allard Hoeve]

- OpenStack driver: deprecated ex_create_snapshot and ex_delete_snapshot in
  favor of create_volume_snapshot and destroy_volume_snapshot. Updated base
  driver method create_storage_volume argument name to be optional.
  (GITHUB-478)
  [Allard Hoeve]

- Add support for creating volumes based on snapshots to EC2 and OS drivers.
  Also modify signature of base NodeDriver.create_volume to reflect the fact
  that all drivers expect a StorageSnapshot object as the snapshot argument.
  (GITHUB-467, LIBCLOUD-672)
  [Allard Hoeve]

- VolumeSnapshots now have a `created` attribute that is a `datetime`
  field showing the creation datetime of the snapshot. The field in
  VolumeSnapshot.extra containing the original string is maintained, so
  this is a backwards-compatible change.
  (GITHUB-473)
  [Allard Hoeve]

- Improve GCE create_node, make sure ex_get_disktype function
  (GITHUB-448)
  [Markos Gogoulos]

- GCE driver fix to handle unknown image projects
  (GITHUB-447)
  [Markos Gogoulos]

- Allow user to pass ``ex_blockdevicemappings`` argument to the create_node
  method in the OpenStack driver.
  (GITHUB-398, LIBCLOUD-637)
  [Allard Hoeve]

- Fix ``list_volume_snapshots`` method in the EC2 driver so it comforms to the
  base API.
  (LIBCLOUD-664, GITHUB-451)
  [Allard Hoeve]

- Add ``volumes_attached`` attibute to ``node.extra`` in the OpenStack driver.
  (LIBCLOUD-668, GITHUB-462)
  [Allard Hoeve]

- Add the following new methods to the Linode driver: ``ex_list_volumes``,
  ``ex_create_volume``, ``ex_destroy_volume``.
  (LIBCLOUD-649, GITHUB-430)
  [Wojciech Wirkijowski]

- Add ``list_volume_snapshots`` method to the OpenStack driver.
  (LIBCLOUD-663, GITHUB-450)
  [Allard Hoeve]

- Add Site to Site VPN functionality to CloudStack driver.
  (GITHUB-465)
  [Avi Nanhkoesingh]

- Add affinity group support to CloudStack driver
  (LIBCLOUD-671, GITHUB-468)
  [Mateusz Korszun]

- Add a support for a new AWS Frankfurt, Germany region (``eu-central-1``) to
  the EC2 driver using AWS Signature v4.
  (GITHUB-444)
  [Gertjan Oude Lohuis, Tomaz Muraus]

- Allow Filtering in EC2 list_images() driver
  (GITHUB-456, LIBCLOUD-667)
  [Katriel Traum]

- Add ex_list_ip_forwarding_rules() to CloudStack driver
  (GITHUB-483)
  [Atsushi Sasaki]

- Add AURORA compute driver
  (LIBCLOUD-641, GITHUB-477)
  [Wido den Hollander]

- Update ``ex_describe_tags`` method in the EC2 driver and allow user to list
  tags for any supported resource. Previously you could only list tags for a
  node or a storage volume.
  (LIBCLOUD-676, GITHUB-482)
  [John Kinsella]

- Various improvements in the HostVirual driver (code refactoring, support for
  managing "packages").
  (LIBCLOUD-670, GITHUB-472)
  [Dinesh Bhoopathy]

- Add support for DigitalOcean API v2.0 while maintaining support for the old
  API v2.0.

  Note: API v2.0 is now used by default. To use the old API v1.0, pass
  ``api_version='1.0'`` argument to the driver constructor.
  (GITHUB-442)
  [Andrew Starr-Bochicchio]

- Add new ``d4.`` instance types to the EC2 driver. Also update EC2 pricing data.
  (GITHUB-490)
  [Tomaz Muraus]

- Add new driver for Microsft Azure Virtual Machines service.
  (LIBCLOUD-556, GITHUB-305, GITHUB-499, GITHUB-538)
  [Michael Bennett, davidcrossland, Richard Conway, Matt Baldwin, Tomaz Muraus]

- Fix VPC lookup method in CloudStack driver
  (GITHUB-506)
  [Avi Nanhkoesingh]

- Add new driver for the Dimension Data provider based on the OpSource driver.
  (LIBCLOUD-698, GITHUB-507, LIBCLOUD-700, GITHUB-513)
  [Anthony Shaw]

- Add "virtualmachine_id" attribute to the ``CloudStackAddress`` class in the
  CloudStack driver.
  (LIBCLOUD-679, GITHUB-485)
  [Atsushi Sasaki]

- Allow user to pass filters via arguments to the
  ``ex_list_port_forwarding_rules`` in the CloudStack driver.
  (LIBCLOUD-678, GITHUB-484)
  [Atsushi Sasaki]

- Fix an issue with ``list_nodes`` in the CloudSigma driver throwing an
  exception if a node in the list had a static IP.
  (LIBCLOUD-707, GITHUB-514)
  [Chris O'Brien]

- Don't throw an exception if a limit for a particular CloudStack resource is
  "Unlimited" and not a number.
  (GITHUB-512)
  [Syed Mushtaq Ahmed]

- Allow user to pass ``ex_config_drive`` argument to the ``create_node`` method
  in the OpenStack driver.
  (LIBCLOUD-356, GITHUB-330)
  [Ryan Parrish]

- Add new driver for Cloudwatt (https://www.cloudwatt.com/en/) provider.
  (GITHUB-338)
  [Anthony Monthe]

- Add new driver for Packet (https://www.packet.com/) provider.
  (LIBCLOUD-703, GITHUB-527)
  [Aaron Welch]

- Update Azure VM pricing information and add information for new D instance
  types.
  (GITHUB-528)
  [Michael Bennett]

- Add ``ex_get_node`` and ``ex_get_volume`` methods to CloudStack driver.
  (GITHUB-532)
  [Anthony Monthe]

- Update CloudSigma driver so the "unavailable" and "paused" node state is
  correctly mapped to "error" and "paused" respectively.
  (GITHUB-517)
  [Chris O'Brien]

- Add SSH key pair management methods to the Gandi driver.
  (GITHUB-534)
  [Anthony Monthe]

- Add ``ex_get_node`` and ``ex_get_volume`` methods to Gandi driver.
  (GITHUB-534)
  [Anthony Monthe]

- Add ``fault`` attribute to the ``extra`` dictionary of the ``Node`` instance
  returned by the OpenStack driver.
  (LIBCLOUD-730, GITHUB-557)
  [Nick Fox]

- Add new driver for Onapp IaaS platform.
  (LIBCLOUD-691, GITHUB-502)
  [Matthias Wiesner]

- Allow user to inject custom data / script into the Azure node by passing
  ``ex_custom_data`` argument to the ``create_node`` method.
  (LIBCLOUD-726, GITHUB-554)
  [David Wilson]

- Add ``ex_create_cloud_service`` and ``ex_destroy_cloud_service`` method to the
  Azure driver.
  (LIBCLOUD-724, GITHUB-551)
  [David Wilson]

- Add support for passing user data when creating a DigitalOcean node
  (``ex_user_data`` argument).
  (LIBCLOUD-731, GITHUB-559)
  [David Wilson]

- Allow user to specify which arguments are passed to ``list_nodes`` method
  which is called inside ``wait_until_running`` by passing
  ``ex_list_nodes_kwargs`` argument to the ``wait_until_running`` method.
  (``ex_user_data`` argument).
  (LIBCLOUD-723, GITHUB-548)
  [David Wilson]

- Allow user to pass ``ex_volume_type`` argument to the ``create_volume`` method
  in the OpennStack driver.
  (GITHUB-553)
  [Rico Echwald-Tijsen]

- Add new driver for RunAbove (https://www.runabove.com) provider.
  (GITHUB-550)
  [Anthony Monthe]

- Fix a bug with exception being throw inside the CloudStack driver when the
  provider returned no error message in the body.
  (GITHUB-555)
  [Konstantin Skaburskas]

- Various improvements in the DigitalOcean driver:
   - Increase page size to API maximum.
   - Add ``ex_create_attr`` kwarg to ``create_node`` method.
   - Update all the ``list_*`` methods to use paginated requests
   - Allow user to specify page size by passing ``ex_per_page`` argument to the
     constructor.

  (LIBCLOUD-717, GITHUB-537)
  [Javier Castillo II]

Storage
~~~~~~~

- Fix a bug with authentication in the OpenStack Swift driver.
  (GITHUB-492, LIBCLOUD-635)
  [Tom Fifield]

- Add AuroraObjects Storage Driver.
  (GITHUB-540, LIBCLOUD-719)
  [Wido den Hollander]

Loadbalancer
~~~~~~~~~~~~

- Add a new driver for Softlayer load-balancing service
  (https://www.softlayer.com/load-balancing).
  (GITHUB-500, LIBCLOUD-688)
  [Avi Weit]

DNS
~~~

- Fix a bug when a ZoneDoesntExist exception was thrown when listing records
  for a zone which has no records in the HostVirtual driver.
  (GITHUB-460)
  [Vanč Levstik]

- Correctly handle MX records priority in the Route53 driver.
  (GITHUB-469)
  [Vanč Levstik]

- Allow user to create an A record which points directly to the domain zone
  name in the Route53 driver.
  (GITHUB-469)
  [Vanč Levstik]

- Fix delete_zone method in the HostVirtual driver.
  (GITHUB-461)
  [Vanč Levstik]

- Fix parsing of the record name in the HostVirtual driver.
  (GITHUB-461)
  [Vanč Levstik]

- Add new driver for DigitalOcean DNS service.
  (GITHUB-505)
  [Javier Castillo II]

Changes with Apache Libcloud 0.17.0
-----------------------------------

General
~~~~~~~

- Use ``match_hostname`` function from ``backports.ssl_match_hostname``
  package to verify the SSL certificate hostname instead of relying on
  our own logic.
  (GITHUB-374)
  [Alex Gaynor]

Compute
~~~~~~~

- Add new `eu-west-2` & `us-east-2` regions to the OUTSCALE_INC & OUTSCALE_SAS drivers.
  [Filipe Silva /lordshion]

- GCE driver updated to include ex_stop_node() and ex_start_node() methods.
  (GITHUB-442)
  [Eric Johnson]

- GCE driver now raises ResourceNotFoundError when the specified image is
  not found in any image project. Previously, this would return None but now
  raises the not-found exception instead. This fixes a bug where returning
  None caused ex_delete_image to raise an AttributeError.
  (GITHUB-441)
  [Eric Johnson]

- GCE driver update to support JSON format Service Account files and a PY3
  fix from Siim Põder for LIBCLOUD-627.
  (LIBCLOUD-627, LIBCLOUD-657, GITHUB-438)
  [Eric Johnson]

- GCE driver fixed for missing param on ex_add_access_config.
  (GITHUB-435)
  [Peter Mooshammer]

- GCE driver support for HTTP load-balancer resources.
  (LIBCLOUD-605, GITHUB-429)
  [Lee Verberne]

- GCE driver updated to make better use of GCEDiskTypes.
  (GITHUB-428)
  [Eric Johnson]

- GCE driver list_images() now returns all non-deprecated images by default.
  (LIBCLOUD-602, GITHUB-423)
  [Eric Johnson]

- Improve GCE API coverage for create_node().
  (GITHUB-419)
  [Eric Johnson]

- GCE Licenses added to the GCE driver.
  (GITHUB-420)
  [Eric Johnson]

- GCE Projects support common instance metadata and usage export buckets.
  (GITHUB-409)
  [Eric Johnson]

- Improvements to TargetPool resource in GCE driver.
  (GITHUB-414)
  [Eric Johnson]

- Adding TargetInstances resource to GCE driver.
  (GITHUB-393)
  [Eric Johnson]

- Adding DiskTypes resource to GCE driver.
  (GITHUB-391)
  [Eric Johnson]

- Fix boot disk auto_delete in GCE driver.
  (GITHUB-412)
  [Igor Bogomazov]

- Add Routes to GCE driver.
  (GITHUB-410)
  [Eric Johnson]

- Add missing ``ubuntu-os-cloud`` images to the GCE driver.
  (LIBCLOUD-632, GITHUB-385)
  [Borja Martin]

- Add new `us-east-2` and `us-east-3` region to the Joyent driver.
  (GITHUB-386)
  [Anthony Monthe]

- Add missing t2. instance types to the us-west-1 region in the EC2 driver.
  (GITHUB-388)
  [Matt Lehman]

- Add option to expunge VM on destroy in CloudStack driver.
  (GITHUB-382)
  [Roeland Kuipers]

- Add extra attribute in list_images for CloudStack driver.
  (GITHUB-389)
  [Loic Lambiel]

- Add ``ex_security_group_ids`` argument to the create_node method in the
  EC2 driver. This way users can launch VPC nodes with security groups.
  (GITHUB-373)
  [Itxaka Serrano]

- Add description argument to GCE Network.
  (GITHUB-397)
  [Eric Johnson]

- GCE: Improve MachineType (size) coverage of GCE API.
  (GITHUB-396)
  [Eric Johnson]

- GCE: Improved Images coverage.
  (GITHUB-395)
  [Eric Johnson]

- GCE: Support for global IP addresses.
  (GITHUB-390, GITHUB-394)
  [Eric Johnson]

- GCE: Add missing snapshot attributes.
  (GITHUB-401)
  [Eric Johnson]

- AWS: Set proper disk size in c3.X instance types.
  (GITHUB-405)
  [Itxaka Serrano]

- Fix a bug with handling of the ``ex_keyname`` argument in the Softlayer
  driver.
  (GITHUB-416, LIBCLOUD-647)
  [Dustin Oberloh]

- Update CloudSigma region list (remove Las Vegas, NV region and add new San
  Jose, CA and Miami, FL region).
  (GITHUB-417)
  [Viktor Petersson]

- Add ``ex_get_node`` method to the Joyent driver.
  (GITHUB-421)
  [Anthony Monthe]

- Add support for placement group management to the EC2 driver.
  (GITHUB-418)
  [Mikhail Ovsyannikov]

- Add new tok02 region to the Softlayer driver.
  (GITHUB-436, LIBCLOUD-656)
  [Dustin Oberloh]

- Add new Honolulu, HI endpoint to the CloudSigma driver.
  (GITHUB-439)
  [Stephen D. Spencer]

- Fix a bug with config_drive attribute in the OpenStack driver. New versions
  of OpenStack now return a boolean and not a string.
  (GITHUB-433)
  [quilombo]

- Add support for Abiquo API v3.x, remove support for now obsolete API v2.x.
  (GITHUB-433, LIBCLOUD-652)
  [David Freedman]

- Allow rootdisksize parameter in create_node CloudStack driver
  (GITHUB-440, LIBCLOUD-658)
  [Loic Lambiel]

Storage
~~~~~~~

- Allow user to pass ``headers`` argument to the ``upload_object`` and
  ``upload_object_via_stream`` method.

  This way user can specify CORS headers with the drivers which support that.
  (GITHUB-403, GITHUB-404)
  [Peter Schmidt]

- Fix upload_object_via_stream so it works correctly under Python 3.x if user
  manually passes an iterator to the method.

  Also improve how reading a file in chunks works with drivers which support
  chunked encoding - always try to fill a chunk with CHUNK_SIZE bytes instead
  of directly streaming the chunk which iterator returns.

  Previously, if iterator returned 1 byte in one iteration, we would directly
  send this as a single chunk to the API.
  (GITHUB-408, LIBCLOUD-639)
  [Peter Schmidt]

Loadbalancer
~~~~~~~~~~~~

- Updates to CloudStack driver.
  (GITHUB-434)
  [Jeroen de Korte]

DNS
~~~

- New driver for Softlayer DNS service.
  (GITHUB-413, LIBCLOUD-640)
  [Vanč Levstik]

- Fix a bug with ``ex_create_multi_value_record`` method in the Route53 driver
  only returning a single record.
  (GITHUB-431, LIBCLOUD-650)
  [Itxaka Serrano]

Changes with Apache Libcloud 0.16.0
-----------------------------------

General
~~~~~~~

- Add new ``OpenStackIdentity_3_0_Connection`` class for working with
  OpenStack Identity (Keystone) service API v3.
  [Tomaz Muraus]

- Add support for prettifying JSON or XML response body which is printed to a
  file like object when using ``LIBCLOUD_DEBUG`` environment variable.
  This option can be enabled by setting
  ``LIBCLOUD_DEBUG_PRETTY_PRINT_RESPONSE`` environment variable.
  [Tomaz Muraus]

- Add support for using an HTTP proxy for outgoing HTTP and HTTPS requests.
  [Tomaz Muraus, Philip Kershaw]

Compute
~~~~~~~

- Fix an issue with ``LIBCLOUD_DEBUG`` not working correctly with the
  Linode driver.
  [Tomaz Muraus, Juan Carlos Moreno]
  (LIBCLOUD-598, GITHUB-342)

- Add new driver for VMware vSphere (http://www.vmware.com/products/vsphere/)
  based clouds.
  [Tomaz Muraus]

- Add two new default node states - ``NodeState.SUSPENDED`` and
  ``NodeState.ERROR``.
  [Tomaz Muraus]

- Fix to join networks properly in ``deploy_node`` in the CloudStack
  driver.
  (LIBCLOUD-593, GITUHB-336)
  [Atsushi Sasaki]

- Create ``CloudStackFirewallRule`` class and corresponding methods.
  (LIBCLOUD-594, GITHUB-337)
  [Atsushi Sasaki]

- Add support for SSD disks to Google Compute driver.
  (GITHUB-339)
  [Eric Johnson]

- Add utility ``get_regions`` and ``get_service_names`` methods to the
  ``OpenStackServiceCatalog`` class.
  [Andrew Mann, Tomaz Muraus]

- Fix a bug in ``ex_get_console_output`` in the EC2 driver which would cause
  an exception to be thrown if there was no console output for a particular
  node.

  Reported by Chris DeRamus.
  [Tomaz Muraus]

- Add ip_address parameter in CloudStack driver ``create_node`` method.
  (GITHUB-346)
  [Roeland Kuipers]

- Fix ``ParamikoSSHClient.run`` and ``deploy_node`` method to work correctly
  under Python 3.
  (GITHUB-347)
  [Eddy Reyes]

- Update OpenStack driver to map more node states to states recognized by
  Libcloud.
  [Chris DeRamus]

- Fix a bug with ``ex_metadata`` argument handling in the Google Compute Engine
  driver ``create_node`` method.
  (LIBCLOUD-544, GITHUB-349, GITHUB-353)
  [Raphael Theberge]

- Add SSH key pair management methods to the Softlayer driver.
  (GITHUB-321, GITHUB-354)
  [Itxaka Serrano]

- Correctly categorize node IP addresses into public and private when dealing
  with OpenStack floating IPs.
  [Andrew Mann]

- Add new t2 instance types to the EC2 driver.
  [Tomaz Muraus]

- Add support for Amazon GovCloud to the EC2 driver (us-gov-west-1 region).
  [Chris DeRamus]

- Allow user to pass "gp2" for "ex_volume_type" argument to the create_volume
  method in the EC2 driver.

  Reported by Xavier Barbosa.
  [Tomaz Muraus, Xavier Barbosa]

- Add new driver for ProfitBricks provider.
  (LIBCLOUD-589, GITHUB-352)
  [Matt Baldwin]

- Various improvements and bugs fixes in the GCE driver. For a list, see
  https://github.com/apache/libcloud/pull/360/commits
  (GITHUB-360)
  [Evgeny Egorochkin]

- Allow user to specify virtualization type when registering an EC2 image by
  passing ``virtualization_type`` argument to the ``ex_register_image`` method.
  (GITHUB-361)
  [Andy Grimm]

- Add ``ex_create_image`` method to the GCE driver.
  (GITHUB-358, LIBCLOUD-611)
  [Katriel Traum]

- Add some methods to CloudStack driver:
  create_volume_snapshot, list_snapshots, destroy_volume_snapshot
  create_snapshot_template, ex_list_os_types)
  (GITHUB-363, LIBCLOUD-616)
  [Oleg Suharev]

- Added VPC support and Egress Firewall rule support fo CloudStack
  (GITHUB-363)
  [Jeroen de Korte]

- Add additional attributes to the ``extra`` dictionary of OpenStack
  StorageVolume object.
  (GITHUB-366)
  [Gertjan Oude Lohuis]

- Fix ``create_volume`` method in the OpenStack driver to return a created
  volume object (instance of StorageVolume) on success, instead of a boolean
  indicating operation success.
  (GITHUB-365)
  [Gertjan Oude Lohuis]

- Add optional project parameters for ex_list_networks() to CloudStack driver
  (GITHUB-367, LIBCLOUD-615)
  [Rene Moser]

- CLOUDSTACK: option to start VM in a STOPPED state
  (GITHUB-368)
  [Roeland Kuipers]

- Support "config_drive" in the OpenStack driver. Allow users to pass
  ``ex_config_drive`` argument to the ``create_node`` and ``ex_rebuild_node``
  method.
  (GITHUB-370)
  [Nirmal Ranganathan]

- Add support for service scopes to the ``create_node`` method in the GCE
  driver.
  (LIBCLOUD-578, GITHUB-373)
  [Eric Johnson]

- Update GCE driver to allow for authentication with internal metadata service.
  (LIBCLOUD-625, LIBCLOUD-276, GITHUB-276)
  [Eric Johnson]

- Fix a bug in Elasticstack node creation method where it would raise
  exceptions because of missing data in a response, and also fix pulling the
  IP from the proper data item.
  (GITHUB-325)
  [Michael Bennett]

- Fix a bug which prevented user to connect and instantiate multiple EC2 driver
  instances for different regions at the same time.
  (GITHUB-325)
  [Michael Bennett]

- Add methods in CloudStack driver to manage mutiple nics per vm.
  (GITHUB-369)
  [Roeland Kuipers]

- Implements VPC network ACLs for CloudStack driver.
  (GITHUB-371)
  [Jeroen de Korte]

Storage
~~~~~~~

- Fix a bug with CDN requests in the CloudFiles driver.
  [Tomaz Muraus]

- Fix a bug with not being able to specify meta_data / tags when uploading an
  object using Google Storage driver.
  (LIBCLOUD-612, GITHUB-356)
  [Stefan Friesel]

Loadbalancer
~~~~~~~~~~~~

- Allow user to specify session affinity algorithm in the GCE driver by passing
  ``ex_session_affinity`` argument to the ``create_balancer`` method.
  (LIBCLOUD-595, GITHUB-341)
  [Lee Verberne, Eric Johnson]

DNS
~~~

- Various fixes in the Google DNS driver.
  (GITHUB-378)
  [Franck Cuny]

Changes with Apache Libcloud 0.15.1
-----------------------------------

Compute
~~~~~~~

- Allow user to limit a list of subnets which are returned by passing
  ``subnet_ids`` and ``filters`` argument to the ``ex_list_subnets``
  method in the EC2 driver.
  (LIBCLOUD-571, GITHUB-306)
  [Lior Goikhburg]

- Allow user to limit a list of internet gateways which are returned by
  passing ``gateway_ids`` and ``filters`` argument to the
  ``ex_list_internet_gateways`` method in the EC2 driver.
  (LIBCLOUD-572, GITHUB-307)
  [Lior Goikhburg]

- Allow user to filter which nodes are returned by passing ``ex_filters``
  argument to the ``list_nodes`` method in the EC2 driver.
  (LIBCLOUD-580, GITHUB-320)
  [Lior Goikhburg]

- Add network_association_id to ex_list_public_ips and CloudstackAddress object
  (GITHUB-327)
  [Roeland Kuipers]

- Allow user to specify admin password by passing ``ex_admin_pass`` argument
  to the ``create_node`` method in the Openstack driver.
  (GITHUB-315)
  [Marcus Devich]

- Fix a possible race condition in deploy_node which would occur if node
  is online and can be accessed via SSH, but the SSH key we want to use hasn't
  been installed yet.

  Previously, we would immediately throw if we can connect, but the SSH key
  hasn't been installed yet.
  (GITHUB-331)
  [David Gay]

- Propagate an exception in ``deploy_node`` method if user specified an invalid
  path to the private key file. Previously this exception was silently swallowed
  and ignored.
  [Tomaz Muraus]

DNS
~~~

- Include a better message in the exception which is thrown when a request
  in the Rackspace driver ends up in an ``ERROR`` state.
  [Tomaz Muraus]

Changes with Apache Libcloud 0.15.0
-----------------------------------

General
~~~~~~~

- Use lxml library (if available) for parsing XML. This should substantially
  reduce parsing time and memory usage for large XML responses (e.g. retrieving
  all the available images in the EC2 driver).
  [Andrew Mann]

- Use --head flag instead of -X HEAD when logging curl lines for HEAD requests
  in debug mode.

  Reported by Brian Metzler.
  (LIBCLOUD-552)
  [Tomaz Muraus]

- Fix Python 3 compatibility bugs in the following functions:

  * import_key_pair_from_string in the EC2 driver
  * publickey._to_md5_fingerprint
  * publickey.get_pubkey_ssh2_fingerprint

  (GITHUB-301)
  [Csaba Hoch]

- Update CA_CERTS_PATH to also look for CA cert bundle which comes with
  openssl Homebrew formula on OS x (/usr/local/etc/openssl/cert.pem).
  (GITHUB-309)
  [Pedro Romano]

- Update Google drivers to allow simultaneous authornization for all the
  supported Google Services.
  (GITHUB-302)
  [Eric Johnson]

Compute
~~~~~~~

- Fix create_key_pair method which was not returning private key.
  (LIBCLOUD-566)
  [Sebastien Goasguen]

- Map "Stopped" node state in the CloudStack driver to NodeState.STOPPED
  instead of NodeState.TERMINATED, "Stopping" to NodeState.PENDING instead of
  NodeState.TERMINATED and "Expunging" to NodeState.PENDING instead of
  NodeState.TERMINATED.
  (GITHUB-246)
  [Chris DeRamus, Tomaz Muraus]

- Add ex_create_tags and ex_delete_tags method to the CloudStack driver.
  (LIBCLOUD-514, GITHUB-248)
  [Chris DeRamus]

- Add new G2 instances to the EC2 driver.
  [Tomaz Muraus]

- Add support for multiple API versions to the Eucalyptus driver and allows
  user to pass "api_version" argument to the driver constructor.
  (LIBCLOUD-516, GITHUB-249)
  [Chris DeRamus]

- Map "Powered Off" state in the vCloud driver from "TERMINATED" to "STOPPED".
  (GITHUB-251)
  [Ash Berlin]

- Add ex_rename_node method to the DigitalOcean driver.
  (GITHUB-252)
  [Rahul Ranjan]

- Improve error parsing in the DigitalOcean driver.

  Reported by Deni Bertovic.
  [Tomaz Muraus]

- Add extension methods for the VPC internet gateway management to the EC2
  driver.
  (LIBCLOUD-525, GITHUB-255)
  [Chris DeRamus]

- Add CloudStackProject class to the CloudStack driver and add option to select
  project and disk offering on node creation.
  (LIBCLOUD-526, GITHUB-257)
  [Jim Divine]

- Fix IP address handling in the OpenStack driver.
  (LIBCLOUD-503, GITHUB-235)
  [Markos Gogoulos]

- Ad new ex_delete_image and ex_deprecate_image method to the GCE driver.
  (GITHUB-260)
  [Franck Cuny]

- Ad new ex_copy_image method to the GCE driver.
  (GITHUB-258)
  [Franck Cuny]

- Ad new ex_set_volume_auto_delete method to the GCE driver.
  (GITHUB-264)
  [Franck Cuny]

- Add ex_revoke_security_group_ingress method to the CloudStack driver.
  [Chris DeRamus, Tomaz Muraus]

- Allow user to pass ex_ebs_optimized argument to the create_node method
  in the EC2 driver.
  (GITHUB-272)
  [zerthimon]

- Add "deprecated" attribute to the Node object in the Google Compute Engine
  driver.
  (GITHUB-276)
  [Chris / bassdread]

- Update Softlayer driver to use "fullyQualifiedDomainName" instead of
  "hostname" attribute for the node name.
  (GITHUB-280)
  [RoelVanNyen]

- Allow user to specify target tags using target_tags attribute when creating
  a firewall rule in the GCE driver.
  (GITHUB-278)
  [zerthimon]

- Add new standard API for image management and initial implementation for the
  EC2 and Rackspace driver.
  (GITHUB-277)
  [Matt Lehman]

- Allow user to specify "displayname" attribute when creating a CloudStack node
  by passing "ex_displayname" argument to the method.

  Also allow "name" argument to be empty (None). This way CloudStack
  automatically uses Node's UUID for the name.
  (GITHUB-289)
  [Jeff Moody]

- Deprecate "key" argument in the SSHClient class in favor of new "key_files"
  argument.

  Also add a new "key_material" argument. This argument can contain raw string
  version of a private key.

  Note 1: "key_files" and "key_material" arguments are mutually exclusive.
  Note 2: "key_material" argument is not supported in the ShellOutSSHClient.

- Use node id attribute instead of the name for the "lconfig" label in the
  Linode driver. This way the label is never longer than 48 characters.
  (GITHUB-287)
  [earthgecko]

- Add a new driver for Outscale SAS and Outscale INC cloud
  (http://www.outscale.com).
  (GITHUB-285, GITHUB-293, LIBCLOUD-536, LIBCLOUD-553)
  [Benoit Canet]

- Add new driver for HP Public Cloud (Helion) available via Provider.HPCLOUD
  constant.
  [Tomaz Muraus]

- Allow user to specify availability zone when creating an OpenStack node by
  passing "ex_availability_zone" argument to the create_node method.
  Note: This will only work if the OpenStack installation is running
  availability zones extension.
  (GITHUB-295, LIBCLOUD-555)
  [syndicut]

- Allow user to pass filters to ex_list_networks method in the EC2 driver.
  (GITHUB-294)
  [zerthimon]

- Allow user to retrieve container images using ex_get_image method in the
  Google Compute Engine driver.
  (GITHUB-299, LIBCLOUD-562)
  [Magnus Andersson]

- Add new driver for Kili public cloud (http://kili.io/)
  [Tomaz Muraus]

- Add "timeout" argument to the ParamikoSSHClient.run method. If this argument
  is specified and the command passed to run method doesn't finish in the
  defined timeout, `SSHCommandTimeoutError` is throw and the connection to the
  remote server is closed.

  Note #1: If timed out happens, this functionality doesn't guarantee that the
  underlying command will be stopped / killed. The way it works it simply
  closes a connect to the remote server.
  [Tomaz Muraus]

  Note #2: "timeout" argument is only available in the Paramiko SSH client.

- Make "cidrs_ips" argument in the ex_authorize_security_group_egress method in
  the EC2 driver mandatory.
  (GITHUB-301)
  [Csaba Hoch]

- Add extension methods for managing floating IPs (ex_get_floating_ip,
  ex_create_floating_ip, ex_delete_floating_ip) to the Openstack 1.1 driver.
  (GITHUB-301)
  [Csaba Hoch]

- Fix bug in RimuHosting driver which caused driver not to work when the
  provider returned compressed (gzip'ed) response.
  (LIBCLOUD-569, GITHUB-303)
  [amastracci]

- Fix issue with overwriting the server memory values in the RimuHosting
  driver.
  (GUTHUB-308)
  [Dustin Oberloh]

- Add ex_all_tenants argument to the list_nodes method in the OpenStack driver.
  (GITHUB-312)
  [LIBCLOUD-575, Zak Estrada]

- Add support for network management for advanced zones
  (ex_list_network_offerings, ex_create_network, ex_delete_network) in the
  CloudStack driver.
  (GITHUB-316)
  [Roeland Kuipers]

- Add extension methods for routes and route table management to the EC2
  driver (ex_list_route_tables, ex_create_route_table, ex_delete_route_table,
  ex_associate_route_table, ex_dissociate_route_table,
  ex_replace_route_table_association, ex_create_route, ex_delete_route,
  ex_replace_route)
  (LIBCLOUD-574, GITHUB-313)
  [Lior Goikhburg]

- Fix ex_list_snapshots for HP Helion OpenStack based driver.
  [Tomaz Muraus]

- Allow user to specify volume type and number of IOPS when creating a new
  volume in the EC2 driver by passing ``ex_volume_type`` and ``ex_iops``
  argument to the ``create_volume`` method.
  [Tomaz Muraus]

- Fix ex_unpause_node method in the OpenStack driver.
  (GITHUB-317)
  [Pablo Orduña]

- Allow user to launch EC2 node in a specific VPC subnet by passing
  ``ex_subnet`` argument to the create_node method.
  (GITHUB-318)
  [Lior Goikhburg]

Storage
~~~~~~~

- Fix container name encoding in the iterate_container_objects and
  get_container_cdn_url method in the CloudFiles driver. Previously, those
  methods would throw an exception if user passed in a container name which
  contained a whitespace.

  Reported by Brian Metzler.
  (LIBCLOUD-552)
  [Tomaz MUraus]

- Fix a bug in the OpenStack Swift driver which prevented the driver to work
  with installations where region names in the service catalog weren't upper
  case.
  (LIBCLOUD-576, GITHUB-311)
  [Zak Estrada]

Load Balancer
~~~~~~~~~~~~~

- Add extension methods for policy managagement to the ELB driver.
  (LIBCLOUD-522, GITHUB-253)
  [Rahul Ranjan]

DNS
~~~

- Fix update_record method in the Route56 driver so it works correctly for
  records with multiple values.
  [Tomaz Muraus]

- Add ex_create_multi_value_record method to the Route53 driver which allows
  user to create a record with multiple values with a single call.
  [Tomaz Muraus]

- Add new driver for Google DNS.
  (GITHUB-269)
  [Franck Cuny]

Changes with Apache Libcloud 0.14.1
-----------------------------------

Compute
~~~~~~~

- Add new m3.medium and m3.large instance information to the EC2 driver.
  [Tomaz Muraus]

- Add a new driver for CloudSigma API v2.0.
  [Tomaz Muraus]

- Add "volume_id" attribute to the Node "extra" dictionary in the EC2 driver.
  Also fix the value of the "device" extra attribute in the StorageVolume
  object. (LIBCLOUD-501)
  [Oleg Suharev]

- Add the following extension methods to the OpenStack driver: ex_pause_node,
  ex_unpause_node, ex_suspend_node, ex_resume_node.
  (LIBCLOUD-505, GITHUB-238)
  [Chris DeRamus]

- Add ex_limits method to the CloudStack driver.
  (LIBCLOUD-507, GITHUB-240)
  [Chris DeRamus]

- Add "extra" dictionary to the CloudStackNode object and include more
  attributes in the "extra" dictionary of the network and volume object.
  (LIBCLOUD-506, GITHUB-239)
  [Chris DeRamus]

- Add ex_register_image method to the EC2 driver.
  (LIBCLOUD-508, GITHUB-241)
  [Chris DeRamus]

- Add methods for managing volume snapshots to the OpenStack driver.
  (LIBCLOUD-512, GITHUB-245)
  [Chris DeRamus]

Load Balancer
~~~~~~~~~~~~~

- Fix a bug in the ex_targetpool_add_node and ex_targetpool_remove_node method
  in the GCE driver.
  [Rick Wright]

Storage
~~~~~~~

- Allow user to use an internal endpoint in the CloudFiles driver by passing
  "use_internal_url" argument to the driver constructor.
  (GITHUB-229, GITHUB-231)
  [John Obelenus]

DNS
~~~

- Add PTR to the supported record types in the Rackspace driver.
  [Tomaz Muraus]

- Fix Zerigo driver to set Record.name attribute for records which refer
  to the bare domain to "None" instead of an empty string.
  [Tomaz Muraus]

- For consistency with other drivers, update Rackspace driver to set
  Record.name attribute for the records which refer to the bare domain
  to "None" instead of setting them to FQDN.
  [Tomaz Muraus]

- Update Rackspace driver to support paginating through zones and records.
  (GITHUB-230)
  [Roy Wellington]

- Update Route53 driver so it supports handling records with multiple values
  (e.g. MX).
  (LIBCLOUD-504, GITHUB-237)
  [Chris DeRamus]

- Update Route53 driver to better handle SRV records.
  [Tomaz Muraus]

- Update Route53 driver, make sure "ttl" attribute in the Record extra
  dictionary is always an int.
  [Tomaz Muraus]

Changes with Apache Libcloud 0.14.0
-----------------------------------

General
~~~~~~~

- Update API endpoints which are used in the HostVirtual drivers.
  (LIBCLOUD-489)
  [Dinesh Bhoopathy]

- Add support for Amazon security token to the Amazon drivers.
  (LIBCLOUD-498, GITHUB-223)
  [Noah Kantrowitz]

Compute
~~~~~~~

- Remove Slicehost driver.

  SliceHost API has been shut down in 2012 so it makes no sense to keep
  this driver.
  [Tomaz Muraus]

- Modify drivers for public cloud providers which use HTTP Basic
  authentication to not allow insecure connections (secure constructor
  kwarg being set to False) by default.

  This way credentials can't accidentally be sent in plain text over the
  write.

  Affected drivers: Bluebox, Joyent, NephoScale, OpSource, VPSNet
  [Tomaz Muraus]

- Remove "public_ip" and "private_ip" property which has been deprecated in
  0.7.0 from the Node object.
  [Tomaz Muraus]

- Move "is_private_ip" and "is_valid_ip_address" function from
  libcloud.compute.base into libcloud.utils.networking module.
  [Tomaz Muraus]

- Allow user to pass "url" argument to the CloudStack driver constructor.
  This argument can be provided instead of "host" and "path" arguments and
  can contain a full URL to the API endpoint. (LIBCLOUD-430)
  [Tomaz Muraus]

- Allow user to pass None as a "location" argument to the create_node
  method. (LIBCLOUD-431)
  [Tomaz Muraus]

- Refactor CloudStack Connection class so it looks more like other
  connection classes and user can specify which attributes to send as part
  of query parameters in the GET request and which inside the body of a POST
  request.
  [Tomaz Muraus, Philipp Strube]

- Add a new driver for Exoscale (https://www.exoscale.ch/) provider.
  [Tomaz Muraus]

- Fix a bug in Abiquo driver which caused the driver to fail if the endpoint
  URL didn't start with "/api". (LIBCLOUD-447)

  Reported by Igor Ajdisek.
  [Tomaz Muraus]

- Modify CloudStack driver to correctly throw InvalidCredsError exception if
  invalid credentials are provided.
  [Tomaz Muraus]

- Don't throw an exception if a node object is missing an "image" attribute
  in the list nodes / get node response.

  This could happen if node is in an error state. (LIBCLOUD-455)
  [Dustin Spicuzza, Tomaz Muraus]

- Update CloudStack driver to better handle errors and throw ProviderError
  instead of a generic Exception.
  [Tomaz Muraus]

- Modify ex_list_networks methods in CloudStack driver to not thrown if there
  are no networks available.
  [Tomaz Muraus]

- Bump API version used in the EC2 driver from 2010-08-21 to 2013-10-15.
  (LIBCLOUD-454)
  [Tomaz Muraus]

- Add ex_get_limits method for retrieving account resource limits to the
  EC2 driver.
  [Tomaz Muraus]

- Update us-west-1 region in the EC2 driver to include c3 instance types.
  Also include pricing information.
  [Tomaz Muraus]

- For consistency, rename "ex_add_ip_forwarding_rule" method to
  "ex_create_ip_forwarding_rule".
  (GITHUB-196)
  [Oleg Suharev]

- Add support for new "i2" instance types to Amazon EC2 driver. Also
  update pricing file. (LIBCLOUD-465)
  [Chris DeRamus]

- Allow user to specify VPC id when creating a security group in the EC2
  driver by passing "vpc_id" argument to ex_create_security_group method.
  (LIBCLOUD-463, GITHUB-201)
  [Chris DeRamus]

- Add extension methods for managing security group rules
  (ex_authorize_security_group_ingress, ex_authorize_security_group_egress,
  ex_revoke_security_group_ingress, ex_revoke_security_group_egress) to the
  EC2 driver. (LIBCLOUD-466, GITHUB-202)
  [Chris DeRamus]

- Add extension methods for deleting security groups
  (ex_delete_security_group, ex_delete_security_group_by_id,
  ex_delete_security_group_by_name) to the EC2 driver.
  (LIBCLOUD-464, GITHUB-199)
  [Chris DeRamus]

- Add extension method for listing reserved instances
  (ex_list_reserved_nodes) to the EC2 driver. (LIBCLOUD-469, GITHUB-205)
  [Chris DeRamus]

- Add extension methods for VPC management (ex_list_networks,
  ex_create_network, ex_delete_network) to the EC2 driver.
  (LIBCLOUD-467, GITHUB-203)
  [Chris DeRamus]

- Add extension methods for VPC subnet management (ex_list_subnets,
  ex_create_subnet, ex_delete_subnet) to the EC2 driver.
  (LIBCLOUD-468, GITHUB-207)
  [Chris DeRamus]

- Add ex_get_console_output extension method to the EC2 driver.
  (LIBCLOUD-471, GITHUB-209)
  [Chris DeRamus]

- Include additional provider-specific attributes in the 'extra' dictionary
  of the StorageVolume class in the EC2 driver. (LIBCLOUD-473, GITHUB-210)
  [Chris DeRamus]

- Change attribute name in the 'extra' dictionary of EC2 and CloudStack
  Node object from "keyname" to "key_name". (LIBCLOUD-475)
  [Oleg Suharev]

- Fix a deployment issue which would some times cause a process to hang if
  the executed deployment script printed a lot of output to stdout or stderr.
  [Tomaz Muraus]

- Add additional attributes to the "extra" dictionary of the VolumeSnapshot
  object in the EC2 driver.

  Also modify create_volume_snapshot method to correctly handle "name"
  argument. Previous, "name" argument was used as a snapshot description,
  now it's used as a Tag with a key "Name". (LIBCLOUD-480, GITHUB-214)
  [Chris DeRamus]

- Store additional attributes (iops, tags, block_device_mapping) in the
  "extra" dictionary of the NodeImage object in the EC2 driver.

  Also fix ex_image_ids filtering in the list_images method.
  (LIBCLOUD-481, GITHUB-215)
  [Chris DeRamus]

- Add extension methods for network interface management
  (ex_list_network_interfaces, ex_create_network_interface,
  ex_attach_network_interface_to_node, ex_detach_network_interface,
  ex_delete_network_interface) to the EC2 driver. (LIBCLOUD-474)
  [Chris DeRamus]

- Update Google Compute Engine driver to use and work with API v1.
  (LIBCLOUD-450)
  [Rick Wright]

- Modify ParamikoSSHClient so that "password" and "key" arguments are not
  mutually exclusive and both can be provided. (LIBCLOUD-461, GITHUB-194)
  [Markos Gogoulos]

- Add extension methods for the Elastic IP management to the EC2 driver.
  Also modify "ex_allocate_address" and "ex_release_address" method to
  take "domain" argument so it also works with VPC.
  (LIBCLOUD-470, GITHUB-208, GITHUB-220)
  [Chris DeRamus]

- Add additional provider specific attributes to the "extra" dictionary of
  the Node object in the EC2 driver. (LIBCLOUD-493, GITHUB-221)
  [Chris DeRamus]

- Add ex_copy_image and ex_create_image_from_node method to the EC2 driver.
  (LIBCLOUD-494, GITHUB-222)
  [Chris DeRamus]

Storage
~~~~~~~

- Allow user to specify 'Content-Disposition' header in the CloudFiles
  driver by passing 'content_disposition' key in the extra dictionary of
  the upload object methods. (LIBCLOUD-430)
  [Michael Farrell]

- Fix CloudFiles driver so it references a correct service catalog entry for
  the CDN endpoint.

  This was broken in the 0.14.0-beta3 release when we migrated all the
  Rackspace drivers to use auth 2.0 by default. (GITHUB-186)
  [John Obelenus]

- Update storage drivers to default to "application/octet-stream"
  Content-Type if none is provided and none can be guessed.
  (LIBCLOUD-433)
  [Michael Farrell]

- Fix a bug so you can now upload 0 bytes sized objects using multipart
  upload in the S3 driver. (LIBCLOUD-490)

  Reported by Noah Kantrowitz.
  [Tomaz Muraus]

- Update OpenStack Swift driver constructor so it accepts "region",
  "ex_force_service_type" and "ex_force_service_name" argument.
  [Tomaz Muraus]

- Deprecate "CLOUDFILES_SWIFT" provider constant in favor of new
  "OPENSTACK_SWIFT" one.
  [Tomaz Muraus]

- Add support for setting an ACL when uploading and object.
  (LIBCLOUD-497, GITHUB-223)
  [Noah Kantrowitz]

- Modify get_container method to use a more efficient "HEAD"
  approach instead of calling list_containers + doing late
  filterting.
  (LIBCLOUD-498, GITHUB-223)
  [Noah Kantrowitz]

DNS
~~~

- Implement iterate_* methods in the Route53 driver and makes it work
  correctly if there are more results which can fit on a single page.
  Previously, only first 100 results were returned. (LIBCLOUD-434)
  [Chris Clarke]

- Update HostVirtual driver constructor to only take "key" and other valid
  arguments. Previously it also took "secret" argument which it silently
  ignored. (LIBCLOUD-483)

  Reported by  Andrew Udvare.
  [Tomaz Muraus]

- Fix list_records method in the HostVirtual driver.
  (LIBCLOUD-484, GITHUB-218)

  Reported by Andrew Udvare.
  [Dinesh Bhoopathy]

Changes with Apache Libcloud 0.14.0-beta3
-----------------------------------------

General
~~~~~~~

- If the file exists, read pricing data from ~/.libcloud/pricing.json
  by default. If the file doesn't exist, fall back to the old behavior
  and use pricing data which is bundled with the release.
  [Tomaz Muraus]

- Add libcloud.pricing.download_pricing_file function for downloading and
  updating the pricing file.
  [Tomaz Muraus]

- Fix libcloud.utils.py3.urlquote so it works with unicode strings under
  Python 2. (LIBCLOUD-429)
  [Michael Farrell]

Compute
~~~~~~~

- Refactor Rackspace driver classes and make them easier to use. Now there
  are two Rackspace provider constants - Provider.RACKSPACE which
  represents new next-gen OpenStack servers and
  Provider.RACKSPACE_FIRST_GEN which represents old first-gen cloud
  servers.

  Note: This change is backward incompatible. For more information on those
  changes and how to update your code, please visit "Upgrade Notes"
  documentation page - http://s.apache.org/lc0140un
  [Tomaz Muraus]

- Deprecate the following EC2 provider constants: EC2_US_EAST,
  EC2_EU, EC2_EU_WEST, EC2_AP_SOUTHEAST, EC2_AP_NORTHEAST,
  EC2_US_WEST_OREGON, EC2_SA_EAST, EC2_SA_EAST and replace it with a new
  EC2 constant.
  Driver referenced by this new constant now takes a "region" argument which
  dictates to which region to connect.

  Note: Deprecated constants will continue to work until the next major
  release. For more information on those changes and how to update your
  code, please visit "Upgrade Notes" documentation page -
  http://s.apache.org/lc0140un
  [Tomaz Muraus]

- Add support for volume related functions to OpenNebula driver.
  (LIBCLOUD-354)
  [Emanuele Rocca]

- Add methods for managing storage volumes to the OpenStack driver.
  (LIBCLOUD-353)
  [Bernard Kerckenaere]

- Add new driver for Google Compute Engine (LIBCLOUD-266, LIBCLOUD-386)
  [Rick Wright]

- Fix create_node "features" metadata and update affected drivers.
  (LIBCLOUD-367)
  [John Carr]

- Update EC2 driver to accept the auth kwarg (it will accept NodeAuthSSH
  objects and automatically import a public key that is not already
  uploaded to the EC2 keyring). (Follow on from LIBCLOUD-367).
  [John Carr]

- Unify extension argument names for assigning a node to security groups
  in EC2 and OpenStack driver.
  Argument in the EC2 driver has been renamed from ex_securitygroup to
  ex_security_groups. For backward compatibility reasons, old argument
  will continue to work until the next major release. (LIBCLOUD-375)
  [Tomaz Muraus]

- Add ex_import_keypair_from_string and ex_import_keypair method to the
  CloudStack driver. (LIBCLOUD-380)
  [Sebastien Goasguen]

- Add support for managing floating IP addresses to the OpenStack driver.
  (LIBCLOUD-382)
  [Ivan Kusalic]

- Add extension methods for handling port forwarding to the CloudStack
  driver, rename CloudStackForwardingRule class to
  CloudStackIPForwardingRule. (LIBCLOUD-348, LIBCLOUD-381)
  [sebastien goasguen]

- Hook up deploy_node functionality in the CloudStack driver and unify
  extension arguments for handling security groups. (LIBCLOUD-388)
  [sebastien goasguen]

- Allow user to pass "args" argument to the ScriptDeployment and
  ScriptFileDeployment class. This argument tells which command line
  arguments get passed to the ScriptDeployment script. (LIBCLOUD-394)

  Note: This change is backward incompatible. For more information on how
  this affects your code and how to update it, visit "Upgrade Notes"
  documentation page - http://s.apache.org/lc0140un
  [Tomaz Muraus]

- Allow user to specify IAM profile to use when creating an EC2 node.
  (LIBCLOUD-403)
  [Xavier Barbosa]

- Add support for keypair management to the OpenStack driver.
  (LIBCLOUD-392)
  [L. Schaub]

- Allow user to specify disk partitioning mode using ex_disk_config argument
  in the OpenStack based drivers. (LIBCLOUD-402)
  [Brian Curtin]

- Add new driver for NephoScale provider (http://nephoscale.com/).
  (LIBCLOUD-404)
  [Markos Gogoulos]

- Update network related extension methods so they work correctly with
  both, OpenStack and Rackspace driver. (LIBCLOUD-368)
  [Tomaz Muraus]

- Add tests for networking functionality in the OpenStack and Rackspace
  driver.
  [Tomaz Muraus]

- Allow user to pass all supported extension arguments to ex_rebuild_server
  method in the OpenStack driver. (LIBCLOUD-408)
  [Dave King]

- Add pricing information for Rackspace Cloud Sydney region.
  [Tomaz Muraus]

- Update EC2 instance type map and pricing data. High Storage instances are
  now also available in Sydney and Singapore region.
  [Tomaz Muraus]

- Add new methods for managing storage volumes and snapshots to the EC2
  driver (list_volumes, list_snapshots, destroy_volume_snapshot,
  create_volume_snapshot) (LIBCLOUD-409)
  [Oleg Suharev]

- Add the following new extension methods to EC2 driver: ex_destroy_image,
  ex_modify_instance_attributes, ex_delete_keypair. (LIBCLOUD-409)
  [Oleg Suharev]

- Allow user to specify a port range when creating a port forwarding rule.
  (LIBCLOUD-409)
  [Oleg Suharev]

- Align Joyent driver with other drivers and deprecate "location" argument
  in the driver constructor in favor of "region" argument.

  Note: Deprecated argument will continue to work until the next major
  release.
  [Tomaz Muraus]

- Deprecate the following ElasticHosts provider constants: ELASTICHOSTS_UK1,
  ELASTICHOSTS_UK2, ELASTICHOSTS_US1, ELASTICHOSTS_US2, ELASTICHOSTS_US3,
  ELASTICHOSTS_CA1, ELASTICHOSTS_AU1, ELASTICHOSTS_CN1 and replace it with a
  new ELASTICHOSTS constant.
  Driver referenced by this new constant now takes a "region" argument which
  dictates to which region to connect.

  Note: Deprecated constants will continue to work until the next major
  release. For more information on those changes and how to update your
  code, please visit "Upgrade Notes" documentation page -
  http://s.apache.org/lc0140un (LIBCLOUD-383)
  [Michael Bennett, Tomaz Muraus]

- Add log statements to our ParamikoSSHClient wrapper. This should make
  debugging deployment issues easier. (LIBCLOUD-414)
  [Tomaz Muraus]

- Add new "NodeState.STOPPED" node state. Update HostVirual and EC2 driver to
  also recognize this new state. (LIBCLOUD-296)
  [Jayy Vis]

- Add new Hong Kong endpoint to Rackspace driver.
  [Brian Curtin]

- Fix ex_delete_keypair method in the EC2 driver. (LIBCLOUD-415)
  [Oleg Suharev]

- Add the following new extension methods for elastic IP management to the
  EC2 driver: ex_allocate_address, ex_disassociate_address,
  ex_release_address. (LIBCLOUD-417)
  [Patrick Armstrong]

- For consistency and accuracy, rename "ex_associate_addresses" method in the
  EC2 driver to "ex_associate_address_with_node".

  Note: Old method will continue to work until the next major release.
  [Tomaz Muraus]

- Add new driver for CloudFrames (http://www.cloudfounders.com/CloudFrames)
  provider. (LIBCLOUD-358)
  [Bernard Kerckenaere]

- Update default kernel versions which are used when creating a Linode
  server.

  Old default kernel versions:

  - x86 - 2.6.18.8-x86_64-linode1
  - x86_64 - 2.6.39.1-linode34

  New default kernel versions:

  - x86 - 3.9.3-x86-linode52
  - x86_64 - 3.9.3-x86_64-linode33

  (LIBCLOUD-424)
  [Tomaz Muraus, Jon Chen]

- Disable cache busting functionality in the OpenStack and Rackspace next-gen
  driver and enable it only for Rackspace first-gen driver.
  [Tomaz Muraus]

- Update Google Compute Engine driver to v1beta16.
  [Rick Wright]

- Modify auth_url variable in the OpenStack drivers so it works more like
  users would expect it to.

  Previously path specified in the auth_url was ignored and only protocol,
  hostname and port were used. Now user can provide a full url for the
  auth_url variable and the path provided in the url is also used.
  [DaeMyung Kang, Tomaz Muraus]

- Allow user to associate arbitrary key/value pairs with a node by passing
  "ex_metadata" argument (dictionary) to create_node method in the EC2
  driver.
  Those values are associated with a node using tags functionality.
  (LIBCLOUD-395)
  [Ivan Kusalic]

- Add "ex_get_metadata" method to EC2 and OpenStack driver. This method reads
  metadata dictionary from the Node object. (LIBCLOUD-395)
  [Ivan Kusalic]

- Multiple improvements in the Softlayer driver:
    - Map "INITIATING" node state to NodeState.PENDING
    - If node is launching remap "halted" state to "pending"
    - Add more node sizes
    - Add ex_stop_node and ex_start_node method
    - Update tests response fixtures

  (LIBCLOUD-416)
  [Markos Gogoulos]

- Modify list_sizes method in the KT UCloud driver to work, even if the item
  doesn't have 'diskofferingid' attribute. (LIBCLOUD-435)
  [DaeMyung Kang]

- Add new c3 instance types to the EC2 driver.
  [Tomaz Muraus]

- Fix an issue with the ex_list_keypairs and ex_list_security_groups method
  in the CloudStack driver which caused an exception to be thrown if the API
  returned no keypairs / security groups.
  (LIBCLOUD-438)
  [Carlos Reategui, Tomaz Muraus]

- Fix a bug in the OpenStack based drivers with not correctly checking if the
  auth token has expired before re-using it. (LIBCLOUD-428)

  Reported by Michael Farrell.
  [Tomaz Muraus,  Michael Farrell]

Storage
~~~~~~~

- Deprecate CLOUDFILES_US and CLOUDFILES_UK provider constant and replace
  it with a new CLOUDFILES constant.
  Driver referenced by this new constant takes a "region" keyword argument
  which can be one of 'ord', 'dfw', 'iad', 'syd', 'lon'.

  Note: Deprecated constants will continue to work until the next major
  release.
  For more information on this change, please visit "Upgrade Notes"
  documentation section - http://s.apache.org/lc0140un
  [Tomaz Muraus]

- Allow users to filter objects starting with a prefix by passing ex_prefix
  argument to the list_container_objects method in the S3, Google Storage
  and CloudFiles driver. (LIBCLOUD-369)
  [Stefan Friesel]

- Fix an issue with mutating connectionCls.host attribute in the Azure
  driver. This bug prevented user from having multiple Azure drivers with
  different keys instantiated at the same time. (LIBCLOUD-399)
  [Olivier Grisel]

- Add a new driver for KT UCloud based on the OpenStack Swift driver.
  (LIBCLOUD-431).
  [DaeMyung Kang]

Load Balancer
~~~~~~~~~~~~~

- Deprecate RACKSPACE_US and RACKSPACE_UK provider constant and replace it
  with a new RACKSPACE constant.
  Driver referenced by this new constant takes a "region" keyword argument
  which can be one of the following: 'ord', 'dfw', 'iad', 'syd', 'lon'.

  Note: Deprecated constants will continue to work until the next major
  release.
  For more information on this change, please visit "Upgrade Notes"
  documentation section - http://s.apache.org/lc0140un
  [Tomaz Muraus]

- Add new driver for Google Compute Engine (LIBCLOUD-386)
  [Rick Wright]

- Add new Hong Kong endpoint to Rackspace driver.
  [Brian Curtin]

DNS
~~~

- Deprecate RACKSPACE_US and RACKSPACE_UK provider constant and replace it
  with a new RACKSPACE constant.
  Driver referenced by this new constant takes a "region" keyword argument
  which can be one of the following: 'us', 'uk'.

  Note: Deprecated constants will continue to work until the next major
  release.
  For more information on this change, please visit "Upgrade Notes"
  documentation section - http://s.apache.org/lc0140un
  [Tomaz Muraus]

- Use string instead of integer for RecordType ENUM value.

  Note: If you directly use an integer instead of RecordType ENUM class you
  need to update your code to use the RecordType ENUM otherwise the code
  won't work. For more information on how to do that, see "Upgrade Notes"
  documentation section - http://s.apache.org/lc0140un
  [Tomaz Muraus]

- Add "export_zone_to_bind_format" and export_zone_to_bind_zone_file method
  which allows users to export Libcloud Zone to BIND zone format.
  (LIBCLOUD-398)
  [Tomaz Muraus]

- Update issue with inexistent zone / record handling in the get_zone and
  get_record method in the Linode driver. Those issues were related to
  changes in the Linode API. (LIBCLOUD-425)
  [Jon Chen]

Changes with Apache Libcloud 0.13.3
-----------------------------------

Compute
~~~~~~~

- Send "scrub_data" query parameter when destroying a DigitalOcean node.
  This will cause disk to be scrubbed (overwritten with 0's) when destroying
  a node. (LIBCLOUD-487)

  Note: This fixes a security issue with a potential leak of data contained
  on the destroyed node which only affects users of the DigitalOcean driver.
  (CVE-2013-6480)
  [Tomaz Muraus]

Changes with Apache Libcloud 0.13.2
-----------------------------------

General
~~~~~~~

- Don't sent Content-Length: 0 header with POST and PUT request if "raw"
  mode is used. This fixes a regression which could cause broken behavior
  in some storage driver when uploading a file from disk.
  (LIBCLOUD-396)
  [Ivan Kusalic]

Compute
~~~~~~~

- Added Ubuntu Linux 12.04 image to ElasticHost driver image list.
  (LIBCLOUD-364)
  [Bob Thompson]

- Update ElasticHosts driver to store drive UUID in the node 'extra' field.
  (LIBCLOUD-357)
  [Bob Thompson]

Storage
~~~~~~~

- Store last_modified timestamp in the Object extra dictionary in the S3
  driver. (LIBCLOUD-373)
  [Stefan Friesel]

Load Balancer
~~~~~~~~~~~~~

- Expose CloudStack driver directly through the Provider.CLOUDSTACK
  constant.
  [Tomaz Muraus]

DNS
~~~

- Modify Zerigo driver to include record TTL in the record 'extra' attribute
  if a record has a TTL set.
  [Tomaz Muraus]

- Modify values in the Record 'extra' dictionary attribute in the Zerigo DNS
  driver to be set to None instead of an empty string ('') if a value for
  the provided key is not set.
  [Tomaz Muraus]

Changes with Apache Libcloud 0.13.1
-----------------------------------

General
~~~~~~~

- Fix a regression introduced in 0.13.0 and make sure to include
  Content-Length 0 with PUT and POST requests. (LIBCLOUD-362, LIBCLOUD-390)
  [Tomaz Muraus]

Compute
~~~~~~~

- Fix a bug in the ElasticHosts driver and check for right HTTP status
  code when determining drive imaging success. (LIBCLOUD-363)
  [Bob Thompson]

- Update Opsource driver to include node public ip address (if available).
  (LIBCLOUD-384)
  [Michael Bennett]

Storage
~~~~~~~

- Fix a regression with calling encode_container_name instead of
  encode_object_name on object name in get_object method.
  Reported by Ben Meng (LIBCLOUD-366)
  [Tomaz Muraus]

- Ensure that AWS S3 multipart upload works for small iterators.
  (LIBCLOUD-378)
  [Mahendra M]

Changes with Apache Libcloud 0.13.0
-----------------------------------

General
~~~~~~~

- Add homebrew curl-ca-bundle path to CA_CERTS_PATH. This will make Libcloud
  use homebrew curl ca bundle file (if available) for server certificate
  validation. (LIBCLOUD-324)
  [Robert Chiniquy]

- Modify OpenStackAuthConnection and change auth_token_expires attribute to
  be a datetime object instead of a string.
  [Tomaz Muraus]

- Modify OpenStackAuthConnection to support re-using of the existing auth
  token if it's still valid instead of re-authenticating on every
  authenticate() call.
  [Tomaz Muraus]

- Modify base Connection class to not send Content-Length header if body is
  not provided.
  [Tomaz Muraus]

- Add the new error class ProviderError and modify InvalidCredsError to
  inherit from it. (LIBCLOUD-331)
  [Jayy Vis]

Misc
----

- Add unittest2 library dependency for tests and update some tests to use
  it.
  [Tomaz Muraus]

Compute
~~~~~~~

- Fix destroy_node method in the experimental libvirt driver.
  [Aymen Fitati]

- Add ex_start_node method to the Joyent driver. (LIBCLOUD-319)
  [rszabo50]

- Fix Python 3 compatibility issue in the ScriptFileDeployment class.
  (LIBCLOUD-321)
  [Arfrever Frehtes Taifersar Arahesis]

- Add ex_set_metadata_entry and ex_get_metadata method to the VCloud driver.
  (LIBCLOUD-318)
  [Michel Samia]

- Various improvements and bug-fixes in the VCloud driver. (LIBCLOUD-323)
  [Michel Samia]

- Various bug fixes and improvements in the HostVirtual driver.
  (LIBCLOUD-249)
  [Dinesh Bhoopathy]

- Modify list_sizes method in the OpenStack driver to include
  OpenStackNodeSize object which includes 'vcpus' attribute which holds
  a number of virtual CPUs for this size. (LIBCLOUD-325)
  [Carlo]

- For consistency rename "ex_describe_keypairs" method in the EC2 driver to
  "ex_describe_keypair".
  [Tomaz Muraus]

- Modify "ex_describe_keypair" method to return key fingerprint in the
  return value. (LIBCLOUD-326)
  [Andre Merzky, Tomaz Muraus]

- Populate private_ips attribute in the CloudStack drive when returning
  a Node object from the create_node method. (LIBCLOUD-329)
  [Sebastien Goasguen, Tomaz Muraus]

- Allow user to pass extra arguments via "extra_args" argument which are
  then passed to the "deployVirtualMachine" call in the CloudStack driver
  create_node method. (LIBCLOUD-330)
  [Sebastien Goasguen, Tomaz Muraus]

- Update Gandi driver to handle new billing model. (LIBCLOUD-317)
  [Aymeric Barantal]

- Fix a bug in the Linode driver and remove extra newline which is added
  when generating a random root password in create_node. (LIBCLOUD-334)
  [Juan Carlos Moreno]

- Add extension methods for managing keypairs to the CloudStack driver.
  (LIBCLOUD-333)
  [sebastien goasguen]

- Add extension methods for managing security groups to the CloudStack
  driver. (LIBCLOUD-332)
  [sebastien goasguen]

- Add extension methods for starting and stoping the node to the
  CloudStack driver. (LIBCLOUD-338)
  [sebastien goasguen]

- Fix old _wait_until_running method. (LIBCLOUD-339)
  [Bob Thompson]

- Allow user to override default async task completion timeout by
  specifying ex_clone_timeout argument. (LIBCLOUD-340)
  [Michal Galet]

- Fix a bug in the GoGrid driver get_uuid method. (LIBCLOUD-341)
  [Bob Thompson]

- Fix a bug with deploy_node not respecting 'timeout' kwarg.
  [Kevin Carter]

- Modify create_node method in CloudStack driver to return an instance of
  CloudStackNode and add a new "expunging" node state. (LIBCLOUD-345)
  [sebastien goasguen]

- Update API endpoint hostnames in the ElasticHost driver and use hostnames
  which return a valid SSL certificate. (LIBCLOUD-346)
  [Bob Thompson]

- Add ex_list_networks method and missing tests for list_templates to the
  CloudStack driver. (LIBCLOUD-349)
  [Philipp Strube]

- Correctly throw InvalidCredsError if user passes invalid credentials to
  the DigitalOcean driver.
  [Tomaz Muraus]

Storage
~~~~~~~

- Fix an issue with double encoding the container name in the CloudFiles
  driver upload_object method.
  Also properly encode container and object name used in the HTTP request
  in the get_container and get_object method. (LIBCLOUD-328)
  [Tomaz Muraus]

Load Balancer
~~~~~~~~~~~~~

- Add ex_list_current_usage method to the Rackspace driver.

Changes with Apache Libcloud 0.12.4
-----------------------------------

Compute
~~~~~~~

- Fix a regression in Softlayer driver caused by the xmlrpclib changes.
  (LIBCLOUD-310)
  [Jason Johnson]

- Allow user to pass alternate ssh usernames to deploy_node
  (ssh_alternate_usernames kwarg) which are used for authentication if the
  default one doesn't work. (LIBCLOUD-309)
  [Chris Psaltis, Tomaz Muraus]

- Fix a bug in EC2 list_locations method - 'name' attribute didn't contain a
  the right value.
  [Tomaz Muraus]

- Add new ScriptFileDeployment deployment class which reads deploy script
  from a file.
  [Rudolf J Streif]

- Add support for API version 5.1 to the vCloud driver and accept any value
  which is a multiple of four for ex_vm_memory kwarg in create_node method.
  (LIBCLOUD-314)
  [Trevor Powell]

Storage
~~~~~~~

- Fix a regression with removed ex_force_service_region constructor kwarg in
  the CloudFiles driver. (LIBCLOUD-260)

Changes with Apache Libcloud 0.12.3
-----------------------------------

General
~~~~~~~

- Fix Python 3.x related regressions. (LIBCLOUD-245)
  Reported by Arfrever Frehtes Taifersar Arahesis.
  [Tomaz Muraus]

- Fix a regression introduced with recent xmlrpiclib changes which broke all
  the Gandi.net drivers. (LIBCLOUD-288)

  Reported by Hutson Betts.
  [Tomaz Muraus]

- Improve deploy code to work correctly if the ssh user doesn't have access
  to the /root directory.

  Previously the ScriptDeployment script was stored in /root folder by
  default. Now it's stored in users home directory under filename
  ~/libcloud_deploymeny_<random>.sh. (LIBCLOUD-302)

  Reported by rotem on #libcloud.
  [Tomaz Muraus]

Compute
~~~~~~~

- Improve public and private IP address handling in OpenStack 1.1 driver.
  Assume every IP address which doesn't have a label "public" or "internet"
  is private. (LIBCLOUD-297)
  [Grischa Meyer, Tomaz Muraus]

- Add new driver for DigitalOcean provider - https://www.digitalocean.com/.
  (LIBCLOUD-304)
  [Tomaz Muraus]

- Fix a regression in ParamikoSSHClient.run method which caused this methid
  to only work as expected if you passed an absolute or a relative path to
  the script to it. (LIBCLOUD-278)
  [Tomaz Muraus]

DNS
~~~

- Allow user to specify 'priority' extra argument when creating a MX or SRV
  record.
  [Brian Jinwright, Tomaz Muraus]

Changes with Apache Libcloud 0.12.1
-----------------------------------

General
~~~~~~~

- Deprecate LazyList method of iteration over large paginated collections
  and use a new, more efficient generator based approach which doesn't
  require the iterator to be pre-exhausted and buffering all of the values
  in memory.

  Existing list_* methods which previously used LazyList class are
  preserving the old behavior and new iterate_* methods which use a new
  generator based approach have been added. (LIBCLOUD-254)
  [Mahendra M]

- Replace old ENUM style provider constants and replace them with a string
  version.
  This change allows users to dynamically register new drivers using a new
  set_driver method. (LIBCLOUD-255)
  [Mahendra M]

- Allow user to explicitly specify which CA file is used for verifying
  the server certificate by setting 'SSL_CERT_FILE' environment variable.

  Note: When this variable is specified, the specified path is the only
  CA file which is used to verifying the server certificate. (LIBCLOUD-283)
  [Tomaz Muraus, Erinn Looney-Triggs]

- Add a common module (libcloud.common.xmlrpc) for handling XML-RPC
  requests using Libcloud http layer.

  Also refactor existing drivers which use xmlrpclib directly (VCL, Gandi,
  Softlayer) to use this module.

  This change allows drivers to support LIBCLOUD_DEBUG and SSL certificate
  validation functionality. Previously they have bypassed Libcloud http
  layer so this functionality was not available. (LIBCLOUD-288)
  [John Carr]

Compute
~~~~~~~

- Fix string interpolation bug in __repr__ methods in the IBM SCE driver.
  (LIBCLOUD-242)
  [Tomaz Muraus]

- Fix test failures which happened in Python 3.3 due to:
  - hash randomization
  - changes in xml.etree module
  - changes in xmlrpc module
  (LIBCLOUD-245)
  [Tomaz Muraus]

- Improvements and additions in vCloud driver:
    - Expose generic query method (ex_query)
    - Provide functionality to get and set control access for vApps. This way
      created vApps can be shared between users/groups or everyone.

  (LIBCLOUD-251)
  [Michal Galet]

- Update EC2 pricing data to reflect new, lower prices -
  http://aws.typepad.com/aws/2012/10/new-ec2-second-generation-standard-instances-and-price-reductions-1.html
  [Tomaz Muraus]

- Update EC2 instance size to reflect new m3 instance types. Also refactor
  the code to make it easier to maintain.
  [Tomaz Muraus]

- Add a new driver for HostVirtual (http://www.vr.org) provider.
  (LIBCLOUD-249)
  [Dinesh Bhoopathy]

- Fix a bug where a numeric instead of a string value was used for the
  content-length header in VCloud driver. (LIBCLOUD-256)
  [Brian DeGeeter, Tomaz Muraus]

- Add a new driver for new Asia Pacific (Sydney) EC2 region.
  [Tomaz Muraus]

- Add support for managing security groups to the OpenStack driver. This
  patch adds the following extension methods:
  - ex_list_security_groups, ex_get_node_security_groups methods
  - ex_create_security_group, ex_delete_security_group
  - ex_create_security_group_rule, ex_delete_security_group_rule
  (LIBCLOUD-253)
  [L. Schaub]

- Modify ElasticStack driver class to pass 'vnc auto' instead of
  'vnc:ip auto' argument to the API when creating a server.
  It looks like 'vnc:ip' has been replaced with 'vnc'.
  [Rick Copeland, Tomaz Muraus]

- Add new EC2 instance type - High Storage Eight Extra Large Instance
  (hs1.8xlarge).
  [Tomaz Muraus]

- Map 'shutting-down' node state in EC2 driver to UNKNOWN. Previously
  it was mapped to TERMINATED. (LIBCLOUD-280)

  Note: This change is backward incompatible which means you need to update
  your code if you rely on the old behavior.
  [Tomaz Muraus, Marcin Kuzminski]

- Change _wait_until_running method so it supports waiting on multiple nodes
  and make it public (wait_until_running). (LIBCLOUD-274)
  [Nick Bailey]

- Add new EC2 instance type - High Memory Cluster Eight Extra Large.
  (cr1.8xlarge).
  [Tomaz Muraus]

- Add new driver for Abiquo provider - http://www.abiquo.com (LIBCLOUD-250).
  [Jaume Devesa]

- Allow user to pass 'ex_blockdevicemappings' kwarg to the EC2 driver
  'create_node' method. (LIBCLOUD-282)
  [Joe Miller, Tomaz Muraus]

- Improve error handling in the Brightbox driver.
  [Tomaz Muraus]

- Fix the ScriptDeployment step to work correctly if user provides a
  relative path for the script argument. (LIBCLOUD-278)
  [Jaume Devesa]

- Fix Softlayer driver and make sure all the code is up to date and works
  with the latest version of the actual Softlayer deployment (v3).
  (LIBCLOUD-287)
  [Kevin McDonald]

- Update EC2 driver, m3 instance types are now available in all the regions
  except Brazil.

  Also update pricing to reflect new (lower) prices.
  [Tomaz Muraus]

- Minor improvements in the HostVirtual driver and add new ex_get_node and
  ex_build_node extension method. (LIBCLOUD-249)
  [Dinesh Bhoopathy]

- Add ex_destroy_image method to IBM SCE driver. (LIBCLOUD-291)
  [Perry Zou]

- Add the following new regions to the ElasticHosts driver: sjc-c, syd-v,
  hkg-e. (LIBCLOUD-293)
  [Tomaz Muraus]

- Fix create_node in OpenStack driver to work correctly if 'adminPass'
  attribute is not present in the response.
  [Gavin McCance, Tomaz Muraus]

- Allow users to filter images returned by the list_images method in the EC2
  driver by providing ex_image_ids argument. (LIBCLOUD-294)
  [Chris Psaltis, Joseph Hall]

- Add support for OpenNebula 3.8. (LIBCLOUD-295)
  [Guillaume ZITTA]

- Add missing 'deletd' -> terminated mapping to OpenStack driver.
  (LIBCLOUD-276)
  [Jayy Vis]

- Fix create_node in OpenStack driver to work correctly if 'adminPass'
  attribute is not present in the response. (LIBCLOUD-292)
  [Gavin McCance, Tomaz Muraus]

Storage
~~~~~~~

- Add a new local storage driver.
  (LIBCLOUD-252, LIBCLOUD-258, LIBCLOUD-265, LIBCLOUD-273)
  [Mahendra M]

- Fix a bug which caused the connection to not be closed when using Python
  2.6 and calling get_object on an object which doesn't exist in the S3
  driver. (LIBCLOUD-257)
  [John Carr]

- Add a new generator based method for listing / iterating over the
  containers (iterate_containers). (LIBCLOUD-261)
  [Mahendra M]

- Add ex_purge_object_from_cdn method to the CloudFiles driver.
  (LIBCLOUD-267)
  [Tomaz Muraus]

- Support for multipart uploads and other improvements in the S3 driver
  so it can more easily be re-used with other implementations (e.g. Google
  Storage, etc.).

  Also default to a multipart upload when using upload_object_via_stream.
  This methods is more efficient compared to old approach because it only
  requires buffering a single multipart chunk (5 MB) in memory.
  (LIBCLOUD-269)
  [Mahendra M]

- Add new driver for Windows Azure Storage with support for block and page
  blobs. (LIBCLOUD-80)
  [Mahendra M]

DNS
~~~

- Update 'if type' checks in the update_record methods to behave correctly
  if users passes in RecordType.A with a value of 0 - if type is not None.
  (LIBCLOUD-247)
  [Tomaz Muraus]

- New driver for HostVirtual provider (www.vr.org). (LIBCLOUD-249)
  [Dinesh Bhoopathy]

- Finish Amazon Route53 driver. (LIBCLOUD-132)
  [John Carr]

- Add new driver for Gandi provider (https://www.gandi.net). (LIBCLOUD-281)
  [John Carr]

Load-Balancer
~~~~~~~~~~~~~

- Add new driver for AWS Elastic Load Balancing service. (LIBCLOUD-169)
  [John Carr]

Changes with Apache Libcloud 0.11.4
-----------------------------------

General
~~~~~~~

- Fix some of tests failures which happened in Python 3.3 due to randomized
  dictionary ordering. (LIBCLOUD-245)
  [Tomaz Muraus]

Compute
~~~~~~~

- Fix a bug where a numeric instead of a string value was used for the
  content-length header in VCloud driver. (LIBCLOUD-256)
  [Brian DeGeeter, Tomaz Muraus]

Storage
~~~~~~~

- Don't ignore ex_force_service_region argument in the CloudFiles driver.
  (LIBCLOUD-260)
  [Dan Di Spaltro]

- Fix a bug which caused the connection to not be closed when using Python
  2.6 and calling get_object on an object which doesn't exist in the S3
  driver. (LIBCLOUD-257)
  [John Carr]

DNS
~~~

- Update 'if type' checks in the update_record methods to behave correctly
  if users passes in RecordType.A with a value of 0 - if type is not None.
  (LIBCLOUD-247)
  [Tomaz Muraus]

Changes with Apache Libcloud 0.11.3
-----------------------------------

Storage
~~~~~~~

- Include 'last_modified' and 'content_type' attribute in the Object
  'extra' dictionary when retrieving object using get_object in the S3
  driver. Also modify 'meta_data' dictionary to include all the headers
  prefixed with 'x-amz-meta-'.
  [Tomaz Muraus]

Changes with Apache Libcloud 0.11.2
-----------------------------------

General
~~~~~~~

- Fix a bug with the Libcloud SSL verification code. Code was too strict and
  didn't allow "-" character in the sub-domain when using a wildcard
  certificate.

  Note: This is NOT a security vulnerability. (LIBCLOUD-244)
  [Tomaz Muraus]

Compute
~~~~~~~

- Add new Rackspace Nova driver for Chicago (ORD) location (LIBCLOUD-234)
  [Brian McDaniel]

- Add capacity information to Vdc objects and implement power operations.
  (LIBCLOUD-239)
  [Michal Galet]

- Allow user to pass 'timeout' argument to the 'deploy_node' method.
  [Tomaz Muraus]

- Add ex_list_security_groups, ex_authorize_security_group and
  ex_describe_all_keypairs methods to the EC2 driver. (LIBCLOUD-241,
  LIBCLOUD-243)
  [Nick Bailey]

- Add new methods for managing storage volumes and other extenstion methods
  to the IBM SCE driver. (LIBCLOUD-242)
  [Sengor Kusturica]

Storage
~~~~~~~

- Add the following new methods to the CloudFiles driver:
  ex_set_account_metadata_temp_url_key, ex_get_object_temp_url. (GITHUB-72)
  [Shawn Smith]

Load-balancer
~~~~~~~~~~~~~

- Add 'balancer' attribute to the Member instance. This attribute refers to
  the LoadBalancer instance this member belongs to.
  [Tomaz Muraus]

Changes with Apache Libcloud 0.11.1
-----------------------------------

General
~~~~~~~

- Fix hostname validation in the SSL verification code (CVE-2012-3446).

  Reported by researchers from the University of Texas at Austin (Martin
  Georgiev, Suman Jana and Vitaly Shmatikov).

Changes with Apache Libcloud 0.11.0
-----------------------------------

Compute
~~~~~~~

- Add a timeout of 10 seconds to OpenStackAuthConnection class.
  (LIBCLOUD-199)
  [Chris Gilmer]

- Add time.sleep(wait_period) to _ssh_client_connect to prevent busy loops
  when we immediately can't connect to a server. (LIBCLOUD-197)
  [Jay Doane]

- Fix a bug with Python 3 support in the following drivers
  - IBM SCE,
  - CloudStack
  - CloudSigma
  - OpenNebula
  - VpsNet
  - EC2
  - ElasticStack
  - vCloud
  - OpSource
  - Slicehost
  - Joyent
  (LIBCLOUD-204)
  [Sengor Kusturica, Hutson Betts, Tomaz Muraus]

- Make CloudStack driver more robust and make it work if list_images() call
  returns no images. (LIBCLOUD-202)
  [Gabriel Reid]

- Add force_ipv4 argument to _wait_until_running and default it to True.
  This will make Libcloud ignore IPv6 addresses when using deploy_node.
  (LIBCLOUD-200)
  [Jay Doane, Tomaz Muraus]

- Include error text if a CloudStack async job returns an error code.
  (LIBCLOUD-207)
  [Gabriel Reid]

- Add extenstion methods for block storage volume management to the
  CloudStack driver. (LIBCLOUD-208)
  [Gabriel Reid]

- New driver for KT UCloud (http://home.ucloud.olleh.com/main.kt) based on
  the CloudStack driver.
  [DaeMyung Kang]

- Add a standard API and methods for managing storage volumes to the
  EC2 and CloudStack drivers. Base API consistent of the following methods:
  create_volume, destroy_volume, attach_volume, detach_volume.
  (LIBCLOUD-213)
  [Gabriel Reid]

- Change ex_describe_tags, ex_create_tags and ex_delete_tags methods
  signature in the EC2 driver. Argument is now called resource (previously
  it was called node). This methods work with both Node and StorageVolume
  objects. (LIBCLOUD-213)
  [Gabriel Reid, Tomaz Muraus]

- Add Rackspace Nova London driver.
  [Chris Gilmer]

- Fix a bug - If user doesn't pass in 'network_id' argument to the
  create_node method in the CloudStack driver, don't explicitly define it.
  (LIBCLOUD-219)
  [Bruno Mahé, Tomaz Muraus]

- Modify EC2 driver to also return cc2.8xlarge cluster compute instance in
  the eu-west-1 region.
  [Tomaz Muraus]

- Add 'auth_user_variable' to the  OpenStackAuthConnection class.
  [Mark Everett]

- Fix a bug with repeated URLs in some requests the vCloud driver.
  (LIBCLOUD-222)
  [Michal Galet]

- New Gridspot driver with basic list and destroy functionality.
  (LIBCLOUD-223)
  [Amir Elaguizy]

- Add methods for managing storage volumes to the Gandi driver.
  (LIBCLOUD-225)
  [Aymeric Barantal]

DNS
~~~

- Add support for GEO RecordType to Zerigo driver. (LIBCLOUD-203)
  [Gary Wilson]

- Fix a bug with Python 3 support in the following drivers (LIBCLOUD-204)
  - Zerigo
  [Tomaz Muraus]

- Add support for URL RecordType to Zerigo driver. (LIBCLOUD-209)
  [Bojan Mihelac]

- Properly handle record creation when user doesn't provider a record name
  and wants to create a record for the actual domain.
  Reported by Matt Perry (LIBCLOUD-224)
  [Tomaz Muraus]

Storage
~~~~~~~

- Fix a bug with Python 3 support in the following drivers
  - Atmos
  - Google Storage
  - Amazon S3
  (LIBCLOUD-204)
  [Tomaz Muraus]

- Fix a bug in the CloudFiles driver which prevented it to work with
  accounts which use a non ORD endpoint. (LIBCLOUD-205)
  [Geoff Greer]

- Fix a bug in the enable_container_cdn method. (LIBCLOUD-206)
  [Geoff Greer]

- Allow user to specify container CDN TTL when calling container.enable_cd()
  using ex_ttl keyword argument in the CloudFiles driver.
  [Tomaz Muraus]

- Add ex_enable_static_website and ex_set_error_page method to the
  CloudFiles driver.
  [Tomaz Muraus]

- Propagate kwargs passed to container.download_object() to
  driver.download_object(). (LIBCLOUD-227)
  [Benno Rice]

- Fix a bug with not escaping container and object name in the Atmos driver.
  [Russell Keith-Magee, Benno Rice]

- Fix upload_object_via_stream method in the Atmos driver. (LIBCLOUD-228)
  [Benno Rice]

- Fix a bug with uploading zero-sized files in the OpenStack Swift /
  CloudFiles driver.
  [Tomaz Muraus]

- Fix a bug with content_type and encoding of object and path names in
  the Atmos driver.
  [Russell Keith-Magee]

Other
~~~~~

- Unify docstrings formatting in the compute drivers. (LIBCLOUD-229)
  [Ilgiz Islamgulov]

Changes with Apache Libcloud 0.10.1
-----------------------------------

General
~~~~~~~

- Add timeout attribute to base 'Connection' class and pass it to the
  connection class constructor if Python version is not 2.5.
  [Chris Gilmer]

Compute
~~~~~~~

- Update IBM SBC driver so it works with IBM Smart Cloud Enterprise.
  (LIBCLOUD-195)
  [Sengor Kusturica]

- Add ex_register_iso method to the CloudStack driver. (LIBCLOUD-196)
  [Daemian Mack]

- Allow user to specify which IP to use when calling deploy_node.
  (defaults to 'public_ips'). Previously it only worked with public IP, now
  user can pass 'private_ips' as an argument and SSH client will try to
  connect to the node first private IP address.
  [Jay Doane]

- Fix CloudSigmaLvsNodeDriver connectionCls bug.
  [Jerry Chen]

- Add 'ex_keyname' argument to the create_node method in the OpenStack
  driver. (LIBCLOUD-177)
  [Jay Doane]

- Fix a problem in deploy_node - make it work with providers which
  don't  instantly return created node in the list_node response.
  Also add __str__ and __repr__ method to DeploymentError so the
  error message is more useful. (LIBCLOUD-176)
  [Jouke Waleson, Tomaz Muraus]

- Add 'ssh_key' feature to Brigthbox driver. This way it works with
  deploy_node. (LIBCLOUD-179)
  [Neil Wilson]

- Add Joyent compute driver.
  [Tomaz Muraus]

- Store auth token expire times on the connection class in the attribute
  called 'auth_token_expires'. (LIBCLOUD-178)
  [Chris Gilmer, Brad Morgan]

- Add new driver for VCL cloud
  (http://www.educause.edu/blog/hes8/CloudComputingandtheVirtualCom/167931)
  (LIBCLOUD-180)
  [Jason Gionta, Tomaz Muraus]

- Improve and add new features to Brightbox driver
    - Update fixtures to represent actual api output
    - Update compute tests to 100% coverage
    - Add userdata and server group extensions to create_node
    - Add ipv6 support to public ip list
    - Improve in line documentation
    - Add lots of api output information to Node and Image
      'extra' attributes
    - Allow variable API versions (api_version argument)
    - Allow reverse dns updates for cloud ip extensions

  (LIBCLOUD-184)
  [Neil Wilson, Tomaz Muraus]

- Add ex_userdata argument to the OpenStack 1.1 driver. (LIBCLOUD-185)
  [Jay Doane]

- Modify Vmware vCloud driver and implement new features
  for the vCloud version 1.5. (LIBCLOUD-183)
  [Michal Galet, Sengor Kusturica]

- Allow user to pass mode argument to SSHClient.put method and default it to
  'w'. (LIBCLOUD-188)
  [Jay Doane]

- Modify SSHKeyDeployment step to use append mode so it doesn't overwrite
  existing entries in .ssh/authorized_keys. (LIBCLOUD-187)
  [Jay Doane]

- Modify ParamikoSSHClient to connect to the SSH agent and automatically
  look for private keys in ~/.ssh if the 'auth' and 'ssh_key' argument
  is not specified when calling deploy_node. (LIBCLOUD-182)
  [Tomaz Muraus]

- Add ex_rescue and ex_unrescue method to OpenStack 1.1 driver.
  (LIBCLOUD-193)
  [Shawn Smith]

- Include 'password' in the node extra dictionary when calling deploy_node
  if the password auth is used.
  [Juan Carlos Moreno]

- Add FileDeployment class to libcloud.compute.deployment module. This can
  be used as a replacement for ex_files argument if the provider supports
  deployment functionality. (LIBCLOUD-190)
  [Jay Doane]

Storage
~~~~~~~

- Large object upload support for CloudFiles driver
- Add CLOUDFILES_SWIFT driver to connect to OpenStack Swift
  [Dmitry Russkikh, Roman Bogorodskiy]

Load-balancer
~~~~~~~~~~~~~

- Don't include 'body_regex' attribute in the Rackspace driver body if
  body_regex is None or empty string. (LIBCLOUD-186)
  [Bill Woodward]

- Don't split Load balancer IP addresses into public and private list.
  Include all the addresses in the 'virtualIps' variable in the extra
  dictionary (Rackspace driver). (LIBCLOUD-191)
  [Adam Pickeral]

Changes with Apache Libcloud 0.9.1
----------------------------------

General
~~~~~~~

- Make parsing of the Auth API responses in the OpenStack drivers more
  flexible and extensible.

  Now, every connection class that inherits from the openstack base
  connection must implement get_endpoint(), who's job is to return the
  correct endpoint out of the service catalog.

  Note: The openstack.py base driver no longer works by default with
  Rackspace nova. The default endpoint parsed from the service catalog
  is the default compute endpoint for devstack. (LIBCLOUD-151)
  [Brad Morgan]

- Allow user to pass ex_tenant_name keyword argument to the OpenStack node
  driver class. This scopes all the endpoints returned by the Auth API
  endpoint to the provided tenant. (LIBCLOUD-172)
  [James E. Blair]

- Allow user to specify OpenStack service catalog parameters (service type,
  name and region). This way base OpenStack driver can be used with
  different providers without needing to subclass. (LIBCLOUD-173)
  [James E. Blair]

- Fix a bug with handling compressed responses in the Linode driver.
  (LIBCLOUD-158)
  [Ben Agricola]

Compute
~~~~~~~

- Add new RackspaceNovaBeta and RackspaveNovaDfw driver based on the
  OpenStack. (LIBCLOUD-151)
  [Brad Morgan]

- Include 'created' and 'updated' attribute in the OpenStack 1.1 driver.
  (LIBCLOUD-155)
  [Chris Gilmer]

- Include 'minRam' and 'minDisk' attribute in the OpenStack 1.1 driver
  Node extra dictionary. (LIBCLOUD-163)
  [Chris Gilmer]

- Allow users to use a list of tuples for the query string parameters inside
  the OpenStack connection classes. This way same key can be specified
  multiple times (LIBCLOUD-153)
  [Dave King]

- Allow user to pass 'max_tries' keyword argument to deploy_node method.
  [Tomaz Muraus]

- Include original exception error message when re-throwing an exception
  inside _run_deployment_script method.
  [Tomaz Muraus]

- Add support for ElasticHosts new United States (Los Angeles) and Canada
  (Toronto) locations. (GITHUB-53)
  [Jaime Irurzun]

- Add serverId attribute to the NodeImage object extra dictionary in the
  OpenStack driver.
  [Mark Everett]

- Add new EC2 instance type - m1.medium.
  [Tomaz Muraus]

- Allow user to re-use auth tokens and pass 'ex_force_auth_token' keyword
  argument to the OpenStack driver constructor. (LIBCLOUD-164)
  [Dave King]

- Add new experimental libvirt driver.
  [Tomaz Muraus]

- Properly handle OpenStack providers which return public IP addresses under
  the 'internet' key in the addresses dictionary.
  [Tomaz Muraus]

- Update create_node in Linode driver and make it return a Node object
  instead of a list. Reported by Jouke Waleson. (LIBCLOUD-175)
  [Tomaz Muraus]

Storage
~~~~~~~

- Don't lowercase special header names in the Amazon S3 storage driver.
  (LIBCLOUD-149)
  [Tomaz Muraus]

Load-balancer
~~~~~~~~~~~~~

- Allow user to specify a condition and weight when adding a member in
  the Rackspace driver.
  [Adam Pickeral]

- Add an extension method (ex_balancer_attach_members) for attaching
  multiple members to a load balancer in the Rackspace driver.
  (LIBCLOUD-152)
  [Adam Pickeral]

- Add ex_creaate_balancer method to the Rackspace driver and allow user to
  pass 'vip' argument to it. (LIBCLOUD-166)
  [Adam Pickeral]

- Update Rackspace driver to support Auth 2.0. (LIBCLOUD-165)
  [Dave King]

- Add new ex_create_balancer_access_rule and
  ex_create_balancer_access_rule_no_poll method to the Rackspace driver.
  (LIBCLOUD-170)
  [Dave King]

DNS
~~~

- Update Rackspace driver to support Auth 2.0. (LIBCLOUD-165)
  [Dave King]

Changes with Apache Libcloud 0.8.0
----------------------------------

General
~~~~~~~

- Add 'request_kwargs' argument to the get_poll_request_kwargs method.
  This argument contains kwargs which were previously used to initiate the
  poll request.
  [Mark Everett]

- Add support for handling compressed responses (deflate, gzip). Also send
  "Accept-Encoding" "gzip,deflate" header with all the requests.
  [Tomaz Muraus]

- Fix debug module (LIBCLOUD_DEBUG env variable) so it works with Python 3
  [Tomaz Muraus]

Compute
~~~~~~~

- Added support for retrieving OpenNebula v3.2 instance types, OpenNebula
  v3.0 network Public attribute support, and additional code coverage
  tests.
  [Hutson Betts]

- Add implementation for ex_save_image method to the OpenStack 1.1 driver.
  [Shawn Smith]

- Add support for Amazon new South America (Sao Paulo) location.
  [Tomaz Muraus]

- Fix a bug in OpenStack driver when 2.0_apikey or 2.0_password
  'auth_version' is used.
  [Tomaz Muraus]

- Current OpenNebula OCCI implementation does not support a proper
  restart method. Rather it suspends and resumes. Therefore, restart_node
  has been removed from the OpenNebula driver.
  [Hutson Betts]

- Enable ex_delete_image method in the OpenStack 1.1 driver.
  [Shawn Smith]

- Return NodeImage instance in OpenStack 1.1 driver ex_save_image method
  (LIBCLOUD-138)
  [Shawn Smith]

- Enable reboot_node method in the OpenNebula 3.2 driver.
  [Hutson Betts]

- Fix a public_ips Node variable assignment in the Gandi.net driver.
  [Aymeric Barantal]

- Updated the list of node states for OpenNebula drivers. (LIBCLOUD-148)
  [Hutson Betts]

Storage
~~~~~~~

- Propagate extra keyword arguments passed to the Rackspace driver
  connection class.
  [Dave King]

Load-balancer
~~~~~~~~~~~~~

- Add 'extra' attribute to the LoadBalancer object and retrieve all the
  virtual IP addresses in the Rackspace driver.
  [Dave King]

- Add list_supported_algorithms() method to the base LoadBalancer class.
  This method returns a list of supported algorithms by the provider.
  [Dave King]

- Update Rackspace driver:
    - Add two new supported algorithms: WEIGHTED_ROUND_ROBIN,
      WEIGHTED_LEAST_CONNECTIONS
    - Add ex_list_algorithm_names method
    - Add ex_get_balancer_error_page method
    - Add ex_balancer_access_list method
    - Populate LoadBalancer extra dictionary with more attributes
    - Add support for health monitors and connection throttling
    - Add more balancer states
    - ex_list_protocols_with_default_ports

  [Dave King]

- Propagate extra keyword arguments passed to the Rackspace driver
  connection class.
  [Dave King]

- Add 'extra' attribute to the Member object and populate it in
  the Rackspace driver.
  [Mark Everett]

- Adds status to the Member object and conditions an 'enum'
  (Rackspace driver).
  [Mark Everett]

- Add update_balancer method to the base LoadBalancer class.
  [Mark Everett]

- Add update_balancer method to the Rackspace driver.
  [Mark Everett]

- Add created and updated attribute to the LoadBalancer extra dictionary in
  the Rackspace driver.
  [Mark Everett]

- Fix protocol name maping in the Rackspace driver.
  [Bill Woodward]

Changes with Apache Libcloud 0.7.1
----------------------------------

General
~~~~~~~

 - Fix a minor bug in debug mode (LIBCLOUD_DEBUG=/dev/stderr) which has been
   introduced when adding Python 3 compatibility layer.
   [Paul Querna]

 - Update OpenStack Auth API endpoint paths.
   [Paul Querna]

Changes with Apache Libcloud 0.7.0
----------------------------------

General
~~~~~~~

- Add support for Python 3.x.
  [Tomaz Muraus]

- Remove old deprecated paths.
  [Tomaz Muraus]

Compute
~~~~~~~

- Update CloudSigma Zurich API endpoint address.
  [Tomaz Muraus]

- Add new US Las Vegas endpoint to CloudSigma driver (types.CLOUDSIGMA_US)
  [Tomaz Muraus]

- Allow user to specify drive type (hdd, ssd) when creating a
  CloudSigma server.

  Note 'ssd' drive_type doesn't work with the API yet.
  [Tomaz Muraus]

- Update OpenStack 1.1 driver to comply with the API specs. Need to make
  another call to retrieve node name and ip addresses when creating a node,
  because the first call only returns an id an the password. (GITHUB-40)
  [Dave King]

- Add ex_node_ids argument to the EC2 driver list_nodes method.
  (GITHUB-39)
  [Suvish Vt]

- If OpenStack Auth 2.0 API is used, also parse out tenant id and
  name and save it on the connection class (conn.tenant['id'],
  conn.tenant['name']).
  [Tomaz Muraus]

- Add new "Cluster Compute Eight Extra Large" size to the Amazon EC2
  driver.
  [Tomaz Muraus]

- Add the following extension methods to the EC2 compute driver:
  ex_describe_all_addresses, ex_associate_addresses, ex_start_node,
  ex_stop_node.
  [Suvish Vt]

- Change public_ip and private_ip attribute on the Node object to the
  public_ips and private_ips since both of the objects are always a list.

  Note: For backward compatibility you can still access public_ip and
  private_ip attributes, but this will be removed in the next release.
  [Tomaz Muraus]

- Fix an inconsistency in IBM SBC driver and make sure public_ips and
  private_ips attributes are a list.
  [Tomaz Muraus]

- Fix an inconsistency in OpSource driver and make sure public_ips is an
  empty list ([]), not 'unknown'
  [Tomaz Muraus]

- Updated support for OpenNebula.org v1.4, v2.x, and v3.x APIs and included
  additional compute tests validating functionality. (LIBCLOUD-121)
  [Hutson Betts]

Load-balancer
~~~~~~~~~~~~~

- Add ex_member_address argument to the Rackspace driver list_balancers
  method. If this argument is provided, only loadbalancers which have a
  member with the provided IP address attached are returned.
  [Tomaz Muraus]

Changes with Apache Libcloud 0.6.2
----------------------------------

General
~~~~~~~

- Fix a bug in PollingConnection class - actually use and don't ignore
  the poll_interval
  [Tomaz Muraus]

Compute
~~~~~~~

- Add support for Auth 2.0 API (keystone) to the OpenStack Auth
  connection class.
  [Brad Morgan]

- Add list_locations method to the OpenStack driver and fix some
  inconsistencies in the OpenStack driver extension method signatures.
  [Brad Morgan]

- Update Amazon EC2 driver and pricing data to support a new region -
  US West 2 (Oregon)
  [Tomaz Muraus]

- Expose 'CLOUDSTACK' provider. This driver can be used with an
  arbitrary CloudStack installation.
  [Tomaz Muraus]

Storage
~~~~~~~

- Update Amazon S3 driver to support a new region - US West 2 (Oregon)
  [Tomaz Muraus]

DNS
~~~

- Increase the default poll interval in the Rackspace driver to 2.5
  seconds.
  [Tomaz Muraus]

- Fix a bug in Rackspace Cloud DNS driver and make sure to throw an
  exception if an unexpected status code is returned. Reported by
  "jeblair".
  [Tomaz Muraus]

Changes with Apache Libcloud 0.6.1
----------------------------------

General
~~~~~~~

- Modify ParamikoSSHClient.connect so it supports authentication using a
  key file, (LIBCLOUD-116)
  [Jay Doane]

- User must now explicitly specify a path when using LIBCLOUD_DEBUG
  environment variable. (LIBCLOUD-95)
  [daveb, Tomaz Muraus]

- Add new XmlResponse and JsonResponse base class and modify all the
  driver-specific response classes to inherit from one of those two
  classes where applicable.
  [Caio Romão]

- Add new 'PollingConnection' class. This class can work with 'async'
  APIs. It sends and an initial request and then periodically poll the API
  until the job has completed or a timeout has been reached.
  [Tomaz Muraus]

Compute
~~~~~~~

- Add 24GB size to the GoGrid driver
  [Roman Bogorodskiy]

- Fix API endpoint URL in the Softlayer driver
  [Tomaz Muraus]

- Add support for OpenNebula 3.0 API (LIBCLOUD-120)
  [Hutson Betts]

- Add more attributes to the extra dictionary in the EC2 driver.
  (GITHUB-31)
  [Juan Carlos Moreno]

- Fix IP address assignment in the EC2 driver. Don't include "None" in the
  public_ip and private_ip Node list attribute.
  [Tomaz Muraus]

- Make deploy_node functionality more robust and don't start deployment if
  node public_ip attribute is an empty list.
  [Tomaz Muraus]

- Support SSH key authentication when using deploy_node.
  [Russell Haering, Tomaz Muraus]

- Enable deploy_node functionality in the EC2 driver using SSH key
  authentication
  [Russell Haering, Tomaz Muraus]

- Enable paramiko library debug log level if LIBCLOUD_DEBUG is used and
  paramiko is installed.
  [Tomaz Muraus]

- Fix the request signature generation in the base EC2 compute driver.
  If the endpoint is using a non-standard port (Eucalyptus based
  installations), append it to the hostname used to generate the
  signature.
  [Simon Delamare]

- Add new "unavailable" state to the BrightboxNodeDriver class.
  [Tim Fletcher]

- Increase a PollingConnection timeout in the CloudStack connection
  and fix the context dictionary creation in the _async_request method.
  [Oleg Suharev]

- Fix networks retrieval in the CloudStack driver create_node method.
  Also only pass 'networkids' field to the API if there are any networks
  available.
  [Oleg Suharev, Tomaz Muraus]

- Fix list_nodes in the CloudStack driver. Private IPs aren't always
  available.
  [Tomaz Muraus]

Load-baancer
~~~~~~~~~~~~

- Add a missing argument to the method call inside
  LoadBalancer.attach_compute_node and Driver.balancer_attach_compute_node.
  [Tim Fletcher, Tomaz Muraus]

- Add missing destroy() method to the LoadBalancer class.
  [Tomaz Muraus]

DNS
~~~

- New drivers for Rackspace Cloud DNS (US and UK region)
  [Tomaz Muraus]

- Add list_record_types() method. This method returns a list of record
  types supported by the provider.
  [Tomaz Muraus]

Changes with Apache Libcloud 0.6.0-beta1
----------------------------------------

General
~~~~~~~

- All the driver classes now inherit from the BaseDriver class
  [Tomaz Muraus]

- Prefer simplejson (if available) over json module. (LIBCLOUD-112)
  [Geoff Greer]

- Update compute demo and change the syntax of test credentials stored in
  test/secrets.py-dist. (LIBCLOUD-111)
  [Mike Nerone]

- Enable SSL certificate verification by default and throw an exception
  if CA certificate files cannot be found. This can be overridden by
  setting libcloud.security.VERIFY_SSL_CERT_STRICT to False.
  [Tomaz Muraus]

Compute
~~~~~~~

- Support for 1.1 API and many other improvements in the OpenStack driver ;
  LIBCLOUD-83
  [Mike Nerone, Paul Querna, Brad Morgan, Tomaz Muraus]

- Add some extra methods to the Gandi.net driver (LIBCLOUD-115)
  [Aymeric Barantal]

- Add ex_delete_image method to the Rackspace driver. (GITHUB-27)
  [David Busby]

- Linode driver now supports new 'Japan' location
  [Jed Smith]

- Rackspace driver now inherits from the OpenStack one instead of doing
  it vice versa. (LIBCLOUD-110)
  [Mike Nerone]

- Properly populate NodeImage "details" dictionary in the Rackspace
  compute driver. (LIBCLOUD-107)
  [Lucy Mendel]

- Fix a bug in Eucalyptus driver ex_describe_addresses method.
  [Tomaz Muraus]

- Add the following new extenstion methods to the Rackspace driver:
  ex_resize, ex_confirm_resize, ex_revert_resize.
  [Tomaz Muraus]

- Also allow user to pass in Node object to some ex\_ methods in
  the Rackspace compute driver.
  [Tomaz Muraus]

- Throw an exception in deploy_node if paramiko library is not
  available
  [Tomaz Muraus]

- Fix chmod argument value which is passed to the sftpclient.put
  method; GITHUB-17
  [John Carr]

- New driver for Ninefold.com. (LIBCLOUD-98)
  [Benno Rice]

Storage
~~~~~~~

- New driver for Google Storage based on the v1.0 / legacy API
  [Tomaz Muraus]

- New driver for Ninefold.com. (GITHUB-19)
  [Benno Rice]

- Fix a bug in uploading an object with some versions of Python 2.7
  where httplib library doesn't automatically call str() on the
  header values.
  [Tomaz Muraus]

- Allow users to upload (create) 0-bytes large (empty) objects
  [Tomaz Muraus]

Load-balancer
~~~~~~~~~~~~~

- New driver for Rackspace UK location
  [Tomaz Muraus]

- New driver for Ninefold.com. (LIBCLOUD-98)
  [Benno Rice]

DNS
~~~

- Drivers for Linode DNS and Zerigo DNS
  [Tomaz Muraus]

- Brand new DNS API!
  [Tomaz Muraus]

Changes with Apache Libcloud 0.5.2
----------------------------------

Compute
~~~~~~~

- New driver for serverlove.com and skalicloud.com
  [Tomaz Muraus]

- Fix node name and tag handling in the Amazon EC2 driver
  [Wiktor Kolodziej]

- Fix pricing and response handling in the OpenStack driver
  [Andrey Zhuchkov]

- Fix deploy_node() method and make it more robust
  [Tomaz Muraus]

- Users can now pass file like objects to ScriptDeployment and
  SSHKeyDeployment constructor.
  [Tomaz Muraus]

- Include node tags when calling list_nodes() in the Amazon EC2
  driver
  [Trevor Pounds]

- Properly handle response errors in the Rackspace driver and
  only throw InvalidCredsError if the returned status code is 401
  [Brad Morgan]

- Fix the create_node method in the Nimbus driver and make the
  "ex_create_tag" method a no-op, because Nimbus doesn't support creating
  tags.
  [Tomaz Muraus]

Storage
~~~~~~~

- Fix handling of the containers with a lot of objects. Now a LazyList
  object is returned when user calls list_container_objects() method
  and this object transparently handles pagination.
  [Danny Clark, Wiktor Kolodziej]

Changes with Apache Libcloud 0.5.0
----------------------------------

- Existing APIs directly on the libcloud.* module have been
  deprecated and will be removed in version 0.6.0.  Most methods
  were moved to the libcloud.compute.* module.

- Add new libcloud.loadbalancers API, with initial support for:
    - GoGrid Load Balancers
    - Rackspace Load Balancers

  [Roman Bogorodskiy]

- Add new libcloud.storage API, with initial support for:
   - Amazon S3
   - Rackspace CloudFiles

  [Tomaz Muraus]

- Add new libcloud.compute drivers for:
   - Bluebox [Christian Paredes]
   - Gandi.net [Aymeric Barantal]
   - Nimbus [David LaBissoniere]
   - OpenStack [Roman Bogorodskiy]
   - Opsource.net [Joe Miller]

- Added "pricing" module and improved pricing handling.
  [Tomaz Muraus]

- Updates to the GoGrid compute driver:
    - Use API version 1.0.
    - Remove sandbox flag.
    - Add ex_list_ips() to list IP addresses assigned to the account.
    - Implement ex_edit_image method which allows changing image attributes
      like name, description and make image public or private.

  [Roman Bogorodskiy]

- Updates to the Amazon EC2 compute driver:
   - When creating a Node, use the name argument to set a Tag with the
     value.  [Tomaz Muraus]
   - Add extension method for modifying node attributes and changing the
     node size. [Tomaz Muraus]
   - Add support for the new Amazon Region (Tokyo). [Tomaz Muraus]
   - Added ex_create_tags and ex_delete_tags. [Brandon Rhodes]
   - Include node Elastic IP addresses in the node public_ip attribute
     for the EC2 nodes. [Tomaz Muraus]
   - Use ipAddress and privateIpAddress attribute for the EC 2node public
     and private ip. [Tomaz Muraus]
   - Add ex_describe_addresses method to the EC2 driver. [Tomaz Muraus]

- Updates to the Rackspace CloudServers compute driver:
   - Add ex_rebuild() and ex_get_node_details() [Andrew Klochkov]
   - Expose URI of a Rackspace node to the node meta data. [Paul Querna]

- Minor fixes to get the library and tests working on Python 2.7 and PyPy.
  [Tomaz Muraus]

Changes with Apache Libcloud 0.4.2 (Released January 18, 2011)
--------------------------------------------------------------

- Fix EC2 create_node to become backward compatible for
  NodeLocation.
  [Tomaz Muraus]

- Update code for compatibility with CPython 2.5
  [Jerry Chen]

- Implement ex_edit_node method for GoGrid driver which allows
  changing node attributes like amount of RAM or description.
  [Roman Bogorodskiy]

- Add ex_set_password and ex_set_server_name to Rackspace driver.
  [Peter Herndon, Paul Querna]

- Add Hard and Soft reboot methods to Rackspace driver.
  [Peter Herndon]

- EC2 Driver availability zones, via ex_list_availability_zones;
  list_locations rewrite to include availability zones
  [Tomaz Muraus]

- EC2 Driver Idempotency capability in create_node; LIBCLOUD-69
  [David LaBissoniere]

- SSL Certificate Name Verification:
    - libcloud.security module
    - LibcloudHTTPSConnection, LibcloudHTTPConnection (alias)
    - Emits warning when not verifying, or CA certs not found

- Append ORD1 to available Rackspace location, but keep in the
  same node as DFW1, because it's not readable or writeable from
  the API.
  [Per suggestion of Grig Gheorghiu]

- ex_create_ip_group, ex_list_ip_groups, ex_delete_ip_group,
  ex_share_ip, ex_unshare_ip, ex_list_ip_addresses additions
  to Rackspace driver
  [Andrew Klochkov]

- New driver for CloudSigma.
  [Tomaz Muraus]

- New driver for Brightbox Cloud. (LIBCLOUD-63)
  [Tim Fletcher]

- Deployment capability to ElasticHosts
  [Tomaz Muraus]

- Allow deploy_node to use non-standard SSH username and port
  [Tomaz Muraus]

- Added Rackspace UK (London) support
  [Chmouel Boudjnah]

- GoGrid driver: add support for locations, i.e. listing
  of locations and creation of a node in specified
  location
  [Roman Bogorodskiy]

- GoGrid and Rackspace drivers: add ex_save_image() extra
  call to convert running node to an image
  [Roman Bogorodskiy]

- GoGrid driver: add support for creating 'sandbox' server
  and populate isSandbox flag in node's extra information.
  [Roman Bogorodskiy]

- Add ImportKeyPair and DescribeKeyPair to EC2. (LIBCLOUD-62)
  [Philip Schwartz]

- Update EC2 driver and test fixtures for new API.
  [Philip Schwartz]

Changes with Apache Libcloud 0.4.0 [Released October 6, 2010]
-------------------------------------------------------------

- Add create keypair functionality to EC2 Drivers. (LIBCLOUD-57)
  [Grig Gheorghiu]

- Improve handling of GoGrid accounts with limited access
  API keys.
  [Paul Querna]

- New Driver for ElasticHosts. (LIBCLOUD-45)
  [Tomaz Muraus]

- Use more consistent name for GoGrid driver and use http
  POST method for 'unsafe' operations
  [Russell Haering]

- Implement password handling and add deployment support
  for GoGrid nodes.
  [Roman Bogorodskiy]

- Fix behavior of GoGrid's create_node to wait for a Node ID.
  [Roman Bogorodskiy]

- Add ex_create_node_nowait to GoGrid driver if you don't need to
  wait for a Node ID when creating a node.
  [Roman Bogorodskiy]

- Removed libcloud.interfaces module.
  [Paul Querna]

- Removed dependency on zope.interfaces.
  [Paul Querna]

- RimuHosting moved API endpoint address.
  [Paul Querna]

- Fix regression and error in GoGrid driver for parsing node objects.
  [Roman Bogorodskiy]

- Added more test cases for GoGrid driver. (LIBCLOUD-34)
  [Roman Bogorodskiy, Jerry Chen]

- Fix parsing of Slicehost nodes with multiple Public IP addresses.
  [Paul Querna]

- Add exit_status to ScriptDeployment. (LIBCLOUD-36)
  [Paul Querna]

- Update prices for several drivers.
   [Brad Morgan, Paul Querna]

- Update Linode driver to reflect new plan sizes.
  [Jed Smith]

- Change default of 'location' in Linode create_node. (LIBCLOUD-41)
   [Jed Smith, Steve Steiner]

- Document the Linode driver.
  [Jed Smith]

- Request a private, LAN IP address at Linode creation.
  [Jed Smith]

Changes with Apache Libcloud 0.3.1 [Released May 11, 2010]
----------------------------------------------------------

- Updates to Apache License blocks to correctly reflect status as an
   Apache Project.

- Fix NOTICE file to use 2010 copyright date.

- Improve error messages for when running the test cases without
  first setting up a secrets.py

Changes with Apache Libcloud 0.3.0 [Tagged May 6, 2010, not released]
---------------------------------------------------------------------

- New Drivers for:
    - Dreamhost
    - Eucalyptus
    - Enomaly ECP
    - IBM Developer Cloud
    - OpenNebula
    - SoftLayer

- Added new deployment and bootstrap API.

- Improved Voxel driver.

- Added support for Amazon EC2 Asia Pacific (Singapore) Region.

- Improved test coverage for all drivers.

- Add support for multiple security groups in EC2.

- Fixed bug in Rackspace and RimuHosting when using multiple threads.

- Improved debugging and logging of HTTP requests.

- Improved documentation for all classes and methods.

Changes with Apache Libcloud 0.2.0 [Tagged February 2, 2010]
------------------------------------------------------------

- First public release.
