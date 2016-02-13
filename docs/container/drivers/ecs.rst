Amazon Elastic Container Service Documentation
==============================================

Elastic Container Service is a container-as-a-service feature of `AWS`_.

.. figure:: /_static/images/provider_logos/aws.png
    :align: center
    :width: 300
    :target: http://aws.amazon.com/

To provide API key access, you should apply one of the roles:
* AmazonEC2ContainerServiceFullAccess
* AmazonEC2ContainerServiceReadOnlyAccess

Instantiating the driver
------------------------
        
.. literalinclude:: /examples/container/ecs/instantiate_driver.py
   :language: python

Deploying a container
---------------------

.. literalinclude:: /examples/container/ecs/deploy_container.py
   :language: python

Deploying a container from Docker Hub
-------------------------------------

Docker Hub Client :class:`~libcloud.container.utils.docker.HubClient` is a shared utility class for interfacing to the public Docker Hub Service.

You can use this class for fetching images to deploy to services like ECS

.. literalinclude:: /examples/container/docker_hub.py
   :language: python

Deploying a container from Amazon Elastic Container Registry (ECR)
------------------------------------------------------------------

Amazon ECR is a combination of the Docker Registry V2 API and a proprietary API. The ECS driver includes methods for talking to both APIs.

Docker Registry API Client :class:`~libcloud.container.utils.docker.RegistryClient` is a shared utility class for interfacing to the public Docker Hub Service.

You can use a factory method to generate an instance of RegsitryClient from the ECS driver. This will request a 12 hour token from the Amazon API and instantiate a :class:`~libcloud.container.utils.docker.RegistryClient`
object with those credentials.

.. literalinclude:: /examples/container/ecs/container_registry.py
   :language: python

API Docs
--------

.. autoclass:: libcloud.container.drivers.ecs.ElasticContainerDriver
    :members:
    :inherited-members:


.. _`AWS`: https://aws.amazon.com/