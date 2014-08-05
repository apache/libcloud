OpenStack Compute Driver Documentation
======================================

`OpenStack`_ is an open-source project which allows you to build and run your
own public or a private cloud.

.. figure:: /_static/images/provider_logos/openstack.png
    :align: center
    :width: 200
    :target: http://www.openstack.org/

Among many other private clouds, it also powers Rackspace's Public Cloud.

.. _connecting-to-openstack-installation:

Connecting to the OpenStack installation
----------------------------------------

OpenStack driver constructor takes different arguments with which you describe
your OpenStack installation. Those arguments describe things such as the
authentication service API URL, authentication service API version and so on.

Keep in mind that the majority of those arguments are optional and in the most
common scenario with a default installation, you will only need to provide
``ex_force_auth_url`` argument.

Available arguments:

* ``ex_force_auth_url`` - Authentication service (Keystone) API URL. It can
  either be a full URL with a path (e.g.
  ``https://192.168.1.101:5000/v2.0/tokens/``) or a base URL without a path
  (e.g. ``https://192.168.1.1``). If no path is provided, default path for the
  provided auth version is appended to the base URL.
* ``ex_force_auth_version`` - API version of the authentication service. This
  argument determines how authentication is performed. Valid and supported
  versions are:

  * ``1.0`` - authenticate against the keystone using the provided username
    and API key (old and deprecated version which was used by Rackspace in
    the past)
  * ``1.1`` - authenticate against the keystone using the provided username
    and API key (old and deprecated version which was used by Rackspace in
    the past)
  * ``2.0`` or ``2.0_apikey`` - authenticate against keystone with a username
    and API key
  * ``2.0_password`` - authenticate against keystone with a username and
    password

  Unless you are working with a very old version of OpenStack you will either
  want to use ``2.0_apikey`` or ``2.0_password``.
* ``ex_tenant_name`` - tenant / project name
* ``ex_force_auth_token`` - token which is used for authentication. If this
  argument is provided, normal authentication flow is skipped and the OpenStack
  API endpoint is directly hit with the provided token.
  Normal authentication flow involves hitting the auth service (Keystone) with
  the provided username and either password or API key and requesting an
  authentication token.
* ``ex_force_service_type``
* ``ex_force_service_name``
* ``ex_force_service_region``
* ``ex_force_base_url`` - Base URL to the OpenStack API endpoint. By default,
  driver obtains API endpoint URL from the server catalog, but if this argument
  is provided, this step is skipped and the provided value is used directly.

Some examples which show how to use this arguments can be found in the section
bellow.

Examples
--------

1. Most common use case - specifying only authentication service endpoint URL and API version
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: /examples/compute/openstack/simple_auth.py
   :language: python

2. Specifying which entry to select in the service catalog using service_type service_name and service_region arguments
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: /examples/compute/openstack/custom_service_catalog_selection_args.py
   :language: python

3. Skipping the endpoint selection using service catalog by providing ``ex_force_base_url`` argument
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Keep in mind that the base url must also contain tenant id as the last
component of the URL (``12345`` in the example bellow).

.. literalinclude:: /examples/compute/openstack/force_base_url.py
   :language: python

4. Skipping normal authentication flow and hitting the API endpoint directly using the ``ex_force_auth_token`` argument
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This is an advanced use cases which assumes you manage authentication and token
retrieval yourself.

If you use this argument, the driver won't hit authentication service and as
such, won't be aware of the token expiration time.

This means auth token will be considered valid for the whole life time of the
driver instance and you will need to manually re-instantiate a driver with a new
token before the currently used one is about to expire.

.. literalinclude:: /examples/compute/openstack/force_auth_token.py
   :language: python

5. Connecting and specifying a tenant
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This example shows how to connect to OpenStack installation which requires you
to specify a tenant (``ex_tenant_name`` argument).

.. literalinclude:: /examples/compute/openstack/tenant_name.py
   :language: python

6. HP Cloud (www.hpcloud.com)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Connecting to HP Cloud US West and US East (OpenStack Havana).

.. literalinclude:: /examples/compute/openstack/hpcloud.py
   :language: python

Non-standard functionality and extension methods
------------------------------------------------

OpenStack driver exposes a bunch of non-standard functionality through
extension methods and arguments.

This functionality includes:

* server image management
* network management
* floating IP management
* key-pair management

For information on how to use this functionality please see the method
docstrings bellow.

Other Information
-----------------

Authentication token re-use
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Since version 0.13.0, the driver caches auth token in memory and re-uses it
between different requests.

This means that driver will only hit authentication service and obtain auth
token on the first request or if the auth token is about to expire.

As noted in the example 4 above, this doesn't hold true if you use
``ex_force_auth_token`` argument.

Troubleshooting
---------------

I get ``Could not find specified endpoint`` error
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This error indicates that the driver couldn't find a specified API endpoint
in the service catalog returned by the authentication service.

There are many different things which could cause this error:

1. Service catalog is empty
2. You have not specified a value for one of the following arguments
   ``ex_service_type``, ``ex_service_name``, ``ex_service_region`` and the
   driver is using the default values which don't match your installation.
3. You have specified invalid value for one or all of the following arguments:
   ``ex_service_type``, ``ex_service_name``, ``ex_service_region``

The best way to troubleshoot this issue is to use ``LIBCLOUD_DEBUG``
functionality which is documented in the debugging section. This
functionality allows you to introspect the response from the authentication
service and you can make sure that ``ex_service_type``, ``ex_service_name``,
``ex_service_region`` arguments match values returned in the service catalog.

If the service catalog is empty, you have two options:

1. Populate the service catalog and makes sure the ``ex_service_type``,
   ``ex_service_name`` and ``ex_service_region`` arguments match the values
   defined in the service catalog.
2. Provide the API endpoint url using ``ex_force_base_url`` argument and skip
   the "endpoint selection using the service catalog" step all together

I get ``Resource not found`` error
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This error most likely indicates that you have used an invalid value for the
``ex_force_base_url`` argument.

Keep in mind that this argument should point to the OpenStack API endpoint and
not to the authentication service API endpoint. API service and authentication
service are two different services which listen on different ports.

API Docs
--------

Please note that there are two API versions of the OpenStack Compute API, which
are supported by two different subclasses of the OpenStackNodeDriver. The
default is the 1.1 API. The 1.0 API is supported to be able to connect to
OpenStack instances which do not yet support the version 1.1 API.

Compute 1.1 API version (current)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: libcloud.compute.drivers.openstack.OpenStack_1_1_NodeDriver
    :members:
    :inherited-members:

Compute 1.0 API version (old installations)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: libcloud.compute.drivers.openstack.OpenStack_1_0_NodeDriver
    :members:
    :inherited-members:

.. _`OpenStack`: http://www.openstack.org/
