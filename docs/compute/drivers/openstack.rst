OpenStack Compute Driver Documentation
======================================

Connecting to the OpenStack installation
----------------------------------------

OpenStack driver constructor takes different arguments with which you tell it
information about your OpenStack installation. Those arguments describe things
such as the authentication service API URL, authentication service API version
and so on.

Keep in mind that majority of those arguments are optional and in the most
common scenario with a default installation, you will only need to provide
``ex_force_auth_url`` argument.

* ``ex_force_auth_url`` - Authentication service (Keystone) API URL (e.g.
  ``http://192.168.1.101:5000/v2.0``)
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
    * `2.0_password`` - authenticate against keystone with a username and
      password

  Unless you are working with a very old version of OpenStack you will either
  want to use ``2.0_apikey`` or ``2.0_password``.
* ``ex_force_auth_token`` - token which is used for authentication. If this
  argument is provided, normal authentication flow is skipped and the OpenStack
  API endpoint is directly hit with the provided token.
  Normal authentication flow involves hitting the auth service (Keystone) with
  the provided username and either password or API key and requesting an
  authentication token.
* ``ex_force_service_type``
* ``ex_force_service_name``
* ``ex_force_service_region``
* ``ex_force_base_url``

Examples

1. Most common use case - specifying only authentication service endpoint URL
   and API version

2. Specifying which entry to select in the service catalog using service_type,
   service_name and service_region arguments

3. Skipping the endpoint selection using service catalog by providing
   ``ex_force_base_url`` argument

4. Skipping normal authentication flow and hitting the API endpoint directly
   using the ``ex_force_auth_token`` argument


Simple workflow
---------------

Troubleshooting
---------------

I get ``Could not find specified endpoint`` error
-------------------------------------------------

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

TODO: link to the ml thread

I get ``Resource not found`` error
----------------------------------

TODO: link to the ml thread

This error most likely indicates that you have used an invalid value for the
``ex_force_base_url`` argument.

Keep in mind that this argument should point to the OpenStack API endpoint and
not to the authentication service API endpoint. API service and authentication
service are two different services which listen on different ports.

API Docs
--------

.. autoclass:: libcloud.compute.drivers.openstack.OpenStackNodeDriver
    :members:
    :inherited-members:
