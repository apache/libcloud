Compute Examples
================

Example: Creating a Node
------------------------

.. literalinclude:: /examples/compute/create_node.py
   :language: python

Example: List Nodes Across Multiple Providers
---------------------------------------------

.. literalinclude:: /examples/compute/list_nodes_across_multiple_providers.py
   :language: python

Example: Bootstrapping Puppet on a Node
---------------------------------------

.. literalinclude:: /examples/compute/bootstrapping_puppet_on_node.py
   :language: python

Create an OpenStack node using trystack.org provider
----------------------------------------------------

`trystack.org`_ allows users to try out OpenStack for free. This example
demonstrates how to launch an OpenStack node on the ``trystack.org`` provider
using a generic OpenStack driver.

.. literalinclude:: /examples/compute/trystack.py
   :language: python

.. _`trystack.org`: http://trystack.org/

Create an OpenStack node using a local OpenStack provider
---------------------------------------------------------

This example shows how to create a node using a local OpenStack installation.
Don't forget to replace ``your_auth_username``, ``your_auth_password`` and
``ex_force_auth_url`` with the correct values specific to your installation.

.. note::
    This example works with Libcloud version 0.9.0 and above.

.. literalinclude:: /examples/compute/openstack_simple.py
   :language: python

Create a VMware vCloud v1.5 node using generic provider
-------------------------------------------------------

This example demonstrates how to launch a VMware vCloud v1.5 node on a
generic provider such as a test lab

.. note::
    This example works with Libcloud version 0.10.1 and above.

.. literalinclude:: /examples/compute/vmware_vcloud_1.5.py
   :language: python

Create EC2 node using a provided key pair and security groups
-------------------------------------------------------------

.. note::

    This example assumes the provided key pair already exists. If the key pair
    doesn't exist yet, you can create it using AWS dashboard, or
    :func:`ex_import_keypair` driver method.

This example demonstrates how to create an EC2 node using an existing key pair.
Created node also gets added to the provided security groups.

.. literalinclude:: /examples/compute/create_ec2_node_keypair_and_to_secgroup.py
   :language: python

As noted in the example, you use `ex_keyname` argument to specify key pair name
and `ex_securitygroup` to specify a name of a single (``str``) or multiple
groups (``list``) you want this node to be added to.

Create EC2 node using a custom AMI
----------------------------------

This examples demonstrates how to create an EC2 node using a custom AMI (Amazon
Machine Image).

AMI's are region specific which means you need to select AMI which is available
in the region of an EC2 driver you have instantiated.

In Libcloud 0.13.0 and lower, region is determined based on the provider
constant (``us-east-1`` is available as ``Provider.EC2_US_EAST``, ``us-west-1``
is available as ``Provider.EC2_US_WEST`` and so on). For a full list of
supported providers and provider constants, see
:doc:`supported providers page </compute/supported_providers>`

.. literalinclude:: /examples/compute/create_ec2_node_custom_ami.py
   :language: python

Create EC2 node using an IAM Profile
------------------------------------

.. note::

    This example assumes the IAM profile already exists. If the key pair
    doesn't exist yet, you must create it manually.

.. literalinclude:: /examples/compute/create_ec2_node_iam.py
   :language: python

Create a node on a CloudStack provider using a provided key pair and security groups
------------------------------------------------------------------------------------

.. note::

    This example assumes the provided key pair already exists. If the key pair
    doesn't exist yet, you can create it using the provider's own UI, or
    :func:`ex_create_keypair` driver method.
    This functionality is only available in Libcloud 0.14.0 and above.

This example demonstrates how to create a node using an existing key pair.
Created node also gets added to the provided security groups.

.. literalinclude:: /examples/compute/create_cloudstack_node_keypair_secgroup.py
   :language: python

Create flaoting IP and attach it to a node using a local OpenStack provider
---------------------------------------------------------------------------

This example demonstrates how to use OpenStack's floating IPs.

.. literalinclude:: /examples/compute/openstack_floating_ips.py
   :language: python

Create an IBM SCE Windows node using generic provider
-----------------------------------------------------

.. note::

    ex_configurationData is the key component of this example.

This example shows how to create a Windows node using IBM SmartCloud Enterpiese.

.. literalinclude:: /examples/compute/create_ibm_sce_windows_node.py
   :language: python
