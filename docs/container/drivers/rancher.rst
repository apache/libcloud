Rancher Container Service Documentation
=======================================

Rancher is a container orchestration platform.

.. figure:: /_static/images/provider_logos/rancher.png
    :align: center
    :width: 300
    :target: http://rancher.com/

This driver supports the main top-level interactions for handling containers,
services, and stacks in a Rancher Environment.

Here are some notes around this driver:

- Does not support user based API credentials, only Environment API
  credentials (one env, no cluster support)
- Does not support images other than docker formatted images. ``docker:``
  prefix is forced!
- Images follow a standardized format. See deploy_container docstring!
- ``launchConfig`` options for ``ex_deploy_service`` can all be defined at the
  top level then get slipstreamed appropriately.
- Passing your own cert/key of any sort for SSL/TLS is not presently supported.

To enable API access, obtain an Environment API Key from your Rancher Server
for the specific environment you want to control.

Instantiating the driver
------------------------

.. literalinclude:: /examples/container/rancher/instantiate_driver.py
   :language: python

Deploying a container
---------------------

.. literalinclude:: /examples/container/rancher/deploy_container.py
   :language: python

Deploying a service
-------------------

.. literalinclude:: /examples/container/rancher/deploy_service.py
   :language: python

Deploying a stack
-----------------

.. literalinclude:: /examples/container/rancher/deploy_stack.py
   :language: python

Searching for a container
-------------------------

.. literalinclude:: /examples/container/rancher/search_containers.py
   :language: python

API Docs
--------

.. autoclass:: libcloud.container.drivers.rancher.RancherContainerDriver
    :members:
    :inherited-members:

Contributors
------------

For the first version of this driver, Mario Loria of Arroyo Networks wrote most
of the code. He received help from Anthony Shaw, a core libcloud contributor
and Vincent Fiduccia, software architect at Rancher Labs.

.. _`Rancher`: https://rancher.com/