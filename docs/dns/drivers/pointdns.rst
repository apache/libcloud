Point DNS Driver Documentation
==============================

`PointDNS`_ provides an API that gives access to point zone, records, http and
email redirects management. The API is built using RESTful principles.

XML and JSON are supported as responses to API calls but this provider only
support JSON.

Instantiating the driver
------------------------

.. literalinclude:: /examples/dns/pointdns/instantiate_driver.py
   :language: python

API Docs
--------

.. autoclass:: libcloud.dns.drivers.pointdns.PointDNSDriver
    :members:
    :inherited-members:

.. _`PointDNS`: https://pointhq.com
