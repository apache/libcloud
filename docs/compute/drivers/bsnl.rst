BSNL Compute Driver Documentation
=================================

BSNL and Dimension Data (formerly known as Datacraft) have teamed up to launch
dedicated Internet data centres across India to help you leverage the power of
cloud computing. Empowered by BSNL and managed by Dimension Data, these facilities
have been designed to the highest global IT standards, using cutting-edge
technologies to offer you unprecedented bandwidth and latency. 

.. figure:: /_static/images/provider_logos/bsnl.png
    :align: center
    :width: 300
    :target: http://www.bsnlcloud.com/

IaaS has its own non-standard `API`_ , `libcloud` provides a Python
wrapper on top of this `API`_ with common methods with other IaaS solutions and
Public cloud providers. Therefore, you can use use the BSNL libcloud
driver to communicate with both the public and private clouds.

Instantiating a driver
----------------------

When you instantiate a driver you need to pass the following arguments to the
driver constructor:

* ``user_id`` - Your BSNL Cloud username
* ``key`` - Your BSNL Cloud password
* ``region`` - The region key, one of the possible region keys

Possible regions:

* ``bsnl-in`` : BSNL India (IN) - **Default**
* ``bsnl-na`` : BSNL North America (USA)
* ``bsnl-eu`` : BSNL Europe
* ``bsnl-af`` : BSNL Africa
* ``bsnl-au`` : BSNL Australia

.. literalinclude:: /examples/compute/bsnl/instantiate_driver.py
   :language: python

The base `libcloud` API allows you to:

* list nodes, images, instance types, locations

Non-standard functionality and extension methods
------------------------------------------------

The BSNL driver exposes some `libcloud` non-standard
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

.. autoclass:: libcloud.compute.drivers.bsnl.BSNLNodeDriver
    :members:
    :inherited-members:

.. _`API`: http://www.bsnlcloud.com/pages/index.asp
