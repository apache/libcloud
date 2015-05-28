DigitalOcean DNS Driver Documentation
=====================================

`DigitalOcean`_ is an American virtual private server provider based in New
York City with data centers in New York, Amsterdam, San Francisco, London,
Singapore and Frankfurt.

.. figure:: /_static/images/provider_logos/digitalocean.png
    :align: center
    :width: 300
    :target: https://www.digitalocean.com/

Instantiating a driver
----------------------

DigitalOcean dns driver only supports the v2.0 API requiring a Personal Access
Token to initialize as the key.

Instantiating the driver
-------------------------------------

.. literalinclude:: /examples/dns/digitalocean/instantiate_driver.py
   :language: python

API Docs
--------

.. autoclass:: libcloud.dns.drivers.digitalocean.DigitalOceanDNSDriver
    :members:
    :inherited-members:

.. _`DigitalOcean`: https://www.digitalocean.com/
