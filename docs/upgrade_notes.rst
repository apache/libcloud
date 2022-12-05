Upgrade Notes
=============

This page describes how to upgrade from a previous version to a new version
which contains backward incompatible or semi-incompatible changes and how to
preserve the old behavior when this is possible.

Libcloud 3.7.0
--------------

* Support for Python 3.6 which has been EOL for more than a year now has been
  removed.

  If you still want to use Libcloud with Python 3.6, you should use an older
  release which still supports Python 3.6.

Libcloud 3.6.0
--------------

* Compatibility layer has been introduced for paramiko SSH based deployment
  functionality.

  paramiko v2.9.0 introduced a change to prefer SHA-2 variants of RSA key
  verification algorithm (https://github.com/paramiko/paramiko/blob/2.9.0/sites/www/changelog.rst#changelog).
  With this version paramiko would fail to connect to older OpenSSH
  servers which don't support this algorithm (e.g. default setup on Ubuntu
  14.04) and throw authentication error.

  The code has been updated to be backward compatible. It first tries to
  connect to the server using default preferred algorithm values and in case
  that fails, it will fall back to the old approach with SHA-2 variants
  disabled.

  This functionality can be disabled by setting
  ``LIBCLOUD_PARAMIKO_SHA2_BACKWARD_COMPATIBILITY``environment variable to
  ``false``.

  For security reasons (to prevent possible downgrade attacks and similar) you
  are encouraged to do that in case you know you won't be connecting to any old

Libcloud 3.5.0
--------------

* Support for Python 3.5 which has been EOL for more than a year now has been
  removed.

  If you still want to use Libcloud with Python 3.5, you should use an older
  release which still supports Python 3.5.

* The OpenStack compute driver has moved the floating ip related functions
  from nova to neutron. This change affects all the floating ip related
  functions of the ``OpenStack_2_NodeDriver`` class. Two new classes have been
  added ``OpenStack_2_FloatingIpPool`` and ``OpenStack_2_FloatingIpAddress``.
  The main change applies to the FloatingIP class where ``node_id`` property
  cannot be directly obtained from FloatingIP information and it must be
  gotten from the related Port information with the ``get_node_id()`` method.

Libcloud 3.4.0
--------------

* Exception message changed in OpenStack drivers

  Attempting to use an identity API that requires authentication without an
  authentication token raises a ValueError.  The exception message used to be
  "Not to be authenticated to perform this request", but has now been changed
  to "Need to be authenticated to perform this request".

* Code which retries HTTP requests on 429 rate limit reached status code has
  been updated to respect ``timeout`` argument and stop retrying if timeout
  has been reached.

  Previously if API kept returning 429 status code back to the client, the code
  would try to retry for ever and in some scenarios when Retry-After value is
  not available in the response headers, also use 0 seconds for the sleep /
  retry delay which would cause busy waiting.

  If you want to preserve old behavior, you can do that by setting
  ``retryCls`` variable on the driver connection instance to
  ``RetryForeverOnRateLimitError`` as shown below.:

  .. sourcecode:: python

    from libcloud.utils.retry import RetryForeverOnRateLimitError

    driver.connection.retryCls = RetryForeverOnRateLimitError
    ...

Libcloud 3.3.0
--------------

* ``libcloud.pricing.get_size_pricing()`` now only caches pricing data in
  memory for the requested drivers.

  This way we avoid unnecessary overhead of caching data in memory for all the
  drivers.

  If you want to revert to the old behavior (cache pricing data for all the
  drivers in memory), you can do that by passing ``cache_all=True`` argument
  to that function as shown below:

  .. sourcecode:: python

    from libcloud.pricing import get_size_pricing

    price = get_size_price("compute", "bluebox", cache_all=True)

  Or by setting ``libcloud.pricing.CACHE_ALL_PRICING_DATA`` module level
  variable to ``True``:

  .. sourcecode:: python

    import libcloud.pricing

    libcloud.pricing.CACHE_ALL_PRICING_DATA = True

    # Your code here
    # ...

  Passing ``cache_all=True`` might come handy in situations where you know the
  application will work with a lot of different drivers - this way you can
  avoid multiple disk reads when requesting pricing data for different drivers.

* Packet driver has been renamed to Equinix Metal. Provider name
  has changed from ``Provider.PACKET`` to ``Provider.EQUINIXMETAL``,
  while everything else works as before.

  Before:

    .. sourcecode:: python

      from libcloud.compute.types import Provider
      from libcloud.compute.providers import get_driver

      cls = get_driver(Provider.PACKET)
      driver = cls('api_key')

  After:

    .. sourcecode:: python

      from libcloud.compute.types import Provider
      from libcloud.compute.providers import get_driver

      cls = get_driver(Provider.EQUINIXMETAL)
      driver = cls('api_key')

