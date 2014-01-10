Rackspace Compute Driver Documentation
======================================

`Rackspace`_ is a public and private cloud provider based in San Antonio, Texas
with data centers in United States, United Kingdom, China and Australia.

.. figure:: /_static/images/provider_logos/rackspace.png
    :align: center
    :width: 300
    :target: http://www.rackspace.com/cloud/

Rackspace driver supports working with legacy, first-gen cloud servers and
next-gen OpenStack based cloud servers.

Rackspace driver is based on the OpenStack driver so for more information about
that and OpenStack specific documentation, please refer to
:doc:`OpenStack Compute Driver Documentation <openstack>` page.

Instantiating a driver
----------------------

When you instantiate a driver you need to pass the following arguments to the
driver constructor:

* ``username`` - your Rackspace Cloud username
* ``api_key`` - your Rackspace Cloud API key
* ``region`` - Which region to use. Supported regions depend on the driver type
  (next-gen vs first-gen).

Instantiating a next-gen driver
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Supported regions: ``dfw``, ``ord``, ``iad``, ``lon``, ``syd``, ``hkg``

.. literalinclude:: /examples/compute/rackspace/instantiate_next_gen.py
   :language: python

Instantiating a first-gen driver
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Keep in mind that first-gen cloud servers have been deprecated and you are
strongly encouraged to use next-gen cloud servers.

Supported regions: ``us``, ``uk``

.. literalinclude:: /examples/compute/rackspace/instantiate_first_gen.py
   :language: python

Examples
--------

1. Working with 'performance' cloud server flavors
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Rackspace recently announced new 'performance' flavors of their cloud servers.
The example bellow shows how to use this new flavors.

Keep in mind that this new flavors are currently only supported in the following
regions: ``iad``, ``ord``, ``lon``.

.. literalinclude:: /examples/compute/rackspace/performance_flavors.py
   :language: python

API Docs
--------

.. autoclass:: libcloud.compute.drivers.rackspace.RackspaceNodeDriver
    :members:
    :inherited-members:

.. autoclass:: libcloud.compute.drivers.rackspace.RackspaceFirstGenNodeDriver
    :members:
    :inherited-members:

.. _`Rackspace`: http://www.rackspace.com/cloud/
