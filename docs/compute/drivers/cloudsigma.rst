CloudSigma Compute Driver Documentation
=======================================

`CloudSigma`_ is a pure IaaS provided based in Zurich, Switzerland with
data centers in Zurich, Switzerland, Las Vegas, United States and Washington DC,
United States.

.. figure:: /_static/images/provider_logos/cloudsigma.png
    :align: center
    :width: 300
    :target: https://www.cloudsigma.com

CloudSigma driver supports working with legacy `API v1.0`_ and a new and
actively supported `API v2.0`_. API v1.0 has been deprecated and as such,
you are strongly encouraged to migrate any existing code which uses API v1.0 to
API v2.0.

Instantiating a driver
----------------------

CloudSigma driver constructor takes different arguments with which you tell
it which region to connect to, which api version to use and so on.

Available arguments:

* ``region`` - Which region to connect to. Defaults to ``zrh``. All the
  supported values: ``zrh``, ``lvs``, ``wdc``
* ``api_version`` - Which API version to use. Defaults to ``2.0``. All the
  supported values: ``1.0`` (deprecated), ``2.0``

For information on how to use those arguments, see the `Examples`_ section
below.

Basics
------

Pre-installed library drives vs installation CD drives
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

CloudSigma has a concept of so called library drives. Library drives exist in
two forms:

1. Pre-installed library drives
2. Installation CD drives

Pre-installed library drives already have an existing operating system
installed on them. They can be cloned and directly used when creating a server.

In Libcloud, pre-installed library drives are exposed as
:class:`libcloud.compute.base.NodeImage` objects through a standard
:meth:`libcloud.compute.base.NodeDriver.list_images` method.

Installation CD drives are different and not something which is supported by a
big chunk of other providers. Unlike pre-installed drives which represent an
already installed operating system, those drives represent an operating system
installation medium (CD / DVD).

Those installation CD drives don't fit well into the ``NodeImage`` concept so they
are represented using
:class:`libcloud.compute.drivers.cloudsigma.CloudSigmaDrive` objects through the
:meth:`libcloud.compute.drivers.cloudsigma.CloudSigma_2_0_NodeDriver.ex_list_library_drives`
method.

For more information and examples on how to use the installation CD drives, see
the `Create a server using an installation CD`_ example below.

Library drives vs user drives
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

As noted above, CloudSigma has a concept called library drives. You can use
library drives either by cloning them (pre-installed library drives) or by
directly mounting them to the server (installer CD drives).

Besides library drives, CloudSigma also has a concept of user drives. User
drives are drives which belong to your account. Those drives have either been
cloned from the library drives or created from scratch.

To view all the drives which belong to your account, you can use the
:meth:`libcloud.compute.drivers.cloudsigma.CloudSigma_2_0_NodeDriver.ex_list_user_drives`
method.

Server creation work-flow
~~~~~~~~~~~~~~~~~~~~~~~~~

Server creation work-flow consists of multiple steps and depends on the type of
the image you are using.

If you are using a pre-installed image:

1. Provided image is cloned so it can be used
2. Cloned drive is resized to match the size specified using NodeSize
3. Server is created and the cloned drive is attached to it
4. Server is started

If you are using an installation CD:

1. Server is created and selected installation CD is attached to it
2. Server is started

Examples
--------

Connect to zrh region using new API v2.0
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: /examples/compute/cloudsigma/connect_to_api_2_0.py
   :language: python

Connect to zrh region using deprecated API v1.0
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

As noted above, API 1.0 has been deprecated and you are strongly encouraged to
migrate any code which uses API 1.0 to API 2.0. This example is only included
here for completeness.

.. literalinclude:: /examples/compute/cloudsigma/connect_to_api_1_0.py
   :language: python

Listing available sizes, images and drives
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In Libcloud, a :class:`libcloud.compute.base.NodeSize` represents a physical
configuration of a server and a :class:`libcloud.compute.base.NodeImage`
represents an operating system.

To comply with a standard Libcloud API,
:meth:`libcloud.compute.base.NodeDriver.list_images` method only returns
available pre-installed library images. Those images can be passed directly
to
:meth:`libcloud.compute.drivers.cloudsigma.CloudSigma_2_0_NodeDriver.create_node`
method and used to create a server.

