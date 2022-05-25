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
* ``stop_node`` - Stop a ``Node``

Images
------
* ``create_images`` - Returns a ``NodeImage``
* ``list_images`` - Returns a list of ``NodeImage``
* ``get_image`` - Returns a ``NodeImage``
* ``delete_image`` - Return a ``bool``
* ``ex_create_image_export_task`` - Returns a ``dict``
* ``ex_list_image_export_task`` - Returns a ``list`` of ``dict``
* ``ex_update_image`` - Returns a ``dict``

Key Pairs
_________
* ``create_key_pair`` - Returns a ``KeyPair``
* ``list_key_pairs`` - Returns a list of ``KeyPair``
* ``get_key_pair`` - Returns a ``KeyPair``
* ``delete_key_pair`` - Returns a ``bool``

Snapshots
---------
* ``create_volume_snapshot`` - Returns a ``VolumeSnapshot``
* ``list_snapshots`` - Returns a list of ``VolumeSnapshot``
* ``destroy_volume_snapshot`` - Returns a ``bool``
* ``list_volume_snapshots`` - Returns a list of ``VolumeSnapshot``
* ``ex_create_snapshot_export_task`` - Returns a ``dict``
* ``ex_list_snapshot_export_tasks`` - Returns a ``list`` of ``dict``
* ``ex_update_snapshot`` - Returns a ``dict``

Volumes
-------
* ``create_volume`` - Returns a ``StorageVolume``
* ``list_volumes`` - Returns a list of ``StorageVolume``
* ``destroy_volume`` - Returns a ``bool``
* ``attach_volume`` - Return a ``bool``
* ``detach_volume`` - Returns a ``bool``

Outscale Extra Functions
------------------------

The Outscale driver implement the following extra methods:

Public IPs
----------
* ``ex_create_public_ip`` - Returns a ``bool``
* ``ex_delete_public_ip`` - Returns a ``bool``
* ``ex_list_public_ips`` - Returns a ``dict``
* ``ex_list_public_ip_ranges`` - Returns a ``dict``
* ``ex_attach_public_ip`` - Returns a ``bool``
* ``ex_detach_public_ip`` - Returns a ``bool``

Accounts
--------
* ``ex_check_account`` - Returns a ``bool``
* ``ex_read_account`` - Returns a ``dict``
* ``ex_reset_account_password`` - Returns a ``dict``
* ``ex_send_reset_password_email`` - Returns a ``bool``
* ``ex_create_account`` - Returns a ``bool``
* ``ex_update_account`` - Returns a ``dict``
* ``ex_list_consumption_account`` - Returns a ``list`` of ``dict``

Tags
----
* ``ex_create_tag`` - Returns a ``bool``
* ``ex_create_tags`` - Returns a ``bool``
* ``ex_delete_tags`` - Returns a ``bool``
* ``ex_list_tags`` - Returns a ``dict``

Regions and SubRegions
----------------------
* ``ex_list_regions`` - Returns a ``list`` of ``dict``
* ``ex_list_subregions`` - Returns a ``list`` of ``dict``

Access Keys
-----------
* ``ex_create_access_key`` - Returns a ``dict``
* ``ex_delete_access_key`` - Returns a ``bool``
* ``ex_list_access_keys`` - Returns a ``list`` of ``dict``
* ``ex_list_secret_access_key`` - Returns a ``dict``
* ``ex_update_access_key`` - Returns a ``dict``

Client Gateways
---------------
* ``ex_create_client_gateway`` - Returns a ``dict``
* ``ex_delete_client_gateway`` - Returns a ``bool``
* ``ex_list_client_gateways`` - Returns a ``list`` of ``dict``

Dhcp Options
------------
* ``ex_create_dhcp_options`` - Returns a ``dict``
* ``ex_delete_dhcp_options`` - Returns a ``bool``
* ``ex_list_dhcp_options`` - Returns a ``list`` of ``dict``

Direct Links
------------
* ``ex_create_direct_link`` - Returns a ``dict``
* ``ex_delete_direct_link`` - Returns a ``bool``
* ``ex_list_direct_links`` - Returns a ``list`` of ``dict``

