Scaleway Compute Driver Documentation
=====================================

`Scaleway`_ is a dedicated bare metal cloud hosting provider based in Paris

.. figure:: /_static/images/provider_logos/scaleway.png
    :align: center
    :width: 300
    :target: https://www.scaleway.com/

Instantiating a driver and listing nodes
----------------------------------------

.. literalinclude:: /examples/compute/scaleway/list_nodes.py
   :language: python

Instantiating a driver and listing volumes
------------------------------------------

.. literalinclude:: /examples/compute/scaleway/list_volumes.py
  :language: python

API Docs
--------

.. autoclass:: libcloud.compute.drivers.scaleway.ScalewayNodeDriver
    :members:
    :inherited-members:

.. _`Scaleway`: https://www.scaleway.com/
