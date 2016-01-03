AuroraCompute Computer Driver Documentation
===========================================

`PCextreme B.V.`_ is a Dutch cloud provider. It provides a public cloud offering
under the name AuroraCompute. All cloud services are under the family name Aurora.

The datacenters / availability zones are located in:

- Amsterdam (NL)
- Rotterdam (NL)
- Miami (US)
- Los Angelos (US)
- Tokyo (JP)


.. figure:: /_static/images/provider_logos/pcextreme.png
    :align: center
    :width: 300
    :target: https://www.pcextreme.com/aurora/compute

The AuroraCompute driver is based on the CloudStack driver. Please refer to
:doc:`CloudStack Compute Driver Documentation <cloudstack>` page for more
information.


Instantiating a driver
----------------------

When you instantiate a driver you need to pass the following arguments to the
driver constructor:

* ``key`` - Your AuroraCompute API key
* ``secret`` - Your AuroraCompute secret key

You can find your 'key' and 'secret' in the AuroraCompute `Control Panel`_ under
your users.

With these credentials you can instantiate a driver:

.. literalinclude:: /examples/compute/auroracompute/instantiate_driver.py
   :language: python


Using a different region
------------------------

By default the region AMS (Amsterdam) is selected by the driver.

AuroraCompute supports multiple regions and when instantiating the driver you can
choose a region.

Keep in mind that each region uses different credentials. These can be found in
the `Control Panel`_ under your users.

In this example we select the Miami (MIA) region:

.. literalinclude:: /examples/compute/auroracompute/instantiate_driver_region.py
   :language: python


API Docs
--------

.. autoclass:: libcloud.compute.drivers.auroracompute.AuroraComputeNodeDriver
    :members:
    :inherited-members:

.. _`PCextreme B.V.`: https://www.pcextreme.com/
.. _`Control Panel`: https://cp.pcextreme.nl/
