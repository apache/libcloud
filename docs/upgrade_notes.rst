Upgrade Notes
=============

This page describes how to upgrade from a previous version to a new version
which contains backward incompatible or semi-incompatible changes and how to
preserve the old behavior when this is possible.

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
