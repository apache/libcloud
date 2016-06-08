Aliyun(AliCloud) ECS Driver Documentation
=========================================

`Aliyun(AliCloud) Elastic Compute Service (ECS)`_ is a simple and efficient computing service, whose processing capacity is scalable. It can help you quickly build a more stable and secure application. It helps you improve the efficiency of operation and maintenance, and reduce the cost of IT. ECS enables you to focus on core business innovation.

Regions
-------

The Aliyun supports mutiple regions, which indicates the distinct physical location all over the world. The current available regions in China are Hangzhou, Qingdao, Beijing, and Shenzhen. Other regions available outside of Chinese Mainland are Hong Kong, Singapore, and United States.

You can select the AliCloud region according to the customer base, cost effectiveness, disaster recovery site, or any compliance requirements. ECS instances in the same region can communicate with each other over intranet, whereas cross-region ECS communication requires the internet connection.

A region equals to `NodeLocation` in libcloud. Users can list all available regions, for example:

.. literalinclude:: /examples/compute/ecs/list_locations.py
   :language: python

ECS Instance Types
------------------

An instance type defines some computing capabilities, including CPU, memory, associated with a set of ECS instances.

Aliyun provides two generations, three instance type families, and more than ten instance types to support different usecases.

For more information, please refer to the `Instance Generations`_ section, `Instance Type Families`_ section and `Instance Type`_ section of the official documentation.

An instance type equals to the `NodeSize` in libcloud. Users can list all available instance types, for example:

.. literalinclude:: /examples/compute/ecs/list_sizes.py
   :language: python

Security Groups
---------------

A security group is a logical grouping which groups instances in the same region with the same security requirements and mutual trust. Security groups, like firewalls, are used to configure network access controls for one or more ECS instances.

Each instance belongs to at least one security group and this must be specified at the time of creation.

Users can list all defined security groups, for example:

.. literalinclude:: /examples/compute/ecs/ex_list_security_groups.py
   :language: python

For more information, please refer to the `Security Groups`_ section of the official documentation.

Images
------

An image is an ECS instance operating environment template. It generally includes the operating system and preloaded software. It equals to `NodeImage` in libcloud.

Users can list all available images, for example:

.. literalinclude:: /examples/compute/ecs/list_images.py
   :language: python

Storage
-------

Aliyun ECS provides multiple types of storage disks for instances to meet the requirements of different application scenarios. An instance can use all these types of volumes independently.

There are three types of disks: general cloud disk, SSD cloud disk and ephemeral SSD disk.

Aliyun provides the snapshot mechanism. This creates a snapshot that retains a copy of the data on a disk at a certain time point manually or automatically.

Aliyun storage disks equal to `StorageVolume` in libcloud. Users can manage volumes and snapshots, for example:

.. literalinclude:: /examples/compute/ecs/manage_volumes_and_snapshots.py
   :language: python

For more information, please refer to the `Storage`_ section of the official documentation.

IP Address
----------

IP addresses are an important means for users to access ECS instances and for ECS instances to provide external services. Each instance will be allocated a private network card and bound to a specific private IP and a public network card by default.

Private IPs can be used for SLB load balancing, intranet mutual access between ECS instances or between an ECS instance and another cloud service within the same region. Data traffic through private IPs between instances in the same region is free.

Public IPs are used to access the instance from the internet. Public network traffic is not free.

Users can select different internet charge type and bandwidth limitations.

Instance lifecycle management
-----------------------------

.. literalinclude:: /examples/compute/ecs/manage_nodes.py
   :language: python

API Reference
-------------

.. autoclass:: libcloud.compute.drivers.ecs.ECSDriver
    :members:
    :inherited-members:

.. _`Aliyun(AliCloud) Elastic Compute Service (ECS)`: https://www.aliyun.com/product/ecs/?lang=en
.. _`Instance Generations`: https://docs.aliyun.com/en#/pub/ecs_en_us/product-introduction/instance&instancegeneration
.. _`Instance Type Families`: https://docs.aliyun.com/en#/pub/ecs_en_us/product-introduction/instance&instancetypefamily
.. _`Instance Type`: https://docs.aliyun.com/en#/pub/ecs_en_us/product-introduction/instance&type
.. _`Security Groups`: https://docs.aliyun.com/en#/pub/ecs_en_us/product-introduction/network&securitygroup
.. _`Storage`: https://docs.aliyun.com/en#/pub/ecs_en_us/product-introduction/storage&summary
