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
   
API Docs
--------

.. autoclass:: libcloud.container.drivers.ecs.ElasticContainerDriver
    :members:
    :inherited-members:


.. _`AWS`: https://aws.amazon.com/