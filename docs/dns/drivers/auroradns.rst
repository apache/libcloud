AuroraDNS DNS driver documentation
==================================

`PCextreme B.V.`_ is a Dutch cloud provider. It provides a public cloud offering
under the name AuroraCompute. All cloud services are under the family name
Aurora.

`AuroraDNS`_ is a highly available DNS service which also provides health
checking.

Records can be attached to a health check. When this health check becomes
unhealthy this record will no longer be served.

This provides the possibility to create loadbalancing over multiple servers
without the requirement of a central loadbalancer in the network. It is also
provider agnostic, health checks can point to any IP/Host on the internet.

IPv6
----
AuroraDNS fully supports IPv6:

* DNS queries over IPv6
* AAAA records
* Health checks over IPv6

Instantiating a driver
----------------------

When you instantiate a driver, you need to pass a your ``key`` and ``secret``
to the driver constructor. These can be obtained in the control panel of
AuroraDNS.

For example:

.. literalinclude:: /examples/dns/auroradns/instantiate_driver.py
   :language: python

Disabling and enabling records
------------------------------

Records in can be disabled and enabled. By default all new records are enabled,
but this property can be set during creation and can be updated.

For example:

.. literalinclude:: /examples/dns/auroradns/instantiate_driver.py
   :language: python

In this example we create a record, but disable it. This means it will not be
served.

Afterwards we enable the record and this make the DNS server serve this specific
record.

Health Checks
-------------

AuroraDNS has support for Health Checks which will disable all records attached
to that health check should it fail. With this you can create DNS based
loadbalancing over multiple records.

In the example below we create a health check and afterwards attach a newly
created record to this health check.

For example:

.. literalinclude:: /examples/dns/auroradns/health_checks.py
   :language: python

API Docs
--------

.. autoclass:: libcloud.dns.drivers.auroradns.AuroraDNSDriver
    :members:
    :inherited-members:

.. autoclass:: libcloud.dns.drivers.auroradns.AuroraDNSHealthCheck
    :members:
    :inherited-members:

.. _`PCextreme B.V.`: https://www.pcextreme.nl/
.. _`AuroraDNS`: https://www.pcextreme.nl/en/aurora/dns
