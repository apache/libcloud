Rackspace Compute Driver Documentation
======================================

`Rackspace`_ is a public and private cloud provider based in San Antonio, Texas
with datacenters in United States, United Kingdom, China and Australia.

Rackspace driver supports working with legacy, first-gen cloud servers and
next-gen OpenStack based cloud servers. Driver is based on the OpenStack so for
more informsa

Rackspace driver is based on the OpenStack driver so for more information about
that and OpenStack specific documentation, please refer to
:doc:`OpenStack Compute Driver Documentation <openstack>` page.

Instantiating a driver
----------------------

Examples
--------

1. Working with 'performance' cloud server flavors
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Rackspace recently annouced new 'perfomance' flavors of their cloud servers.
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
