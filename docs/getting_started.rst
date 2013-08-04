Getting Started
===============

Installation
------------

Libcloud is available on PyPi and can be installed using pip:

.. sourcecode:: bash

    pip install apache-libcloud

Upgrading
---------

If you used pip to install the library you can also use it to upgrade it:

.. sourcecode:: bash

    pip install --upgrade apache-libcloud

Example: Connecting with a Driver
---------------------------------

.. literalinclude:: /examples/compute/list_nodes.py
   :language: python

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
