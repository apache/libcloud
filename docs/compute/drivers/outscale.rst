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
------------------------------

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

Volumes
-------
* ``create_volume`` - Returns a ``StorageVolume``
* ``list_volumes`` - Returns a list of ``StorageVolume``
* ``destroy_volume`` - Returns a ``boolean``
* ``attach_volume`` - Return a ``boolean``
* ``detach_volume`` - Returns a ``boolean``


