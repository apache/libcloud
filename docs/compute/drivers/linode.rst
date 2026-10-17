Linode Compute Driver Documentation
===================================

`Linode`_ is an American cloud hosting provider offering virtual private
servers (Linodes) in data centers around the world.

.. figure:: /_static/images/provider_logos/linode.png
    :align: center
    :width: 200
    :target: https://www.linode.com/

How to get API Access Token
---------------------------

Visit https://cloud.linode.com/profile/tokens and create a Personal Access
Token. The token is used as the ``key`` argument when instantiating the driver.

Examples
--------

1. Create Linode driver - how to create the Linode driver with an access token
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: /examples/compute/linode/linode_compute_simple.py
   :language: python

API Docs
--------

.. autoclass:: libcloud.compute.drivers.linode.LinodeNodeDriverV4
    :members:
    :inherited-members:

.. _`Linode`: https://www.linode.com/