* New ``libcloud.common.base.ALLOW_PATH_DOUBLE_SLASHES`` module level variable
  has been added which defaults to ``False`` for backward compatibility reasons.

  When set to ``True``, Libcloud code won't perform any URL path sanitization
  and will allow URL paths with double slashes (e.g.
  ``/my-bucket//foo/1.txt``).

  This may come handy to the users who have S3 paths which contains double
  slashes or similar and are upgrading from Libcloud ``v2.3.0`` or older where
  no path sanitization was performed.

  Example S3 bucket layout with this option disabled (default) and enabled.

  Object with the following name: ``/my-bucket/sub-directory/file.txt``

    .. code-block:: bash

      # Disabled

      root
      +-- my-bucket/
        +-- sub-directory/
          +-- file.txt

      # Enabled

      root
      +-- /
        +-- my-bucket/
          +-- sub-directory/
            +-- file.txt

  Object with the following name: ``/my-bucket//directory1/file.txt``

    .. code-block:: bash

      # Disabled

      root
      +-- my-bucket/
        +-- directory1/
          +-- file.txt

      # Enabled

      root
      +-- /
        +-- my-bucket/
          +-- /
            +-- directory1/
              +-- file.txt

  As you can see from the examples above, directory layout is not the same
  with this option enabled and disabled so you should be careful when you
  use it.

  This change affects all the drivers which are used when that module level
  variable is set.

Libcloud 3.2.0
--------------

* To accommodate for more complex pricing schemes, pricing data format for AWS
  EC2 inside ``libcloud/data/pricing.json`` file has changes.

  Previously, it contained a mapping of ``<driver name>_<driver rigion>`` ->
  ``<instance size>`` -> ``<price>`` and now the pricing is in the following
  format: ``ec_{linux,windows}`` -> ``<instance size>`` -> ``<region>`` ->
  ``<price>``.

  This format gives us more flexibility for more complex pricing schemes and
  also allows us to store prices for non-Linux instances.

Libcloud 3.0.0
--------------

* This release drops support for Python versions older than 3.5.0.

  If you still need to use Libcloud with Python 2.7 or Python 3.4 you can do
  that by using the latest release which still supported those Python versions
  (Libcloud v2.8.0).

* This release removes VMware vSphere driver which relied on old and
  unmaintained ``pysphere`` library which doesn't support Python 3.

* This release removes support for PageBlob objects from the Azure Blobs
  storage driver. The ``ex_blob_type`` and ``ex_page_blob_size`` arguments
  have been removed from the ``upload_object`` and ``upload_object_via_stream``
  methods.

* The ``ex_prefix`` keyword argument in the ``iterate_container_objects``
  and ``list_container_objects`` methods in all storage drivers has been
  renamed to ``prefix`` to indicate the promotion of the argument to the
  standard storage driver API.

Libcloud 2.8.0
--------------

* ``deploy_node()`` method in the GCE driver has been updated so it complies
  with the base compute API.

  This means that the method now takes the same argument as the base
  ``deploy_node()`` method (``deployment``, ``ssh_username``, ``ssh_port``,
  etc.) plus all the keyword arguments which are supported by the
  ``create_node()`` method.

* ``group_name`` keyword argument in the ``create_node()`` method in the
  Abiquo driver has been renamed to ``ex_group_name`` to comply with the
  convention for naming non-standard arguments (arguments which are not
  part of the standard compute API).

Libcloud 2.7.0
--------------

* AWS S3 driver has moved from "driver class per region" model to "single driver
  class with ``region`` constructor argument" model. This means this driver now
  follows the same approach as other multi region drivers.

  Before:

  .. sourcecode:: python

      from libcloud.storage.types import Provider
      from libcloud.storage.providers import get_driver

      S3_EU_CENTRAL = get_driver(Provider.S3_EU_CENTRAL)
      S3_EU_WEST_1 = get_driver(Provider.S3_EU_WEST)

      driver_eu_central = S3_EU_CENTRAL('api key', 'api secret')
      driver_eu_west_1 = S3_EU_WEST_1('api key', 'api secret')

  After:

  .. sourcecode:: python

      from libcloud.storage.types import Provider
      from libcloud.storage.providers import get_driver

      S3 = get_driver(Provider.S3)

      driver_eu_central = S3('api key', 'api secret', region='eu-central-1')
      driver_eu_west_1 = S3('api key', 'api secret', region='eu-west-1')

  For now, old approach will still work, but it will be deprecated and fully
  removed in a future release. Deprecation and removal will be announced well in
  advance.

- New ``start_node`` and ``stop_node`` methods have been added to the base
  Libcloud compute API NodeDriver class.

  A lot of the existing compute drivers already implemented that functionality
  via extension methods (``ex_start_node``, ``ex_stop_node``) so it was decided
  to promote those methods to be part of the standard Libcloud compute API and
  update all the affected drivers.

  For backward compatibility reasons, existing ``ex_start`` and ``ex_stop_node``
  methods will still work until a next major release.

  If you are relying on code which uses ``ex_start`` and ``ex_stop_node``
  methods, you are encouraged to update it to utilize new ``start_node`` and
  ``stop_node`` methods since those ``ex_`` methods are now deprecated and will
  be removed in a future major release.

Libcloud 1.0.0
--------------

* Per-region provider constants and related driver classes which have been
  deprecated in Libcloud 0.14.0 have now been fully removed.

  Those provider drivers have moved to the single provider constant +
  ``region`` constructor argument in Libcloud 0.14.0.

Libcloud 0.20.0
---------------

* New optional ``ttl`` argument has been added to ``libcloud.dns.base.Record``
  class constructor before the existing ``extra`` argument.

  If you have previously manually instantiated this class and didn't use
  keyword arguments, you need to update your code to correctly pass arguments
  to the constructor (you are encouraged to use keyword arguments to avoid such
  issues in the future).

* All NodeState, StorageVolumeState, VolumeSnapshotState and Provider attributes
  are now strings instead of integers.

  If you are using the ``tostring`` and ``fromstring`` methods of NodeState,
  you are fine. If you are using NodeState.RUNNING and the like, you are also fine.

  However, if you have previously depended on these being integers,
  you need to update your code to depend on strings. You should consider starting
  using the ``tostring`` and ``fromstring`` methods as the output of these functions
  will not change in future versions, while the implementation might.

Libcloud 0.19.0
---------------

* The base signature of NodeDriver.create_volume has changed. The snapshot
  argument is now expected to be a VolumeSnapshot instead of a string.
  The older signature was never correct for built-in drivers, but custom
  drivers may break. (GCE accepted strings, names or None and still does.
  Other drivers did not implement creating volumes from snapshots at all
  until now.)

* VolumeSnapshots now have a `created` attribute that is a `datetime`
  field showing the creation datetime of the snapshot. The field in
  VolumeSnapshot.extra containing the original string is maintained, so
  this is a backwards-compatible change.

* The OpenStack compute driver methods ex_create_snapshot and
  ex_delete_snapshot are now deprecated by the standard methods
  create_volume_snapshot and destroy_volume_snapshot. You should update your
  code.

* The compute base driver now considers the name argument to
  create_volume_snapshot to be optional. All official implementations of this
  methods already considered it optional. You should update any custom
  drivers if they rely on the name being mandatory.

Libcloud 0.16.0
---------------

Changes in the OpenStack authentication and service catalog classes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. note::
    If you are only working with the driver classes and have never dorectly
    touched the classes mentioned below, then you aren't affected and those
    changes are fully backward compatible.

To make OpenStack authentication and identity related classes more extensible,
easier to main and easier to use, those classes have been refactored. All of
the changes are described below.

* New ``libcloud.common.openstack_identity`` module has been added. This module
  contains code for working with OpenStack Identity (Keystone) service.
* ``OpenStackAuthConnection`` class has been removed and replaced with one
  connection class per Keystone API version
  (``OpenStackIdentity_1_0_Connection``, ``OpenStackIdentity_2_0_Connection``,
  ``OpenStackIdentity_3_0_Connection``).
* New ``get_auth_class`` method has been added to ``OpenStackBaseConnection``
  class. This method allows you to retrieve an instance of the authentication
  class which is used with the current connection.
* ``OpenStackServiceCatalog`` class has been refactored to store parsed catalog
  entries in a structured format (``OpenStackServiceCatalogEntry`` and
  ``OpenStackServiceCatalogEntryEndpoint`` class). Previously entries were
  stored in an unstructured form in a dictionary. All the catalog entries can
  be retrieved by using ``OpenStackServiceCatalog.get_entris`` method.
* ``ex_force_auth_version`` argument in ``OpenStackServiceCatalog`` constructor
  method has been renamed to ``auth_version``
* ``get_regions``, ``get_service_types`` and ``get_service_names`` methods on
  the ``OpenStackServiceCatalog`` class have been modified to always return the
  result in the same order (result values are sorted beforehand).

For more information and examples, please refer to the
`Libcloud now supports OpenStack Identity (Keystone) API v3`_ blog post.

Libcloud 0.14.1
---------------

Fix record name inconsistencies in the Rackspace DNS driver
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``Record.name`` attribute is now correctly set to ``None`` for records which
refer to the bare domain name. Previously, ``Record.name`` attribute for such
records was set to the domain name.

For example, lets have a look at a record which points to the domain
``example.com``.

New ``Record.name`` attribute value for such record: ``None``

Old ``Record.name`` attribute value for such record: ``example.com``

This was done to make the Rackspace driver consistent with the other ones.

Libcloud 0.14.0
---------------

To make drivers with multiple regions easier to use, one of the big changes in
this version is move away from the old "one class per region" model to a new
single class plus ``region`` argument model.

More information on how this affects existing drivers and your code can be
found below.

Default Content-Type is now provided if none is supplied and none can be guessed
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In older versions, Libcloud would throw an exception when a content type is not
supplied and none can't be automatically detected when uploading an object.

This has changed with the 0.14.0 release. Now if no content type is specified
and none can't be detected, a default content type of
``application/octet-stream`` is used.

If you want to preserve the old behavior, you can set ``strict_mode`` attribute
on the driver object to ``True``.

.. sourcecode:: python

    from libcloud.storage.types import Provider
    from libcloud.stoage.providers import get_driver

    cls = get_driver(Provider.CLOUDFILES)
    driver = cls('username', 'api key')

    driver.strict_mode = True

If you are not using strict mode and you are uploading a binary object, we
still encourage you to practice Python's "explicit is better than implicit"
mantra and explicitly specify Content-Type of ``application/octet-stream``.

SSH Key pair management functionality has been promoted to the base API
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

SSH key pair management functionality has been promoted to be a part of the
base compute API.

As such, the following new classes and methods have been added:

* `libcloud.compute.base.KeyPair`
* `libcloud.compute.base.NodeDriver.list_key_pairs`
* `libcloud.compute.base.NodeDriver.create_key_pair`
* `libcloud.compute.base.NodeDriver.import_key_pair_from_string`
* `libcloud.compute.base.NodeDriver.import_key_pair_from_file`
* `libcloud.compute.base.NodeDriver.delete_key_pair`

Previously, this functionality was available in some of the provider drivers
(CloudStack, EC2, OpenStack) via the following extension methods:

* `ex_list_keypairs`
* `ex_create_keypair`
* `ex_import_keypair_from_string`
* `ex_import_keypair`
* `ex_delete_keypair`

Existing extension methods will continue to work until the next major release,
but you are strongly encouraged to start using new methods which are now part
of the base compute API and are guaranteed to work the same across different
providers.

New default kernel versions used when creating Linode servers
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Kernel versions which are used by default when creating Linode servers have been
updated.

Old default kernel versions:

* x86 (no paravirt-ops) - ``2.6.18.8-x86_64-linode1`` (#60)
* x86 (paravirt-ops) - ``2.6.18.8-x86_64-linode1`` (#110)
* x86_64 (no paravirt-ops) - ``2.6.39.1-linode34`` (#107)
* x86 (paravirt-ops)64 - ``2.6.18.8-x86_64-linode1`` (#111)

New default kernel versions:

* x86 - ``3.9.3-x86-linode52`` (#137)
* x86_64 - ``3.9.3-x86_64-linode33`` (#138)

Those new kernel versions now come with paravirt-ops by default.

If you want to preserve the old behavior, you can pass ``ex_kernel`` argument to
the ``create_node`` method.

Keep in mind that using old kernels is strongly discouraged since they contain
known security holes.

For example:

.. sourcecode:: python

    from libcloud.compute.types import Provider
    from libcloud.compute.providers import get_driver

    cls = get_driver(Provider.LINODE)

    driver = cls('username', 'api_key')
    driver.create_node(..., ex_kernel=110)

Addition of new "STOPPED" node state
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This version includes a new state called
:class:`libcloud.compute.types.NodeState.STOPPED`. This state represents a node
which has been stopped and can be started later on (unlike TERMINATED state
which represents a node which has been terminated and can't be started later
on).

As such, ``EC2`` and ``HostVirual`` drivers have also been updated to recognize
this new state.

Before addition of this state, nodes in this state were mapped to
``NodeState.UNKNOWN``.

Amazon EC2 compute driver changes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Amazon EC2 compute driver has moved to single class plus ``region`` argument
model. As such, the following provider constants have been deprecated:

* ``EC2_US_EAST``
* ``EC2_US_WEST_OREGON``
* ``EC2_EU``
* ``EC2_EU_WEST``
* ``EC2_AP_SOUTHEAST``
* ``EC2_AP_SOUTHEAST2``
* ``EC2_AP_NORTHEAST``
* ``EC2_SA_EAST``

And replaced with a single constant:

* ``EC2`` - Supported values for the ``region`` argument are: ``us-east-1``,
  ``us-west-1``, ``us-west-2``, ``eu-west-1``, ``ap-southeast-1``,
  ``ap-northeast-1``, ``sa-east-1``, ``ap-southeast-2``. Default value is
  ``us-east-1``.

List which shows how old classes map to a new ``region`` argument value:

* ``EC2_US_EAST`` -> ``us-east-1``
* ``EC2_US_WEST`` -> ``us-west-1``
* ``EC2_US_WEST_OREGON`` -> ``us-west-2``
* ``EC2_EU`` -> ``eu-west-1``
* ``EC2_EU_WEST`` -> ``eu-west-1``
* ``EC2_AP_SOUTHEAST`` -> ``ap-southeast-1``
* ``EC2_AP_SOUTHEAST2`` -> ``ap-southeast-2``
* ``EC2_AP_NORTHEAST`` -> ``ap-northeast-1``
* ``EC2_SA_EAST`` -> ``sa-east-1``

Old code:

.. sourcecode:: python

    from libcloud.compute.types import Provider
    from libcloud.compute.providers import get_driver

    cls1 = get_driver(Provider.EC2)
    cls2 = get_driver(Provider.EC2_EU_WEST)

    driver1 = cls('username', 'api_key')
    driver2 = cls('username', 'api_key')

New code:

.. sourcecode:: python

    from libcloud.compute.types import Provider
    from libcloud.compute.providers import get_driver

    cls = get_driver(Provider.EC2)

    driver1 = cls('username', 'api_key', region='us-east-1')
    driver2 = cls('username', 'api_key', region='eu-west-1')

Rackspace compute driver changes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Rackspace compute driver has moved to single class plus ``region`` argument
model. As such, the following provider constants have been **removed**:

* ``RACKSPACE``
* ``RACKSPACE_UK``
* ``RACKSPACE_AU``
* ``RACKSPACE_NOVA_ORD``
* ``RACKSPACE_NOVA_DFW``
* ``RACKSPACE_NOVA_LON``
* ``RACKSPACE_NOVA_BETA``

And replaced with two new constants:

* ``RACKSPACE_FIRST_GEN`` - Supported values for ``region`` argument are: ``us``, ``uk``.
  Default value is ``us``.
* ``RACKSPACE`` - Supported values for the ``region`` argument are:
  ``dfw``, ``ord``, ``iad``, ``lon``, ``syd``, ``hkg``.
  Default value is ``dfw``.

Besides that, ``RACKSPACE`` provider constant now defaults to next-generation
OpenStack based servers. Previously it defaulted to first generation cloud
servers.

If you want to preserve old behavior and use first-gen drivers you need to use
``RACKSPACE_FIRST_GEN`` provider constant.

First generation cloud servers now also use auth 2.0 by default. Previously they
used auth 1.0.

Because of the nature of this first-gen to next-gen change, old constants have
been fully removed and unlike region changes in other driver, this change is not
backward compatible.

List which shows how old, first-gen classes map to a new ``region`` argument
value:

* ``RACKSPACE`` -> ``us``
* ``RACKSPACE_UK`` -> ``uk``

List which shows how old, next-gen classes map to a new ``region`` argument
value:

* ``RACKSPACE_NOVA_ORD`` -> ``ord``
* ``RACKSPACE_NOVA_DFW`` -> ``dfw``
* ``RACKSPACE_NOVA_LON`` -> ``lon``
* ``RACKSPACE_AU`` -> ``syd``

More examples which show how to update your code to work with a new version can
be found below.

Old code (connecting to a first-gen provider):

.. sourcecode:: python

    from libcloud.compute.types import Provider
    from libcloud.compute.providers import get_driver

    cls1 = get_driver(Provider.RACKSPACE) # US regon
    cls2 = get_driver(Provider.RACKSPACE_UK) # UK regon

    driver1 = cls('username', 'api_key')
    driver2 = cls('username', 'api_key')

New code (connecting to a first-gen provider):

.. sourcecode:: python

    from libcloud.compute.types import Provider
    from libcloud.compute.providers import get_driver

    cls = get_driver(Provider.RACKSPACE_FIRST_GEN)

    driver1 = cls('username', 'api_key', region='us')
    driver2 = cls('username', 'api_key', region='uk')

Old code (connecting to a next-gen provider)

.. sourcecode:: python

    from libcloud.compute.types import Provider
    from libcloud.compute.providers import get_driver

    cls1 = get_driver(Provider.RACKSPACE_NOVA_ORD)
    cls2 = get_driver(Provider.RACKSPACE_NOVA_DFW)
    cls3 = get_driver(Provider.RACKSPACE_NOVA_LON)

    driver1 = cls('username', 'api_key')
    driver2 = cls('username', 'api_key')
    driver3 = cls('username', 'api_key')

New code (connecting to a next-gen provider)

.. sourcecode:: python

    from libcloud.compute.types import Provider
    from libcloud.compute.providers import get_driver

    cls = get_driver(Provider.RACKSPACE)

    driver1 = cls('username', 'api_key', region='ord')
    driver2 = cls('username', 'api_key', region='dfw')
    driver3 = cls('username', 'api_key', region='lon')

CloudStack compute driver changes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

CloudStack driver received a lot of changes and additions which will make it
more pleasant to use. Backward incompatible changes are listed below:

* ``CloudStackForwardingRule`` class has been renamed to
  ``CloudStackIPForwardingRule``

* ``create_node`` method arguments are now more consistent with other drivers.
  Security groups are now passed as ``ex_security_groups``, SSH keypairs
  are now passed as ``ex_keyname`` and userdata is now passed as
  ``ex_userdata``.

* For advanced networking zones, multiple networks can now be passed to the
  ``create_node`` method instead of a single network id. These networks need
  to be instances of the ``CloudStackNetwork`` class.

* The ``extra_args`` argument of the ``create_node`` method has been removed.
  The only arguments accepted are now the defaults ``name``, ``size``,
  ``image``, ``location`` plus ``ex_keyname``, ``ex_userdata``,
  ``ex_security_groups`` and ``networks``.

Joyent compute driver changes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Joyent driver has been aligned with other drivers and now the constructor takes
``region`` instead of ``location`` argument.

For backward compatibility reasons, old argument will continue to work until the
next major release.

Old code:

.. sourcecode:: python

    from libcloud.compute.types import Provider
    from libcloud.compute.providers import get_driver

    cls = get_driver(Provider.JOYENT)

    driver = cls('username', 'api_key', location='us-east-1')

Old code:

.. sourcecode:: python

    from libcloud.compute.types import Provider
    from libcloud.compute.providers import get_driver

    cls = get_driver(Provider.JOYENT)

    driver = cls('username', 'api_key', region='us-east-1')

ElasticHosts compute driver changes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

ElasticHosts compute driver has moved to single class plus ``region`` argument
model. As such, the following provider constants have been deprecated:

* ``ELASTICHOSTS_UK1``
* ``ELASTICHOSTS_UK1``
* ``ELASTICHOSTS_US1``
* ``ELASTICHOSTS_US2``
* ``ELASTICHOSTS_US3``
* ``ELASTICHOSTS_CA1``
* ``ELASTICHOSTS_AU1``
* ``ELASTICHOSTS_CN1``

And replaced with a single constant:

* ``ELASTICHOSTS`` - Supported values for the ``region`` argument are:
  ``lon-p``, ``lon-b``, ``sat-p``, ``lax-p``, ``sjc-c``, ``tor-p``, ``syd-y``,
  ``cn-1`` Default value is ``sat-p``.

List which shows how old classes map to a new ``region`` argument value:

* ``ELASTICHOSTS_UK1`` -> ``lon-p``
* ``ELASTICHOSTS_UK1`` -> ``lon-b``
* ``ELASTICHOSTS_US1`` -> ``sat-p``
* ``ELASTICHOSTS_US2`` -> ``lax-p``
* ``ELASTICHOSTS_US3`` -> ``sjc-c``
* ``ELASTICHOSTS_CA1`` -> ``tor-p``
* ``ELASTICHOSTS_AU1`` -> ``syd-y``
* ``ELASTICHOSTS_CN1`` -> ``cn-1``

Because of this change main driver class has also been renamed from
:class:`libcloud.compute.drivers.elastichosts.ElasticHostsBaseNodeDriver`
to :class:`libcloud.compute.drivers.elastichosts.ElasticHostsNodeDriver`.

Only users who directly instantiate a driver and don't use recommended
``get_driver`` method are affected by this change.

Old code:

.. sourcecode:: python

    from libcloud.compute.types import Provider
    from libcloud.compute.providers import get_driver

    cls1 = get_driver(Provider.ELASTICHOSTS_UK1)
    cls2 = get_driver(Provider.ELASTICHOSTS_US2)

    driver1 = cls('username', 'api_key')
    driver2 = cls('username', 'api_key')

New code:

.. sourcecode:: python

    from libcloud.compute.types import Provider
    from libcloud.compute.providers import get_driver

    cls = get_driver(Provider.ELASTICHOSTS)

    driver1 = cls('username', 'api_key', region='lon-p')
    driver2 = cls('username', 'api_key', region='lax-p')

Unification of extension arguments for security group handling in the EC2 driver
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To unify extension arguments for handling security groups between drivers,
``ex_securitygroup`` argument in the EC2 ``create_node`` method has been
renamed to ``ex_security_groups``.

For backward compatibility reasons, old argument will continue to work for
until a next major release.

CloudFiles Storage driver changes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``CLOUDFILES_US`` and ``CLOUDFILES_UK`` provider constants have been deprecated
and a new ``CLOUDFILES`` constant has been added.

User can now use this single constant and specify which region to use by
passing ``region`` argument to the driver constructor.

Old code:

.. sourcecode:: python

    from libcloud.storage.types import Provider
    from libcloud.storage.providers import get_driver

    cls1 = get_driver(Provider.CLOUDFILES_US)
    cls2 = get_driver(Provider.CLOUDFILES_UK)

    driver1 = cls1('username', 'api_key')
    driver2 = cls1('username', 'api_key')

New code:

.. sourcecode:: python

    from libcloud.compute.types import Provider
    from libcloud.compute.providers import get_driver

    cls = get_driver(Provider.CLOUDFILES)

    driver1 = cls1('username', 'api_key', region='dfw')
    driver2 = cls1('username', 'api_key', region='lon')

Rackspace DNS driver changes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Rackspace DNS driver has moved to one class plus ``region`` argument model. As
such, the following provider constants have been deprecated:

* ``RACKSPACE_US``
* ``RACKSPACE_UK``

And replaced with a single constant:

* ``RACKSPACE`` - Supported values for ``region`` arguments are ``us``, ``uk``.
  Default value is ``us``.

Old code:

.. sourcecode:: python

    from libcloud.dns.types import Provider
    from libcloud.dns.providers import get_driver

    cls1 = get_driver(Provider.RACKSPACE_US)
    cls2 = get_driver(Provider.RACKSPACE_UK)

    driver1 = cls1('username', 'api_key')
    driver2 = cls1('username', 'api_key')

New code:

.. sourcecode:: python

    from libcloud.dns.types import Provider
    from libcloud.dns.providers import get_driver

    cls = get_driver(Provider.RACKSPACE)

    driver1 = cls1('username', 'api_key', region='us')
    driver2 = cls1('username', 'api_key', region='uk')

Rackspace load balancer driver changes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Rackspace loadbalancer driver has moved to one class plus ``region`` argument
model. As such, the following provider constants have been deprecated:

* ``RACKSPACE_US``
* ``RACKSPACE_UK``

And replaced with a single constant:

* ``RACKSPACE`` - Supported values for ``region`` arguments are ``dfw``,
  ``ord``, ``iad``, ``lon``, ``syd``, ``hkg``. Default value is ``dfw``.

Old code:

.. sourcecode:: python

    from libcloud.loadbalancer.types import Provider
    from libcloud.loadbalancer.providers import get_driver

    cls1 = get_driver(Provider.RACKSPACE_US)
    cls2 = get_driver(Provider.RACKSPACE_UK)

    driver1 = cls1('username', 'api_key')
    driver2 = cls1('username', 'api_key')

New code:

.. sourcecode:: python

    from libcloud.loadbalancer.types import Provider
    from libcloud.loadbalancer.providers import get_driver

    cls = get_driver(Provider.RACKSPACE)

    driver1 = cls1('username', 'api_key', region='ord')
    driver2 = cls1('username', 'api_key', region='lon')

ScriptDeployment and ScriptFileDeployment constructor now takes args argument
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:class:`libcloud.compute.deployment.ScriptDeployment` and
:class:`libcloud.compute.deployment.ScriptFileDeployment` class constructor now
take ``args`` as a second argument.

Previously this argument was not present and the second argument was ``name``.

If you have a code which instantiate those classes directly and passes two or
more arguments (not keyword arguments) to the constructor you need to update
it to preserve the old behavior.

Old code:

.. sourcecode:: python

    sd = ScriptDeployment('#!/usr/bin/env bash echo "ponies!"', 'ponies.sh')

New code:

.. sourcecode:: python

    sd = ScriptDeployment('#!/usr/bin/env bash echo "ponies!"', None,
                          'ponies.sh')

Even better (using keyword arguments):

.. sourcecode:: python

    sd = ScriptDeployment(script='#!/usr/bin/env bash echo "ponies!"',
                          name='ponies.sh')

Pricing data changes
~~~~~~~~~~~~~~~~~~~~

By default this version of Libcloud tries to read pricing data from the
``~/.libcloud/pricing.json`` file. If this file doesn't exist, Libcloud falls
back to the old behavior and the pricing data is read from the pricing file
which is shipped with each release.

For more information, please see :ref:`using-custom-pricing-file` page.

RecordType ENUM value is now a string
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:class:`libcloud.dns.types.RecordType` ENUM value used be an integer, but from
this version on, it's now a string. This was done to make it simpler and remove
unnecessary indirection.

If you use `RecordType` class in your code as recommended, no changes are
required, but if you use integer values directly, you need to update your
code to use `RecordType` class otherwise it will break.

OK:

.. sourcecode:: python

    # ...
    record = driver.create_record(name=www, zone=zone, type=RecordType.A,
                                  data='127.0.0.1')

Not OK:

.. sourcecode:: python

    # ...
    record = driver.create_record(name=www, zone=zone, type=0,
                                  data='127.0.0.1')

Cache busting functionality is now only enabled in Rackspace first-gen driver
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Cache busting functionality has been disabled in the Rackspace next-gen driver
and all of the OpenStack drivers. It's now only enabled in the Rackspace
first-gen driver.

Cache busting functionality works by appending a random query parameter to
every GET HTTP request. It was originally added to the Rackspace first-gen
driver a long time ago to avoid excessive HTTP caching on the provider side.
This excessive caching some times caused list_nodes and other calls to return
stale data.

This approach should not be needed with Rackspace next-gen and OpenStack drivers
so it has been disabled.

No action is required on the user's side.

libcloud.security.VERIFY_SSL_CERT_STRICT variable has been removed
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``libcloud.security.VERIFY_SSL_CERT_STRICT`` variable has been introduced in
version 0.4.2 when we initially added support for SSL certificate verification.
This variable was added to ease the migration from older versions of Libcloud
which didn't verify SSL certificates.

In version 0.6.0, this variable has been set to ``True`` by default and
deprecated.

In this release, this variable has been fully removed. For more information
on how SSL certificate validation works in Libcloud, see the :doc:`SSL
Certificate Validation </other/ssl-certificate-validation>` page.

get_container method changes in the S3 driver
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Previously, the ``get_container`` method in the S3 driver used a very
inefficient approach of using ``list_containers`` + late filterting.

The code was changed to use a more efficient approach which means using
a single HTTP ``HEAD`` request.

The only downside of this approach is that it doesn't return container
creation date.

If you need the container creation date, you should use ``list_containers``
method and do the later filtering yourself.

Libcloud 0.8
------------

* ``restart_node`` method has been removed from the OpenNebula compute driver,
  because OpenNebula OCCI implementation does not support a proper restart
  method.

* ``ex_save_image`` method in the OpenStack driver now returns a ``NodeImage``
  instance.

For a full list of changes, please see the `CHANGES file
<https://git.apache.org/repos/asf?p=libcloud.git;a=blob;f=CHANGES;h=fd1f9cd8917bf9d9c5f4d5344872dbccba894444;hb=b26812db71e6c36be3cc5f7fcb87f82b267bfddd>`__.

Libcloud 0.7
------------

* For consistency, ``public_ip`` and ``private_ip`` attribute on the ``Node``
  object have been renamed to ``public_ips`` and ``private_ips`` respectively.

In 0.7 you can still access those attributes using the old way, but this option
will be removed in the next major release.

**Note: If you have places in your code where you directly instantiate a
``Node`` class, you need to update it.**

Old code:

.. sourcecode:: python

    node = Node(id='1', name='test node', state=NodeState.PENDING,
                private_ip=['10.0.0.1'], public_ip=['88.77.66.77'],
                driver=driver)

Updated code:

.. sourcecode:: python

    node = Node(id='1', name='test node', state=NodeState.PENDING,
                private_ips=['10.0.0.1'], public_ips=['88.77.66.77'],
                driver=driver)

* Old deprecated paths have been removed. If you still haven't updated your
  code you need to do it now, otherwise it won't work with 0.7 and future
  releases.

Below is a list of old paths and their new locations:

* ``libcloud.base`` -> ``libcloud.compute.base``
* ``libcloud.deployment`` -> ``libcloud.compute.deployment``
* ``libcloud.drivers.*`` -> ``libcloud.compute.drivers.*``
* ``libcloud.ssh`` -> ``libcloud.compute.ssh``
* ``libcloud.types`` -> ``libcloud.compute.types``
* ``libcloud.providers`` -> ``libcloud.compute.providers``

In the ``contrib/`` directory you can also find a simple bash script which can
perform a search and replace for you - `migrate_paths.py <https://svn.apache.org/repos/asf/libcloud/trunk/contrib/migrate_paths.sh>`_.

For a full list of changes, please see the `CHANGES file
<https://git.apache.org/repos/asf?p=libcloud.git;a=blob;f=CHANGES;h=276948338c2581de1178e51f7f7cdbd4e7ba9286;hb=2ad8f3fa1f258d6c53d7b058cdc6cd9ab1fd579b>`__.

Libcloud 0.6
------------

* SSL certificate verification is now enabled by default and an exception is
  thrown if CA certificate files cannot be found.

To revert to the old behavior, set ``libcloud.security.VERIFY_SSL_CERT_STRICT``
variable to ``False``:

.. sourcecode:: python

    libcloud.security.VERIFY_SSL_CERT_STRICT = False

**Note: You are strongly discouraged from disabling SSL certificate validation.
If you disable it and no CA certificates files are found on the system you are
vulnerable to a man-in-the-middle attack**

More information on how to acquire and install CA certificate files on
different operating systems can be found on :doc:`SSL Certificate Validation
page </other/ssl-certificate-validation>`

* OpenStack driver now defaults to using OpenStack 1.1 API.

To preserve the old behavior and use OpenStack 1.0 API, pass
``api_version='1.0'`` keyword argument to the driver constructor.

For example:

.. sourcecode:: python

    Cls = get_provider(Provider.OPENSTACK)
    driver = Cls('user_name', 'api_key', False, 'host', 8774, api_version='1.0')

* OpenNebula driver now defaults to using OpenNebula 3.0 API

To preserve the old behavior and use OpenNebula 1.4 API, pass
``api_version='1.4'`` keyword argument to the driver constructor.

For example:

.. sourcecode:: python

    Cls = get_provider(Provider.OPENNEBULA)
    driver = Cls('key', 'secret', api_version='1.4')

For a full list of changes, please see the `CHANGES file <https://svn.apache.org/viewvc/libcloud/trunk/CHANGES?revision=1198753&view=markup>`__.

.. _`Libcloud now supports OpenStack Identity (Keystone) API v3`: http://www.tomaz.me/2014/08/23/libcloud-now-supports-openstack-identity-keystone-api-v3.html
