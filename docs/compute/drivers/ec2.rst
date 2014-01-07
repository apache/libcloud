Amazon EC2 Driver Documentation
===============================

`Amazon Elastic Compute Cloud (EC2)`_ is one of the oldest IaaS service
providers out there and a central part of Amazon.com's cloud computing
platform, Amazon Web Services (AWS).

.. figure:: /_static/images/provider_logos/aws.png
    :align: center
    :width: 300
    :target: https://aws.amazon.com/ec2/

It allows users to rent virtual servers in more than 8 regions such as:

* US East (Northern Virginia) Region
* US West (Oregon) Region
* US West (Northern California) Region
* EU (Ireland) Region
* Asia Pacific (Singapore) Region
* Asia Pacific (Sydney) Region
* Asia Pacific (Tokyo) Region
* South America (Sao Paulo) Region

Examples
--------

Allocate, Associate, Disassociate, and Release an Elastic IP
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: /examples/compute/create_ec2_node_and_associate_elastic_ip.py
   :language: python

API Docs
--------

.. autoclass:: libcloud.compute.drivers.ec2.BaseEC2NodeDriver
    :members:
    :inherited-members:

.. _`Amazon Elastic Compute Cloud (EC2)`: https://aws.amazon.com/ec2/
