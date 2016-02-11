Internet Solutions Compute Driver Documentation
===============================================

Internet Solutions (IS) is the first commericial ISP in South Africa and currently the largest in
the southern cape. IS offer a public cloud service based called Compute-as-a-Service (CAAS).
The CaaS service is available on one of the public cloud instances.

.. figure:: /_static/images/provider_logos/internetsolutions.png
    :align: center
    :width: 300
    :target: http://www.cloud.is.co.za/

CaaS has its own non-standard `API`_ , `libcloud` provides a Python
wrapper on top of this `API`_ with common methods with other IaaS solutions and
Public cloud providers. Therefore, you can use use the Internet Solutions libcloud
driver to communicate with both the public and private clouds.

Instantiating a driver
----------------------

When you instantiate a driver you need to pass the following arguments to the
driver constructor:

* ``user_id`` - Your Internet Solutions Cloud username
* ``key`` - Your Internet Solutions Cloud password
* ``region`` - The region key, one of the possible region keys

Possible regions:

* ``is-na`` : Internet Solutions North America (USA)
* ``is-eu`` : Internet Solutions Europe
* ``is-af`` : Internet Solutions Africa - **Default**
* ``is-au`` : Internet Solutions Australia
* ``is-latam`` : Internet Solutions Latin America
* ``is-ap`` : Internet Solutions Asia Pacific
* ``is-canada`` : Internet Solutions Canada region

.. literalinclude:: /examples/compute/internetsolutions/instantiate_driver.py
   :language: python

The base `libcloud` API allows you to:

* list nodes, images, instance types, locations

Non-standard functionality and extension methods
------------------------------------------------

The Internet Solutions driver exposes some `libcloud` non-standard
functionalities through extension methods and arguments.

These functionalities include:

* start and stop a node
* list networks
* create firewalls, configure network address translation
* provision layer 3 networks

For information on how to use these functionalities please see the method
docstrings below. You can also use an interactive shell for exploration as
shown in the examples.

API Docs
--------

.. autoclass:: libcloud.compute.drivers.internetsolutions.InternetSolutionsNodeDriver
    :members:
    :inherited-members:

.. _`API`: http://www.cloud.is.co.za/IS-Public-CaaS/Pages/REST-based-API.aspx
