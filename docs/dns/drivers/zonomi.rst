Zonomi DNS Driver Documentation
===============================

`Zonomi`_ name servers are spread around the globe (London, Dallas, New York
and Auckland). It offers Fully redundant, fault-tolerant, reliable name
servers, Instant updates, Low TTLs, Wildcard domain names, Any DNS record type,
Dynamic DNS, DNS API, Round robin DNS, No need to transfer your domain name
registrar, Integrates with Pingability's DNS fail over, Vanity name servers.

Read more at: http://zonomi.com/

Instantiating the driver
------------------------

.. literalinclude:: /examples/dns/zonomi/instantiate_driver.py
   :language: python

API Docs
--------

.. autoclass:: libcloud.dns.drivers.zonomi.ZonomiDNSDriver
    :members:
    :inherited-members:

.. _`Zonomi`: http://zonomi.com/
