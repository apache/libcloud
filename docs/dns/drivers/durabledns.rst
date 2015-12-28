Durable DNS Driver Documentation
================================

`DurableDNS`_ provides DNS hosting solutions for customers of all
sizes. Works with all hosting arrangements - shared web hosting, virtual
private servers, dedicated servers, and servers hosted on dynamic IP addresses.
The servers are located in data centers located in different areas of North
America. This geographic separation ensures that your DNS records are never
off-line due to network problems, natural disasters, data center failures, or
supplier failures.

See more at https://durabledns.com/

Instantiating the driver
------------------------

.. literalinclude:: /examples/dns/durabledns/instantiate_driver.py
   :language: python

API Docs
--------

.. autoclass:: libcloud.dns.drivers.durabledns.DurableDNSDriver
    :members:
    :inherited-members:

.. _`DurableDNS`: https://durabledns.com/
