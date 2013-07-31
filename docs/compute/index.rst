Compute
=======

The compute component of ``libcloud`` allows you to manage cloud and virtual
servers offered by different providers, more than 20 in total.

In addition to  managing the servers this component also allows you to run
deployment scripts on newly created servers. Deployment or "bootstrap" scripts
allow you to execute arbitrary shell commands. This functionality is usually
used to prepare your freshly created server, install your SSH key, and run a
configuration management tool (such as Puppet, Chef, or cfengine) on it.

Terminology
-----------

* **Node** - represents a cloud or virtual server.
* **NodeSize** - represents node hardware configuration. Usually this is amount
  of the available RAM, bandwidth, CPU speed and disk size. Most of the drivers
  also expose hourly price (in dollars) for the Node of this size.
* **NodeImage** - represents an operating system image.
* **NodeLocation** - represents a physical location where a server can be.
* **NodeState** - represents a node state. Standard states are: ``running``,
  ``rebooting``, ``terminated``, ``pending``, and ``unknown```.
