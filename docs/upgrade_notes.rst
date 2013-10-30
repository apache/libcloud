Upgrade Notes
=============

This page describes how to upgrade from a previous version to a new version
which contains backward incompatible or semi-incompatible changes and how to
preserve the old behavior when this is possible.

Libcloud 0.14.0
---------------

To make drivers with multiple regions easier to use, one of the big changes in
this version is move away from the old "one class per region" model to a new
single class plus ``region`` argument model.

More information on how this affects existing drivers and your code can be
found bellow.

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

* ``RACKSPACE`` - Supported values for ``region`` argument are: ``us``, ``uk``.
  Default value is ``us``.
* ``RACKSPACE_FIRST_GEN`` - Supported values for the ``region`` argument are:
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
be found bellow.

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
more pleasant to use. Backward incompatible changes are listed bellow:

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

Libcloud 0.8
------------

* ``restart_node`` method has been removed from the OpenNebula compute driver,
  because OpenNebula OCCI implementation does not support a proper restart
  method.

* ``ex_save_image`` method in the OpenStack driver now returns a ``NodeImage``
  instance.

For a full list of changes, please see the `CHANGES file <https://git-wip-us.apache.org/repos/asf?p=libcloud.git;a=blob;f=CHANGES;h=fd1f9cd8917bf9d9c5f4d5344872dbccba894444;hb=b26812db71e6c36be3cc5f7fcb87f82b267bfddd>`_.

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
code you need to do it now, otherwise it won't work with 0.7 and future releases.

Bellow is a list of old paths and their new locations:

* ``libcloud.base`` -> ``libcloud.compute.base``
* ``libcloud.deployment`` -> ``libcloud.compute.deployment``
* ``libcloud.drivers.*`` -> ``libcloud.compute.drivers.*``
* ``libcloud.ssh`` -> ``libcloud.compute.ssh``
* ``libcloud.types`` -> ``libcloud.compute.types``
* ``libcloud.providers`` -> ``libcloud.compute.providers``

In the ``contrib/`` directory you can also find a simple bash script which can
perform a search and replace for you - `migrate_paths.py <https://svn.apache.org/repos/asf/libcloud/trunk/contrib/migrate_paths.sh>`_.

For a full list of changes, please see the `CHANGES file <https://git-wip-us.apache.org/repos/asf?p=libcloud.git;a=blob;f=CHANGES;h=276948338c2581de1178e51f7f7cdbd4e7ba9286;hb=2ad8f3fa1f258d6c53d7b058cdc6cd9ab1fd579b>`_.

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

For a full list of changes, please see the `CHANGES file <https://svn.apache.org/viewvc/libcloud/trunk/CHANGES?revision=1198753&view=markup>`_.