Direct Link Interfaces
----------------------
* ``ex_create_direct_link_interface`` - Returns a ``dict``
* ``ex_delete_direct_link_interface`` - Returns a ``bool``
* ``ex_list_direct_link_interfaces`` - Returns a ``list`` of ``dict``

Flexible GPU
------------
* ``ex_create_flexible_gpu`` - Returns a ``dict``
* ``ex_delete_flexible_gpu`` - Returns a ``bool``
* ``ex_link_flexible_gpu`` - Returns a ``bool``
* ``ex_unlink_flexible_gpu`` - Returns a ``bool``
* ``ex_list_flexible_gpu_catalog`` - Returns a ``list`` of ``dict``
* ``ex_list_flexible_gpus`` - Returns a ``list`` of ``dict``
* ``ex_update_flexible_gpu`` - Returns a ``dict``

Internet Services
-----------------
* ``ex_create_internet_service`` - Returns a ``dict``
* ``ex_delete_internet_service`` - Returns a ``bool``
* ``ex_link_internet_service`` - Returns a ``bool``
* ``ex_unlink_internet_service`` - Returns a ``bool``
* ``ex_list_internet_services`` - Returns a ``list`` of ``dict``

Listener
--------
* ``ex_create_listener_rule`` - Returns a ``dict``
* ``ex_create_load_balancer_listeners`` - Returns a ``dict``
* ``ex_delete_listener_rule`` - Returns a ``bool``
* ``ex_delete_load_balancer_listeners`` - Returns a ``bool``
* ``ex_list_listener_rules`` - Returns a ``bool``
* ``ex_update_listener_rule`` - Returns a ``dict``

Load Balancers
--------------
* ``ex_create_load_balancer`` - Returns a ``dict``
* ``ex_update_load_balancer`` - Returns a ``dict``
* ``ex_create_load_balancer_tags`` - Returns a ``bool``
* ``ex_delete_load_balancer`` - Returns a ``bool``
* ``ex_delete_load_balancer_tags`` - Returns a ``bool``
* ``ex_deregister_vms_in_load_balancer`` - Returns a ``bool``
* ``ex_register_vms_in_load_balancer`` - Returns a ``bool``
* ``ex_list_load_balancer_tags`` - Returns a ``list`` of ``dict``
* ``ex_list_vms_health`` - Returns a ``list`` of ``dict``
* ``ex_list_load_balancers`` - Returns a ``list`` of ``dict``

Load Balancer Policies
----------------------
* ``ex_create_load_balancer_policy`` - Returns a ``dict``
* ``ex_delete_load_balancer_policy`` - Returns a ``bool``

Nat Services
------------
* ``ex_create_nat_service`` - Returns a ``dict``
* ``ex_delete_nat_service`` - Returns a ``bool``
* ``ex_list_nat_services`` - Returns a ``list`` of ``dict``

Net
---
* ``ex_create_net`` - Returns a ``dict``
* ``ex_delete_net`` - Returns a ``bool``
* ``ex_list_nets`` - Returns a ``list`` of ``dict``
* ``ex_update_net`` - Returns a ``dict``

Net Access Point
----------------
* ``ex_create_net_access_point`` - Returns a ``dict``
* ``ex_delete_net_access_point`` - Returns a ``bool``
* ``ex_list_net_access_point_services`` - Returns a ``list`` of ``dict``
* ``ex_list_net_access_points`` - Returns a ``list`` of ``dict``
* ``ex_update_net_access_point`` - Returns a ``dict``

Net Peerings
------------
* ``ex_accept_net_peering`` - Returns a ``dict``
* ``ex_create_net_peering`` - Returns a ``dict``
* ``ex_delete_net_peering`` - Returns a ``bool``
* ``ex_list_net_peerings`` - Returns a ``list`` of ``dict``
* ``ex_reject_net_peering`` - Returns a ``dict``

