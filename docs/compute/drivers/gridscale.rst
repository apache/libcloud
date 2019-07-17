gridscale Compute Driver Documentation
======================================

`gridscale`_ is a German cloud provider with focus on awesome user experience.

.. figure:: /_static/images/provider_logos/gridscale.png
    :align: center
    :width: 300
    :target: https://www.gridscale.io/

Instantiating a driver
----------------------

The gridscale driver requires your User_Uuid and your API-Token.
You will have to generate a API-Token first, to be able to do that,
you want to make an account and create a token under the API-Key option in
the panel.

.. literalinclude:: /examples/compute/gridscale/instantiate_driver.py
   :language: python

Creating a Server
-----------------

.. literalinclude:: /examples/compute/gridscale/create_node.py
   :language: python

Create a server, SSH into it and run deployment script on it
------------------------------------------------------------

.. literalinclude:: /examples/compute/gridscale/deploy_node.py
   :language: python

API Docs
--------

API
~~~

.. autoclass:: libcloud.compute.drivers.gridscale.GridscaleNodeDriver
    :members:
    :inherited-members:


.. _`gridscale`: https://www.gridscale.io/
