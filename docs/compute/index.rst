Compute
=======

The compute component of ``libcloud`` allows you to manage cloud and virtual
servers offered by different providers, more than 20 in total.

In addition to  managing the servers this component also allows you to run
deployment scripts on newly created servers. Deployment or "bootstrap" scripts
allow you to execute arbitrary shell commands. This functionality is usually
used to prepare your freshly created server, install your SSH key, and run a
configuration management tool (such as Puppet, Chef, or cfengine) on it.

Besides managing cloud and virtual servers, compute component also allows you
to manage cloud block storage (not to be confused with cloud object storage)
for providers which support it.
Block storage management is lives under compute API, because it is in most cases
tightly coupled with compute resources.

Terminology
-----------

Compute
~~~~~~~

* :class:`~libcloud.compute.base.Node` - represents a cloud or virtual server.
* :class:`~libcloud.compute.base.NodeSize` - represents node hardware
  configuration. Usually this is amount of the available RAM, bandwidth,
  CPU speed and disk size. Most of the drivers also expose an hourly price
  (in dollars) for the Node of this size.
* :class:`~libcloud.compute.base.NodeImage` - represents an operating system
  image.
* :class:`~libcloud.compute.base.NodeLocation` - represents a physical location
  where a server can be.
* :class:`~libcloud.compute.types.NodeState` - represents a node state.
  Standard states are: ``running``, ``stopped``, ``rebooting``, ``terminated``,
  ``pending``, and ``unknown``.

Key Pair Management
~~~~~~~~~~~~~~~~~~~

* :class:`~libcloud.compute.base.KeyPair` - represents an SSH key pair object.

Block Storage
~~~~~~~~~~~~~

* :class:`~libcloud.compute.base.StorageVolume` - represents a block storage
  volume
* :class:`~libcloud.compute.base.VolumeSnapshot` - represents a point in time
  snapshot of a StorageVolume

Supported Providers
-------------------

For a list of supported providers see :doc:`supported providers page
</compute/supported_providers>`.

Pricing
-------

For majority of the compute providers Libcloud provides estimated pricing
information which tells users how much it costs per hour to run a :class:`Node`
with a specific :class:`NodeSize`.

For more information, please see the :doc:`pricing page </compute/pricing>`.

Deployment
----------

Libcloud provides deployment functionality which makes bootstrapping a server
easier. It allows you to create a server and run shell commands on it once the
server has been created.

For more information and examples, please see the :doc:`deployment page
</compute/deployment>`.

SSH key pair management
-----------------------

Compute API also allows you to manage your SSH key pairs.

For more information and examples, please see the :doc:`key pair management
page </compute/key_pair_management>`.

Examples
--------

We have :doc:`examples of several common patterns </compute/examples>`.

API Reference
-------------

For a full reference of all the classes and methods exposed by the compute
API, see :doc:`this page </compute/api>`.
