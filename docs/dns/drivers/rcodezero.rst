RcodeZero DNS Driver Documentation
==================================

.. figure:: /_static/images/provider_logos/rcodezero.png
    :align: center
    :width: 300
    :target: https://www.rcodezero.at/en

`RcodeZero`_ is a European Anycast DNS service provided by nic.at. 

Supported Features:

- more than 35 nodes
- two seperate clouds with different ASes 
- full IPv4/IPv6 support
- primary as well as secondary Nameservers
- DNSSEC signing
- ANAME(ALIAS) records
- extensive statistics
- management via web interface or a REST based API
- DDoS mitigation
- dedicated IP addresses (optional)

Read more at https://www.rcodezero.at/en or get the API documentation
at https://my.rcodezero.at/api-doc

Instantiating the driver
------------------------

Log into https://my.rcodezero.at/ and get your API key. Pass the API key,
hostname and port to the driver constructor as shown below.

.. literalinclude:: /examples/dns/rcodezero/instantiate_driver.py
   :language: python

API Docs
--------

.. autoclass:: libcloud.dns.drivers.rcodezero.RcodeZeroDNSDriver
    :members:
    :inherited-members:

.. _`RcodeZero`: https://my.rcodezero.at/en
