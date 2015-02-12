Vultr Compute Driver Documentation
==================================

`Vultr`_ is a public cloud provider based in multiple countries.

.. figure:: /_static/images/provider_logos/vultr.png
    :align: center
    :width: 200
    :target: http://www.vultr.com


How to get API Key
------------------

Visit https://my.vultr.com/settings/#API

You can see Your API Key in API Information Section in the middle of page.
If you want to change your API Key, press the Regenerate Button.

Examples
--------

1. Create vultr driver - how to create vultr driver with api key
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: /examples/compute/vultr/vultr_compute_simple.py
   :language: python

API Docs
--------

.. autoclass:: libcloud.compute.drivers.vultr.VultrNodeDriver
    :members:
    :inherited-members:

.. _`vultr`: http://www.vultr.com
