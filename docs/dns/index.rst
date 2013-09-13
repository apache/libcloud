DNS
===

.. note::

    DNS API is available in Libcloud 0.6.0 and higher.

DNS API allows you to manage DNS as A Service and services such as Zerigo DNS,
Rackspace Cloud DNS and others.

Terminology
-----------

* **Zone** - Represents a DNS zone or so called domain.
* **Record** - Represents a DNS record. Each record belongs to a Zone and has
  a ``type`` and ``data`` attribute. Value of the ``data`` attribute depends on
  the record type.
  Some record types also require user to associate additional attributes with
  them. Those additional attributes are stored in the ``extra`` attribute
  (dictionary) on the record object. An example include ``MX`` and ``SRV``
  record type which also contains a priority.
* **RecordType** - Represents a DNS record type (``A``, ``AAAA``, ``MX``,
  ``TXT``, ``SRV``, ``PTR``, ``NS``, etc.)
* **Zone Type** - Each zone has a ``type`` attribute. This attribute represents
  a zone type. Type can either be ``master`` (also called primary) or ``slave``
  (also called secondary).

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
