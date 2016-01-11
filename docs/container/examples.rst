:orphan:

Container Examples
==================

Installing a container image and deploying it
---------------------------------------------

This example shows how to get install a container image, deploy and start that container.

.. note::
    This example works with Libcloud version 0.21.0 and above.

.. literalinclude:: /examples/container/install_and_deploy.py
   :language: python

Working with cluster supported providers
----------------------------------------

This example shows listing the clusters, find a specific named cluster and deploying a container to it.

.. literalinclude:: /examples/container/working_with_clusters.py
   :language: python

Working with docker hub
-----------------------

Docker Hub Client :class:`~libcloud.container.utils.docker.HubClient` is a shared utility class for interfacing to the public Docker Hub Service.

You can use this class for fetching images to deploy to services like ECS

.. literalinclude:: /examples/container/docker_hub.py
   :language: python