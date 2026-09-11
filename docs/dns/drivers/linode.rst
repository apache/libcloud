Linode DNS Driver Documentation
===============================

`Linode`_ is an American cloud hosting provider that offers managed DNS for
domains through its Domains service.

.. figure:: /_static/images/provider_logos/linode.png
    :align: center
    :width: 200
    :target: https://www.linode.com/

Driver features
---------------

* Manage zones (domains) and records for Linode hosted domains
* Supports the SOA, NS, MX, A, AAAA, CNAME, PTR, TXT, SRV and CAA record types

How to get API Access Token
---------------------------

Visit https://cloud.linode.com/profile/tokens and create a Personal Access
Token. The token is used as the ``key`` argument when instantiating the driver.

Examples
--------

Instantiating the driver
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: /examples/dns/linode/instantiate_driver.py
   :language: python

API Docs
--------

.. autoclass:: libcloud.dns.drivers.linode.LinodeDNSDriverV4
    :members:
    :inherited-members:

.. _`Linode`: https://www.linode.com/
