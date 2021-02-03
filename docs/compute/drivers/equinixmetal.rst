EquinixMetal Compute Driver Documentation
=========================================

`EquinixMetal`_ is a dedicated bare metal cloud hosting provider

.. figure:: /_static/images/provider_logos/equinixmetal.png
    :align: center
    :width: 300
    :target: https://metal.equinix.com/

Instantiating a driver and listing devices in a project
-------------------------------------------------------

.. literalinclude:: /examples/compute/equinixmetal/instantiate_api_v1.0.py
   :language: python

API Docs
--------

.. autoclass:: libcloud.compute.drivers.equinixmetal.EquinixMetalNodeDriver
    :members:
    :inherited-members:

.. _`EquinixMetal`: https://metal.equinix.com/