Nics
----
* ``ex_create_nic`` - Returns a ``dict``
* ``ex_delete_nic`` - Returns a ``bool``
* ``ex_link_nic`` - Returns a ``bool``
* ``ex_unlink_nic`` - Returns a ``bool``
* ``ex_link_private_ips`` - Returns a ``bool``
* ``ex_list_nics`` - Returns a ``list`` of ``dict``
* ``ex_unlink_private_ips`` - Returns a ``bool``
* ``ex_update_nic`` - Returns a ``dict``

Product Types
-------------
* ``ex_list_product_types`` - Returns a ``list`` of ``dict``

Quotas
------
* ``ex_list_quotas`` - Returns a ``list`` of ``dict``

Routes
------
* ``ex_create_route`` - Returns a ``dict``
* ``ex_delete_route`` - Returns a ``bool``
* ``ex_update_route`` - Returns a ``dict``

Route Tables
------------
* ``ex_create_route_table`` - Returns a ``dict``
* ``ex_delete_route_table`` - Returns a ``bool``
* ``ex_link_route_table`` - Returns a ``bool``
* ``ex_list_route_tables`` - Returns a ``list`` of ``dict``
* ``ex_unlink_route_table`` - Returns a ``bool``

Server Certificates
-------------------
* ``ex_create_server_certificate`` - Returns a ``dict``
* ``ex_delete_server_certificate`` - Returns a ``bool``
* ``ex_list_server_certificates`` - Returns a ``list`` of ``dict``
* ``ex_update_server_certificate`` - Returns a ``dict``

Virtual Gateways
----------------
* ``ex_create_virtual_gateway`` - Returns a ``dict``
* ``ex_delete_virtual_gateway`` - Returns a ``bool``
* ``ex_link_virtual_gateway`` - Returns a ``dict``
* ``ex_list_virtual_gateways`` - Returns a ``list`` of ``dict``
* ``ex_unlink_virtual_gateway`` - Returns a ``bool``
* ``ex_update_route_propagation`` - Returns a ``dict``

Security Groups
---------------
* ``ex_create_security_group`` - Returns a ``dict``
* ``ex_delete_security_group`` - Returns a ``bool``
* ``ex_list_security_groups`` - Returns a ``list`` of ``dict``

Security Group Rules
--------------------
* ``ex_create_security_group_rule`` - Returns a ``dict``
* ``ex_delete_security_group_rule`` - Returns a ``dict``


Subnets
-------
* ``ex_create_subnet`` - Returns a ``dict``
* ``ex_delete_subnet`` - Returns a ``bool``
* ``ex_list_subnets`` - Returns a ``list`` of ``dict``
* ``ex_update_subnet`` - Returns a ``dict``

Tasks
-----
* ``ex_delete_export_task`` - Returns a ``bool``

Vpn Connections
---------------
* ``ex_create_vpn_connection`` - Returns a ``dict``
* ``ex_create_vpn_connection_route`` - Returns a ``bool``
* ``ex_delete_vpn_connection`` - Returns a ``bool``
* ``ex_delete_vpn_connection_route`` - Returns a ``bool``
* ``ex_list_vpn_connections`` - Returns a ``list`` of ``dict``

Nodes
-----
* ``ex_read_admin_password_node`` - Returns a ``str``
* ``ex_read_console_output_node`` - Returns a ``str``
* ``ex_list_node_types`` - Returns a ``list`` of ``dict``
* ``ex_list_nodes_states`` - Returns a ``list`` of ``dict``
* ``ex_update_node`` - Returns a ``list`` of ``dict``

Certificate Authority
---------------------
* ``ex_create_certificate_authority`` - Returns a ``dict``
* ``ex_delete_certificate_authority`` - Returns a ``bool``
* ``ex_read_certificate_authorities`` - Returns a ``list`` of ``dict``

API Access Rules
----------------
* ``ex_create_api_access_rule`` - Returns a ``dict``
* ``ex_delete_api_access_rule`` - Returns a ``bool``
* ``ex_read_api_access_rules`` - Returns a ``list`` of ``dict``
* ``ex_update_api_access_rule`` - Returns a ``dict``


