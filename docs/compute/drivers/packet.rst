Packet Compute Driver Documentation
===================================

`Packet`_ is a dedicated bare metal cloud hosting provider based in New York
City

.. figure:: /_static/images/provider_logos/packet.png
    :align: center
    :width: 300
    :target: https://www.packet.net/

Instantiating a driver and listing devices in a project
-------------------------------------------------------

.. literalinclude:: /examples/compute/packet/instantiate_api_v1.0.py
   :language: python

API Docs
--------

.. autoclass:: libcloud.compute.drivers.packet.PacketNodeDriver
    :members:
    :inherited-members:

.. _`Packet`: https://www.packet.net/
