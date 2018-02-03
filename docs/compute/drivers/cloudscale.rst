cloudscale.ch Compute Driver Documentation
==========================================

`cloudscale.ch`_ is a public cloud provider based in Switzerland.

.. figure:: /_static/images/provider_logos/cloudscale.png
    :align: center
    :width: 200
    :target: http://www.cloudscale.ch


How to get an API Key
---------------------

Simply visit `<https://control.cloudscale.ch/user/api-tokens>`_ and generate
your key.

You can generate read and read/write API keys. These token types give you more
access control. Revoking an API token is also possible.

Using the API to the full extent
--------------------------------

Most of the `cloudscale.ch` API is covered by the simple commands:

- ``driver.list_sizes()``
- ``driver.list_images()``
- ``driver.list_nodes()``
- ``driver.reboot_node(node)``
- ``driver.ex_start_node(node)``
- ``driver.ex_stop_node(node)``
- ``driver.ex_node_by_uuid(server_uuid)``
- ``driver.destroy_node(node)``
- ``driver.create_node(name, size, image, ex_create_attr={})``

In our :ref:`example <cloudscale-examples>` below you can see how you use 
``ex_create_attr`` when creating servers. Possible dictionary entries in 
``ex_create_attr`` are:

- ``ssh_keys`` (``list`` of ``str``) - A list of SSH public keys.
- ``volume_size_gb`` (``int``) - The size in GB of the root volume.
- ``bulk_volume_size_gb`` (``int``) - The size in GB of the bulk storage volume.
- ``use_public_network`` (``bool``) - Attaching/Detaching the public network interface.
- ``use_private_network`` (``bool``) - Attaching/Detaching the private network interface.
- ``use_ipv6`` (``bool``) - Enabling/Disabling IPv6.
- ``anti_affinity_with`` (``str``) - Pass the UUID of another server.
- ``user_data`` (``str``) - Cloud-init configuration (cloud-config). Provide YAML.


There's more extensive documentation on these parameters in our
`Server-Create API Documentation`_.

.. _cloudscale-examples:

Examples
--------

Create a cloudscale.ch server
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: /examples/compute/cloudscale/cloudscale_compute_simple.py
   :language: python

API Docs
--------

.. autoclass:: libcloud.compute.drivers.cloudscale.CloudscaleNodeDriver
    :members: create_node, list_images, list_nodes, list_sizes, 
              wait_until_running, reboot_node, ex_start_node, ex_stop_node,
              ex_node_by_uuid, destroy_node
    :undoc-members: 

.. _`cloudscale.ch`: https://www.cloudscale.ch
.. _`cloudscale.ch API`: https://www.cloudscale.ch/en/api/v1
.. _`Server-Create API Documentation`: https://www.cloudscale.ch/en/api/v1#servers-create
