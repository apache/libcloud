OnApp DNS Driver Documentation
=================================

`OnApp`_ Cloud integrates its fully redundant DNS network into the OnApp
Control Panel, so you can manage DNS for your own domains, and your customers’
domains. Its Anycast DNS service is hosted at datacenters around the world,
and it’s free of charge for customers running the full version of OnApp Cloud,
with CDN enabled. Get fast, fully redundant DNS for free!

Instantiating the driver
------------------------

.. literalinclude:: /examples/dns/onapp/instantiate_driver.py
   :language: python

API Docs
--------

.. autoclass:: libcloud.dns.drivers.onapp.OnAppDNSDriver
    :members:
    :inherited-members:

.. _`OnApp`: http://onapp.com/
