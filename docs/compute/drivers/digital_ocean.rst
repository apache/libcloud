DigitalOcean Compute Driver Documentation
=========================================

`DigitalOcean`_ is an American virtual private server provider based in New York
City with data centers in New York, Amsterdam, San Francisco, London and
Singapore.

.. figure:: /_static/images/provider_logos/digitalocean.png
    :align: center
    :width: 300
    :target: https://www.digitalocean.com/

Instantiating a driver
----------------------

DigitalOcean driver supports two API versions - old API v1.0 and the new API
v2.0 which is currently in beta. Since trunk (to be libcloud v0.18.0), the
driver uses new API v2.0 by default.

Instantiating a driver using API v2.0
-------------------------------------

.. literalinclude:: /examples/compute/digitalocean/instantiate_api_v2.0.py
   :language: python

Instantiating a driver using API v1.0
-------------------------------------

.. literalinclude:: /examples/compute/digitalocean/instantiate_api_v1.0.py
   :language: python

API Docs
--------

API v2.0
~~~~~~~~

.. autoclass:: libcloud.compute.drivers.digitalocean.DigitalOcean_v2_NodeDriver
    :members:
    :inherited-members:

API v1.0
~~~~~~~~

.. autoclass:: libcloud.compute.drivers.digitalocean.DigitalOcean_v1_NodeDriver
    :members:
    :inherited-members:

.. _`DigitalOcean`: https://www.digitalocean.com/
