HostVirtual DNS Driver Documentation
====================================

`Host Virtual`_ is a cloud hosting provider that operates dual-stack IPv4
and IPv6 IaaS clouds in 15 locations worldwide.

Instantiating a driver
----------------------

When you instantiate a driver, you need to pass a single ``key`` argument to
the driver constructor. This argument represents your API secret key.

For example:

.. literalinclude:: /examples/dns/hostvirtual/instantiate_driver.py
   :language: python

.. _`Host Virtual`: https://www.hostvirtual.com/
