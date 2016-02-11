CloudStack Compute Driver Documentation
=======================================

`CloudStack`_ is an Apache Software Foundation open source software designed to
deploy and manage large networks of virtual machines, as a highly available,
highly scalable Infrastructure as a Service (IaaS) cloud computing platform.
CloudStack is used by a number of service providers to offer public cloud
services, and by many companies to provide an on-premises (private) cloud
offering, or as part of a hybrid cloud solution.

.. figure:: /_static/images/provider_logos/cloudstack.png
    :align: center
    :width: 300
    :target: http://cloudstack.apache.org

`CloudStack`_ has its own non-standard `API`_ , `libcloud` provides a Python
wrapper on top of this `API`_ with common methods with other IaaS solutions and
Public cloud providers. Therefore, you can use use the `CloudStack` libcloud
driver to communicate with your local CloudStack based private cloud as well
as CloudStack based public clouds.

Instantiating a driver
----------------------

When you instantiate a driver you need to pass the following arguments to the
driver constructor:

* ``key`` - Your CloudStack API key
* ``secret`` - Your CloudStack secret key
* ``host`` - The host of your CloudStack endpoint
  (e.g ``localhost`` for ``http://localhost:8080/client/api``)
* ``path`` - The path to your CloudStack endpoint
  (e.g ``/client/api`` for ``http://localhost:8080/client/api``)
* ``url`` - The url to your CloudStack endpoint, mutually exclusive with
  ``host`` and ``path``
* ``secure`` - True or False. True by default

Typically this will lead to:

.. literalinclude:: /examples/compute/cloudstack/instantiate_driver_host_path.py
   :language: python

A complete ``url`` can be used instead:

.. literalinclude:: /examples/compute/cloudstack/instantiate_driver_url.py
   :language: python

In the testing scenario where you are running CloudStack locally, the connection
may be insecure and you may run it on a specific port. In that case, the
instantiation would look like this

.. literalinclude:: /examples/compute/cloudstack/instantiate_driver_insecure_port.py
   :language: python

If you are making a connection to a secure cloud that does not use a trusted
certificate, you will have to disable the SSL verification like so:

.. literalinclude:: /examples/compute/cloudstack/turn_off_ssl_verification.py
   :language: python

For more information on how SSL certificate validation works in Libcloud, see
the :doc:`SSL Certificate Validation </other/ssl-certificate-validation>` page.

`libcloud` now features CloudStack based drivers for the `exoscale`_ and
`ikoula`_ public clouds. Instantiating drivers to those clouds is shown
in the example section below.

The base `libcloud` API allows you to:

* list nodes, images, instance types, locations
* list, create, attach, detach, delete volumes

Non-standard functionality and extension methods
------------------------------------------------

The CloudStack driver exposes a lot of `libcloud` non-standard
functionalities through extension methods and arguments.

These functionalities include:

* start and stop a node
* list disk offerings
* list networks
* list, allocate and release public IPs,
* list, create and delete port forwarding rules
* list, create and delete IP forwarding rules
* list, create, delete and authorize security groups

.. compound::

   Some methods are only valid for `CloudStack`_ advanced zones, while others
   are suited for basic zones.

For information on how to use these functionalities please see the method
docstrings below. You can also use an interactive shell for exploration as
shown in the examples.

Basic Zone Examples
-------------------

To start experimenting with libcloud, starting an ipython interactive shell can
be very handy. Tab completion and shell history are available. Below is an
example of starting such an interactive shell for the exoscale public cloud.
Once started you can explore the libcloud API.

1. Start an interactive shell on Exoscale public cloud
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: /examples/compute/cloudstack/start_interactive_shell_exoscale.py
   :language: python

After experimenting through an interactive shell, you can write scripts that
will directly execute libcloud commands. For instance starting a node with a
specific ssh keypair and a couple of security groups can be done as shown in
the following example:

2. SSH Keypairs management on Exoscale public cloud
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The base libcloud API has been extended to handle management of ssh keypairs.
This is very useful for CloudStack basic zones. SSH Keypairs, can be listed,
created, deleted and imported. This new base API is only available in libcloud
trunk.

.. literalinclude:: /examples/compute/cloudstack/ssh_keypairs_management_exoscale.py
   :language: python

3. Security Groups management on Exoscale public cloud
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Currently there is no security group class defined, hence the result of
`ex_list_securitry_groups()` is a list of dictionaries and not classes.

.. literalinclude:: /examples/compute/cloudstack/security_groups_management.py
   :language: python

4. Create a node with a keypair and a list of security groups
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: /examples/compute/cloudstack/create_cloudstack_node_keypair_secgroup.py
   :language: python

5. Deploying a node with a keypair
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Executing deployment scripts when creating node is currently only supported in
basic zones. The `deploy_node` method is used instead of the `create_node`,
ssh key are passed as arguments as well as a list of scripts.

.. literalinclude:: /examples/compute/cloudstack/deploy_node_with_keypair_security_group.py
   :language: python

Advanced Zone examples
----------------------

Advanced zones in CloudStack provide tenant isolation via VLANs or SDN
technologies like GRE/STT meshes. In a typical advanced zones, users will
deploy nodes on a private network and will use NAT to access their nodes.
Therefore one needs to specify the network a node needs to be deployed on,
and needs to setup port forwarding or IP forwarding rules.

1. Start an interactive shell on Ikoula public cloud
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Instantiation of driver for an advanced zone is the same as with a basic zone,
for example on the `ikoula`_ cloud:

.. literalinclude:: /examples/compute/cloudstack/start_interactive_shell_ikoula.py
   :language: python

2. Create a node on a guest network and allocate an IP
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Starting a node requires a specific guest network.

.. literalinclude:: /examples/compute/cloudstack/create_node_advanced_zone.py
   :language: python

3. List, create and delete a Port forwarding rule
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To access the node via ssh you need you can create a port forwarding rule like so:

.. literalinclude:: /examples/compute/cloudstack/port_forwarding_management.py
   :language: python

API Docs
--------

.. autoclass:: libcloud.compute.drivers.cloudstack.CloudStackNodeDriver
    :members:
    :inherited-members:

.. _`CloudStack`: http://cloudstack.apache.org
.. _`API`: http://cloudstack.apache.org/docs/api/
.. _`exoscale`: https://www.exoscale.ch/
.. _`ikoula`: http://www.ikoula.com/
