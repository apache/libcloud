ProfitBricks Driver Documentation
=================================

`ProfitBricks`_ is an innovative and enterprise-grade IaaS provider.

.. figure:: /_static/images/provider_logos/profitbricks.png
    :align: center
    :width: 300
    :target: https://www.profitbricks.com/

The ProfitBricks driver allows you to integrate with the `ProfitBricks Cloud API`_ to manage
virtual data centers and other resources located in the United States and Germany availability zones.

Instantiating a Driver
----------------------

Before you start using the ProfitBricks driver you will have to sign up for a ProfitBricks account.
To instantiate a driver you will need to pass your ProfitBrick credentials, i.e., username and password.

.. literalinclude:: /examples/compute/profitbricks/instantiate_driver.py
   :language: python

Examples
--------

Create a data center
~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: /examples/compute/profitbricks/create_datacenter.py
   :language: python

Create a LAN
~~~~~~~~~~~~

.. literalinclude:: /examples/compute/profitbricks/create_lan.py
   :language: python

Create a node
~~~~~~~~~~~~~

.. literalinclude:: /examples/compute/profitbricks/create_node.py
   :language: python

Create an SSD volume
~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: /examples/compute/profitbricks/create_volume.py
   :language: python

Refer to the `driver documentation`_ for more examples and code snippets.

API Docs
--------

.. autoclass:: libcloud.compute.drivers.profitbricks.ProfitBricksNodeDriver
    :members:
    :inherited-members:

.. autoclass:: libcloud.compute.drivers.profitbricks.Datacenter
    :members:

.. autoclass:: libcloud.compute.drivers.profitbricks.ProfitBricksNetworkInterface
    :members:

.. autoclass:: libcloud.compute.drivers.profitbricks.ProfitBricksFirewallRule
    :members:

.. autoclass:: libcloud.compute.drivers.profitbricks.ProfitBricksLan
    :members:

.. autoclass:: libcloud.compute.drivers.profitbricks.ProfitBricksLoadBalancer
    :members:

.. autoclass:: libcloud.compute.drivers.profitbricks.ProfitBricksAvailabilityZone
    :members:

.. autoclass:: libcloud.compute.drivers.profitbricks.ProfitBricksIPBlock
    :members:

.. _`ProfitBricks`: https://www.profitbricks.com/
.. _`ProfitBricks Cloud API`: https://devops.profitbricks.com/api/cloud/
.. _`driver documentation`: https://devops.profitbricks.com/libraries/libcloud/

