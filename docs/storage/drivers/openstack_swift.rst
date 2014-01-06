OpenStack Swift Storage Driver Documentation
============================================

Connecting to the OpenStack Swift installation
----------------------------------------------

When connecting to the OpenStack Swift installation, you need to, besides
the username and api key argument also pass the following keyword arguments to
the driver constructor:

* ``ex_force_auth_url`` - Authentication service (Keystone) API URL. It can
  either be a full URL with a path.
* ``ex_force_service_type`` - Service type which will be used to find a
  matching service in the service catalog. Defaults to ``object-store``
* ``ex_force_service_name`` Service name which will be used to find a matching
  service in the service catalog. Defaults to ``swift``

For more information about other keyword arguments you can pass to the
constructor, please refer to the :ref:`Connecting to the OpenStack installation
<connecting-to-openstack-installation>` section of our documentation.

Examples
--------

1. Connect to OpenStack Swift Installation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This example shows how to connect to a Swift installation which uses a
non-default value (``Object Storage Service``) for the service name attribute
in the service catalog.

.. literalinclude:: /examples/storage/swift/connect_to_swift.py
   :language: python

2. Connecting to Rackspace CloudFiles using a generic Swift driver
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This example shows how to connect to the Rackspace CloudFiles using a generic
Swift driver.

Keep in mind that this example is here only for demonstration purposes. When
you are connecting to Rackspace CloudFiles installation for real, you should use
``CLOUDFILES`` provider constant which only requires you to specify username,
api key and region.

.. literalinclude:: /examples/storage/swift/connect_to_rackspace_cloudfiles.py
   :language: python
