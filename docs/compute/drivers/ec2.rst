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

Using temporary security credentials
------------------------------------

Since Libcloud 0.14.0 above, all the Amazon drivers support using temporary
security credentials.

Temporary credentials can be used by passing ``token`` argument to the driver
constructor in addition to the access and secret key. In this case ``token``
represents a temporary session token, access key represents temporary
access key and secret key represents a temporary secret key.

For example:

.. literalinclude:: /examples/compute/ec2/temporary_credentials.py
   :language: python

For more information, please refer to the `Using Temporary Security
Credentials`_ section of the official documentation.

Examples
--------

Allocate, Associate, Disassociate, and Release an Elastic IP
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: /examples/compute/create_ec2_node_and_associate_elastic_ip.py
   :language: python

Create a general purpose SSD volume
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: /examples/compute/ec2/create_general_purpose_ssd_volume.py
   :language: python

Create a provisioned IOPS volume
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: /examples/compute/ec2/create_provisioned_iops_volume.py
   :language: python

API Docs
--------

.. autoclass:: libcloud.compute.drivers.ec2.BaseEC2NodeDriver
    :members:
    :inherited-members:

.. _`Amazon Elastic Compute Cloud (EC2)`: https://aws.amazon.com/ec2/
.. _`Using Temporary Security Credentials`: http://docs.aws.amazon.com/STS/latest/UsingSTS/using-temp-creds.html