If you want to list all the available images and drives, you should use
:meth:`libcloud.compute.drivers.cloudsigma.CloudSigma_2_0_NodeDriver.ex_list_library_drives`
method.

The example below shows how to list all the available sizes, images and
drives.

.. literalinclude:: /examples/compute/cloudsigma/list_sizes_images_drives.py
   :language: python

Create a server using a custom node size
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Unlike most of the other cloud providers out there, CloudSigma is not limited
to pre-defined instance sizes and allows you to specify your own custom size
when creating a node.

This means you can totally customize server for your work-load and specify
exactly how much CPU, memory and disk space you want.

To follow Libcloud standard API, CloudSigma driver also exposes some
pre-defined instance sizes through the
:meth:`libcloud.compute.drivers.cloudsigma.CloudSigma_2_0_NodeDriver.list_sizes`
method.

This example shows how to create a node using a custom size.

.. literalinclude:: /examples/compute/cloudsigma/create_server_custom_size.py
   :language: python

Keep in mind that there are some limits in place:

* CPU - 1 GHz to 80GHz
* Memory - 1 GB to 128 GB
* Disk - 1 GB to 8249 GB

You can find exact limits and free capacity for your account's location using
:meth:`libcloud.compute.drivers.cloudsigma.CloudSigma_2_0_NodeDriver.ex_list_capabilities`
method.

Create a server with a VLAN
~~~~~~~~~~~~~~~~~~~~~~~~~~~

By default, each server created with Libcloud has one network interface with a
public IP assigned.

Besides networks with a public IP, CloudSigma also allows you to create and use
VLANs.

This example shows how to do that. It first creates a VLAN by purchasing a
subscription and then assigns the create VLAN to a node upon creation.

Created node will have two network interfaces assigned - one with a public IP
and one with the provided VLAN.

.. literalinclude:: /examples/compute/cloudsigma/create_server_with_vlan.py
   :language: python

Create a server using an installation CD
----------------------------------------

This example shows how to create a server using an installation CD instead
of a pre-installed drive (all the other create server examples in this section
assume you are using a pre-installed drive).

Creating a server using an installation CD means that you can't directly use
the server after it has been created. Instead, you need to connect to the
server using VNC and walk-through the installation process.

The example below shows how to create a server using FreeBSD 8.2 installation
CD.

.. literalinclude:: /examples/compute/cloudsigma/create_server_using_installation_cd.py
   :language: python

Associate metadata with a server upon creation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

CloudSigma allows you to associate arbitrary key / value pairs with each
server. This examples shows how to do that upon server creation.

.. literalinclude:: /examples/compute/cloudsigma/create_server_with_metadata.py
   :language: python

Add a tag to the server
~~~~~~~~~~~~~~~~~~~~~~~

CloudSigma allows you to organize resources such as servers and drivers by
tagging them. This example shows how to do that.

.. literalinclude:: /examples/compute/cloudsigma/tag_server.py
   :language: python

Open a VNC tunnel to the server
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

CloudSigma allows you to connect and manage your server using `VNC`_. To
connect to the server using VNC, you can use clients such as ``vinagre`` or
``vncviewer`` on Ubuntu and other Linux distributions.

This example shows how to open a VNC connection to your server and retrieve
a connection URL.

