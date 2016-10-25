DigitalOcean Compute Driver Documentation
=========================================

`DigitalOcean`_ is an American cloud provider based in New York City with data
centers in New York, Amsterdam, San Francisco, London, Singapore, Frankfurt,
Toronto, and Bangalore.

.. figure:: /_static/images/provider_logos/digitalocean.png
    :align: center
    :width: 300
    :target: https://www.digitalocean.com/

Instantiating a driver
----------------------

The DigitalOcean driver supports API v2.0, requiring a Personal Access
Token to initialize as the key. The older API v1.0 `reached end of life on
November 9, 2015`_. Support for API v1.0 was removed in libcloud v1.2.2.

Instantiating a driver using API v2.0
-------------------------------------

.. literalinclude:: /examples/compute/digitalocean/instantiate_api_v2.0.py
   :language: python

Creating a Droplet using API v2.0
---------------------------------

.. literalinclude:: /examples/compute/digitalocean/create_api_v2.0.py
   :language: python

API Docs
--------

API v2.0
~~~~~~~~

.. autoclass:: libcloud.compute.drivers.digitalocean.DigitalOcean_v2_NodeDriver
    :members:
    :inherited-members:


.. _`DigitalOcean`: https://www.digitalocean.com/
.. _`reached end of life on November 9, 2015`: https://developers.digitalocean.com/documentation/changelog/api-v1/sunsetting-api-v1/