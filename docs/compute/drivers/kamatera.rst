Kamatera Driver Documentation
===============================
`Kamatera`_ is a global cloud services platform provider, providing enterprise-grade cloud infrastructure products.
Kamatera is operating in 13 global data centers, with thousands of servers worldwide, serving tens of thousands of
clients including start-ups, application developers, international enterprises, and SaaS providers.

.. figure:: /_static/images/provider_logos/kamatera.png
    :align: center
    :width: 300
    :target: https://www.kamatera.com/

Kamatera operates globally from 13 data centers.

Enabling API access
-------------------

To allow API access to your Kamatera account, you first need to add an API key
by visiting `Kamatera Console`_ and adding a new key under API Keys. Use the
created key Client ID and Secret as the arguments to the driver constructor.

.. _`Kamatera`: https://www.kamatera.com/
.. _`Kamatera Console`: https://console.kamatera.com/

Examples
--------

Instantiating a driver
~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: /examples/compute/kamatera/instantiate_driver.py
   :language: python

Selecting location, size and disk image
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: /examples/compute/kamatera/selecting_location_size_image.py
   :language: python
