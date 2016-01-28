Container
=========

.. note::

    Container API is available in Libcloud 1.0.0-pre1 and higher.

.. note::

    Container API is currently in an EXPERIMENTAL state.

Container API allows users to install and deploy containers onto container based virtualization platforms. This is designed to target both
on-premise installations of software like Docker as well as interfacing with Cloud Service Providers that offer Container-as-a-Service APIs.

For a working example of the container driver with cluster support, see the example for Amazon's Elastic Container Service:

.. literalinclude:: /examples/container/ecs/deploy_container.py
   :language: python

For an example of the simple container support, see the Docker example:

.. literalinclude:: /examples/container/docker/deploy_container.py
   :language: python

Drivers
-------
Container-as-a-Service providers will implement the `ContainerDriver` class to provide functionality for :

* Listing deployed containers
* Starting, stopping and restarting containers (where supported)
* Destroying containers
* Creating/deploying containers
* Listing container images
* Installing container images (pulling an image from a local copy or remote repository)

Driver base API documentation is found here:

* :class:`~libcloud.container.base.ContainerDriver` - A driver for interfacing to a container provider


Simple Container Support
------------------------

* :class:`~libcloud.container.base.ContainerImage` - Represents an image that can be deployed, like an application or an operating system
* :class:`~libcloud.container.base.Container` - Represents a deployed container image running on a container host

Cluster Suppport
----------------

Cluster support extends on the basic driver functions, but where drivers implement the class-level attribute `supports_clusters` as True
clusters may be listed, created and destroyed. When containers are deployed, the target cluster can be specified.

* :class:`~libcloud.container.base.ContainerCluster` - Represents a deployed container image running on a container host
* :class:`~libcloud.container.base.ClusterLocation` - Represents a location for clusters to be deployed

Bootstrapping Docker with Compute Drivers
-----------------------------------------

The compute and container drivers can be combined using the :doc:`deployment </compute/deployment>` feature of the compute driver to bootstrap an installation of a container virtualization provider like Docker.
Then using the Container driver, you can connect to that API and install images and deploy containers.

Supported Providers
-------------------

For a list of supported providers see :doc:`supported providers page
</container/supported_providers>`.

Examples
--------

We have :doc:`examples of several common patterns </container/examples>`.

API Reference
-------------

For a full reference of all the classes and methods exposed by the Container
API, see :doc:`this page </container/api>`.

Utility Classes
---------------

There are some utility classes for example, a Docker Hub API client for fetching images
and iterating through repositories see :doc:`this page </container/utilities>`.
