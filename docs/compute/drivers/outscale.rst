Outscale Driver Documentation
=================================

`Outscale`_ provides an IaaS platform allowing
developers to benefit from all the flexibility of the Cloud.
This IaaS platform relies on TINA OS, its Cloud manager whose purpose is to
provide great performances on the Cloud.
TINA OS is software developed by Outscale.

.. figure:: /_static/images/provider_logos/outscale.jpg
    :align: center
    :width: 300
    :target: https://www.outscale.com/

Outscale users can start virtual machines in the following regions:

* cloudgouv-west-1, France
* eu-west-2, France
* us-est-2, US
* us-west-1, US
* cn-southeast-1, China

Outscale is an European company and is priced in Euros.

Instantiating a driver
~~~~~~~~~~~~~~~~~~~~~~

When you instantiate a driver you need to pass the following arguments to the
driver constructor:

* ``key`` - Your Outscale  access key
* ``secret`` - Your Outscale secret key
* ``region`` - The region you want to make action on
* ``service`` - The Outscale service you want to use

Once you have some credentials you can instantiate the driver as shown below.

.. literalinclude:: /examples/compute/outscale/instantiate.py
   :language: python

List the Virtual Machines (node)
--------------------------------

Listing the Virtual Machines on Outscale using libcloud works the same as on any
other platform. This example is just to show exactly that.

This example will list the Virtual Machines in eu-west-2 region.

.. literalinclude:: /examples/compute/outscale/list_nodes.py
   :language: python


API Documentation
-----------------

.. autoclass:: libcloud.compute.drivers.outscale.OutscaleNodeDriver
    :members:
    :inherited-members:

.. _`Outscale`: https://docs.outscale.com/api
.. _`Outscale Inc.`: outscale_inc.html

Outscale Implementation of Libcloud
-----------------------------------

The Outscale driver implements the following ``NodeDriver`` functions:

Regions
-------
* ``list_locations`` - Returns a list of ``NodeLocation``

Nodes
-----
* ``create_node`` - Creates a ``Node``
* ``reboot_node`` - Reboots a ``Node``
* ``list_nodes`` - Returns a list of ``Node``
* ``destroy_node`` - Destroys an existing ``Node``
* ``start_node`` - Start a ``Node``
* ``start_node`` - Start a ``Node``
* ``stop_node`` - Stop a ``Node``

Images
------
* ``create_images`` - Returns a ``NodeImage``
* ``list_images`` - Returns a list of ``NodeImage``
* ``get_image`` - Returns a ``NodeImage``
* ``delete_image`` - Return a ``boolean``

Key Pairs
_________
* ``create_key_pair`` - Returns a ``KeyPair``
* ``list_key_pairs`` - Returns a list of ``KeyPair``
* ``get_key_pair`` - Returns a ``KeyPair``
* ``delete_key_pair`` - Returns a ``boolean``

Snapshots
---------
* ``create_volume_snapshot`` - Returns a ``VolumeSnapshot``
* ``list_snapshots`` - Returns a list of ``VolumeSnapshot``
* ``destroy_volume_snapshot`` - Returns a ``boolean``
* ``list_volume_snapshots`` - Returns a list of ``VolumeSnapshot``

Volumes
-------
* ``create_volume`` - Returns a ``StorageVolume``
* ``list_volumes`` - Returns a list of ``StorageVolume``
* ``destroy_volume`` - Returns a ``boolean``
* ``attach_volume`` - Return a ``boolean``
* ``detach_volume`` - Returns a ``boolean``

Outscale Extra Functions
------------------------

The Outscale driver implement the following extra methods:

IP
__
* ``ex_create_public_ip`` - Returns a ``boolean``
* ``ex_delete_public_ip`` - Returns a ``boolean``
* ``ex_list_public_ips`` - Returns a ``dict``
* ``ex_list_public_ip_ranges`` - Returns a ``dict``
* ``ex_attach_public_ip`` - Returns a ``boolean``
* ``ex_detach_public_ip`` - Returns a ``boolean``


Accounts
--------
* ``ex_check_account`` - Returns a ``boolean``
* ``ex_read_account`` - Returns a ``dict``
* ``ex_reset_account_password`` - Returns a ``dict``
* ``ex_send_reset_password_email`` - Returns a ``boolean``
* ``ex_create_account`` - Returns a ``boolean``
* ``ex_update_account`` - Returns a ``dict``


Tags
----
* ``ex_create_tag`` - Returns a ``boolean``
* ``ex_create_tags`` - Returns a ``boolean``
* ``ex_delete_tags`` - Returns a ``boolean``
* ``ex_list_tags`` - Returns a ``dict``

Regions and SubRegions
----------------------
* ``ex_list_regions`` - Returns a ``list`` of ``dict``
* ``ex_list_subregions`` - Returns a ``list`` of ``dict``

Access Keys
-----------
* ``ex_create_access_key`` - Returns a ``dict``
* ``ex_delete_access_key`` - Returns a ``boolean``
* ``ex_list_access_keys`` - Returns a ``list`` of ``dict``
* ``ex_list_secret_access_key`` - Returns a ``dict``
* ``ex_update_access_key`` - Returns a ``dict``

Client Gateways
---------------
* ``ex_create_client_gateway`` - Returns a ``dict``
* ``ex_delete_client_gateway`` - Returns a ``boolean``
* ``ex_list_client_gateways`` - Returns a ``list`` of ``dict``

Dhcp Options
------------
* ``ex_create_dhcp_options`` - Returns a ``dict``
* ``ex_delete_dhcp_options`` - Returns a ``boolean``
* ``ex_list_dhcp_options`` - Returns a ``list`` of ``dict``

Direct Links
------------
* ``ex_create_direct_link`` - Returns a ``dict``
* ``ex_delete_direct_link`` - Returns a ``boolean``
* ``ex_list_direct_links`` - Returns a ``list`` of ``dict``

Direct Link Interfaces
----------------------
* ``ex_create_direct_link_interface`` - Returns a ``dict``
* ``ex_delete_direct_link_interface`` - Returns a ``boolean``
* ``ex_list_direct_link_interfaces`` - Returns a ``list`` of ``dict``
