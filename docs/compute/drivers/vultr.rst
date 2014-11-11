Vultr Compute Driver Documentation
========================================

`Vultr`_ is a public cloud provider based in mulitiple counties.

How to get API Key
------------------

visit https://my.vultr.com/settings/#API
You can see Your API Key in API Information Section in the middle of page
if you want to change your API Key, press Regenerate Button.

Examples
--------

1. create vultr driver - how to create vultr driver with api key
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: /examples/compute/vultr/vultr_compute_simple.py
   :language: python

API Docs
--------

.. autoclass:: libcloud.compute.drivers.vultr.VultrNodeDriver
    :members:
    :inherited-members:

.. _`vultr`: http://www.vultr.com
