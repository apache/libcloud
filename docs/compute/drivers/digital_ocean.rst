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

Driver capabilities
-------------------

The :doc:`provider matrix </compute/supported_providers>` lists the standard
methods supported by each driver. The table below adds DigitalOcean-specific
details, including how catalogs are retrieved and which operations require
extension methods. Method names refer to ``DigitalOcean_v2_NodeDriver``.

.. list-table:: DigitalOcean API v2 capabilities
   :header-rows: 1
   :widths: 25 20 55

   * - Capability
     - Interface
     - Details
   * - Images
     - ``list_images``
     - Fetched from ``/v2/images`` with pagination; no hardcoded image catalog.
       The ``location`` argument does not filter the results.
   * - Sizes
     - ``list_sizes``
     - Fetched from ``/v2/sizes`` with pagination; no hardcoded size catalog.
       Pass ``location`` to filter sizes by region.
   * - Locations
     - ``list_locations``
     - Fetched from ``/v2/regions``. Only available regions are returned by
       default; use ``ex_available=False`` to include unavailable regions.
   * - Droplet lifecycle
     - Standard methods
     - ``list_nodes``, ``create_node``, ``reboot_node``, and ``destroy_node``
       are supported.
   * - User data and SSH keys
     - ``create_node`` options
     - Pass user data through ``ex_user_data`` and SSH key IDs or fingerprints
       through ``ex_create_attr={"ssh_keys": [...]}``.
   * - IPv6
     - Extension options/methods
     - Use ``ex_create_attr={"ipv6": True}`` when creating a Droplet, or
       ``ex_enable_ipv6`` for an existing Droplet.
   * - Start and stop
     - Extension methods
     - Use ``ex_power_on_node`` and ``ex_shutdown_node``. The standard
       ``start_node`` and ``stop_node`` methods are not implemented.
   * - Block storage
     - Standard methods
     - ``list_volumes``, ``create_volume``, ``destroy_volume``, ``attach_volume``,
       and ``detach_volume`` are supported, as are volume snapshot methods.

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