After you have retrieved the URL, you will also need a password which you
specified (or it was auto-generated if you haven't specified it) when creating a
server.

If you can't remember the password, you can use
:meth:`libcloud.compute.drivers.CloudSigma_2_0_NodeDriver.list_nodes` method
and access ``node.extra['vnc_password']`` attribute.

After you are done using VNC, it's recommended to close a tunnel using
:meth:`libcloud.compute.drivers.cloudsigma.CloudSigma_2_0_NodeDriver.ex_close_vnc_tunnel`
method.

.. literalinclude:: /examples/compute/cloudsigma/open_vnc_tunnel.py
   :language: python

Attach firewall policy to the server
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

CloudSigma allows you to restrict access to your servers by using firewall
policies. This example shows how to attach an existing policy to all your
servers tagged with ``database-server``.

.. literalinclude:: /examples/compute/cloudsigma/attach_firewall_policy.py
   :language: python

Starting a server in a different availability group using avoid functionality
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

CloudSigma allows you to specify a list of server UUIDs which to avoid when
starting a server.

This helps make your infrastructure more highly available and is useful when
you want to create a server in a different availability zone than the existing
server.

The example below shows how to create a new server in a different availability
zone from all the existing servers.

Keep in mind that `as noted in the CloudSigma documentation
<https://zrh.cloudsigma.com/docs/availability_groups.html#general-notes-on-avoid-functionality>`_,
this functionality uses the best effort mode. This means that the request might
succeed even if the avoid can not be satisfied and the requested resource ends
in the same availability group as an avoid resource.

.. literalinclude:: /examples/compute/cloudsigma/create_node_ex_avoid.py
   :language: python

To check which servers and drives share the same physical compute / storage
host, you can use the
:meth:`libcloud.compute.drivers.cloudsigma.CloudSigma_2_0_NodeDriver.ex_list_servers_availability_groups`
and :meth:`libcloud.compute.drivers.cloudsigma.CloudSigma_2_0_NodeDriver.ex_list_drives_availability_groups`
method as displayed below.

.. literalinclude:: /examples/compute/cloudsigma/check_avail_groups.py
   :language: python

Both of those methods return a ``list``. Servers and drives which share the same
physical host will be stored under the same index in the returned list.

Purchasing a subscription
~~~~~~~~~~~~~~~~~~~~~~~~~

A lot of resources such as SSDs, VLANs, IPs and others are created by
purchasing a subscription.

When you purchase a subscription you need to supply the following arguments:

* ``amount`` - Subscription amount. Unit depends on the purchased resource.
  For example, if you are purchasing a ``vlan`` resource, ``amount`` represents
  a number of VLAN networks you want to purchase.
* ``period`` - For how long to purchase the subscription. Example values:
  ``1 month``, ``30 days``, etc.
* ``resource`` - Resource to purchase the subscription for. Valid values:
  ``cpu``, ``mem``, ``tx``, ``ip``, ``vlan``
* ``auto_renew`` - ``True`` to auto renew the subscription when it expires.

The example below shows how to purchase a single VLAN for a duration of
30 days which will be automatically renewed when it expires.

.. literalinclude:: /examples/compute/cloudsigma/create_vlan_subscription.py
   :language: python

Retrieving the account balance
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This example shows how to retrieve the account balance. The method returns a
dictionary with two keys - ``balance`` and ``currency``.

.. literalinclude:: /examples/compute/cloudsigma/get_account_balance.py
   :language: python

Other Resources
---------------

* `CloudSigma API V2.0 is now supported in Libcloud`_ - CloudSigma Blog

API Docs
--------

.. autoclass:: libcloud.compute.drivers.cloudsigma.CloudSigma_2_0_NodeDriver
    :members:

.. autoclass:: libcloud.compute.drivers.cloudsigma.CloudSigmaDrive
    :members:

.. autoclass:: libcloud.compute.drivers.cloudsigma.CloudSigmaTag
    :members:

.. autoclass:: libcloud.compute.drivers.cloudsigma.CloudSigmaSubscription
    :members:

.. autoclass:: libcloud.compute.drivers.cloudsigma.CloudSigmaFirewallPolicy
    :members:

.. autoclass:: libcloud.compute.drivers.cloudsigma.CloudSigmaFirewallPolicyRule
    :members:

.. _`CloudSigma`: http://www.cloudsigma.com/
.. _`API v1.0`: https://www.cloudsigma.com/legacy/cloudsigma-api-1-0/
.. _`API v2.0`: https://zrh.cloudsigma.com/docs/
.. _`VNC`: http://en.wikipedia.org/wiki/Virtual_Network_Computing
.. _`CloudSigma API V2.0 is now supported in Libcloud`: https://www.cloudsigma.com/2014/02/11/cloudsigma-api-v2-0-is-now-supported-in-libcloud/
