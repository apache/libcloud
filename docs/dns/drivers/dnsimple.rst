DNSimple DNS Driver Documentation
=================================

`DNSimple`_ is a hosted DNS Service Provider that you can use to manage your
domains. Offers both a web interface and an iPhone application for adding and
removing domains and DNS records as well as an HTTP API with various code
libraries and tools.

Instantiating the driver
------------------------

.. literalinclude:: /examples/dns/dnsimple/instantiate_driver.py
   :language: python

API Docs
--------

.. autoclass:: libcloud.dns.drivers.dnsimple.DNSimpleDNSDriver
    :members:
    :inherited-members:

.. _`DNSimple`: https://dnsimple.com/
