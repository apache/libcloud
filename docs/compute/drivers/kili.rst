Kili Cloud Computer Driver Documentation
========================================

`Kili Cloud`_ is a public cloud provider based in Africa.

Kili Cloud driver is based on the OpenStack one. For more information
information and OpenStack specific documentation, please refer to
:doc:`OpenStack Compute Driver Documentation <openstack>` page.

Examples
--------

1. Instantiating the driver
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Unlike other OpenStack based providers, Kili cloud also requires you to specify
tenant name when connecting to their cloud. You can do that by passing
``tenant_name`` argument to the driver constructor as shown in the code example
below.

This attribute represents a company name you have entered while signing up for
Kili.

.. literalinclude:: /examples/compute/openstack/kilicloud_native.py
   :language: python

API Docs
--------

.. autoclass:: libcloud.compute.drivers.kili.KiliCloudNodeDriver
    :members:
    :inherited-members:

.. _`Kili Cloud`: http://kili.io/
.. _`Kili Cloud dashboard`: https://dash.kili.io
