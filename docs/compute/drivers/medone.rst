Med-1 Public Cloud Compute Driver Documentation
===============================================


Med-1 is Israel’s main Internet exchange point. As such, it offers a broad
range of hosting, storage, management and data center operation solutions and
services.

Med-1 have a public cloud service, with highly-secure datacenters in Israel and throughout
the world based on the Dimension Data Cloud platform.

.. figure:: /_static/images/provider_logos/med-one.png
    :align: center
    :width: 300
    :target: http://www.med-1.com/

CaaS has its own non-standard `API`_ , `libcloud` provides a Python
wrapper on top of this `API`_ with common methods with other IaaS solutions and
Public cloud providers. Therefore, you can use use the Med-1 libcloud
driver to communicate with both the public and private clouds.

Instantiating a driver
----------------------

When you instantiate a driver you need to pass the following arguments to the
driver constructor:

* ``user_id`` - Your Med-1 Cloud username
* ``key`` - Your Med-1 Cloud password
* ``region`` - The region key, one of the possible region keys

Possible regions:

* ``med1-il`` : Med-1 Israel (IL) - **Default**
* ``med1-na`` : Med-1 North America (USA)
* ``med1-eu`` : Med-1 Europe
* ``med1-af`` : Med-1 Africa
* ``med1-au`` : Med-1 Australia
* ``med1-ap`` : Med-1 Asia Pacific
* ``med1-latam`` : Med-1 Latin America
* ``med1-canada`` : Med-1 Canada

.. literalinclude:: /examples/compute/medone/instantiate_driver.py
   :language: python

The base `libcloud` API allows you to:

* list nodes, images, instance types, locations

Non-standard functionality and extension methods
------------------------------------------------

The Med-1 driver exposes some `libcloud` non-standard
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

.. autoclass:: libcloud.compute.drivers.medone.MedOneNodeDriver
    :members:
    :inherited-members:

.. _`API`: http://www.med-1.com/%D7%90%D7%95%D7%93%D7%95%D7%AA-medonecloud/
