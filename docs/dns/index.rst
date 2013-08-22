DNS
===

.. note::

    DNS API is available in Libcloud 0.6.0 and higher.

DNS API allows you to manage DNS as A Service and services such as Zerigo DNS,
Rackspace Cloud DNS and others.

Terminology
-----------

* **Zone** - represents a DNS zone or so called domain.
* **Record** - represents a DNS record. Each record belongs to a Zone and has 
  a record type and data attribute. Data depends on the record type.
* **RecordType** - represents a DNS record type (A, AAAA, MX, TXT, etc.)

Supported Providers
-------------------

For a list of supported providers see :doc:`supported providers page
</dns/supported_providers>`.

Examples
--------

We have :doc:`examples of several common patterns </dns/examples>`.

API Reference
-------------

There is a reference to :doc:`all the methods on the base dns driver
</dns/api/>`.
